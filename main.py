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
        self.rowan = RowanAssistant()
        self.message_queue = Queue()
        self.running = True
        self.module_manager = ModuleManager()
        self.active_modules = []
        self.loop = None
        self.loop_thread = None
        self.gui = None
        self._shutdown_lock = threading.Lock()

    @contextmanager
    def _event_loop_context(self):
        """Context manager for event loop lifecycle"""
        try:
            self.start_event_loop()
            yield
        finally:
            self.cleanup_event_loop()

    def start_event_loop(self):
        """Start asyncio event loop in background thread"""
        def run_loop():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()
            except Exception as e:
                print(f"Event loop error: {e}")
            finally:
                self.loop.close()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

    def cleanup_event_loop(self):
        """Clean up event loop resources"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=5)
            
        if self.loop and not self.loop.is_closed():
            self.loop.close()
            
        self.loop = None
        self.loop_thread = None

    def initialize_modules(self):
        """Initialize and start enabled modules"""
        try:
            # Load core modules
            for module_name in ['conversation', 'calendar_skill']:
                if self.module_manager.load_module(module_name):
                    self.active_modules.append(module_name)

            # Initialize GUI with error handling
            try:
                self.gui = RowanGUI(self.rowan)
            except Exception as e:
                print(f"GUI initialization error: {e}")
                self.gui = None

            # Start Discord module if configured
            if 'discord' in self.module_manager.modules:
                discord_module = self.module_manager.get_module('discord')
                if self.loop and discord_module:
                    asyncio.run_coroutine_threadsafe(
                        discord_module.start(), self.loop
                    )

        except Exception as e:
            print(f"Error initializing modules: {e}")
            self.stop()

    def process_queue(self):
        """Process messages from queue"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=0.1)
                response = self.rowan.chat(
                    message,
                    context_type=InteractionContext.CASUAL,
                    source=InteractionSource.CONSOLE
                )
                print(f"Rowan: {response}")
            except Empty:  # Changed from Queue.Empty to Empty
                continue
            except Exception as e:
                print(f"Error processing message: {str(e)}")

    def start(self):
        """Start the application"""
        try:
            print("Starting Rowan Assistant...")
            with self._event_loop_context():
                self.initialize_modules()
                
                # Start message processing thread
                process_thread = threading.Thread(
                    target=self.process_queue,
                    daemon=True
                )
                process_thread.start()
                
                if self.gui:
                    self.gui.mainloop()
                else:
                    self.run()

        except Exception as e:
            print(f"Error starting application: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the application with proper cleanup"""
        with self._shutdown_lock:
            if not self.running:
                return
                
            print("\nShutting down...")
            self.running = False
            
            # Stop all active modules
            for module_name in self.active_modules:
                try:
                    self.module_manager.shutdown_module(module_name)
                except Exception as e:
                    print(f"Error shutting down {module_name}: {e}")

            # Close Rowan and cleanup
            try:
                self.rowan.close()
            except Exception as e:
                print(f"Error closing Rowan: {e}")

            # Exit cleanly
            sys.exit(0)

    def run(self):
        """Run in console mode"""
        print("Rowan Assistant initialized. Type 'exit' to quit.")
        try:
            while self.running:
                message = input("You: ").strip()
                if message.lower() in ['exit', 'quit']:
                    break
                self.message_queue.put(message)
        except KeyboardInterrupt:
            print("\nExiting gracefully...")
        finally:
            self.stop()

    def __del__(self):
        """Ensure proper cleanup on deletion"""
        if self.running:
            self.stop()

if __name__ == "__main__":
    app = RowanApplication()
    app.start()