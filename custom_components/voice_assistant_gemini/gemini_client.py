"""Gemini API client for Voice Assistant integration."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Dict, List, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import GEMINI_VOICES

_LOGGER = logging.getLogger(__name__)

# Gemini API endpoints
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODELS = {
    "text": "gemini-2.0-flash",
    "tts": "gemini-2.5-flash-preview-tts",
    "conversation": "gemini-2.0-flash"
}

# Available TTS voices from the API documentation
GEMINI_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe",
    "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", 
    "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", 
    "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
]


class GeminiAPIError(Exception):
    """Exception raised for Gemini API errors."""
    pass


class GeminiClient:
    """Client for Google Gemini API using REST calls."""
    
    def __init__(self, api_key: str, hass: HomeAssistant):
        """Initialize the Gemini client."""
        self.api_key = api_key
        self.hass = hass
    
    def _get_session(self):
        """Get Home Assistant's aiohttp session."""
        return async_get_clientsession(self.hass)
    
    async def close(self):
        """Close method for compatibility - HA manages the session."""
        pass
    
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Gemini API."""
        url = f"{GEMINI_BASE_URL}/{endpoint}?key={self.api_key}"
        
        session = self._get_session()
        
        try:
            # Log request details for debugging (without API key)
            _LOGGER.debug(f"Making Gemini API request to endpoint: {endpoint}")
            _LOGGER.debug(f"Payload structure: {type(payload)}, contents length: {len(payload.get('contents', []))}")
            
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"Gemini API error {response.status}: {error_text}")
                    
                    # Add specific handling for common errors
                    if response.status == 400 and "INVALID_ARGUMENT" in error_text:
                        _LOGGER.error("INVALID_ARGUMENT error - check audio format, model support, or payload structure")
                    elif response.status == 403:
                        _LOGGER.error("Permission denied - check API key and billing status")
                    elif response.status == 429:
                        _LOGGER.error("Rate limit exceeded - reduce request frequency")
                    
                    raise GeminiAPIError(f"API request failed: {response.status} - {error_text}")
                
                return await response.json()
        
        except Exception as e:
            # Import aiohttp here to avoid import issues
            try:
                import aiohttp
                if isinstance(e, aiohttp.ClientError):
                    _LOGGER.error(f"HTTP client error: {e}")
                    raise GeminiAPIError(f"HTTP client error: {e}")
            except ImportError:
                pass
            
            if isinstance(e, json.JSONDecodeError):
                _LOGGER.error(f"JSON decode error: {e}")
                raise GeminiAPIError(f"Invalid JSON response: {e}")
            
            _LOGGER.error(f"Unexpected error in API request: {e}")
            raise GeminiAPIError(f"API request failed: {e}")
    
    async def generate_text(self, prompt: str, model: str = None) -> str:
        """Generate text using Gemini API."""
        if model is None:
            model = GEMINI_MODELS["text"]
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }
        
        endpoint = f"models/{model}:generateContent"
        
        try:
            response = await self._make_request(endpoint, payload)
            
            # Extract text from response
            if "candidates" in response and response["candidates"]:
                candidate = response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            
            _LOGGER.error(f"Unexpected response format: {response}")
            raise GeminiAPIError("Unexpected response format")
            
        except Exception as e:
            _LOGGER.error(f"Error generating text: {e}")
            raise GeminiAPIError(f"Text generation failed: {e}")
    
    async def generate_speech(self, text: str, voice: str = "Kore") -> bytes:
        """Generate speech using Gemini TTS API."""
        if voice not in GEMINI_VOICES:
            _LOGGER.warning(f"Unknown voice {voice}, using default 'Kore'")
            voice = "Kore"
        
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice
                        }
                    }
                }
            }
        }
        
        endpoint = f"models/{GEMINI_MODELS['tts']}:generateContent"
        
        try:
            response = await self._make_request(endpoint, payload)
            
            # Extract audio data from response
            if "candidates" in response and response["candidates"]:
                candidate = response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "inlineData" in parts[0] and "data" in parts[0]["inlineData"]:
                        # Decode base64 audio data
                        audio_data = parts[0]["inlineData"]["data"]
                        return base64.b64decode(audio_data)
            
            _LOGGER.error(f"Unexpected TTS response format: {response}")
            raise GeminiAPIError("Unexpected TTS response format")
            
        except Exception as e:
            _LOGGER.error(f"Error generating speech: {e}")
            raise GeminiAPIError(f"Speech generation failed: {e}")
    
    async def conversation(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Have a conversation using Gemini API."""
        # Build conversation contents with proper Gemini API format
        contents = []
        
        # Add conversation messages with correct role mapping
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Map Home Assistant roles to Gemini API roles
            if role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                # Gemini API uses "model" instead of "assistant"
                contents.append({
                    "role": "model", 
                    "parts": [{"text": content}]
                })
            elif role == "system":
                # System messages should be handled via systemInstruction parameter
                continue
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 1500
            }
        }
        
        # Add system instruction if provided
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        endpoint = f"models/{GEMINI_MODELS['conversation']}:generateContent"
        
        try:
            response = await self._make_request(endpoint, payload)
            
            # Extract text from response
            if "candidates" in response and response["candidates"]:
                candidate = response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            
            _LOGGER.error(f"Unexpected conversation response format: {response}")
            raise GeminiAPIError("Unexpected conversation response format")
            
        except Exception as e:
            _LOGGER.error(f"Error in conversation: {e}")
            raise GeminiAPIError(f"Conversation failed: {e}")
    
    async def transcribe_audio(self, audio_data: bytes, language: str = "en-US") -> str:
        """Transcribe audio using Gemini API."""
        try:
            # Debug: Check the first few bytes of audio data
            first_bytes = audio_data[:16] if len(audio_data) >= 16 else audio_data
            _LOGGER.debug(f"Audio data first 16 bytes: {first_bytes}")
            _LOGGER.debug(f"Audio data size: {len(audio_data)} bytes")
            
            # Convert audio to base64 for inline data
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Detect MIME type based on audio data
            mime_type = "audio/wav"  # Default to WAV
            
            if audio_data.startswith(b'RIFF'):
                # Check if it's a proper WAV file (RIFF + WAVE)
                if len(audio_data) >= 12 and audio_data[8:12] == b'WAVE':
                    mime_type = "audio/wav"
                    _LOGGER.debug("Detected proper WAV format (RIFF+WAVE)")
                else:
                    # RIFF but not WAVE - treat as WAV anyway
                    mime_type = "audio/wav"
                    _LOGGER.debug("RIFF format but not WAVE - treating as WAV")
            elif audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'\xff\xf3') or audio_data.startswith(b'\xff\xf2'):
                mime_type = "audio/mp3"
                _LOGGER.debug("Detected MP3 format")
            elif audio_data.startswith(b'fLaC'):
                mime_type = "audio/flac"
                _LOGGER.debug("Detected FLAC format")
            elif audio_data.startswith(b'OggS'):
                mime_type = "audio/ogg"
                _LOGGER.debug("Detected OGG format")
            else:
                # This is likely raw PCM data from ESPHome
                _LOGGER.info(f"No recognized audio header found, treating as raw PCM data")
                _LOGGER.info(f"Raw PCM data size: {len(audio_data)} bytes, first 16 bytes: {first_bytes.hex()}")
                
                # Create proper WAV header for raw PCM data
                # ESPHome typically sends 16kHz, 16-bit, mono PCM
                audio_data = self._create_wav_from_pcm(audio_data)
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                mime_type = "audio/wav"
                _LOGGER.info(f"Created WAV container from raw PCM, new size: {len(audio_data)} bytes")
            
            _LOGGER.debug(f"Using MIME type: {mime_type} for audio transcription")
            
            # Use the correct payload format for audio transcription
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "text": "Please transcribe the speech in this audio."
                        },
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": audio_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,  # Low temperature for accurate transcription
                    "maxOutputTokens": 1000
                }
            }
            
            # Use gemini-2.0-flash which supports audio transcription
            endpoint = f"models/gemini-2.0-flash:generateContent"
            
            response = await self._make_request(endpoint, payload)
            
            # Extract transcription from response
            if "candidates" in response and response["candidates"]:
                candidate = response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        transcription = parts[0]["text"].strip()
                        # Clean up the transcription (remove any prefixes like "Transcription:")
                        transcription_lower = transcription.lower()
                        if transcription_lower.startswith("transcription:"):
                            transcription = transcription[14:].strip()
                        elif transcription_lower.startswith("transcript:"):
                            transcription = transcription[11:].strip()
                        elif transcription_lower.startswith("the transcription is:"):
                            transcription = transcription[21:].strip()
                        elif transcription_lower.startswith("speech transcription:"):
                            transcription = transcription[21:].strip()
                        return transcription
            
            _LOGGER.error(f"Unexpected STT response format: {response}")
            raise GeminiAPIError("Unexpected STT response format")
            
        except Exception as e:
            _LOGGER.error(f"Error transcribing audio: {e}")
            raise GeminiAPIError(f"Audio transcription failed: {e}")

    def _create_wav_from_pcm(self, pcm_data: bytes) -> bytes:
        """Create a WAV file from raw PCM data."""
        # Assume standard ESPHome parameters: 16kHz, 16-bit, mono
        sample_rate = 16000
        bits_per_sample = 16
        channels = 1
        
        # Calculate derived values
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        file_size = 36 + data_size
        
        _LOGGER.debug(f"Creating WAV header: sample_rate={sample_rate}, channels={channels}, bits_per_sample={bits_per_sample}")
        _LOGGER.debug(f"PCM data size: {data_size}, expected file size: {file_size + 8}")
        
        # Create WAV header
        header = bytearray()
        
        # RIFF header
        header.extend(b'RIFF')
        header.extend(file_size.to_bytes(4, 'little'))
        header.extend(b'WAVE')
        
        # fmt chunk
        header.extend(b'fmt ')
        header.extend((16).to_bytes(4, 'little'))  # Subchunk1Size (16 for PCM)
        header.extend((1).to_bytes(2, 'little'))   # AudioFormat (1 for PCM)
        header.extend(channels.to_bytes(2, 'little'))
        header.extend(sample_rate.to_bytes(4, 'little'))
        header.extend(byte_rate.to_bytes(4, 'little'))
        header.extend(block_align.to_bytes(2, 'little'))
        header.extend(bits_per_sample.to_bytes(2, 'little'))
        
        # data chunk
        header.extend(b'data')
        header.extend(data_size.to_bytes(4, 'little'))
        
        wav_data = bytes(header) + pcm_data
        _LOGGER.debug(f"Created WAV file with header size: {len(header)} bytes, total size: {len(wav_data)} bytes")
        
        return wav_data

    async def test_connection(self) -> bool:
        """Test the connection to Gemini API."""
        try:
            await self.generate_text("Hello, this is a test.")
            return True
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            return False 