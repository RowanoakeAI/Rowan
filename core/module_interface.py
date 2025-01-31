from typing import Dict, Any
from utils.logger import setup_logger

class ModuleInterface:
    """Base interface that all modules must implement"""
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the module"""
        raise NotImplementedError
        
    def process(self, input_data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input through the module"""
        raise NotImplementedError
        
    def shutdown(self) -> bool:
        """Clean shutdown of module - returns True if successful"""
        return True