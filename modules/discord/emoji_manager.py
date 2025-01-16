import json
from typing import List, Dict, Optional
import random

class EmojiManager:
    def __init__(self, emoji_file: str):
        self.emoji_file = emoji_file
        self.emojis: List[Dict] = []
        self.load_emojis()
        
    def load_emojis(self):
        """Load emojis from JSON file"""
        try:
            with open(self.emoji_file, 'r') as f:
                data = json.load(f)
                self.emojis = data['emojis']
        except Exception as e:
            print(f"Error loading emojis: {e}")
            self.emojis = []
            
    def find_matching_emojis(self, text: str) -> List[str]:
        """Find emojis matching triggers in text"""
        matching = []
        text_lower = text.lower()
        
        for emoji in self.emojis:
            if any(trigger in text_lower for trigger in emoji['triggers']):
                matching.append(emoji['emoji'])
                
        return matching
        
    def add_emojis_to_response(self, response: str) -> str:
        """Intelligently add emojis to response"""
        matching_emojis = self.find_matching_emojis(response)
        
        if not matching_emojis:
            return response
            
        # Randomly select 1-2 matching emojis
        selected_emojis = random.sample(
            matching_emojis, 
            min(len(matching_emojis), random.randint(1, 2))
        )
        
        # Add emojis at natural positions
        if random.random() < 0.5:  # 50% chance for prefix
            response = f"{' '.join(selected_emojis)} {response}"
        else:  # Otherwise append
            response = f"{response} {' '.join(selected_emojis)}"
            
        return response