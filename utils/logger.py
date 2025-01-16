import logging
import logging.handlers
import os
import json
import threading
import datetime
from typing import Optional, Dict, Union
from functools import lru_cache
from config.settings import Settings

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
    env: str = 'development'
) -> logging.Logger:
    """
    Set up and return a logger instance with enhanced features
    
    Args:
        name: Logger name
        log_format: 'standard' or 'json'
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        env: Environment ('development', 'production', 'testing')
    
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
            
        logger.setLevel(Settings.LOG_LEVEL)
        
        # Validate and create log directory
        if not os.path.isabs(Settings.LOG_DIR):
            raise LoggerError("LOG_DIR must be an absolute path")
        os.makedirs(Settings.LOG_DIR, exist_ok=True)
        
        # Create handlers with rotation
        handlers = []
        
        # Main log file handler
        main_log_path = os.path.join(Settings.LOG_DIR, f"rowan_{env}.log")
        fh = logging.handlers.RotatingFileHandler(
            main_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handlers.append(fh)
        
        # Error log file handler
        error_log_path = os.path.join(Settings.LOG_DIR, f"rowan_error_{env}.log")
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
            handler.setLevel(Settings.LOG_LEVEL)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
        
    except Exception as e:
        raise LoggerError(f"Failed to setup logger: {str(e)}") from e

def get_performance_logger(name: str) -> logging.Logger:
    """Get a specialized logger for performance metrics"""
    logger = setup_logger(f"{name}_performance", log_format='json')
    return logger