document.addEventListener('DOMContentLoaded', function() {
    // Fix for mobile viewport height issues with browsers
    function setVh() {
        let vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
        
        // Additional fix for chat container height
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            // Make sure the chat container is properly sized based on available space
            const windowHeight = window.innerHeight;
            const headerHeight = document.querySelector('header')?.offsetHeight || 0;
            const footerHeight = document.querySelector('footer')?.offsetHeight || 0;
            const welcomeMessageHeight = document.querySelector('.welcome-message')?.offsetHeight || 0;
            const mainPadding = 40; // 20px top + 20px bottom
            const quickLinksHeight = document.querySelector('.quick-links')?.offsetHeight || 0;
            const inputAreaHeight = document.querySelector('.input-area')?.offsetHeight || 0;
            
            // Set a reasonable height that fits the viewport
            // Subtract the height of the quick links to ensure they're always visible
            const availableHeight = windowHeight - headerHeight - footerHeight - mainPadding - welcomeMessageHeight;
            
            // Set height for the container
            chatContainer.style.maxHeight = `${availableHeight}px`;
            
            // Adjust chat messages area to make room for input and quick links
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages) {
                chatMessages.style.maxHeight = `${availableHeight - inputAreaHeight - quickLinksHeight}px`;
                chatMessages.style.height = `${availableHeight - inputAreaHeight - quickLinksHeight}px`;
            }
            
            console.log(`Window height: ${windowHeight}, Available: ${availableHeight}, Quick links: ${quickLinksHeight}, Input: ${inputAreaHeight}`);
        }
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
    
    function checkBackendStatus() {
        if (backendChecked) return Promise.resolve(backendAvailable);
        
        console.log("Checking backend status...");
        return fetch('/api/debug')
            .then(response => {
                backendChecked = true;
                if (response.ok) {
                    console.log("Backend API is responding!");
                    backendAvailable = true;
                    return response.json();
                } else {
                    console.error("Backend API is not responding:", response.status);
                    backendAvailable = false;
                    throw new Error(`API returned status ${response.status}`);
                }
            })
            .then(data => {
                console.log("API Debug endpoint response:", data);
                return true;
            })
            .catch(error => {
                console.error("Error checking backend:", error);
                return false;
            });
    }
    
    // Landing page transitions
    startChatButton.addEventListener('click', function() {
        // First check if backend is available
        checkBackendStatus().then(isAvailable => {
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
                        addMessage('Sorry, the AI service is currently unavailable. Please try again later.', 'assistant');
                    }, 1000);
                    return;
                }
                
                window.setTimeout(() => {
                    removeTypingIndicator();
                    
                    // Try simplified hello message first
                    fetch('/simple-chat', {
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
                        
                        // Fallback to regular chat endpoint
                        fetch('/chat', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ user_input: 'hello' })
                        })
                        .then(response => response.json())
                        .then(data => {
                            addMessage(data.response, 'assistant');
                        })
                        .catch(err => {
                            console.error('Both endpoints failed:', err);
                            addMessage('Hi there! 👋 I\'m Brooks\' personal AI assistant. Ask me anything about him, his interests, projects, or background!', 'assistant');
                        });
                    });
                }, 1500);
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
        // Updated regex to handle URL encoded characters
        const photoLinkRegex = /\/static\/images\/[^\s"'<>]+\.(jpeg|jpg|png|mov)/g;
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
                
                img.onload = () => {
                    spinner.remove();
                    container.appendChild(img);
                };
                
                img.onerror = () => {
                    spinner.remove();
                    container.innerHTML = '<p style="color: red;">Failed to load image.</p>';
                };
                
                img.src = src;
                
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
        
        // Try the main chat endpoint first
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_input: message })
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
        return fetch('/simple-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_input: message })
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
        
        fetch('/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Conversation reset:', data);
            addTypingIndicator();
            
            window.setTimeout(() => {
                removeTypingIndicator();
                fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ user_input: 'hello' })
                })
                .then(response => response.json())
                .then(data => {
                    addMessage(data.response, 'assistant');
                })
                .catch(error => {
                    console.error('Error starting conversation:', error);
                    addMessage('Hi there! 👋 I\'m Brooks\' personal AI assistant. Our conversation has been reset. What would you like to know?', 'assistant');
                });
            }, 1000);
        })
        .catch(error => {
            console.error('Error resetting conversation:', error);
            addMessage('Failed to reset the conversation. Please try again.', 'assistant');
        });
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
        // Use the filename as-is since it's already URL encoded from the backend
        img.src = `/static/images/${photo.filename}`;
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

    // Accessibility improvements
    sendButton.setAttribute('aria-label', 'Send message');
    resetButton.setAttribute('aria-label', 'Reset conversation');
    backToLandingButton.setAttribute('aria-label', 'Back to landing page');
    startChatButton.setAttribute('aria-label', 'Start chatting with Brooks\' AI assistant');
    userInput.setAttribute('aria-label', 'Type your message here');
});