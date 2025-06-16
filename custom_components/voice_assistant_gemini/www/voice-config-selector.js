/**
 * Voice Configuration Selector for Voice Assistant Gemini
 * Used in configuration flow to preview and select voices
 */

class VoiceConfigSelector extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.voices = [
            "Kore", "Puck", "Zephyr", "Charon", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe",
            "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", 
            "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", 
            "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ];
        this.voiceDescriptions = {
            "Kore": "Firm and confident tone",
            "Puck": "Upbeat and energetic",
            "Zephyr": "Bright and clear",
            "Charon": "Informative and professional",
            "Fenrir": "Excitable and dynamic",
            "Leda": "Youthful and friendly",
            "Orus": "Firm and authoritative",
            "Aoede": "Breezy and casual",
            "Callirrhoe": "Easy-going and relaxed",
            "Autonoe": "Bright and articulate",
            "Enceladus": "Breathy and soft",
            "Iapetus": "Clear and precise",
            "Umbriel": "Easy-going and smooth",
            "Algieba": "Smooth and polished",
            "Despina": "Smooth and gentle",
            "Erinome": "Clear and direct",
            "Algenib": "Gravelly and distinctive",
            "Rasalgethi": "Informative and knowledgeable",
            "Laomedeia": "Upbeat and lively",
            "Achernar": "Soft and warm",
            "Alnilam": "Firm and steady",
            "Schedar": "Even and balanced",
            "Gacrux": "Mature and experienced",
            "Pulcherrima": "Forward and confident",
            "Achird": "Friendly and approachable",
            "Zubenelgenubi": "Casual and conversational",
            "Vindemiatrix": "Gentle and soothing",
            "Sadachbia": "Lively and animated",
            "Sadaltager": "Knowledgeable and wise",
            "Sulafat": "Warm and inviting"
        };
        this.selectedVoice = "Kore";
        this.currentAudio = null;
        this.isPlaying = false;
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        
        // Get initial selected voice from the form if available
        const selectElement = document.querySelector('select[name="default_voice"]');
        if (selectElement && selectElement.value) {
            this.selectedVoice = selectElement.value;
            this.updateSelectedCard();
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--mdc-typography-body1-font-family, Roboto, sans-serif);
                    margin: 16px 0;
                }
                
                .voice-selector-container {
                    border: 1px solid var(--divider-color, #e0e0e0);
                    border-radius: 8px;
                    padding: 16px;
                    background: var(--card-background-color, #fff);
                }
                
                .header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 16px;
                }
                
                .title {
                    font-size: 1.1em;
                    font-weight: 500;
                    color: var(--primary-text-color, #212121);
                    margin: 0;
                }
                
                .preview-all-btn {
                    padding: 6px 12px;
                    background: var(--primary-color, #03a9f4);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.9em;
                    font-weight: 500;
                    transition: background 0.2s ease;
                }
                
                .preview-all-btn:hover {
                    background: var(--dark-primary-color, #0288d1);
                }
                
                .search-container {
                    margin-bottom: 16px;
                }
                
                .search-input {
                    width: 100%;
                    padding: 8px 12px;
                    border: 1px solid var(--divider-color, #e0e0e0);
                    border-radius: 4px;
                    background: var(--card-background-color, #fff);
                    color: var(--primary-text-color, #212121);
                    font-family: inherit;
                    box-sizing: border-box;
                }
                
                .voice-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 12px;
                    max-height: 400px;
                    overflow-y: auto;
                }
                
                .voice-card {
                    border: 2px solid var(--divider-color, #e0e0e0);
                    border-radius: 8px;
                    padding: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background: var(--card-background-color, #fff);
                    position: relative;
                }
                
                .voice-card:hover {
                    border-color: var(--primary-color, #03a9f4);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .voice-card.selected {
                    border-color: var(--primary-color, #03a9f4);
                    background: var(--primary-color, #03a9f4);
                    color: white;
                }
                
                .voice-card.playing {
                    border-color: var(--accent-color, #ff9800);
                    background: var(--accent-color, #ff9800);
                    color: white;
                }
                
                .voice-card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .voice-name {
                    font-weight: 500;
                    font-size: 1.1em;
                }
                
                .voice-preview-btn {
                    padding: 4px 8px;
                    background: rgba(255, 255, 255, 0.2);
                    color: inherit;
                    border: 1px solid currentColor;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.8em;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    opacity: 0.8;
                }
                
                .voice-card:not(.selected):not(.playing) .voice-preview-btn {
                    background: var(--primary-color, #03a9f4);
                    color: white;
                    border-color: var(--primary-color, #03a9f4);
                    opacity: 1;
                }
                
                .voice-preview-btn:hover {
                    opacity: 1;
                    transform: scale(1.05);
                }
                
                .voice-preview-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                    transform: none;
                }
                
                .voice-description {
                    font-size: 0.9em;
                    opacity: 0.9;
                    line-height: 1.3;
                }
                
                .status {
                    margin-top: 12px;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    text-align: center;
                }
                
                .status.success {
                    background: #4caf50;
                    color: white;
                }
                
                .status.error {
                    background: #f44336;
                    color: white;
                }
                
                .status.loading {
                    background: #2196f3;
                    color: white;
                }
                
                .selected-voice-info {
                    margin-top: 16px;
                    padding: 12px;
                    background: var(--primary-color, #03a9f4);
                    color: white;
                    border-radius: 8px;
                    text-align: center;
                }
                
                .hidden {
                    display: none;
                }
                
                .loading-spinner {
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    border: 2px solid currentColor;
                    border-radius: 50%;
                    border-top-color: transparent;
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
            
            <div class="voice-selector-container">
                <div class="header">
                    <h3 class="title">🎤 Select Voice</h3>
                    <button class="preview-all-btn" id="previewAllBtn">
                        🔄 Preview All
                    </button>
                </div>
                
                <div class="search-container">
                    <input 
                        type="text" 
                        class="search-input" 
                        placeholder="Search voices..."
                        id="voiceSearch"
                    />
                </div>
                
                <div class="voice-grid" id="voiceGrid">
                    <!-- Voice cards will be populated here -->
                </div>
                
                <div class="selected-voice-info">
                    <strong>Selected Voice:</strong> <span id="selectedVoiceName">${this.selectedVoice}</span>
                    <br>
                    <span id="selectedVoiceDescription">${this.voiceDescriptions[this.selectedVoice]}</span>
                </div>
                
                <div class="status hidden" id="statusMessage"></div>
            </div>
        `;
        
        this.populateVoices();
    }

    populateVoices() {
        const grid = this.shadowRoot.getElementById('voiceGrid');
        grid.innerHTML = '';
        
        this.voices.forEach(voice => {
            const card = document.createElement('div');
            card.className = `voice-card ${voice === this.selectedVoice ? 'selected' : ''}`;
            card.dataset.voice = voice;
            
            card.innerHTML = `
                <div class="voice-card-header">
                    <div class="voice-name">${voice}</div>
                    <button class="voice-preview-btn" data-voice="${voice}">
                        🔊 Preview
                    </button>
                </div>
                <div class="voice-description">${this.voiceDescriptions[voice]}</div>
            `;
            
            grid.appendChild(card);
        });
    }

    updateSelectedCard() {
        // Update card appearances
        this.shadowRoot.querySelectorAll('.voice-card').forEach(card => {
            const isSelected = card.dataset.voice === this.selectedVoice;
            card.classList.toggle('selected', isSelected);
        });
        
        // Update selected voice info
        this.shadowRoot.getElementById('selectedVoiceName').textContent = this.selectedVoice;
        this.shadowRoot.getElementById('selectedVoiceDescription').textContent = this.voiceDescriptions[this.selectedVoice];
        
        // Update the actual form select element
        const selectElement = document.querySelector('select[name="default_voice"]');
        if (selectElement) {
            selectElement.value = this.selectedVoice;
            selectElement.dispatchEvent(new Event('change'));
        }
    }

    setupEventListeners() {
        // Voice card clicks
        this.shadowRoot.addEventListener('click', (e) => {
            if (e.target.closest('.voice-card') && !e.target.closest('.voice-preview-btn')) {
                const card = e.target.closest('.voice-card');
                this.selectedVoice = card.dataset.voice;
                this.updateSelectedCard();
            }
        });
        
        // Preview button clicks
        this.shadowRoot.addEventListener('click', (e) => {
            if (e.target.classList.contains('voice-preview-btn')) {
                e.stopPropagation();
                const voice = e.target.dataset.voice;
                this.previewVoice(voice, e.target);
            }
        });
        
        // Preview all button
        this.shadowRoot.getElementById('previewAllBtn').addEventListener('click', () => {
            this.previewAllVoices();
        });
        
        // Search functionality
        this.shadowRoot.getElementById('voiceSearch').addEventListener('input', (e) => {
            this.filterVoices(e.target.value);
        });
    }

    async previewVoice(voice, buttonElement) {
        if (this.isPlaying) {
            this.stopCurrentAudio();
            return;
        }

        try {
            // Update UI to show loading
            const originalText = buttonElement.innerHTML;
            buttonElement.innerHTML = '<span class="loading-spinner"></span> Loading...';
            buttonElement.disabled = true;
            
            // Add playing class to card
            const card = buttonElement.closest('.voice-card');
            card.classList.add('playing');
            
            this.showStatus('Generating voice preview...', 'loading');
            
            // Get API key from the form
            const apiKeyInput = document.querySelector('input[name="gemini_api_key"]');
            const apiKey = apiKeyInput ? apiKeyInput.value : null;
            
            if (!apiKey) {
                throw new Error('API key is required for voice preview');
            }
            
            // Call the preview API
            const result = await this.callWebSocketAPI({
                type: 'voice_assistant_gemini/preview_voice',
                voice_name: voice,
                api_key: apiKey,
                text: `Hello! I'm ${voice}. ${this.voiceDescriptions[voice]}.`
            });
            
            if (result.audio_data) {
                // Convert base64 to audio and play
                await this.playAudioFromBase64(result.audio_data);
                this.showStatus(`🔊 Playing preview of ${voice}`, 'success');
            } else {
                throw new Error('No audio data received');
            }
        } catch (error) {
            console.error('Voice preview error:', error);
            this.showStatus(`❌ Preview failed: ${error.message}`, 'error');
        } finally {
            // Reset UI
            buttonElement.innerHTML = originalText;
            buttonElement.disabled = false;
            card.classList.remove('playing');
            this.isPlaying = false;
        }
    }

    async previewAllVoices() {
        let index = 0;
        const button = this.shadowRoot.getElementById('previewAllBtn');
        button.textContent = '⏹️ Stop Preview';
        
        const previewNext = async () => {
            if (index >= this.voices.length) {
                button.textContent = '🔄 Preview All';
                this.showStatus('✅ All voices previewed!', 'success');
                return;
            }
            
            const voice = this.voices[index];
            const card = this.shadowRoot.querySelector(`[data-voice="${voice}"]`);
            const previewBtn = card.querySelector('.voice-preview-btn');
            
            // Auto-scroll to current voice
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            await this.previewVoice(voice, previewBtn);
            
            index++;
            setTimeout(previewNext, 2000); // Wait 2 seconds between voices
        };
        
        await previewNext();
    }

    async callWebSocketAPI(message) {
        return new Promise((resolve, reject) => {
            // Use Home Assistant's connection if available
            if (window.hassConnection) {
                // Use the existing HA connection
                window.hassConnection.sendMessagePromise(message)
                    .then(resolve)
                    .catch(reject);
                return;
            }
            
            // Fallback to creating our own connection
            const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/websocket`;
            const ws = new WebSocket(wsUrl);
            
            let messageId = Math.floor(Math.random() * 1000000);
            
            ws.onopen = () => {
                // Send auth message first
                ws.send(JSON.stringify({
                    type: 'auth',
                    access_token: this.getAccessToken()
                }));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'auth_required') {
                    // Auth required, will be handled in onopen
                    return;
                } else if (data.type === 'auth_ok') {
                    // Send the actual message
                    ws.send(JSON.stringify({
                        id: messageId,
                        ...message
                    }));
                } else if (data.type === 'result' && data.id === messageId) {
                    ws.close();
                    if (data.success) {
                        resolve(data.result);
                    } else {
                        reject(new Error(data.error?.message || 'API call failed'));
                    }
                }
            };
            
            ws.onerror = (error) => {
                reject(new Error('WebSocket connection failed'));
            };
            
            ws.onclose = (event) => {
                if (!event.wasClean) {
                    reject(new Error('WebSocket connection closed unexpectedly'));
                }
            };
        });
    }

    getAccessToken() {
        // Try to get access token from various sources
        if (window.localStorage) {
            const tokens = window.localStorage.getItem('hassTokens');
            if (tokens) {
                try {
                    const parsed = JSON.parse(tokens);
                    return parsed.access_token;
                } catch (e) {
                    // Ignore parsing errors
                }
            }
        }
        
        // Try to get from session storage
        if (window.sessionStorage) {
            const token = window.sessionStorage.getItem('hassAccessToken');
            if (token) {
                return token;
            }
        }
        
        // Try to extract from URL or other sources
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get('access_token');
        if (tokenFromUrl) {
            return tokenFromUrl;
        }
        
        // Fallback - this might not work in all cases
        return 'demo_token';
    }

    async playAudioFromBase64(base64Data) {
        return new Promise((resolve, reject) => {
            try {
                // Convert base64 to blob
                const audioData = atob(base64Data);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const view = new Uint8Array(arrayBuffer);
                
                for (let i = 0; i < audioData.length; i++) {
                    view[i] = audioData.charCodeAt(i);
                }
                
                const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(blob);
                
                // Stop any current audio
                this.stopCurrentAudio();
                
                // Create and play new audio
                this.currentAudio = new Audio(audioUrl);
                this.isPlaying = true;
                
                this.currentAudio.onended = () => {
                    this.isPlaying = false;
                    URL.revokeObjectURL(audioUrl);
                    resolve();
                };
                
                this.currentAudio.onerror = () => {
                    this.isPlaying = false;
                    URL.revokeObjectURL(audioUrl);
                    reject(new Error('Audio playback failed'));
                };
                
                this.currentAudio.play();
            } catch (error) {
                reject(error);
            }
        });
    }

    stopCurrentAudio() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.isPlaying = false;
        
        // Remove playing class from all cards
        this.shadowRoot.querySelectorAll('.voice-card.playing').forEach(card => {
            card.classList.remove('playing');
        });
    }

    filterVoices(searchTerm) {
        const cards = this.shadowRoot.querySelectorAll('.voice-card');
        const term = searchTerm.toLowerCase();
        
        cards.forEach(card => {
            const voice = card.dataset.voice.toLowerCase();
            const description = this.voiceDescriptions[card.dataset.voice].toLowerCase();
            const matches = voice.includes(term) || description.includes(term);
            
            card.style.display = matches ? 'block' : 'none';
        });
    }

    showStatus(message, type) {
        const statusElement = this.shadowRoot.getElementById('statusMessage');
        statusElement.textContent = message;
        statusElement.className = `status ${type}`;
        statusElement.classList.remove('hidden');
        
        // Auto-hide after 3 seconds for success messages
        if (type === 'success') {
            setTimeout(() => {
                statusElement.classList.add('hidden');
            }, 3000);
        }
    }
}

// Register the custom element
customElements.define('voice-config-selector', VoiceConfigSelector);

// Also expose globally for integration with HA config flow
window.VoiceConfigSelector = VoiceConfigSelector; 