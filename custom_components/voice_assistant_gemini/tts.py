"""Text-to-Speech client for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
)
from .gemini_client import GeminiClient, GeminiAPIError, GEMINI_VOICES

_LOGGER = logging.getLogger(__name__)


class Voice(NamedTuple):
    """Voice configuration."""
    name: str
    language: str
    gender: str
    neural: bool = False


class TTSClient:
    """Text-to-Speech client."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        language: str = "en-US",
        provider: str = "gemini_tts",
    ) -> None:
        """Initialize the TTS client."""
        self.hass = hass
        self.api_key = api_key
        self.language = language
        self.provider = provider
        self._client = None
        self._gemini_client = None
        self._retry_count = 0
        self._voices_cache = None
        self._voices_cache_time = None

    async def synthesize(
        self,
        text: str,
        voice: str = "",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        ssml: bool = False,
    ) -> bytes:
        """Synthesize text to speech."""
        try:
            if self.provider == "gemini_tts":
                return await self._synthesize_gemini_tts(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml
                )
            elif self.provider == "google_cloud":
                return await self._synthesize_google_cloud(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml
                )
            elif self.provider == "amazon_polly":
                return await self._synthesize_amazon_polly(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml
                )
            elif self.provider == "azure_tts":
                return await self._synthesize_azure_tts(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml
                )
            else:
                raise ValueError(f"Unsupported TTS provider: {self.provider}")
        
        except Exception as err:
            self._retry_count += 1
            if self._retry_count < RETRY_ATTEMPTS:
                backoff_time = RETRY_BACKOFF_FACTOR ** self._retry_count
                _LOGGER.warning(
                    "TTS synthesis failed (attempt %d): %s. Retrying in %d seconds",
                    self._retry_count, err, backoff_time
                )
                await asyncio.sleep(backoff_time)
                return await self.synthesize(text, voice, speaking_rate, pitch, volume_gain_db, ssml)
            
            _LOGGER.error("TTS synthesis failed after %d attempts: %s", RETRY_ATTEMPTS, err)
            raise RuntimeError(f"Speech synthesis failed: {err}") from err

    async def _get_gemini_client(self):
        """Get Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient(self.api_key, self.hass)
        return self._gemini_client

    async def _synthesize_gemini_tts(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
    ) -> bytes:
        """Synthesize using Gemini TTS API."""
        try:
            client = await self._get_gemini_client()
            
            # Use default voice if none specified
            if not voice or voice not in GEMINI_VOICES:
                voice = "Kore"  # Default voice
            
            # Prepare text with style instructions if needed
            synthesis_text = text
            if speaking_rate != 1.0 or pitch != 0.0:
                # Add natural language instructions for style control
                style_instructions = []
                if speaking_rate < 0.8:
                    style_instructions.append("speak slowly")
                elif speaking_rate > 1.2:
                    style_instructions.append("speak quickly")
                
                if pitch < -0.2:
                    style_instructions.append("with a lower tone")
                elif pitch > 0.2:
                    style_instructions.append("with a higher tone")
                
                if style_instructions:
                    synthesis_text = f"Please {', '.join(style_instructions)}: {text}"
            
            # Generate speech
            audio_content = await client.generate_speech(synthesis_text, voice)
            
            _LOGGER.debug("Synthesized %d bytes of audio with Gemini TTS", len(audio_content))
            self._retry_count = 0  # Reset retry count on success
            return audio_content
        
        except GeminiAPIError as err:
            _LOGGER.error("Gemini TTS synthesis error: %s", err)
            raise RuntimeError(f"Gemini TTS synthesis failed: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error in Gemini TTS synthesis: %s", err)
            raise

    async def _synthesize_google_cloud(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
    ) -> bytes:
        """Synthesize using Google Cloud TTS."""
        try:
            from google.cloud import texttospeech
            
            client = await self._get_google_client()
            
            # Prepare input text
            if ssml and not text.startswith("<speak>"):
                synthesis_input = texttospeech.SynthesisInput(ssml=f"<speak>{text}</speak>")
            elif ssml:
                synthesis_input = texttospeech.SynthesisInput(ssml=text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            if voice:
                voice_config = texttospeech.VoiceSelectionParams(
                    name=voice,
                    language_code=self.language,
                )
            else:
                voice_config = texttospeech.VoiceSelectionParams(
                    language_code=self.language,
                    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
                )
            
            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db,
            )
            
            def _sync_synthesize():
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_config,
                    audio_config=audio_config,
                )
                return response.audio_content
            
            audio_content = await self.hass.async_add_executor_job(_sync_synthesize)
            
            _LOGGER.debug("Synthesized %d bytes of audio", len(audio_content))
            self._retry_count = 0  # Reset retry count on success
            return audio_content
        
        except ImportError as err:
            _LOGGER.error("Google Cloud TTS library not installed: %s", err)
            raise RuntimeError("Google Cloud TTS library not available") from err
        except Exception as err:
            _LOGGER.error("Google Cloud TTS synthesis error: %s", err)
            raise

    async def _synthesize_amazon_polly(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
    ) -> bytes:
        """Synthesize using Amazon Polly."""
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
            
            client = boto3.client('polly', region_name='us-east-1')
            
            # Prepare input text
            text_type = 'ssml' if ssml else 'text'
            if ssml and not text.startswith('<speak>'):
                text = f'<speak>{text}</speak>'
            
            # Configure synthesis
            synthesis_params = {
                'Text': text,
                'TextType': text_type,
                'OutputFormat': 'mp3',
                'VoiceId': voice or 'Joanna',
                'LanguageCode': self.language,
            }
            
            # Add speech marks for rate/pitch control (limited support)
            if speaking_rate != 1.0 and ssml:
                text = f'<prosody rate="{int(speaking_rate * 100)}%">{text}</prosody>'
                synthesis_params['Text'] = text
            
            def _sync_synthesize():
                response = client.synthesize_speech(**synthesis_params)
                return response['AudioStream'].read()
            
            audio_content = await self.hass.async_add_executor_job(_sync_synthesize)
            
            _LOGGER.debug("Synthesized %d bytes of audio with Polly", len(audio_content))
            self._retry_count = 0
            return audio_content
        
        except ImportError as err:
            _LOGGER.error("Boto3 library not installed: %s", err)
            raise RuntimeError("Boto3 library not available") from err
        except (BotoCoreError, ClientError) as err:
            _LOGGER.error("Amazon Polly synthesis error: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Amazon Polly synthesis error: %s", err)
            raise

    async def _synthesize_azure_tts(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
    ) -> bytes:
        """Synthesize using Azure TTS."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # Configure speech service
            speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region="eastus"  # Default region
            )
            speech_config.speech_synthesis_output_format = speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
            
            # Configure voice
            if voice:
                speech_config.speech_synthesis_voice_name = voice
            else:
                speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            
            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            # Prepare SSML with prosody controls
            if ssml:
                ssml_text = text
            else:
                rate_str = f"{int(speaking_rate * 100)}%" if speaking_rate != 1.0 else "medium"
                pitch_str = f"{pitch:+.1f}Hz" if pitch != 0.0 else "medium"
                
                ssml_text = f"""
                <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{self.language}">
                    <voice name="{speech_config.speech_synthesis_voice_name}">
                        <prosody rate="{rate_str}" pitch="{pitch_str}">
                            {text}
                        </prosody>
                    </voice>
                </speak>
                """
            
            def _sync_synthesize():
                result = synthesizer.speak_ssml_async(ssml_text).get()
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    return result.audio_data
                else:
                    raise RuntimeError(f"Azure TTS failed: {result.reason}")
            
            audio_content = await self.hass.async_add_executor_job(_sync_synthesize)
            
            _LOGGER.debug("Synthesized %d bytes of audio with Azure", len(audio_content))
            self._retry_count = 0
            return audio_content
        
        except ImportError as err:
            _LOGGER.error("Azure Speech SDK not installed: %s", err)
            raise RuntimeError("Azure Speech SDK not available") from err
        except Exception as err:
            _LOGGER.error("Azure TTS synthesis error: %s", err)
            raise

    async def _get_google_client(self):
        """Get Google Cloud TTS client."""
        if self._client is None:
            try:
                from google.cloud import texttospeech
                self._client = texttospeech.TextToSpeechClient()
            except ImportError as err:
                _LOGGER.error("Google Cloud TTS library not installed: %s", err)
                raise RuntimeError("Google Cloud TTS library not available") from err
            except Exception as err:
                _LOGGER.error("Error initializing Google Cloud TTS client: %s", err)
                raise RuntimeError(f"Failed to initialize TTS client: {err}") from err
        
        return self._client

    async def list_voices(self) -> list[Voice]:
        """List available voices."""
        # Check cache first (24h expiry)
        if (self._voices_cache and self._voices_cache_time and 
            dt_util.now() - self._voices_cache_time < timedelta(hours=24)):
            return self._voices_cache
        
        try:
            if self.provider == "gemini_tts":
                voices = await self._list_gemini_voices()
            elif self.provider == "google_cloud":
                voices = await self._list_google_voices()
            elif self.provider == "amazon_polly":
                voices = await self._list_polly_voices()
            elif self.provider == "azure_tts":
                voices = await self._list_azure_voices()
            else:
                voices = []
            
            # Cache results
            self._voices_cache = voices
            self._voices_cache_time = dt_util.now()
            
            return voices
        
        except Exception as err:
            _LOGGER.error("Error listing voices: %s", err)
            return []

    async def _list_gemini_voices(self) -> list[Voice]:
        """List Gemini TTS voices."""
        try:
            # Voice descriptions from the API documentation
            voice_descriptions = {
                "Zephyr": "Bright", "Puck": "Upbeat", "Charon": "Informative",
                "Kore": "Firm", "Fenrir": "Excitable", "Leda": "Youthful",
                "Orus": "Firm", "Aoede": "Breezy", "Callirrhoe": "Easy-going",
                "Autonoe": "Bright", "Enceladus": "Breathy", "Iapetus": "Clear",
                "Umbriel": "Easy-going", "Algieba": "Smooth", "Despina": "Smooth",
                "Erinome": "Clear", "Algenib": "Gravelly", "Rasalgethi": "Informative",
                "Laomedeia": "Upbeat", "Achernar": "Soft", "Alnilam": "Firm",
                "Schedar": "Even", "Gacrux": "Mature", "Pulcherrima": "Forward",
                "Achird": "Friendly", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentle",
                "Sadachbia": "Lively", "Sadaltager": "Knowledgeable", "Sulafat": "Warm"
            }
            
            voices = []
            for voice_name in GEMINI_VOICES:
                voices.append(Voice(
                    name=voice_name,
                    language="en-US",  # Gemini TTS supports multiple languages automatically
                    gender="neutral",  # Gemini voices are not specifically gendered
                    neural=True,  # All Gemini voices are neural
                ))
            
            return voices
        
        except Exception as err:
            _LOGGER.error("Error listing Gemini voices: %s", err)
            return []

    async def _list_google_voices(self) -> list[Voice]:
        """List Google Cloud TTS voices."""
        try:
            from google.cloud import texttospeech
            
            client = await self._get_google_client()
            
            def _sync_list():
                response = client.list_voices()
                voices = []
                for voice in response.voices:
                    if self.language in voice.language_codes:
                        voices.append(Voice(
                            name=voice.name,
                            language=voice.language_codes[0],
                            gender=voice.ssml_gender.name.lower(),
                            neural="Neural" in voice.name or "WaveNet" in voice.name,
                        ))
                return voices
            
            return await self.hass.async_add_executor_job(_sync_list)
        
        except Exception as err:
            _LOGGER.error("Error listing Google voices: %s", err)
            return []

    async def _list_polly_voices(self) -> list[Voice]:
        """List Amazon Polly voices."""
        try:
            import boto3
            
            client = boto3.client('polly', region_name='us-east-1')
            
            def _sync_list():
                response = client.describe_voices(LanguageCode=self.language)
                voices = []
                for voice in response['Voices']:
                    voices.append(Voice(
                        name=voice['Id'],
                        language=voice['LanguageCode'],
                        gender=voice['Gender'].lower(),
                        neural=voice.get('SupportedEngines', []) and 'neural' in voice['SupportedEngines'],
                    ))
                return voices
            
            return await self.hass.async_add_executor_job(_sync_list)
        
        except Exception as err:
            _LOGGER.error("Error listing Polly voices: %s", err)
            return []

    async def _list_azure_voices(self) -> list[Voice]:
        """List Azure TTS voices."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region="eastus"
            )
            
            def _sync_list():
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
                result = synthesizer.get_voices_async().get()
                
                voices = []
                if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                    for voice in result.voices:
                        if voice.locale.startswith(self.language[:2]):
                            voices.append(Voice(
                                name=voice.short_name,
                                language=voice.locale,
                                gender=voice.gender.name.lower(),
                                neural="Neural" in voice.short_name,
                            ))
                return voices
            
            return await self.hass.async_add_executor_job(_sync_list)
        
        except Exception as err:
            _LOGGER.error("Error listing Azure voices: %s", err)
            return []

    async def test_connection(self) -> bool:
        """Test the TTS connection."""
        try:
            if self.provider == "gemini_tts":
                client = await self._get_gemini_client()
                return await client.test_connection()
            elif self.provider == "google_cloud":
                client = await self._get_google_client()
                # Test with a simple synthesis
                audio = await self.synthesize("Test", ssml=False)
                return len(audio) > 0
            elif self.provider == "amazon_polly":
                audio = await self.synthesize("Test", ssml=False)
                return len(audio) > 0
            elif self.provider == "azure_tts":
                audio = await self.synthesize("Test", ssml=False)
                return len(audio) > 0
            
            return False
        except Exception as err:
            _LOGGER.error("TTS connection test failed: %s", err)
            return False 