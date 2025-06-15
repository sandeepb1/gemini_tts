"""Speech-to-Text client for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    AUDIO_SAMPLE_WIDTH,
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
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
                
                # Initialize client with credentials
                self._client = speech.SpeechClient()
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