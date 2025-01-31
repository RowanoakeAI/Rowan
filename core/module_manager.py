from typing import Dict, Any, Optional, List
import importlib
import inspect
import time
from utils.logger import setup_logger
from config.settings import Settings
from context.context import Context
from .heartbeat_manager import HeartbeatManager
from .module_interface import ModuleInterface
from modules.notifications import NotificationsModule
from modules.skills.calendar_skill import GoogleCalendarSkill
from config.email_config import EmailConfig

class ModuleManager:
    """Manages loading and lifecycle of Rowan modules"""
    
    MODULE_PATHS = {
        "calendar": "skills.calendar_skill",
        "discord": "discord.discord_module",
        "conversation": "conversation.conversation_module", 
        "spotify": "skills.spotify",
        "system": "skills.system_monitor",
        "notifications": "notifications.notification_module"
    }
    
    DEPENDENCIES = {
        "calendar": ["notifications"],
        "email": ["notifications"]
    }
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.settings = Settings()
        self.modules: Dict[str, ModuleInterface] = {}
        self.heartbeat_manager = HeartbeatManager()

    def initialize(self) -> bool:
        """Initialize all modules with proper configuration"""
        try:
            # Load settings first
            from config.settings import Settings
            
            # Initialize notifications module first
            self.notification_module = NotificationsModule()
            if not self.notification_module.initialize({}):
                self.logger.error("Failed to initialize notifications module")
                return False

            # Initialize calendar module with config
            calendar_config = {
                'calendar': Settings.get_calendar_config(),
                'notification_module': self.notification_module
            }
            
            self.calendar_module = GoogleCalendarSkill()
            if not self.calendar_module.initialize(calendar_config):
                self.logger.error("Failed to initialize calendar module")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Critical error during module initialization: {str(e)}")
            return False

    def load_module(self, module_name: str, config: Dict[str, Any] = None) -> bool:
        """Load a single module with configuration"""
        try:
            if module_name == 'calendar':
                if not config:
                    from config.settings import Settings
                    config = {
                        'calendar': Settings.get_calendar_config(),
                        'notification_module': self.notification_module
                    }
                return self.calendar_module.initialize(config)
            return False
            
        except Exception as e:
            self.logger.error(f"Error loading {module_name}: {str(e)}")
            return False

    def _check_dependencies(self, module_name: str) -> None:
        """Verify module dependencies are loaded"""
        deps = self.DEPENDENCIES.get(module_name, [])
        for dep in deps:
            if dep not in self.modules:
                raise RuntimeError(f"{module_name} requires {dep} module to be loaded first")

    def _import_module(self, module_path: str) -> Optional[ModuleInterface]:
        """Import and instantiate a module class"""
        try:
            module = importlib.import_module(f"modules.{module_path}")
            for _, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, ModuleInterface) and 
                    obj != ModuleInterface):
                    return obj()
        except Exception as e:
            self.logger.error(f"Error importing module {module_path}: {e}")
        return None

    def _get_dependency_order(self) -> List[str]:
        """Get modules in dependency order"""
        ordered = []
        seen = set()
        
        def process_module(name: str):
            if name in seen:
                return
            seen.add(name)
            for dep in self.DEPENDENCIES.get(name, []):
                process_module(dep)
            ordered.append(name)
            
        for module in self.MODULE_PATHS:
            process_module(module)
            
        return ordered

    def shutdown(self) -> bool:
        """Shutdown all modules in reverse dependency order"""
        try:
            # Get modules in reverse dependency order
            shutdown_order = list(reversed(self._get_dependency_order()))
            self.logger.info(f"Shutting down modules in order: {shutdown_order}")
            
            success = True
            start_time = time.time()
            
            # Stop all heartbeats first
            self.heartbeat_manager.stop_all()
            
            # Shutdown modules
            for module_name in shutdown_order:
                if module_name in self.modules:
                    try:
                        module = self.modules[module_name]
                        
                        # Check timeout
                        if time.time() - start_time > self.SHUTDOWN_TIMEOUT:
                            self.logger.error("Module shutdown timeout exceeded")
                            return False
                            
                        # Shutdown module
                        if module.shutdown():
                            self._shutdown_states[module_name] = True
                            self.logger.info(f"Successfully shutdown {module_name}")
                        else:
                            success = False
                            self.logger.error(f"Failed to shutdown {module_name}")
                            
                    except Exception as e:
                        success = False
                        self.logger.error(f"Error during {module_name} shutdown: {e}")
                        
            return success
            
        except Exception as e:
            self.logger.error(f"Critical error during shutdown: {e}")
            return False
        finally:
            # Clear module references
            self.modules.clear()
            self._module_states.clear()
            self._shutdown_states.clear()

class EmailModule(ModuleInterface):
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.notification_module = None
        self.imap = None 
        self.smtp = None
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            if not isinstance(config, dict):
                raise TypeError("Config must be dictionary")
                
            # Store notification module reference
            self.notification_module = config.get('notification_module')
            if not self.notification_module:
                raise ValueError("Notification module required")
                
            # Initialize email configs
            email_config = EmailConfig()
            if not email_config.validate():
                raise ValueError("Invalid email configuration")
                
            # Setup connections
            self._setup_connections(email_config)
            
            self.initialized = True
            self.logger.info("Email module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize email: {e}")
            return False

    def shutdown(self) -> bool:
        """Clean shutdown of email module"""
        try:
            if self.notification_module:
                self.notification_module.stop()
            if self.imap:
                self.imap.logout()
            if self.smtp:
                self.smtp.quit()
            return True
        except Exception as e:
            self.logger.error(f"Error during email module shutdown: {e}")
            return False

class CalendarModule(ModuleInterface):
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.client_id = None
        self.client_secret = None
        self.scopes = None
        self.credentials_file = None
        self.token_file = None
        self.notification_module = None
        self.default_reminder_times = None
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize calendar integration with improved error handling"""
        try:
            if not config:
                self.logger.error("No configuration provided")
                return False
                
            # Get calendar config
            calendar_config = Settings.get_calendar_config()
            
            # Set up configuration
            self.client_id = calendar_config.client_id
            self.client_secret = calendar_config.client_secret
            self.scopes = calendar_config.scopes
            self.credentials_file = calendar_config.credentials_file
            self.token_file = calendar_config.token_file
            
            # Set up notifications if enabled
            if calendar_config.notification_enabled:
                self.notification_module = config.get('notification_module')
                self.default_reminder_times = calendar_config.default_reminder_times
            
            # Initialize authentication
            self._authenticate()
            
            # Mark as initialized
            self.initialized = True
            self.logger.info("Calendar module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize calendar: {str(e)}")
            return False

    def _authenticate(self):
        """Authenticate with the calendar service"""
        # Authentication logic here
        pass

    def shutdown(self) -> bool:
        """Clean shutdown of calendar module"""
        try:
            if self.notification_module:
                self.notification_module.stop()
            return True
        except Exception as e:
            self.logger.error(f"Error during calendar module shutdown: {e}")
            return False

# Initialize manager singleton
module_manager = ModuleManager()

# Initialize modules 
if not module_manager.initialize():
    module_manager.logger.error("Failed to initialize module system")