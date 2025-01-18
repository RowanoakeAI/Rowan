import os
import pickle
from pathlib import Path
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import sys
from tenacity import retry, stop_after_attempt, wait_exponential

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from config.email_config import EmailConfig
from utils.logger import setup_logger

class GmailAuthError(Exception):
    """Custom exception for Gmail authentication errors"""
    pass

class GmailAuthHandler:
    """Handles Gmail OAuth2 authentication with improved error handling"""
    
    DEFAULT_PATHS = [
        'config/client_secrets.json',
        'credentials/client_secrets.json',
        os.path.expanduser('~/.config/rowan/client_secrets.json')
    ]

    def __init__(self) -> None:
        self.logger = setup_logger(__name__)
        self.project_root = Path(__file__).parent.parent
        self._token_path = self.project_root / 'data' / 'gmail_token.pickle'
        self._secrets_path = self._find_secrets_file()

    def _find_secrets_file(self) -> Path:
        """Search for client_secrets.json in multiple locations"""
        for path in self.DEFAULT_PATHS:
            full_path = self.project_root / path
            if full_path.exists():
                return full_path
        return self.project_root / 'config' / 'client_secrets.json'
        
    @property
    def token_path(self) -> str:
        return str(self._token_path)
        
    @property
    def secrets_path(self) -> str:
        return str(self._secrets_path)
        
    def _validate_scopes(self, creds: Credentials) -> bool:
        """Validate if credentials have required scopes"""
        return all(scope in creds.scopes for scope in EmailConfig.SCOPES)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _refresh_token(self, creds: Credentials) -> Credentials:
        """Refresh the access token with retry mechanism"""
        try:
            creds.refresh(Request())
            return creds
        except Exception as e:
            self.logger.error(f"Token refresh failed: {str(e)}")
            raise GmailAuthError(f"Failed to refresh token: {str(e)}")

    def get_gmail_service(self) -> Optional[Credentials]:
        """Get Gmail credentials with enhanced error handling"""
        try:
            if not self._secrets_path.exists():
                self.logger.error(f"Client secrets not found in any default location")
                self.logger.info(f"Please place client_secrets.json in one of: {self.DEFAULT_PATHS}")
                raise FileNotFoundError(f"client_secrets.json not found in default paths")

            return self._authenticate()

        except Exception as e:
            self.logger.error(f"Gmail authentication failed: {str(e)}")
            self._handle_auth_error(e)
            return None

    def _handle_auth_error(self, error: Exception) -> None:
        """Handle authentication errors with guidance"""
        if isinstance(error, FileNotFoundError):
            self.logger.info(
                "To fix:\n"
                "1. Go to Google Cloud Console\n"
                "2. Create a new project\n" 
                "3. Enable Gmail API\n"
                "4. Create OAuth 2.0 credentials\n"
                "5. Download as client_secrets.json\n"
                f"6. Place in one of: {self.DEFAULT_PATHS}"
            )

    def _authenticate(self) -> Credentials:
        """
        Get Gmail credentials using OAuth2
        
        Returns:
            Credentials: Valid Gmail OAuth2 credentials
            
        Raises:
            GmailAuthError: If authentication fails
            FileNotFoundError: If client secrets file is missing
        """
        creds = None
        self.logger.info("Starting Gmail authentication process...")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        
        try:
            if os.path.exists(self.token_path):
                self.logger.info("Found existing token, attempting to load...")
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                self.logger.info("Successfully loaded existing token")
                    
            if not creds or not creds.valid:
                self.logger.info("Token invalid or missing, checking refresh status...")
                if creds and creds.expired and creds.refresh_token:
                    self.logger.info("Token expired, attempting refresh...")
                    creds = self._refresh_token(creds)
                    self.logger.info("Token refresh successful")
                else:
                    self.logger.info("Initiating new OAuth2 flow...")
                    if not os.path.exists(self.secrets_path):
                        self.logger.error(f"Client secrets file not found at {self.secrets_path}")
                        raise FileNotFoundError("client_secrets.json not found")
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.secrets_path, 
                        EmailConfig.SCOPES
                    )
                    self.logger.info("Please authenticate in the browser window...")
                    creds = flow.run_local_server(port=0)
                    self.logger.info("Browser authentication successful")
                
                # Validate scopes
                self.logger.info("Validating permission scopes...")
                if not self._validate_scopes(creds):
                    self.logger.error("Insufficient permission scopes detected")
                    raise GmailAuthError("Insufficient permission scopes")
                self.logger.info("Scope validation successful")
                    
                # Save the credentials for the next run
                self.logger.info("Saving new token...")
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                self.logger.info(f"Token saved successfully at {self.token_path}")
                    
            return creds
            
        except Exception as e:
            self.logger.error(f"Error in Gmail authentication: {str(e)}")
            raise GmailAuthError(f"Authentication failed: {str(e)}")
            
    def initialize_auth(self) -> bool:
        """
        Initialize Gmail authentication
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.logger.info("Initializing Gmail authentication...")
            creds = self.get_gmail_service()
            if creds and creds.valid and self._validate_scopes(creds):
                self.logger.info("Gmail authentication completed successfully")
                return True
            self.logger.warning("Gmail authentication failed validation checks")
            return False
        except Exception as e:
            self.logger.error(f"Gmail authentication initialization failed: {str(e)}")
            return False

auth_handler = GmailAuthHandler()
auth_handler.initialize_auth()