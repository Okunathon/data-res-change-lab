// Get case study from URL parameter
function getCaseStudyFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('study') || 'template1';
}

// Case study titles
const caseStudyTitles = {
    template1: 'Dr. Jennifer Walker',
    template2: 'Case Study Template 2',
    template3: 'Case Study Template 3'
};

// API Configuration
const API_URL = 'http://localhost:8080';
const SESSION_ID = `session_${Date.now()}`;

// Audio recording variables
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let recordingStartTime = 0;

// Feedback tracking
let voiceExchangeCount = 0;
let userMessages = [];
let aiResponses = [];
let feedbackShown = false;
const FEEDBACK_THRESHOLD = 8;

// Initialize chatbot
document.addEventListener('DOMContentLoaded', () => {
    // Only run on simulation page
    if (!document.getElementById('chatMessages')) return;
    
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const messageCountEl = document.getElementById('messageCount');
    const caseStudyNameEl = document.getElementById('caseStudyName');
    
    // Voice mode elements
    const textModeBtn = document.getElementById('textModeBtn');
    const voiceModeBtn = document.getElementById('voiceModeBtn');
    const textInputSection = document.getElementById('textInputSection');
    const voiceInputSection = document.getElementById('voiceInputSection');
    const recordButton = document.getElementById('recordButton');
    const recordIcon = document.getElementById('recordIcon');
    const recordText = document.getElementById('recordText');
    const recordingStatus = document.getElementById('recordingStatus');
    
    let messageCount = 0;
    let currentMode = 'text';
    let isMuted = false;  // Track mute state
    const studyKey = getCaseStudyFromURL();
    
    // Update case study name
    if (caseStudyNameEl) {
        caseStudyNameEl.textContent = caseStudyTitles[studyKey] || 'SaaS Startup';
    }
    
    // Update simulation title
    const simulationTitle = document.getElementById('simulationTitle');
    if (simulationTitle) {
        simulationTitle.textContent = `${caseStudyTitles[studyKey]} Pitch`;
    }
    
    // Mode toggle handlers
    textModeBtn.addEventListener('click', () => {
        currentMode = 'text';
        textModeBtn.classList.add('active');
        voiceModeBtn.classList.remove('active');
        textInputSection.style.display = 'flex';
        voiceInputSection.style.display = 'none';
    });
    
    voiceModeBtn.addEventListener('click', () => {
        currentMode = 'voice';
        voiceModeBtn.classList.add('active');
        textModeBtn.classList.remove('active');
        textInputSection.style.display = 'none';
        voiceInputSection.style.display = 'block';
    });
    
    // Mute button handler
    const muteToggle = document.getElementById('muteToggle');
    if (muteToggle) {
        muteToggle.addEventListener('click', () => {
            isMuted = !isMuted;
            muteToggle.textContent = isMuted ? '🔇' : '🔊';
            muteToggle.classList.toggle('muted', isMuted);
        });
    }
    
    // Jennifer avatar state manager
    function updateJenniferState(state) {
        const avatar = document.getElementById('jenniferAvatar');
        const status = document.getElementById('jenniferStatus');
        
        if (!avatar || !status) return;
        
        const states = {
            listening: { emoji: '👂', text: 'Listening...' },
            thinking: { emoji: '🤔', text: 'Thinking...' },
            happy: { emoji: '😊', text: 'Impressed!' },
            talking: { emoji: '👩🏾‍🔬', text: 'Speaking...' },
            interested: { emoji: '👀', text: 'Interested...' },
            skeptical: { emoji: '🤨', text: 'Skeptical...' }
        };
        
        const stateData = states[state] || states.listening;
        avatar.textContent = stateData.emoji;
        status.textContent = stateData.text;
        
        // Add animation pulse
        avatar.style.animation = 'none';
        setTimeout(() => {
            avatar.style.animation = 'pulse-avatar 1s ease-in-out';
        }, 10);
    }
    
    // Function to add a message to the chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = isUser ? '👤' : '👩🏾‍🔬';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messagePara = document.createElement('p');
        messagePara.textContent = content;
        messageContent.appendChild(messagePara);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        messageCount++;
        if (messageCountEl) {
            messageCountEl.textContent = messageCount;
        }
    }
    
    // Function to add audio message with player
    function addAudioMessage(audioUrl) {
        console.log('[Audio] Adding audio player with URL:', audioUrl);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '👩🏾‍🔬';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const audioPlayer = document.createElement('audio');
        audioPlayer.controls = true;
        audioPlayer.autoplay = true;
        audioPlayer.src = audioUrl;
        audioPlayer.className = 'audio-player';
        
        // Add error handling
        audioPlayer.onerror = (e) => {
            console.error('[Audio] Error loading audio:', e);
            console.error('[Audio] Error details:', audioPlayer.error);
            const errorMsg = document.createElement('p');
            errorMsg.textContent = '⚠️ Audio failed to load';
            errorMsg.style.color = '#e53e3e';
            messageContent.appendChild(errorMsg);
        };
        
        audioPlayer.onloadeddata = () => {
            console.log('[Audio] Audio loaded successfully');
        };
        
        audioPlayer.onplay = () => {
            console.log('[Audio] Audio started playing');
        };
        
        messageContent.appendChild(audioPlayer);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        messageCount++;
        if (messageCountEl) {
            messageCountEl.textContent = messageCount;
        }
    }
    
    // Function to show loading indicator
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message ai-message loading-message';
        loadingDiv.id = 'loadingMessage';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '👩🏾‍🔬';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = '<p>Thinking...</p>';
        
        loadingDiv.appendChild(avatar);
        loadingDiv.appendChild(messageContent);
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function removeLoading() {
        const loadingMsg = document.getElementById('loadingMessage');
        if (loadingMsg) loadingMsg.remove();
    }
    
    // Function to send text message
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        addMessage(message, true);
        userInput.value = '';
        userMessages.push(message);
        
        updateJenniferState('thinking');
        
        // Show loading
        showLoading();
        
        // Send to API
        sendTextMessage(message);
    }
    
    // Function to send text message to API
    async function sendTextMessage(userMessage) {
        try {
            console.log('[Text] Sending message to API...');
            console.log('[Text] Message:', userMessage);
            
            const response = await fetch(`${API_URL}/api/chat-text`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: userMessage,
                    session_id: SESSION_ID,
                    case_study: studyKey,
                    with_audio: !isMuted  // Only generate audio if not muted
                })
            });
            
            console.log('[Text] Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Text] API error response:', errorText);
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = { error: errorText };
                }
                throw new Error(errorData.error || 'API request failed');
            }
            
            const data = await response.json();
            console.log('[Text] API response:', data);
            
            removeLoading();
            
            // Update Jennifer's state based on response sentiment
            const replyLower = data.reply.toLowerCase();
            if (replyLower.includes('great') || replyLower.includes('excellent') || replyLower.includes('impressive')) {
                updateJenniferState('happy');
            } else if (replyLower.includes('question') || replyLower.includes('tell me') || replyLower.includes('interesting')) {
                updateJenniferState('interested');
            } else if (replyLower.includes('concern') || replyLower.includes('unclear') || replyLower.includes('not sure')) {
                updateJenniferState('skeptical');
            } else {
                updateJenniferState('listening');
            }
            
            // Add AI's text response
            addMessage(data.reply, false);
            aiResponses.push(data.reply);
            
            // Update Jennifer to talking state
            updateJenniferState('talking');
            
            // Add and play audio response if available and not muted
            if (data.audio_url && !isMuted) {
                const audioUrl = `${API_URL}${data.audio_url}`;
                console.log('[Text] Audio URL:', audioUrl);
                addAudioMessage(audioUrl);
            }
            
            // Increment exchange count and check if feedback should be shown
            voiceExchangeCount++;
            console.log('[Feedback] Text exchanges:', voiceExchangeCount);
            if (voiceExchangeCount >= FEEDBACK_THRESHOLD && !feedbackShown) {
                console.log('[Feedback] Threshold reached! Showing feedback modal...');
                feedbackShown = true;
                setTimeout(() => showFeedbackModal(), 2000);
            }
            
        } catch (error) {
            removeLoading();
            console.error('[Text] Error:', error);
            console.error('[Text] Error stack:', error.stack);
            addMessage(`Error: ${error.message}. Check console for details.`, false);
        }
    }
    
    // Function to send voice message to API
    async function sendVoiceMessage(audioBlob) {
        try {
            console.log('[Voice] Sending audio to API...');
            console.log('[Voice] Audio blob size:', audioBlob.size, 'bytes');
            console.log('[Voice] Audio blob type:', audioBlob.type);
            
            updateJenniferState('thinking');
            
            showLoading();
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            formData.append('session_id', SESSION_ID);
            formData.append('case_study', studyKey);
            
            console.log('[Voice] Making API request to:', `${API_URL}/api/chat`);
            console.log('[Voice] FormData contents:', {
                audio_size: audioBlob.size,
                session_id: SESSION_ID,
                case_study: studyKey
            });
            
            const response = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                body: formData
            });
            
            console.log('[Voice] Response status:', response.status);
            console.log('[Voice] Response headers:', [...response.headers.entries()]);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Voice] API error response:', errorText);
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = { error: errorText };
                }
                throw new Error(errorData.error || 'API request failed');
            }
            
            const data = await response.json();
            console.log('[Voice] API response:', data);
            
            removeLoading();
            
            // Update Jennifer's state based on response sentiment
            const replyLower = data.reply.toLowerCase();
            if (replyLower.includes('great') || replyLower.includes('excellent') || replyLower.includes('impressive')) {
                updateJenniferState('happy');
            } else if (replyLower.includes('question') || replyLower.includes('tell me') || replyLower.includes('interesting')) {
                updateJenniferState('interested');
            } else if (replyLower.includes('concern') || replyLower.includes('unclear') || replyLower.includes('not sure')) {
                updateJenniferState('skeptical');
            } else {
                updateJenniferState('listening');
            }
            
            // Add user's transcribed message
            addMessage(data.transcript, true);
            userMessages.push(data.transcript);
            
            // Update Jennifer to talking state
            updateJenniferState('talking');
            
            // Add AI's text response
            addMessage(data.reply, false);
            aiResponses.push(data.reply);
            
            // Add and play audio response
            const audioUrl = `${API_URL}${data.audio_url}`;
            console.log('[Voice] Audio URL:', audioUrl);
            addAudioMessage(audioUrl);
            
            // Increment voice exchange count and check if feedback should be shown
            voiceExchangeCount++;
            console.log('[Feedback] Voice exchanges:', voiceExchangeCount);
            if (voiceExchangeCount >= FEEDBACK_THRESHOLD && !feedbackShown) {
                console.log('[Feedback] Threshold reached! Showing feedback modal...');
                feedbackShown = true;
                setTimeout(() => showFeedbackModal(), 2000);
            }
            
        } catch (error) {
            removeLoading();
            console.error('[Voice] Error:', error);
            console.error('[Voice] Error stack:', error.stack);
            addMessage(`Error: ${error.message}. Check console for details.`, false);
        }
    }
    
    // Audio recording setup
    async function setupAudioRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });
            
            // Try different MIME types in order of preference
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                console.log('[Voice] audio/webm;codecs=opus not supported');
                mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    console.log('[Voice] audio/webm not supported');
                    mimeType = 'audio/mp4';
                    if (!MediaRecorder.isTypeSupported(mimeType)) {
                        console.log('[Voice] audio/mp4 not supported, using default');
                        mimeType = '';
                    }
                }
            }
            
            console.log('[Voice] Using MIME type:', mimeType || 'default');
            
            const options = mimeType ? { mimeType } : {};
            mediaRecorder = new MediaRecorder(stream, options);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                const mimeType = mediaRecorder.mimeType || 'audio/webm';
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                console.log('[Voice] Created blob with type:', audioBlob.type, 'size:', audioBlob.size);
                audioChunks = [];
                
                recordingStatus.textContent = 'Processing...';
                await sendVoiceMessage(audioBlob);
                recordingStatus.textContent = '';
            };
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('Could not access microphone. Please check permissions.');
        }
    }
    
    // Record button handlers
    recordButton.addEventListener('mousedown', async () => {
        if (!mediaRecorder) {
            await setupAudioRecording();
        }
        
        if (mediaRecorder && !isRecording) {
            audioChunks = [];
            recordingStartTime = Date.now();
            console.log('[Voice] Starting recording...');
            mediaRecorder.start();
            isRecording = true;
            
            recordButton.classList.add('recording');
            recordIcon.textContent = '⏺️';
            recordText.textContent = 'Recording...';
            recordingStatus.textContent = 'Recording... Release to send';
        }
    });
    
    recordButton.addEventListener('mouseup', () => {
        if (mediaRecorder && isRecording) {
            const recordingDuration = Date.now() - recordingStartTime;
            console.log('[Voice] Stopping recording... Duration:', recordingDuration, 'ms');
            
            if (recordingDuration < 500) {
                console.log('[Voice] Recording too short, ignoring');
                mediaRecorder.stop();
                isRecording = false;
                audioChunks = [];
                
                recordButton.classList.remove('recording');
                recordIcon.textContent = '🎤';
                recordText.textContent = 'Hold to Record';
                recordingStatus.textContent = 'Recording too short! Hold longer.';
                setTimeout(() => {
                    recordingStatus.textContent = '';
                }, 2000);
                return;
            }
            
            mediaRecorder.stop();
            isRecording = false;
            
            recordButton.classList.remove('recording');
            recordIcon.textContent = '🎤';
            recordText.textContent = 'Hold to Record';
        }
    });
    
    recordButton.addEventListener('mouseleave', () => {
        if (isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            
            recordButton.classList.remove('recording');
            recordIcon.textContent = '🎤';
            recordText.textContent = 'Hold to Record';
        }
    });
    
    // Text input event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Feedback modal functions
    function generateFeedback() {
        // Analyze conversation
        const avgUserMessageLength = userMessages.reduce((sum, msg) => sum + msg.split(' ').length, 0) / userMessages.length || 0;
        const hasNumbers = userMessages.some(msg => /\d+/.test(msg));
        const hasProfessionalTone = userMessages.some(msg => 
            /(budget|impact|metrics|outcomes|data|results|roi)/i.test(msg)
        );
        const hasCasualLanguage = userMessages.some(msg => 
            /(hey|hi|yeah|cool|awesome|basically)/i.test(msg)
        );
        
        // Calculate score (0-100)
        let score = 65;
        if (hasProfessionalTone) score += 15;
        if (hasNumbers) score += 10;
        if (avgUserMessageLength > 10 && avgUserMessageLength < 50) score += 10;
        if (!hasCasualLanguage) score += 5;
        if (voiceExchangeCount >= 10) score += 5;
        
        const strengths = [];
        const improvements = [];
        
        // Generate strengths
        if (hasProfessionalTone) {
            strengths.push('Used professional language and industry terminology');
        }
        if (hasNumbers) {
            strengths.push('Included specific numbers and metrics in your pitch');
        }
        if (avgUserMessageLength > 10) {
            strengths.push('Provided detailed, thoughtful responses');
        }
        if (voiceExchangeCount >= 10) {
            strengths.push('Maintained engagement throughout the conversation');
        }
        
        // Generate improvements
        if (!hasProfessionalTone) {
            improvements.push('Incorporate more professional terminology and focus on measurable outcomes');
        }
        if (!hasNumbers) {
            improvements.push('Include specific numbers, budgets, and metrics to strengthen your pitch');
        }
        if (hasCasualLanguage) {
            improvements.push('Maintain a more professional tone and avoid casual language');
        }
        if (avgUserMessageLength < 10) {
            improvements.push('Provide more detailed explanations and context in your responses');
        }
        if (avgUserMessageLength > 50) {
            improvements.push('Keep responses more concise and focused to respect the donor\'s time');
        }
        
        // Default fallbacks
        if (strengths.length === 0) {
            strengths.push('Completed the practice session and engaged with the simulation');
        }
        if (improvements.length === 0) {
            improvements.push('Continue practicing to refine your pitch delivery');
        }
        
        return {
            score: Math.min(100, score),
            strengths,
            improvements,
            insights: {
                exchanges: voiceExchangeCount,
                avgLength: Math.round(avgUserMessageLength),
                professionalTerms: userMessages.filter(msg => 
                    /(budget|impact|metrics|outcomes|data|results)/i.test(msg)
                ).length
            }
        };
    }
    
    function showFeedbackModal() {
        const modal = document.getElementById('feedbackModal');
        if (!modal) return;
        
        const feedback = generateFeedback();
        
        // Populate score
        document.getElementById('performanceScore').textContent = `${feedback.score}/100`;
        
        // Populate strengths
        const strengthsList = document.getElementById('strengthsList');
        strengthsList.innerHTML = feedback.strengths.map(s => `<li>${s}</li>`).join('');
        
        // Populate improvements
        const improvementsList = document.getElementById('improvementsList');
        improvementsList.innerHTML = feedback.improvements.map(i => `<li>${i}</li>`).join('');
        
        // Populate insights
        const insightsList = document.getElementById('insightsList');
        insightsList.innerHTML = `
            <div class="insight-card">
                <div class="insight-value">${feedback.insights.exchanges}</div>
                <div class="insight-label">Exchanges</div>
            </div>
            <div class="insight-card">
                <div class="insight-value">${feedback.insights.avgLength}</div>
                <div class="insight-label">Avg Words/Response</div>
            </div>
            <div class="insight-card">
                <div class="insight-value">${feedback.insights.professionalTerms}</div>
                <div class="insight-label">Professional Terms</div>
            </div>
        `;
        
        // Set up assessment scale handlers
        const assessmentRadios = document.querySelectorAll('input[name="assessment"]');
        const assessmentNote = document.getElementById('assessmentNote');
        const assessmentNotes = {
            '0': "You may want to practice more before pitching to investors.",
            '25': "Good start! Keep refining your pitch.",
            '50': "You're on the right track. Work on the details.",
            '75': "Excellent! Very close to investment-ready.",
            '100': "Outstanding! Ready for real investor pitches."
        };
        
        assessmentRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                const value = e.target.value;
                assessmentNote.textContent = assessmentNotes[value];
                assessmentNote.style.display = 'block';
            });
        });
        
        // Set up review link
        const reviewLink = document.querySelector('.review-link');
        if (reviewLink) {
            reviewLink.onclick = (e) => {
                e.preventDefault();
                alert('Thank you for your feedback! This would normally open a review form.');
            };
        }
        
        modal.classList.add('show');
        
        // Set up modal event handlers
        document.getElementById('closeFeedback').onclick = () => modal.classList.remove('show');
        document.getElementById('continuePractice').onclick = () => modal.classList.remove('show');
        document.getElementById('startNewSession').onclick = () => {
            window.location.reload();
        };
        
        // Close on outside click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        };
    }
});
