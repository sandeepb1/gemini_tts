"""Constants for the Voice Assistant Gemini integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "voice_assistant_gemini"

# Configuration keys
CONF_GEMINI_API_KEY: Final = "gemini_api_key"
CONF_STT_API_KEY: Final = "stt_api_key"
CONF_TTS_API_KEY: Final = "tts_api_key"
CONF_DEFAULT_LANGUAGE: Final = "default_language"
CONF_STT_PROVIDER: Final = "stt_provider"
CONF_TTS_PROVIDER: Final = "tts_provider"
CONF_DEFAULT_VOICE: Final = "default_voice"
CONF_SPEAKING_RATE: Final = "speaking_rate"
CONF_PITCH: Final = "pitch"
CONF_VOLUME_GAIN_DB: Final = "volume_gain_db"
CONF_SSML: Final = "ssml"
CONF_GEMINI_MODEL: Final = "gemini_model"
CONF_TEMPERATURE: Final = "temperature"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_LOGGING_LEVEL: Final = "logging_level"
CONF_ENABLE_TRANSCRIPT_STORAGE: Final = "enable_transcript_storage"
CONF_TRANSCRIPT_RETENTION_DAYS: Final = "transcript_retention_days"

# Default values
DEFAULT_LANGUAGE: Final = "en-US"
DEFAULT_STT_PROVIDER: Final = "google_cloud"
DEFAULT_TTS_PROVIDER: Final = "google_cloud"
DEFAULT_SPEAKING_RATE: Final = 1.0
DEFAULT_PITCH: Final = 0.0
DEFAULT_VOLUME_GAIN_DB: Final = 0.0
DEFAULT_SSML: Final = False
DEFAULT_GEMINI_MODEL: Final = "gemini-pro"
DEFAULT_TEMPERATURE: Final = 0.7
DEFAULT_MAX_TOKENS: Final = 2048
DEFAULT_LOGGING_LEVEL: Final = "INFO"
DEFAULT_TRANSCRIPT_STORAGE: Final = True
DEFAULT_TRANSCRIPT_RETENTION_DAYS: Final = 30

# Service names
SERVICE_STT: Final = "stt"
SERVICE_TTS: Final = "tts"
SERVICE_CONVERSE: Final = "converse"

# Event names
EVENT_STT_RESULT: Final = "voice_assistant_gemini_stt"
EVENT_RESPONSE: Final = "voice_assistant_gemini_response"

# Storage keys
STORAGE_KEY: Final = "voice_assistant_gemini_storage"
STORAGE_VERSION: Final = 1

# Supported languages
SUPPORTED_LANGUAGES: Final = ["en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "it-IT", "pt-BR", "ja-JP", "ko-KR", "zh-CN"]

# Supported STT providers
STT_PROVIDERS: Final = ["google_cloud", "vosk"]

# Supported TTS providers
TTS_PROVIDERS: Final = ["google_cloud", "amazon_polly", "azure_tts"]

# Gemini models
GEMINI_MODELS: Final = ["gemini-pro", "gemini-pro-vision", "gemini-ultra"]

# Logging levels
LOGGING_LEVELS: Final = ["DEBUG", "INFO", "WARNING", "ERROR"]

# Audio settings
AUDIO_SAMPLE_RATE: Final = 16000
AUDIO_CHANNELS: Final = 1
AUDIO_SAMPLE_WIDTH: Final = 2  # 16-bit

# Media directory
MEDIA_DIR: Final = "voice_assistant_gemini"

# Timeout settings
API_TIMEOUT: Final = 30
RETRY_ATTEMPTS: Final = 3
RETRY_BACKOFF_FACTOR: Final = 2 