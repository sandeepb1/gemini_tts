"""Gemini API client using direct REST API calls."""
import asyncio
import json
import logging
import base64
from typing import Dict, Any, Optional, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"Gemini API error {response.status}: {error_text}")
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
    
    async def test_connection(self) -> bool:
        """Test the connection to Gemini API."""
        try:
            await self.generate_text("Hello, this is a test.")
            return True
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            return False 