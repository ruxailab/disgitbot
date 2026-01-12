"""
Centralized logging configuration for the PR Review System
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    name: str = "pr_review",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Default format
    if format_string is None:
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
    
    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return get_logger(name)


# Context manager for temporary log level changes
class LogLevel:
    """Context manager for temporarily changing log level"""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)
        return False
