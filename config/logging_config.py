# config/logging_config.py
import logging
import os
from utils.logger import DEFAULT_LOG_LEVEL, DEFAULT_LOG_DIR

class LoggingConfig:
    """Logging configuration settings"""
    LOG_LEVEL = DEFAULT_LOG_LEVEL
    LOG_DIR = DEFAULT_LOG_DIR