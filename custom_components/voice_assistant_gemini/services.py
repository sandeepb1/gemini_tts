"""Services for Voice Assistant Gemini integration."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEFAULT_LANGUAGE,
    CONF_DEFAULT_VOICE,
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
    DEFAULT_STT_PROVIDER,
    DEFAULT_TEMPERATURE,
    DEFAULT_TTS_PROVIDER,
    DEFAULT_VOLUME_GAIN_DB,
    DOMAIN,
    EVENT_RESPONSE,
    EVENT_STT_RESULT,
    MEDIA_DIR,
    SERVICE_CONVERSE,
    SERVICE_STT,
    SERVICE_TTS,
)
from .conversation import GeminiAgent
from .stt import STTClient
from .tts import TTSClient

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_STT_SCHEMA = vol.Schema({
    vol.Optional("source"): cv.string,
    vol.Optional("audio_data"): cv.string,
    vol.Optional("session_id"): cv.string,
    vol.Optional("language", default=DEFAULT_LANGUAGE): cv.string,
    vol.Optional("provider", default=DEFAULT_STT_PROVIDER): cv.string,
})

SERVICE_TTS_SCHEMA = vol.Schema({
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

SERVICE_CONVERSE_SCHEMA = vol.Schema({
    vol.Optional("text"): cv.string,
    vol.Optional("audio_data"): cv.string,
    vol.Optional("source"): cv.string,
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


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Voice Assistant Gemini."""
    
    try:
        _LOGGER.debug("Setting up Voice Assistant Gemini services")
    
        async def async_handle_stt(call: ServiceCall) -> None:
            """Handle STT service call."""
            try:
                # Get configuration from the first available entry
                entries = hass.config_entries.async_entries(DOMAIN)
                if not entries:
                    _LOGGER.error("No Voice Assistant Gemini integration configured")
                    return
                
                entry = entries[0]  # Use first entry
                config = entry.data
                
                # Get parameters
                source = call.data.get("source")
                audio_data = call.data.get("audio_data")
                session_id = call.data.get("session_id", str(uuid.uuid4()))
                language = call.data.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
                provider = call.data.get("provider", config.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER))
                
                # Get audio data
                if source:
                    audio_bytes = await _get_audio_from_source(hass, source)
                elif audio_data:
                    import base64
                    audio_bytes = base64.b64decode(audio_data)
                else:
                    _LOGGER.error("No audio source or data provided")
                    return
                
                # Initialize STT client
                api_key = config.get(CONF_STT_API_KEY) or config.get(CONF_GEMINI_API_KEY)
                stt_client = STTClient(hass, api_key, language, provider)
                
                # Transcribe audio
                transcript = await stt_client.transcribe(audio_bytes)
                
                # Fire event
                hass.bus.async_fire(EVENT_STT_RESULT, {
                    "session_id": session_id,
                    "text": transcript,
                    "language": language,
                    "provider": provider,
                    "source": source,
                })
                
                _LOGGER.info("STT transcription completed for session %s", session_id)
            
            except Exception as err:
                _LOGGER.error("STT service error: %s", err)
                hass.bus.async_fire(EVENT_STT_RESULT, {
                    "session_id": session_id,
                    "error": str(err),
                })

        async def async_handle_tts(call: ServiceCall) -> None:
            """Handle TTS service call."""
            try:
                # Get configuration from the first available entry
                entries = hass.config_entries.async_entries(DOMAIN)
                if not entries:
                    _LOGGER.error("No Voice Assistant Gemini integration configured")
                    return
                
                entry = entries[0]  # Use first entry
                config = entry.data
                
                # Get parameters
                text = call.data["text"]
                voice = call.data.get("voice", config.get(CONF_DEFAULT_VOICE, ""))
                language = call.data.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
                provider = call.data.get("provider", config.get(CONF_TTS_PROVIDER, DEFAULT_TTS_PROVIDER))
                speaking_rate = call.data.get("speaking_rate", config.get(CONF_SPEAKING_RATE, DEFAULT_SPEAKING_RATE))
                pitch = call.data.get("pitch", config.get(CONF_PITCH, DEFAULT_PITCH))
                volume_gain_db = call.data.get("volume_gain_db", config.get(CONF_VOLUME_GAIN_DB, DEFAULT_VOLUME_GAIN_DB))
                ssml = call.data.get("ssml", config.get(CONF_SSML, DEFAULT_SSML))
                session_id = call.data.get("session_id", str(uuid.uuid4()))
                
                # Initialize TTS client
                api_key = config.get(CONF_TTS_API_KEY) or config.get(CONF_GEMINI_API_KEY)
                tts_client = TTSClient(hass, api_key, language, provider)
                
                # Synthesize speech
                audio_bytes = await tts_client.synthesize(
                    text, voice, speaking_rate, pitch, volume_gain_db, ssml
                )
                
                # Save audio file
                media_path = await _save_audio_file(hass, audio_bytes, session_id)
                
                # Return media content ID
                call.async_set_result({
                    "media_content_id": f"/media/{MEDIA_DIR}/{Path(media_path).name}",
                    "media_content_type": "audio/mp3",
                    "session_id": session_id,
                    "text": text,
                    "voice": voice,
                    "language": language,
                    "provider": provider,
                })
                
                _LOGGER.info("TTS synthesis completed for session %s", session_id)
            
            except Exception as err:
                _LOGGER.error("TTS service error: %s", err)
                call.async_set_result({"error": str(err)})

        async def async_handle_converse(call: ServiceCall) -> None:
            """Handle conversation service call."""
            try:
                # Get configuration from the first available entry
                entries = hass.config_entries.async_entries(DOMAIN)
                if not entries:
                    _LOGGER.error("No Voice Assistant Gemini integration configured")
                    return
                
                entry = entries[0]  # Use first entry
                config = entry.data
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                
                # Get parameters
                text = call.data.get("text")
                audio_data = call.data.get("audio_data")
                source = call.data.get("source")
                session_id = call.data.get("session_id", str(uuid.uuid4()))
                system_prompt = call.data.get("system_prompt")
                model = call.data.get("model", config.get(CONF_GEMINI_MODEL, DEFAULT_GEMINI_MODEL))
                temperature = call.data.get("temperature", config.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
                max_tokens = call.data.get("max_tokens", config.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
                voice_response = call.data.get("voice_response", True)
                language = call.data.get("language", config.get(CONF_DEFAULT_LANGUAGE, DEFAULT_LANGUAGE))
                
                # Get text input
                if not text and (audio_data or source):
                    # Transcribe audio first
                    if source:
                        audio_bytes = await _get_audio_from_source(hass, source)
                    else:
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                    
                    # Initialize STT client
                    stt_api_key = config.get(CONF_STT_API_KEY) or config.get(CONF_GEMINI_API_KEY)
                    stt_provider = config.get(CONF_STT_PROVIDER, DEFAULT_STT_PROVIDER)
                    stt_client = STTClient(hass, stt_api_key, language, stt_provider)
                    
                    text = await stt_client.transcribe(audio_bytes)
                    
                    # Fire STT event
                    hass.bus.async_fire(EVENT_STT_RESULT, {
                        "session_id": session_id,
                        "text": text,
                        "language": language,
                        "provider": stt_provider,
                    })
                
                if not text:
                    _LOGGER.error("No text input provided for conversation")
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
                
                # Generate voice response if requested
                audio_url = None
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
                    
                    # Save audio file
                    media_path = await _save_audio_file(hass, audio_bytes, session_id)
                    audio_url = f"/media/{MEDIA_DIR}/{Path(media_path).name}"
                
                # Fire response event
                hass.bus.async_fire(EVENT_RESPONSE, {
                    "session_id": session_id,
                    "user_text": text,
                    "response_text": response_text,
                    "audio_url": audio_url,
                    "metadata": metadata,
                    "language": language,
                })
                
                # Return result
                result = {
                    "session_id": session_id,
                    "user_text": text,
                    "response_text": response_text,
                    "metadata": metadata,
                }
                
                if audio_url:
                    result.update({
                        "audio_url": audio_url,
                        "media_content_id": audio_url,
                        "media_content_type": "audio/mp3",
                    })
                
                call.async_set_result(result)
                
                _LOGGER.info("Conversation completed for session %s", session_id)
            
            except Exception as err:
                _LOGGER.error("Conversation service error: %s", err)
                call.async_set_result({"error": str(err)})

        # Register services
        hass.services.async_register(
            DOMAIN, SERVICE_STT, async_handle_stt, schema=SERVICE_STT_SCHEMA
        )
        
        hass.services.async_register(
            DOMAIN, SERVICE_TTS, async_handle_tts, schema=SERVICE_TTS_SCHEMA
        )
        
        hass.services.async_register(
            DOMAIN, SERVICE_CONVERSE, async_handle_converse, schema=SERVICE_CONVERSE_SCHEMA
        )
        
        _LOGGER.info("Voice Assistant Gemini services registered")
    
    except Exception as err:
        _LOGGER.error("Failed to set up Voice Assistant Gemini services: %s", err, exc_info=True)
        raise


async def _get_audio_from_source(hass: HomeAssistant, source: str) -> bytes:
    """Get audio data from a source (URL, file path, or entity)."""
    try:
        if source.startswith("http"):
            # Download from URL
            session = async_get_clientsession(hass)
            async with session.get(source) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    raise RuntimeError(f"Failed to download audio: HTTP {response.status}")
        
        elif source.startswith("/"):
            # Read from file path
            with open(source, "rb") as f:
                return f.read()
        
        elif "." in source:
            # Assume it's an entity ID
            state = hass.states.get(source)
            if state and state.attributes.get("entity_picture"):
                # Get media URL from entity
                media_url = state.attributes["entity_picture"]
                if media_url.startswith("/"):
                    media_url = f"{hass.config.api.base_url}{media_url}"
                
                session = async_get_clientsession(hass)
                async with session.get(media_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise RuntimeError(f"Failed to download media: HTTP {response.status}")
            else:
                raise RuntimeError(f"Entity {source} has no media content")
        
        else:
            raise ValueError(f"Invalid audio source: {source}")
    
    except Exception as err:
        _LOGGER.error("Error getting audio from source %s: %s", source, err)
        raise


async def _save_audio_file(hass: HomeAssistant, audio_bytes: bytes, session_id: str) -> str:
    """Save audio bytes to a media file."""
    try:
        # Ensure media directory exists
        media_dir = Path(hass.config.path("www", MEDIA_DIR))
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        filename = f"{session_id}_{uuid.uuid4().hex[:8]}.mp3"
        file_path = media_dir / filename
        
        # Write audio data
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        
        _LOGGER.debug("Saved audio file: %s (%d bytes)", file_path, len(audio_bytes))
        return str(file_path)
    
    except Exception as err:
        _LOGGER.error("Error saving audio file: %s", err)
        raise 