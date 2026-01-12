"""
Retry decorator and utilities for resilient API calls
"""

import time
import functools
import logging
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.RequestException,))
        def fetch_data():
            response = requests.get('https://api.example.com/data')
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {current_delay:.1f}s... Error: {str(e)}"
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Async version of retry decorator for async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated async function with retry logic
        
    Example:
        @retry_async(max_attempts=3, delay=1.0, exceptions=(aiohttp.ClientError,))
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.example.com/data') as response:
                    return await response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_attempts} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    logger.warning(
                        f"Async function {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {current_delay:.1f}s... Error: {str(e)}"
                    )
                    
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt, e)
                        else:
                            on_retry(attempt, e)
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker entering HALF_OPEN state for {func.__name__}")
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker recovered, state: CLOSED")
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout}s"
            )
