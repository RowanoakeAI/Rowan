from enum import Enum

class ContextPriority(Enum):
    """Priority levels for different types of context"""
    CRITICAL = 4
    HIGH = 3 
    MEDIUM = 2
    LOW = 1

class ContextType(Enum):
    """Types of context that can be tracked"""
    CONVERSATION = "conversation"
    MEMORY = "memory"
    EMOTIONAL = "emotional" 
    TASK = "task"
    SYSTEM = "system"
    MODULE = "module"