// LLM Trajectory Replayer
class TrajectoryReplayer {
    constructor() {
        this.currentData = null;
        this.messages = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.playInterval = null;
        this.messageDelay = 1500; // Message interval in milliseconds
        this.autoLoadTrajId = null; // Trajectory ID to auto-load from URL
        this.currentModel = 'agent'; // Current model used by trajectory
        this.isMobile = this.detectMobile(); // Detect if mobile device
        this.abortController = null; // AbortController for canceling fetch requests
        this.currentRequestId = 0; // Request ID to track the latest request
        
        this.initializeElements();
        // Try to hide file selector if needed
        this.checkAutoLoadTrajectory();
        this.initializeEventListeners();
        // Only load file list if no trajectory is auto-loaded
        if (!this.autoLoadTrajId) {
            this.loadTrajectoryFiles();
        }
    }
    
    // Detect if mobile device
    detectMobile() {
        // Check screen width
        if (window.innerWidth <= 768) {
            return true;
        }
        
        // Check user agent
        const userAgent = navigator.userAgent || navigator.vendor || window.opera;
        const mobileRegex = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
        if (mobileRegex.test(userAgent)) {
            return true;
        }
        
        // Check touch support
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
            // Further check screen size to avoid misjudging desktop touch screens
            return window.innerWidth <= 1024;
        }
        
        return false;
    }
    
    // Check if trajectory should be auto-loaded
    checkAutoLoadTrajectory() {
        // Method 1: Get from URL path (e.g., /306)
        const pathname = window.location.pathname;
        // Match paths like /306 or /306/
        const pathMatch = pathname.match(/^\/(\d+)\/?$/);
        if (pathMatch && pathMatch[1]) {
            this.autoLoadTrajId = pathMatch[1];
        } else {
            // Method 2: Get from meta tag (injected by server)
            const metaTag = document.querySelector('meta[name="trajectory-id"]');
            if (metaTag) {
                this.autoLoadTrajId = metaTag.getAttribute('content');
            }
        }
        
        // If trajectory ID found, hide file selector and auto-load
        if (this.autoLoadTrajId) {
            // Immediately hide file selector
            this.hideFileSelector();
            // Immediately load trajectory data
            this.loadTrajectoryById(this.autoLoadTrajId);
        }
    }
    
    // Hide file selector
    hideFileSelector() {
        // Method 1: Use initialized element reference
        if (this.trajFileSelect) {
            this.trajFileSelect.style.display = 'none';
            this.trajFileSelect.hidden = true;
        }
        
        // Method 2: Get directly by ID (ensure hiding even if initialization fails)
        const fileSelector = document.getElementById('traj-file');
        if (fileSelector) {
            fileSelector.style.display = 'none';
            fileSelector.hidden = true;
        }
        
        // If still not found, use query selector
        const selector = document.querySelector('#traj-file');
        if (selector) {
            selector.style.display = 'none';
            selector.hidden = true;
        }
    }
    
    // Load trajectory by ID
    async loadTrajectoryById(trajId) {
        const filename = `${trajId}.json`;
        
        // Cancel any pending fetch request
        if (this.abortController) {
            this.abortController.abort();
        }
        
        // Create new AbortController for this request
        this.abortController = new AbortController();
        const requestId = ++this.currentRequestId;
        
        // Clear previous trajectory
        this.clearMessages();
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.currentModel = 'agent'; // Reset to default value
        if (this.playInterval) {
            clearTimeout(this.playInterval);
            this.playInterval = null;
        }
        this.updateProgress();
        this.updateButtonStates();
        
        try {
            const response = await fetch(`/api/trajectory/${filename}`, {
                signal: this.abortController.signal
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Check if this is still the latest request
            if (requestId !== this.currentRequestId) {
                console.log('Ignoring outdated trajectory data for:', filename);
                return;
            }
            
            this.currentData = data;
            // Pass trajId to processTrajectoryData
            this.processTrajectoryData(data, trajId);
            this.updateTaskInfo(data);
            this.enableControls();
        } catch (error) {
            // Ignore abort errors (they're expected when switching tasks)
            if (error.name === 'AbortError') {
                console.log('Fetch aborted for:', filename);
                return;
            }
            console.error('Failed to load trajectory:', error);
            // Only show error if this is still the current request
            if (requestId === this.currentRequestId) {
                this.showErrorMessage('Failed to load trajectory: ' + error.message);
            }
        }
    }

    // Initialize DOM elements
    initializeElements() {
        this.trajFileSelect = document.getElementById('traj-file');
        this.playBtn = document.getElementById('play-btn');
        this.pauseBtn = document.getElementById('pause-btn');
        this.prevBtn = document.getElementById('prev-btn');
        this.nextBtn = document.getElementById('next-btn');
        this.progressFill = document.getElementById('progress');
        this.progressText = document.getElementById('progress-text');
        this.messagesContainer = document.getElementById('messages-container');
        this.taskInfo = document.getElementById('task-info');
        this.timeInfo = document.getElementById('time-info');
        
        // Task status elements
        this.taskStatus = document.getElementById('task-status');
        if (this.taskStatus) {
            this.taskStatusIcon = this.taskStatus.querySelector('.task-status-icon');
            this.taskStatusText = this.taskStatus.querySelector('.task-status-text');
        }
        
        // Right panel elements
        this.toolSidebar = document.getElementById('tool-sidebar');
        this.toolDetails = document.getElementById('tool-details');
        this.closeSidebarBtn = document.getElementById('close-sidebar');
        
        // Check if critical elements exist
        if (!this.playBtn || !this.pauseBtn || !this.prevBtn || !this.nextBtn) {
            console.error('Critical button elements not found!', {
                playBtn: !!this.playBtn,
                pauseBtn: !!this.pauseBtn,
                prevBtn: !!this.prevBtn,
                nextBtn: !!this.nextBtn
            });
        }
    }

    // Initialize event listeners
    initializeEventListeners() {
        if (this.trajFileSelect) {
            this.trajFileSelect.addEventListener('change', () => {
                this.loadTrajectory();
            });
        }

        if (this.playBtn) {
            this.playBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Play button clicked', {
                    disabled: this.playBtn.disabled,
                    messagesLength: this.messages.length,
                    currentIndex: this.currentIndex
                });
                this.play();
            });
        } else {
            console.error('playBtn not found in DOM');
        }

        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', () => {
                this.pause();
            });
        } else {
            console.error('pauseBtn not found in DOM');
        }

        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Prev button clicked', {
                    disabled: this.prevBtn.disabled,
                    currentIndex: this.currentIndex
                });
                this.prevStep();
            });
        } else {
            console.error('prevBtn not found in DOM');
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Next button clicked', {
                    disabled: this.nextBtn.disabled,
                    currentIndex: this.currentIndex,
                    messagesLength: this.messages.length
                });
                this.nextStep();
            });
        } else {
            console.error('nextBtn not found in DOM');
        }

        // Right panel close button
        this.closeSidebarBtn.addEventListener('click', () => {
            this.hideToolSidebar();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                if (this.isPlaying) {
                    this.pause();
                } else {
                    this.play();
                }
            } else if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
                e.preventDefault();
                this.prevStep();
            } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
                e.preventDefault();
                this.nextStep();
            } else if (e.code === 'Escape') {
                if (!this.isMobile) {
                    this.hideToolSidebar();
                }
            }
        });
        
        // Listen for window resize, re-detect if mobile
        window.addEventListener('resize', () => {
            const wasMobile = this.isMobile;
            this.isMobile = this.detectMobile();
            
            // If switching from desktop to mobile, hide sidebar
            if (!wasMobile && this.isMobile) {
                this.hideToolSidebar();
            }
        });

        // Use event delegation to handle tool call clicks (as backup)
        this.messagesContainer.addEventListener('click', (e) => {
            // Mobile devices do not handle tool call clicks
            if (this.isMobile) {
                return;
            }
            
            // Find nearest tool call header
            const clickedHeader = e.target.closest('.tool-call-header');
            if (!clickedHeader) {
                // If not clicking header, check if inside tool-call-item
                const toolCallItem = e.target.closest('.tool-call-item');
                if (toolCallItem) {
                    const header = toolCallItem.querySelector('.tool-call-header');
                    if (header) {
                        const uniqueId = header.getAttribute('data-tool-call-id') || toolCallItem.getAttribute('data-id');
                        if (uniqueId) {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('Event delegation: Tool call clicked, uniqueId:', uniqueId);
                            this.toggleToolCall(uniqueId);
                        }
                    }
                }
                return;
            }
            
            // Get unique ID
            const uniqueId = clickedHeader.getAttribute('data-tool-call-id');
            if (!uniqueId) {
                const toolCallItem = clickedHeader.closest('.tool-call-item');
                if (toolCallItem) {
                    const id = toolCallItem.getAttribute('data-id');
                    if (id) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Event delegation: Tool call clicked (via item), uniqueId:', id);
                        this.toggleToolCall(id);
                    }
                }
                return;
            }
            
            e.preventDefault();
            e.stopPropagation();
            console.log('Event delegation: Tool call clicked, uniqueId:', uniqueId);
            this.toggleToolCall(uniqueId);
        }, true); // Use capture phase
    }

    // Load trajectory files list
    async loadTrajectoryFiles() {
        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.trajFileSelect.innerHTML = '<option value="">Select trajectory file...</option>';
            
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file;
                    option.textContent = file;
                    this.trajFileSelect.appendChild(option);
                });
            } else {
                this.trajFileSelect.innerHTML = '<option value="">No trajectory files found</option>';
            }
        } catch (error) {
            console.error('Failed to load file list:', error);
            this.trajFileSelect.innerHTML = '<option value="">Load failed</option>';
        }
    }

    // Load trajectory data
    async loadTrajectory() {
        const selectedFile = this.trajFileSelect.value;
        
        // Cancel any pending fetch request
        if (this.abortController) {
            this.abortController.abort();
        }
        
        // Create new AbortController for this request
        this.abortController = new AbortController();
        const requestId = ++this.currentRequestId;
        
        // Clear previous trajectory when selecting a new one
        this.clearMessages();
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.currentModel = 'agent'; // Reset to default value
        if (this.playInterval) {
            clearTimeout(this.playInterval);
            this.playInterval = null;
        }
        this.updateProgress();
        this.updateButtonStates();
        
        if (!selectedFile) {
            this.showEmptyState();
            return;
        }

        try {
            const response = await fetch(`/api/trajectory/${selectedFile}`, {
                signal: this.abortController.signal
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Check if this is still the latest request
            if (requestId !== this.currentRequestId) {
                console.log('Ignoring outdated trajectory data for:', selectedFile);
                return;
            }
            
            this.currentData = data;
            // Pass filename (without .json) to processTrajectoryData
            const fileNameWithoutExt = selectedFile.replace(/\.json$/, '');
            this.processTrajectoryData(data, fileNameWithoutExt);
            this.updateTaskInfo(data);
            this.enableControls();
        } catch (error) {
            // Ignore abort errors (they're expected when switching tasks)
            if (error.name === 'AbortError') {
                console.log('Fetch aborted for:', selectedFile);
                return;
            }
            console.error('Failed to load trajectory:', error);
            // Only show error if this is still the current request
            if (requestId === this.currentRequestId) {
                this.showErrorMessage('Failed to load trajectory: ' + error.message);
            }
        }
    }

    // Process trajectory data
    processTrajectoryData(data, trajId = null) {
        // Double-check: clear messages again to ensure no old messages remain
        // This provides an extra safety layer in case of race conditions
        this.clearMessages();
        
        // Detect model type: get from filename or config
        this.detectModel(data, trajId);
        
        // Filter out tool messages, only keep user, assistant, system messages
        const filteredMessages = (data.messages || []).filter(msg => 
            msg.role === 'user' || msg.role === 'assistant' || msg.role === 'system'
        );
        
        // No longer merge consecutive tool calls, each assistant message is displayed separately
        this.messages = filteredMessages;
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        if (this.playInterval) {
            clearTimeout(this.playInterval);
            this.playInterval = null;
        }
        this.toolResults = this.buildToolResultsMap(data.messages || []);
        
        // Automatically display first user message (instruction)
        this.displayInitialUserMessage();
        
        this.updateProgress();
        this.updateButtonStates();
        this.updateTaskStatus(data.pass);
        this.updateCurrentStepBorder();
        this.updateSidebarForCurrentStep();
        
        // Bind tool call click events for all existing messages
        this.bindAllToolCallEvents();
    }
    
    // Detect model type (unified agent style)
    detectModel(data, trajId = null) {
        // Use unified agent style, no longer distinguish different models
        this.currentModel = 'agent';
    }
    
    // Display initial user message (instruction)
    displayInitialUserMessage() {
        if (this.messages.length === 0) return;
        
        // Find first user message
        const firstUserMessage = this.messages.find(msg => msg.role === 'user');
        if (!firstUserMessage) return;
        
        // Display first user message
        this.displayMessage(firstUserMessage);
        this.currentIndex = 1; // Set current index to 1, as first message is already displayed
        
        // Update progress and button states
        this.updateProgress();
        this.updateButtonStates();
        this.updateCurrentStepBorder();
    }
    
    // Get model icon and name (unified agent style)
    getModelHeader() {
        return {
            icon: "🤔",
            name: "agent"
        };
    }
    
    // Bind click events for all existing tool calls
    bindAllToolCallEvents() {
        // Delay execution to ensure DOM is updated
        setTimeout(() => {
            const allToolCallItems = document.querySelectorAll('.tool-call-item');
            console.log('Binding events to all existing tool calls:', allToolCallItems.length);
            
            allToolCallItems.forEach((item) => {
                const header = item.querySelector('.tool-call-header');
                if (!header) return;
                
                // Check if event is already bound (by checking data-bound attribute)
                if (header.hasAttribute('data-event-bound')) return;
                
                const uniqueId = header.getAttribute('data-tool-call-id') || item.getAttribute('data-id');
                if (!uniqueId) return;
                
                // Mark as bound
                header.setAttribute('data-event-bound', 'true');
                
                // Ensure styles
                header.style.cursor = 'pointer';
                header.style.userSelect = 'none';
                header.style.pointerEvents = 'auto';
                
                // Bind click event
                const clickHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('✅ Click handler fired for:', uniqueId);
                    this.toggleToolCall(uniqueId);
                    return false;
                };
                
                header.addEventListener('click', clickHandler, true);
                header.addEventListener('click', clickHandler, false);
                header.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('✅ MouseDown handler fired for:', uniqueId);
                    this.toggleToolCall(uniqueId);
                    return false;
                }, true);
            });
        }, 100);
    }


    // Build tool results mapping
    buildToolResultsMap(messages) {
        const toolResults = new Map();
        
        messages.forEach(message => {
            if (message.role === 'tool' && message.tool_call_id) {
                toolResults.set(message.tool_call_id, {
                    content: message.content,
                    name: message.name || 'unknown_tool',
                    tool_call_id: message.tool_call_id
                });
            }
        });
        
        return toolResults;
    }

    // Update task information
    updateTaskInfo(data) {
        // Task info display removed - no longer needed
        // const config = data.config || {};
        // const taskName = config.id || 'Unknown Task';
        // const taskDesc = config.task_str || '';
        // const shortDesc = taskDesc.length > 50 ? taskDesc.substring(0, 50) + '...' : taskDesc;
        // if (this.taskInfo) {
        //     this.taskInfo.textContent = `${taskName} - ${shortDesc}`;
        // }
    }

    // Enable control buttons
    enableControls() {
        if (this.playBtn) this.playBtn.disabled = false;
        if (this.pauseBtn) this.pauseBtn.disabled = true;
        this.updateButtonStates();
    }

    // Update button states
    updateButtonStates() {
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentIndex === 0;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = this.currentIndex >= this.messages.length;
        }
    }

    // Play trajectory
    play() {
        console.log('play() called', {
            messagesLength: this.messages.length,
            currentIndex: this.currentIndex,
            isPlaying: this.isPlaying
        });
        
        if (this.messages.length === 0) {
            console.warn('No messages to play');
            return;
        }

        // If playback finished, start from beginning
        if (this.currentIndex >= this.messages.length) {
            this.currentIndex = 0;
            this.clearMessages();
        }

        this.isPlaying = true;
        this.isPaused = false;
        if (this.playBtn) this.playBtn.disabled = true;
        if (this.pauseBtn) this.pauseBtn.disabled = false;
        this.updateButtonStates();

        // Continue playback
        if (this.currentIndex < this.messages.length) {
            this.playNextMessage();
        }
    }

    // Pause playback
    pause() {
        this.isPlaying = false;
        this.isPaused = true;
        this.playBtn.disabled = false;
        this.pauseBtn.disabled = true;
        this.updateButtonStates();

        if (this.playInterval) {
            clearTimeout(this.playInterval);
            this.playInterval = null;
        }
        
        // After pause, ensure all tool calls have event binding
        this.bindAllToolCallEvents();
    }

    // Previous step
    prevStep() {
        if (this.currentIndex === 0) return;
        
        // If playing, pause playback
        if (this.isPlaying) {
            this.pause();
        }
        
        // Remove last message
        const lastMessage = this.messagesContainer.lastElementChild;
        if (lastMessage) {
            lastMessage.remove();
        }
        
        this.currentIndex--;
        this.updateProgress();
        this.updateButtonStates();
        this.updateCurrentStepBorder();
        this.updateSidebarForCurrentStep();
    }

    // Next step
    nextStep() {
        console.log('nextStep() called', {
            currentIndex: this.currentIndex,
            messagesLength: this.messages.length
        });
        
        if (this.currentIndex >= this.messages.length) {
            console.warn('Already at the end');
            return;
        }
        
        // If playing, pause playback
        if (this.isPlaying) {
            this.pause();
        }
        
        const message = this.messages[this.currentIndex];
        if (!message) {
            console.error('No message at index', this.currentIndex);
            return;
        }
        
        this.displayMessage(message);
        this.currentIndex++;
        this.updateProgress();
        this.updateButtonStates();
        this.updateCurrentStepBorder();
        this.updateSidebarForCurrentStep();
    }

    // Play next message
    playNextMessage() {
        if (this.currentIndex >= this.messages.length) {
            this.finishPlayback();
            return;
        }

        const message = this.messages[this.currentIndex];
        this.displayMessage(message);
        this.currentIndex++;
        this.updateProgress();
        this.updateButtonStates();
        this.updateCurrentStepBorder();
        this.updateSidebarForCurrentStep();

        // Continue playing next message
        if (this.isPlaying && this.currentIndex < this.messages.length) {
            this.playInterval = setTimeout(() => {
                this.playNextMessage();
            }, this.messageDelay);
        }
    }

    // Display message
    displayMessage(message) {
        const messageElement = this.createMessageElement(message);
        this.messagesContainer.appendChild(messageElement);
        
        // After element is added to DOM, bind tool call click events
        this.bindToolCallClickEvents(messageElement, message);
        
        // Also immediately bind all tool call events (including existing ones)
        setTimeout(() => this.bindAllToolCallEvents(), 50);

        // Scroll to latest message
        setTimeout(() => {
            messageElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 100);
        
        // Update current step border style
        this.updateCurrentStepBorder();
    }
    
    // Bind tool call click events
    bindToolCallClickEvents(messageElement, message) {
        const hasToolCalls = message.tool_calls && message.tool_calls.length > 0;
        if (!hasToolCalls) return;
        
        // Use requestAnimationFrame to ensure DOM is fully rendered
        requestAnimationFrame(() => {
            const toolCallItems = messageElement.querySelectorAll('.tool-call-item');
            console.log('Found tool call items:', toolCallItems.length);
            
            toolCallItems.forEach((item) => {
                const header = item.querySelector('.tool-call-header');
                if (!header) {
                    console.warn('No header found in tool-call-item');
                    return;
                }
                
                const uniqueId = header.getAttribute('data-tool-call-id') || item.getAttribute('data-id');
                if (!uniqueId) {
                    console.warn('No uniqueId found for tool call');
                    return;
                }
                
                console.log('Binding click handler for:', uniqueId);
                
                // Ensure styles
                header.style.cursor = 'pointer';
                header.style.userSelect = 'none';
                header.style.pointerEvents = 'auto';
                
                // Remove previously existing listeners (by cloning node)
                const newHeader = header.cloneNode(true);
                header.parentNode.replaceChild(newHeader, header);
                
                // Bind click event - use multiple methods to ensure triggering
                const clickHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('✅ Click handler fired for:', uniqueId);
                    this.toggleToolCall(uniqueId);
                    return false;
                };
                
                newHeader.addEventListener('click', clickHandler, true); // Capture phase
                newHeader.addEventListener('click', clickHandler, false); // Bubble phase
                
                // Also bind mousedown as backup
                newHeader.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('✅ MouseDown handler fired for:', uniqueId);
                    this.toggleToolCall(uniqueId);
                    return false;
                }, true);
            });
        });
    }

    // Create message element
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role || 'unknown'}`;

        const role = message.role || 'unknown';
        const content = message.content || '';
        const timestamp = this.formatTime(message.timestamp);
        
        // Check if has tool calls
        const hasToolCalls = message.tool_calls && message.tool_calls.length > 0;
        
        // Get current message index (when displaying)
        const currentMsgIndex = this.currentIndex - 1;
        
        // Add model identifier for all assistant messages (unified agent style)
        let modelHeader = '';
        if (role === 'assistant') {
            const modelInfo = this.getModelHeader();
            const headerClass = 'claude-header'; // Use unified style class
            const labelClass = 'claude-label'; // Unified use of claude-label style
            modelHeader = `
                <div class="${headerClass}">
                    ${modelInfo.icon}
                    <span class="${labelClass}">${modelInfo.name}</span>
                </div>
            `;
        }

        const messageText = this.renderMessageContent(content, role);
        
        messageDiv.innerHTML = `
            ${modelHeader}
            <div class="message-content">
                <div class="message-text">${messageText}</div>
                ${hasToolCalls ? this.createToolCallsSummaryHTML(message.tool_calls, currentMsgIndex) : ''}
                <div class="message-time">${timestamp}</div>
            </div>
        `;
        
        // Save message index to DOM for later lookup
        if (hasToolCalls) {
            messageDiv.setAttribute('data-message-index', currentMsgIndex);
        }
        
        if (hasToolCalls && this.isPlaying && !this.isMobile) {
            setTimeout(() => {
                this.showToolSidebar(message.tool_calls);
            }, 100);
        } else if (!hasToolCalls && this.isPlaying && !this.isMobile) {
            this.hideToolSidebar();
        } else if (this.isMobile) {
            this.hideToolSidebar();
        }

        setTimeout(() => {
            messageDiv.classList.add('visible');
        }, 50);

        return messageDiv;
    }

    createToolCallsSummaryHTML(toolCalls, messageIndex = null) {
        if (!toolCalls || toolCalls.length === 0) return '';

        if (messageIndex === null) {
            messageIndex = this.currentIndex - 1;
        }

        const toolCallsHTML = toolCalls.map((toolCall, index) => {
            const toolName = toolCall.function?.name || '未知工具';
            const toolCallId = toolCall.id;
            
            const toolResult = this.toolResults.get(toolCallId);
            const hasResult = !!toolResult;
            
            const iconClass = hasResult ? 'tool' : 'agent';
            const iconHtml = hasResult ? this.getToolIcon(toolName) : '<div class="agent-icon">A</div>';
            
            let status, statusClass;
            if (hasResult) {
                const toolOutputType = this.categorizeToolOutput(toolName, toolResult.content);
                switch (toolOutputType) {
                    case 'normal_tool_output':
                        status = '●';
                        statusClass = 'status-success';
                        break;
                    case 'overlong_tool_output':
                        status = '●';
                        statusClass = 'status-warning';
                        break;
                    case 'error_in_tool_call':
                    case 'tool_name_not_found':
                        status = '●';
                        statusClass = 'status-error';
                        break;
                    default:
                        status = '●';
                        statusClass = 'status-success';
                }
            } else {
                status = 'Calling';
                statusClass = 'status-calling';
            }
            
            return `
                <div class="tool-call-summary">
                    <div class="tool-call-info">
                        <div class="tool-icon ${iconClass}">${iconHtml}</div>
                        <span class="tool-name">${this.escapeHtml(toolName)}</span>
                        <span class="tool-status ${statusClass}">${status}</span>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="tool-calls-summary-container">
                ${toolCallsHTML}
            </div>
        `;
    }

    createToolCallsHTML(toolCalls, messageIndex) {
        if (!toolCalls || toolCalls.length === 0) return '';

        const toolCallsHTML = toolCalls.map((toolCall, index) => {
            const toolName = toolCall.function?.name || '未知工具';
            const toolArgs = toolCall.function?.arguments || '{}';
            const toolCallId = toolCall.id;
            
            const toolResult = this.toolResults.get(toolCallId);
            const hasResult = !!toolResult;
            
            // Determine if it's agent call or tool response
            const iconClass = hasResult ? 'tool' : 'agent';
            const iconHtml = hasResult ? this.getToolIcon(toolName) : '<div class="agent-icon">A</div>';
            
            let status, statusClass;
            if (hasResult) {
                const toolOutputType = this.categorizeToolOutput(toolName, toolResult.content);
                switch (toolOutputType) {
                    case 'normal_tool_output':
                        status = '●';
                        statusClass = 'status-success';
                        break;
                    case 'overlong_tool_output':
                        status = '●';
                        statusClass = 'status-warning';
                        break;
                    case 'error_in_tool_call':
                    case 'tool_name_not_found':
                        status = '●';
                        statusClass = 'status-error';
                        break;
                    default:
                        status = '●';
                        statusClass = 'status-success';
                }
            } else {
                status = 'Calling';
                statusClass = 'status-calling';
            }
            
            const uniqueId = `tool-${messageIndex}-${index}`;
            
            return `
                <div class="tool-call-item" data-id="${uniqueId}" data-tool-index="${index}">
                    <div class="tool-call-header" data-tool-call-id="${uniqueId}" style="cursor: pointer;">
                        <div class="tool-call-info">
                            <div class="tool-icon ${iconClass}">${iconHtml}</div>
                            <span class="tool-name">${this.escapeHtml(toolName)}</span>
                            <span class="tool-status ${statusClass}">${status}</span>
                        </div>
                    </div>
                    <div class="tool-call-content">
                        <div class="tool-call-details">
                            <div class="tool-section">
                                <div class="tool-section-title">Arguments</div>
                                <div class="tool-args">${this.escapeHtml(JSON.stringify(JSON.parse(toolArgs), null, 2))}</div>
                            </div>
                            ${hasResult ? `
                                <div class="tool-section">
                                    <div class="tool-section-title">Result</div>
                                    <div class="tool-result">${this.escapeHtml(this.extractTextFromResult(toolResult.content))}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="tool-calls-container">
                <div class="tool-calls-block" data-message-index="${messageIndex}">
                    ${toolCallsHTML}
                </div>
            </div>
        `;
    }

    toggleToolCall(uniqueId) {
        if (this.isMobile) {
            return;
        }
        
        console.log('toggleToolCall called with uniqueId:', uniqueId);

        const toolBlock = document.querySelector(`[data-id="${uniqueId}"]`);
        if (!toolBlock) {
            console.error('Tool block not found:', uniqueId);
            return;
        }
        
        console.log('Tool block found, messages length:', this.messages.length);

        toolBlock.classList.toggle('expanded');
        
        const match = uniqueId.match(/tool-(\d+)-(\d+)/);
        if (!match) {
            console.error('Failed to parse uniqueId:', uniqueId);
            return;
        }
        
        const messageIndex = parseInt(match[1]);
        const toolCallIndex = parseInt(match[2]);
        
        if (messageIndex >= 0 && messageIndex < this.messages.length) {
            const message = this.messages[messageIndex];
            if (message && message.tool_calls && message.tool_calls[toolCallIndex]) {
                this.showToolSidebar([message.tool_calls[toolCallIndex]]);
                return;
            }
        }
        
        const messageElement = toolBlock.closest('.message');
        if (messageElement) {
            const domMsgIndex = messageElement.getAttribute('data-message-index');
            if (domMsgIndex !== null) {
                const msgIdx = parseInt(domMsgIndex);
                if (msgIdx >= 0 && msgIdx < this.messages.length) {
                    const message = this.messages[msgIdx];
                    if (message && message.tool_calls && message.tool_calls[toolCallIndex]) {
                        this.showToolSidebar([message.tool_calls[toolCallIndex]]);
                        return;
                    }
                }
            }
        }
        
        const allMessages = Array.from(document.querySelectorAll('.message'));
        for (const msgEl of allMessages) {
            const toolBlocks = msgEl.querySelectorAll('.tool-call-item');
            for (let i = 0; i < toolBlocks.length; i++) {
                if (toolBlocks[i] === toolBlock) {
                    const msgIndex = msgEl.getAttribute('data-message-index');
                    if (msgIndex !== null) {
                        const idx = parseInt(msgIndex);
                        if (idx >= 0 && idx < this.messages.length) {
                            const message = this.messages[idx];
                            if (message && message.tool_calls && message.tool_calls[i]) {
                                this.showToolSidebar([message.tool_calls[i]]);
                                return;
                            }
                        }
                    }
                }
            }
        }
        
        console.error('Could not find tool call data for:', uniqueId);
    }


    categorizeToolOutput(toolName, toolOutputStr) {
        if (!toolOutputStr) return 'normal_tool_output';
        
        let tooloutputType = null;
        
        if (toolOutputStr.trim().startsWith("Error running tool")) {
            tooloutputType = "error_in_tool_call";
        }
        
        if (toolOutputStr.trim().endsWith("Please check this file carefully, as it may be very long!)")) {
            if (tooloutputType !== null) {
                console.warn('Multiple tool output types detected, using overlong_tool_output');
            }
            tooloutputType = "overlong_tool_output";
        }
        
        if (toolOutputStr.trim().startsWith(`Tool ${toolName} not found in agent`)) {
            if (tooloutputType !== null) {
                console.warn('Multiple tool output types detected, using tool_name_not_found');
            }
            tooloutputType = "tool_name_not_found";
        }
        
        if (tooloutputType === null) {
            tooloutputType = "normal_tool_output";
        }
        
        return tooloutputType;
    }

    getToolIcon(toolName) {
        const iconMap = {
            "history": '<img src="icons/history.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "k8s": '<img src="icons/k8s.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google_map": '<img src="icons/google_map.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "git": '<img src="icons/git.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "filesystem": '<img src="icons/filesystem.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "terminal": '<img src="icons/terminal.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "yahoo": '<img src="icons/yahoo.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "github": '<img src="icons/github.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google-cloud": '<img src="icons/google_cloud.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "snowflake": '<img src="icons/snowflake.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "excel": '<img src="icons/excel.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "word": '<img src="icons/word.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "scholarly": '<img src="icons/scholar.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "local-python-execute": '<img src="icons/python.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "canvas": '<img src="icons/canvas.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "fetch": '<img src="icons/fetch.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "overlong": '<Icon icon="filter-list" size={14} color="#4286f6" />',
            "pdf": '<img src="icons/pdf.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "local-web_search": '<img src="icons/google_search.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "web_search": '<img src="icons/google_search.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "local-claim_done": '<img src="icons/claim_done.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "emails": '<img src="icons/mail.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "huggingface": '<img src="icons/hf.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "woocommerce": '<img src="icons/woo.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google_forms": '<img src="icons/google_forms.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "arxiv_local": '<img src="icons/arxiv.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google_sheet": '<img src="icons/google_sheet.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "playwright_with_chunk": '<img src="icons/playwright.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "notion": '<img src="icons/notion.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "wandb": '<img src="icons/wandb.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "memory": '<img src="icons/memory.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "rail_12306": '<img src="icons/12306.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "youtube": '<img src="icons/youtube.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "youtube_transcript": '<img src="icons/youtube_transcript.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google_calendar": '<img src="icons/calendar.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "sleep": '<img src="icons/sleep.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "pptx": '<img src="icons/pptx.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "arxiv": '<img src="icons/latex.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "google": '<img src="icons/google_cloud.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
            "howtocook": '<img src="icons/cook.png" width="14" height="14" style={{margin: 0, padding: 0, display: \'inline-block\', verticalAlign: \'middle\'}} />',
        };
        
        const defaultIcon = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" style={{margin: 0, padding: 0, display: \'inline-block\'}}><path d="M3.5 3.5L7 7L10.5 3.5M3.5 3.5H10.5M3.5 3.5V7M10.5 3.5V7M7 7V10.5M8.75 10.5H10.5M8.75 10.5H7M8.75 10.5V12.25M7 10.5V12.25M10.5 10.5V12.25" stroke="#4A90E2" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        
        if (iconMap[toolName]) {
            return iconMap[toolName];
        }

        if (toolName.toLowerCase().includes('youtube-trans')) {
            return iconMap["youtube_transcript"];
        }

        if (toolName.toLowerCase().includes('history')) {
            return iconMap["history"];
        }

        const serverName = toolName.split("-")[0];

        if (serverName in iconMap) {
            return iconMap[serverName];
        }
        
        const toolNameLower = toolName.toLowerCase();
        
        if (['file', 'read', 'write', 'fs', 'filesystem'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.filesystem || defaultIcon;
        }
        
        if (['git', 'commit', 'push', 'pull'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.git || defaultIcon;
        }
        
        if (['terminal', 'shell', 'cmd', 'bash'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.terminal || defaultIcon;
        }
        
        if (['code', 'python', 'javascript', 'java'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.github || defaultIcon;
        }
        
        
        if (['database', 'db', 'sql', 'mysql'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.snowflake || defaultIcon;
        }
        
        if (['doc', 'pdf', 'word', 'excel'].some(keyword => toolNameLower.includes(keyword))) {
            if (toolNameLower.includes('excel')) {
                return iconMap.excel || defaultIcon;
            } else if (toolNameLower.includes('word')) {
                return iconMap.word || defaultIcon;
            } else {
                return defaultIcon;
            }
        }
        
        if (['arxiv', 'paper', 'research', 'scholar'].some(keyword => toolNameLower.includes(keyword))) {
            return iconMap.scholarly || defaultIcon;
        }

        return defaultIcon;
    }

    finishPlayback() {
        this.isPlaying = false;
        this.isPaused = false;
        this.playBtn.disabled = false;
        this.pauseBtn.disabled = true;
        this.updateButtonStates();
        
        if (this.playInterval) {
            clearTimeout(this.playInterval);
            this.playInterval = null;
        }
        
        this.bindAllToolCallEvents();
    }

    clearMessages() {
        this.messagesContainer.innerHTML = '';
        this.updateCurrentStepBorder();
    }

    // Show empty state
    showEmptyState() {
        this.messagesContainer.innerHTML = '';
        if (this.taskInfo) {
            this.taskInfo.textContent = 'No trajectory loaded';
        }
        if (this.taskStatus) {
            this.taskStatus.style.display = 'none';
        }
        this.updateCurrentStepBorder();
        this.disableControls();
    }

    // Show error message
    showErrorMessage(message) {
        this.messagesContainer.innerHTML = `
            <div class="welcome-message">
                <h2>Load Failed</h2>
                <p>${message}</p>
            </div>
        `;
        if (this.taskInfo) {
            this.taskInfo.textContent = 'Load failed';
        }
        this.disableControls();
    }

    disableControls() {
        this.playBtn.disabled = true;
        this.pauseBtn.disabled = true;
        this.prevBtn.disabled = true;
        this.nextBtn.disabled = true;
    }


    updateProgress() {
        const progress = this.messages.length > 0 ? (this.currentIndex / this.messages.length) * 100 : 0;
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${this.currentIndex} / ${this.messages.length}`;
    }

    updateCurrentStepBorder() {
        const messages = this.messagesContainer.querySelectorAll('.message');
        messages.forEach((msg, index) => {
            const isCurrentStep = (index === this.currentIndex - 1) && !(index === 0 && msg.classList.contains('user'));
            
            if (isCurrentStep) {
                msg.classList.add('current-step');
            } else {
                msg.classList.remove('current-step');
            }
        });
    }
    
    updateSidebarForCurrentStep() {
        if (this.isMobile) {
            this.hideToolSidebar();
            return;
        }
        
        if (!this.messages || this.currentIndex === 0) {
            this.hideToolSidebar();
            return;
        }
        
        const currentMsgIndex = this.currentIndex - 1;
        if (currentMsgIndex < 0 || currentMsgIndex >= this.messages.length) {
            this.hideToolSidebar();
            return;
        }
        
        const currentMessage = this.messages[currentMsgIndex];
        if (currentMessage && currentMessage.tool_calls && currentMessage.tool_calls.length > 0) {
            this.showToolSidebar(currentMessage.tool_calls);
        } else {
            this.hideToolSidebar();
        }
    }
    
    updateTaskStatus(isPass) {
        if (!this.taskStatus || !this.taskStatusIcon || !this.taskStatusText) {
            return;
        }
        
        if (isPass === undefined || isPass === null) {
            this.taskStatus.style.display = 'none';
            return;
        }
        
        this.taskStatus.style.display = 'flex';
        
        if (isPass) {
            this.taskStatus.className = 'task-status task-status-passed';
            this.taskStatusIcon.textContent = '✓';
            this.taskStatusText.textContent = 'Task Completed';
        } else {
            this.taskStatus.className = 'task-status task-status-failed';
            this.taskStatusIcon.textContent = '✗';
            this.taskStatusText.textContent = 'Task Failed';
        }
    }
    
    updateTimeInfo() {
        // Time info display removed - bottom bar removed
        // if (this.timeInfo) {
        //     if (this.currentData && this.currentData.config) {
        //         const launchTime = this.currentData.config.launch_time;
        //         const completionTime = this.currentData.completion_time;
        //         
        //         if (launchTime && completionTime) {
        //             const start = new Date(launchTime);
        //             const end = new Date(completionTime);
        //             const duration = Math.round((end - start) / 1000);
        //             const minutes = Math.floor(duration / 60);
        //             const seconds = duration % 60;
        //             this.timeInfo.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        //         } else {
        //             this.timeInfo.textContent = '--:--';
        //         }
        //     } else {
        //         this.timeInfo.textContent = '--:--';
        //     }
        // }
    }

    renderMessageContent(content, role) {
        if (!content) return '';

        const contextResetPattern = /\[Context reset\]|The context length of the previous interaction exceeds/i;
        if (contextResetPattern.test(content)) {
            return '<span class="context-reset-text">Reset Context</span>';
        }
        
        // Clean content: remove trailing whitespace and unnecessary newlines
        const cleanedContent = this.cleanContent(content);
        
        // Render markdown for assistant and user messages
        if (role === 'assistant' || role === 'user') {
            try {
                // Configure marked options
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    sanitize: false
                });
                
                const rendered = marked.parse(cleanedContent);
                return this.cleanRenderedHtml(rendered);
            } catch (error) {
                console.warn('Markdown parsing failed:', error);
                return this.escapeHtml(cleanedContent);
            }
        }
        
        // For other roles (system), escape HTML
        return this.escapeHtml(cleanedContent);
    }

    // Clean content by removing trailing whitespace and unnecessary newlines
    cleanContent(content) {
        if (!content) return '';
        
        // Remove trailing whitespace from each line
        let cleaned = content.split('\n').map(line => line.trimEnd()).join('\n');
        
        // Remove multiple consecutive newlines (more than 2)
        cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
        
        // Remove trailing newlines at the end
        cleaned = cleaned.replace(/\n+$/, '');
        
        // Remove leading newlines at the start
        cleaned = cleaned.replace(/^\n+/, '');
        
        return cleaned;
    }

    // Clean rendered HTML by removing empty paragraphs and extra whitespace
    cleanRenderedHtml(html) {
        if (!html) return '';
        
        // Remove empty paragraphs
        html = html.replace(/<p>\s*<\/p>/g, '');
        
        // Remove empty list items
        html = html.replace(/<li>\s*<\/li>/g, '');
        
        // Remove extra whitespace between tags
        html = html.replace(/>\s+</g, '><');
        
        // Remove trailing whitespace and newlines
        html = html.trim();
        
        return html;
    }

    // Extract text content from tool result
    extractTextFromResult(content) {
        if (!content) return '';
        
        try {
            // Try to parse as JSON first
            const parsed = JSON.parse(content);
            
            // If it has a text field, return that
            if (parsed && typeof parsed === 'object' && parsed.text) {
                return parsed.text;
            }
            
            // If it's a string, return as is
            if (typeof parsed === 'string') {
                return parsed;
            }
            
            // Otherwise return the full JSON
            return JSON.stringify(parsed, null, 2);
        } catch {
            // If parsing fails, return the content as is
            return content;
        }
    }

    // Utility methods
    formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return timestamp;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

        showToolSidebar(toolCalls) {
            if (this.isMobile) {
                return;
            }
            
            if (!toolCalls || toolCalls.length === 0) {
                this.hideToolSidebar();
                return;
            }

            const sidebarHeader = this.toolSidebar.querySelector('.sidebar-header h3');
            
            if (toolCalls.length > 1) {
                sidebarHeader.innerHTML = `<span class="tool-call-detail-name">Call ${toolCalls.length} tools in parallel</span>`;
            } else {
                const firstToolCall = toolCalls[0];
                const toolName = firstToolCall.function?.name || '未知工具';
                const toolCallId = firstToolCall.id;
                const toolResult = this.toolResults.get(toolCallId);
                const hasResult = !!toolResult;

                const iconHtml = this.getToolIcon(toolName);

                let statusDot;
                if (hasResult) {
                    const toolOutputType = this.categorizeToolOutput(toolName, toolResult.content);
                    switch (toolOutputType) {
                        case 'normal_tool_output':
                            statusDot = '<span class="status-dot status-success">●</span>';
                            break;
                        case 'overlong_tool_output':
                            statusDot = '<span class="status-dot status-warning">●</span>';
                            break;
                        case 'error_in_tool_call':
                        case 'tool_name_not_found':
                            statusDot = '<span class="status-dot status-error">●</span>';
                            break;
                        default:
                            statusDot = '<span class="status-dot status-success">●</span>';
                    }
                } else {
                    statusDot = '<span class="status-dot status-calling">●</span>';
                }

                sidebarHeader.innerHTML = `
                    <div class="tool-call-detail-icon">${iconHtml}</div>
                    <span class="tool-call-detail-name">${this.escapeHtml(toolName)}</span>
                    ${statusDot}
                `;
            }


            const toolDetailsHTML = toolCalls.map((toolCall, index) => {
                const toolName = toolCall.function?.name || '未知工具';
                const toolCallId = toolCall.id;
                const toolResult = this.toolResults.get(toolCallId);
                const hasResult = !!toolResult;
                const toolArgs = toolCall.function?.arguments || '{}';
                const parsedArgs = JSON.parse(toolArgs);


                let argumentsHTML;
                if (toolName === 'local-python-execute' && parsedArgs.code) {
                    argumentsHTML = `
                        <div class="tool-section">
                            <div class="tool-section-title">Code</div>
                            <div class="tool-python-code">${this.escapeHtml(parsedArgs.code)}</div>
                        </div>
                    `;
                } else {
                    argumentsHTML = `
                        <div class="tool-section">
                            <div class="tool-section-title">Arguments</div>
                            <div class="tool-args">${this.escapeHtml(JSON.stringify(parsedArgs, null, 2))}</div>
                        </div>
                    `;
                }


                let resultStatusClass = '';
                if (hasResult) {
                    const toolOutputType = this.categorizeToolOutput(toolName, toolResult.content);
                    switch (toolOutputType) {
                        case 'normal_tool_output':
                            resultStatusClass = 'tool-result-success';
                            break;
                        case 'overlong_tool_output':
                            resultStatusClass = 'tool-result-warning';
                            break;
                        case 'error_in_tool_call':
                        case 'tool_name_not_found':
                            resultStatusClass = 'tool-result-error';
                            break;
                        default:
                            resultStatusClass = 'tool-result-success';
                    }
                }


                let toolHeaderHTML = '';
                if (toolCalls.length > 1) {
                    const iconHtml = this.getToolIcon(toolName);
                    let statusDot;
                    if (hasResult) {
                        const toolOutputType = this.categorizeToolOutput(toolName, toolResult.content);
                        switch (toolOutputType) {
                            case 'normal_tool_output':
                                statusDot = '<span class="status-dot status-success">●</span>';
                                break;
                            case 'overlong_tool_output':
                                statusDot = '<span class="status-dot status-warning">●</span>';
                                break;
                            case 'error_in_tool_call':
                            case 'tool_name_not_found':
                                statusDot = '<span class="status-dot status-error">●</span>';
                                break;
                            default:
                                statusDot = '<span class="status-dot status-success">●</span>';
                        }
                    } else {
                        statusDot = '<span class="status-dot status-calling">●</span>';
                    }
                    
                    toolHeaderHTML = `
                        <div class="parallel-tool-header">
                            <div class="tool-call-detail-icon">${iconHtml}</div>
                            <span class="tool-call-detail-name">${this.escapeHtml(toolName)}</span>
                            ${statusDot}
                        </div>
                    `;
                }

                return `
                    ${toolCalls.length > 1 ? `<div class="parallel-tool-call">${toolHeaderHTML}` : ''}
                    ${argumentsHTML}
                    ${hasResult ? `
                        <div class="tool-section">
                            <div class="tool-section-title">Result</div>
                            <div class="tool-result ${resultStatusClass}">${this.escapeHtml(this.extractTextFromResult(toolResult.content))}</div>
                        </div>
                    ` : ''}
                    ${toolCalls.length > 1 ? '</div>' : ''}
                `;
            }).join('');

            this.toolDetails.innerHTML = toolDetailsHTML;
            this.toolSidebar.classList.add('open');
            console.log('Tool sidebar opened');
        }

    hideToolSidebar() {
        this.toolSidebar.classList.remove('open');
    }
}

let trajectoryReplayer;
document.addEventListener('DOMContentLoaded', () => {
    trajectoryReplayer = new TrajectoryReplayer();
});