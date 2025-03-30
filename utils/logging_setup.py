"""
Configures logging for the YouTube Shorts Automation System.
Includes console and file logging with different levels and formatting.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
import datetime

def setup_logging(log_dir="logs", debug=False):
    """
    Set up logging configuration for both console and file output.
    
    Args:
        log_dir (str): Directory to store log files
        debug (bool): Whether to set logging level to DEBUG
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Determine log level based on debug flag
    console_level = logging.DEBUG if debug else logging.INFO
    file_level = logging.DEBUG  # Always log debug to file
    
    # Generate log filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"shorts_automation_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all logs
    
    # Remove existing handlers if any
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with rich formatting
    console_handler = RichHandler(level=console_level, rich_tracebacks=True, 
                                 omit_repeated_times=False, show_path=True)
    console_format = "%(message)s"
    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with detailed formatting
    file_handler = RotatingFileHandler(
        log_filename, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(file_level)
    file_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    file_formatter = logging.Formatter(file_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Create separate error log
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, f"shorts_automation_errors_{timestamp}.log"),
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Log startup message
    root_logger.info(f"Logging initialized. Log file: {log_filename}")
    if debug:
        root_logger.info("Debug mode enabled")
    
    return root_logger