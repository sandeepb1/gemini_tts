"""Sensor platform for Voice Assistant Gemini."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import VoiceAssistantGeminiCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="session_count",
        name="Active Sessions",
        icon="mdi:chat",
        native_unit_of_measurement="sessions",
    ),
    SensorEntityDescription(
        key="last_interaction",
        name="Last Interaction",
        icon="mdi:clock-outline",
        device_class="timestamp",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Voice Assistant Gemini sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        VoiceAssistantGeminiSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    
    async_add_entities(entities)
    return True


class VoiceAssistantGeminiSensor(CoordinatorEntity, SensorEntity):
    """Voice Assistant Gemini sensor."""

    def __init__(
        self,
        coordinator: VoiceAssistantGeminiCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Voice Assistant Gemini",
            "manufacturer": "Voice Assistant Gemini",
            "model": "Integration",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        if self.entity_description.key == "session_count":
            sessions = self.coordinator.data.get("sessions", {})
            return len(sessions)
        
        elif self.entity_description.key == "last_interaction":
            sessions = self.coordinator.data.get("sessions", {})
            if not sessions:
                return None
            
            # Find the most recent interaction
            latest_time_str = None
            for session_data in sessions.values():
                last_interaction = session_data.get("last_interaction")
                if last_interaction:
                    if latest_time_str is None or last_interaction > latest_time_str:
                        latest_time_str = last_interaction
            
            if latest_time_str:
                try:
                    # Convert string timestamp to datetime object
                    if isinstance(latest_time_str, str):
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(latest_time_str.replace('Z', '+00:00'))
                        # Ensure it's timezone-aware
                        if dt.tzinfo is None:
                            dt = dt_util.as_utc(dt)
                        return dt
                    elif isinstance(latest_time_str, datetime):
                        # Already a datetime, ensure it's timezone-aware
                        if latest_time_str.tzinfo is None:
                            return dt_util.as_utc(latest_time_str)
                        return latest_time_str
                except (ValueError, TypeError) as err:
                    _LOGGER.warning("Invalid timestamp format: %s - %s", latest_time_str, err)
                    return None
            
            return None
        
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success 