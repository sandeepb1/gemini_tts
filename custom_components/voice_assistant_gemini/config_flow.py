"""Config flow for Voice Assistant Gemini integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEFAULT_LANGUAGE,
    CONF_DEFAULT_VOICE,
    CONF_ENABLE_TRANSCRIPT_STORAGE,
    CONF_GEMINI_API_KEY,
    CONF_GEMINI_MODEL,
    CONF_LOGGING_LEVEL,
    CONF_MAX_TOKENS,
    CONF_PITCH,
    CONF_SPEAKING_RATE,
    CONF_SSML,
    CONF_STT_API_KEY,
    CONF_STT_PROVIDER,
    CONF_TEMPERATURE,
    CONF_TRANSCRIPT_RETENTION_DAYS,
    CONF_TTS_API_KEY,
    CONF_TTS_PROVIDER,
    CONF_VOLUME_GAIN_DB,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LANGUAGE,
    DEFAULT_LOGGING_LEVEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PITCH,
    DEFAULT_SPEAKING_RATE,
    DEFAULT_SSML,
    DEFAULT_STT_PROVIDER,
    DEFAULT_TEMPERATURE,
    DEFAULT_TRANSCRIPT_RETENTION_DAYS,
    DEFAULT_TRANSCRIPT_STORAGE,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_VOLUME_GAIN_DB,
    DOMAIN,
    GEMINI_MODELS,
    LOGGING_LEVELS,
    STT_PROVIDERS,
    SUPPORTED_LANGUAGES,
    TTS_PROVIDERS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GEMINI_API_KEY): str,
        vol.Optional(CONF_STT_API_KEY, default=""): str,
        vol.Optional(CONF_TTS_API_KEY, default=""): str,
        vol.Optional(CONF_DEFAULT_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        vol.Optional(CONF_STT_PROVIDER, default=DEFAULT_STT_PROVIDER): vol.In(STT_PROVIDERS),
        vol.Optional(CONF_TTS_PROVIDER, default=DEFAULT_TTS_PROVIDER): vol.In(TTS_PROVIDERS),
        vol.Optional(CONF_DEFAULT_VOICE, default=""): str,
        vol.Optional(CONF_SPEAKING_RATE, default=DEFAULT_SPEAKING_RATE): vol.All(
            vol.Coerce(float), vol.Range(min=0.25, max=4.0)
        ),
        vol.Optional(CONF_PITCH, default=DEFAULT_PITCH): vol.All(
            vol.Coerce(float), vol.Range(min=-20.0, max=20.0)
        ),
        vol.Optional(CONF_VOLUME_GAIN_DB, default=DEFAULT_VOLUME_GAIN_DB): vol.All(
            vol.Coerce(float), vol.Range(min=-96.0, max=16.0)
        ),
        vol.Optional(CONF_SSML, default=DEFAULT_SSML): bool,
        vol.Optional(CONF_GEMINI_MODEL, default=DEFAULT_GEMINI_MODEL): vol.In(GEMINI_MODELS),
        vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
        vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=8192)
        ),
        vol.Optional(CONF_LOGGING_LEVEL, default=DEFAULT_LOGGING_LEVEL): vol.In(LOGGING_LEVELS),
        vol.Optional(CONF_ENABLE_TRANSCRIPT_STORAGE, default=DEFAULT_TRANSCRIPT_STORAGE): bool,
        vol.Optional(CONF_TRANSCRIPT_RETENTION_DAYS, default=DEFAULT_TRANSCRIPT_RETENTION_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=365)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Test Gemini API key using our REST client
    try:
        from .gemini_client import GeminiClient
        client = GeminiClient(data[CONF_GEMINI_API_KEY], hass)
        
        # Test connection
        is_valid = await client.test_connection()
        if not is_valid:
            raise InvalidAuth("Invalid Gemini API key")
        
        # Clean up client
        await client.close()
        
    except ImportError as err:
        _LOGGER.error("Error importing Gemini client: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.error("Error validating Gemini API key: %s", err)
        raise CannotConnect from err

    # Test STT API key if provided
    stt_api_key = data.get(CONF_STT_API_KEY) or data[CONF_GEMINI_API_KEY]
    if data.get(CONF_STT_PROVIDER) == "google_cloud":
        try:
            from google.cloud import speech
            client = speech.SpeechClient()
            # Simple validation - list recognition config
            client.list_phrase_sets(parent="projects/test/locations/global")
        except Exception as err:
            _LOGGER.warning("STT API key validation failed: %s", err)

    # Test TTS API key if provided
    tts_api_key = data.get(CONF_TTS_API_KEY) or data[CONF_GEMINI_API_KEY]
    if data.get(CONF_TTS_PROVIDER) == "google_cloud":
        try:
            from google.cloud import texttospeech
            client = texttospeech.TextToSpeechClient()
            # Simple validation - list voices
            voices = client.list_voices()
            if not voices.voices:
                raise InvalidAuth("Invalid TTS API key")
        except Exception as err:
            _LOGGER.warning("TTS API key validation failed: %s", err)

    return {"title": "Voice Assistant Gemini"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Voice Assistant Gemini."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth.""" 