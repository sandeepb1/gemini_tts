"""WebSocket API for Voice Assistant Gemini."""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEFAULT_LANGUAGE,
    CONF_DEFAULT_VOICE,
    CONF_EMOTION,
    CONF_TONE_STYLE,
    CONF_GEMINI_API_KEY,
    CONF_GEMINI_MODEL,
    CONF_MAX_TOKENS,
    CONF_PITCH,
    CONF_SPEAKING_RATE,
    CONF_SSML,
    CONF_STT_API_KEY,
    CONF_STT_PROVIDER,
    CONF_TEMPERATURE,
    CONF_TTS_API_KEY,
    CONF_TTS_PROVIDER,
    CONF_VOLUME_GAIN_DB,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PITCH,
    DEFAULT_SPEAKING_RATE,
    DEFAULT_SSML,
    DEFAULT_EMOTION,
    DEFAULT_TONE_STYLE,
    DEFAULT_STT_PROVIDER,
    DEFAULT_TEMPERATURE,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_VOLUME_GAIN_DB,
    DOMAIN,
)
from .conversation import GeminiAgent
from .stt import STTClient
from .tts import TTSClient

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_api(hass: HomeAssistant) -> bool:
    """Register WebSocket API commands."""
    try:
        _LOGGER.debug("Registering Voice Assistant Gemini WebSocket API commands")
        websocket_api.async_register_command(hass, ws_list_voices)
        websocket_api.async_register_command(hass, ws_transcribe)
        websocket_api.async_register_command(hass, ws_synthesize)
        websocket_api.async_register_command(hass, ws_converse)
        websocket_api.async_register_command(hass, ws_get_session_history)
        websocket_api.async_register_command(hass, ws_clear_session)
        websocket_api.async_register_command(hass, ws_get_session_stats)
        websocket_api.async_register_command(hass, ws_preview_voice)
        
        _LOGGER.info("Voice Assistant Gemini WebSocket API registered")
    
    except Exception as err:
        _LOGGER.error("Failed to register Voice Assistant Gemini WebSocket API: %s", err, exc_info=True)
        raise

    # Explicitly return to indicate success
    return True


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/list_voices",
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
    vol.Optional("provider", default=DEFAULT_TTS_PROVIDER): cv.string,
})
@websocket_api.async_response
async def ws_list_voices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List available voices."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        
        language = msg.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
        provider = msg.get("provider", config.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER))
        
        # Initialize TTS client
        api_key = config.get(CONF_TTS_API_KEY) or config.get(CONF_GEMINI_API_KEY)
        tts_client = TTSClient(hass, api_key, language, provider)
        
        # Get voices
        voices = await tts_client.list_voices()
        
        connection.send_result(msg["id"], {
            "voices": [
                {
                    "name": voice.name,
                    "language": voice.language,
                    "gender": voice.gender,
                    "neural": voice.neural,
                }
                for voice in voices
            ],
            "provider": provider,
            "language": language,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket list_voices error: %s", err)
        connection.send_error(msg["id"], "list_voices_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/transcribe",
    vol.Required("audio_data"): cv.string,
    vol.Optional("session_id"): cv.string,
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
    vol.Optional("provider", default=DEFAULT_STT_PROVIDER): cv.string,
})
@websocket_api.async_response
async def ws_transcribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Transcribe audio to text."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        
        # Get parameters
        audio_data = msg["audio_data"]
        session_id = msg.get("session_id")
        language = msg.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
        provider = msg.get("provider", config.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER))
        
        # Decode audio data
        audio_bytes = base64.b64decode(audio_data)
        
        # Initialize STT client
        api_key = config.get(CONF_STT_API_KEY) or config.get(CONF_GEMINI_API_KEY)
        stt_client = STTClient(hass, api_key, language, provider)
        
        # Transcribe
        transcript = await stt_client.transcribe(audio_bytes)
        
        connection.send_result(msg["id"], {
            "transcript": transcript,
            "session_id": session_id,
            "language": language,
            "provider": provider,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket transcribe error: %s", err)
        connection.send_error(msg["id"], "transcribe_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/synthesize",
    vol.Required("text"): cv.string,
    vol.Optional("voice", default=""): cv.string,
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
    vol.Optional("provider", default=DEFAULT_TTS_PROVIDER): cv.string,
    vol.Optional("speaking_rate", default=DEFAULT_SPEAKING_RATE): vol.All(
        vol.Coerce(float), vol.Range(min=0.25, max=4.0)
    ),
    vol.Optional("pitch", default=DEFAULT_PITCH): vol.All(
        vol.Coerce(float), vol.Range(min=-20.0, max=20.0)
    ),
    vol.Optional("volume_gain_db", default=DEFAULT_VOLUME_GAIN_DB): vol.All(
        vol.Coerce(float), vol.Range(min=-96.0, max=16.0)
    ),
    vol.Optional("ssml", default=DEFAULT_SSML): cv.boolean,
    vol.Optional("session_id"): cv.string,
})
@websocket_api.async_response
async def ws_synthesize(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Synthesize text to speech."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        
        # Get parameters
        text = msg["text"]
        voice = msg.get("voice", config.get(CONF_DEFAULT_VOICE, ""))
        language = msg.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
        provider = msg.get("provider", config.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER))
        speaking_rate = msg.get("speaking_rate", config.get(CONF_SPEAKING_RATE, DEFAULT_SPEAKING_RATE))
        pitch = msg.get("pitch", config.get(CONF_PITCH, DEFAULT_PITCH))
        volume_gain_db = msg.get("volume_gain_db", config.get(CONF_VOLUME_GAIN_DB, DEFAULT_VOLUME_GAIN_DB))
        ssml = msg.get("ssml", config.get(CONF_SSML, DEFAULT_SSML))
        session_id = msg.get("session_id")
        
        # Initialize TTS client
        api_key = config.get(CONF_TTS_API_KEY) or config.get(CONF_GEMINI_API_KEY)
        tts_client = TTSClient(hass, api_key, language, provider)
        
        # Synthesize
        audio_bytes = await tts_client.synthesize(
            text, voice, speaking_rate, pitch, volume_gain_db, ssml
        )
        
        # Encode audio as base64
        audio_data = base64.b64encode(audio_bytes).decode()
        
        connection.send_result(msg["id"], {
            "audio_data": audio_data,
            "text": text,
            "voice": voice,
            "language": language,
            "provider": provider,
            "session_id": session_id,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket synthesize error: %s", err)
        connection.send_error(msg["id"], "synthesize_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/converse",
    vol.Optional("text"): cv.string,
    vol.Optional("audio_data"): cv.string,
    vol.Optional("session_id"): cv.string,
    vol.Optional("system_prompt"): cv.string,
    vol.Optional("model", default=DEFAULT_GEMINI_MODEL): cv.string,
    vol.Optional("temperature", default=DEFAULT_TEMPERATURE): vol.All(
        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
    ),
    vol.Optional("max_tokens", default=DEFAULT_MAX_TOKENS): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=8192)
    ),
    vol.Optional("voice_response", default=True): cv.boolean,
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
})
@websocket_api.async_response
async def ws_converse(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Have a conversation with Gemini."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        
        # Get parameters
        text = msg.get("text")
        audio_data = msg.get("audio_data")
        session_id = msg.get("session_id")
        system_prompt = msg.get("system_prompt")
        model = msg.get("model", config.get(CONF_GEMINI_MODEL, DEFAULT_GEMINI_MODEL))
        temperature = msg.get("temperature", config.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
        max_tokens = msg.get("max_tokens", config.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
        voice_response = msg.get("voice_response", True)
        language = msg.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
        
        # Get text input
        if not text and audio_data:
            # Transcribe audio first
            audio_bytes = base64.b64decode(audio_data)
            
            # Initialize STT client
            stt_api_key = config.get(CONF_STT_API_KEY) or config.get(CONF_GEMINI_API_KEY)
            stt_provider = config.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER)
            stt_client = STTClient(hass, stt_api_key, language, stt_provider)
            
            text = await stt_client.transcribe(audio_bytes)
        
        if not text:
            connection.send_error(msg["id"], "no_input", "No text or audio input provided")
            return
        
        # Initialize Gemini agent
        gemini_api_key = config.get(CONF_GEMINI_API_KEY)
        gemini_agent = GeminiAgent(
            hass, gemini_api_key, model, temperature, max_tokens, coordinator
        )
        
        # Generate response
        response_text, metadata = await gemini_agent.generate(
            text, session_id, system_prompt
        )
        
        result = {
            "user_text": text,
            "response_text": response_text,
            "metadata": metadata,
            "language": language,
        }
        
        # Generate voice response if requested
        if voice_response:
            # Initialize TTS client
            tts_api_key = config.get(CONF_TTS_API_KEY) or config.get(CONF_GEMINI_API_KEY)
            tts_provider = config.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER)
            tts_client = TTSClient(hass, tts_api_key, language, tts_provider)
            
            # Get TTS settings
            voice = config.get(CONF_DEFAULT_VOICE, "")
            speaking_rate = config.get(CONF_SPEAKING_RATE, DEFAULT_SPEAKING_RATE)
            pitch = config.get(CONF_PITCH, DEFAULT_PITCH)
            volume_gain_db = config.get(CONF_VOLUME_GAIN_DB, DEFAULT_VOLUME_GAIN_DB)
            ssml = config.get(CONF_SSML, DEFAULT_SSML)
            
            # Synthesize response
            audio_bytes = await tts_client.synthesize(
                response_text, voice, speaking_rate, pitch, volume_gain_db, ssml
            )
            
            # Encode audio as base64
            result["audio_data"] = base64.b64encode(audio_bytes).decode()
        
        connection.send_result(msg["id"], result)
    
    except Exception as err:
        _LOGGER.error("WebSocket converse error: %s", err)
        connection.send_error(msg["id"], "converse_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/get_session_history",
    vol.Required("session_id"): cv.string,
})
@websocket_api.async_response
async def ws_get_session_history(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get conversation history for a session."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        
        session_id = msg["session_id"]
        
        # Initialize Gemini agent
        gemini_api_key = config.get(CONF_GEMINI_API_KEY)
        gemini_agent = GeminiAgent(hass, gemini_api_key, coordinator=coordinator)
        
        # Get history
        history = await gemini_agent.get_session_history(session_id)
        
        connection.send_result(msg["id"], {
            "session_id": session_id,
            "history": history,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket get_session_history error: %s", err)
        connection.send_error(msg["id"], "get_history_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/clear_session",
    vol.Required("session_id"): cv.string,
})
@websocket_api.async_response
async def ws_clear_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clear a conversation session."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        
        session_id = msg["session_id"]
        
        # Initialize Gemini agent
        gemini_api_key = config.get(CONF_GEMINI_API_KEY)
        gemini_agent = GeminiAgent(hass, gemini_api_key, coordinator=coordinator)
        
        # Clear session
        await gemini_agent.clear_session(session_id)
        
        connection.send_result(msg["id"], {
            "session_id": session_id,
            "cleared": True,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket clear_session error: %s", err)
        connection.send_error(msg["id"], "clear_session_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/get_session_stats",
})
@websocket_api.async_response
async def ws_get_session_stats(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get conversation session statistics."""
    try:
        # Get configuration
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "no_config", "No integration configured")
            return
        
        entry = entries[0]
        config = entry.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        
        # Initialize Gemini agent
        gemini_api_key = config.get(CONF_GEMINI_API_KEY)
        gemini_agent = GeminiAgent(hass, gemini_api_key, coordinator=coordinator)
        
        # Get stats
        stats = await gemini_agent.get_session_stats()
        
        connection.send_result(msg["id"], stats)
    
    except Exception as err:
        _LOGGER.error("WebSocket get_session_stats error: %s", err)
        connection.send_error(msg["id"], "get_stats_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "voice_assistant_gemini/preview_voice",
    vol.Required("voice_name"): cv.string,
    vol.Optional("text", default="Hello! This is a preview of the selected voice."): cv.string,
    vol.Optional("emotion", default=DEFAULT_EMOTION): cv.string,
    vol.Optional("tone_style", default=DEFAULT_TONE_STYLE): cv.string,
    vol.Optional("speaking_rate", default=DEFAULT_SPEAKING_RATE): vol.All(
        vol.Coerce(float), vol.Range(min=0.25, max=4.0)
    ),
    vol.Optional("pitch", default=DEFAULT_PITCH): vol.All(
        vol.Coerce(float), vol.Range(min=-20.0, max=20.0)
    ),
    vol.Optional("volume_gain_db", default=DEFAULT_VOLUME_GAIN_DB): vol.All(
        vol.Coerce(float), vol.Range(min=-96.0, max=16.0)
    ),
    vol.Optional("api_key"): cv.string,
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
    vol.Optional("provider", default=DEFAULT_TTS_PROVIDER): cv.string,
})
@websocket_api.async_response
async def ws_preview_voice(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Preview a voice by generating audio."""
    try:
        # Get parameters
        voice_name = msg["voice_name"]
        text = msg.get("text", "Hello! This is a preview of the selected voice.")
        emotion = msg.get("emotion", DEFAULT_EMOTION)
        tone_style = msg.get("tone_style", DEFAULT_TONE_STYLE)
        speaking_rate = msg.get("speaking_rate", DEFAULT_SPEAKING_RATE)
        pitch = msg.get("pitch", DEFAULT_PITCH)
        volume_gain_db = msg.get("volume_gain_db", DEFAULT_VOLUME_GAIN_DB)
        language = msg.get("language", DEFAULT_LANGUAGE)
        provider = msg.get("provider", DEFAULT_TTS_PROVIDER)
        api_key = msg.get("api_key")
        
        # If no API key provided, try to get from existing config
        if not api_key:
            entries = hass.config_entries.async_entries(DOMAIN)
            if not entries:
                connection.send_error(msg["id"], "no_config", "No integration configured and no API key provided")
                return
            
            entry = entries[0]
            config = entry.data
            api_key = config.get(CONF_TTS_API_KEY) or config.get(CONF_GEMINI_API_KEY)
        
        if not api_key:
            connection.send_error(msg["id"], "no_api_key", "No API key available")
            return
        
        # Enhance text with emotion and tone styling
        enhanced_text = text
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
        
        # Apply styling if instructions exist
        if style_instructions:
            enhanced_text = f"Please speak {', '.join(style_instructions)}: {text}"
        
        # Initialize TTS client
        tts_client = TTSClient(hass, api_key, language, provider)
        
        # Synthesize voice preview
        audio_data = await tts_client.synthesize(
            text=enhanced_text,
            voice=voice_name,
            speaking_rate=speaking_rate,
            pitch=pitch,
            volume_gain_db=volume_gain_db,
            ssml=False
        )
        
        # Convert to base64 for transmission
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        connection.send_result(msg["id"], {
            "voice_name": voice_name,
            "emotion": emotion,
            "tone_style": tone_style,
            "speaking_rate": speaking_rate,
            "pitch": pitch,
            "volume_gain_db": volume_gain_db,
            "language": language,
            "provider": provider,
            "audio_data": audio_base64,
            "text": text,
            "enhanced_text": enhanced_text,
        })
    
    except Exception as err:
        _LOGGER.error("WebSocket preview_voice error: %s", err)
        connection.send_error(msg["id"], "preview_voice_failed", str(err)) 