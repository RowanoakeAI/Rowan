import os
import json
import re
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
from config.constants import EMAIL_DEFAULTS

@dataclass
class EmailConfig:
    """Email configuration settings for Gmail integration using OAuth2"""
    
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
    _auth_handler = None

    def initialize_auth(self):
        """Initialize auth handler lazily to avoid circular imports"""
        if not self._auth_handler:
            from utils.gmail_auth import GmailAuthHandler
            auth_handler = GmailAuthHandler(token_dir=self.token_dir)
            if not auth_handler.get_gmail_service():
                raise ValueError("Failed to initialize Gmail authentication")
            self._auth_handler = auth_handler
        return self._auth_handler

    def get_credentials(self):
        """Get OAuth credentials"""
        auth = self.initialize_auth()
        return auth.get_gmail_service()