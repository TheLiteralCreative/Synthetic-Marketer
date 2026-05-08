"""API routes. B1 has only /ping and /settings; audit routes land in B2/B3."""
from __future__ import annotations

from fastapi import APIRouter

from backend import __version__, settings as settings_mod
from backend.models import PingResponse, SettingsModel, SettingsResponse

router = APIRouter(prefix="/api")


@router.get("/ping", response_model=PingResponse)
def ping() -> PingResponse:
    """Liveness probe — also reports backend version + readiness state."""
    cfg = settings_mod.load()
    ready = bool(cfg.get("anthropic_api_key"))
    return PingResponse(
        status="ok",
        version=__version__,
        name="Synthetic-Marketer",
        ready=ready,
    )


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    cfg = settings_mod.load()
    return SettingsResponse(**settings_mod.redact_for_response(cfg))


@router.put("/settings", response_model=SettingsResponse)
def put_settings(payload: SettingsModel) -> SettingsResponse:
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    merged = settings_mod.save(update)
    return SettingsResponse(**settings_mod.redact_for_response(merged))
