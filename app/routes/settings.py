"""
Settings routes for MAM Audiobook Finder.
Provides API endpoints for runtime-configurable application settings.
"""
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from settings_service import settings_service
from auto_import import get_auto_import_service
from dependencies.abs import require_admin_if_configured

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


class SettingsUpdateBody(BaseModel):
    """Request body for updating settings."""
    auto_import_enabled: bool | None = None
    auto_import_flatten: bool | None = None
    auto_import_poll_interval: int | None = None

    @field_validator("auto_import_poll_interval")
    @classmethod
    def validate_poll_interval(cls, v):
        if v is not None and (v < 15 or v > 300):
            raise ValueError("Poll interval must be between 15 and 300 seconds")
        return v


@router.get("/api/settings")
def get_settings(_admin: dict | None = Depends(require_admin_if_configured)):
    """
    Get all application settings.

    Returns:
        dict: All current settings with their values
    """
    return settings_service.get_all()


@router.put("/api/settings")
async def update_settings(
    body: SettingsUpdateBody,
    _admin: dict | None = Depends(require_admin_if_configured),
):
    """
    Update multiple settings at once.

    The auto-import service will automatically pick up changes on its next poll cycle.
    """
    updates = {}

    if body.auto_import_enabled is not None:
        updates["auto_import_enabled"] = body.auto_import_enabled

    if body.auto_import_flatten is not None:
        updates["auto_import_flatten"] = body.auto_import_flatten

    if body.auto_import_poll_interval is not None:
        updates["auto_import_poll_interval"] = body.auto_import_poll_interval

    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    success = settings_service.set_many(updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update some settings")

    # Reload auto-import service settings
    service = get_auto_import_service()
    await service.reload_settings()

    logger.info(f"Settings updated: {updates}")
    return {"ok": True, "updated": list(updates.keys())}


@router.post("/api/settings/reset")
async def reset_settings(_admin: dict | None = Depends(require_admin_if_configured)):
    """
    Reset all settings to their default values.
    """
    success = settings_service.reset_to_defaults()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset settings")

    # Reload auto-import service settings
    service = get_auto_import_service()
    await service.reload_settings()

    logger.info("Settings reset to defaults")
    return {"ok": True}


@router.get("/api/settings/auto-import/status")
def get_auto_import_status(_admin: dict | None = Depends(require_admin_if_configured)):
    """
    Get auto-import service status and recent activity.

    Returns:
        dict with:
        - running: bool - Is the service running
        - enabled: bool - Is auto-import enabled
        - poll_interval: int - Current poll interval in seconds
        - last_poll_time: str|None - ISO timestamp of last poll
        - pending_count: int - Number of pending candidates
        - recent_activity: list - Recent auto-import attempts
    """
    service = get_auto_import_service()
    recent = service.get_recent_activity(limit=10)

    return {
        "running": service.is_running,
        "enabled": service.enabled,
        "poll_interval": service.poll_interval,
        "last_poll_time": service.last_poll_time.isoformat() if service.last_poll_time else None,
        "pending_count": service.pending_count,
        "recent_activity": recent,
    }
