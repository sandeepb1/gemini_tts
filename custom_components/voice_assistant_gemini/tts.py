"""Text-to-Speech client for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType, Voice as TTSVoice
from homeassistant.helpers.entity import EntityCategory

from .const import (
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
    DOMAIN,
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
        emotion: str = "neutral",
        tone_style: str = "normal",
    ) -> bytes:
        """Synthesize text to speech."""
        try:
            if self.provider == "gemini_tts":
                return await self._synthesize_gemini_tts(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
                )
            elif self.provider == "google_cloud":
                return await self._synthesize_google_cloud(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
                )
            elif self.provider == "amazon_polly":
                return await self._synthesize_amazon_polly(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
                )
            elif self.provider == "azure_tts":
                return await self._synthesize_azure_tts(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
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
                return await self.synthesize(text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style)
            
            _LOGGER.error("TTS synthesis failed after %d attempts: %s", RETRY_ATTEMPTS, err)
            raise RuntimeError(f"Speech synthesis failed: {err}") from err

    async def synthesize_streaming(
        self,
        text: str,
        voice: str = "",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        ssml: bool = False,
        emotion: str = "neutral",
        tone_style: str = "normal",
        chunk_callback=None,
    ) -> bytes:
        """Synthesize text to speech with streaming support for long texts."""
        try:
            if self.provider == "gemini_tts":
                return await self._synthesize_gemini_tts_streaming(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style, chunk_callback
                )
            else:
                # For non-Gemini providers, fall back to regular synthesis
                return await self.synthesize(text, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style)
        
        except Exception as err:
            _LOGGER.error("TTS streaming synthesis failed: %s", err)
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
        emotion: str = "neutral",
        tone_style: str = "normal",
    ) -> bytes:
        """Synthesize using Gemini TTS API."""
        try:
            client = await self._get_gemini_client()
            
            # Use default voice if none specified
            if not voice or voice not in GEMINI_VOICES:
                voice = "Kore"  # Default voice
            
            # Prepare text with style instructions if needed
            synthesis_text = text
            style_instructions = []
            
            # Add emotion instructions
            if emotion != "neutral":
                emotion_map = {
                    "happy": "in a happy and cheerful manner",
                    "sad": "in a somber and melancholic tone",
                    "excited": "with energy and enthusiasm",
                    "calm": "in a relaxed and peaceful way",
                    "confident": "with confidence and strength",
                    "friendly": "in a warm and approachable manner",
                    "professional": "in a business-like and formal tone"
                }
                if emotion in emotion_map:
                    style_instructions.append(emotion_map[emotion])
            
            # Add tone style instructions  
            if tone_style != "normal":
                tone_map = {
                    "casual": "in a casual and relaxed conversational style",
                    "formal": "in a professional and structured manner",
                    "storytelling": "in an engaging narrative style",
                    "informative": "in a clear and educational way",
                    "conversational": "as if having a natural conversation",
                    "announcement": "as a clear and important announcement",
                    "customer_service": "in a helpful and polite customer service manner"
                }
                if tone_style in tone_map:
                    style_instructions.append(tone_map[tone_style])
            
            # Add speaking rate and pitch instructions
            if speaking_rate < 0.8:
                style_instructions.append("speak slowly")
            elif speaking_rate > 1.2:
                style_instructions.append("speak quickly")
            
            if pitch < -0.2:
                style_instructions.append("with a lower tone")
            elif pitch > 0.2:
                style_instructions.append("with a higher tone")
            
            # Apply styling if instructions exist
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

    async def _synthesize_gemini_tts_streaming(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
        emotion: str = "neutral",
        tone_style: str = "normal",
        chunk_callback=None,
    ) -> bytes:
        """Synthesize using Gemini TTS API with streaming support."""
        try:
            client = await self._get_gemini_client()
            
            # Use default voice if none specified
            if not voice or voice not in GEMINI_VOICES:
                voice = "Kore"  # Default voice
            
            # Prepare text with style instructions if needed
            synthesis_text = text
            style_instructions = []
            
            # Add emotion instructions
            if emotion != "neutral":
                emotion_map = {
                    "happy": "in a happy and cheerful manner",
                    "sad": "in a somber and melancholic tone",
                    "excited": "with energy and enthusiasm",
                    "calm": "in a relaxed and peaceful way",
                    "confident": "with confidence and strength",
                    "friendly": "in a warm and approachable manner",
                    "professional": "in a business-like and formal tone"
                }
                if emotion in emotion_map:
                    style_instructions.append(emotion_map[emotion])
            
            # Add tone style instructions  
            if tone_style != "normal":
                tone_map = {
                    "casual": "in a casual and relaxed conversational style",
                    "formal": "in a professional and structured manner",
                    "storytelling": "in an engaging narrative style",
                    "informative": "in a clear and educational way",
                    "conversational": "as if having a natural conversation",
                    "announcement": "as a clear and important announcement",
                    "customer_service": "in a helpful and polite customer service manner"
                }
                if tone_style in tone_map:
                    style_instructions.append(tone_map[tone_style])
            
            # Add speaking rate and pitch instructions
            if speaking_rate < 0.8:
                style_instructions.append("speak slowly")
            elif speaking_rate > 1.2:
                style_instructions.append("speak quickly")
            
            if pitch < -0.2:
                style_instructions.append("with a lower tone")
            elif pitch > 0.2:
                style_instructions.append("with a higher tone")
            
            # Apply styling if instructions exist
            if style_instructions:
                synthesis_text = f"Please {', '.join(style_instructions)}: {text}"
            
            # Generate speech using streaming approach
            audio_content = await client.generate_speech_streaming(
                synthesis_text, 
                voice, 
                chunk_callback=chunk_callback
            )
            
            _LOGGER.debug("Synthesized %d bytes of streaming audio with Gemini TTS", len(audio_content))
            self._retry_count = 0  # Reset retry count on success
            return audio_content
        
        except GeminiAPIError as err:
            _LOGGER.error("Gemini TTS streaming synthesis error: %s", err)
            raise RuntimeError(f"Gemini TTS streaming synthesis failed: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error in Gemini TTS streaming synthesis: %s", err)
            raise

    async def _synthesize_google_cloud(
        self,
        text: str,
        voice: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        ssml: bool,
        emotion: str = "neutral",
        tone_style: str = "normal",
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
        emotion: str = "neutral",
        tone_style: str = "normal",
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
        emotion: str = "neutral",
        tone_style: str = "normal",
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
                
                # Initialize client in executor to avoid blocking
                def _create_client():
                    return texttospeech.TextToSpeechClient()
                
                self._client = await self.hass.async_add_executor_job(_create_client)
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up TTS provider."""
    # Get values from options first, then config data
    options = config_entry.options
    data = config_entry.data
    
    # Create TTS provider
    api_key = options.get("tts_api_key") or data.get("tts_api_key") or options.get("gemini_api_key") or data.get("gemini_api_key")
    language = options.get("default_language") or data.get("default_language", "en-US")
    provider = options.get("tts_provider") or data.get("tts_provider", "gemini_tts")
    model = options.get("tts_model") or data.get("tts_model", "gemini-2.5-flash-preview-tts")
    
    tts_provider = GeminiTTSProvider(hass, config_entry, api_key, language, provider, model)
    
    async_add_entities([tts_provider])
    return True


class GeminiTTSProvider(TextToSpeechEntity):
    """Gemini TTS provider for Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_key: str,
        language: str,
        provider: str,
        model: str,
    ) -> None:
        """Initialize the TTS provider."""
        super().__init__()
        self.hass = hass
        self.config_entry = config_entry
        self.provider = provider  # Store provider attribute
        self.language = language  # Store language attribute
        self.model = model  # Store model attribute
        self._client = TTSClient(hass, api_key, language, provider)
        self._attr_name = f"Gemini TTS ({provider})"
        self._attr_unique_id = f"{config_entry.entry_id}_tts"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def name(self) -> str:
        """Return the name of the TTS provider."""
        return self._attr_name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the TTS provider."""
        return self._attr_unique_id

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return [
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR",
            "ru-RU", "ja-JP", "ko-KR", "zh-CN", "zh-TW", "ar-SA", "hi-IN"
        ]

    @property
    def default_language(self) -> str:
        """Return the default language."""
        options = self.config_entry.options
        data = self.config_entry.data
        return options.get("default_language") or data.get("default_language", "en-US")

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options."""
        return ["voice", "speed", "pitch"]

    @property
    def supported_voices(self) -> list[TTSVoice]:
        """Return list of supported voices."""
        from .const import GEMINI_VOICES, GEMINI_VOICE_DESCRIPTIONS
        
        # Return a comprehensive list of Gemini voices with descriptions
        if self.provider == "gemini_tts":
            voices = []
            for voice_id in GEMINI_VOICES:
                description = GEMINI_VOICE_DESCRIPTIONS.get(voice_id, "")
                display_name = f"{voice_id} - {description}" if description else voice_id
                voices.append(TTSVoice(voice_id=voice_id, name=display_name))
            return voices
        else:
            return []

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert raw PCM data to WAV format."""
        import struct
        import io
        
        # Gemini TTS returns 16-bit signed little-endian PCM at 24kHz, mono
        sample_rate = 24000
        channels = 1
        bits_per_sample = 16
        
        # Calculate sizes
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        file_size = 36 + data_size
        
        # Create WAV header
        wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF',           # ChunkID
            file_size,         # ChunkSize
            b'WAVE',           # Format
            b'fmt ',           # Subchunk1ID
            16,                # Subchunk1Size (PCM)
            1,                 # AudioFormat (PCM)
            channels,          # NumChannels
            sample_rate,       # SampleRate
            byte_rate,         # ByteRate
            block_align,       # BlockAlign
            bits_per_sample,   # BitsPerSample
            b'data',           # Subchunk2ID
            data_size          # Subchunk2Size
        )
        
        # Combine header and data
        return wav_header + pcm_data

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Return TTS audio."""
        try:
            _LOGGER.debug("TTS request - provider: %s, message: %s", getattr(self, 'provider', 'NOT_SET'), message)
            if options is None:
                options = {}
            
            # Extract options
            voice = options.get("voice", "")
            
            # Use default voice from config if no voice specified
            if not voice:
                config_options = self.config_entry.options
                config_data = self.config_entry.data
                voice = config_options.get("default_voice") or config_data.get("default_voice", "Kore")
            
            speaking_rate = float(options.get("speed", 1.0))
            pitch = float(options.get("pitch", 0.0))
            volume_gain_db = 0.0
            ssml = False
            
            # Extract emotion and tone style from options or config
            config_options = self.config_entry.options
            config_data = self.config_entry.data
            emotion = options.get("emotion") or config_options.get("emotion") or config_data.get("emotion", "neutral")
            tone_style = options.get("tone_style") or config_options.get("tone_style") or config_data.get("tone_style", "normal")
            
            # Check if streaming should be used (for longer texts or explicit request)
            use_streaming = options.get("streaming", len(message) > 200)
            
            # Synthesize speech
            if use_streaming and self.provider == "gemini_tts":
                _LOGGER.debug("Using streaming synthesis for %d character message", len(message))
                audio_data = await self._client.synthesize_streaming(
                    message, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
                )
            else:
                audio_data = await self._client.synthesize(
                    message, voice, speaking_rate, pitch, volume_gain_db, ssml, emotion, tone_style
                )
            
            # Ensure we return proper audio format
            if not audio_data:
                raise RuntimeError("No audio data received from TTS service")
            
            # Gemini TTS returns raw PCM audio data (16-bit signed little-endian at 24kHz)
            # We need to convert it to a proper WAV format for Home Assistant
            if self.provider == "gemini_tts":
                # Convert raw PCM to WAV format
                wav_data = self._pcm_to_wav(audio_data)
                return ("wav", wav_data)
            else:
                return ("mp3", audio_data)
        
        except Exception as err:
            _LOGGER.error("TTS synthesis error: %s", err)
            raise 