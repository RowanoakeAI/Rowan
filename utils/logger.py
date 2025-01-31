import logging
import logging.handlers
import os
import json
import threading
import datetime
from typing import Optional, Dict, Union
from functools import lru_cache

# Remove the config import that creates the circular dependency
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

class LoggerError(Exception):
    """Custom exception for logger related errors"""
    pass

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    def format(self, record):
        log_data = {
            'timestamp': datetime.datetime.fromtimestamp(record.created).isoformat(),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'process': record.process,
            'thread': record.thread,
            'thread_name': record.threadName
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

@lru_cache(maxsize=None)
def setup_logger(
    name: str,
    log_format: str = 'standard',
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    env: str = 'development',
    log_level: int = DEFAULT_LOG_LEVEL,
    log_dir: str = DEFAULT_LOG_DIR
) -> logging.Logger:
    """
    Set up and return a logger instance with enhanced features
    
    Args:
        name: Logger name
        log_format: 'standard' or 'json'
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        env: Environment ('development', 'production', 'testing')
        log_level: Logging level
        log_dir: Directory to store log files
    
    Returns:
        logging.Logger: Configured logger instance
    
    Raises:
        LoggerError: If logger configuration fails
    """
    if not name or not isinstance(name, str):
        raise LoggerError("Logger name must be a non-empty string")

    try:
        logger = logging.getLogger(name)
        
        if logger.handlers:
            return logger
            
        logger.setLevel(log_level)
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Create handlers
        handlers = []
        
        # Main log file handler
        main_log_path = os.path.join(log_dir, f"rowan_{env}.log")
        fh = logging.handlers.RotatingFileHandler(
            main_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handlers.append(fh)
        
        # Error log file handler
        error_log_path = os.path.join(log_dir, f"rowan_error_{env}.log")
        error_fh = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_fh.setLevel(logging.ERROR)
        handlers.append(error_fh)
        
        # Console handler
        ch = logging.StreamHandler()
        handlers.append(ch)
        
        # Set formatters
        if log_format.lower() == 'json':
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - [%(process)d:%(thread)d] - '
                '%(levelname)s - %(module)s - %(message)s'
            )
        
        # Configure handlers
        for handler in handlers:
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        logger.propagate = False
        
        return logger
        
    except Exception as e:
        raise LoggerError(f"Failed to setup logger: {str(e)}") from e

def get_performance_logger(name: str) -> logging.Logger:
    """Get a specialized logger for performance metrics"""
    logger = setup_logger(f"{name}_performance", log_format='json')
    return logger