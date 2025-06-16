/**
 * Voice Preview Component for Voice Assistant Gemini
 * Allows users to preview voices before selecting them
 */

class VoicePreviewCard extends HTMLElement {
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
        this.currentAudio = null;
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--paper-font-body1_-_font-family);
                    padding: 16px;
                    background: var(--card-background-color);
                    border-radius: 8px;
                    box-shadow: var(--ha-card-box-shadow);
                }
                
                .header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 16px;
                }
                
                .title {
                    font-size: 1.2em;
                    font-weight: 500;
                    color: var(--primary-text-color);
                    margin: 0;
                }
                
                .voice-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 12px;
                    margin-bottom: 16px;
                }
                
                .voice-card {
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    padding: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background: var(--card-background-color);
                }
                
                .voice-card:hover {
                    border-color: var(--primary-color);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .voice-card.selected {
                    border-color: var(--primary-color);
                    background: var(--primary-color);
                    color: white;
                }
                
                .voice-name {
                    font-weight: 500;
                    margin-bottom: 4px;
                }
                
                .voice-description {
                    font-size: 0.9em;
                    opacity: 0.8;
                }
                
                .controls {
                    display: flex;
                    gap: 12px;
                    align-items: center;
                    margin-bottom: 16px;
                    flex-wrap: wrap;
                }
                
                .text-input {
                    flex: 1;
                    min-width: 200px;
                    padding: 8px 12px;
                    border: 1px solid var(--divider-color);
                    border-radius: 4px;
                    background: var(--card-background-color);
                    color: var(--primary-text-color);
                }
                
                .preview-btn {
                    padding: 8px 16px;
                    background: var(--primary-color);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: background 0.2s ease;
                }
                
                .preview-btn:hover {
                    background: var(--dark-primary-color);
                }
                
                .preview-btn:disabled {
                    background: var(--disabled-text-color);
                    cursor: not-allowed;
                }
                
                .status {
                    padding: 8px 12px;
                    border-radius: 4px;
                    margin-top: 12px;
                    font-size: 0.9em;
                }
                
                .status.success {
                    background: var(--success-color);
                    color: white;
                }
                
                .status.error {
                    background: var(--error-color);
                    color: white;
                }
                
                .status.loading {
                    background: var(--info-color);
                    color: white;
                }
                
                .audio-player {
                    margin-top: 12px;
                    width: 100%;
                }
                
                .hidden {
                    display: none;
                }
            </style>
            
            <div class="header">
                <h3 class="title">🎤 Voice Preview</h3>
            </div>
            
            <div class="controls">
                <input 
                    type="text" 
                    class="text-input" 
                    placeholder="Enter text to preview (or use default)"
                    value="Hello! This is a preview of the selected voice."
                />
                <button class="preview-btn" id="previewBtn">
                    🔊 Preview Voice
                </button>
            </div>
            
            <div class="voice-grid" id="voiceGrid">
                <!-- Voice cards will be populated here -->
            </div>
            
            <div class="status hidden" id="status"></div>
            <audio class="audio-player hidden" id="audioPlayer" controls></audio>
        `;
        
        this.populateVoices();
    }
    
    populateVoices() {
        const grid = this.shadowRoot.getElementById('voiceGrid');
        grid.innerHTML = '';
        
        this.voices.forEach(voice => {
            const card = document.createElement('div');
            card.className = 'voice-card';
            card.dataset.voice = voice;
            
            card.innerHTML = `
                <div class="voice-name">${voice}</div>
                <div class="voice-description">${this.voiceDescriptions[voice] || 'Natural voice'}</div>
            `;
            
            card.addEventListener('click', () => this.selectVoice(voice));
            grid.appendChild(card);
        });
        
        // Select first voice by default
        this.selectVoice(this.voices[0]);
    }
    
    selectVoice(voice) {
        // Remove previous selection
        this.shadowRoot.querySelectorAll('.voice-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Select new voice
        const selectedCard = this.shadowRoot.querySelector(`[data-voice="${voice}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
            this.selectedVoice = voice;
        }
    }
    
    setupEventListeners() {
        const previewBtn = this.shadowRoot.getElementById('previewBtn');
        const textInput = this.shadowRoot.querySelector('.text-input');
        
        previewBtn.addEventListener('click', () => this.previewVoice());
        
        // Listen for voice preview events
        window.addEventListener('voice_assistant_gemini_voice_preview', (event) => {
            this.handlePreviewResult(event.detail);
        });
    }
    
    async previewVoice() {
        if (!this.selectedVoice) {
            this.showStatus('Please select a voice first', 'error');
            return;
        }

        const previewBtn = this.shadowRoot.getElementById('previewBtn');
        const textInput = this.shadowRoot.querySelector('.text-input');
        const text = textInput.value.trim() || "Hello! This is a preview of the selected voice.";

        try {
            // Update UI to show loading
            const originalText = previewBtn.textContent;
            previewBtn.textContent = '🔄 Generating...';
            previewBtn.disabled = true;
            
            this.showStatus('Generating voice preview...', 'loading');
            
            // Call the Home Assistant WebSocket API directly
            const result = await this.callHomeAssistantService('voice_assistant_gemini.synthesize', {
                text: text,
                voice: this.selectedVoice,
                speaking_rate: 1.0,
                pitch: 0.0,
                volume_gain_db: 0.0
            });
            
            if (result && result.audio_data) {
                // Convert base64 to audio and play
                await this.playAudioFromBase64(result.audio_data);
                this.showStatus(`🔊 Playing preview of ${this.selectedVoice}`, 'success');
            } else {
                throw new Error('No audio data received from service');
            }
        } catch (error) {
            console.error('Voice preview error:', error);
            this.showStatus(`❌ Preview failed: ${error.message}`, 'error');
            
            // Fallback to WebSocket API
            try {
                this.showStatus('Trying alternative method...', 'loading');
                const wsResult = await this.callWebSocketAPI({
                    type: 'voice_assistant_gemini/synthesize',
                    text: text,
                    voice: this.selectedVoice
                });
                
                if (wsResult && wsResult.audio_data) {
                    await this.playAudioFromBase64(wsResult.audio_data);
                    this.showStatus(`🔊 Playing preview of ${this.selectedVoice}`, 'success');
                } else {
                    throw new Error('No audio data received from WebSocket API');
                }
            } catch (wsError) {
                console.error('WebSocket preview error:', wsError);
                this.showStatus(`❌ Preview failed: ${wsError.message}. Make sure the integration is properly configured.`, 'error');
            }
        } finally {
            // Reset UI
            previewBtn.textContent = originalText;
            previewBtn.disabled = false;
        }
    }

    async callHomeAssistantService(service, data) {
        return new Promise((resolve, reject) => {
            // Use Home Assistant's service calling mechanism if available
            if (window.hass && window.hass.callService) {
                const [domain, serviceAction] = service.split('.');
                window.hass.callService(domain, serviceAction, data)
                    .then(resolve)
                    .catch(reject);
                return;
            }
            
            // Fallback to fetch API
            fetch('/api/services/' + service, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(resolve)
            .catch(reject);
        });
    }

    async callWebSocketAPI(message) {
        return new Promise((resolve, reject) => {
            // Use Home Assistant's connection if available
            if (window.hassConnection && window.hassConnection.sendMessagePromise) {
                window.hassConnection.sendMessagePromise(message)
                    .then(resolve)
                    .catch(reject);
                return;
            }
            
            // Fallback to creating our own connection
            const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/websocket`;
            const ws = new WebSocket(wsUrl);
            
            let messageId = Math.floor(Math.random() * 1000000);
            let timeout = setTimeout(() => {
                ws.close();
                reject(new Error('WebSocket request timeout'));
            }, 30000); // 30 second timeout
            
            ws.onopen = () => {
                ws.send(JSON.stringify({
                    type: 'auth',
                    access_token: this.getAccessToken()
                }));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'auth_required') {
                    return;
                } else if (data.type === 'auth_ok') {
                    ws.send(JSON.stringify({
                        id: messageId,
                        ...message
                    }));
                } else if (data.type === 'result' && data.id === messageId) {
                    clearTimeout(timeout);
                    ws.close();
                    if (data.success) {
                        resolve(data.result);
                    } else {
                        reject(new Error(data.error?.message || 'API call failed'));
                    }
                }
            };
            
            ws.onerror = (error) => {
                clearTimeout(timeout);
                reject(new Error('WebSocket connection failed'));
            };
            
            ws.onclose = (event) => {
                clearTimeout(timeout);
                if (!event.wasClean) {
                    reject(new Error('WebSocket connection closed unexpectedly'));
                }
            };
        });
    }

    getAccessToken() {
        // Try multiple methods to get the access token
        
        // Method 1: From Home Assistant object
        if (window.hass && window.hass.auth && window.hass.auth.data && window.hass.auth.data.access_token) {
            return window.hass.auth.data.access_token;
        }
        
        // Method 2: From localStorage
        if (window.localStorage) {
            const hassTokens = localStorage.getItem('hassTokens');
            if (hassTokens) {
                try {
                    const tokens = JSON.parse(hassTokens);
                    if (tokens.access_token) {
                        return tokens.access_token;
                    }
                } catch (e) {
                    // Ignore parsing errors
                }
            }
        }
        
        // Method 3: From sessionStorage
        if (window.sessionStorage) {
            const token = sessionStorage.getItem('hassAccessToken');
            if (token) {
                return token;
            }
        }
        
        // Method 4: From URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get('access_token');
        if (tokenFromUrl) {
            return tokenFromUrl;
        }
        
        // Fallback - this will likely fail but at least we try
        console.warn('Could not find Home Assistant access token');
        return 'unknown_token';
    }

    async playAudioFromBase64(base64Data) {
        const audioPlayer = this.shadowRoot.getElementById('audioPlayer');
        audioPlayer.src = `data:audio/wav;base64,${base64Data}`;
        audioPlayer.classList.remove('hidden');
        await audioPlayer.play();
    }

    handlePreviewResult(data) {
        this.shadowRoot.getElementById('previewBtn').disabled = false;
        
        if (data.success) {
            this.showStatus(`Voice preview generated for ${data.voice}`, 'success');
            
            // Play the audio
            const audioPlayer = this.shadowRoot.getElementById('audioPlayer');
            audioPlayer.src = data.media_url;
            audioPlayer.classList.remove('hidden');
            audioPlayer.play().catch(err => {
                console.warn('Could not auto-play audio:', err);
            });
        } else {
            this.showStatus(`Error generating preview: ${data.error}`, 'error');
        }
    }
    
    showStatus(message, type) {
        const status = this.shadowRoot.getElementById('status');
        status.textContent = message;
        status.className = `status ${type}`;
        status.classList.remove('hidden');
        
        if (type === 'success') {
            setTimeout(() => {
                status.classList.add('hidden');
            }, 5000);
        }
    }
}

// Register the custom element
customElements.define('voice-preview-card', VoicePreviewCard);

// Auto-register with Home Assistant if available
if (window.customCards) {
    window.customCards = window.customCards || [];
    window.customCards.push({
        type: 'voice-preview-card',
        name: 'Voice Preview Card',
        description: 'Preview Gemini TTS voices before selection'
    });
} 