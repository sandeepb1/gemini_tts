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
from .gemini_client import GeminiClient, GeminiAPIError

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

    async def _get_gemini_client(self):
        """Get Gemini API client."""
        if self._client is None:
            try:
                self._client = GeminiClient(self.api_key, self.hass)
                # Test the connection
                if not await self._client.test_connection():
                    raise RuntimeError("Failed to connect to Gemini API")
            except Exception as err:
                _LOGGER.error("Error initializing Gemini client: %s", err)
                raise RuntimeError(f"Failed to initialize Gemini client: {err}") from err
        
        return self._client

    async def _validate_audio(self, audio_bytes: bytes) -> bytes:
        """Validate and convert audio format if needed."""
        try:
            # Check if audio starts with RIFF header (WAV format)
            if audio_bytes.startswith(b'RIFF'):
                # It's a WAV file, we can parse it
                with io.BytesIO(audio_bytes) as audio_io:
                    with wave.open(audio_io, 'rb') as wav_file:
                        channels = wav_file.getnchannels()
                        sample_rate = wav_file.getframerate()
                        sample_width = wav_file.getsampwidth()
                        
                        _LOGGER.debug(
                            "WAV audio format: channels=%d, sample_rate=%d, sample_width=%d",
                            channels, sample_rate, sample_width
                        )
            else:
                # Not a WAV file, but that's okay for Gemini API
                _LOGGER.debug("Audio format: Non-WAV format detected, size=%d bytes", len(audio_bytes))
            
            # For Gemini API, we can accept various formats
            # Just return the original audio
            return audio_bytes
        
        except Exception as err:
            _LOGGER.debug("Audio validation error: %s", err)
            # If validation fails, that's fine for Gemini API
            return audio_bytes

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio to text."""
        try:
            # Validate audio format
            audio_bytes = await self._validate_audio(audio_bytes)
            
            if self.provider == "google_cloud" or self.provider == "gemini":
                return await self._transcribe_gemini(audio_bytes)
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

    async def _transcribe_gemini(self, audio_bytes: bytes) -> str:
        """Transcribe using Gemini Live API."""
        try:
            # Validate audio data
            if not audio_bytes or len(audio_bytes) == 0:
                _LOGGER.error("Empty audio data provided for transcription")
                raise RuntimeError("Empty audio data provided")
            
            # Check if audio data is too large (20MB limit for inline data)
            if len(audio_bytes) > 20 * 1024 * 1024:
                _LOGGER.error(f"Audio data too large: {len(audio_bytes)} bytes (max 20MB)")
                raise RuntimeError("Audio data exceeds 20MB limit")
            
            client = await self._get_gemini_client()
            
            _LOGGER.debug(f"Transcribing audio with Gemini Live API, size: {len(audio_bytes)} bytes")
            
            # Use the new Live API transcription method
            result = await client.transcribe_audio(audio_bytes, self.language)
            
            if not result:
                raise RuntimeError("Empty transcription result")
            
            _LOGGER.debug(f"Gemini Live API transcription successful: {result}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Gemini Live API transcription error: {e}")
            raise RuntimeError(f"Audio transcription failed: {e}")

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
            if self.provider == "google_cloud" or self.provider == "gemini":
                client = await self._get_gemini_client()
                return await client.test_connection()
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