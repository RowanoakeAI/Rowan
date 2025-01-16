import { CONFIG, CONSTANTS } from './config.js';

// Remove duplicate CONFIG declaration and use imported constants
const {
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    DEBOUNCE_DELAY,
    REQUEST_TIMEOUT,
    STATS_UPDATE_INTERVAL
} = CONSTANTS;

const DEFAULT_API_KEY = CONFIG.API_KEY;
let statsUpdateInterval;
const counter = document.getElementById('counter');

class RowanAPI {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseUrl = `https://${CONFIG.API_HOST}:${CONFIG.API_PORT}`;
        this.requestQueue = [];
        this.cache = new Map();
        this.isProcessingQueue = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    async checkConnection() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

            const response = await fetch(`${this.baseUrl}/status`, {
                headers: {
                    'X-API-Key': this.apiKey
                },
                signal: controller.signal
            }); 
            clearTimeout(timeoutId);
            
            this.reconnectAttempts = 0;
            return response.ok;
        } catch (error) {
            this.reconnectAttempts++;
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return this.checkConnection();
            }
            return false;
        }
    }

    async sendMessage(message) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({ message, resolve, reject });
            this.processQueue();
        });
    }

    async processQueue() {
        if (this.isProcessingQueue || this.requestQueue.length === 0) return;
        this.isProcessingQueue = true;

        while (this.requestQueue.length > 0) {
            const { message, resolve, reject } = this.requestQueue[0];

            try {
                const response = await this.sendRequestWithRetry(message);
                resolve(response);
            } catch (error) {
                reject(error);
            }

            this.requestQueue.shift();
        }

        this.isProcessingQueue = false;
    }

    async sendRequestWithRetry(message, attempt = 1) {
        try {
            // Check cache first
            const cacheKey = JSON.stringify(message);
            if (this.cache.has(cacheKey)) {
                return this.cache.get(cacheKey);
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

            const sanitizedMessage = this.sanitizeInput(message);
            const response = await fetch(`${this.baseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    message: sanitizedMessage,
                    context_type: 'casual',
                    source: 'web'
                }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error('API request failed');
            }

            const data = await response.json();
            // Cache the response
            this.cache.set(cacheKey, data.response);
            return data.response;
        } catch (error) {
            if (attempt < RETRY_ATTEMPTS) {
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return this.sendRequestWithRetry(message, attempt + 1);
            }
            throw error;
        }
    }

    sanitizeInput(input) {
        return input.replace(/[<>]/g, '').trim();
    }
}

let rowanApi = null;
let connectionCheckInterval;
const messagesContainer = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const connectionStatus = document.getElementById('connection-status');

// Debounce function
function debounce(func, delay) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

window.addEventListener('DOMContentLoaded', async () => {
    rowanApi = new RowanAPI(DEFAULT_API_KEY);
    checkConnection();
    connectionCheckInterval = setInterval(checkConnection, 5000);
    
    // Initial stats update
    await updateCodebaseStats();
    
    // Set up interval for stats updates
    statsUpdateInterval = setInterval(updateCodebaseStats, STATS_UPDATE_INTERVAL);
});

window.addEventListener('beforeunload', () => {
    clearInterval(connectionCheckInterval);
    clearInterval(statsUpdateInterval);
});

const addMessage = (message, isUser = false) => {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', isUser ? 'user-message' : 'assistant-message');
    messageElement.textContent = message;
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
};

const checkConnection = async () => {
    if (!rowanApi) return;
    const isConnected = await rowanApi.checkConnection();
    connectionStatus.textContent = isConnected ? 'Connected' : 'Disconnected';
    connectionStatus.classList.toggle('connected', isConnected);
};

const handleSendMessage = debounce(async () => {
    const message = messageInput.value.trim();
    if (!message || !rowanApi) return;

    messageInput.value = '';
    addMessage(message, true);

    try {
        const response = await rowanApi.sendMessage(message);
        addMessage(response);
    } catch (error) {
        addMessage('Error: Failed to get response from Rowan');
    }
}, DEBOUNCE_DELAY);

apiKeyInput.addEventListener('change', () => {
    rowanApi = new RowanAPI(apiKeyInput.value);
    checkConnection();
});

sendButton.addEventListener('click', handleSendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSendMessage();
});

function updateCounter() {
    const text = messageInput.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    counter.textContent = `${words} words | ${chars} characters`;
}

messageInput.addEventListener('input', updateCounter);

// Add this function
async function updateCodebaseStats() {
    try {
        console.log('Fetching codebase stats...');
        const response = await fetch('codebase_stats.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Update DOM with stats
        const stats = {
            'stats-files': data.total.files,
            'stats-lines': data.total.lines,
            'stats-code': data.total.code_lines,
            'stats-comments': data.total.comment_lines,
            'stats-char': data.total.chars,
            'stats-words': data.total.words,
            'stats-size': (data.total.size / 1024).toFixed(2)
        };

        Object.entries(stats).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = typeof value === 'number' ? 
                    value.toLocaleString() : value;
            }
        });

        console.log('Stats updated successfully');
    } catch (error) {
        console.error('Failed to update codebase stats:', error);
    }
}