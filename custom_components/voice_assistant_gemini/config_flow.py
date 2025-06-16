"""Config flow for Voice Assistant Gemini integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.http import StaticPathConfig

from .const import (
    CONF_DEFAULT_LANGUAGE,
    CONF_DEFAULT_VOICE,
    CONF_ENABLE_TRANSCRIPT_STORAGE,
    CONF_GEMINI_API_KEY,
    CONF_GEMINI_MODEL,
    CONF_CONVERSATION_MODEL,
    CONF_TTS_MODEL,
    CONF_STT_MODEL,
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
    DEFAULT_CONVERSATION_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_STT_MODEL,
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
    GEMINI_VOICES,
    GEMINI_VOICE_DESCRIPTIONS,
    CONVERSATION_MODELS,
    TTS_MODELS,
    STT_MODELS,
    LOGGING_LEVELS,
    STT_PROVIDERS,
    SUPPORTED_LANGUAGES,
    TTS_PROVIDERS,
)

_LOGGER = logging.getLogger(__name__)

# Step 1: Basic API Configuration
STEP_API_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GEMINI_API_KEY): str,
        vol.Optional(CONF_STT_API_KEY, default=""): str,
        vol.Optional(CONF_TTS_API_KEY, default=""): str,
    }
)

# Step 2: Service Configuration
STEP_SERVICES_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEFAULT_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        vol.Optional(CONF_STT_PROVIDER, default=DEFAULT_STT_PROVIDER): vol.In(STT_PROVIDERS),
        vol.Optional(CONF_TTS_PROVIDER, default=DEFAULT_TTS_PROVIDER): vol.In(TTS_PROVIDERS),
        vol.Optional(CONF_CONVERSATION_MODEL, default=DEFAULT_CONVERSATION_MODEL): vol.In(list(CONVERSATION_MODELS.keys())),
        vol.Optional(CONF_TTS_MODEL, default=DEFAULT_TTS_MODEL): vol.In(list(TTS_MODELS.keys())),
        vol.Optional(CONF_STT_MODEL, default=DEFAULT_STT_MODEL): vol.In(list(STT_MODELS.keys())),
    }
)

# Step 3: Voice and Audio Configuration
STEP_VOICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEFAULT_VOICE, default="Kore"): vol.In(GEMINI_VOICES),
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
    }
)

# Step 4: Advanced Configuration
STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
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

# Legacy single-step schema for backwards compatibility
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GEMINI_API_KEY): str,
        vol.Optional(CONF_STT_API_KEY, default=""): str,
        vol.Optional(CONF_TTS_API_KEY, default=""): str,
        vol.Optional(CONF_DEFAULT_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        vol.Optional(CONF_STT_PROVIDER, default=DEFAULT_STT_PROVIDER): vol.In(STT_PROVIDERS),
        vol.Optional(CONF_TTS_PROVIDER, default=DEFAULT_TTS_PROVIDER): vol.In(TTS_PROVIDERS),
        vol.Optional(CONF_DEFAULT_VOICE, default="Kore"): vol.In(GEMINI_VOICES),
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
        vol.Optional(CONF_CONVERSATION_MODEL, default=DEFAULT_CONVERSATION_MODEL): vol.In(list(CONVERSATION_MODELS.keys())),
        vol.Optional(CONF_TTS_MODEL, default=DEFAULT_TTS_MODEL): vol.In(list(TTS_MODELS.keys())),
        vol.Optional(CONF_STT_MODEL, default=DEFAULT_STT_MODEL): vol.In(list(STT_MODELS.keys())),
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
    
    # Test Gemini API key using direct HTTP request
    try:
        import json
        
        # Test the API key with a simple request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={data[CONF_GEMINI_API_KEY]}"
        payload = {
            "contents": [{
                "parts": [{"text": "Hello"}]
            }],
            "generationConfig": {
                "maxOutputTokens": 10
            }
        }
        
        session = async_get_clientsession(hass)
        
        # Set a timeout for the validation request
        timeout = 10  # 10 seconds timeout
        
        async with session.post(
            url, 
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 400:
                # Check if it's an API key issue
                error_text = await response.text()
                if "API_KEY_INVALID" in error_text or "invalid" in error_text.lower():
                    raise InvalidAuth("Invalid Gemini API key")
                else:
                    _LOGGER.warning(f"Gemini API validation warning: {error_text}")
                    # Continue anyway - might be a temporary issue
            elif response.status == 401 or response.status == 403:
                raise InvalidAuth("Invalid Gemini API key")
            elif response.status != 200:
                error_text = await response.text()
                _LOGGER.warning(f"Gemini API validation returned {response.status}: {error_text}")
                # Don't fail the config for non-auth errors - might be temporary
            else:
                # Check if we got a valid response
                try:
                    result = await response.json()
                    if "candidates" not in result and "error" in result:
                        error_info = result.get("error", {})
                        if error_info.get("code") in [401, 403]:
                            raise InvalidAuth("Invalid Gemini API key")
                        else:
                            _LOGGER.warning(f"Gemini API validation warning: {error_info}")
                except json.JSONDecodeError:
                    _LOGGER.warning("Could not parse Gemini API response during validation")
        
    except InvalidAuth:
        # Re-raise auth errors
        raise
    except Exception as err:
        _LOGGER.warning("Could not validate Gemini API key during config: %s", err)
        # Don't fail the config for network/temporary issues
        # The API key will be validated when actually used

    # Skip STT/TTS validation during config flow to avoid blocking calls
    # These will be validated when the integration is actually used
    _LOGGER.info("Skipping STT/TTS validation during config flow - will validate on first use")

    return {"title": "Voice Assistant Gemini"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Voice Assistant Gemini."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._config_data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose setup type."""
        if user_input is not None:
            setup_type = user_input.get("setup_type", "guided")
            if setup_type == "guided":
                return await self.async_step_api()
            else:
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("setup_type", default="guided"): vol.In({
                    "guided": "Guided Setup (Recommended)",
                    "advanced": "Advanced Setup (All Options)"
                })
            }),
            description_placeholders={
                "setup_info": "Choose your preferred setup method:\n\n"
                             "• Guided Setup: Step-by-step configuration with recommendations\n"
                             "• Advanced Setup: All options on one page"
            }
        )

    async def async_step_api(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle API configuration step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate API key
                await validate_input(self.hass, user_input)
                self._config_data.update(user_input)
                return await self.async_step_services()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="api",
            data_schema=STEP_API_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "api_info": "Configure your API keys:\n\n"
                           "• Gemini API Key: Required for all services\n"
                           "• STT API Key: Optional, uses Gemini key if empty\n"
                           "• TTS API Key: Optional, uses Gemini key if empty"
            }
        )

    async def async_step_services(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle service configuration step."""
        if user_input is not None:
            self._config_data.update(user_input)
            return await self.async_step_voice()

        # Create dynamic schema with model descriptions
        services_schema_dict = {}
        
        # Language selection
        services_schema_dict[vol.Optional(CONF_DEFAULT_LANGUAGE, default=DEFAULT_LANGUAGE)] = vol.In(SUPPORTED_LANGUAGES)
        
        # Provider selections
        services_schema_dict[vol.Optional(CONF_STT_PROVIDER, default=DEFAULT_STT_PROVIDER)] = vol.In(STT_PROVIDERS)
        services_schema_dict[vol.Optional(CONF_TTS_PROVIDER, default=DEFAULT_TTS_PROVIDER)] = vol.In(TTS_PROVIDERS)
        
        # Model selections with descriptions
        services_schema_dict[vol.Optional(CONF_CONVERSATION_MODEL, default=DEFAULT_CONVERSATION_MODEL)] = vol.In(list(CONVERSATION_MODELS.keys()))
        services_schema_dict[vol.Optional(CONF_TTS_MODEL, default=DEFAULT_TTS_MODEL)] = vol.In(list(TTS_MODELS.keys()))
        services_schema_dict[vol.Optional(CONF_STT_MODEL, default=DEFAULT_STT_MODEL)] = vol.In(list(STT_MODELS.keys()))

        return self.async_show_form(
            step_id="services",
            data_schema=vol.Schema(services_schema_dict),
            description_placeholders={
                "services_info": "Configure AI models and providers:\n\n"
                               f"Conversation Models:\n{self._format_model_descriptions(CONVERSATION_MODELS)}\n\n"
                               f"TTS Models:\n{self._format_model_descriptions(TTS_MODELS)}\n\n"
                               f"STT Models:\n{self._format_model_descriptions(STT_MODELS)}"
            }
        )

    async def async_step_voice(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle voice and audio configuration step."""
        if user_input is not None:
            self._config_data.update(user_input)
            return await self.async_step_final()

        # Register the voice selector script with Home Assistant
        import os
        from homeassistant.components.http.static import StaticResource
        from homeassistant.const import CONF_FILENAME
        
        # Register the voice selector script with Home Assistant
        www_path = os.path.join(os.path.dirname(__file__), "www")
        voice_selector_path = os.path.join(www_path, "voice-simple-selector.js")
        
        # Make sure the www directory is accessible
        if self.hass.http and os.path.exists(voice_selector_path):
            static_path_config = StaticPathConfig(
                f"/{DOMAIN}/voice-simple-selector.js",
                voice_selector_path,
                True
            )
            await self.hass.http.async_register_static_paths([static_path_config])

        return self.async_show_form(
            step_id="voice",
            data_schema=STEP_VOICE_DATA_SCHEMA,
            description_placeholders={
                "voice_info": f"""Configure voice and audio settings:

🎤 **Voice Selection with Descriptions**
Choose from 30 unique Gemini voices, each with distinct personality traits.
The interactive selector below shows descriptions for each voice to help you find the perfect match for your assistant.

**Features:**
• 🎭 30 unique voices with personality descriptions
• 🔍 Search voices by name or characteristics  
• ✨ Visual selection with live preview
• 📱 Responsive design for all devices

**Audio Settings:**
• Speaking Rate: 0.25 (very slow) to 4.0 (very fast)
• Pitch: -20.0 (lower) to 20.0 (higher)  
• Volume Gain: -96.0 (quieter) to 16.0 (louder)

<script src="/{DOMAIN}/voice-simple-selector.js"></script>
<voice-simple-selector></voice-simple-selector>

**Voice Preview:**
After completing setup, you can test voices using:
• The Voice Assistant dashboard card
• Home Assistant's TTS service
• Developer Tools > Services > `voice_assistant_gemini.tts`

**Popular Voice Recommendations:**
• **Kore** - Firm and confident (great for commands)
• **Puck** - Upbeat and energetic (perfect for notifications)  
• **Zephyr** - Bright and clear (excellent for announcements)
• **Charon** - Informative and professional (ideal for news/weather)
• **Leda** - Youthful and friendly (wonderful for casual conversations)"""
            }
        )

    async def async_step_final(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle final configuration step."""
        if user_input is not None:
            self._config_data.update(user_input)
            return self.async_create_entry(title="Voice Assistant Gemini", data=self._config_data)

        return self.async_show_form(
            step_id="final",
            data_schema=STEP_ADVANCED_DATA_SCHEMA,
            description_placeholders={
                "final_info": "Configure advanced settings:\n\n"
                             "• Temperature: Controls response creativity (0.0-1.0)\n"
                             "• Max Tokens: Maximum response length (1-8192)\n"
                             "• Transcript Storage: Save conversation history\n"
                             "• Retention Days: How long to keep transcripts"
            }
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced single-step configuration."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="advanced",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "advanced_info": "Advanced configuration with all options:\n\n"
                               f"Model Recommendations:\n{self._format_all_model_descriptions()}\n\n"
                               f"Voice Options:\n{self._format_voice_descriptions()}"
            }
        )

    def _format_model_descriptions(self, models_dict: dict) -> str:
        """Format model descriptions for display."""
        return "\n".join([f"• {desc}" for desc in models_dict.values()])

    def _format_all_model_descriptions(self) -> str:
        """Format all model descriptions."""
        return (
            f"Conversation: {self._format_model_descriptions(CONVERSATION_MODELS)}\n"
            f"TTS: {self._format_model_descriptions(TTS_MODELS)}\n"
            f"STT: {self._format_model_descriptions(STT_MODELS)}"
        )

    def _format_voice_descriptions(self) -> str:
        """Format voice descriptions for display."""
        # Show first 10 voices to avoid overwhelming the UI
        voices_to_show = list(GEMINI_VOICE_DESCRIPTIONS.items())[:10]
        formatted = "\n".join([f"• {desc}" for _, desc in voices_to_show])
        if len(GEMINI_VOICE_DESCRIPTIONS) > 10:
            formatted += f"\n• ... and {len(GEMINI_VOICE_DESCRIPTIONS) - 10} more voices available"
        return formatted

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Voice Assistant Gemini."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        current_data = self._config_entry.data
        current_options = self._config_entry.options

        # Create schema with current values as defaults
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEFAULT_LANGUAGE,
                    default=current_options.get(CONF_DEFAULT_LANGUAGE, current_data.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
                ): vol.In(SUPPORTED_LANGUAGES),
                vol.Optional(
                    CONF_STT_PROVIDER,
                    default=current_options.get(CONF_STT_PROVIDER, current_data.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER))
                ): vol.In(STT_PROVIDERS),
                vol.Optional(
                    CONF_TTS_PROVIDER,
                    default=current_options.get(CONF_TTS_PROVIDER, current_data.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER))
                ): vol.In(TTS_PROVIDERS),
                vol.Optional(
                    CONF_CONVERSATION_MODEL,
                    default=current_options.get(CONF_CONVERSATION_MODEL, current_data.get(CONF_CONVERSATION_MODEL, current_data.get(CONF_GEMINI_MODEL, DEFAULT_CONVERSATION_MODEL)))
                ): vol.In(list(CONVERSATION_MODELS.keys())),
                vol.Optional(
                    CONF_TTS_MODEL,
                    default=current_options.get(CONF_TTS_MODEL, current_data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL))
                ): vol.In(list(TTS_MODELS.keys())),
                vol.Optional(
                    CONF_STT_MODEL,
                    default=current_options.get(CONF_STT_MODEL, current_data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL))
                ): vol.In(list(STT_MODELS.keys())),
                vol.Optional(
                    CONF_DEFAULT_VOICE,
                    default=current_options.get(CONF_DEFAULT_VOICE, current_data.get(CONF_DEFAULT_VOICE, "Kore"))
                ): vol.In(GEMINI_VOICES),
                vol.Optional(
                    CONF_SPEAKING_RATE,
                    default=current_options.get(CONF_SPEAKING_RATE, current_data.get(CONF_SPEAKING_RATE, DEFAULT_SPEAKING_RATE))
                ): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=4.0)),
                vol.Optional(
                    CONF_PITCH,
                    default=current_options.get(CONF_PITCH, current_data.get(CONF_PITCH, DEFAULT_PITCH))
                ): vol.All(vol.Coerce(float), vol.Range(min=-20.0, max=20.0)),
                vol.Optional(
                    CONF_VOLUME_GAIN_DB,
                    default=current_options.get(CONF_VOLUME_GAIN_DB, current_data.get(CONF_VOLUME_GAIN_DB, DEFAULT_VOLUME_GAIN_DB))
                ): vol.All(vol.Coerce(float), vol.Range(min=-96.0, max=16.0)),
                vol.Optional(
                    CONF_SSML,
                    default=current_options.get(CONF_SSML, current_data.get(CONF_SSML, DEFAULT_SSML))
                ): bool,
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=current_options.get(CONF_TEMPERATURE, current_data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    default=current_options.get(CONF_MAX_TOKENS, current_data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=8192)),
                vol.Optional(
                    CONF_LOGGING_LEVEL,
                    default=current_options.get(CONF_LOGGING_LEVEL, current_data.get(CONF_LOGGING_LEVEL, DEFAULT_LOGGING_LEVEL))
                ): vol.In(LOGGING_LEVELS),
                vol.Optional(
                    CONF_ENABLE_TRANSCRIPT_STORAGE,
                    default=current_options.get(CONF_ENABLE_TRANSCRIPT_STORAGE, current_data.get(CONF_ENABLE_TRANSCRIPT_STORAGE, DEFAULT_TRANSCRIPT_STORAGE))
                ): bool,
                vol.Optional(
                    CONF_TRANSCRIPT_RETENTION_DAYS,
                    default=current_options.get(CONF_TRANSCRIPT_RETENTION_DAYS, current_data.get(CONF_TRANSCRIPT_RETENTION_DAYS, DEFAULT_TRANSCRIPT_RETENTION_DAYS))
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "options_info": "Modify your Voice Assistant Gemini configuration:\n\n"
                               f"Model Recommendations:\n"
                               f"• Conversation: {CONVERSATION_MODELS}\n"
                               f"• TTS: {TTS_MODELS}\n"
                               f"• STT: {STT_MODELS}\n\n"
                               f"Voice Options: {len(GEMINI_VOICES)} voices available\n"
                               "Changes will take effect after saving."
            }
        ) 