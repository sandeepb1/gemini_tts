"""Test the Voice Assistant Gemini STT client."""
import pytest
from unittest.mock import Mock, patch, AsyncMock

from custom_components.voice_assistant_gemini.stt import STTClient


@pytest.mark.asyncio
async def test_stt_google_cloud_success(mock_hass, mock_google_stt, mock_audio_data):
    """Test successful Google Cloud STT transcription."""
    client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    transcript = await client.transcribe(mock_audio_data)
    
    assert transcript == "Hello world"
    mock_google_stt.assert_called_once()


@pytest.mark.asyncio
async def test_stt_google_cloud_empty_result(mock_hass, mock_audio_data):
    """Test Google Cloud STT with empty result."""
    with patch("google.cloud.speech.SpeechClient") as mock_client:
        mock_response = Mock()
        mock_response.results = []
        mock_client.return_value.recognize.return_value = mock_response
        
        client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        transcript = await client.transcribe(mock_audio_data)
        
        assert transcript == ""


@pytest.mark.asyncio
async def test_stt_google_cloud_error(mock_hass, mock_audio_data):
    """Test Google Cloud STT with error."""
    with patch("google.cloud.speech.SpeechClient") as mock_client:
        mock_client.return_value.recognize.side_effect = Exception("API Error")
        
        client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        with pytest.raises(RuntimeError):
            await client.transcribe(mock_audio_data)


@pytest.mark.asyncio
async def test_stt_vosk_success(mock_hass, mock_audio_data):
    """Test successful Vosk STT transcription."""
    with patch("vosk.Model") as mock_model, \
         patch("vosk.KaldiRecognizer") as mock_recognizer, \
         patch("json.loads") as mock_json, \
         patch("os.path.exists", return_value=True):
        
        mock_json.return_value = {"text": "hello world"}
        
        client = STTClient(mock_hass, "test_api_key", "en-US", "vosk")
        transcript = await client.transcribe(mock_audio_data)
        
        assert transcript == "hello world"


@pytest.mark.asyncio
async def test_stt_vosk_import_error(mock_hass, mock_audio_data):
    """Test Vosk STT with import error."""
    with patch("custom_components.voice_assistant_gemini.stt.vosk", side_effect=ImportError):
        client = STTClient(mock_hass, "test_api_key", "en-US", "vosk")
        
        with pytest.raises(RuntimeError, match="Vosk library not available"):
            await client.transcribe(mock_audio_data)


@pytest.mark.asyncio
async def test_stt_unsupported_provider(mock_hass, mock_audio_data):
    """Test STT with unsupported provider."""
    client = STTClient(mock_hass, "test_api_key", "en-US", "unsupported")
    
    with pytest.raises(RuntimeError):
        await client.transcribe(mock_audio_data)


@pytest.mark.asyncio
async def test_stt_streaming_large_audio(mock_hass):
    """Test STT with large audio file requiring streaming."""
    large_audio_data = b"x" * (1024 * 1024 + 1)  # 1MB + 1 byte
    
    with patch("google.cloud.speech.SpeechClient") as mock_client:
        # Mock streaming response
        mock_streaming_response = [Mock()]
        mock_streaming_response[0].results = [Mock()]
        mock_streaming_response[0].results[0].is_final = True
        mock_streaming_response[0].results[0].alternatives = [Mock()]
        mock_streaming_response[0].results[0].alternatives[0].transcript = "streaming result"
        
        mock_client.return_value.streaming_recognize.return_value = mock_streaming_response
        
        client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        transcript = await client.transcribe(large_audio_data)
        
        assert transcript == "streaming result"


@pytest.mark.asyncio
async def test_stt_test_connection_success(mock_hass, mock_google_stt):
    """Test successful STT connection test."""
    client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    result = await client.test_connection()
    
    assert result is True


@pytest.mark.asyncio
async def test_stt_test_connection_failure(mock_hass):
    """Test failed STT connection test."""
    with patch("google.cloud.speech.SpeechClient", side_effect=Exception("Connection failed")):
        client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        result = await client.test_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_stt_retry_mechanism(mock_hass, mock_audio_data):
    """Test STT retry mechanism on failures."""
    with patch("google.cloud.speech.SpeechClient") as mock_client:
        # First call fails, second succeeds
        mock_client.return_value.recognize.side_effect = [
            Exception("Temporary error"),
            Mock(results=[Mock(alternatives=[Mock(transcript="retry success")])])
        ]
        
        client = STTClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        with patch("asyncio.sleep"):  # Speed up test
            transcript = await client.transcribe(mock_audio_data)
        
        assert transcript == "retry success"
        assert mock_client.return_value.recognize.call_count == 2 