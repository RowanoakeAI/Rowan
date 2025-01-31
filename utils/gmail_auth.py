import os
import pickle
from pathlib import Path
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.logger import setup_logger

# Move scopes directly here to break circular import
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailAuthError(Exception):
    """Custom exception for Gmail authentication errors"""
    pass

class GmailAuthHandler:
    """Handles Gmail OAuth2 authentication"""
    def __init__(self, scopes: Optional[List[str]] = None, token_dir: Optional[str] = None):
        self.logger = setup_logger(__name__)
        self.project_root = Path(__file__).parent.parent
        self.scopes = scopes or GMAIL_SCOPES
        
        # Set up paths
        self.token_dir = Path(token_dir) if token_dir else self.project_root / 'data'
        self._token_path = self.token_dir / 'gmail_token.pickle'
        self._secrets_path = self._find_secrets_file()


    def _find_secrets_file(self) -> Path:
        """Search for client_secrets.json in multiple locations"""
        search_paths = [
            'config/client_secrets.json',
            'credentials/client_secrets.json',
            'secrets/client_secrets.json'
        ]
        
        for path in search_paths:
            full_path = self.project_root / path
            if full_path.exists():
                return full_path
        return self.project_root / 'config' / 'client_secrets.json'

    def initialize_auth(self) -> bool:
        """Initialize Gmail authentication"""
        try:
            self.logger.info("Initializing Gmail authentication...")
            creds = self.get_gmail_service()
            if creds and creds.valid and self._validate_scopes(creds):
                self.logger.info("Gmail authentication completed successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Gmail authentication failed: {str(e)}")
            return False

    def get_gmail_service(self) -> Optional[Credentials]:
        """Get Gmail credentials"""
        try:
            if not self._secrets_path.exists():
                raise FileNotFoundError("client_secrets.json not found")
            return self._authenticate()
        except Exception as e:
            self.logger.error(f"Failed to get Gmail service: {str(e)}")
            return None

    def _validate_scopes(self, creds: Credentials) -> bool:
        """Validate credential scopes"""
        return all(scope in creds.scopes for scope in self.scopes)

    def _authenticate(self) -> Optional[Credentials]:
        """Authenticate with Gmail"""
        creds = None
        if self._token_path.exists():
            self.logger.info("Found existing token, attempting to load...")
            with open(self._token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            creds = self._handle_invalid_credentials(creds)

        return creds

    def _handle_invalid_credentials(self, creds: Optional[Credentials]) -> Optional[Credentials]:
        """Handle invalid or expired credentials"""
        try:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Token expired, attempting refresh...")
                creds = self._refresh_token(creds)
                self.logger.info("Token refresh successful")
            else:
                self.logger.info("Getting new credentials...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._secrets_path), self.scopes)
                creds = flow.run_local_server(port=0)

            # Save the credentials
            self._save_credentials(creds)
            return creds
        except Exception as e:
            self.logger.error(f"Failed to handle invalid credentials: {str(e)}")
            return None

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file"""
        self.logger.info("Saving new token...")
        os.makedirs(os.path.dirname(self._token_path), exist_ok=True)
        with open(self._token_path, 'wb') as token:
            pickle.dump(creds, token)
        self.logger.info(f"Token saved successfully at {self._token_path}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _refresh_token(self, creds: Credentials) -> Credentials:
        """Refresh the access token"""
        creds.refresh(Request())
        return creds

auth_handler = GmailAuthHandler()
auth_handler.initialize_auth()