"""API module configuration"""

class APIConfig:
    # API Settings
    API_PORT = 7692
    API_HOST = "0.0.0.0"
    
    # Security 
    API_KEY_HEADER = "X-API-Key"
    # Support both simple keys and dict-based keys with expiration
    API_KEYS = {
        "rowankey": {}  # Empty dict means no expiration
    }
    JWT_SECRET = "rowantest"  # Replace with secure secret in production
    
    # Rate Limiting
    RATE_LIMIT = 60  # Requests per minute
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        return bool(cls.API_KEYS and cls.JWT_SECRET)