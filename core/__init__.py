"""
Core functionality package.
"""
from .rowan_assistant import RowanAssistant
from .llm_interface import OllamaInterface
from .personal_memory import PersonalMemorySystem, InteractionContext, PersonalityTrait
from .nlp import TextAnalyzer  
from .memory_manager import MemoryManager  

__all__ = [
    'RowanAssistant',
    'PersonalMemorySystem',
    'OllamaInterface',
    'InteractionContext',
    'PersonalityTrait',
    'TextAnalyzer',
    'MemoryManager'
]