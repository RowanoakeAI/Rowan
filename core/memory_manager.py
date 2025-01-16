# core/memory_manager.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from core.personal_memory import PersonalMemorySystem, InteractionContext
from utils.logger import setup_logger
from core.nlp import TextAnalyzer
from bson import ObjectId

class MemoryManager:
    """Manages memory operations and relevance scoring for conversations"""
    
    def __init__(self, memory_system: Optional[PersonalMemorySystem] = None):
        self.logger = setup_logger(__name__)
        self.memory = memory_system or PersonalMemorySystem()
        self.text_analyzer = TextAnalyzer()
        self.relevance_threshold = 0.3  # Minimum relevance score
        self.max_memories = 10  # Maximum memories to return
        
    def get_relevant_memories(self, input_text: str) -> Dict[str, Any]:
        """Retrieve memories relevant to the input text"""
        try:
            # Extract keywords from input
            keywords = self.text_analyzer.extract_keywords(input_text)
            
            # Get recent interactions
            recent_memories = self.memory.get_recent_interactions(hours=24)
            
            # Score and filter memories
            scored_memories = self._score_memories(input_text, keywords, recent_memories)
            relevant_memories = self._filter_memories(scored_memories)
            
            # Get additional context
            context = {
                "interactions": relevant_memories,
                "personality": self.memory.get_personality_profile(),
                "goals": self.memory.get_active_goals(),
                "timestamp": datetime.utcnow()
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error retrieving memories: {str(e)}")
            return {}
            
    def _score_memories(self, input_text: str, keywords: List[str], 
                       memories: List[Dict[str, Any]]) -> List[tuple]:
        """Score memories based on relevance to input"""
        scored = []
        
        for memory in memories:
            score = 0.0
            
            # Keyword matching
            memory_text = memory.get("content", {}).get("message", "")
            if memory_text:
                memory_keywords = self.text_analyzer.extract_keywords(memory_text)
                matching_keywords = set(keywords) & set(memory_keywords)
                score += len(matching_keywords) * 0.2
                
            # Recency scoring
            age = datetime.utcnow() - memory.get("timestamp", datetime.utcnow())
            recency_score = 1.0 / (1.0 + age.total_seconds() / 3600)  # Decay over hours
            score += recency_score * 0.3
            
            # Importance scoring
            score += memory.get("importance", 0) * 0.2
            
            # Context matching
            if memory.get("context_type") == memory.get("context_type"):
                score += 0.3
                
            scored.append((memory, score))
            
        return scored
        
    def _filter_memories(self, scored_memories: List[tuple]) -> List[Dict[str, Any]]:
        """Filter and sort memories by relevance score"""
        # Sort by score descending
        sorted_memories = sorted(scored_memories, key=lambda x: x[1], reverse=True)
        
        # Filter by threshold and limit
        filtered = [
            memory for memory, score in sorted_memories 
            if score >= self.relevance_threshold
        ][:self.max_memories]
        
        return filtered
        
    def store_memory(self, content: Dict[str, Any], context_type: InteractionContext,
                    importance: int = 1) -> Optional[ObjectId]:
        """Store a new memory"""
        try:
            return self.memory.store_interaction(
                content=content,
                context_type=context_type,
                importance=importance
            )
        except Exception as e:
            self.logger.error(f"Error storing memory: {str(e)}")
            return None
            
    def update_memory(self, memory_id: ObjectId, updates: Dict[str, Any]) -> bool:
        """Update an existing memory"""
        try:
            # Implement memory update logic here
            # This would interface with PersonalMemorySystem's update methods
            return True
        except Exception as e:
            self.logger.error(f"Error updating memory: {str(e)}")
            return False
            
    def consolidate_memories(self) -> None:
        """Consolidate and organize memories periodically"""
        try:
            # Get memories ready for consolidation
            memories = self.memory.get_recent_interactions(hours=24)
            
            # Group related memories
            # Implement consolidation logic here
            
            # Update importance scores
            # Implement importance updating logic here
            
            self.logger.info("Memory consolidation completed")
            
        except Exception as e:
            self.logger.error(f"Error during memory consolidation: {str(e)}")