"""
Rowan Assistant - An AI assistant framework
Copyright (C) 2025 Rowan Development Team

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or any later version.
"""

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

class RowanApplication:
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
        self.window_hidden = False
        atexit.register(self.cleanup)

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
        self.window_hidden = False
        self.icon.stop()
        self.gui.deiconify()
        
    def hide_window(self):
        """Hide main window to system tray"""
        self.window_hidden = True
        self.gui.withdraw()
        threading.Thread(target=self.icon.run, daemon=True).start()
        
    def exit_application(self):
        """Exit application from tray"""
        self.window_closed = True
        self.icon.stop()
        self.cleanup()
        sys.exit(0)

    def on_window_closing(self):
        """Handler for window close button"""
        self.hide_window()
        return

    def cleanup(self):
        """Clean up threads and resources"""
        if self.window_closed:  # Prevent multiple cleanups
            if self.icon:
                self.icon.stop()
            if self.gui and self.gui.winfo_exists():
                self.gui.quit()
                self.gui.destroy()
        
        self.should_run = False
        
        # Handle threads
        for thread in self.threads:
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        
        # Cleanup modules and assistant
        if self.module_manager:
            self.module_manager.shutdown_all()
        
        if self.assistant:
            self.assistant.close()

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
                })
            ]
            
            # Load each module with its specific config
            for module_name, module_config in modules_to_load:
                config = base_config.copy()
                config.update(module_config)
                
                if not self.module_manager.load_module(module_name, config):
                    self.logger.error(f"Failed to load module: {module_name}")
                    raise Exception(f"Module initialization failed: {module_name}")
            
            # Initialize GUI with reference to assistant after modules are loaded
            self.gui = RowanGUI(rowan_assistant=self.assistant)
            
            # Add window close protocol
            self.create_tray_icon()
            self.gui.protocol("WM_DELETE_WINDOW", self.on_window_closing)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Rowan: {str(e)}")
            print(f"Failed to initialize Rowan: {str(e)}")
            return False

    def start(self):
        if self.initialize():
            try:
                # Start GUI main loop
                self.gui.mainloop()
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                print(f"Error in main loop: {str(e)}")
            finally:
                if not self.window_closed:
                    self.cleanup()
        else:
            print("Failed to start Rowan due to initialization error")

if __name__ == "__main__":
    app = RowanApplication()
    app.start()