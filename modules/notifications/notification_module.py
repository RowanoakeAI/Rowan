from typing import Dict, Any, Optional, List
from datetime import datetime
import platform
import threading
import queue
from pathlib import Path
from core.module_manager import ModuleInterface
from utils.logger import setup_logger
import os
import subprocess

# Platform-specific imports with error handling
WINDOWS_NOTIFICATIONS = False
LINUX_NOTIFICATIONS = False
MACOS_NOTIFICATIONS = True if platform.system() == "Darwin" else False

try:
    from win10toast import ToastNotifier
    WINDOWS_NOTIFICATIONS = True
except ImportError:
    pass

try:
    import notify2
    LINUX_NOTIFICATIONS = True
except ImportError:
    pass

class NotificationsModule(ModuleInterface):
    """Handles system notifications and alerts for Rowan"""

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.initialized = False
        self.notification_queue = queue.Queue()
        self.notification_thread = None
        self.running = False
        self.notifier = None
        self.notification_history = []
        self.max_history = 100

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the notification module with config"""
        try:
            self.max_history = config.get('max_history', 100)
            success = self._setup_platform_notifier()
            if success:
                self.start()
                self.initialized = True
                self.logger.info("Notification module initialized successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize notification module: {str(e)}")
            return False

    def _setup_platform_notifier(self) -> bool:
        """Setup the appropriate notification system based on platform"""
        system = platform.system()
        
        try:
            if system == "Windows":
                if WINDOWS_NOTIFICATIONS:
                    self.notifier = ToastNotifier()
                    # Verify initialization succeeded
                    if not self.notifier:
                        raise RuntimeError("Failed to initialize ToastNotifier")
                    return True
                else:
                    self.logger.warning("Windows notifications not available - win10toast not installed")
            elif system == "Linux":
                if LINUX_NOTIFICATIONS:
                    notify2.init("Rowan")
                    self.notifier = notify2
                    return True
                else:
                    self.logger.warning("Linux notifications not available - notify2 not installed")
            elif system == "Darwin":
                # For macOS, we don't need a notifier object since we use osascript
                self.notifier = True
                return True
            else:
                self.logger.warning(f"No notification system available for {system}")
            
            # Fallback to no notifications
            self.notifier = None
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {str(e)}")
            self.notifier = None
            return False

    def send_notification(self, title: str, message: str, timeout: int = 10) -> bool:
        """Send a notification using the appropriate platform method"""
        if not self.initialized or not self.notifier:
            self.logger.error("Notification system not initialized")
            return False

        try:
            system = platform.system()
            if system == "Windows" and WINDOWS_NOTIFICATIONS and isinstance(self.notifier, ToastNotifier):
                self.notifier.show_toast(title, message, duration=timeout, threaded=True)
            elif system == "Linux" and LINUX_NOTIFICATIONS and self.notifier == notify2:
                notification = notify2.Notification(title, message)
                notification.timeout = timeout * 1000  # Convert to milliseconds
                notification.show()
            elif system == "Darwin" and self.notifier:
                self._send_macos_notification(title, message)
            else:
                self.logger.warning(f"No notification system available for {system}")
                return False
            
            # Add to history
            self.notification_history.append({
                'title': title,
                'message': message,
                'timestamp': datetime.now()
            })
            
            # Trim history if needed
            while len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            return False

    def _send_macos_notification(self, title: str, message: str):
        """Send notification on macOS using osascript"""
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(['osascript', '-e', script], capture_output=True)

    def start(self):
        """Start the notification module"""
        self.running = True
        self.notification_thread = threading.Thread(target=self._process_queue)
        self.notification_thread.daemon = True
        self.notification_thread.start()

    def stop(self):
        """Stop the notification module"""
        self.running = False
        if self.notification_thread:
            self.notification_thread.join()

    def _process_queue(self):
        """Process notifications in the queue"""
        while self.running:
            try:
                notification = self.notification_queue.get(timeout=1)
                self.send_notification(
                    notification.get('title', 'Notification'),
                    notification.get('message', ''),
                    notification.get('timeout', 10)
                )
                self.notification_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing notification: {str(e)}")

    def queue_notification(self, title: str, message: str, timeout: int = 10) -> bool:
        """Add notification to queue"""
        try:
            notification = {
                'title': title,
                'message': message,
                'timeout': timeout,
                'timestamp': datetime.now()
            }
            self.notification_queue.put(notification)
            self.notification_history.append(notification)
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue notification: {str(e)}")
            return False

    def get_notification_history(self) -> List[Dict[str, Any]]:
        """Return notification history"""
        return self.notification_history

    def process(self, input_data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process notification requests"""
        if isinstance(input_data, dict):
            success = self.queue_notification(
                input_data.get('title', 'Notification'),
                input_data.get('message', ''),
                input_data.get('timeout', 10)
            )
            return {'success': success}
        return {'success': False, 'error': 'Invalid input data'}