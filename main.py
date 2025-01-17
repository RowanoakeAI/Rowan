"""
Rowan Assistant - An AI assistant framework
"""

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
import pystray
from PIL import Image
from pynput import keyboard  # Add this import

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from core.rowan_assistant import RowanAssistant
from core.personal_memory import InteractionContext, InteractionSource
from core.module_manager import ModuleManager
from modules.discord import DiscordModule
from modules.gui import RowanGUI
from modules.skills.calendar_skill import GoogleCalendarSkill
from config.discord_config import DiscordConfig
from config.api_config import APIConfig

class RowanApplication:
    # Add exit status constants
    EXIT_SUCCESS = 0
    EXIT_INIT_FAILURE = 1
    EXIT_RUNTIME_ERROR = 2
    EXIT_KEYBOARD_INTERRUPT = 3

    def __init__(self):
        self.assistant = None
        self.gui = None
        self.event_queue = Queue()
        self.should_run = True
        self.module_manager = None
        self.logger = logging.getLogger(__name__)
        self.threads = []
        self.window_closed = False
        self.icon = None
        self.icon_thread = None
        self.window_hidden = False
        self._shutting_down = False
        self._icon_ready = threading.Event()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.cleanup)

        self.hotkey = None

    def create_tray_icon(self):
        """Create system tray icon with menu"""
        icon_path = Path(__file__).parent / "assets" / "rowan.png"
        self.icon_image = Image.open(icon_path)  # Store reference
        menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Hide", self.hide_window),
            pystray.MenuItem("Exit", self.exit_application)
        )
        self.icon = pystray.Icon("Rowan", self.icon_image, "Rowan Assistant", menu)
        
    def show_window(self):
        """Show main window"""
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
        """Hide main window to system tray"""
        if self.gui:
            self.window_hidden = True
            self.gui.withdraw()
            
            # Create new tray icon thread if needed
            if not self.icon_thread or not self.icon_thread.is_alive():
                self.create_tray_icon()
                self.icon_thread = threading.Thread(target=self.icon.run, daemon=True)
                self.icon_thread.start()

    def exit_application(self):
        """Exit application from tray"""
        if not self._shutting_down:
            self.window_closed = True
            if self.icon:
                self.icon.stop()
            self.cleanup()
            sys.exit(0)

    def on_window_closing(self):
        """Handler for window close button"""
        self.hide_window()
        return

    def _signal_handler(self, signum, frame):
        """Handle termination signals gracefully"""
        if not self._shutting_down:
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.exit_application()

    def cleanup(self):
        """Clean up threads and resources"""
        if self._shutting_down:
            return
            
        self._shutting_down = True
        self.logger.info("Starting cleanup process...")

        try:
            # Stop hotkey listener first
            if self.hotkey:
                try:
                    self.hotkey.stop()
                    self.logger.info("Hotkey listener stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping hotkey listener: {e}")

            # Stop tray icon
            if self.icon:
                try:
                    if self.icon_thread and self.icon_thread.is_alive():
                        self.icon.stop()
                        self.icon_thread.join(timeout=1.0)
                except Exception as e:
                    self.logger.error(f"Error stopping tray icon: {e}")

            if self.window_closed:
                if self.icon:
                    self.icon.stop()
                if self.gui and self.gui.winfo_exists():
                    self.gui.quit()
                    self.gui.destroy()
            
            self.should_run = False
            
            # Handle threads with timeout
            for thread in self.threads:
                if thread and thread.is_alive():
                    thread.join(timeout=2.0)
            
            # Cleanup modules and assistant
            if self.module_manager:
                try:
                    self.module_manager.shutdown_all()
                except Exception as e:
                    self.logger.error(f"Error during module shutdown: {e}")
            
            if self.assistant:
                try:
                    self.assistant.close()
                except Exception as e:
                    self.logger.error(f"Error closing assistant: {e}")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            self.logger.info("Cleanup completed")

    @contextmanager
    def managed_thread(self, target, *args, **kwargs):
        """Context manager for thread lifecycle management"""
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        self.threads.append(thread)
        thread.start()
        try:
            yield thread
        finally:
            if thread.is_alive():
                thread.join(timeout=0.5)
            self.threads.remove(thread)

    def initialize(self):
        try:
            # Initialize event loop for main thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize Rowan Assistant first
            self.assistant = RowanAssistant(model_name="rowdis")
            
            # Set up module manager with base configuration
            self.module_manager = ModuleManager()
            
            # Prepare base config for modules
            base_config = {
                "rowan": self.assistant,
                "memory": self.assistant.memory,
                "debug": True
            }
            
            # Load core modules in specific order with configuration
            modules_to_load = [
                ("conversation", {}),
                ("calendar_skill", {}),
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
            
            # Load each module with proper error handling and async support
            for module_name, module_config in modules_to_load:
                config = base_config.copy()
                config.update(module_config)
                
                try:
                    # Run module loading in event loop if needed
                    if module_name == "api":
                        loop.run_until_complete(self._async_load_module(module_name, config))
                    else:
                        if not self.module_manager.load_module(module_name, config):
                            self.logger.error(f"Failed to load module: {module_name}")
                            raise Exception(f"Module initialization failed: {module_name}")
                except Exception as e:
                    self.logger.error(f"Error loading module {module_name}: {str(e)}")
                    raise
            
            # Initialize GUI with reference to assistant after modules are loaded
            self.gui = RowanGUI(rowan_assistant=self.assistant)
            
            # Setup hotkey before GUI mainloop
            try:
                self.hotkey = keyboard.GlobalHotKeys({
                    '<ctrl>+<alt>+r': lambda: self.gui.after(0, self.toggle_window)
                })
                self.hotkey.start()  # Start listening immediately
                self.logger.info("Global hotkey registered successfully")
            except Exception as e:
                self.logger.error(f"Failed to register global hotkey: {e}")

            # Add window close protocol
            self.create_tray_icon()
            self.gui.protocol("WM_DELETE_WINDOW", self.hide_window)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Rowan: {str(e)}")
            print(f"Failed to initialize Rowan: {str(e)}")
            return False

    async def _async_load_module(self, module_name: str, config: dict) -> bool:
        """Helper method to load async modules"""
        if not self.module_manager.load_module(module_name, config):
            self.logger.error(f"Failed to load module: {module_name}")
            raise Exception(f"Module initialization failed: {module_name}")
        return True

    def start(self):
        """Start the application with improved error handling"""
        try:
            if not self.initialize():
                self.logger.error("Failed to start Rowan due to initialization error")
                return False
                
            # Start GUI main loop with exception handling
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
        """Handle application shutdown with status"""
        try:
            self.logger.info(f"Shutting down with status code: {status_code}")
            self.cleanup()
        finally:
            sys.exit(status_code)

    def toggle_window(self):
        """Toggle window visibility safely"""
        if self._shutting_down:
            return
            
        try:
            if self.window_hidden:
                self.show_window()
            else:
                self.hide_window()
        except Exception as e:
            self.logger.error(f"Error toggling window: {e}")

if __name__ == "__main__":
    app = RowanApplication()
    try:
        success = app.start()
        if not success:
            app.shutdown(app.EXIT_INIT_FAILURE)
        else:
            app.shutdown(app.EXIT_SUCCESS)
    except KeyboardInterrupt:
        app.logger.info("Received keyboard interrupt")
        app.shutdown(app.EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        app.logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        app.shutdown(app.EXIT_RUNTIME_ERROR)