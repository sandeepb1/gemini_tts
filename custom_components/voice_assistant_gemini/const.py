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
CONF_EMOTION: Final = "emotion"
CONF_TONE_STYLE: Final = "tone_style"
CONF_GEMINI_MODEL: Final = "gemini_model"
CONF_CONVERSATION_MODEL: Final = "conversation_model"
CONF_TTS_MODEL: Final = "tts_model"
CONF_STT_MODEL: Final = "stt_model"
CONF_TEMPERATURE: Final = "temperature"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_LOGGING_LEVEL: Final = "logging_level"
CONF_ENABLE_TRANSCRIPT_STORAGE: Final = "enable_transcript_storage"
CONF_TRANSCRIPT_RETENTION_DAYS: Final = "transcript_retention_days"

# Default values
DEFAULT_LANGUAGE: Final = "en-US"
DEFAULT_STT_PROVIDER: Final = "google_cloud"
DEFAULT_TTS_PROVIDER: Final = "gemini_tts"
DEFAULT_SPEAKING_RATE: Final = 1.0
DEFAULT_PITCH: Final = 0.0
DEFAULT_VOLUME_GAIN_DB: Final = 0.0
DEFAULT_SSML: Final = False
DEFAULT_EMOTION: Final = "neutral"
DEFAULT_TONE_STYLE: Final = "normal"
DEFAULT_GEMINI_MODEL: Final = "gemini-2.0-flash"
DEFAULT_CONVERSATION_MODEL: Final = "gemini-2.0-flash"
DEFAULT_TTS_MODEL: Final = "gemini-2.5-flash-preview-tts"
DEFAULT_STT_MODEL: Final = "gemini-2.0-flash"
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
TTS_PROVIDERS: Final = ["gemini_tts", "google_cloud", "amazon_polly", "azure_tts"]

# Gemini models
GEMINI_MODELS: Final = ["gemini-2.0-flash", "gemini-2.5-flash-preview-tts", "gemini-pro", "gemini-pro-vision", "gemini-ultra"]

# Conversation models with recommendations
CONVERSATION_MODELS: Final = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Recommended - Fast & Accurate)",
    "gemini-pro": "Gemini Pro (Balanced Performance)",
    "gemini-ultra": "Gemini Ultra (Highest Quality, Slower)",
}

# TTS models with recommendations
TTS_MODELS: Final = {
    "gemini-2.5-flash-preview-tts": "Gemini 2.5 Flash TTS (Recommended - Natural Voices)",
    "gemini-2.0-flash": "Gemini 2.0 Flash (Basic TTS)",
}

# STT models with recommendations
STT_MODELS: Final = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Recommended - Fast Recognition)",
    "gemini-pro": "Gemini Pro (Higher Accuracy)",
}

# Voice descriptions for better UX
GEMINI_VOICE_DESCRIPTIONS: Final = {
    "Kore": "Kore - Firm and confident tone",
    "Puck": "Puck - Upbeat and energetic",
    "Zephyr": "Zephyr - Bright and clear",
    "Charon": "Charon - Informative and professional",
    "Fenrir": "Fenrir - Excitable and dynamic",
    "Leda": "Leda - Youthful and friendly",
    "Orus": "Orus - Firm and authoritative",
    "Aoede": "Aoede - Breezy and casual",
    "Callirrhoe": "Callirrhoe - Easy-going and relaxed",
    "Autonoe": "Autonoe - Bright and articulate",
    "Enceladus": "Enceladus - Breathy and soft",
    "Iapetus": "Iapetus - Clear and precise",
    "Umbriel": "Umbriel - Easy-going and smooth",
    "Algieba": "Algieba - Smooth and polished",
    "Despina": "Despina - Smooth and gentle",
    "Erinome": "Erinome - Clear and direct",
    "Algenib": "Algenib - Gravelly and distinctive",
    "Rasalgethi": "Rasalgethi - Informative and knowledgeable",
    "Laomedeia": "Laomedeia - Upbeat and lively",
    "Achernar": "Achernar - Soft and warm",
    "Alnilam": "Alnilam - Firm and steady",
    "Schedar": "Schedar - Even and balanced",
    "Gacrux": "Gacrux - Mature and experienced",
    "Pulcherrima": "Pulcherrima - Forward and confident",
    "Achird": "Achird - Friendly and approachable",
    "Zubenelgenubi": "Zubenelgenubi - Casual and conversational",
    "Vindemiatrix": "Vindemiatrix - Gentle and soothing",
    "Sadachbia": "Sadachbia - Lively and animated",
    "Sadaltager": "Sadaltager - Knowledgeable and wise",
    "Sulafat": "Sulafat - Warm and inviting",
}

# Logging levels
LOGGING_LEVELS: Final = ["DEBUG", "INFO", "WARNING", "ERROR"]

# Available emotions for TTS
EMOTION_OPTIONS: Final = {
    "neutral": "Neutral - Standard delivery",
    "happy": "Happy - Upbeat and cheerful",
    "sad": "Sad - Somber and melancholic", 
    "excited": "Excited - Energetic and enthusiastic",
    "calm": "Calm - Relaxed and peaceful",
    "confident": "Confident - Assertive and strong",
    "friendly": "Friendly - Warm and approachable",
    "professional": "Professional - Business-like and formal"
}

# Available tone styles for TTS
TONE_STYLE_OPTIONS: Final = {
    "normal": "Normal - Standard speaking style",
    "casual": "Casual - Relaxed conversational style", 
    "formal": "Formal - Professional and structured",
    "storytelling": "Storytelling - Narrative and engaging",
    "informative": "Informative - Clear and educational",
    "conversational": "Conversational - Natural dialogue style",
    "announcement": "Announcement - Clear and attention-grabbing",
    "customer_service": "Customer Service - Helpful and polite"
}

# Available Gemini TTS voices
GEMINI_VOICES: Final = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe",
    "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", 
    "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", 
    "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
]

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