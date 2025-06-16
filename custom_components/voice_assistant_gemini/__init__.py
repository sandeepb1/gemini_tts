"""The Voice Assistant Gemini integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .coordinator import VoiceAssistantGeminiCoordinator
from .services import async_setup_services
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CONVERSATION, Platform.STT, Platform.TTS]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Voice Assistant Gemini from a config entry."""
    _LOGGER.info("Setting up Voice Assistant Gemini integration")
    
    try:
        # Initialize storage
        _LOGGER.debug("Initializing storage")
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        
        # Create coordinator
        _LOGGER.debug("Creating coordinator")
        coordinator = VoiceAssistantGeminiCoordinator(hass, entry, store)
        
        # Store coordinator in hass data
        _LOGGER.debug("Storing coordinator in hass data")
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "store": store,
        }
        
        # Initialize coordinator data without triggering sensor updates yet
        _LOGGER.debug("Initializing coordinator data")
        try:
            # Load initial data without triggering listeners
            storage_data = await store.async_load() or {}
            coordinator.data = {
                "sessions": storage_data.get("sessions", {}),
                "last_update": None,
            }
            coordinator.last_update_success = True
            _LOGGER.debug("Coordinator data initialized successfully")
        except Exception as coord_err:
            _LOGGER.error("Failed to initialize coordinator data: %s", coord_err, exc_info=True)
            # Set empty data to prevent sensor errors
            coordinator.data = {"sessions": {}, "last_update": None}
            coordinator.last_update_success = True
        
        # Setup services
        _LOGGER.debug("Setting up services")
        try:
            setup_result = await async_setup_services(hass)
            if setup_result:
                _LOGGER.debug("Services setup completed successfully")
            else:
                _LOGGER.warning("Services setup returned False")
        except Exception as service_err:
            _LOGGER.error("Failed to setup services: %s", service_err, exc_info=True)
            # Don't fail the entire setup for service errors
        
        # Register WebSocket API
        _LOGGER.debug("Registering WebSocket API")
        try:
            ws_result = async_register_websocket_api(hass)
            if ws_result:
                _LOGGER.debug("WebSocket API registration completed successfully")
            else:
                _LOGGER.warning("WebSocket API registration returned False")
        except Exception as ws_err:
            _LOGGER.error("Failed to register WebSocket API: %s", ws_err, exc_info=True)
            # Don't fail the entire setup for WebSocket errors
        
        # Setup platforms
        _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
            _LOGGER.debug("Platforms setup completed successfully")
        except Exception as platform_err:
            _LOGGER.error("Failed to setup platforms: %s", platform_err, exc_info=True)
            raise
        
        # Now refresh coordinator data properly (this will trigger sensor updates)
        _LOGGER.debug("Performing initial coordinator refresh")
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.debug("Coordinator refresh completed successfully")
        except Exception as coord_err:
            _LOGGER.warning("Coordinator refresh failed, but continuing: %s", coord_err)
            # Don't fail setup if refresh fails - sensors will show unavailable
        
        # Add options update listener
        _LOGGER.debug("Adding options update listener")
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        
        _LOGGER.info("Voice Assistant Gemini integration setup complete")
        return True
    
    except Exception as err:
        _LOGGER.error("Failed to set up Voice Assistant Gemini integration: %s", err, exc_info=True)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Voice Assistant Gemini integration")
    
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "stt")
            hass.services.async_remove(DOMAIN, "tts")
            hass.services.async_remove(DOMAIN, "converse")
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry) 