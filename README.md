# Voice Assistant Gemini for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/your-username/voice_assistant_gemini?style=for-the-badge)](https://github.com/your-username/voice_assistant_gemini/releases)
[![GitHub](https://img.shields.io/github/license/your-username/voice_assistant_gemini?style=for-the-badge)](LICENSE)

A comprehensive Home Assistant custom integration that provides advanced voice assistant capabilities using Google Gemini AI for intelligent conversations, combined with multiple Speech-to-Text (STT) and Text-to-Speech (TTS) providers.

## ✨ Features

### 🎤 Speech Recognition (STT)
- **Google Cloud Speech-to-Text**: Premium cloud-based recognition with high accuracy
- **Vosk**: Offline speech recognition for privacy-conscious users
- **Streaming support** for large audio files
- **Multiple language support** with automatic detection
- **Audio format validation** and preprocessing

### 🔊 Text-to-Speech (TTS)
- **Google Cloud Text-to-Speech**: Natural-sounding voices with SSML support
- **Amazon Polly**: Wide variety of voices including neural models
- **Azure Cognitive Services**: Microsoft's TTS with custom voice support
- **Voice parameter control**: Rate, pitch, volume, and language selection
- **Voice caching** for improved performance

### 🤖 AI Conversation
- **Google Gemini AI**: Advanced conversational AI with context awareness
- **Session management**: Persistent conversation history across interactions
- **System prompts**: Customizable AI personality and behavior
- **History truncation**: Automatic management of conversation length
- **Conversation summaries**: AI-generated summaries of chat sessions

### 🎨 Modern Frontend
- **Voice Assistant Card**: Beautiful Lovelace card with voice recording
- **Real-time status**: Visual feedback during recording and processing
- **Conversation UI**: Chat-like interface with message history
- **Settings panel**: Easy configuration of voice parameters
- **Responsive design**: Works on desktop and mobile devices

### 🔧 Advanced Features
- **Multiple provider fallback**: Automatic failover between services
- **Session persistence**: Conversations survive Home Assistant restarts
- **WebSocket API**: Real-time communication for responsive UI
- **Comprehensive logging**: Detailed logs for troubleshooting
- **Retry mechanisms**: Automatic retry with exponential backoff
- **Security**: API key validation and secure storage

## 📦 Installation

### HACS (Recommended)

1. **Install HACS** if you haven't already
2. **Add this repository** to HACS:
   - Go to HACS → Integrations
   - Click the "+" button
   - Search for "Voice Assistant Gemini"
   - Click "Install"
3. **Restart Home Assistant**
4. **Add the integration**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Voice Assistant Gemini"

### Manual Installation

1. **Download** the latest release from the [releases page](https://github.com/your-username/voice_assistant_gemini/releases)
2. **Extract** the archive to `custom_components/voice_assistant_gemini/` in your Home Assistant config directory
3. **Restart Home Assistant**
4. **Add the integration** via the UI

## 🔑 API Keys Setup

### Google Gemini API Key (Required)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the key for configuration

### Google Cloud (Optional - for STT/TTS)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Speech-to-Text and Text-to-Speech APIs
4. Create a service account key (JSON format)
5. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable or upload the JSON content

### Amazon Polly (Optional - for TTS)
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Create an IAM user with Polly access
3. Generate access keys
4. Use the access key ID and secret

### Azure TTS (Optional - for TTS)
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create a Cognitive Services resource
3. Get the API key and region

## ⚙️ Configuration

### Basic Configuration

After adding the integration, you'll be guided through the setup:

1. **API Keys**: Enter your Google Gemini API key (required) and optional provider keys
2. **Language Settings**: Choose your default language (e.g., `en-US`, `es-ES`, `fr-FR`)
3. **Provider Selection**: Choose STT and TTS providers
4. **Voice Settings**: Configure speech rate, pitch, and volume
5. **AI Settings**: Set Gemini model, temperature, and token limits

### Advanced Configuration

The integration supports extensive customization through the Home Assistant UI:

```yaml
# Configuration.yaml (for reference - use UI instead)
voice_assistant_gemini:
  gemini_api_key: "your_gemini_api_key"
  default_language: "en-US"
  stt_provider: "google_cloud"  # or "vosk"
  tts_provider: "google_cloud"  # or "amazon_polly", "azure_tts"
  speaking_rate: 1.0
  pitch: 0.0
  volume_gain_db: 0.0
  ssml: false
  gemini_model: "gemini-pro"
  temperature: 0.7
  max_tokens: 2048
  enable_transcript_storage: true
  transcript_retention_days: 30
```

## 🎮 Usage

### Lovelace Card

Add the voice assistant card to your dashboard:

```yaml
type: custom:voice-assistant-gemini-card
title: "Voice Assistant"
show_settings: true
theme: "auto"  # or "light", "dark"
```

### Services

The integration provides several services for automation:

#### `voice_assistant_gemini.transcribe`
Convert speech to text:

```yaml
service: voice_assistant_gemini.transcribe
data:
  audio_data: "{{ audio_data_base64 }}"
  language: "en-US"  # optional
  provider: "google_cloud"  # optional
```

#### `voice_assistant_gemini.synthesize`
Convert text to speech:

```yaml
service: voice_assistant_gemini.synthesize
data:
  text: "Hello, how can I help you today?"
  voice: "en-US-Standard-A"  # optional
  speaking_rate: 1.2  # optional
  language: "en-US"  # optional
  provider: "google_cloud"  # optional
```

#### `voice_assistant_gemini.converse`
Have a conversation with Gemini:

```yaml
service: voice_assistant_gemini.converse
data:
  message: "What's the weather like today?"
  session_id: "user_123"  # optional
  system_prompt: "You are a helpful assistant"  # optional
```

### WebSocket API

For real-time communication (used by the frontend card):

```javascript
// List available voices
connection.sendMessage({
  type: "voice_assistant_gemini/list_voices",
  provider: "google_cloud",
  language: "en-US"
});

// Transcribe audio
connection.sendMessage({
  type: "voice_assistant_gemini/transcribe",
  audio_data: base64AudioData,
  language: "en-US"
});

// Synthesize speech
connection.sendMessage({
  type: "voice_assistant_gemini/synthesize",
  text: "Hello world",
  voice: "en-US-Standard-A"
});
```

## 🎛️ Voice Parameters

### Speaking Rate
- **Range**: 0.25 to 4.0
- **Default**: 1.0 (normal speed)
- **Example**: 1.5 = 50% faster, 0.75 = 25% slower

### Pitch
- **Range**: -20.0 to 20.0 semitones
- **Default**: 0.0 (natural pitch)
- **Example**: 5.0 = higher pitch, -5.0 = lower pitch

### Volume Gain
- **Range**: -96.0 to 16.0 dB
- **Default**: 0.0 (no change)
- **Example**: 6.0 = louder, -6.0 = quieter

## 🌍 Supported Languages

### Google Cloud
- English (US, UK, AU, IN)
- Spanish (ES, MX, AR)
- French (FR, CA)
- German, Italian, Portuguese
- Japanese, Korean, Chinese (Mandarin)
- And many more...

### Amazon Polly
- 29+ languages
- 60+ voices
- Neural voices available

### Vosk (Offline)
- English, Spanish, French, German
- Russian, Chinese, Italian
- Portuguese, Dutch, Turkish
- And more (requires model download)

## 🔧 Troubleshooting

### Common Issues

#### "API Key Invalid" Error
- Verify your Google Gemini API key is correct
- Check if the API is enabled in Google Cloud Console
- Ensure you have sufficient quota

#### STT Not Working
- Check microphone permissions in your browser
- Verify audio format (WAV, FLAC, MP3 supported)
- Check network connectivity to cloud services

#### TTS No Sound
- Verify browser audio permissions
- Check Home Assistant media player setup
- Test with different TTS providers

#### Offline STT (Vosk) Issues
- Download required language models
- Check available disk space
- Verify Python dependencies are installed

### Debugging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.voice_assistant_gemini: debug
```

### Log Analysis

Common log messages and solutions:

- **"Connection timeout"**: Check internet connectivity
- **"Quota exceeded"**: Verify API usage limits
- **"Audio format not supported"**: Convert to supported format
- **"Session not found"**: Check session management settings

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/voice_assistant_gemini.git
   cd voice_assistant_gemini
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

4. **Format code**:
   ```bash
   black custom_components/
   isort custom_components/
   ```

### Submitting Changes

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Add** tests for new functionality
5. **Submit** a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google** for Gemini AI and Cloud services
- **Home Assistant** community for the amazing platform
- **Contributors** who help improve this integration
- **HACS** for simplifying custom component distribution

## 📧 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/your-username/voice_assistant_gemini/issues)
- **Home Assistant Community**: [Discussion forum](https://community.home-assistant.io/)
- **Documentation**: This README and inline code documentation

## 🔄 Changelog

### Version 1.0.0
- Initial release
- Google Gemini AI integration
- Multiple STT/TTS providers
- Modern Lovelace card
- WebSocket API
- Session management
- Comprehensive testing

---

**Made with ❤️ for the Home Assistant community** 