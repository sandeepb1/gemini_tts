/**
 * Simple Voice Selector for Voice Assistant Gemini Configuration
 * Displays voice options with descriptions for easy selection
 */

class VoiceSimpleSelector extends HTMLElement {
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
        
        // Hide the original select element since we're replacing it
        if (selectElement) {
            selectElement.style.display = 'none';
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
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                
                .header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 16px;
                }
                
                .title {
                    font-size: 1.2em;
                    font-weight: 500;
                    color: var(--primary-text-color, #212121);
                    margin: 0;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .search-container {
                    margin-bottom: 16px;
                }
                
                .search-input {
                    width: 100%;
                    padding: 10px 16px;
                    border: 2px solid var(--divider-color, #e0e0e0);
                    border-radius: 6px;
                    background: var(--card-background-color, #fff);
                    color: var(--primary-text-color, #212121);
                    font-family: inherit;
                    font-size: 14px;
                    box-sizing: border-box;
                    transition: border-color 0.2s ease;
                }
                
                .search-input:focus {
                    outline: none;
                    border-color: var(--primary-color, #03a9f4);
                }
                
                .voice-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 12px;
                    max-height: 500px;
                    overflow-y: auto;
                    padding: 4px;
                }
                
                .voice-card {
                    border: 2px solid var(--divider-color, #e0e0e0);
                    border-radius: 10px;
                    padding: 16px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    background: var(--card-background-color, #fff);
                    position: relative;
                }
                
                .voice-card:hover {
                    border-color: var(--primary-color, #03a9f4);
                    box-shadow: 0 4px 12px rgba(3, 169, 244, 0.15);
                    transform: translateY(-2px);
                }
                
                .voice-card.selected {
                    border-color: var(--primary-color, #03a9f4);
                    background: linear-gradient(135deg, var(--primary-color, #03a9f4), #29b6f6);
                    color: white;
                    box-shadow: 0 6px 16px rgba(3, 169, 244, 0.3);
                    transform: translateY(-2px);
                }
                
                .voice-name {
                    font-weight: 600;
                    font-size: 1.2em;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .voice-name::before {
                    content: "🎤";
                    font-size: 1.1em;
                }
                
                .voice-card.selected .voice-name::before {
                    content: "✨";
                }
                
                .voice-description {
                    font-size: 0.95em;
                    opacity: 0.85;
                    line-height: 1.4;
                    font-style: italic;
                }
                
                .voice-card.selected .voice-description {
                    opacity: 0.95;
                }
                
                .selected-voice-info {
                    margin-top: 20px;
                    padding: 16px;
                    background: linear-gradient(135deg, var(--primary-color, #03a9f4), #29b6f6);
                    color: white;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 8px rgba(3, 169, 244, 0.2);
                }
                
                .selected-voice-info h4 {
                    margin: 0 0 8px 0;
                    font-size: 1.1em;
                    font-weight: 600;
                }
                
                .selected-voice-info p {
                    margin: 0;
                    opacity: 0.9;
                    font-style: italic;
                }
                
                .preview-note {
                    margin-top: 16px;
                    padding: 12px;
                    background: #f5f5f5;
                    border-left: 4px solid var(--primary-color, #03a9f4);
                    border-radius: 4px;
                    font-size: 0.9em;
                    color: var(--secondary-text-color, #666);
                }
                
                .hidden {
                    display: none;
                }
                
                .no-results {
                    text-align: center;
                    padding: 40px 20px;
                    color: var(--secondary-text-color, #666);
                    font-style: italic;
                }
                
                .stats {
                    margin-top: 12px;
                    font-size: 0.85em;
                    color: var(--secondary-text-color, #666);
                    text-align: center;
                }
            </style>
            
            <div class="voice-selector-container">
                <div class="header">
                    <h3 class="title">
                        🎭 Choose Your Voice
                    </h3>
                </div>
                
                <div class="search-container">
                    <input 
                        type="text" 
                        class="search-input" 
                        placeholder="🔍 Search voices by name or personality..."
                        id="voiceSearch"
                    />
                </div>
                
                <div class="voice-grid" id="voiceGrid">
                    <!-- Voice cards will be populated here -->
                </div>
                
                <div class="stats" id="voiceStats">
                    Showing ${this.voices.length} voices
                </div>
                
                <div class="selected-voice-info">
                    <h4>Selected Voice: <span id="selectedVoiceName">${this.selectedVoice}</span></h4>
                    <p id="selectedVoiceDescription">${this.voiceDescriptions[this.selectedVoice]}</p>
                </div>
                
                <div class="preview-note">
                    <strong>💡 Tip:</strong> After setting up the integration, you can preview voices using the 
                    voice assistant card or by calling the <code>voice_assistant_gemini.tts</code> service.
                </div>
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
                <div class="voice-name">${voice}</div>
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
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    setupEventListeners() {
        // Voice card clicks
        this.shadowRoot.addEventListener('click', (e) => {
            const card = e.target.closest('.voice-card');
            if (card) {
                this.selectedVoice = card.dataset.voice;
                this.updateSelectedCard();
            }
        });
        
        // Search functionality
        this.shadowRoot.getElementById('voiceSearch').addEventListener('input', (e) => {
            this.filterVoices(e.target.value);
        });
    }

    filterVoices(searchTerm) {
        const cards = this.shadowRoot.querySelectorAll('.voice-card');
        const term = searchTerm.toLowerCase();
        let visibleCount = 0;
        
        cards.forEach(card => {
            const voice = card.dataset.voice.toLowerCase();
            const description = this.voiceDescriptions[card.dataset.voice].toLowerCase();
            const matches = voice.includes(term) || description.includes(term);
            
            card.style.display = matches ? 'block' : 'none';
            if (matches) visibleCount++;
        });
        
        // Update stats
        const statsElement = this.shadowRoot.getElementById('voiceStats');
        if (term) {
            statsElement.textContent = `Showing ${visibleCount} of ${this.voices.length} voices`;
        } else {
            statsElement.textContent = `Showing ${this.voices.length} voices`;
        }
        
        // Show no results message if needed
        const grid = this.shadowRoot.getElementById('voiceGrid');
        if (visibleCount === 0 && term) {
            if (!this.shadowRoot.querySelector('.no-results')) {
                const noResults = document.createElement('div');
                noResults.className = 'no-results';
                noResults.textContent = `No voices found matching "${term}"`;
                grid.appendChild(noResults);
            }
        } else {
            const noResults = this.shadowRoot.querySelector('.no-results');
            if (noResults) {
                noResults.remove();
            }
        }
    }
}

// Register the custom element
customElements.define('voice-simple-selector', VoiceSimpleSelector);

// Also expose globally for integration with HA config flow
window.VoiceSimpleSelector = VoiceSimpleSelector; 