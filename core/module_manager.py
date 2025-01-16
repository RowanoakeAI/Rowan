from typing import Dict, Any, Type, Optional
import importlib
import inspect
from pathlib import Path
from utils.logger import setup_logger
from config.settings import Settings
from core.context import Context

class ModuleInterface:
    """Base interface that all modules must implement"""
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the module"""
        raise NotImplementedError
        
    def process(self, input_data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input through the module"""
        raise NotImplementedError
        
    def shutdown(self) -> None:
        """Clean shutdown of module"""
        raise NotImplementedError

class ModuleManager:
    """Manages loading and lifecycle of Rowan modules"""
    
    MODULE_PATHS = {
        "calendar": "skills.calendar_skill",
        "calendar_skill": "skills.calendar_skill",  # Add alias
        "discord": "discord",
        "conversation": "conversation"
    }
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.settings = Settings()
        self.modules: Dict[str, ModuleInterface] = {}
        self.module_configs: Dict[str, Dict[str, Any]] = {}
        self._module_states: Dict[str, bool] = {}
        self.context = Context()

    def load_module(self, module_name: str, base_config: Dict[str, Any] = None) -> bool:
        """Load a module with provided base configuration"""
        try:
            # Check if already loaded
            if module_name in self.modules:
                return True

            # Get module path
            module_path_suffix = self.MODULE_PATHS.get(module_name)
            if not module_path_suffix:
                self.logger.error(f"No path mapping for module: {module_name}")
                return False
                
            module_path = f"modules.{module_path_suffix}"
            
            # Import module
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                self.logger.error(f"Failed to import {module_path}: {str(e)}")
                return False

            # Map module names to their class names
            class_mapping = {
                "calendar": "GoogleCalendarSkill",
                "calendar_skill": "GoogleCalendarSkill",
                "discord": "DiscordModule",
                "conversation": "ConversationModule"
            }
            
            class_name = class_mapping.get(module_name) or f"{module_name.title()}Module"
            
            if not hasattr(module, class_name):
                self.logger.error(f"Module {module_path} missing class: {class_name}")
                return False

            # Initialize module
            module_class = getattr(module, class_name)
            module_instance = module_class()
            
            # Merge configs might not be handling all required configuration properly
            config = self._load_module_config(module_name)
            if base_config:
                config.update(base_config)

            # Initialize with config
            if not module_instance.initialize(config):
                self.logger.error(f"Failed to initialize {module_name}")
                return False
                
            self.modules[module_name] = module_instance
            self.module_configs[module_name] = config
            self._module_states[module_name] = True
            
            self.logger.info(f"Successfully loaded module: {module_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error loading {module_name}: {str(e)}")
            self._module_states[module_name] = False
            return False
            
    def _load_module_config(self, module_name: str) -> Dict[str, Any]:
        try:
            config = {}
            config_path = Path(__file__).parent.parent / 'config' / f'{module_name}_config.py'
            
            if config_path.exists():
                spec = importlib.util.spec_from_file_location(f"{module_name}_config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                config = {k: v for k, v in inspect.getmembers(config_module)
                         if not k.startswith('_')}
                
            # Ensure required base config
            config.setdefault('enabled', True)
            config.setdefault('debug', self.settings.DEBUG)
            return config
            
        except Exception as e:
            self.logger.warning(f"Error loading config for {module_name}: {str(e)}")
            return {'enabled': False}
            
    def get_module(self, module_name: str) -> Optional[ModuleInterface]:
        """Get a loaded module by name"""
        return self.modules.get(module_name)
        
    def process_input(self, module_name: str, input_data: Any,
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input through a specific module with context tracking"""
        try:
            module = self.get_module(module_name)
            if not module:
                raise KeyError(f"Module {module_name} not loaded")

            # Check module state
            module_state = self.context.get_module_state(module_name)
            if not module_state or not module_state.is_active:
                raise RuntimeError(f"Module {module_name} is not in ready state")

            # Track command
            self.context.update_module_state(
                module_name,
                is_active=True,
                command=str(input_data)
            )

            # Process command
            response = module.process(input_data, context)

            # Update state with response
            self.context.update_module_state(
                module_name,
                is_active=True,
                response=response
            )

            return response

        except Exception as e:
            self.logger.error(f"Error processing through module {module_name}: {str(e)}")
            error_response = {
                "success": False,
                "error": str(e),
                "module": module_name
            }
            self.context.update_module_state(
                module_name,
                is_active=False,
                response=error_response
            )
            return error_response
            
    def shutdown_module(self, module_name: str) -> bool:
        """Gracefully shutdown a module"""
        try:
            module = self.get_module(module_name)
            if module:
                module.shutdown()
                self.modules.pop(module_name)
                self._module_states.pop(module_name)
                self.logger.info(f"Successfully shut down module: {module_name}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error shutting down module {module_name}: {str(e)}")
            return False
            
    def shutdown_all(self) -> None:
        """Shutdown all modules gracefully"""
        for module_name in list(self.modules.keys()):
            self.shutdown_module(module_name)