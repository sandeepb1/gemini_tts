class VoiceConfigEnhanced extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.selectedVoice = 'Kore';
        this.isPlaying = false;
        this.audioContext = null;
        this.currentAudioBuffer = null;
        
        // Voice data with descriptions and characteristics
        this.voices = {
            "Kore": { description: "Firm and confident tone", characteristics: ["confident", "professional"] },
            "Puck": { description: "Upbeat and energetic", characteristics: ["happy", "excited"] },
            "Zephyr": { description: "Bright and clear", characteristics: ["clear", "friendly"] },
            "Charon": { description: "Informative and professional", characteristics: ["professional", "informative"] },
            "Fenrir": { description: "Excitable and dynamic", characteristics: ["excited", "dynamic"] },
            "Leda": { description: "Youthful and friendly", characteristics: ["friendly", "casual"] },
            "Orus": { description: "Firm and authoritative", characteristics: ["confident", "formal"] },
            "Aoede": { description: "Breezy and casual", characteristics: ["casual", "friendly"] },
            "Callirrhoe": { description: "Easy-going and relaxed", characteristics: ["calm", "casual"] },
            "Autonoe": { description: "Bright and articulate", characteristics: ["clear", "professional"] },
            "Enceladus": { description: "Breathy and soft", characteristics: ["calm", "gentle"] },
            "Iapetus": { description: "Clear and precise", characteristics: ["clear", "professional"] },
            "Umbriel": { description: "Easy-going and smooth", characteristics: ["calm", "conversational"] },
            "Algieba": { description: "Smooth and polished", characteristics: ["professional", "confident"] },
            "Despina": { description: "Smooth and gentle", characteristics: ["calm", "friendly"] },
            "Erinome": { description: "Clear and direct", characteristics: ["clear", "informative"] },
            "Algenib": { description: "Gravelly and distinctive", characteristics: ["unique", "confident"] },
            "Rasalgethi": { description: "Informative and knowledgeable", characteristics: ["informative", "professional"] },
            "Laomedeia": { description: "Upbeat and lively", characteristics: ["happy", "excited"] },
            "Achernar": { description: "Soft and warm", characteristics: ["calm", "friendly"] },
            "Alnilam": { description: "Firm and steady", characteristics: ["confident", "professional"] },
            "Schedar": { description: "Even and balanced", characteristics: ["neutral", "professional"] },
            "Gacrux": { description: "Mature and experienced", characteristics: ["professional", "confident"] },
            "Pulcherrima": { description: "Forward and confident", characteristics: ["confident", "assertive"] },
            "Achird": { description: "Friendly and approachable", characteristics: ["friendly", "casual"] },
            "Zubenelgenubi": { description: "Casual and conversational", characteristics: ["casual", "conversational"] },
            "Vindemiatrix": { description: "Gentle and soothing", characteristics: ["calm", "gentle"] },
            "Sadachbia": { description: "Lively and animated", characteristics: ["excited", "dynamic"] },
            "Sadaltager": { description: "Knowledgeable and wise", characteristics: ["informative", "professional"] },
            "Sulafat": { description: "Warm and inviting", characteristics: ["friendly", "warm"] }
        };
        
        this.render();
    }

    connectedCallback() {
        this.setupEventListeners();
        this.initializeAudioContext();
    }

    initializeAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }

    async generateVoiceSample(voiceName) {
        const sampleText = `Hello! I'm ${voiceName}. This is how I sound when speaking. I hope you like my voice!`;
        
        try {
            // Use Home Assistant WebSocket API for voice preview
            return new Promise((resolve, reject) => {
                const connection = window.hassConnection;
                if (!connection) {
                    reject(new Error('Home Assistant connection not available'));
                    return;
                }
                
                const emotion = this.shadowRoot.querySelector('#emotion-select').value;
                const toneStyle = this.shadowRoot.querySelector('#tone-select').value;
                
                connection.sendMessagePromise({
                    type: 'voice_assistant_gemini/preview_voice',
                    voice_name: voiceName,
                    text: sampleText,
                    emotion: emotion,
                    tone_style: toneStyle,
                    speaking_rate: 1.0,
                    pitch: 0.0,
                    volume_gain_db: 0.0
                }).then(result => {
                    // Convert base64 audio data to ArrayBuffer
                    const binaryString = atob(result.audio_data);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    resolve(bytes.buffer);
                }).catch(error => {
                    reject(error);
                });
            });
        } catch (error) {
            console.warn('Voice sample generation failed:', error);
            // Return null to indicate failure
            return null;
        }
    }

    async playVoiceSample(voiceName) {
        if (this.isPlaying) {
            this.stopPlayback();
            return;
        }

        const playButton = this.shadowRoot.querySelector(`[data-voice="${voiceName}"] .play-button`);
        const originalContent = playButton.innerHTML;
        
        try {
            this.isPlaying = true;
            playButton.innerHTML = '<span class="loading">⏳</span> Loading...';
            playButton.disabled = true;

            const audioData = await this.generateVoiceSample(voiceName);
            
            if (!audioData || !this.audioContext) {
                throw new Error('Audio generation or playback not available');
            }

            const audioBuffer = await this.audioContext.decodeAudioData(audioData);
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            playButton.innerHTML = '<span class="playing">⏸️</span> Playing...';
            
            source.onended = () => {
                this.isPlaying = false;
                playButton.innerHTML = originalContent;
                playButton.disabled = false;
            };
            
            source.start(0);
            this.currentAudioBuffer = source;
            
        } catch (error) {
            console.error('Playback error:', error);
            this.isPlaying = false;
            playButton.innerHTML = '<span class="error">❌</span> Error';
            playButton.disabled = false;
            
            // Reset button after 2 seconds
            setTimeout(() => {
                playButton.innerHTML = originalContent;
            }, 2000);
        }
    }

    stopPlayback() {
        if (this.currentAudioBuffer) {
            this.currentAudioBuffer.stop();
            this.currentAudioBuffer = null;
        }
        this.isPlaying = false;
        
        // Reset all play buttons
        this.shadowRoot.querySelectorAll('.play-button').forEach(button => {
            button.innerHTML = '<span class="play-icon">▶️</span> Preview';
            button.disabled = false;
        });
    }

    setupEventListeners() {
        // Voice selection
        this.shadowRoot.addEventListener('click', (e) => {
            if (e.target.classList.contains('voice-option') || e.target.closest('.voice-option')) {
                const voiceOption = e.target.classList.contains('voice-option') ? e.target : e.target.closest('.voice-option');
                const voiceName = voiceOption.dataset.voice;
                this.selectVoice(voiceName);
            }
        });

        // Play button clicks
        this.shadowRoot.addEventListener('click', (e) => {
            if (e.target.classList.contains('play-button') || e.target.closest('.play-button')) {
                e.stopPropagation();
                const playButton = e.target.classList.contains('play-button') ? e.target : e.target.closest('.play-button');
                const voiceOption = playButton.closest('.voice-option');
                const voiceName = voiceOption.dataset.voice;
                this.playVoiceSample(voiceName);
            }
        });

        // Search functionality
        const searchInput = this.shadowRoot.querySelector('#voice-search');
        searchInput.addEventListener('input', (e) => {
            this.filterVoices(e.target.value);
        });

        // Category filtering
        this.shadowRoot.addEventListener('click', (e) => {
            if (e.target.classList.contains('category-filter')) {
                this.filterByCategory(e.target.dataset.category);
                // Update active filter
                this.shadowRoot.querySelectorAll('.category-filter').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
            }
        });
    }

    selectVoice(voiceName) {
        this.selectedVoice = voiceName;
        
        // Update UI
        this.shadowRoot.querySelectorAll('.voice-option').forEach(option => {
            option.classList.remove('selected');
        });
        this.shadowRoot.querySelector(`[data-voice="${voiceName}"]`).classList.add('selected');
        
        // Update form field if it exists
        const formField = document.querySelector('select[name="default_voice"]');
        if (formField) {
            formField.value = voiceName;
            formField.dispatchEvent(new Event('change'));
        }

        // Dispatch custom event
        this.dispatchEvent(new CustomEvent('voice-selected', {
            detail: { voice: voiceName },
            bubbles: true
        }));
    }

    filterVoices(searchTerm) {
        const voiceOptions = this.shadowRoot.querySelectorAll('.voice-option');
        const term = searchTerm.toLowerCase();
        
        voiceOptions.forEach(option => {
            const voiceName = option.dataset.voice.toLowerCase();
            const description = this.voices[option.dataset.voice].description.toLowerCase();
            const characteristics = this.voices[option.dataset.voice].characteristics.join(' ').toLowerCase();
            
            const matches = voiceName.includes(term) || 
                          description.includes(term) || 
                          characteristics.includes(term);
            
            option.style.display = matches ? 'flex' : 'none';
        });
    }

    filterByCategory(category) {
        const voiceOptions = this.shadowRoot.querySelectorAll('.voice-option');
        
        if (category === 'all') {
            voiceOptions.forEach(option => {
                option.style.display = 'flex';
            });
            return;
        }
        
        voiceOptions.forEach(option => {
            const voiceData = this.voices[option.dataset.voice];
            const matches = voiceData.characteristics.includes(category);
            option.style.display = matches ? 'flex' : 'none';
        });
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                
                .config-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                .config-section {
                    background: #f8f9fa;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border: 1px solid #e9ecef;
                }
                
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 15px;
                    color: #2c3e50;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .search-container {
                    margin-bottom: 20px;
                }
                
                #voice-search {
                    width: 100%;
                    padding: 12px 16px;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    font-size: 16px;
                    transition: border-color 0.2s;
                }
                
                #voice-search:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
                }
                
                .category-filters {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }
                
                .category-filter {
                    padding: 6px 12px;
                    border: 1px solid #dee2e6;
                    background: white;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 12px;
                    transition: all 0.2s;
                }
                
                .category-filter:hover {
                    background: #e9ecef;
                }
                
                .category-filter.active {
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }
                
                .voice-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 12px;
                    max-height: 400px;
                    overflow-y: auto;
                    padding: 10px 0;
                }
                
                .voice-option {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 16px;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: white;
                }
                
                .voice-option:hover {
                    border-color: #007bff;
                    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.1);
                }
                
                .voice-option.selected {
                    border-color: #007bff;
                    background: #f8f9ff;
                    box-shadow: 0 2px 12px rgba(0, 123, 255, 0.15);
                }
                
                .voice-info {
                    flex: 1;
                    min-width: 0;
                }
                
                .voice-name {
                    font-weight: 600;
                    font-size: 14px;
                    color: #2c3e50;
                    margin-bottom: 4px;
                }
                
                .voice-description {
                    font-size: 12px;
                    color: #6c757d;
                    line-height: 1.3;
                }
                
                .voice-actions {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-left: 12px;
                }
                
                .play-button {
                    padding: 6px 12px;
                    border: 1px solid #28a745;
                    background: #28a745;
                    color: white;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 11px;
                    transition: all 0.2s;
                    white-space: nowrap;
                }
                
                .play-button:hover:not(:disabled) {
                    background: #218838;
                    transform: translateY(-1px);
                }
                
                .play-button:disabled {
                    opacity: 0.7;
                    cursor: not-allowed;
                    transform: none;
                }
                
                .play-icon, .loading, .playing, .error {
                    font-size: 12px;
                }
                
                .controls-section {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                }
                
                .control-group {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .control-label {
                    font-weight: 500;
                    font-size: 14px;
                    color: #495057;
                }
                
                .control-select {
                    padding: 10px 12px;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    font-size: 14px;
                    background: white;
                }
                
                .control-select:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
                }
                
                .selected-voice-info {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 16px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                
                .selected-voice-name {
                    font-size: 20px;
                    font-weight: bold;
                    margin-bottom: 4px;
                }
                
                .selected-voice-desc {
                    opacity: 0.9;
                    font-size: 14px;
                }
                
                @media (max-width: 600px) {
                    .voice-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .controls-section {
                        grid-template-columns: 1fr;
                    }
                    
                    .category-filters {
                        justify-content: center;
                    }
                }
            </style>
            
            <div class="config-container">
                <div class="config-section">
                    <h3 class="section-title">
                        🎭 Voice Selection & Preview
                    </h3>
                    
                    <div class="selected-voice-info">
                        <div class="selected-voice-name">Selected: ${this.selectedVoice}</div>
                        <div class="selected-voice-desc">${this.voices[this.selectedVoice].description}</div>
                    </div>
                    
                    <div class="search-container">
                        <input 
                            type="text" 
                            id="voice-search" 
                            placeholder="🔍 Search voices by name or characteristics..."
                            autocomplete="off"
                        >
                    </div>
                    
                    <div class="category-filters">
                        <button class="category-filter active" data-category="all">All Voices</button>
                        <button class="category-filter" data-category="professional">Professional</button>
                        <button class="category-filter" data-category="friendly">Friendly</button>
                        <button class="category-filter" data-category="confident">Confident</button>
                        <button class="category-filter" data-category="calm">Calm</button>
                        <button class="category-filter" data-category="excited">Excited</button>
                        <button class="category-filter" data-category="casual">Casual</button>
                    </div>
                    
                    <div class="voice-grid">
                        ${Object.entries(this.voices).map(([name, data]) => `
                            <div class="voice-option ${name === this.selectedVoice ? 'selected' : ''}" data-voice="${name}">
                                <div class="voice-info">
                                    <div class="voice-name">${name}</div>
                                    <div class="voice-description">${data.description}</div>
                                </div>
                                <div class="voice-actions">
                                    <button class="play-button" type="button">
                                        <span class="play-icon">▶️</span> Preview
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="config-section">
                    <h3 class="section-title">
                        🎨 Voice Styling & Expression
                    </h3>
                    
                    <div class="controls-section">
                        <div class="control-group">
                            <label class="control-label" for="emotion-select">Emotion</label>
                            <select id="emotion-select" class="control-select">
                                <option value="neutral">Neutral - Standard delivery</option>
                                <option value="happy">Happy - Upbeat and cheerful</option>
                                <option value="sad">Sad - Somber and melancholic</option>
                                <option value="excited">Excited - Energetic and enthusiastic</option>
                                <option value="calm">Calm - Relaxed and peaceful</option>
                                <option value="confident">Confident - Assertive and strong</option>
                                <option value="friendly">Friendly - Warm and approachable</option>
                                <option value="professional">Professional - Business-like and formal</option>
                            </select>
                        </div>
                        
                        <div class="control-group">
                            <label class="control-label" for="tone-select">Tone Style</label>
                            <select id="tone-select" class="control-select">
                                <option value="normal">Normal - Standard speaking style</option>
                                <option value="casual">Casual - Relaxed conversational style</option>
                                <option value="formal">Formal - Professional and structured</option>
                                <option value="storytelling">Storytelling - Narrative and engaging</option>
                                <option value="informative">Informative - Clear and educational</option>
                                <option value="conversational">Conversational - Natural dialogue style</option>
                                <option value="announcement">Announcement - Clear and attention-grabbing</option>
                                <option value="customer_service">Customer Service - Helpful and polite</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

customElements.define('voice-config-enhanced', VoiceConfigEnhanced); 