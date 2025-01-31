from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class CalendarConfig:
    """Calendar module configuration"""
    client_id: str
    client_secret: str 
    scopes: List[str]
    credentials_file: str
    token_file: str
    notification_enabled: bool = True
    default_reminder_times: List[int] = (15, 30, 60)
    sync_interval: int = 300  # 5 minutes
    max_retries: int = 3