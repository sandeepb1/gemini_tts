class StreamingAudioPlayer extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.currentSource = null;
        this.nextStartTime = 0;
        this.render();
    }

    connectedCallback() {
        this.initializeAudioContext();
        this.setupEventListeners();
    }

    initializeAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }

    setupEventListeners() {
        const playButton = this.shadowRoot.querySelector('#play-button');
        const stopButton = this.shadowRoot.querySelector('#stop-button');
        
        playButton.addEventListener('click', () => this.startStreaming());
        stopButton.addEventListener('click', () => this.stopStreaming());
    }

    async startStreaming() {
        const text = this.getAttribute('text') || 'Hello, this is a streaming audio test.';
        const voice = this.getAttribute('voice') || 'Kore';
        const emotion = this.getAttribute('emotion') || 'neutral';
        const toneStyle = this.getAttribute('tone-style') || 'normal';

        if (this.isPlaying) {
            this.stopStreaming();
            return;
        }

        this.isPlaying = true;
        this.updateUI('streaming');
        this.audioQueue = [];
        this.nextStartTime = this.audioContext.currentTime;

        try {
            await this.streamTTS({
                text: text,
                voice: voice,
                emotion: emotion,
                tone_style: toneStyle
            });
        } catch (error) {
            console.error('Streaming error:', error);
            this.updateUI('error');
            this.isPlaying = false;
        }
    }

    stopStreaming() {
        this.isPlaying = false;
        this.audioQueue = [];
        
        if (this.currentSource) {
            try {
                this.currentSource.stop();
            } catch (e) {
                // Audio already stopped
            }
            this.currentSource = null;
        }
        
        this.updateUI('stopped');
    }

    async streamTTS(params) {
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
            let receivedChunks = 0;
            let totalChunks = 0;

            const handleMessage = (msg) => {
                if (msg.id !== messageId) return;

                if (msg.type === 'result' && msg.result) {
                    const result = msg.result;
                    
                    if (result.type === 'streaming_chunk') {
                        receivedChunks++;
                        totalChunks = result.total_chunks;
                        
                        this.handleAudioChunk(result);
                        this.updateProgress(result.progress);
                        
                    } else if (result.type === 'streaming_complete') {
                        this.updateUI('complete');
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

    async handleAudioChunk(chunkData) {
        if (!this.audioContext || !this.isPlaying) return;

        try {
            // Decode audio chunk
            const binaryString = atob(chunkData.audio_data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
            
            // Schedule audio chunk for playback
            this.scheduleAudioChunk(audioBuffer, chunkData.chunk_index);
            
        } catch (error) {
            console.error('Error processing audio chunk:', error);
        }
    }

    scheduleAudioChunk(audioBuffer, chunkIndex) {
        if (!this.audioContext || !this.isPlaying) return;

        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);

        // Schedule with minimal gap between chunks
        const startTime = Math.max(this.audioContext.currentTime, this.nextStartTime);
        source.start(startTime);
        
        // Update next start time
        this.nextStartTime = startTime + audioBuffer.duration;

        // Handle chunk completion
        source.onended = () => {
            if (chunkIndex === 0) {
                // First chunk started playing
                this.updateUI('playing');
            }
        };

        this.currentSource = source;
    }

    updateProgress(progress) {
        const progressBar = this.shadowRoot.querySelector('.progress-fill');
        const progressText = this.shadowRoot.querySelector('.progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${progress * 100}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progress * 100)}%`;
        }
    }

    updateUI(state) {
        const playButton = this.shadowRoot.querySelector('#play-button');
        const stopButton = this.shadowRoot.querySelector('#stop-button');
        const status = this.shadowRoot.querySelector('.status');
        const progressContainer = this.shadowRoot.querySelector('.progress-container');

        switch (state) {
            case 'streaming':
                playButton.textContent = '⏳ Generating...';
                playButton.disabled = true;
                stopButton.disabled = false;
                status.textContent = 'Generating audio...';
                progressContainer.style.display = 'block';
                break;
                
            case 'playing':
                playButton.textContent = '⏸️ Playing';
                status.textContent = 'Playing audio...';
                break;
                
            case 'complete':
                playButton.textContent = '▶️ Play Streaming';
                playButton.disabled = false;
                stopButton.disabled = true;
                status.textContent = 'Streaming complete';
                this.isPlaying = false;
                break;
                
            case 'stopped':
                playButton.textContent = '▶️ Play Streaming';
                playButton.disabled = false;
                stopButton.disabled = true;
                status.textContent = 'Ready';
                progressContainer.style.display = 'none';
                break;
                
            case 'error':
                playButton.textContent = '❌ Error';
                playButton.disabled = false;
                stopButton.disabled = true;
                status.textContent = 'Error occurred';
                setTimeout(() => {
                    playButton.textContent = '▶️ Play Streaming';
                    status.textContent = 'Ready';
                }, 3000);
                break;
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    padding: 16px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                    margin: 16px 0;
                }
                
                .streaming-player {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                
                .controls {
                    display: flex;
                    gap: 8px;
                    align-items: center;
                }
                
                .control-button {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background-color 0.2s;
                }
                
                .control-button:hover:not(:disabled) {
                    background: #0056b3;
                }
                
                .control-button:disabled {
                    background: #6c757d;
                    cursor: not-allowed;
                }
                
                .control-button.stop {
                    background: #dc3545;
                }
                
                .control-button.stop:hover:not(:disabled) {
                    background: #c82333;
                }
                
                .status {
                    font-size: 14px;
                    color: #6c757d;
                    flex: 1;
                }
                
                .progress-container {
                    display: none;
                    margin-top: 8px;
                }
                
                .progress-bar {
                    width: 100%;
                    height: 8px;
                    background: #e9ecef;
                    border-radius: 4px;
                    overflow: hidden;
                }
                
                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #007bff, #0056b3);
                    width: 0%;
                    transition: width 0.3s ease;
                }
                
                .progress-text {
                    font-size: 12px;
                    color: #6c757d;
                    text-align: center;
                    margin-top: 4px;
                }
                
                .streaming-info {
                    font-size: 12px;
                    color: #6c757d;
                    background: #e3f2fd;
                    padding: 8px;
                    border-radius: 4px;
                    border-left: 3px solid #2196f3;
                }
            </style>
            
            <div class="streaming-player">
                <div class="streaming-info">
                    🚀 Streaming TTS: Audio starts playing as soon as first chunk is ready
                </div>
                
                <div class="controls">
                    <button id="play-button" class="control-button">▶️ Play Streaming</button>
                    <button id="stop-button" class="control-button stop" disabled>⏹️ Stop</button>
                    <span class="status">Ready</span>
                </div>
                
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">0%</div>
                </div>
            </div>
        `;
    }
}

// Register the custom element
customElements.define('streaming-audio-player', StreamingAudioPlayer);

// Auto-inject into TTS configuration or service pages
document.addEventListener('DOMContentLoaded', function() {
    function addStreamingPlayer() {
        // Look for TTS-related pages or forms
        const ttsElements = document.querySelector('[data-domain="voice_assistant_gemini"]') ||
                           document.querySelector('.voice-assistant') ||
                           document.querySelector('[data-service="tts"]');
        
        if (ttsElements && !document.querySelector('streaming-audio-player')) {
            const streamingPlayer = document.createElement('streaming-audio-player');
            streamingPlayer.setAttribute('text', 'This is a demonstration of streaming text-to-speech. The audio will start playing as soon as the first chunk is ready, providing a much faster experience for longer texts.');
            streamingPlayer.setAttribute('voice', 'Kore');
            streamingPlayer.setAttribute('emotion', 'friendly');
            streamingPlayer.setAttribute('tone-style', 'conversational');
            
            ttsElements.appendChild(streamingPlayer);
        }
    }
    
    // Try to add player immediately
    addStreamingPlayer();
    
    // Also watch for dynamic content loading
    const observer = new MutationObserver(addStreamingPlayer);
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}); 