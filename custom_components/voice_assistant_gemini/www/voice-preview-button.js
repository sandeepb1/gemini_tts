// Voice Preview Button Component for Home Assistant Config Flow
class VoicePreviewButton extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.isPlaying = false;
        this.audioContext = null;
        this.currentAudioBuffer = null;
        this.render();
    }

    connectedCallback() {
        this.initializeAudioContext();
        this.setupEventListeners();
        this.observeFormChanges();
    }

    initializeAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }

    setupEventListeners() {
        const playButton = this.shadowRoot.querySelector('#preview-button');
        const streamingButton = this.shadowRoot.querySelector('#streaming-button');
        
        playButton.addEventListener('click', () => this.handlePreview());
        streamingButton.addEventListener('click', () => this.handleStreamingPreview());
    }

    observeFormChanges() {
        // Watch for form changes to update preview with selected voice
        const observer = new MutationObserver(() => {
            this.updatePreviewButton();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    updatePreviewButton() {
        const voiceSelect = document.querySelector('select[data-field="default_voice"]') || 
                           document.querySelector('select[name="default_voice"]');
        const emotionSelect = document.querySelector('select[data-field="emotion"]') || 
                             document.querySelector('select[name="emotion"]');
        const toneSelect = document.querySelector('select[data-field="tone_style"]') || 
                          document.querySelector('select[name="tone_style"]');

        if (voiceSelect) {
            const selectedVoice = voiceSelect.value || 'Kore';
            const selectedEmotion = emotionSelect ? emotionSelect.value || 'neutral' : 'neutral';
            const selectedTone = toneSelect ? toneSelect.value || 'normal' : 'normal';
            
            const infoSpan = this.shadowRoot.querySelector('#voice-info');
            infoSpan.textContent = `${selectedVoice} (${selectedEmotion}, ${selectedTone})`;
        }
    }

    async handlePreview() {
        if (this.isPlaying) {
            this.stopPlayback();
            return;
        }

        const playButton = this.shadowRoot.querySelector('#preview-button');
        const originalText = playButton.textContent;
        
        try {
            this.isPlaying = true;
            playButton.textContent = '⏳ Loading...';
            playButton.disabled = true;

            const audioData = await this.generateVoiceSample();
            
            if (!audioData || !this.audioContext) {
                throw new Error('Audio generation or playback not available');
            }

            const audioBuffer = await this.audioContext.decodeAudioData(audioData);
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            playButton.textContent = '⏸️ Playing...';
            
            source.onended = () => {
                this.isPlaying = false;
                playButton.textContent = originalText;
                playButton.disabled = false;
            };
            
            source.start(0);
            this.currentAudioBuffer = source;
            
        } catch (error) {
            console.error('Voice preview error:', error);
            this.isPlaying = false;
            playButton.textContent = '❌ Error';
            playButton.disabled = false;
            
            // Reset button after 2 seconds
            setTimeout(() => {
                playButton.textContent = originalText;
            }, 2000);
        }
    }

    async generateVoiceSample() {
        try {
            // Get current form values
            const voiceSelect = document.querySelector('select[data-field="default_voice"]') || 
                               document.querySelector('select[name="default_voice"]');
            const emotionSelect = document.querySelector('select[data-field="emotion"]') || 
                                 document.querySelector('select[name="emotion"]');
            const toneSelect = document.querySelector('select[data-field="tone_style"]') || 
                              document.querySelector('select[name="tone_style"]');

            const voiceName = voiceSelect ? voiceSelect.value || 'Kore' : 'Kore';
            const emotion = emotionSelect ? emotionSelect.value || 'neutral' : 'neutral';
            const toneStyle = toneSelect ? toneSelect.value || 'normal' : 'normal';
            
            const sampleText = `Hello! I'm ${voiceName}. This is how I sound with ${emotion} emotion and ${toneStyle} style.`;

            // Use Home Assistant WebSocket API for voice preview
            return new Promise((resolve, reject) => {
                // Try to get HA connection from various possible locations
                const connection = window.hassConnection || 
                                 window.hass?.connection ||
                                 (window.hass && window.hass.callWS);
                
                if (!connection) {
                    reject(new Error('Home Assistant connection not available'));
                    return;
                }

                const message = {
                    type: 'voice_assistant_gemini/preview_voice',
                    voice_name: voiceName,
                    text: sampleText,
                    emotion: emotion,
                    tone_style: toneStyle,
                    speaking_rate: 1.0,
                    pitch: 0.0,
                    volume_gain_db: 0.0
                };

                // Handle different connection types
                if (connection.sendMessagePromise) {
                    connection.sendMessagePromise(message)
                        .then(result => {
                            const binaryString = atob(result.audio_data);
                            const bytes = new Uint8Array(binaryString.length);
                            for (let i = 0; i < binaryString.length; i++) {
                                bytes[i] = binaryString.charCodeAt(i);
                            }
                            resolve(bytes.buffer);
                        })
                        .catch(reject);
                } else if (typeof connection === 'function') {
                    // Legacy call format
                    connection(message)
                        .then(result => {
                            const binaryString = atob(result.audio_data);
                            const bytes = new Uint8Array(binaryString.length);
                            for (let i = 0; i < binaryString.length; i++) {
                                bytes[i] = binaryString.charCodeAt(i);
                            }
                            resolve(bytes.buffer);
                        })
                        .catch(reject);
                } else {
                    reject(new Error('Unsupported connection type'));
                }
            });
        } catch (error) {
            console.warn('Voice sample generation failed:', error);
            return null;
        }
    }

    async handleStreamingPreview() {
        if (this.isPlaying) {
            this.stopPlayback();
            return;
        }

        const streamingButton = this.shadowRoot.querySelector('#streaming-button');
        const originalText = streamingButton.textContent;
        
        try {
            this.isPlaying = true;
            streamingButton.textContent = '⏳ Starting stream...';
            streamingButton.disabled = true;

            // Get current form values
            const voiceSelect = document.querySelector('select[data-field="default_voice"]') || 
                               document.querySelector('select[name="default_voice"]');
            const emotionSelect = document.querySelector('select[data-field="emotion"]') || 
                                 document.querySelector('select[name="emotion"]');
            const toneSelect = document.querySelector('select[data-field="tone_style"]') || 
                              document.querySelector('select[name="tone_style"]');

            const voiceName = voiceSelect ? voiceSelect.value || 'Kore' : 'Kore';
            const emotion = emotionSelect ? emotionSelect.value || 'neutral' : 'neutral';
            const toneStyle = toneSelect ? toneSelect.value || 'normal' : 'normal';
            
            const sampleText = `This is a streaming demonstration of the ${voiceName} voice with ${emotion} emotion and ${toneStyle} style. Notice how the audio starts playing immediately as chunks are generated, providing a much faster experience for longer texts. This streaming approach is especially beneficial for longer announcements, stories, or detailed messages.`;

            await this.streamVoicePreview({
                text: sampleText,
                voice: voiceName,
                emotion: emotion,
                tone_style: toneStyle
            });

        } catch (error) {
            console.error('Streaming preview error:', error);
            this.isPlaying = false;
            streamingButton.textContent = '❌ Stream Error';
            streamingButton.disabled = false;
            
            // Reset button after 3 seconds
            setTimeout(() => {
                streamingButton.textContent = originalText;
            }, 3000);
        }
    }

    async streamVoicePreview(params) {
        const streamingButton = this.shadowRoot.querySelector('#streaming-button');
        let chunkCount = 0;
        let nextStartTime = this.audioContext.currentTime;

        return new Promise((resolve, reject) => {
            const connection = window.hassConnection || 
                             window.hass?.connection ||
                             (window.hass && window.hass.callWS);

            if (!connection) {
                reject(new Error('Home Assistant connection not available'));
                return;
            }

            const message = {
                type: 'voice_assistant_gemini/synthesize_streaming',
                text: params.text,
                voice: params.voice,
                emotion: params.emotion,
                tone_style: params.tone_style,
                speaking_rate: 1.0,
                pitch: 0.0,
                volume_gain_db: 0.0
            };

            let messageId;
            let totalChunks = 0;

            const handleMessage = (msg) => {
                if (msg.id !== messageId) return;

                if (msg.type === 'result' && msg.result) {
                    const result = msg.result;
                    
                    if (result.type === 'streaming_chunk') {
                        chunkCount++;
                        totalChunks = result.total_chunks;
                        
                        this.playAudioChunk(result.audio_data, nextStartTime);
                        streamingButton.textContent = `🎵 Playing (${chunkCount}/${totalChunks})`;
                        
                        // Calculate next start time (approximately)
                        nextStartTime += 2; // Estimate 2 seconds per chunk
                        
                    } else if (result.type === 'streaming_complete') {
                        streamingButton.textContent = '✅ Stream Complete';
                        setTimeout(() => {
                            streamingButton.textContent = '🚀 Stream Preview';
                            streamingButton.disabled = false;
                            this.isPlaying = false;
                        }, 2000);
                        resolve(result);
                        connection.removeEventListener('message', handleMessage);
                    }
                } else if (msg.type === 'result' && msg.error) {
                    reject(new Error(msg.error.message || 'Streaming failed'));
                    connection.removeEventListener('message', handleMessage);
                }
            };

            connection.addEventListener('message', handleMessage);

            // Send the streaming request
            if (connection.sendMessagePromise) {
                messageId = Math.random().toString(36).substr(2, 9);
                connection.sendMessage({...message, id: messageId});
            } else if (typeof connection === 'function') {
                connection(message)
                    .then(resolve)
                    .catch(reject);
            } else {
                reject(new Error('Unsupported connection type'));
            }
        });
    }

    async playAudioChunk(audioData, startTime) {
        if (!this.audioContext || !this.isPlaying) return;

        try {
            // Decode audio chunk
            const binaryString = atob(audioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
            
            // Schedule audio chunk for playback
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            // Schedule with minimal gap between chunks
            const scheduleTime = Math.max(this.audioContext.currentTime, startTime);
            source.start(scheduleTime);
            
        } catch (error) {
            console.error('Error playing audio chunk:', error);
        }
    }

    stopPlayback() {
        if (this.currentAudioBuffer) {
            try {
                this.currentAudioBuffer.stop();
            } catch (e) {
                // Audio already stopped
            }
            this.currentAudioBuffer = null;
        }
        this.isPlaying = false;
        
        const playButton = this.shadowRoot.querySelector('#preview-button');
        const streamingButton = this.shadowRoot.querySelector('#streaming-button');
        
        if (playButton) {
            playButton.textContent = '▶️ Preview Voice';
            playButton.disabled = false;
        }
        
        if (streamingButton) {
            streamingButton.textContent = '🚀 Stream Preview';
            streamingButton.disabled = false;
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    margin: 16px 0;
                    padding: 16px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                
                .preview-container {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                #preview-button, #streaming-button {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background-color 0.2s;
                    margin-right: 8px;
                }
                
                #streaming-button {
                    background: #28a745;
                }
                
                #preview-button:hover:not(:disabled) {
                    background: #0056b3;
                }
                
                #streaming-button:hover:not(:disabled) {
                    background: #1e7e34;
                }
                
                #preview-button:disabled, #streaming-button:disabled {
                    background: #6c757d;
                    cursor: not-allowed;
                }
                
                .voice-info {
                    font-size: 14px;
                    color: #6c757d;
                    flex: 1;
                }
                
                .preview-label {
                    font-weight: 500;
                    color: #495057;
                    margin-bottom: 8px;
                }
            </style>
            
            <div class="preview-label">🎵 Voice Preview</div>
            <div class="preview-container">
                <button id="preview-button" type="button">▶️ Preview Voice</button>
                <button id="streaming-button" type="button">🚀 Stream Preview</button>
                <span class="voice-info" id="voice-info">Select a voice to preview</span>
            </div>
        `;
    }
}

// Register the custom element
customElements.define('voice-preview-button', VoicePreviewButton);

// Auto-inject into config forms
document.addEventListener('DOMContentLoaded', function() {
    function addPreviewButton() {
        // Look for voice selection dropdowns
        const voiceSelect = document.querySelector('select[data-field="default_voice"]') || 
                           document.querySelector('select[name="default_voice"]');
        
        if (voiceSelect && !document.querySelector('voice-preview-button')) {
            const previewButton = document.createElement('voice-preview-button');
            
            // Insert after the voice select element's parent
            const insertPoint = voiceSelect.closest('.form-group') || voiceSelect.parentElement;
            if (insertPoint) {
                insertPoint.insertAdjacentElement('afterend', previewButton);
            }
        }
    }
    
    // Try to add button immediately
    addPreviewButton();
    
    // Also watch for dynamic content loading
    const observer = new MutationObserver(addPreviewButton);
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}); 