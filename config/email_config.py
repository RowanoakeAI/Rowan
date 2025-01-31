import os
import json
import re
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
from config.constants import GMAIL_SCOPES, EMAIL_DEFAULTS
from utils.gmail_auth import GmailAuthHandler
from google.oauth2.credentials import Credentials

@dataclass
class EmailConfig:
    """Email configuration settings for Gmail integration using OAuth2"""
    
    SCOPES = GMAIL_SCOPES
    
    # Server settings
    EMAIL_IMAP_SERVER: str = EMAIL_DEFAULTS['imap_server']
    EMAIL_SMTP_SERVER: str = EMAIL_DEFAULTS['smtp_server'] 
    EMAIL_SMTP_PORT: int = EMAIL_DEFAULTS['smtp_port']
    
    # OAuth settings
    email: str = os.getenv('EMAIL', '')
    credentials_file: str = os.path.join(os.path.dirname(__file__), "client_secrets.json")
    token_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    max_emails_to_fetch: int = EMAIL_DEFAULTS['max_emails']
    cache_duration: int = EMAIL_DEFAULTS['cache_duration']
    
    # Runtime attributes
    _auth_handler: Optional['GmailAuthHandler'] = None
    _credentials: Optional['Credentials'] = None

    def _load_credentials(self) -> None:
        """Load OAuth credentials from client_secrets.json"""
        try:
            if not os.path.exists(self.credentials_file):
                raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                
            with open(self.credentials_file, 'r') as f:
                creds = json.load(f)
                
            if 'installed' not in creds:
                raise ValueError("Invalid credentials format")
                
            self.client_id = creds['installed']['client_id']
            self.client_secret = creds['installed']['client_secret']
            
        except Exception as e:
            raise ValueError(f"Failed to load OAuth credentials: {str(e)}")

    def __post_init__(self):
        """Initialize OAuth credentials"""
        # Import here to avoid circular dependency
        from utils.gmail_auth import GmailAuthHandler
        
        self._load_credentials()
        
        # Initialize auth handler with proper scopes and token directory
        self._auth_handler = self.initialize_auth()
        
        # Validate configuration
        self.validate()
        
    def validate(self) -> None:
        """Validate the configuration settings"""
        if not self._is_valid_email(self.email):
            raise ValueError("Invalid email format")
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing OAuth2 credentials")

    def get_credentials(self):
        """Get OAuth credentials"""
        if not self._auth_handler:
            raise ValueError("Auth handler not initialized")
        return self._auth_handler.get_gmail_service()

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format using regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def initialize_auth(self) -> 'GmailAuthHandler':
        # Import here to avoid circular dependency
        from utils.gmail_auth import GmailAuthHandler
        
        auth_handler = GmailAuthHandler(
            scopes=self.SCOPES,
            token_dir=self.token_dir
        )
        if not auth_handler.initialize_auth():
            raise ValueError("Failed to initialize Gmail authentication")
        return auth_handler