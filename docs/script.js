import { CONFIG } from './config.js';

const DEFAULT_API_KEY = CONFIG.API_KEY;
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 1000;
const DEBOUNCE_DELAY = 300;
const REQUEST_TIMEOUT = 5000;
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

window.addEventListener('DOMContentLoaded', () => {
    rowanApi = new RowanAPI(DEFAULT_API_KEY);
    checkConnection();
    connectionCheckInterval = setInterval(checkConnection, 5000);
});

window.addEventListener('beforeunload', () => {
    clearInterval(connectionCheckInterval);
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