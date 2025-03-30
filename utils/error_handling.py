"""
Error handling utilities for YouTube Shorts Automation System.
Provides decorators and functions for consistent error handling across modules.
"""
import logging
import functools
import time
import traceback
from typing import Callable, Optional, TypeVar, Any

# Type variables for generic function types
T = TypeVar('T')
R = TypeVar('R')

class AutomationError(Exception):
    """Base exception class for automation system errors."""
    pass

class APIError(AutomationError):
    """Exception for errors related to external API calls."""
    pass

class ConfigError(AutomationError):
    """Exception for configuration-related errors."""
    pass

class ContentError(AutomationError):
    """Exception for content generation errors."""
    pass

class MediaError(AutomationError):
    """Exception for media processing errors."""
    pass

class WorkflowError(AutomationError):
    """Exception for workflow execution errors."""
    pass

def retry(
    max_tries: int = 3, 
    delay: float = 1.0, 
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_tries: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier e.g. value of 2 will double the delay each retry
        exceptions: Tuple of exceptions to catch and retry on
        logger: Logger to use. If None, gets logger with function's module name
        
    Returns:
        Decorated function that will retry on specified exceptions
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            # Get logger if not provided
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # Initialize variables
            mtries, mdelay = max_tries, delay
            
            # Try calling the function
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    msg = f"{str(e)}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    
                    # Capture traceback for debugging
                    logger.debug(f"Exception traceback: {traceback.format_exc()}")
                    
                    # Wait and update counters
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            
            # Last attempt
            return func(*args, **kwargs)
        return wrapper
    return decorator

def safe_execute(
    fallback_return: Optional[T] = None,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    Decorator to safely execute a function, catching exceptions and returning a fallback value.
    
    Args:
        fallback_return: Value to return if an exception occurs
        exceptions: Tuple of exceptions to catch
        logger: Logger to use. If None, gets logger with function's module name
        
    Returns:
        Decorated function that won't raise specified exceptions
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            # Get logger if not provided
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                logger.debug(f"Exception traceback: {traceback.format_exc()}")
                return fallback_return
        return wrapper
    return decorator

def log_execution_time(
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: Logger to use. If None, gets logger with function's module name
        
    Returns:
        Decorated function that logs its execution time
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get logger if not provided
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            logger.debug(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
            return result
        return wrapper
    return decorator