class VoiceAssistantGeminiCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.sessionId = null;
    this.conversationHistory = [];
    this.config = {};
  }

  setConfig(config) {
    if (!config) {
      throw new Error('Invalid configuration');
    }
    this.config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot.hasChildNodes()) {
      this.render();
    }
  }

  connectedCallback() {
    this.generateSessionId();
  }

  generateSessionId() {
    this.sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
  }

  render() {
    const title = this.config.title || 'Voice Assistant Gemini';
    const showControls = this.config.show_controls !== false;
    const showHistory = this.config.show_history !== false;
    const theme = this.config.theme || 'default';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --primary-color: #1976d2;
          --secondary-color: #f50057;
          --background-color: #fafafa;
          --surface-color: #ffffff;
          --text-primary: #212121;
          --text-secondary: #757575;
          --border-color: #e0e0e0;
          --success-color: #4caf50;
          --warning-color: #ff9800;
          --error-color: #f44336;
        }

        .card {
          background: var(--surface-color);
          border-radius: 16px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          padding: 24px;
          font-family: 'Roboto', sans-serif;
          color: var(--text-primary);
          max-width: 600px;
          margin: 0 auto;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--border-color);
        }

        .title {
          font-size: 1.5rem;
          font-weight: 500;
          color: var(--text-primary);
        }

        .status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--success-color);
        }

        .status-dot.listening {
          background: var(--warning-color);
          animation: pulse 1s infinite;
        }

        .status-dot.processing {
          background: var(--primary-color);
          animation: pulse 1s infinite;
        }

        .status-dot.error {
          background: var(--error-color);
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .conversation {
          max-height: 400px;
          overflow-y: auto;
          margin-bottom: 24px;
          padding: 16px;
          background: var(--background-color);
          border-radius: 12px;
          min-height: 100px;
        }

        .message {
          margin-bottom: 16px;
          display: flex;
          gap: 12px;
        }

        .message.user {
          flex-direction: row-reverse;
        }

        .message-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1rem;
          font-weight: 500;
          flex-shrink: 0;
        }

        .message.user .message-avatar {
          background: var(--primary-color);
          color: white;
        }

        .message.assistant .message-avatar {
          background: var(--secondary-color);
          color: white;
        }

        .message-content {
          background: white;
          padding: 12px 16px;
          border-radius: 18px;
          max-width: 70%;
          box-shadow: 0 1px 4px rgba(0,0,0,0.1);
          position: relative;
        }

        .message.user .message-content {
          background: var(--primary-color);
          color: white;
        }

        .message-text {
          margin: 0;
          line-height: 1.4;
        }

        .message-actions {
          margin-top: 8px;
          display: flex;
          gap: 8px;
        }

        .message-action {
          background: none;
          border: none;
          cursor: pointer;
          color: var(--text-secondary);
          font-size: 0.75rem;
          padding: 4px 8px;
          border-radius: 12px;
          transition: background-color 0.2s;
        }

        .message-action:hover {
          background: rgba(0,0,0,0.1);
        }

        .controls {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          align-items: center;
          justify-content: center;
        }

        .record-button {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          border: none;
          background: var(--primary-color);
          color: white;
          font-size: 1.5rem;
          cursor: pointer;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        .record-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(0,0,0,0.3);
        }

        .record-button.recording {
          background: var(--secondary-color);
          animation: pulse-button 1s infinite;
        }

        .record-button:disabled {
          background: var(--text-secondary);
          cursor: not-allowed;
          transform: none;
        }

        @keyframes pulse-button {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }

        .text-input-container {
          display: flex;
          gap: 8px;
          align-items: flex-end;
        }

        .text-input {
          flex: 1;
          padding: 12px 16px;
          border: 2px solid var(--border-color);
          border-radius: 24px;
          font-size: 1rem;
          resize: none;
          min-height: 20px;
          max-height: 100px;
          font-family: inherit;
          transition: border-color 0.2s;
        }

        .text-input:focus {
          outline: none;
          border-color: var(--primary-color);
        }

        .send-button {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          border: none;
          background: var(--primary-color);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .send-button:hover {
          background: #1565c0;
          transform: translateY(-1px);
        }

        .send-button:disabled {
          background: var(--text-secondary);
          cursor: not-allowed;
          transform: none;
        }

        .settings {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--border-color);
        }

        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }

        .setting-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .setting-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary);
        }

        .setting-input {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 8px;
          font-size: 0.875rem;
        }

        .error-message {
          background: var(--error-color);
          color: white;
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 0.875rem;
        }

        .hidden {
          display: none;
        }

        .loading {
          opacity: 0.6;
          pointer-events: none;
        }

        .transcript {
          font-style: italic;
          color: var(--text-secondary);
          font-size: 0.875rem;
          margin-top: 8px;
        }
      </style>

      <div class="card">
        <div class="header">
          <div class="title">${title}</div>
          <div class="status">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Ready</span>
          </div>
        </div>

        <div id="errorMessage" class="error-message hidden"></div>

        <div class="conversation" id="conversation">
          <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <p class="message-text">Hello! I'm your Voice Assistant powered by Google Gemini. You can speak to me or type your message below.</p>
            </div>
          </div>
        </div>

        ${showControls ? `
        <div class="controls">
          <button class="record-button" id="recordButton" title="Hold to record">
            🎤
          </button>
        </div>

        <div class="text-input-container">
          <textarea 
            class="text-input" 
            id="textInput" 
            placeholder="Type your message here or use the microphone above..."
            rows="1"
          ></textarea>
          <button class="send-button" id="sendButton" title="Send message">
            ➤
          </button>
        </div>
        ` : ''}

        ${showControls ? `
        <div class="settings">
          <div class="settings-grid">
            <div class="setting-group">
              <label class="setting-label">Voice</label>
              <select class="setting-input" id="voiceSelect">
                <option value="">Default</option>
              </select>
            </div>
            <div class="setting-group">
              <label class="setting-label">Language</label>
              <select class="setting-input" id="languageSelect">
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
                <option value="de-DE">German</option>
                <option value="fr-FR">French</option>
                <option value="es-ES">Spanish</option>
                <option value="it-IT">Italian</option>
              </select>
            </div>
            <div class="setting-group">
              <label class="setting-label">Speaking Rate</label>
              <input type="range" class="setting-input" id="speakingRate" min="0.25" max="4" step="0.25" value="1">
            </div>
          </div>
        </div>
        ` : ''}
      </div>
    `;

    this.setupEventListeners();
    this.loadVoices();
  }

  setupEventListeners() {
    const recordButton = this.shadowRoot.getElementById('recordButton');
    const sendButton = this.shadowRoot.getElementById('sendButton');
    const textInput = this.shadowRoot.getElementById('textInput');

    if (recordButton) {
      recordButton.addEventListener('mousedown', () => this.startRecording());
      recordButton.addEventListener('mouseup', () => this.stopRecording());
      recordButton.addEventListener('touchstart', () => this.startRecording());
      recordButton.addEventListener('touchend', () => this.stopRecording());
    }

    if (sendButton) {
      sendButton.addEventListener('click', () => this.sendMessage());
    }

    if (textInput) {
      textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      textInput.addEventListener('input', (e) => {
        this.autoResizeTextarea(e.target);
      });
    }
  }

  autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  }

  async loadVoices() {
    try {
      const result = await this._hass.callWS({
        type: 'voice_assistant_gemini/list_voices',
        language: this.shadowRoot.getElementById('languageSelect')?.value || 'en-US'
      });

      const voiceSelect = this.shadowRoot.getElementById('voiceSelect');
      if (voiceSelect && result.voices) {
        voiceSelect.innerHTML = '<option value="">Default</option>';
        result.voices.forEach(voice => {
          const option = document.createElement('option');
          option.value = voice.name;
          option.textContent = `${voice.name} (${voice.gender})`;
          voiceSelect.appendChild(option);
        });
      }
    } catch (error) {
      console.error('Failed to load voices:', error);
    }
  }

  async startRecording() {
    if (this.isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      this.audioChunks = [];
      this.isRecording = true;

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        this.processRecording();
      };

      this.mediaRecorder.start();
      this.updateStatus('listening', 'Listening...');

    } catch (error) {
      console.error('Failed to start recording:', error);
      this.showError('Microphone access denied or not available');
    }
  }

  stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) return;

    this.mediaRecorder.stop();
    this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    this.isRecording = false;
    this.updateStatus('processing', 'Processing...');
  }

  async processRecording() {
    try {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      const audioBuffer = await audioBlob.arrayBuffer();
      const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioBuffer)));

      await this.sendConversation(null, base64Audio);
    } catch (error) {
      console.error('Failed to process recording:', error);
      this.showError('Failed to process audio recording');
      this.updateStatus('idle', 'Ready');
    }
  }

  async sendMessage() {
    const textInput = this.shadowRoot.getElementById('textInput');
    const text = textInput?.value.trim();
    
    if (!text) return;

    textInput.value = '';
    this.autoResizeTextarea(textInput);
    
    await this.sendConversation(text);
  }

  async sendConversation(text = null, audioData = null) {
    try {
      this.updateStatus('processing', 'Processing...');
      
      if (text) {
        this.addMessage('user', text);
      }

      const result = await this._hass.callWS({
        type: 'voice_assistant_gemini/converse',
        text: text,
        audio_data: audioData,
        session_id: this.sessionId,
        voice_response: true,
        language: this.shadowRoot.getElementById('languageSelect')?.value || 'en-US'
      });

      if (result.response_text) {
        this.addMessage('assistant', result.response_text);
        
        if (result.audio_data) {
          this.playAudio(result.audio_data);
        }
      }

      this.updateStatus('idle', 'Ready');
    } catch (error) {
      console.error('Conversation error:', error);
      this.showError('Failed to process your request: ' + error.message);
      this.updateStatus('error', 'Error');
      setTimeout(() => this.updateStatus('idle', 'Ready'), 3000);
    }
  }

  addMessage(role, content) {
    const conversation = this.shadowRoot.getElementById('conversation');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    
    messageDiv.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <p class="message-text">${this.escapeHtml(content)}</p>
        ${role === 'assistant' ? `
          <div class="message-actions">
            <button class="message-action" onclick="this.getRootNode().host.speakText('${this.escapeHtml(content)}')">🔊</button>
            <button class="message-action" onclick="navigator.clipboard.writeText('${this.escapeHtml(content)}')">📋</button>
          </div>
        ` : ''}
      </div>
    `;
    
    conversation.appendChild(messageDiv);
    conversation.scrollTop = conversation.scrollHeight;
  }

  async speakText(text) {
    try {
      const result = await this._hass.callWS({
        type: 'voice_assistant_gemini/synthesize',
        text: text,
        voice: this.shadowRoot.getElementById('voiceSelect')?.value || '',
        speaking_rate: parseFloat(this.shadowRoot.getElementById('speakingRate')?.value || '1'),
        language: this.shadowRoot.getElementById('languageSelect')?.value || 'en-US'
      });

      if (result.audio_data) {
        this.playAudio(result.audio_data);
      }
    } catch (error) {
      console.error('TTS error:', error);
    }
  }

  playAudio(base64Audio) {
    try {
      const audio = new Audio('data:audio/mp3;base64,' + base64Audio);
      this.updateStatus('speaking', 'Speaking...');
      
      audio.onended = () => {
        this.updateStatus('idle', 'Ready');
      };
      
      audio.onerror = () => {
        this.updateStatus('idle', 'Ready');
      };
      
      audio.play();
    } catch (error) {
      console.error('Audio playback error:', error);
      this.updateStatus('idle', 'Ready');
    }
  }

  updateStatus(status, text) {
    const statusDot = this.shadowRoot.getElementById('statusDot');
    const statusText = this.shadowRoot.getElementById('statusText');
    const recordButton = this.shadowRoot.getElementById('recordButton');

    if (statusDot) {
      statusDot.className = `status-dot ${status}`;
    }
    
    if (statusText) {
      statusText.textContent = text;
    }

    if (recordButton) {
      if (status === 'listening') {
        recordButton.classList.add('recording');
      } else {
        recordButton.classList.remove('recording');
      }
      
      recordButton.disabled = status === 'processing';
    }
  }

  showError(message) {
    const errorElement = this.shadowRoot.getElementById('errorMessage');
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.classList.remove('hidden');
      setTimeout(() => {
        errorElement.classList.add('hidden');
      }, 5000);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  getCardSize() {
    return 6;
  }
}

customElements.define('voice-assistant-gemini-card', VoiceAssistantGeminiCard);

// Register the card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'voice-assistant-gemini-card',
  name: 'Voice Assistant Gemini Card',
  description: 'A voice-enabled chat interface for Google Gemini AI assistant'
});

// Add to Lovelace card registry
if (window.loadCardHelpers) {
  window.loadCardHelpers().then(() => {
    if (window.customCards && !window.customCards.find(card => card.type === 'voice-assistant-gemini-card')) {
      window.customCards.push({
        type: 'voice-assistant-gemini-card',
        name: 'Voice Assistant Gemini Card',
        description: 'A voice-enabled chat interface for Google Gemini AI assistant'
      });
    }
  });
} 