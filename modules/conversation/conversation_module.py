# modules/conversation/conversation_module.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from core.personal_memory import InteractionContext
from utils.logger import setup_logger
from core.nlp import TextAnalyzer
from core.memory_manager import MemoryManager
from core.module_manager import ModuleInterface

@dataclass
class ConversationState:
    """Tracks the current state of a conversation"""
    context_type: InteractionContext
    turn_count: int
    last_update: datetime
    sentiment: float = 0.0
    topic: str = ""

class ConversationModule(ModuleInterface):  # Add ModuleInterface inheritance
    """Handles natural conversation interactions with the assistant"""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.logger = setup_logger(__name__)
        self.state = ConversationState(
            context_type=InteractionContext.CASUAL,
            turn_count=0,
            last_update=datetime.now()
        )
        self.history: List[Dict[str, Any]] = []
        self.text_analyzer = TextAnalyzer()
        self.memory_manager = memory_manager or MemoryManager()
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the conversation module"""
        try:
            # Optional: Configure from passed settings
            if config:
                self.memory_manager = config.get('memory_manager', self.memory_manager)
            
            self.logger.info("Conversation module initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation module: {str(e)}")
            return False
            
    def shutdown(self) -> None:
        """Clean shutdown of module"""
        self.logger.info("Shutting down conversation module")
        
    def process(self, input_data: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process conversational input"""
        try:
            # Preprocess input
            cleaned_input = self._preprocess_input(input_data)
            
            # Update conversation state
            self.state.turn_count += 1
            self.state.last_update = datetime.now()
            
            # Analyze input
            sentiment = self.text_analyzer.analyze_sentiment(cleaned_input)
            self.state.sentiment = sentiment
            
            # Determine context
            context_type = self._determine_context_type(cleaned_input, context)
            self.state.context_type = context_type
            
            # Generate response using memory and context
            memory_context = self.memory_manager.get_relevant_memories(cleaned_input)
            response = self._generate_response(
                input_text=cleaned_input,
                context_type=context_type,
                sentiment=sentiment,
                memories=memory_context
            )
            
            # Update conversation history
            self._update_history(cleaned_input, response, context_type)
            
            return self._format_response(response)
            
        except Exception as e:
            self.logger.error(f"Error in conversation processing: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your message.",
                "error": str(e),
                "success": False
            }

    def _preprocess_input(self, input_text: str) -> str:
        """Clean and normalize input text"""
        return input_text.strip().lower()

    def _generate_response(self, input_text: str, context_type: InteractionContext,
                         sentiment: float, memories: Dict[str, Any]) -> str:
        """Generate appropriate response based on context and memories"""
        try:
            response = self.assistant.chat(
                message=input_text,
                context_type=context_type,
                sentiment=sentiment,
                memories=memories
            )
            return response
        except Exception as e:
            self.logger.error(f"Response generation error: {str(e)}")
            return "I'm having trouble formulating a response right now."

    def _update_history(self, user_input: str, response: str, context_type: InteractionContext):
        """Update conversation history"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response,
            "context_type": context_type,
            "sentiment": self.state.sentiment
        })
        
        # Trim history if too long
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def _format_response(self, response: str) -> Dict[str, Any]:
        """Format the response with metadata"""
        return {
            "response": response,
            "context_type": self.state.context_type,
            "sentiment": self.state.sentiment,
            "turn_count": self.state.turn_count,
            "success": True
        }

    def _determine_context_type(self, input_text: str, context: Dict[str, Any] = None) -> InteractionContext:
        """Determine the appropriate context type for the interaction"""
        # Default to casual
        if not input_text:
            return InteractionContext.CASUAL
            
        # Check for emotional content
        emotional_keywords = {"feel", "happy", "sad", "angry", "love", "hate"}
        if any(word in input_text.lower() for word in emotional_keywords):
            return InteractionContext.EMOTIONAL
            
        # Check for task-oriented content    
        task_keywords = {"do", "task", "goal", "schedule", "plan", "help"}
        if any(word in input_text.lower() for word in task_keywords):
            return InteractionContext.TASK_ORIENTED
            
        # Check for learning content
        learning_keywords = {"learn", "teach", "explain", "how", "why", "what"}
        if any(word in input_text.lower() for word in learning_keywords):
            return InteractionContext.LEARNING
            
        # Check for professional content
        professional_keywords = {"work", "business", "project", "meeting"}
        if any(word in input_text.lower() for word in professional_keywords):
            return InteractionContext.PROFESSIONAL
            
        return InteractionContext.CASUAL