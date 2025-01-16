from typing import Dict, Any
import re
from datetime import datetime
from .personal_memory import MemorySystem
from ..config.memory_config import MemoryConfig
from ..config.settings import Settings
from .module_manager import ModuleManager
from .context import Context
from ..utils.logger import setup_logger
from modules.conversation import ConversationModule

class Rowan:
    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logger(__name__)
        self.conversation = ConversationModule()
        self.module_manager = ModuleManager()
        self.context = Context()
        
        # Module-specific keywords mapping
        self.MODULE_KEYWORDS = {
            "calendar": {
                "patterns": [
                    r"schedule",
                    r"appointment",
                    r"meeting",
                    r"remind me",
                    r"add.*calendar",
                    r"check.*calendar",
                    r"remove.*event"
                ],
                "commands": ["add", "check", "remove", "list", "update"]
            },
            "discord": {
                "patterns": [
                    r"discord",
                    r"server",
                    r"channel",
                    r"dm",
                    r"message"
                ]
            }
        }
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Load all enabled modules"""
        for module_name in self.settings.ENABLED_MODULES:
            self.module_manager.load_module(module_name)
    
    def _determine_module(self, input_data: str) -> str:
        """Determine which module should handle the input based on content analysis"""
        input_lower = input_data.lower()
        
        # Check each module's patterns
        for module_name, config in self.MODULE_KEYWORDS.items():
            patterns = config.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, input_lower):
                    # Verify module is loaded and active
                    if self.module_manager.get_module(module_name):
                        return module_name
                        
        # Default to conversation module if no specific module matches
        return "conversation"

    def process_input(self, input_data: str) -> Dict[str, Any]:
        """Process user input through appropriate module"""
        try:
            # Determine which module should handle this input
            module_name = self._determine_module(input_data)
            
            # Create context for module processing
            context = {
                "source": "user",
                "timestamp": datetime.now(),
                "original_input": input_data
            }
            
            if module_name == "conversation":
                return self.conversation.process(input_data, context)
            
            # Process through specific module
            response = self.module_manager.process_input(
                module_name,
                input_data,
                context
            )
            
            # If module processing failed, fallback to conversation
            if not response.get("success", False):
                self.logger.warning(f"Module {module_name} processing failed, falling back to conversation")
                return self.conversation.process(input_data, context)
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            return {
                "response": "I encountered an error processing your input.",
                "error": str(e),
                "success": False
            }