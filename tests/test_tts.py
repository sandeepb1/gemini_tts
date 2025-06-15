"""Test the Voice Assistant Gemini TTS client."""
import pytest
from unittest.mock import Mock, patch

from custom_components.voice_assistant_gemini.tts import TTSClient, Voice


@pytest.mark.asyncio
async def test_tts_google_cloud_success(mock_hass, mock_google_tts):
    """Test successful Google Cloud TTS synthesis."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    audio_bytes = await client.synthesize("Hello world", ssml=False)
    
    assert audio_bytes == b"fake_audio_data"
    mock_google_tts.assert_called_once()


@pytest.mark.asyncio
async def test_tts_google_cloud_with_ssml(mock_hass, mock_google_tts):
    """Test Google Cloud TTS with SSML input."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    audio_bytes = await client.synthesize(
        "<speak>Hello <break time='1s'/> world</speak>", 
        ssml=True
    )
    
    assert audio_bytes == b"fake_audio_data"


@pytest.mark.asyncio
async def test_tts_google_cloud_with_voice_settings(mock_hass, mock_google_tts):
    """Test Google Cloud TTS with voice settings."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    audio_bytes = await client.synthesize(
        "Hello world",
        voice="en-US-Standard-A",
        speaking_rate=1.5,
        pitch=5.0,
        volume_gain_db=2.0,
        ssml=False
    )
    
    assert audio_bytes == b"fake_audio_data"


@pytest.mark.asyncio
async def test_tts_amazon_polly_success(mock_hass):
    """Test successful Amazon Polly TTS synthesis."""
    with patch("boto3.client") as mock_boto_client:
        mock_response = {
            "AudioStream": Mock()
        }
        mock_response["AudioStream"].read.return_value = b"polly_audio_data"
        mock_boto_client.return_value.synthesize_speech.return_value = mock_response
        
        client = TTSClient(mock_hass, "test_api_key", "en-US", "amazon_polly")
        audio_bytes = await client.synthesize("Hello world")
        
        assert audio_bytes == b"polly_audio_data"


@pytest.mark.asyncio
async def test_tts_azure_success(mock_hass):
    """Test successful Azure TTS synthesis."""
    with patch("azure.cognitiveservices.speech.SpeechConfig") as mock_config, \
         patch("azure.cognitiveservices.speech.SpeechSynthesizer") as mock_synthesizer:
        
        mock_result = Mock()
        mock_result.reason = Mock()
        mock_result.reason.__class__.__name__ = "SynthesizingAudioCompleted"
        mock_result.audio_data = b"azure_audio_data"
        
        mock_synthesizer.return_value.speak_ssml_async.return_value.get.return_value = mock_result
        
        # Mock the enum comparison
        with patch("azure.cognitiveservices.speech.ResultReason") as mock_reason:
            mock_reason.SynthesizingAudioCompleted = mock_result.reason
            
            client = TTSClient(mock_hass, "test_api_key", "en-US", "azure_tts")
            audio_bytes = await client.synthesize("Hello world")
            
            assert audio_bytes == b"azure_audio_data"


@pytest.mark.asyncio
async def test_tts_list_voices_google_cloud(mock_hass, mock_google_tts):
    """Test listing voices with Google Cloud TTS."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    voices = await client.list_voices()
    
    assert len(voices) == 1
    assert voices[0].name == "en-US-Standard-A"
    assert voices[0].language == "en-US"
    assert voices[0].gender == "female"


@pytest.mark.asyncio
async def test_tts_list_voices_amazon_polly(mock_hass):
    """Test listing voices with Amazon Polly."""
    with patch("boto3.client") as mock_boto_client:
        mock_response = {
            "Voices": [
                {
                    "Id": "Joanna",
                    "LanguageCode": "en-US",
                    "Gender": "Female",
                    "SupportedEngines": ["standard", "neural"]
                }
            ]
        }
        mock_boto_client.return_value.describe_voices.return_value = mock_response
        
        client = TTSClient(mock_hass, "test_api_key", "en-US", "amazon_polly")
        voices = await client.list_voices()
        
        assert len(voices) == 1
        assert voices[0].name == "Joanna"
        assert voices[0].neural is True


@pytest.mark.asyncio
async def test_tts_unsupported_provider(mock_hass):
    """Test TTS with unsupported provider."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "unsupported")
    
    with pytest.raises(RuntimeError):
        await client.synthesize("Hello world")


@pytest.mark.asyncio
async def test_tts_google_cloud_error(mock_hass):
    """Test Google Cloud TTS with error."""
    with patch("google.cloud.texttospeech.TextToSpeechClient") as mock_client:
        mock_client.return_value.synthesize_speech.side_effect = Exception("API Error")
        
        client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        with pytest.raises(RuntimeError):
            await client.synthesize("Hello world")


@pytest.mark.asyncio
async def test_tts_test_connection_success(mock_hass, mock_google_tts):
    """Test successful TTS connection test."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    result = await client.test_connection()
    
    assert result is True


@pytest.mark.asyncio
async def test_tts_test_connection_failure(mock_hass):
    """Test failed TTS connection test."""
    with patch("google.cloud.texttospeech.TextToSpeechClient", side_effect=Exception("Connection failed")):
        client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        result = await client.test_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_tts_retry_mechanism(mock_hass):
    """Test TTS retry mechanism on failures."""
    with patch("google.cloud.texttospeech.TextToSpeechClient") as mock_client:
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.audio_content = b"retry_success"
        
        mock_client.return_value.synthesize_speech.side_effect = [
            Exception("Temporary error"),
            mock_response
        ]
        
        client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
        
        with patch("asyncio.sleep"):  # Speed up test
            audio_bytes = await client.synthesize("Hello world")
        
        assert audio_bytes == b"retry_success"
        assert mock_client.return_value.synthesize_speech.call_count == 2


@pytest.mark.asyncio
async def test_tts_voices_cache(mock_hass, mock_google_tts):
    """Test that voices are cached properly."""
    client = TTSClient(mock_hass, "test_api_key", "en-US", "google_cloud")
    
    # First call
    voices1 = await client.list_voices()
    # Second call should use cache
    voices2 = await client.list_voices()
    
    assert voices1 == voices2
    # Should only call the API once due to caching
    assert mock_google_tts.return_value.list_voices.call_count == 1 