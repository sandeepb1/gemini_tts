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
        
        const text = this.shadowRoot.querySelector('.text-input').value || 
                    "Hello! This is a preview of the selected voice.";
        
        this.showStatus('Generating voice preview...', 'loading');
        this.shadowRoot.getElementById('previewBtn').disabled = true;
        
        try {
            // Call the voice preview service
            await window.hassConnection.callService('voice_assistant_gemini', 'preview_voice', {
                voice: this.selectedVoice,
                text: text
            });
        } catch (error) {
            this.showStatus(`Error: ${error.message}`, 'error');
            this.shadowRoot.getElementById('previewBtn').disabled = false;
        }
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