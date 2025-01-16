import psutil
import platform
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import re
from core.module_manager import ModuleInterface
from utils.logger import setup_logger

class SystemMonitorSkill(ModuleInterface):
    """System monitoring and resource tracking module"""

    COMMAND_PATTERNS = {
        "cpu": r"(?:check |show |get |what'?s? |how'?s? |)(?:cpu|processor|processing|compute).*?(?:usage|load|status)",
        "memory": r"(?:check |show |get |what'?s? |how'?s? |)(?:memory|ram|mem).*?(?:usage|status|available|used)",
        "disk": r"(?:check |show |get |what'?s? |how'?s? |)(?:disk|storage|drive).*?(?:space|usage|status|available|used)",
        "all": r"(?:check |show |get |what'?s? |how'?s? |)(?:system|everything|all).*?(?:status|health|resources|overview)"
    }

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)
        self.initialized = False
        self.command_handlers = {
            "cpu": self._handle_cpu,
            "memory": self._handle_memory,
            "disk": self._handle_disk,
            "all": self._handle_all
        }

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize system monitor"""
        try:
            self.logger.info("System monitor initialized successfully")
            self.initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize system monitor: {str(e)}")
            return False

    def _parse_command(self, input_text: str) -> Tuple[Optional[str], str]:
        """Parse input text to determine command and parameters"""
        input_lower = input_text.lower()
        
        for cmd, pattern in self.COMMAND_PATTERNS.items():
            if re.search(pattern, input_lower):
                return cmd, input_text
        
        return None, input_text

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU usage information"""
        return {
            "percent": psutil.cpu_percent(interval=1),
            "cores": psutil.cpu_count(),
            "freq": psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else None
        }

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information"""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent
        }

    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage information"""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "free": disk.free,
            "used": disk.used,
            "percent": disk.percent
        }

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes into human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"

    def _handle_cpu(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CPU status check"""
        try:
            cpu = self._get_cpu_info()
            response = (f"CPU Usage: {cpu['percent']}%\n"
                      f"Cores: {cpu['cores']}\n")
            if cpu['freq']:
                response += f"Frequency: {cpu['freq']/1000:.1f} GHz"
            
            return {"success": True, "response": response}
        except Exception as e:
            self.logger.error(f"Error checking CPU status: {str(e)}")
            return {"success": False, "response": "Unable to get CPU information"}

    def _handle_memory(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory status check"""
        try:
            mem = self._get_memory_info()
            response = (f"Memory Usage: {mem['percent']}%\n"
                      f"Total: {self._format_bytes(mem['total'])}\n"
                      f"Used: {self._format_bytes(mem['used'])}\n"
                      f"Available: {self._format_bytes(mem['available'])}")
            
            return {"success": True, "response": response}
        except Exception as e:
            self.logger.error(f"Error checking memory status: {str(e)}")
            return {"success": False, "response": "Unable to get memory information"}

    def _handle_disk(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disk status check"""
        try:
            disk = self._get_disk_info()
            response = (f"Disk Usage: {disk['percent']}%\n"
                      f"Total: {self._format_bytes(disk['total'])}\n"
                      f"Used: {self._format_bytes(disk['used'])}\n"
                      f"Free: {self._format_bytes(disk['free'])}")
            
            return {"success": True, "response": response}
        except Exception as e:
            self.logger.error(f"Error checking disk status: {str(e)}")
            return {"success": False, "response": "Unable to get disk information"}

    def _handle_all(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle full system status check"""
        try:
            cpu = self._get_cpu_info()
            mem = self._get_memory_info()
            disk = self._get_disk_info()
            
            response = (
                f"System Status Overview:\n\n"
                f"CPU:\n"
                f"- Usage: {cpu['percent']}%\n"
                f"- Cores: {cpu['cores']}\n\n"
                f"Memory:\n"
                f"- Usage: {mem['percent']}%\n"
                f"- Available: {self._format_bytes(mem['available'])}\n\n"
                f"Disk:\n"
                f"- Usage: {disk['percent']}%\n"
                f"- Free: {self._format_bytes(disk['free'])}"
            )
            
            return {"success": True, "response": response}
        except Exception as e:
            self.logger.error(f"Error checking system status: {str(e)}")
            return {"success": False, "response": "Unable to get system information"}

    def process(self, input_data: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process system monitor commands"""
        if not self.initialized:
            return {
                "success": False,
                "response": "System monitor not initialized properly"
            }

        try:
            command, params = self._parse_command(input_data)
            if not command:
                self.logger.warning(f"Invalid command format: {input_data}")
                return {
                    "success": False,
                    "response": "Invalid system monitor command format"
                }

            handler = self.command_handlers.get(command)
            if not handler:
                self.logger.warning(f"Unsupported command: {command}")
                return {
                    "success": False,
                    "response": "Unsupported system monitor operation"
                }

            self.logger.info(f"Processing system monitor command: {command}")
            return handler(params, context or {})

        except Exception as e:
            self.logger.error(f"Error processing system monitor command: {str(e)}")
            return {
                "success": False,
                "response": "Error processing system monitor request"
            }