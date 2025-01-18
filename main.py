"""
Rowan Assistant - An AI assistant framework
"""

# Standard library imports
import signal
import sys
import asyncio
from pathlib import Path
import threading
from queue import Queue, Empty
from typing import List, Optional
import time
from contextlib import contextmanager
import logging
import atexit
import tkinter as tk

# Third-party imports
import pystray
from PIL import Image
from pynput import keyboard

# Local application imports
from core.rowan_assistant import RowanAssistant
from core.module_manager import ModuleManager
from modules.gui.gui_module import RowanGUI
from config.discord_config import DiscordConfig
from config.api_config import APIConfig

class RowanApplication:
    # Exit status constants
    EXIT_SUCCESS = 0
    EXIT_INIT_FAILURE = 1 
    EXIT_RUNTIME_ERROR = 2
    EXIT_KEYBOARD_INTERRUPT = 3

    def __init__(self):
        # Core components
        self.assistant = None
        self.gui = None
        self.module_manager = None
        
        # Threading and events
        self.event_queue = Queue()
        self.threads: List[threading.Thread] = []
        self.should_run = True
        
        # Window management
        self.window_closed = False
        self.window_hidden = False
        self.icon = None
        self.icon_thread = None
        self._icon_ready = threading.Event()
        self._shutting_down = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.cleanup)

        self.hotkey = None

    def initialize(self) -> bool:
        try:
            # Initialize event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize core components
            self.assistant = RowanAssistant(model_name="rowdis")
            self.module_manager = ModuleManager()
            
            # Base configuration for modules
            base_config = {
                "rowan": self.assistant,
                "memory": self.assistant.memory,
                "debug": True
            }
            
            # Add notifications to core modules to load
            modules_to_load = [
                ("conversation", {}),
                ("calendar_skill", {}),
                ("notifications", {}),  # Add notifications module
                ("discord", {
                    "token": DiscordConfig.DISCORD_TOKEN,
                    "rowan": self.assistant,
                    "memory": self.assistant.memory
                }),
                ("api", {
                    "api_port": APIConfig.API_PORT,
                    "rowan": self.assistant
                })
            ]
            
            # Load modules
            for module_name, module_config in modules_to_load:
                config = base_config.copy()
                config.update(module_config)
                try:
                    if module_name == "api":
                        loop.run_until_complete(self._async_load_module(module_name, config))
                    else:
                        if not self.module_manager.load_module(module_name, config):
                            raise Exception(f"Module initialization failed: {module_name}")
                except Exception as e:
                    self.logger.error(f"Error loading module {module_name}: {str(e)}")
                    raise

            # Initialize GUI but keep it hidden
            self.gui = RowanGUI(rowan_assistant=self.assistant)
            self.window_hidden = True
            self.gui.withdraw()
            
            # Create tray icon
            self.create_tray_icon()
            self.gui.protocol("WM_DELETE_WINDOW", self.hide_window)

            # Send startup notification
            notifications = self.module_manager.get_module("notifications")
            if notifications:
                notifications.send_notification(
                    "Rowan Assistant",
                    "Rowan has started and is running in the background",
                    timeout=5
                )

            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Rowan: {str(e)}")
            return False

    def cleanup(self):
        """Enhanced cleanup with better error handling"""
        if self._shutting_down:
            return
            
        self._shutting_down = True
        self.logger.info("Starting cleanup process...")

        try:
            # Stop hotkey listener first
            if self.hotkey:
                try:
                    self.hotkey.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping hotkey listener: {e}")

            # Clean up modules and assistant
            if self.module_manager:
                try:
                    self.module_manager.shutdown_all()
                except Exception as e:
                    self.logger.error(f"Error shutting down modules: {e}")
                    
            if self.assistant:
                try:
                    self.assistant.close()
                except Exception as e:
                    self.logger.error(f"Error closing assistant: {e}")

            # Stop remaining threads
            for thread in self.threads[:]:
                try:
                    if thread and thread.is_alive():
                        thread.join(timeout=2.0)
                    self.threads.remove(thread)
                except Exception as e:
                    self.logger.error(f"Error stopping thread: {e}")

        except Exception as e:
            self.logger.error(f"Critical error during cleanup: {e}")
        finally:
            self.logger.info("Cleanup completed")

    @contextmanager
    def managed_thread(self, target, *args, **kwargs):
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        self.threads.append(thread)
        thread.start()
        try:
            yield thread
        finally:
            if thread.is_alive():
                thread.join(timeout=0.5)
            self.threads.remove(thread)

    async def _async_load_module(self, module_name: str, config: dict) -> bool:
        if not self.module_manager.load_module(module_name, config):
            self.logger.error(f"Failed to load module: {module_name}")
            raise Exception(f"Module initialization failed: {module_name}")
        return True

    def create_tray_icon(self):
        icon_path = Path(__file__).parent / "assets" / "rowan.png"
        self.icon_image = Image.open(icon_path)
        menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Hide", self.hide_window),
            pystray.MenuItem("Exit", self.exit_application)
        )
        self.icon = pystray.Icon("Rowan", self.icon_image, "Rowan Assistant", menu)

    def show_window(self):
        if self.icon and self.icon_thread and self.icon_thread.is_alive():
            self.icon.stop()
            self.icon_thread.join()
            self.icon_thread = None
            
        if self.gui:
            self.window_hidden = False
            self.gui.deiconify()
            self.gui.lift()
            self.gui.focus_force()

    def hide_window(self):
        if self.gui:
            self.window_hidden = True
            self.gui.withdraw()
            
            if not self.icon_thread or not self.icon_thread.is_alive():
                self.create_tray_icon()
                self.icon_thread = threading.Thread(target=self.icon.run, daemon=True)
                self.icon_thread.start()

    def toggle_window(self):
        if self._shutting_down:
            return
            
        try:
            if self.window_hidden:
                self.show_window()
            else:
                self.hide_window()
        except Exception as e:
            self.logger.error(f"Error toggling window: {e}")

    def exit_application(self):
        """Safely exit the application from the system tray"""
        if not self._shutting_down:
            try:
                self.window_closed = True
                # Stop processing any new events
                self.should_run = False
                
                # Hide window first to prevent UI issues
                if self.gui and not self.window_hidden:
                    self.gui.withdraw()
                
                # Stop icon first to prevent callback issues
                if self.icon:
                    try:
                        self.icon.stop()
                        if self.icon_thread and self.icon_thread.is_alive():
                            self.icon_thread.join(timeout=1.0)
                    except Exception as e:
                        self.logger.error(f"Error stopping tray icon: {e}")
                
                # Run cleanup operations
                self.cleanup()
                
                # Exit main thread last
                self.logger.info("Exiting application...")
                if self.gui and self.gui.winfo_exists():
                    self.gui.after(100, lambda: self.gui.quit())
                else:
                    sys.exit(self.EXIT_SUCCESS)
                    
            except Exception as e:
                self.logger.error(f"Error during exit: {e}")
                sys.exit(self.EXIT_RUNTIME_ERROR)

    def _signal_handler(self, signum, frame):
        if not self._shutting_down:
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.exit_application()

    def start(self):
        try:
            if not self.initialize():
                self.logger.error("Failed to start Rowan due to initialization error")
                return False
                
            # Start GUI main loop
            if self.gui:
                try:
                    self.gui.mainloop()
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt in main loop")
                    return False
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                    return False

            return True
                
        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}", exc_info=True)
            return False
        finally:
            if not self.window_closed:
                self.cleanup()

    def shutdown(self, status_code: int) -> None:
        """Gracefully shutdown the application with the given status code"""
        try:
            self.logger.info(f"Shutting down with status code: {status_code}")
            self.cleanup()
            # Let the GUI close properly if it exists
            if self.gui and self.gui.winfo_exists():
                self.gui.quit()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            # Use os._exit to ensure clean exit
            import os
            os._exit(status_code)

if __name__ == "__main__":
    app = RowanApplication()
    status_code = app.EXIT_SUCCESS
    
    try:
        success = app.start()
        if not success:
            status_code = app.EXIT_INIT_FAILURE
    except KeyboardInterrupt:
        app.logger.info("Received keyboard interrupt")
        status_code = app.EXIT_KEYBOARD_INTERRUPT
    except Exception as e:
        app.logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        status_code = app.EXIT_RUNTIME_ERROR
    finally:
        app.shutdown(status_code)