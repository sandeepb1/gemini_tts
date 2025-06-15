"""Test the Voice Assistant Gemini config flow."""
import pytest
from unittest.mock import patch, Mock

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResultType

from custom_components.voice_assistant_gemini.config_flow import ConfigFlow
from custom_components.voice_assistant_gemini.const import DOMAIN, CONF_GEMINI_API_KEY


async def test_form_user_success(hass, mock_gemini):
    """Test successful user configuration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.voice_assistant_gemini.config_flow.validate_input",
        return_value={"title": "Voice Assistant Gemini"},
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_GEMINI_API_KEY: "test_api_key",
                "default_language": "en-US",
                "stt_provider": "google_cloud",
                "tts_provider": "google_cloud",
                "speaking_rate": 1.0,
                "pitch": 0.0,
                "volume_gain_db": 0.0,
                "ssml": False,
                "gemini_model": "gemini-pro",
                "temperature": 0.7,
                "max_tokens": 2048,
                "logging_level": "INFO",
                "enable_transcript_storage": True,
                "transcript_retention_days": 30,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Voice Assistant Gemini"
    assert result2["data"][CONF_GEMINI_API_KEY] == "test_api_key"


async def test_form_invalid_auth(hass):
    """Test invalid authentication."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.voice_assistant_gemini.config_flow.validate_input",
        side_effect=Exception("Invalid API key"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_GEMINI_API_KEY: "invalid_key",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect(hass):
    """Test connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.voice_assistant_gemini.config_flow.validate_input",
        side_effect=ConnectionError("Cannot connect"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_GEMINI_API_KEY: "test_key",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_validate_input_success(hass, mock_gemini):
    """Test successful input validation."""
    from custom_components.voice_assistant_gemini.config_flow import validate_input

    data = {
        CONF_GEMINI_API_KEY: "test_api_key",
        "gemini_model": "gemini-pro",
    }

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as mock_model:
        
        mock_model.return_value.generate_content.return_value.text = "Test response"
        
        result = await validate_input(hass, data)
        assert result["title"] == "Voice Assistant Gemini"


async def test_validate_input_invalid_key(hass):
    """Test validation with invalid API key."""
    from custom_components.voice_assistant_gemini.config_flow import validate_input, InvalidAuth

    data = {
        CONF_GEMINI_API_KEY: "invalid_key",
        "gemini_model": "gemini-pro",
    }

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as mock_model:
        
        mock_model.return_value.generate_content.side_effect = Exception("Invalid API key")
        
        with pytest.raises(Exception):
            await validate_input(hass, data) 