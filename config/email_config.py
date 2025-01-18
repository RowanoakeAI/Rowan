import os
import json
import re
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class EmailConfig:
    """Email configuration settings for Gmail integration using OAuth2"""
    
    # Class-level constant for scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    email: str = os.getenv('EMAIL', '')
    client_id: str = ''
    client_secret: str = ''
    credentials_file: str = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    imap_server: str = "imap.gmail.com"
    smtp_server: str = "smtp.gmail.com" 
    smtp_port: int = 465
    max_emails_to_fetch: int = 10
    cache_duration: int = 300  # 5 minutes

    def __post_init__(self):
        """Initialize default values and validate configuration"""
        self._load_credentials()
        self.validate()
    
    def validate(self) -> None:
        """Validate the configuration settings"""
        if not self._is_valid_email(self.email):
            raise ValueError("Invalid email format")
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing OAuth2 credentials")
        if not self.smtp_port or not isinstance(self.smtp_port, int):
            raise ValueError("Invalid SMTP port")
        if not self.imap_server:
            raise ValueError("Missing IMAP server configuration")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format using regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @classmethod
    def from_env(cls) -> 'EmailConfig':
        """Create configuration from environment variables"""
        return cls(
            email=os.getenv('EMAIL'),
            client_id=os.getenv('GMAIL_CLIENT_ID'),
            client_secret=os.getenv('GMAIL_CLIENT_SECRET'),
            credentials_file=os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_token.json')
        )

    def _load_credentials(self):
        """Load credentials from JSON file if exists"""
        try:
            with open(self.credentials_file) as f:
                creds = json.load(f)
                self.client_id = creds['installed']['client_id'] 
                self.client_secret = creds['installed']['client_secret']
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            # Fallback to environment variables
            self.client_id = os.getenv('GMAIL_CLIENT_ID', '')
            self.client_secret = os.getenv('GMAIL_CLIENT_SECRET', '')