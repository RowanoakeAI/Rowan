from typing import Dict, Any, List, Optional
import requests
import json
from datetime import datetime
from bson import ObjectId
from json import JSONEncoder
from .personal_memory import PersonalMemorySystem, InteractionContext
from utils.serialization import DataSerializer
from utils.json_encoder import RowanJSONEncoder

# Add custom JSON encoder
class MongoJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

class OllamaInterface:
    def __init__(self, model_name: str = "rowdis", base_url: str = "http://localhost:11434", 
                 memory_system: Optional[PersonalMemorySystem] = None):
        self.model_name = model_name
        self.base_url = base_url
        self.memory = memory_system or PersonalMemorySystem()  # Use passed instance or get singleton
        
    def generate_context(self, query: str) -> str:
        """Generate context from memory for the model"""
        # Get recent interactions and serialize them
        recent = self.memory.get_recent_interactions(hours=24)
        serialized_recent = DataSerializer.serialize_object(recent)
        
        # Get active goals and serialize
        goals = self.memory.get_active_goals()
        serialized_goals = DataSerializer.serialize_object(goals)
        
        # Get personality profile and serialize
        personality = self.memory.get_personality_profile()
        serialized_personality = DataSerializer.serialize_object(personality)
        
        # Create a formatted context string using serialized data
        context = f"""You are Rowan, a personal AI assistant. Here's your current context:

Personality Profile:
{json.dumps(serialized_personality['traits'], indent=2, cls=RowanJSONEncoder)}

Recent Interactions:
{json.dumps(serialized_recent[-3:], indent=2, cls=RowanJSONEncoder)}

Active Goals:
{json.dumps(serialized_goals, indent=2, cls=RowanJSONEncoder)}

Please maintain this personality and context in your response.
Current query: {query}
"""
        return context

    def call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Make a call to Ollama API"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama: {e}")
            return {"error": str(e)}

    def process_query(self, query: str, context_type: InteractionContext = InteractionContext.CASUAL) -> str:
        """Process a query through Ollama with memory context"""
        # Generate context from memory
        context = self.generate_context(query)
        
        # Create full prompt
        full_prompt = f"{context}\n\nUser: {query}\nRowan:"
        
        # Get response from Ollama
        response = self.call_ollama(full_prompt)
        
        if "error" in response:
            return f"I apologize, but I encountered an error: {response['error']}"
        
        return response.get("response", "I apologize, but I couldn't generate a response.")