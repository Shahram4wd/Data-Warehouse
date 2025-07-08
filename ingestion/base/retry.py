"""
Retry mechanisms for sync operations
"""
import time
import logging
import random
from typing import Callable, Any, Optional, Type, Union
from functools import wraps
from ingestion.base.exceptions import (
    RetryableException, RateLimitException, APIException, SyncException
)

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry mechanisms"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            RetryableException,
            RateLimitException,
            APIException
        )

def exponential_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay"""
    delay = config.initial_delay * (config.backoff_factor ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add jitter to prevent thundering herd
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay

def retry_with_backoff(
    config: RetryConfig = None,
    on_retry: Callable[[Exception, int], None] = None
):
    """
    Decorator for retrying operations with exponential backoff
    
    Args:
        config: RetryConfig instance
        on_retry: Callback function called on each retry attempt
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if this is the last attempt
                    if attempt == config.max_retries:
                        logger.error(f"Max retries ({config.max_retries}) exceeded for {func.__name__}")
                        raise
                    
                    # Check if exception is retryable
                    if not isinstance(e, config.retryable_exceptions):
                        logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                        raise
                    
                    # Handle rate limiting
                    if isinstance(e, RateLimitException) and e.retry_after:
                        delay = e.retry_after
                        logger.warning(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}")
                    else:
                        delay = exponential_backoff(attempt, config)
                        logger.warning(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {attempt + 1}/{config.max_retries})")
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    time.sleep(delay)
            
            # This shouldn't be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

class RetryableOperation:
    """Class for managing retryable operations"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
    
    def execute(
        self,
        operation: Callable,
        *args,
        on_retry: Callable[[Exception, int], None] = None,
        **kwargs
    ):
        """
        Execute an operation with retry logic
        
        Args:
            operation: Function to execute
            *args: Positional arguments for the operation
            on_retry: Callback function called on each retry attempt
            **kwargs: Keyword arguments for the operation
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if this is the last attempt
                if attempt == self.config.max_retries:
                    self.logger.error(f"Max retries ({self.config.max_retries}) exceeded")
                    raise
                
                # Check if exception is retryable
                if not isinstance(e, self.config.retryable_exceptions):
                    self.logger.error(f"Non-retryable exception: {e}")
                    raise
                
                # Handle rate limiting
                if isinstance(e, RateLimitException) and e.retry_after:
                    delay = e.retry_after
                    self.logger.warning(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}")
                else:
                    delay = exponential_backoff(attempt, self.config)
                    self.logger.warning(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{self.config.max_retries})")
                
                # Call retry callback if provided
                if on_retry:
                    on_retry(e, attempt + 1)
                
                time.sleep(delay)
        
        # This shouldn't be reached, but just in case
        raise last_exception

# Convenience functions for common retry patterns
def retry_api_call(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for API calls with standard retry logic"""
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        retryable_exceptions=(APIException, RateLimitException)
    )
    return retry_with_backoff(config)

def retry_database_operation(max_retries: int = 2, initial_delay: float = 0.5):
    """Decorator for database operations with retry logic"""
    from ingestion.base.exceptions import DatabaseException
    
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        retryable_exceptions=(DatabaseException,)
    )
    return retry_with_backoff(config)

def retry_bulk_operation(max_retries: int = 1, initial_delay: float = 2.0):
    """Decorator for bulk operations with retry logic"""
    from ingestion.base.exceptions import BulkOperationException
    
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        retryable_exceptions=(BulkOperationException, APIException)
    )
    return retry_with_backoff(config)
