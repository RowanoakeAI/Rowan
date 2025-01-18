from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from core.personal_memory import PersonalMemorySystem, InteractionContext, PersonalityTrait
from core.llm_interface import OllamaInterface
from core.context_generation import ContextGenerator
from utils.logger import setup_logger
from config.settings import Settings
from utils.json_encoder import RowanJSONEncoder
from utils.serialization import DataSerializer
from core.personal_memory import InteractionSource

class RowanAssistant:
    def __init__(self, model_name: str = None):
        self.logger = setup_logger(__name__)
        self.settings = Settings()
        self.memory = PersonalMemorySystem()  # Will return singleton instance
        model = model_name or self.settings.DEFAULT_MODEL
        self.llm = OllamaInterface(model_name=model, memory_system=self.memory)
        self.context_generator = ContextGenerator(self.memory)

    def chat(self, message: str, 
             context_type: InteractionContext = InteractionContext.CASUAL,
             source: InteractionSource = InteractionSource.UNKNOWN,
             mood: Optional[str] = None) -> str:
        try:
            self.logger.info(f"Processing chat message from {source.value} with context type: {context_type}")
            
            # Generate context
            context = self.context_generator.generate_context(message)
            
            # Process query
            response = self.llm.process_query(message, context_type)
            
            # Create content dictionary with source
            content = {
                "message": message,
                "response": response,
                "source": source.value,
                "timestamp": datetime.utcnow()
            }
            
            # Use the serializer
            serialized_content = DataSerializer.serialize_dict(content)
            
            self.memory.store_interaction(
                content=serialized_content,
                context_type=context_type,
                source=source,
                mood=mood,
                importance=1
            )
            
            return response
                
        except Exception as e:
            self.logger.error(f"Error in chat processing: {str(e)}")
            self.logger.exception("Detailed traceback:")  # This will log the full traceback
            return "I apologize, but I encountered an error processing your message."

    def set_preference(self, category: str, item: str, rating: float,
                      context: Dict[str, Any] = None) -> None:
        """Set a user preference with logging"""
        try:
            self.logger.info(f"Setting preference: {category}/{item} = {rating}")
            self.memory.store_preference(category, item, rating, context)
        except Exception as e:
            self.logger.error(f"Error setting preference: {str(e)}")
            raise

    def set_goal(self, title: str, description: str, deadline: datetime,
                priority: int, milestones: List[Dict[str, Any]] = None) -> None:
        """Set a new goal with milestones"""
        try:
            self.logger.info(f"Setting goal: {title}")
            self.memory.set_goal(title, description, deadline, priority, milestones)
        except Exception as e:
            self.logger.error(f"Error setting goal: {str(e)}")
            raise

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get comprehensive daily summary with patterns"""
        try:
            interactions = self.memory.get_recent_interactions(hours=24)
            goals = self.memory.get_active_goals()
            patterns = self.memory.analyze_patterns()
            insights = self.memory.generate_insights()
            
            return {
                "interactions": interactions,
                "active_goals": goals,
                "patterns": patterns,
                "insights": insights,
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            self.logger.error(f"Error generating daily summary: {str(e)}")
            return {"error": str(e)}

    def update_personality_trait(self, trait: PersonalityTrait, value: float,
                               context: Dict[str, Any]) -> None:
        """Update personality traits based on interactions"""
        try:
            self.logger.info(f"Updating personality trait: {trait.value} = {value}")
            self.memory.update_personality_trait(trait, value, context)
        except Exception as e:
            self.logger.error(f"Error updating personality trait: {str(e)}")
            raise

    def get_context(self, query: str) -> str:
        """Generate context for a given query"""
        try:
            return self.context_generator.generate_context(query)
        except Exception as e:
            self.logger.error(f"Error generating context: {str(e)}")
            return ""

    def store_feedback(self, interaction_id: str, feedback_type: str,
                      content: Dict[str, Any], rating: int = None) -> None:
        """Store user feedback about interactions"""
        try:
            self.logger.info(f"Storing feedback for interaction: {interaction_id}")
            self.memory.store_feedback(interaction_id, feedback_type, content, rating)
        except Exception as e:
            self.logger.error(f"Error storing feedback: {str(e)}")
            raise

    def close(self) -> None:
        """Properly close all connections"""
        try:
            self.memory.close()
            self.logger.info("Rowan Assistant shut down successfully")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")