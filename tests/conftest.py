"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import Mock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.voice_assistant_gemini.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Mock a config entry."""
    return config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Voice Assistant Gemini",
        data={
            "gemini_api_key": "test_gemini_key",
            "stt_api_key": "",
            "tts_api_key": "",
            "default_language": "en-US",
            "stt_provider": "google_cloud",
            "tts_provider": "google_cloud",
            "default_voice": "",
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
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.config_entries = Mock()
    hass.config_entries.async_entries.return_value = []
    hass.services = Mock()
    hass.bus = Mock()
    hass.async_add_executor_job = Mock()
    return hass


@pytest.fixture
def mock_store():
    """Mock storage."""
    store = Mock(spec=Store)
    store.async_load.return_value = {"sessions": {}}
    store.async_save = Mock()
    return store


@pytest.fixture
def mock_google_stt():
    """Mock Google Cloud Speech client."""
    with patch("google.cloud.speech.SpeechClient") as mock_client:
        mock_response = Mock()
        mock_response.results = [Mock()]
        mock_response.results[0].alternatives = [Mock()]
        mock_response.results[0].alternatives[0].transcript = "Hello world"
        mock_client.return_value.recognize.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_google_tts():
    """Mock Google Cloud TTS client."""
    with patch("google.cloud.texttospeech.TextToSpeechClient") as mock_client:
        mock_response = Mock()
        mock_response.audio_content = b"fake_audio_data"
        mock_client.return_value.synthesize_speech.return_value = mock_response
        
        mock_voices_response = Mock()
        mock_voices_response.voices = [Mock()]
        mock_voices_response.voices[0].name = "en-US-Standard-A"
        mock_voices_response.voices[0].language_codes = ["en-US"]
        mock_voices_response.voices[0].ssml_gender.name = "FEMALE"
        mock_client.return_value.list_voices.return_value = mock_voices_response
        yield mock_client


@pytest.fixture
def mock_gemini():
    """Mock Google Gemini client."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_response = Mock()
        mock_response.text = "This is a test response from Gemini."
        mock_model.return_value.generate_content.return_value = mock_response
        yield mock_model


@pytest.fixture
def mock_audio_data():
    """Mock audio data."""
    return b"fake_audio_wav_data"


@pytest.fixture
def mock_base64_audio():
    """Mock base64 encoded audio."""
    import base64
    return base64.b64encode(b"fake_audio_wav_data").decode()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield 