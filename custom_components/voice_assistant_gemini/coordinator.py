"""Data update coordinator for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ENABLE_TRANSCRIPT_STORAGE,
    CONF_TRANSCRIPT_RETENTION_DAYS,
    DEFAULT_TRANSCRIPT_RETENTION_DAYS,
    DOMAIN,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
)

_LOGGER = logging.getLogger(__name__)


class VoiceAssistantGeminiCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Voice Assistant Gemini integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: Store,
    ) -> None:
        """Initialize."""
        self.entry = entry
        self.store = store
        self._retry_count = 0
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),  # Check for cleanup every hour
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Load storage data
            storage_data = await self.store.async_load() or {}
            
            # Perform periodic cleanup if transcript storage is enabled
            if self.entry.options.get(CONF_ENABLE_TRANSCRIPT_STORAGE, True):
                await self._cleanup_old_transcripts(storage_data)
            
            # Reset retry count on successful update
            self._retry_count = 0
            
            return {
                "sessions": storage_data.get("sessions", {}),
                "last_update": datetime.now().isoformat(),
            }
        
        except Exception as err:
            self._retry_count += 1
            backoff_time = min(60 * (RETRY_BACKOFF_FACTOR ** self._retry_count), 3600)
            
            _LOGGER.error(
                "Error updating Voice Assistant Gemini data (attempt %d): %s. "
                "Retrying in %d seconds",
                self._retry_count,
                err,
                backoff_time,
            )
            
            if self._retry_count < RETRY_ATTEMPTS:
                # Schedule retry with exponential backoff
                await asyncio.sleep(backoff_time)
                return await self._async_update_data()
            
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _cleanup_old_transcripts(self, storage_data: dict[str, Any]) -> None:
        """Clean up old transcript sessions."""
        if "sessions" not in storage_data:
            return
        
        retention_days = self.entry.options.get(
            CONF_TRANSCRIPT_RETENTION_DAYS, DEFAULT_TRANSCRIPT_RETENTION_DAYS
        )
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        sessions_to_remove = []
        for session_id, session_data in storage_data["sessions"].items():
            try:
                last_interaction = datetime.fromisoformat(
                    session_data.get("last_interaction", "")
                )
                if last_interaction < cutoff_date:
                    sessions_to_remove.append(session_id)
            except (ValueError, TypeError):
                # Invalid date format, mark for removal
                sessions_to_remove.append(session_id)
        
        if sessions_to_remove:
            _LOGGER.info(
                "Cleaning up %d old transcript sessions", len(sessions_to_remove)
            )
            for session_id in sessions_to_remove:
                storage_data["sessions"].pop(session_id, None)
            
            # Save updated data
            await self.store.async_save(storage_data)

    async def async_request_refresh(self) -> None:
        """Request a refresh."""
        await self.async_refresh()

    async def async_get_session_data(self, session_id: str) -> dict[str, Any]:
        """Get session data for a specific session."""
        storage_data = await self.store.async_load() or {}
        sessions = storage_data.get("sessions", {})
        return sessions.get(session_id, {"history": [], "created_at": None, "last_interaction": None})

    async def async_save_session_data(self, session_id: str, session_data: dict[str, Any]) -> None:
        """Save session data for a specific session."""
        storage_data = await self.store.async_load() or {}
        if "sessions" not in storage_data:
            storage_data["sessions"] = {}
        
        storage_data["sessions"][session_id] = session_data
        await self.store.async_save(storage_data)

    async def async_clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        storage_data = await self.store.async_load() or {}
        if "sessions" in storage_data and session_id in storage_data["sessions"]:
            storage_data["sessions"].pop(session_id)
            await self.store.async_save(storage_data)
            _LOGGER.info("Cleared session: %s", session_id)

    async def async_clear_all_sessions(self) -> None:
        """Clear all sessions."""
        storage_data = await self.store.async_load() or {}
        storage_data["sessions"] = {}
        await self.store.async_save(storage_data)
        _LOGGER.info("Cleared all sessions") 