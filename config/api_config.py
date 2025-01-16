"""API module configuration"""

class APIConfig:
    # API Settings
    API_PORT = 7692
    API_HOST = "0.0.0.0"
    
    # Security 
    API_KEY_HEADER = "X-API-Key"
    API_KEYS = ["test_key"]  # Replace with secure keys in production
    JWT_SECRET = "your-secret-key"  # Replace with secure secret in production
    
    # Rate Limiting
    RATE_LIMIT = 60  # Requests per minute
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        return bool(cls.API_KEYS and cls.JWT_SECRET)