# core/context_generator.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import re
import numpy as np
from .context_types import ContextType, ContextPriority  # Import from shared module
from core.personal_memory import PersonalMemorySystem, InteractionContext, PersonalityTrait
from .context import ModuleContextState, Context
from utils.logger import setup_logger
from config.settings import Settings

class ContextGenerator:
    def __init__(self, memory: PersonalMemorySystem):
        self.memory = memory
        self.max_context_length = 4000
        self.logger = setup_logger(__name__)  # Add logger initialization
        self.context = Context()  # Add Context instance
        self.settings = Settings()  # Add settings instance
        
        # Enhanced module patterns with command specificity
        self.module_patterns = {
            "calendar": {
                "commands": {
                    "add": r"(?:schedule|add|create|set up|make).*?(?:meeting|appointment|event|reminder)",
                    "check": r"(?:check|look up|show|tell me|display|view).*?(?:calendar|schedule)",
                    "remove": r"(?:remove|delete|cancel|clear).*?(?:meeting|appointment|event)",
                    "list": r"(?:list|show|get|tell me).*?(?:events|meetings|appointments)"
                },
                "general": [r"calendar", r"schedule", r"appointment", r"meeting", r"remind me", r"event"]
            },
            "discord": {
                "commands": {
                    "send": r"(?:send|post|write).*?(?:message|reply)",
                    "read": r"(?:read|check|show).*?(?:messages|channel)",
                    "manage": r"(?:manage|update|change).*?(?:server|channel|role)"
                },
                "general": [r"discord", r"server", r"channel", r"message"]
            }
        }

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        intent_scores = {
            "personal": 0.0,
            "task": 0.0,
            "knowledge": 0.0,
            "emotional": 0.0,
            "preference": 0.0,
            "module": None,
            "command": None,
            "confidence": 0.0  # Add confidence score
        }
        
        # Normalize input
        query_lower = query.lower().strip()
        
        # Check for explicit command markers
        command_markers = ["!", "/", ".", "run", "execute", "do"]
        is_explicit_command = any(query_lower.startswith(m) for m in command_markers)
        
        # Apply higher confidence for explicit commands
        if is_explicit_command:
            intent_scores["confidence"] = 0.9

        # Enhanced module pattern matching
        for module_name, patterns in self.module_patterns.items():
            # Check specific command patterns first
            for cmd, pattern in patterns["commands"].items():
                if re.search(pattern, query_lower):
                    intent_scores.update({
                        "module": module_name,
                        "command": cmd,
                        "task": 1.0,
                        "confidence": 0.8 + (0.1 if is_explicit_command else 0)
                    })
                    return intent_scores

        return intent_scores

    def get_time_relevant_context(self) -> Dict[str, Any]:
        """Get context relevant to current time"""
        current_time = datetime.now().replace(microsecond=0)  # Remove microseconds for cleaner timestamps
        current_hour = current_time.hour
        
        # Determine time of day context
        time_context = {
            "time_of_day": "morning" if 5 <= current_hour < 12 else
                        "afternoon" if 12 <= current_hour < 17 else
                        "evening" if 17 <= current_hour < 22 else
                        "night",
            "day_of_week": current_time.strftime("%A"),
            "is_weekend": current_time.weekday() >= 5,
            "current_time": current_time  # Add the actual timestamp
        }
        
        # Get schedule for today
        start_time = current_time.replace(hour=0, minute=0, second=0)
        end_time = (start_time + timedelta(days=1))
        
        today_schedule = self.memory.get_schedule_range(
            start_time,
            end_time
        )
        
        return {
            "temporal": time_context,
            "schedule": today_schedule
        }

    def get_emotional_context(self) -> Dict[str, Any]:
        """Analyze recent emotional patterns"""
        recent_interactions = self.memory.get_recent_interactions(hours=24)
        
        # Analyze mood patterns
        moods = [i.get('mood') for i in recent_interactions if i.get('mood')]
        if moods:
            from collections import Counter
            mood_counts = Counter(moods)
            dominant_mood = max(mood_counts.items(), key=lambda x: x[1])[0]
        else:
            dominant_mood = None
            
        return {
            "current_mood": dominant_mood,
            "mood_pattern": dict(mood_counts) if moods else {},
            "emotional_context": self.memory.analyze_patterns().get('mood_patterns', [])
        }

    def get_relevant_goals(self, query: str) -> List[Dict[str, Any]]:
        """Get goals relevant to the current query"""
        active_goals = self.memory.get_active_goals()
        
        # Score goals based on relevance to query
        scored_goals = []
        for goal in active_goals:
            relevance_score = 0
            
            # Check title and description for relevance
            if any(word in query.lower() for word in goal['title'].lower().split()):
                relevance_score += 0.5
            if any(word in query.lower() for word in goal['description'].lower().split()):
                relevance_score += 0.3
                
            # Prioritize urgent goals
            if goal['deadline']:
                days_until_deadline = (goal['deadline'] - datetime.now()).days
                if days_until_deadline <= 7:  # Urgent if within a week
                    relevance_score += 0.2
                    
            if relevance_score > 0:
                scored_goals.append((goal, relevance_score))
                
        # Sort by relevance and return top goals
        scored_goals.sort(key=lambda x: x[1], reverse=True)
        return [goal for goal, score in scored_goals[:3]]

    def get_relevant_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant knowledge based on query"""
        # Extract potential topics from query
        # This could be enhanced with proper NLP
        words = query.lower().split()
        
        relevant_knowledge = []
        for topic in self.memory.knowledge.distinct("topic"):
            if any(word in topic.lower() for word in words):
                knowledge = self.memory.knowledge.find_one({"topic": topic})
                if knowledge:
                    relevant_knowledge.append(knowledge)
                    
        return relevant_knowledge

    def get_preference_context(self, query: str) -> Dict[str, Any]:
        """Get relevant preferences based on query"""
        # Extract potential categories from query
        categories = set()
        for category in self.memory.preferences.distinct("category"):
            if any(word in query.lower() for word in category.lower().split()):
                categories.add(category)
                
        preferences = {}
        for category in categories:
            prefs = self.memory.get_preferences_by_category(category)
            if prefs:
                preferences[category] = prefs
                
        return preferences

    def generate_context(self, query: str) -> str:
        """Enhanced context generation with module command awareness"""
        intent_scores = self.analyze_query_intent(query)
        context_parts = []
        
        # Prioritize module context if present
        if (module_name := intent_scores["module"]):
            module_state = self.get_module_state(module_name)
            
            if module_state:
                module_context = {
                    "name": module_name,
                    "active": module_state.is_active,
                    "command": intent_scores.get("command"),
                    "last_command": module_state.last_command,
                    "error_count": module_state.error_count,
                    "state": "ready" if module_state.is_active else "inactive"
                }
                
                context_parts.append(
                    f"""Module Context:
Module: {module_context['name']}
State: {module_context['state']}
Command: {module_context['command'] or 'None'}
Last Command: {module_context['last_command'] or 'None'}
Error Count: {module_context['error_count']}"""
                )

        # Add personality baseline
        personality = self.memory.get_personality_profile()
        context_parts.append(f"""You are Rowan, a personal AI assistant with the following personality traits:
{json.dumps(personality['traits'], indent=2)}""")

        # Add time context
        time_context = self.get_time_relevant_context()
        context_parts.append(f"""Current temporal context:
Time of day: {time_context['temporal']['time_of_day']}
Day: {time_context['temporal']['day_of_week']}
{'Weekend' if time_context['temporal']['is_weekend'] else 'Weekday'}""")

        # Add emotional context if relevant
        if intent_scores["emotional"] > 0.3:
            emotional_context = self.get_emotional_context()
            context_parts.append(f"""Current emotional context:
Dominant mood: {emotional_context['current_mood']}
Recent mood patterns: {json.dumps(emotional_context['mood_pattern'], indent=2)}""")

        # Add relevant goals
        if intent_scores["task"] > 0.3:
            relevant_goals = self.get_relevant_goals(query)
            if relevant_goals:
                context_parts.append("Relevant goals:")
                for goal in relevant_goals:
                    context_parts.append(f"- {goal['title']}: {goal['description']}")

        # Add relevant knowledge
        if intent_scores["knowledge"] > 0.3:
            relevant_knowledge = self.get_relevant_knowledge(query)
            if relevant_knowledge:
                context_parts.append("Relevant knowledge:")
                for knowledge in relevant_knowledge:
                    context_parts.append(f"- {knowledge['topic']}: {knowledge['content']}")

        # Add preference context
        if intent_scores["preference"] > 0.3:
            preference_context = self.get_preference_context(query)
            if preference_context:
                context_parts.append("Relevant preferences:")
                for category, prefs in preference_context.items():
                    context_parts.append(f"- {category}:")
                    for pref in prefs:
                        context_parts.append(f"  - {pref['item']}: {pref['rating']}")

        # Combine with strict module priority
        if intent_scores["module"]:
            full_context = "\n\n".join([context_parts[0]] + context_parts[1:])
        else:
            full_context = "\n\n".join(context_parts)

        # Add final instruction
        full_context += "\n\nPlease use this context to provide a personalized, relevant response while maintaining consistency with previous interactions and personality traits."
        
        return full_context

    def get_module_state(self, module_name: str) -> Optional[ModuleContextState]:
        """Enhanced module state tracking"""
        try:
            # Get state from database
            state_data = self.memory.get_module_state(module_name)
            if not state_data:
                return None
                
            # Convert to ModuleContextState
            state = ModuleContextState(
                module_name=module_name,
                is_active=state_data.get('state', {}).get('is_active', False),
                last_command=state_data.get('state', {}).get('last_command'),
                last_response=state_data.get('state', {}).get('last_response'),
                error_count=state_data.get('state', {}).get('error_count', 0)
            )
            
            # Validate error count
            if state.error_count > 5:
                self.logger.warning(f"Resetting module state for {module_name} due to high error count")
                self.memory.reset_module_state(module_name)
                return None
                
            return state
            
        except Exception as e:
            self.logger.error(f"Error getting module state: {str(e)}")
            return None

    def get_contextual_guidelines(self) -> Dict[str, Any]:
        """Enhanced guidelines with module awareness"""
        guidelines = super().get_contextual_guidelines()
        
        # Add module-specific guidelines if relevant
        module_context = self.memory.context.get_context(ContextType.MODULE)
        if module_context:
            guidelines["module_specific"] = True
            guidelines["formality_level"] += 0.2  # Increase formality for module interactions
            
        return guidelines
    
    def _calculate_formality_level(self, personality: Dict[str, Any]) -> float:
        """Calculate appropriate formality level based on personality"""
        conscientiousness = personality['traits'].get(PersonalityTrait.CONSCIENTIOUSNESS.value, 0.5)
        extraversion = personality['traits'].get(PersonalityTrait.EXTRAVERSION.value, 0.5)
        
        # Higher conscientiousness and lower extraversion suggests more formal communication
        return (conscientiousness * 0.7 + (1 - extraversion) * 0.3)
    
    def _determine_response_style(self, personality: Dict[str, Any]) -> str:
        """Determine appropriate response style based on personality"""
        openness = personality['traits'].get(PersonalityTrait.OPENNESS.value, 0.5)
        extraversion = personality['traits'].get(PersonalityTrait.EXTRAVERSION.value, 0.5)
        
        if openness > 0.7 and extraversion > 0.7:
            return "enthusiastic"
        elif openness > 0.7:
            return "analytical"
        elif extraversion > 0.7:
            return "friendly"
        else:
            return "balanced"

    def merge_context_sources(self, query: str) -> Dict[str, Any]:
        """Merge multiple context sources with weighted relevance"""
        context_sources = {
            "temporal": self.get_time_relevant_context(),
            "emotional": self.get_emotional_context(),
            "knowledge": self.get_relevant_knowledge(query),
            "goals": self.get_relevant_goals(query),
            "preferences": self.get_preference_context(query)
        }
        
        # Weight different context sources
        weights = {
            "temporal": 0.2,
            "emotional": 0.3,
            "knowledge": 0.2,
            "goals": 0.2,
            "preferences": 0.1
        }
        
        return {
            source: {
                "data": data,
                "weight": weights[source],
                "relevance_score": self._calculate_relevance(data, query)
            }
            for source, data in context_sources.items()
        }

# Update the OllamaInterface to use the new context generator
class OllamaInterface:
    def __init__(self, model_name: str = None, base_url: str = None):
        settings = Settings()
        self.model_name = model_name or settings.MODEL_CONFIG["name"]
        self.base_url = base_url or settings.MODEL_CONFIG["base_url"]
        self.memory = PersonalMemorySystem()
        self.context_generator = ContextGenerator(self.memory)
    
    def process_query(self, query: str, context_type: InteractionContext = InteractionContext.CASUAL) -> str:
        # Generate rich context
        context = self.context_generator.generate_context(query)
        
        # Get response guidelines
        guidelines = self.context_generator.get_contextual_guidelines()
        
        # Create full prompt
        full_prompt = f"""{context}

Response Guidelines:
- Formality Level: {guidelines['formality_level']:.2f}
- Style: {guidelines['response_style']}
- Empathy Level: {guidelines['empathy_level']:.2f}
- Detail Level: {guidelines['detail_level']:.2f}

User Query: {query}

Rowan:"""
        
        # Get response from Ollama
        response = self.call_ollama(full_prompt)
        
        if "error" in response:
            return f"I apologize, but I encountered an error: {response['error']}"
        
        # Store interaction in memory
        self.memory.store_interaction(
            content={
                "query": query,
                "response": response.get("response", ""),
                "model": self.model_name,
                "context_used": context,
                "guidelines_used": guidelines
            },
            context_type=context_type
        )
        
        return response.get("response", "I apologize, but I couldn't generate a response.")