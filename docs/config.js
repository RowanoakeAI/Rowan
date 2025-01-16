import { CONFIG } from './config.js';

export const CONFIG = {
    API_PORT: 7692,
    API_HOST: 'localhost',
    API_KEY: 'publickey'
};

const DEFAULT_API_KEY = CONFIG.API_KEY;
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 1000;
const DEBOUNCE_DELAY = 300;
const REQUEST_TIMEOUT = 5000;
const MAX_REQUESTS_PER_MINUTE = 60;
const CIRCUIT_BREAKER_THRESHOLD = 5;

class RowanAPI {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseUrl = `https://${CONFIG.API_HOST}:${CONFIG.API_PORT}`;
        this.requestQueue = [];
        this.cache = new Map();
        this.isProcessingQueue = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.requestCount = 0;
        this.lastRequestTime = Date.now();
        this.failureCount = 0;
        this.circuitOpen = false;
        this.lastCircuitReset = Date.now();
    }

    validateRequest(message) {
        if (!message || typeof message !== 'string') {
            throw new Error('Invalid message format');
        }
        if (message.length > 1000) {
            throw new Error('Message too long');
        }
        return true;
    }

    checkRateLimit() {
        const now = Date.now();
        if (now - this.lastRequestTime >= 60000) {
            this.requestCount = 0;
            this.lastRequestTime = now;
        }
        if (this.requestCount >= MAX_REQUESTS_PER_MINUTE) {
            throw new Error('Rate limit exceeded');
        }
        this.requestCount++;
    }

    async checkCircuitBreaker() {
        if (this.circuitOpen) {
            if (Date.now() - this.lastCircuitReset > RETRY_DELAY * 5) {
                this.circuitOpen = false;
                this.failureCount = 0;
                this.lastCircuitReset = Date.now();
            } else {
                throw new Error('Circuit breaker is open');
            }
        }
    }

    async checkConnection() {
        try {
            await this.checkCircuitBreaker();
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

            const response = await fetch(`${this.baseUrl}/status`, {
                headers: {
                    'X-API-Key': this.apiKey,
                    'Accept': 'application/json'
                },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.reconnectAttempts = 0;
            this.failureCount = 0;
            return true;
        } catch (error) {
            console.error('Connection check failed:', error);
            this.failureCount++;
            
            if (this.failureCount >= CIRCUIT_BREAKER_THRESHOLD) {
                this.circuitOpen = true;
                this.lastCircuitReset = Date.now();
            }

            this.reconnectAttempts++;
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return this.checkConnection();
            }
            return false;
        }
    }

    async sendRequestWithRetry(message, attempt = 1) {
        try {
            await this.checkCircuitBreaker();
            this.checkRateLimit();
            this.validateRequest(message);

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
                    'X-API-Key': this.apiKey,
                    'Accept': 'application/json'
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
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (!data || !data.response) {
                throw new Error('Invalid response format');
            }

            this.cache.set(cacheKey, data.response);
            this.failureCount = 0;
            return data.response;
        } catch (error) {
            console.error('Request failed:', error);
            this.failureCount++;
            
            if (this.failureCount >= CIRCUIT_BREAKER_THRESHOLD) {
                this.circuitOpen = true;
                this.lastCircuitReset = Date.now();
            }

            if (attempt < RETRY_ATTEMPTS) {
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return this.sendRequestWithRetry(message, attempt + 1);
            }
            throw error;
        }
    }

    sanitizeInput(input) {
        if (typeof input !== 'string') return '';
        return input.replace(/[<>{}]/g, '').trim();
    }

    // ... rest of the existing code ...
}

// ... rest of the existing code ...