from typing import Dict, Any, Optional, Literal
from datetime import datetime
import re
from utils.logger import setup_logger
from core.module_manager import ModuleManager
from core.personal_memory import InteractionSource
from modules.conversation import ConversationModule

InputType = Literal["text", "voice"]

class InputHandler:
    """Handles input processing and module routing"""
    
    def __init__(self, module_manager: ModuleManager, conversation_module: ConversationModule):
        self.logger = setup_logger(__name__)
        self.module_manager = module_manager
        self.conversation = conversation_module
        
        # Module routing patterns
        self.MODULE_PATTERNS = {
            "calendar": r"(?:schedule|event|appointment|remind)",
            "system": r"(?:cpu|memory|disk|system|monitor)",
            "discord": r"(?:discord|server|channel|message)",
        }

    def process_input(self, 
                     input_text: str,
                     source: InteractionSource = InteractionSource.UNKNOWN,
                     input_type: InputType = "text",
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user input and route to appropriate module"""
        try:
            if not input_text or not input_text.strip():
                return {
                    "success": False,
                    "response": "Please provide valid input",
                    "error": "Empty input"
                }

            # Preprocess based on input type
            cleaned_input = (self._preprocess_voice(input_text) 
                           if input_type == "voice" 
                           else self._preprocess_input(input_text))
            
            # Build context with input type
            input_context = self._build_context(cleaned_input, source, input_type, context)
            
            # Determine target module
            module_name = self._determine_module(cleaned_input)
            
            if module_name == "conversation":
                return self.conversation.process(cleaned_input, input_context)
            
            # Process through specific module
            response = self.module_manager.process_input(
                module_name, 
                cleaned_input,
                input_context
            )
            
            # Fallback to conversation if module fails
            if not response.get("success", False):
                self.logger.warning(f"Module {module_name} failed, falling back to conversation")
                return self.conversation.process(cleaned_input, input_context)
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            return {
                "success": False,
                "response": "I encountered an error processing your request",
                "error": str(e)
            }
            
    def _preprocess_input(self, input_text: str) -> str:
        """Clean and normalize input text"""
        # Remove extra whitespace
        cleaned = " ".join(input_text.split())
        return cleaned.strip()

    def _preprocess_voice(self, voice_input: str) -> str:
        """Special preprocessing for voice input"""
        # Remove speech recognition artifacts
        cleaned = re.sub(r'\[.*?\]', '', voice_input)
        # Remove filler words
        filler_words = r'\b(um|uh|er|ah|like|you know|i mean)\b'
        cleaned = re.sub(filler_words, '', cleaned, flags=re.IGNORECASE)
        return self._preprocess_input(cleaned)
        
    def _determine_module(self, input_text: str) -> str:
        """Determine which module should handle the input"""
        input_lower = input_text.lower()
        
        for module_name, pattern in self.MODULE_PATTERNS.items():
            if re.search(pattern, input_lower):
                if self.module_manager.get_module(module_name):
                    return module_name
                    
        return "conversation"
        
    def _build_context(self,
                      input_text: str,
                      source: InteractionSource,
                      input_type: InputType,
                      extra_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build processing context with input type information"""
        context = {
            "timestamp": datetime.now(),
            "source": source,
            "input_type": input_type,
            "original_input": input_text
        }
        
        if extra_context:
            context.update(extra_context)
            
        return context