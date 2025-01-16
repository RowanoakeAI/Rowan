import sys
import asyncio
from pathlib import Path
import keyboard
import threading
from queue import Queue
from typing import List, Optional
import time

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

    def start_event_loop(self):
        """Start asyncio event loop in background thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

    def init_modules(self):
        """Initialize all enabled modules"""
        # First start event loop for async operations
        self.start_event_loop()
        
        # Create base config with shared dependencies
        base_config = {
            "rowan": self.rowan,
            "loop": self.loop
        }

        # Load Discord module with config
        if self.module_manager.load_module("discord", base_config):
            discord_module = self.module_manager.get_module("discord")
            self.active_modules.append(discord_module)
            future = asyncio.run_coroutine_threadsafe(
                discord_module.client.start(discord_module.token),
                self.loop
            )

        # Load Calendar module
        if self.module_manager.load_module("calendar", base_config):
            calendar_module = self.module_manager.get_module("calendar")
            self.active_modules.append(calendar_module)

        # Initialize GUI 
        self.gui = RowanGUI(self.rowan)
        self.gui.protocol("WM_DELETE_WINDOW", self._on_gui_close)
        
        # Set up hotkey
        keyboard.add_hotkey('ctrl+alt+r', self.handle_hotkey)

    def _on_gui_close(self):
        """Handle GUI window closing"""
        self.gui.withdraw()  # Hide window instead of destroying

    # Update RowanApplication.handle_hotkey() method:
    def handle_hotkey(self):
        """Handle global hotkey press"""
        try:
            if self.gui and not self.gui.winfo_viewable():
                self.gui.deiconify()  # Show window if hidden
            else:
                user_input = input("\nRowan Hotkey Active - Enter message ('exit' to quit): ").strip()
                if user_input.lower() not in ['exit', 'quit']:
                    response = self.rowan.chat(
                        user_input, 
                        source=InteractionSource.LOCAL
                    )
                    print(f"\nRowan: {response}")
                else:
                    self.message_queue.put(user_input)
        except Exception as e:
            print(f"Error handling hotkey: {e}")

    async def process_messages(self):
        """Process messages from queue"""
        while self.running:
            if not self.message_queue.empty():
                message = self.message_queue.get()
                if message.lower() in ['exit', 'quit']:
                    self.shutdown()
                    return
                response = self.rowan.chat(message)
                print(f"\nRowan: {response}")
            await asyncio.sleep(0.1)

    def start(self):
        """Start the application"""
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Start event loop first
        self.start_event_loop()
        self.init_modules()

        try:
            if self.gui:
                self.gui.mainloop()
            
            # Keep running even after GUI closes
            while self.running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nReceived shutdown signal...")
        finally:
            self.shutdown()
            
    def shutdown(self):
        """Clean shutdown of all components"""
        self.running = False
        
        # Stop event loop
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join()
        
        # Shutdown active modules
        for module in self.active_modules:
            try:
                module.shutdown()
            except Exception as e:
                print(f"Error shutting down module: {e}")
                
        # Clean up GUI if it exists
        if self.gui:
            self.gui.destroy()
            
        print("Shutdown complete")

def main():
    app = RowanApplication()
    app.start()

if __name__ == "__main__":
    main()