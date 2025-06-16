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
        # Build conversation contents
        contents = []
        
        # Add system prompt if provided
        if system_prompt:
            contents.append({
                "parts": [{"text": f"System: {system_prompt}"}]
            })
        
        # Add conversation messages
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                contents.append({
                    "parts": [{"text": f"User: {content}"}]
                })
            elif role == "assistant":
                contents.append({
                    "parts": [{"text": f"Assistant: {content}"}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 1500
            }
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
        """Transcribe audio using Gemini Live API."""
        try:
            # Debug: Check the first few bytes of audio data
            first_bytes = audio_data[:16] if len(audio_data) >= 16 else audio_data
            _LOGGER.debug(f"Audio data first 16 bytes: {first_bytes}")
            _LOGGER.debug(f"Audio data size: {len(audio_data)} bytes")
            
            # Detect if this is raw PCM data (common for ESPHome/voice assistants)
            if audio_data.startswith(b'RIFF'):
                # Check if it's a proper WAV file (RIFF + WAVE)
                if len(audio_data) >= 12 and audio_data[8:12] == b'WAVE':
                    _LOGGER.debug("Detected proper WAV format (RIFF+WAVE)")
                    # Extract PCM data from WAV file
                    audio_data = self._extract_pcm_from_wav(audio_data)
                else:
                    _LOGGER.debug("RIFF format but not WAVE - treating as raw PCM")
            elif audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'\xff\xf3') or audio_data.startswith(b'\xff\xf2'):
                _LOGGER.error("MP3 format not supported for Live API transcription")
                raise GeminiAPIError("MP3 format not supported for Live API transcription")
            elif audio_data.startswith(b'fLaC'):
                _LOGGER.error("FLAC format not supported for Live API transcription")
                raise GeminiAPIError("FLAC format not supported for Live API transcription")
            elif audio_data.startswith(b'OggS'):
                _LOGGER.error("OGG format not supported for Live API transcription")
                raise GeminiAPIError("OGG format not supported for Live API transcription")
            else:
                # This is likely raw PCM data from ESPHome
                _LOGGER.info(f"No recognized audio header found, treating as raw PCM data")
                _LOGGER.info(f"Raw PCM data size: {len(audio_data)} bytes, first 16 bytes: {first_bytes.hex()}")
            
            # Use Live API for audio transcription
            return await self._transcribe_with_live_api(audio_data)
            
        except Exception as e:
            _LOGGER.error(f"Error transcribing audio: {e}")
            raise GeminiAPIError(f"Audio transcription failed: {e}")

    async def _transcribe_with_live_api(self, pcm_data: bytes) -> str:
        """Transcribe audio using Gemini Live API."""
        try:
            from google.genai import types
            
            # Configure Live API session for text output
            config = types.LiveConnectConfig(
                response_modalities=["TEXT"],
                input_audio_transcription={}  # Enable input transcription
            )
            
            _LOGGER.debug(f"Starting Live API session for transcription")
            
            # Create Live API session
            async with self.client.aio.live.connect(
                model="gemini-2.0-flash-live-001", 
                config=config
            ) as session:
                
                # Send audio data as realtime input
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=pcm_data, 
                        mime_type="audio/pcm;rate=16000"
                    )
                )
                
                # Wait for transcription response
                transcription = ""
                timeout_seconds = 10
                
                try:
                    async with asyncio.timeout(timeout_seconds):
                        async for response in session.receive():
                            # Check for input transcription
                            if (hasattr(response, 'server_content') and 
                                response.server_content and 
                                hasattr(response.server_content, 'input_transcription') and
                                response.server_content.input_transcription):
                                
                                transcription += response.server_content.input_transcription.text
                                _LOGGER.debug(f"Received transcription: {response.server_content.input_transcription.text}")
                            
                            # Check for text response (alternative transcription method)
                            if response.text:
                                transcription += response.text
                                _LOGGER.debug(f"Received text response: {response.text}")
                            
                            # Check if turn is complete
                            if (hasattr(response, 'server_content') and 
                                response.server_content and 
                                hasattr(response.server_content, 'turn_complete') and
                                response.server_content.turn_complete):
                                _LOGGER.debug("Turn complete signal received")
                                break
                                
                except asyncio.TimeoutError:
                    _LOGGER.warning(f"Transcription timeout after {timeout_seconds} seconds")
                    if not transcription:
                        raise GeminiAPIError("Transcription timeout - no response received")
                
                if transcription:
                    # Clean up the transcription
                    transcription = transcription.strip()
                    _LOGGER.info(f"Transcription successful: {transcription}")
                    return transcription
                else:
                    _LOGGER.warning("No transcription received from Live API")
                    raise GeminiAPIError("No transcription received")
                    
        except Exception as e:
            _LOGGER.error(f"Live API transcription error: {e}")
            raise GeminiAPIError(f"Live API transcription failed: {e}")

    def _extract_pcm_from_wav(self, wav_data: bytes) -> bytes:
        """Extract PCM data from WAV file."""
        try:
            # Simple WAV parser to extract PCM data
            # WAV format: RIFF header (12 bytes) + fmt chunk + data chunk
            
            if len(wav_data) < 44:  # Minimum WAV file size
                _LOGGER.warning("WAV file too small, treating as raw PCM")
                return wav_data
            
            # Find the data chunk
            data_offset = 12  # Skip RIFF header
            
            while data_offset < len(wav_data) - 8:
                chunk_id = wav_data[data_offset:data_offset + 4]
                chunk_size = int.from_bytes(wav_data[data_offset + 4:data_offset + 8], 'little')
                
                if chunk_id == b'data':
                    # Found data chunk, extract PCM data
                    pcm_start = data_offset + 8
                    pcm_end = pcm_start + chunk_size
                    pcm_data = wav_data[pcm_start:pcm_end]
                    _LOGGER.debug(f"Extracted {len(pcm_data)} bytes of PCM data from WAV")
                    return pcm_data
                
                # Move to next chunk
                data_offset += 8 + chunk_size
                if chunk_size % 2:  # Align to even byte boundary
                    data_offset += 1
            
            _LOGGER.warning("No data chunk found in WAV file, treating as raw PCM")
            return wav_data
            
        except Exception as e:
            _LOGGER.warning(f"Error parsing WAV file: {e}, treating as raw PCM")
            return wav_data

    async def test_connection(self) -> bool:
        """Test the connection to Gemini API."""
        try:
            await self.generate_text("Hello, this is a test.")
            return True
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            return False 