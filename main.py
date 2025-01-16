"""
Rowan Assistant - An AI assistant framework
Copyright (C) [year]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import sys
import asyncio
from pathlib import Path
import threading
from queue import Queue, Empty
from typing import List, Optional
import time
from contextlib import contextmanager

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

class RowanApplication:
    def __init__(self):
        self.assistant = None
        self.gui = None
        self.event_queue = Queue()
        self.should_run = True

    def initialize(self):
        try:
            # Initialize Rowan Assistant first
            self.assistant = RowanAssistant(model_name="rowdis")
            
            # Initialize GUI with reference to assistant
            self.gui = RowanGUI(rowan_assistant=self.assistant)
            
            # Set up module manager
            self.module_manager = ModuleManager()
            
            # Load core modules in specific order
            self.module_manager.load_module("conversation")
            self.module_manager.load_module("calendar_skill")
            self.module_manager.load_module("discord")
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize Rowan: {str(e)}")
            return False

    def start(self):
        if self.initialize():
            try:
                # Start GUI main loop
                self.gui.mainloop()
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
        else:
            print("Failed to start Rowan due to initialization error")

if __name__ == "__main__":
    app = RowanApplication()
    app.start()