"""Speech-to-Text client for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.stt import SpeechToTextEntity, SpeechMetadata, SpeechResult, SpeechResultState
from homeassistant.helpers.entity import EntityCategory

from .const import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    AUDIO_SAMPLE_WIDTH,
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class STTClient:
    """Speech-to-Text client."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        language: str = "en-US",
        provider: str = "google_cloud",
    ) -> None:
        """Initialize the STT client."""
        self.hass = hass
        self.api_key = api_key
        self.language = language
        self.provider = provider
        self._client = None
        self._retry_count = 0

    async def _get_google_client(self):
        """Get Google Cloud Speech client."""
        if self._client is None:
            try:
                from google.cloud import speech
                
                # Initialize client with credentials in executor to avoid blocking
                def _create_client():
                    return speech.SpeechClient()
                
                self._client = await self.hass.async_add_executor_job(_create_client)
            except ImportError as err:
                _LOGGER.error("Google Cloud Speech library not installed: %s", err)
                raise RuntimeError("Google Cloud Speech library not available") from err
            except Exception as err:
                _LOGGER.error("Error initializing Google Cloud Speech client: %s", err)
                raise RuntimeError(f"Failed to initialize Speech client: {err}") from err
        
        return self._client

    async def _validate_audio(self, audio_bytes: bytes) -> bytes:
        """Validate and convert audio format if needed."""
        try:
            # Check if audio is WAV format
            with io.BytesIO(audio_bytes) as audio_io:
                with wave.open(audio_io, 'rb') as wav_file:
                    channels = wav_file.getnchannels()
                    sample_rate = wav_file.getframerate()
                    sample_width = wav_file.getsampwidth()
                    
                    _LOGGER.debug(
                        "Audio format: channels=%d, sample_rate=%d, sample_width=%d",
                        channels, sample_rate, sample_width
                    )
                    
                    # Check if conversion is needed
                    if (channels != AUDIO_CHANNELS or 
                        sample_rate != AUDIO_SAMPLE_RATE or 
                        sample_width != AUDIO_SAMPLE_WIDTH):
                        
                        _LOGGER.info(
                            "Converting audio format from %dx%d@%d to %dx%d@%d",
                            channels, sample_rate, sample_width,
                            AUDIO_CHANNELS, AUDIO_SAMPLE_RATE, AUDIO_SAMPLE_WIDTH
                        )
                        
                        # TODO: Add audio conversion logic here
                        # For now, we'll use the original audio
                        return audio_bytes
                    
                    return audio_bytes
        
        except Exception as err:
            _LOGGER.warning("Audio validation failed: %s", err)
            return audio_bytes

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio to text."""
        try:
            # Validate audio format
            audio_bytes = await self._validate_audio(audio_bytes)
            
            if self.provider == "google_cloud":
                return await self._transcribe_google_cloud(audio_bytes)
            elif self.provider == "vosk":
                return await self._transcribe_vosk(audio_bytes)
            else:
                raise ValueError(f"Unsupported STT provider: {self.provider}")
        
        except Exception as err:
            self._retry_count += 1
            if self._retry_count < RETRY_ATTEMPTS:
                backoff_time = RETRY_BACKOFF_FACTOR ** self._retry_count
                _LOGGER.warning(
                    "STT transcription failed (attempt %d): %s. Retrying in %d seconds",
                    self._retry_count, err, backoff_time
                )
                await asyncio.sleep(backoff_time)
                return await self.transcribe(audio_bytes)
            
            _LOGGER.error("STT transcription failed after %d attempts: %s", RETRY_ATTEMPTS, err)
            raise RuntimeError(f"Speech transcription failed: {err}") from err

    async def _transcribe_google_cloud(self, audio_bytes: bytes) -> str:
        """Transcribe using Google Cloud Speech-to-Text."""
        try:
            from google.cloud import speech
            
            client = await self._get_google_client()
            
            # Configure audio and recognition settings
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=AUDIO_SAMPLE_RATE,
                language_code=self.language,
                audio_channel_count=AUDIO_CHANNELS,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=False,
            )
            
            # Handle large audio files with streaming
            if len(audio_bytes) > 1024 * 1024:  # 1MB threshold
                return await self._transcribe_streaming(client, audio_bytes, config)
            
            # Use synchronous recognition for smaller files
            def _sync_recognize():
                response = client.recognize(config=config, audio=audio)
                if response.results:
                    transcript = ""
                    for result in response.results:
                        transcript += result.alternatives[0].transcript + " "
                    return transcript.strip()
                return ""
            
            transcript = await self.hass.async_add_executor_job(_sync_recognize)
            
            if not transcript:
                _LOGGER.warning("No speech detected in audio")
                return ""
            
            _LOGGER.debug("Transcription result: %s", transcript)
            self._retry_count = 0  # Reset retry count on success
            return transcript
        
        except Exception as err:
            _LOGGER.error("Google Cloud Speech transcription error: %s", err)
            raise

    async def _transcribe_streaming(self, client, audio_bytes: bytes, config) -> str:
        """Handle streaming transcription for large audio files."""
        try:
            from google.cloud import speech
            
            def _streaming_recognize():
                # Create streaming request generator
                def request_generator():
                    yield speech.StreamingRecognizeRequest(
                        streaming_config=speech.StreamingRecognitionConfig(
                            config=config,
                            interim_results=False,
                        )
                    )
                    
                    # Send audio in chunks
                    chunk_size = 1024 * 64  # 64KB chunks
                    for i in range(0, len(audio_bytes), chunk_size):
                        chunk = audio_bytes[i:i + chunk_size]
                        yield speech.StreamingRecognizeRequest(audio_content=chunk)
                
                # Process streaming response
                responses = client.streaming_recognize(request_generator())
                transcript = ""
                
                for response in responses:
                    for result in response.results:
                        if result.is_final:
                            transcript += result.alternatives[0].transcript + " "
                
                return transcript.strip()
            
            return await self.hass.async_add_executor_job(_streaming_recognize)
        
        except Exception as err:
            _LOGGER.error("Streaming transcription error: %s", err)
            raise

    async def _transcribe_vosk(self, audio_bytes: bytes) -> str:
        """Transcribe using Vosk (offline)."""
        try:
            import json
            import vosk
            
            # Initialize Vosk model
            if not hasattr(self, '_vosk_model'):
                model_path = f"/usr/share/vosk-model-{self.language.lower()}"
                if not os.path.exists(model_path):
                    model_path = f"/usr/share/vosk-model-en-us"  # Fallback
                
                self._vosk_model = vosk.Model(model_path)
            
            # Create recognizer
            rec = vosk.KaldiRecognizer(self._vosk_model, AUDIO_SAMPLE_RATE)
            
            def _vosk_recognize():
                # Process audio
                rec.AcceptWaveform(audio_bytes)
                result = json.loads(rec.FinalResult())
                return result.get("text", "")
            
            transcript = await self.hass.async_add_executor_job(_vosk_recognize)
            
            _LOGGER.debug("Vosk transcription result: %s", transcript)
            self._retry_count = 0  # Reset retry count on success
            return transcript
        
        except ImportError as err:
            _LOGGER.error("Vosk library not installed: %s", err)
            raise RuntimeError("Vosk library not available") from err
        except Exception as err:
            _LOGGER.error("Vosk transcription error: %s", err)
            raise

    async def test_connection(self) -> bool:
        """Test the STT connection."""
        try:
            if self.provider == "google_cloud":
                client = await self._get_google_client()
                # Simple test - list recognition config
                def _test():
                    return True  # Just test client initialization
                
                await self.hass.async_add_executor_job(_test)
                return True
            elif self.provider == "vosk":
                # Test Vosk availability
                import vosk
                return True
            
            return False
        except Exception as err:
            _LOGGER.error("STT connection test failed: %s", err)
            return False 


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up STT provider."""
    # Get values from options first, then config data
    options = config_entry.options
    data = config_entry.data
    
    # Create STT provider
    api_key = options.get("stt_api_key") or data.get("stt_api_key") or options.get("gemini_api_key") or data.get("gemini_api_key")
    language = options.get("default_language") or data.get("default_language", "en-US")
    provider = options.get("stt_provider") or data.get("stt_provider", "google_cloud")
    model = options.get("stt_model") or data.get("stt_model", "gemini-2.0-flash")
    
    stt_provider = GeminiSTTProvider(hass, config_entry, api_key, language, provider, model)
    
    async_add_entities([stt_provider])
    return True


class GeminiSTTProvider(SpeechToTextEntity):
    """Gemini STT provider for Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_key: str,
        language: str,
        provider: str,
        model: str,
    ) -> None:
        """Initialize the STT provider."""
        self.hass = hass
        self.config_entry = config_entry
        self._client = STTClient(hass, api_key, language, provider)
        self._attr_name = f"Gemini STT ({provider})"
        self._attr_unique_id = f"{config_entry.entry_id}_stt"
        self._attr_entity_category = EntityCategory.CONFIG
        self.model = model

    @property
    def name(self) -> str:
        """Return the name of the STT provider."""
        return self._attr_name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the STT provider."""
        return self._attr_unique_id

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return [
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR",
            "ru-RU", "ja-JP", "ko-KR", "zh-CN", "zh-TW", "ar-SA", "hi-IN"
        ]

    @property
    def supported_formats(self) -> list[str]:
        """Return list of supported formats."""
        return ["wav"]  # Focus on WAV format for assist pipeline compatibility

    @property
    def supported_codecs(self) -> list[str]:
        """Return list of supported codecs."""
        return ["pcm"]  # Focus on PCM codec for assist pipeline compatibility

    @property
    def supported_bit_rates(self) -> list[int]:
        """Return list of supported bit rates."""
        return [16]  # 16-bit audio depth

    @property
    def supported_channels(self) -> list[int]:
        """Return list of supported channels."""
        return [1]  # Mono audio for assist pipeline compatibility

    @property
    def supported_sample_rates(self) -> list[int]:
        """Return list of supported sample rates."""
        return [16000]  # 16kHz sample rate for assist pipeline compatibility

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream
    ) -> SpeechResult:
        """Process audio stream to text."""
        try:
            # Read audio data from stream
            audio_data = b""
            async for chunk in stream:
                audio_data += chunk
            
            if not audio_data:
                return SpeechResult(
                    text="",
                    result=SpeechResultState.ERROR,
                )
            
            # Transcribe audio
            transcript = await self._client.transcribe(audio_data)
            
            return SpeechResult(
                text=transcript,
                result=SpeechResultState.SUCCESS,
            )
        
        except Exception as err:
            _LOGGER.error("STT processing error: %s", err)
            return SpeechResult(
                text="",
                result=SpeechResultState.ERROR,
            ) 