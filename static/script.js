document.addEventListener('DOMContentLoaded', function() {
    console.log("Document loaded - script running!");
    
    // Handle dropdown navigation for mobile users
    const navToggle = document.querySelector('.nav-toggle');
    const navContent = document.querySelector('.nav-content');

    if (navToggle && navContent) {
        navToggle.addEventListener('click', function() {
            navContent.style.display = navContent.style.display === 'block' ? 'none' : 'block';
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!navToggle.contains(e.target) && !navContent.contains(e.target)) {
                navContent.style.display = 'none';
            }
        });
    }
    
    // Handle consent toggle for OAuth features if the element exists
    const consentCheckbox = document.getElementById('consent');
    if (consentCheckbox) {
        consentCheckbox.addEventListener('change', async function() {
            await fetch('/set-consent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ consent: this.checked })
            }).then(response => {
                if (response.ok) {
                    console.log(`OAuth consent set to: ${this.checked}`);
                } else {
                    console.error('Failed to set consent status');
                }
            }).catch(err => {
                console.error('Error setting consent:', err);
            });
        });
    }
    
    // Import data collector and prompt integration
    Promise.all([
        import('/static/data_collection.js'),
        import('/static/prompt-integration.js')
    ]).then(([dataCollectorModule, promptIntegrationModule]) => {
        // Store modules globally for later use
        window.LolaDataCollector = dataCollectorModule.default;
        window.promptIntegration = promptIntegrationModule;
        
        // Initialize data collector with default settings
        window.LolaDataCollector.initialize();
        console.log("Data collector initialized");
        
        // Set up periodic updates to keep AI context fresh
        setInterval(() => {
            promptIntegrationModule.updateAIPrompt();
        }, 300000); // Update every 5 minutes
        
        // Show the opt-in experience after a delay
        setTimeout(() => {
            // Only show if the user hasn't made a choice yet
            if (!localStorage.getItem('lola_enhancedExperienceShown')) {
                window.LolaDataCollector.offerEnhancedExperience((choice) => {
                    console.log(`User chose ${choice ? 'enhanced' : 'basic'} experience`);
                    localStorage.setItem('lola_enhancedExperienceShown', 'true');
                    
                    // Force an immediate update after the choice is made
                    promptIntegrationModule.updateAIPrompt();
                });
            }
        }, 30000); // Show after 30 seconds
    }).catch(error => {
        console.error("Error loading modules:", error);
    });
    
    // Simplified viewport height function
    function setVh() {
        let vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
        console.log("Viewport height set");
    }
    
    // Set the value initially and on resize/orientation change
    setVh();
    window.addEventListener('resize', () => {
        setTimeout(setVh, 100);
    });
    window.addEventListener('orientationchange', () => {
        setTimeout(setVh, 100);
    });
    
    // Fix for double-tap zoom on mobile
    document.addEventListener('touchstart', function(e) {
        if (e.touches.length > 1) {
            e.preventDefault();
        }
    }, { passive: false });
    // DOM Elements
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const resetButton = document.getElementById('reset-button');
    const backToLandingButton = document.getElementById('back-to-landing');
    const startChatButton = document.getElementById('start-chat-button');
    const landingSection = document.getElementById('landing-section');
    const chatSection = document.getElementById('chat-section');
    const quickLinkButtons = document.querySelectorAll('.quick-link-btn');
    
    // State variables
    let isWaitingForResponse = false;
    
    // Set up quick link buttons
    quickLinkButtons.forEach(button => {
        button.addEventListener('click', function() {
            const message = this.getAttribute('data-message');
            if (message && !isWaitingForResponse) {
                userInput.value = message;
                sendMessage();
            }
        });
    });
    
    // First check if backend is responding
    let backendChecked = false;
    let backendAvailable = false;
    
    // Direct S3 image URLs
    const s3BaseUrl = "https://aboutbrooks.s3.us-east-1.amazonaws.com";
    const s3Images = {
        profileImage: `${s3BaseUrl}/Me%20on%20a%20boat%20in%20Alabama.jpeg`,
        workshop: `${s3BaseUrl}/Workshop.jpeg`,
        fishing: `${s3BaseUrl}/Sailfish.jpeg`,
        reading: `${s3BaseUrl}/Book%20Vase.jpeg`,
        projects: `${s3BaseUrl}/Carrier%20Pigeons.jpeg`
    };
    
    // Try to load profile image from S3 directly
    function tryLoadS3Images() {
        console.log("Loading S3 images directly...");
        
        // Try to set profile image if element exists
        const profileImg = document.getElementById('profile-image');
        const placeholder = document.getElementById('profile-image-placeholder');
        
        if (profileImg && placeholder) {
            profileImg.src = s3Images.profileImage;
            profileImg.onload = function() {
                placeholder.style.display = 'none';
                profileImg.style.display = 'block';
                console.log("S3 profile image loaded successfully");
            };
            profileImg.onerror = function() {
                console.log("Failed to load S3 profile image");
            };
        } else {
            console.log("Profile image elements not found in the DOM");
        }
    }
    
    // Try to load S3 images on page load
    setTimeout(tryLoadS3Images, 1000);
    
    // Check if backend APIs are available
    function checkBackendStatus() {
        if (backendChecked) return Promise.resolve(backendAvailable);
        
        console.log("Checking backend status...");
        
        // Try the simple test endpoint
        return fetch('/test')
            .then(response => {
                if (response.ok) {
                    console.log("API test endpoint is responding!");
                    backendChecked = true;
                    backendAvailable = true;
                    return true;
                } else {
                    console.error("API test is not responding:", response.status);
                    backendChecked = true;
                    backendAvailable = false;
                    throw new Error(`API returned status ${response.status}`);
                }
            })
            .catch(error => {
                console.error("Error checking backend:", error);
                backendChecked = true;
                backendAvailable = false;
                
                // Show a notice about backend issues
                const staticNotice = document.createElement('div');
                staticNotice.style.position = 'fixed';
                staticNotice.style.bottom = '10px';
                staticNotice.style.right = '10px';
                staticNotice.style.background = 'rgba(230, 126, 34, 0.7)';
                staticNotice.style.color = 'white';
                staticNotice.style.padding = '10px';
                staticNotice.style.borderRadius = '5px';
                staticNotice.style.zIndex = '1000';
                staticNotice.style.maxWidth = '300px';
                staticNotice.innerHTML = `Backend services unavailable. Chat functionality limited.`;
                
                // Auto-hide after 5 seconds
                setTimeout(() => {
                    staticNotice.style.opacity = '0';
                    staticNotice.style.transition = 'opacity 1s';
                    setTimeout(() => staticNotice.remove(), 1000);
                }, 5000);
                
                document.body.appendChild(staticNotice);
                
                return false;
            });
    }
    
    // Fun fact button handler
    const funFactButton = document.getElementById('fun-fact-button');
    if (funFactButton) {
        funFactButton.addEventListener('click', function() {
            fetch('/api/simple-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_input: 'Tell me a fun fact about Brooks!' })
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.response) {
                    // Show the fun fact in a popup or alert
                    alert(data.response);
                    // Optionally, auto-start the chat
                    startChatButton.click();
                }
            })
            .catch(error => {
                console.error('Error fetching fun fact:', error);
                alert("Oops, couldn't fetch a fun fact. Let's chat instead!");
                startChatButton.click();
            });
        });
    }
    
    // Landing page transitions
    startChatButton.addEventListener('click', function() {
        // First check if backend is available
        checkBackendStatus().then(isAvailable => {
            // Switch to chat view
            landingSection.style.display = 'none';
            chatSection.style.display = 'block';
            resetButton.style.display = 'block';
            backToLandingButton.style.display = 'block';
            
            // Initialize chat with a greeting
            if (chatMessages.children.length === 0) {
                addTypingIndicator();
                
                if (!isAvailable) {
                    // If backend isn't responding, show a fallback message
                    setTimeout(() => {
                        removeTypingIndicator();
                        addMessage('Hi there! 👋 I\'m Brooks\' personal AI assistant. Our servers are currently busy. Please try again later!', 'assistant');
                    }, 1000);
                    return;
                }
                
                window.setTimeout(() => {
                    removeTypingIndicator();
                    
                    // Try the simple chat endpoint
                    fetch('/api/simple-chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ user_input: 'hello' })
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`API returned status ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data && data.response) {
                            addMessage(data.response, 'assistant');
                        } else {
                            throw new Error('Invalid response format');
                        }
                    })
                    .catch(error => {
                        console.error('Error starting conversation:', error);
                        addMessage('Hi there! 👋 I\'m Brooks\' personal AI assistant. Ask me anything about him, his interests, projects, or background!', 'assistant');
                    });
                }, 1000);
            }
        });
    });
    
    backToLandingButton.addEventListener('click', function() {
        chatSection.style.display = 'none';
        landingSection.style.display = 'flex';
        resetButton.style.display = 'none';
        backToLandingButton.style.display = 'none';
    });
    
    // Event Listeners for chat
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !isWaitingForResponse && userInput.value.trim() !== '') {
            sendMessage();
        }
    });
    
    sendButton.addEventListener('click', function() {
        if (!isWaitingForResponse && userInput.value.trim() !== '') {
            sendMessage();
        }
    });
    
    resetButton.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset this conversation?')) {
            resetConversation();
        }
    });
    
    // Apply a solid color background for the hero banner for now
    try {
        const heroBanner = document.querySelector('.hero-banner');
        if (heroBanner) {
            // Use a gradient background instead of an image
            heroBanner.style.backgroundImage = 'linear-gradient(to right, rgba(52, 152, 219, 0.8), rgba(41, 128, 185, 0.9))';
        }
    } catch (e) {
        console.log('Error setting hero banner style', e);
    }
    
    // Helper Functions
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        
        // Message text container
        const textContainer = document.createElement('div');
        textContainer.className = 'message-text';
        
        // Detect photo links and replace them with inline images
        // Updated regex to handle S3 URLs and URL encoded characters
        const photoLinkRegex = /(https:\/\/aboutbrooks\.s3\.us-east-1\.amazonaws\.com\/[^\s"'<>]+\.(jpeg|jpg|png|mov))/g;
        let messageText = text;
        const links = messageText.match(photoLinkRegex);
        
        if (links) {
            // First, split the message by found links
            let parts = messageText.split(photoLinkRegex);
            messageText = '';
            
            // Then reassemble with proper breaks
            let linkIndex = 0;
            for (let i = 0; i < parts.length; i++) {
                // Add text part
                messageText += parts[i];
                
                // Add link if we have one
                if (linkIndex < links.length && i < parts.length - 1) {
                    messageText += `<br><div class="inline-photo-container" data-src="${links[linkIndex]}"></div><br>`;
                    linkIndex++;
                }
            }
        }
        
        textContainer.innerHTML = messageText;
        messageDiv.appendChild(textContainer);
        
        // Add feedback button for assistant messages
        if (sender === 'assistant') {
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback';
            feedbackDiv.innerHTML = `
                <span>Was this helpful?</span>
                <button class="feedback-btn" data-value="yes">Yes</button>
                <button class="feedback-btn" data-value="no">No</button>
            `;
            messageDiv.appendChild(feedbackDiv);
        }
        
        // Load inline images
        if (links) {
            const containers = textContainer.querySelectorAll('.inline-photo-container');
            containers.forEach(container => {
                const src = container.getAttribute('data-src');
                const img = document.createElement('img');
                img.className = 'inline-photo';
                img.alt = 'Photo shared by Brooks\' AI assistant';
                img.style.maxWidth = '250px';
                img.style.margin = '10px 0';
                img.style.cursor = 'pointer';
                img.style.display = 'block';
                
                // Add loading spinner
                const spinner = document.createElement('div');
                spinner.className = 'photo-loading-spinner';
                spinner.innerHTML = '<div class="spinner"></div>';
                container.appendChild(spinner);
                
                // Try to fix double extension issues if they occur
                let cleanSrc = src;
                // Fix potential double extensions like .jpeg.jpeg
                const extensionRegex = /\.(jpeg|jpg|png|mov)(\.(jpeg|jpg|png|mov))$/i;
                if (extensionRegex.test(cleanSrc)) {
                    cleanSrc = cleanSrc.replace(extensionRegex, '.$1');
                    console.log("Fixed double extension in URL:", cleanSrc);
                }
                
                img.onload = () => {
                    spinner.remove();
                    container.appendChild(img);
                };
                
                img.onerror = () => {
                    spinner.remove();
                    console.error("Failed to load image:", cleanSrc);
                    container.innerHTML = '<p style="color: red;">Failed to load image.</p>';
                };
                
                img.src = cleanSrc;
                
                // Make image expandable
                img.addEventListener('click', () => {
                    // Simulate a photo object for the modal
                    const filename = src.split('/').pop();
                    const photo = {
                        filename: filename,
                        title: filename.split('.')[0].replace(/-/g, ' '),
                        description: `Shared by Brooks' AI assistant`
                    };
                    openPhotoModal(photo);
                });
            });
        }
        
        // Add timestamp
        const timeSpan = document.createElement('div');
        timeSpan.classList.add('message-time');
        const now = new Date();
        timeSpan.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timeSpan);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    function addTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.classList.add('typing-indicator');
        indicator.innerHTML = '<span></span><span></span><span></span>';
        indicator.id = 'typing-indicator';
        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message || isWaitingForResponse) {
            return;
        }
        
        userInput.value = '';
        addMessage(message, 'user');
        addTypingIndicator();
        isWaitingForResponse = true;
        
        // Get user data from collector if available
        let userData = null;
        if (window.LolaDataCollector) {
            userData = window.LolaDataCollector.getAllData();
            console.log("Including user data in request:", userData);
        }
        
        // Try the API routes in order with user data - first try the primary /chat endpoint
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                user_input: message,
                user_data: userData
            })
        })
        .then(response => {
            if (!response.ok) {
                console.log(`Main chat endpoint failed with status: ${response.status}. Trying fallback...`);
                // If main endpoint fails, try the simple-chat endpoint
                return tryFallbackChat(message);
            }
            return response.json();
        })
        .then(data => {
            removeTypingIndicator();
            if (data && data.response) {
                addMessage(data.response, 'assistant');
            } else {
                throw new Error('Invalid response format');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Sorry, I encountered an error. Please try again or reset the conversation.', 'assistant');
        })
        .finally(() => {
            isWaitingForResponse = false;
            userInput.focus(); // Refocus input for better UX
        });
    }
    
    // Fallback chat function that uses the simple-chat endpoint
    function tryFallbackChat(message) {
        console.log("Trying fallback chat endpoint...");
        
        // Get user data from collector if available (simplified for fallback)
        let userData = null;
        if (window.LolaDataCollector) {
            userData = {
                deviceType: window.LolaDataCollector.userData.basic.deviceType,
                visitTime: window.LolaDataCollector.userData.basic.visitTime
            };
        }
        
        return fetch('/api/simple-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                user_input: message,
                user_data: userData
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Fallback chat also failed: ${response.statusText}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Fallback chat error:', error);
            throw error; // Rethrow to handle in the main chain
        });
    }
    
    function resetConversation() {
        chatMessages.innerHTML = '';
        console.log('Conversation reset locally');
        
        // Simple local reset (serverless doesn't maintain session state)
        addTypingIndicator();
        
        setTimeout(() => {
            removeTypingIndicator();
            
            // Try to get a welcome message from the API
            fetch('/api/simple-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_input: 'hello' })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API returned status ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.response) {
                    addMessage(data.response, 'assistant');
                } else {
                    throw new Error('Invalid response format');
                }
            })
            .catch(error => {
                console.error('Error starting conversation after reset:', error);
                addMessage('Hi there! 👋 I\'m Brooks\' personal AI assistant. Our conversation has been reset. What would you like to know?', 'assistant');
            });
        }, 1000);
    }
    
    // Photo modal functionality
    function openPhotoModal(photo) {
        let photoModal = document.getElementById('photo-modal');
        
        if (!photoModal) {
            photoModal = document.createElement('div');
            photoModal.id = 'photo-modal';
            photoModal.className = 'photo-modal';
            document.body.appendChild(photoModal);
            
            photoModal.addEventListener('click', function(e) {
                if (e.target === photoModal) {
                    closePhotoModal();
                }
            });
        }
        
        photoModal.innerHTML = '';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'photo-modal-content';
        
        const img = document.createElement('img');
        
        // Get the source URL and check for double extensions
        let imgSrc = photo.filename.includes('aboutbrooks.s3') ? 
            photo.filename : 
            `https://aboutbrooks.s3.us-east-1.amazonaws.com/${photo.filename}`;
            
        // Fix potential double extensions like .jpeg.jpeg
        const extensionRegex = /\.(jpeg|jpg|png|mov)(\.(jpeg|jpg|png|mov))$/i;
        if (extensionRegex.test(imgSrc)) {
            imgSrc = imgSrc.replace(extensionRegex, '.$1');
            console.log("Fixed double extension in modal URL:", imgSrc);
        }
        
        img.src = imgSrc;
        img.alt = photo.title;
        
        const caption = document.createElement('div');
        caption.className = 'photo-modal-caption';
        caption.innerHTML = `<h3>${photo.title}</h3><p>${photo.description}</p>`;
        
        const closeBtn = document.createElement('span');
        closeBtn.className = 'photo-modal-close';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', closePhotoModal);
        
        modalContent.appendChild(closeBtn);
        modalContent.appendChild(img);
        modalContent.appendChild(caption);
        photoModal.appendChild(modalContent);
        
        photoModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    function closePhotoModal() {
        const modal = document.getElementById('photo-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        document.body.style.overflow = 'auto';
    }
    
    // Add keyboard event listener for ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });
    
    // Add feedback handling
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('feedback-btn')) {
            const value = e.target.getAttribute('data-value');
            const messageDiv = e.target.closest('.message');
            const messageText = messageDiv.querySelector('.message-text').textContent;
            
            // Send feedback to the server
            fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    feedback: value
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    e.target.parentElement.innerHTML = 'Thanks for your feedback!';
                }
            })
            .catch(error => {
                console.error('Error submitting feedback:', error);
            });
        }
    });

    // Accessibility improvements
    sendButton.setAttribute('aria-label', 'Send message');
    resetButton.setAttribute('aria-label', 'Reset conversation');
    backToLandingButton.setAttribute('aria-label', 'Back to landing page');
    startChatButton.setAttribute('aria-label', 'Start chatting with Brooks\' AI assistant');
    userInput.setAttribute('aria-label', 'Type your message here');
});