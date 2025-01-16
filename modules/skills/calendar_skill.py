# modules/skills/calendar_skill.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from core.module_manager import ModuleInterface
from core.personal_memory import PersonalMemorySystem
from utils.logger import setup_logger
from typing import Dict, Any
import os.path
import pickle
from dateutil.parser import parse as parse_date
import re
from typing import Tuple, Optional

class GoogleCalendarSkill(ModuleInterface):
    """Desktop OAuth implementation for Google Calendar"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',              # Full access
        'https://www.googleapis.com/auth/calendar.readonly',     # Read-only
        'https://www.googleapis.com/auth/calendar.events',       # Manage events
        'https://www.googleapis.com/auth/calendar.events.readonly', # Read events
        'https://www.googleapis.com/auth/calendar.settings.readonly', # Read settings
        'https://www.googleapis.com/auth/calendar.addons.execute', # Add-ons
    ]

    # Update CLIENT_CONFIG for desktop app
    CLIENT_CONFIG = {
        "installed": {
            "client_id": "339870206772-0s4785kprlqhfjg2rj2255c2pf5hfg1c.apps.googleusercontent.com",
            "project_id": "rowan-448007",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "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",
            "redirect_uris": ["http://localhost"]
        }
    }

    # Update command patterns to be more natural
    COMMAND_PATTERNS = {
        "add": r"(?:can you |please |)(?:schedule|add|create|set up|make).*?(?:meeting|appointment|event|reminder)",
        "check": r"(?:can you |please |what)(?:check|look up|show|tell me|display|view|do I have).*?(?:calendar|schedule|planned|upcoming)",
        "remove": r"(?:can you |please |)(?:remove|delete|cancel|clear).*?(?:meeting|appointment|event)",
        "list": r"(?:can you |please |)(?:list|show|get|tell me|what are).*?(?:events|meetings|appointments|schedule)"
    }

    def __init__(self):
        super().__init__()
        self.creds = None
        self.service = None
        self.memory = PersonalMemorySystem()
        self.logger = setup_logger(__name__)
        self.initialized = False
        self.command_handlers = {
            "add": self._handle_add,
            "check": self._handle_check,
            "remove": self._handle_remove,
            "list": self._handle_list
        }
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize calendar integration with improved error handling"""
        try:
            if not config:
                self.logger.error("No configuration provided")
                return False
                
            self._authenticate()
            self.initialized = True
            self.logger.info("Calendar module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize calendar: {str(e)}")
            return False

    def _authenticate(self):
        """Handle desktop app authentication"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', 
                    self.SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Desktop flow
                )
                self.creds = flow.run_local_server(port=0)
                
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('calendar', 'v3', credentials=self.creds)

    def sync_events(self):
        """Sync Google Calendar events with Rowan's memory"""
        try:
            # Get events from the next 7 days
            now = datetime.utcnow()
            timeMin = now.isoformat() + 'Z'
            timeMax = (now + timedelta(days=7)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=timeMin,
                timeMax=timeMax,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            # Store in Rowan's memory
            for event in events:
                self.memory.store_calendar_event({
                    'event_id': event['id'],
                    'title': event['summary'],
                    'start': event.get('start', {}).get('dateTime', event['start'].get('date')),
                    'end': event.get('end', {}).get('dateTime', event['end'].get('date')),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': [a.get('email') for a in event.get('attendees', [])]
                })
                
            return len(events)

        except Exception as e:
            self.logger.error(f"Error syncing calendar events: {e}")
            return 0

    def add_event(self, title: str, start_time: datetime, 
                 end_time: datetime, description: str = None,
                 location: str = None) -> bool:
        """Add new calendar event and sync to memory"""
        try:
            event = {
                'summary': title,
                'start': {'dateTime': start_time.isoformat()},
                'end': {'dateTime': end_time.isoformat()}
            }
            if description:
                event['description'] = description
            if location:
                event['location'] = location

            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            # Store in Rowan's memory
            self.memory.store_calendar_event({
                'event_id': created_event['id'],
                'title': title,
                'start': start_time,
                'end': end_time,
                'description': description,
                'location': location
            })
            
            return True

        except Exception as e:
            self.logger.error(f"Error adding calendar event: {e}")
            return False

    def process(self, input_data: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process calendar commands with improved validation"""
        if not self.initialized:
            return {
                "success": False,
                "response": "Calendar module not initialized properly"
            }

        try:
            command, params = self._parse_command(input_data)
            if not command:
                self.logger.warning(f"Invalid command format: {input_data}")
                return {
                    "success": False,
                    "response": "Invalid calendar command format"
                }

            handler = self.command_handlers.get(command)
            if not handler:
                self.logger.warning(f"Unsupported command: {command}")
                return {
                    "success": False,
                    "response": "Unsupported calendar operation"
                }

            self.logger.info(f"Processing calendar command: {command}")
            result = handler(params, context or {})
            
            if not isinstance(result, dict) or 'success' not in result:
                self.logger.error(f"Invalid handler response format from {command}")
                return {
                    "success": False,
                    "response": "Internal processing error"
                }
                
            return result

        except Exception as e:
            self.logger.exception(f"Error processing calendar command: {str(e)}")
            return {
                "success": False,
                "response": "Error processing calendar request"
            }

    def _parse_command(self, input_text: str) -> Tuple[Optional[str], str]:
        """Parse input text to determine command and parameters"""
        input_lower = input_text.lower()
        
        for cmd, pattern in self.COMMAND_PATTERNS.items():
            if re.search(pattern, input_lower):
                return cmd, input_text
        
        return None, input_text

    def _handle_add(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add/schedule commands with improved parsing"""
        try:
            doc = input_text.lower()
            
            # Extract date/time with better patterns
            date_matches = re.findall(r'(?:on|for|at|this|next) (.*?)(?:$|\s(?:with|about|for|to))', doc)
            if not date_matches:
                return {"success": False, "response": "I couldn't determine when this event should be scheduled. When would you like it?"}
            
            # Extract duration if specified
            duration_match = re.findall(r'for (\d+) (?:hour|hours|hr|hrs)', doc)
            duration = int(duration_match[0]) if duration_match else 1
            
            start_time = parse_date(date_matches[0], fuzzy=True)
            end_time = start_time + timedelta(hours=duration)
            
            # Better title extraction
            title_pattern = r'(?:schedule|add|create|set up|make) (.*?)(?:(?:on|at|for|next|this|with|about)|$)'
            title_matches = re.findall(title_pattern, doc)
            title = title_matches[0].strip() if title_matches else "Untitled Event"
            
            # Extract location if any
            location_match = re.findall(r'(?:at|in) (.*?)(?:$|\s(?:on|at|for))', doc)
            location = location_match[0].strip() if location_match else None
            
            # Extract description/notes
            desc_match = re.findall(r'(?:about|regarding|notes?:?) (.*?)(?:$)', doc)
            description = desc_match[0].strip() if desc_match else None
            
            success = self.add_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location
            )

            if success:
                response = f"I've scheduled '{title}' for {start_time.strftime('%A, %B %d at %I:%M %p')}"
                if location:
                    response += f" at {location}"
                if duration != 1:
                    response += f" for {duration} hours"
                return {"success": True, "response": response}
            
            return {"success": False, "response": "I wasn't able to add that event. Would you like to try again?"}

        except Exception as e:
            self.logger.error(f"Error in calendar add: {str(e)}")
            return {
                "success": False,
                "response": "I had trouble understanding when to schedule that. Could you rephrase it?"
            }

    def _format_event_time(self, event_time: str) -> str:
        """Format event time for display"""
        dt = parse_date(event_time)
        return dt.strftime("%A, %B %d at %I:%M %p")

    def _handle_check(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle calendar check commands with better formatting"""
        try:
            events_count = self.sync_events()
            if events_count > 0:
                events = self.memory.get_calendar_events()
                response = "Here's what's coming up:\n\n"
                for event in events[:5]:
                    response += f"• {event['title']}\n"
                    response += f"  {self._format_event_time(event['start'])}"
                    if event.get('location'):
                        response += f" at {event['location']}"
                    response += "\n"
                return {"success": True, "response": response}
            return {"success": True, "response": "You don't have any upcoming events scheduled."}
        except Exception as e:
            return {"success": False, "response": "I had trouble checking your calendar. Would you like to try again?"}

    def _handle_remove(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event removal commands"""
        # TODO: Implement event removal logic
        return {"success": False, "response": "Event removal not implemented yet"}

    def _handle_list(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle listing events"""
        return self._handle_check(input_text, context)