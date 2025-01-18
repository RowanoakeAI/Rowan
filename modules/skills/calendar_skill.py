# modules/skills/calendar_skill.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from core.module_manager import ModuleInterface
from core.personal_memory import PersonalMemorySystem
from utils.logger import setup_logger
from typing import Dict, Any, List, Optional
import os.path
import pickle
from dateutil.parser import parse as parse_date
import re
from typing import Tuple, Optional
from threading import Timer
from modules.notifications.notification_module import NotificationsModule
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from dateutil.tz import tzlocal
from dateutil.relativedelta import relativedelta
import pytz
import calendar

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
        "list": r"(?:can you |please |)(?:list|show|get|tell me|what are).*?(?:events|meetings|appointments|schedule)",
        "modify": r"(?:can you |please |)(?:update|modify|change|reschedule).*?(?:meeting|appointment|event)",
        "update": r"(?:can you |please |)(?:update|modify|change).*?(?:details|description|location|time) for.*?(?:meeting|appointment|event)",
        "recurring": r"(?:can you |please |)(?:schedule|add|create|set up|make).*?(?:weekly|daily|monthly|every|recurring).*?(?:meeting|appointment|event)"
    }

    # Add recurrence pattern definitions
    RECURRENCE_PATTERNS = {
        'daily': ['RRULE:FREQ=DAILY'],
        'weekly': ['RRULE:FREQ=WEEKLY'],
        'monthly': ['RRULE:FREQ=MONTHLY'],
        'weekday': ['RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'],
        'custom': lambda interval, freq: [f'RRULE:FREQ={freq};INTERVAL={interval}']
    }

    # Add time of day definitions
    TIME_OF_DAY = {
        'morning': (8, 0),    # 8:00 AM
        'afternoon': (13, 0), # 1:00 PM
        'evening': (18, 0),   # 6:00 PM
        'night': (20, 0)      # 8:00 PM
    }

    # Default durations (in hours)
    DEFAULT_DURATIONS = {
        'meeting': 1,
        'appointment': 1,
        'lunch': 1,
        'dinner': 2,
        'conference': 2,
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
        self.notification_module: Optional[NotificationsModule] = None
        self.notification_timers = {}  # Store active notification timers
        self.default_reminder_times = [15, 30, 60]  # Minutes before event
        self.last_sync_time = None
        self.sync_state = {
            'success': False,
            'last_attempt': None,
            'error': None,
            'events_synced': 0
        }
        # Add new sync configuration
        self.sync_config = {
            'batch_size': 100,
            'sync_interval': 300,  # 5 minutes
            'max_retries': 3,
            'conflict_resolution': 'newer_wins'
        }
        
        # Add sync state tracking
        self.sync_state = {
            'last_sync': None,
            'pending_changes': [],
            'conflicts': [],
            'sync_in_progress': False
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
            
            # Initialize notification module
            self.notification_module = config.get('notification_module')
            if not self.notification_module:
                self.logger.warning("No notification module provided - notifications disabled")
            
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _sync_events_with_retry(self) -> Tuple[bool, List[Dict]]:
        """Sync events with retry mechanism"""
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
        
        return True, events_result.get('items', [])

    def sync_events(self) -> int:
        """Enhanced sync with improved error handling"""
        try:
            self.sync_state['last_attempt'] = datetime.now()
            
            # Validate service connection
            if not self.service or not self.initialized:
                raise ValueError("Calendar service not properly initialized")

            # Attempt sync with retry
            success, events = self._sync_events_with_retry()
            
            # Process and store events
            synced_count = 0
            for event in events:
                try:
                    # Validate event data
                    if not self._validate_event_data(event):
                        self.logger.warning(f"Skipping invalid event: {event.get('id', 'unknown')}")
                        continue
                        
                    # Store event
                    self.memory.store_calendar_event({
                        'event_id': event['id'],
                        'title': event['summary'],
                        'start': event.get('start', {}).get('dateTime', event['start'].get('date')),
                        'end': event.get('end', {}).get('dateTime', event['end'].get('date')),
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'attendees': [a.get('email') for a in event.get('attendees', [])]
                    })
                    synced_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing event {event.get('id', 'unknown')}: {str(e)}")
                    continue

            # Update sync state
            self.sync_state.update({
                'success': True,
                'last_sync': datetime.now(),
                'error': None,
                'events_synced': synced_count
            })
            
            self.logger.info(f"Successfully synced {synced_count} events")
            return synced_count

        except RetryError as e:
            self._handle_sync_failure("Max retries exceeded", e)
            raise
            
        except ValueError as e:
            self._handle_sync_failure("Validation error", e)
            raise
            
        except Exception as e:
            self._handle_sync_failure("Unexpected error", e)
            raise

    def _validate_event_data(self, event: Dict) -> bool:
        """Validate event data structure"""
        required_fields = ['id', 'summary', 'start']
        return all(field in event for field in required_fields)

    def _handle_sync_failure(self, error_type: str, error: Exception) -> None:
        """Handle sync failures with detailed logging"""
        self.sync_state.update({
            'success': False,
            'error': f"{error_type}: {str(error)}"
        })
        
        self.logger.error(
            "Calendar sync failed\n"
            f"Error Type: {error_type}\n"
            f"Error: {str(error)}\n"
            f"Last Success: {self.sync_state.get('last_sync', 'Never')}\n"
            "Attempted Recovery: True"
        )

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'success': self.sync_state['success'],
            'last_sync': self.sync_state.get('last_sync'),
            'last_attempt': self.sync_state['last_attempt'],
            'error': self.sync_state.get('error'),
            'events_synced': self.sync_state['events_synced']
        }

    def add_event(self, title: str, start_time: datetime, 
                 end_time: datetime, description: str = None,
                 location: str = None, attendees: List[str] = None,
                 reminder_times: List[int] = None,
                 recurrence: Dict[str, Any] = None) -> bool:
        """Add new calendar event with recurrence support"""
        try:
            event = {
                'summary': title,
                'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'}
            }
            
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
                event['guestsCanModify'] = True

            # Add recurrence rules
            if recurrence:
                if recurrence['type'] in self.RECURRENCE_PATTERNS:
                    if recurrence['type'] == 'custom':
                        event['recurrence'] = self.RECURRENCE_PATTERNS['custom'](
                            recurrence['interval'],
                            recurrence['frequency']
                        )
                    else:
                        event['recurrence'] = self.RECURRENCE_PATTERNS[recurrence['type']]

                # Add end conditions
                if 'until' in recurrence:
                    event['recurrence'][0] += f';UNTIL={recurrence["until"].strftime("%Y%m%dT%H%M%SZ")}'
                elif 'count' in recurrence:
                    event['recurrence'][0] += f';COUNT={recurrence["count"]}'

            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all' if attendees else 'none'
            ).execute()

            # Store in memory with recurrence info
            event_data = {
                'event_id': created_event['id'],
                'title': title,
                'start': start_time,
                'end': end_time,
                'description': description,
                'location': location,
                'attendees': attendees or [],
                'recurrence': recurrence
            }
            self.memory.store_calendar_event(event_data)

            # Schedule notifications for first occurrence
            self.schedule_notifications(
                created_event['id'],
                event_data,
                reminder_times
            )

            return True

        except Exception as e:
            self.logger.error(f"Error adding recurring calendar event: {e}")
            return False

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing calendar event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Apply updates
            for key, value in updates.items():
                if key in ['start', 'end']:
                    event[key] = {'dateTime': value.isoformat(), 'timeZone': 'UTC'}
                else:
                    event[key] = value

            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all' if event.get('attendees') else 'none'
            ).execute()

            # Update memory
            self.memory.store_calendar_event({
                'event_id': updated_event['id'],
                'title': updated_event['summary'],
                'start': parse_date(updated_event['start']['dateTime']),
                'end': parse_date(updated_event['end']['dateTime']),
                'description': updated_event.get('description'),
                'location': updated_event.get('location'),
                'attendees': [a.get('email') for a in updated_event.get('attendees', [])]
            })

            # Reschedule notifications if time changed
            if 'start' in updates:
                self.cleanup_notifications(event_id)
                if updated_event:
                    event_details = {
                        'id': updated_event['id'],
                        'title': updated_event['summary'],
                        'start': parse_date(updated_event['start']['dateTime']),
                        'location': updated_event.get('location')
                    }
                    self.schedule_notifications(event_id, event_details)

            return True

        except Exception as e:
            self.logger.error(f"Error updating calendar event: {e}")
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

    def _parse_event_details(self, input_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse event details with improved datetime handling"""
        details = {}
        
        # Parse title
        title_match = re.search(r'(?:schedule|add|create|set up|make)\s+(.*?)(?:on|at|for|next|this|tomorrow|$)', input_text)
        if title_match:
            details['title'] = title_match.group(1).strip()

        # Parse location
        location_match = re.search(r'(?:at|in)\s+(.*?)(?:on|at|for|$)', input_text)
        if location_match:
            details['location'] = location_match.group(1).strip()

        # Parse date/time
        datetime_result = self._parse_datetime(input_text, context)
        if datetime_result:
            details['start_time'], details['end_time'] = datetime_result

        return details

    def _parse_datetime(self, date_str: str, context: Dict[str, Any] = None) -> Optional[Tuple[datetime, datetime]]:
        """Enhanced datetime parsing with context awareness"""
        try:
            now = datetime.now(tzlocal())
            date_str = date_str.lower().strip()
            start_time = None
            duration = None

            # Handle relative dates
            if 'tomorrow' in date_str:
                base_date = now + timedelta(days=1)
            elif 'next week' in date_str:
                base_date = now + timedelta(weeks=1)
            elif 'next' in date_str:
                day_match = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', date_str)
                if day_match:
                    target_day = list(calendar.day_name).index(day_match.group(1).title())
                    days_ahead = target_day - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    base_date = now + timedelta(days=days_ahead)
            else:
                try:
                    base_date = parse_date(date_str, fuzzy=True)
                except ValueError:
                    base_date = now

            # Parse time of day
            time_match = None
            for time_desc, (hour, minute) in self.TIME_OF_DAY.items():
                if time_desc in date_str:
                    time_match = (hour, minute)
                    break

            # Parse specific time
            time_pattern = r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
            specific_time = re.search(time_pattern, date_str)
            
            if specific_time:
                hour = int(specific_time.group(1))
                minute = int(specific_time.group(2) or 0)
                meridiem = specific_time.group(3)
                
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                
                start_time = base_date.replace(hour=hour, minute=minute)
            elif time_match:
                start_time = base_date.replace(hour=time_match[0], minute=time_match[1])
            else:
                # Default to morning if no time specified
                start_time = base_date.replace(hour=9, minute=0)

            # Parse duration
            duration_match = re.search(r'for\s+(\d+)\s*(?:hour|hr|h)s?', date_str)
            if duration_match:
                duration = int(duration_match.group(1))
            else:
                # Try to determine default duration from event type
                for event_type, default_duration in self.DEFAULT_DURATIONS.items():
                    if event_type in date_str:
                        duration = default_duration
                        break
                if not duration:
                    duration = 1  # Default 1 hour

            end_time = start_time + timedelta(hours=duration)

            # Ensure timezone awareness
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=tzlocal())
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=tzlocal())

            return start_time, end_time

        except Exception as e:
            self.logger.error(f"Error parsing datetime: {str(e)}")
            return None

    def _handle_add(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add/schedule commands"""
        try:
            details = self._parse_event_details(input_text)
            
            if not details.get('start_time'):
                return {
                    "success": False,
                    "response": "I couldn't determine when this event should be scheduled. When would you like it?"
                }

            success = self.add_event(**details)
            
            if success:
                response = f"I've scheduled '{details['title']}' for {details['start_time'].strftime('%A, %B %d at %I:%M %p')}"
                if details.get('location'):
                    response += f" at {details['location']}"
                return {"success": True, "response": response}
            
            return {
                "success": False,
                "response": "I wasn't able to add that event. Would you like to try again?"
            }

        except Exception as e:
            self.logger.error(f"Error in calendar add: {str(e)}")
            return {
                "success": False,
                "response": "I had trouble understanding that. Could you rephrase it?"
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

    def schedule_notifications(self, event_id: str, event_details: Dict[str, Any], 
                            reminder_times: List[int] = None) -> None:
        """Schedule notifications for an event"""
        if not self.notification_module:
            return

        reminder_times = reminder_times or self.default_reminder_times
        start_time = event_details['start']

        for minutes in reminder_times:
            notify_time = start_time - timedelta(minutes=minutes)
            if notify_time > datetime.now():
                timer = Timer(
                    (notify_time - datetime.now()).total_seconds(),
                    self._send_event_notification,
                    args=[event_id, event_details, minutes]
                )
                self.notification_timers[f"{event_id}_{minutes}"] = timer
                timer.start()

    def _send_event_notification(self, event_id: str, event_details: Dict[str, Any], 
                               minutes_before: int) -> None:
        """Send notification for upcoming event"""
        if not self.notification_module:
            return

        title = f"Calendar Event: {event_details['title']}"
        message = f"Event starts in {minutes_before} minutes"
        if event_details.get('location'):
            message += f" at {event_details['location']}"

        self.notification_module.queue_notification(
            title=title,
            message=message,
            timeout=30  # Show notification for 30 seconds
        )

    def cleanup_notifications(self, event_id: str) -> None:
        """Cancel pending notifications for an event"""
        for timer_id in list(self.notification_timers.keys()):
            if timer_id.startswith(f"{event_id}_"):
                timer = self.notification_timers.pop(timer_id)
                timer.cancel()

    def shutdown(self) -> None:
        """Clean shutdown of calendar module"""
        try:
            # Close memory system connection
            if hasattr(self, 'memory'):
                self.memory.close()
            
            # Clear credentials and service
            if hasattr(self, 'service'):
                self.service = None
            if hasattr(self, 'creds'):
                self.creds = None
                
            # Clear initialized state
            self.initialized = False
            
            self.logger.info("Calendar module shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during calendar module shutdown: {str(e)}")

    def sync_calendar(self, force: bool = False) -> Dict[str, Any]:
        """Sync calendar with enhanced error handling and conflict resolution"""
        if not self.initialized:
            return {'success': False, 'error': 'Calendar not initialized'}
            
        try:
            self.sync_state['sync_in_progress'] = True
            
            # Get local and remote events
            local_events = self.memory.get_calendar_events()
            remote_events = self._fetch_remote_events()
            
            # Detect conflicts
            conflicts = self._detect_conflicts(local_events, remote_events)
            if conflicts:
                self._resolve_conflicts(conflicts)
                
            # Sync changes
            changes = self._sync_changes(local_events, remote_events)
            
            # Update sync state
            self.sync_state.update({
                'last_sync': datetime.now(),
                'pending_changes': [],
                'conflicts': conflicts,
                'sync_in_progress': False,
                'last_status': 'success'
            })
            
            return {
                'success': True,
                'changes': changes,
                'conflicts_resolved': len(conflicts)
            }
            
        except Exception as e:
            self.sync_state.update({
                'sync_in_progress': False,
                'last_status': 'error',
                'last_error': str(e)
            })
            self.logger.error(f"Sync failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _detect_conflicts(self, local: List[Dict], remote: List[Dict]) -> List[Dict]:
        """Detect conflicts between local and remote events"""
        conflicts = []
        for local_event in local:
            remote_event = next(
                (e for e in remote if e['id'] == local_event['id']), 
                None
            )
            if remote_event and self._is_conflict(local_event, remote_event):
                conflicts.append({
                    'local': local_event,
                    'remote': remote_event,
                    'type': 'update_conflict'
                })
        return conflicts

    def _resolve_conflicts(self, conflicts: List[Dict]) -> None:
        """Resolve conflicts based on configuration"""
        for conflict in conflicts:
            if self.sync_config['conflict_resolution'] == 'newer_wins':
                local_modified = parse_date(conflict['local']['modified'])
                remote_modified = parse_date(conflict['remote']['modified'])
                
                if local_modified > remote_modified:
                    self._update_remote_event(conflict['local'])
                else:
                    self._update_local_event(conflict['remote'])

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update event with improved error handling and sync"""
        try:
            # Validate updates
            if not self._validate_updates(updates):
                return {
                    'success': False,
                    'error': 'Invalid update data'
                }
                
            # Get current event
            current = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Apply updates
            updated = self._apply_updates(current, updates)
            
            # Update remote
            result = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=updated,
                sendUpdates='all'
            ).execute()
            
            # Update local cache
            self.memory.update_calendar_event(event_id, updated)
            
            # Handle notifications
            self._handle_notification_updates(event_id, updated)
            
            return {
                'success': True,
                'event': result
            }
            
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_notification_updates(self, event_id: str, event_data: Dict) -> None:
        """Update notifications for modified events"""
        # Clear existing notifications
        self.cleanup_notifications(event_id)
        
        # Schedule new notifications
        if event_data.get('reminders', {}).get('useDefault', True):
            reminder_times = self.default_reminder_times
        else:
            reminder_times = [
                r['minutes'] 
                for r in event_data['reminders'].get('overrides', [])
            ]
            
        self.schedule_notifications(
            event_id,
            event_data,
            reminder_times
        )