import os
import json
import shutil
import pathlib
from typing import Any, Dict, Union, Optional, BinaryIO
from datetime import datetime
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging
from utils.logger import setup_logger  # Changed from relative to absolute import

class FileHandlingError(Exception):
    """Custom exception for file handling operations"""
    pass

class FileUtils:
    def __init__(self, base_path: str = None):
        self.logger = setup_logger(__name__)
        self.base_path = base_path or os.path.abspath(os.path.dirname(__file__))
        self.backup_dir = os.path.join(self.base_path, "backups")
        self._ensure_directories()
        self._encryption_key = None

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        os.makedirs(self.backup_dir, exist_ok=True)

    def _generate_encryption_key(self, password: str, salt: bytes = None) -> bytes:
        """Generate encryption key from password"""
        if not salt:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def set_encryption_key(self, password: str) -> None:
        """Set encryption key for file operations"""
        self._encryption_key = self._generate_encryption_key(password)

    def _create_backup(self, filepath: str) -> str:
        """Create a backup of the file before modifications"""
        if not os.path.exists(filepath):
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_path = os.path.join(
            self.backup_dir,
            f"{filename}.{timestamp}.bak"
        )
        shutil.copy2(filepath, backup_path)
        return backup_path

    def load_json(self, filepath: str, decrypt: bool = False) -> Dict[str, Any]:
        """Load and parse JSON file with optional decryption"""
        try:
            if not os.path.exists(filepath):
                raise FileHandlingError(f"File not found: {filepath}")

            with open(filepath, 'rb' if decrypt else 'r') as f:
                content = f.read()
                
            if decrypt:
                if not self._encryption_key:
                    raise FileHandlingError("Encryption key not set")
                fernet = Fernet(self._encryption_key)
                content = fernet.decrypt(content).decode()
                
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            raise FileHandlingError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise FileHandlingError(f"Error loading file: {str(e)}")

    def save_json(self, data: Dict[str, Any], filepath: str, 
                 encrypt: bool = False, create_backup: bool = True) -> None:
        """Save data to JSON file with optional encryption and backup"""
        try:
            if create_backup and os.path.exists(filepath):
                self._create_backup(filepath)

            content = json.dumps(data, indent=2)
            
            if encrypt:
                if not self._encryption_key:
                    raise FileHandlingError("Encryption key not set")
                fernet = Fernet(self._encryption_key)
                content = fernet.encrypt(content.encode())
                
                with open(filepath, 'wb') as f:
                    f.write(content)
            else:
                with open(filepath, 'w') as f:
                    f.write(content)
                    
        except Exception as e:
            raise FileHandlingError(f"Error saving file: {str(e)}")

    def delete_file(self, filepath: str, confirm: bool = True) -> bool:
        """Safely delete file with optional confirmation"""
        try:
            if not os.path.exists(filepath):
                raise FileHandlingError(f"File not found: {filepath}")

            if confirm:
                backup_path = self._create_backup(filepath)
                self.logger.info(f"Backup created at: {backup_path}")

            os.remove(filepath)
            return True
            
        except Exception as e:
            raise FileHandlingError(f"Error deleting file: {str(e)}")

    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Get detailed file information"""
        try:
            if not os.path.exists(filepath):
                raise FileHandlingError(f"File not found: {filepath}")

            stat = os.stat(filepath)
            path = pathlib.Path(filepath)
            
            return {
                "name": path.name,
                "extension": path.suffix,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "accessed": datetime.fromtimestamp(stat.st_atime),
                "checksum": self._calculate_checksum(filepath)
            }
            
        except Exception as e:
            raise FileHandlingError(f"Error getting file info: {str(e)}")

    def _calculate_checksum(self, filepath: str, algorithm: str = 'sha256') -> str:
        """Calculate file checksum"""
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def create_directory(self, dirpath: str) -> None:
        """Create directory if it doesn't exist"""
        try:
            os.makedirs(dirpath, exist_ok=True)
        except Exception as e:
            raise FileHandlingError(f"Error creating directory: {str(e)}")

    def list_directory(self, dirpath: str, pattern: str = None) -> list:
        """List directory contents with optional pattern matching"""
        try:
            path = pathlib.Path(dirpath)
            if pattern:
                return list(path.glob(pattern))
            return list(path.iterdir())
        except Exception as e:
            raise FileHandlingError(f"Error listing directory: {str(e)}")

    def restore_backup(self, filepath: str, backup_timestamp: str = None) -> bool:
        """Restore file from backup"""
        try:
            filename = os.path.basename(filepath)
            if backup_timestamp:
                backup_path = os.path.join(
                    self.backup_dir,
                    f"{filename}.{backup_timestamp}.bak"
                )
            else:
                # Get most recent backup
                backups = sorted(
                    pathlib.Path(self.backup_dir).glob(f"{filename}.*.bak"),
                    key=os.path.getmtime,
                    reverse=True
                )
                if not backups:
                    raise FileHandlingError("No backups found")
                backup_path = str(backups[0])

            shutil.copy2(backup_path, filepath)
            return True
            
        except Exception as e:
            raise FileHandlingError(f"Error restoring backup: {str(e)}")