"""
Core functionality package.
"""
from .rowan_assistant import RowanAssistant
from .llm_interface import OllamaInterface
from .personal_memory import PersonalMemorySystem, InteractionContext, PersonalityTrait
from .context_generation import ContextGenerator
from .nlp import TextAnalyzer  # Changed from 'nlp' to '.nlp'
from .memory_manager import MemoryManager  # Changed from 'memory_manager' to '.memory_manager'
from .context import Context

__all__ = [
    'RowanAssistant',
    'llmInterface',
    'PersonalMemorySystem',
    'InteractionContext',
    'PersonalityTrait',
    'ContextGenerator',
    'TextAnalyzer',
    'MemoryManager',
    'Context'
]