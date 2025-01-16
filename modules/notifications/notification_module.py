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

class NotificationModule(ModuleInterface):
    """Handles system notifications and alerts for Rowan"""

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.initialized = False
        self.notification_queue = queue.Queue()
        self.notification_thread = None
        self.running = False
        self.notifier = None
        
        # Initialize platform-specific notifier
        self._setup_platform_notifier()

    def _setup_platform_notifier(self):
        """Setup the appropriate notification system based on platform"""
        system = platform.system()
        
        try:
            if system == "Windows" and WINDOWS_NOTIFICATIONS:
                self.notifier = ToastNotifier()
                self.initialized = True
            elif system == "Linux" and LINUX_NOTIFICATIONS:
                notify2.init("Rowan")
                self.notifier = notify2
                self.initialized = True
            elif system == "Darwin":  # macOS
                self.initialized = True  # Uses osascript directly
            else:
                self.logger.warning(f"No notification system available for {system}")
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {str(e)}")

    def send_notification(self, title: str, message: str, timeout: int = 10) -> bool:
        """Send a notification using the appropriate platform method"""
        if not self.initialized:
            self.logger.error("Notification system not initialized")
            return False

        try:
            system = platform.system()
            if system == "Windows" and WINDOWS_NOTIFICATIONS:
                self.notifier.show_toast(title, message, duration=timeout, threaded=True)
            elif system == "Linux" and LINUX_NOTIFICATIONS:
                notification = self.notifier.Notification(title, message)
                notification.timeout = timeout * 1000  # Convert to milliseconds
                notification.show()
            elif system == "Darwin":
                self._send_macos_notification(title, message)
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