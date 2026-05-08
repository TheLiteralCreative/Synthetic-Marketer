"""Settings persistence — JSON file at data/settings.json.

For B1: simple JSON file. API key storage will move to OS keychain
(via `keyring` package) in B5 — JSON is fine for non-secret config.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "anthropic_api_key": "",
    "psi_api_key": "",
    "output_folder": str(ROOT),
    "theme": "system",
    "track_costs": True,
}


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict[str, Any]:
    """Load settings, applying defaults for any missing keys."""
    _ensure_data_dir()
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in DEFAULTS})
    return merged


def save(settings: dict[str, Any]) -> dict[str, Any]:
    """Persist settings, returning the merged result."""
    _ensure_data_dir()
    current = load()
    current.update({k: v for k, v in settings.items() if k in DEFAULTS})
    SETTINGS_PATH.write_text(
        json.dumps(current, indent=2) + "\n", encoding="utf-8"
    )
    return current


def redact_for_response(settings: dict[str, Any]) -> dict[str, Any]:
    """Strip secret fields before sending to client."""
    out = dict(settings)
    for key in ("anthropic_api_key", "psi_api_key"):
        val = out.get(key, "")
        if val:
            out[key] = f"set ({len(val)} chars)"
        else:
            out[key] = ""
    return out
