# core/context.py
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from utils.serialization import DataSerializer
from utils.logger import setup_logger

class ContextType(Enum):
    """Types of context that can be tracked"""
    CONVERSATION = "conversation"
    MEMORY = "memory"
    EMOTIONAL = "emotional"
    TASK = "task"
    SYSTEM = "system"
    MODULE = "module"  # Add module context type

@dataclass
class ContextState:
    """Represents the current state of context"""
    type: ContextType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    priority: int = 1

@dataclass
class ModuleContextState:
    """Track module-specific context"""
    module_name: str
    is_active: bool
    last_command: Optional[str] = None
    last_response: Optional[Dict[str, Any]] = None
    error_count: int = 0

class Context:
    """Manages conversation and interaction context"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.states: Dict[ContextType, ContextState] = {}
        self.history: List[ContextState] = []
        self.max_history = 100
        self.module_states: Dict[str, ModuleContextState] = {}
        
    def update_context(self, 
                      context_type: ContextType,
                      data: Dict[str, Any],
                      metadata: Optional[Dict[str, Any]] = None,
                      priority: int = 1) -> None:
        """Update context for a specific type"""
        try:
            state = ContextState(
                type=context_type,
                timestamp=datetime.utcnow(),
                data=data,
                metadata=metadata,
                priority=priority
            )
            
            # Store in current states
            self.states[context_type] = state
            
            # Add to history
            self.history.append(state)
            
            # Trim history if needed
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
                
            self.logger.debug(f"Updated {context_type.value} context")
            
        except Exception as e:
            self.logger.error(f"Error updating context: {str(e)}")
            raise

    def get_context(self, context_type: Optional[ContextType] = None) -> Dict[str, Any]:
        """Get current context state(s)"""
        try:
            if context_type:
                state = self.states.get(context_type)
                return DataSerializer.serialize_dict(asdict(state)) if state else {}
            
            # Return all contexts if no specific type requested
            return DataSerializer.serialize_dict({
                ctype.value: asdict(state) 
                for ctype, state in self.states.items()
            })
            
        except Exception as e:
            self.logger.error(f"Error getting context: {str(e)}")
            return {}

    def get_context_history(self, 
                          context_type: Optional[ContextType] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get context history, optionally filtered by type"""
        try:
            history = self.history
            if context_type:
                history = [state for state in history if state.type == context_type]
                
            # Get last N entries and serialize
            recent = history[-limit:]
            return DataSerializer.serialize_object(
                [asdict(state) for state in recent]
            )
            
        except Exception as e:
            self.logger.error(f"Error getting context history: {str(e)}")
            return []

    def clear_context(self, context_type: Optional[ContextType] = None) -> None:
        """Clear specific or all context"""
        try:
            if context_type:
                self.states.pop(context_type, None)
            else:
                self.states.clear()
                
            self.logger.info(f"Cleared {'all' if not context_type else context_type.value} context")
            
        except Exception as e:
            self.logger.error(f"Error clearing context: {str(e)}")

    def merge_contexts(self, priority_type: Optional[ContextType] = None) -> Dict[str, Any]:
        """Merge all contexts into single view, optionally prioritizing one type"""
        try:
            merged = {}
            
            # Sort states by priority
            sorted_states = sorted(
                self.states.items(),
                key=lambda x: (
                    x[1].priority if x[0] != priority_type else float('inf'),
                    x[1].timestamp
                ),
                reverse=True
            )
            
            # Merge states, later states override earlier ones
            for _, state in sorted_states:
                merged.update(state.data)
                
            return DataSerializer.serialize_dict(merged)
            
        except Exception as e:
            self.logger.error(f"Error merging contexts: {str(e)}")
            return {}

    def update_module_state(self, 
                          module_name: str,
                          is_active: bool,
                          command: Optional[str] = None,
                          response: Optional[Dict[str, Any]] = None) -> None:
        """Track module state changes"""
        try:
            state = self.module_states.get(module_name, ModuleContextState(module_name, is_active))
            
            if command:
                state.last_command = command
            if response:
                state.last_response = response
                if not response.get('success', False):
                    state.error_count += 1
                    
            self.module_states[module_name] = state
            
            # Update context
            self.update_context(
                ContextType.MODULE,
                {
                    "module": module_name,
                    "state": asdict(state)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error updating module state: {str(e)}")

    def get_module_state(self, module_name: str) -> Optional[ModuleContextState]:
        """Get current state of a module"""
        return self.module_states.get(module_name)