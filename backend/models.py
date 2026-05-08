"""Pydantic models for API request/response shapes."""
from typing import Optional

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    status: str
    version: str
    name: str
    ready: bool


class SettingsModel(BaseModel):
    anthropic_api_key: Optional[str] = None
    psi_api_key: Optional[str] = None
    output_folder: Optional[str] = None
    theme: Optional[str] = Field(default=None, pattern="^(system|light|dark)$")
    track_costs: Optional[bool] = None


class SettingsResponse(BaseModel):
    output_folder: str
    theme: str
    track_costs: bool
    anthropic_api_key: str  # redacted
    psi_api_key: str  # redacted
