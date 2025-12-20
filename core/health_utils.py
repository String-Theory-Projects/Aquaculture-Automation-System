"""
Health check utility functions for retry logic and timeout protection.

This module provides shared utilities for:
- Retry logic with exponential backoff
- Timeout protection for health checks
- Status code determination (503 vs 500)
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class HealthCheckTimeoutError(Exception):
    """Custom timeout error for health checks"""
    pass


def with_timeout(timeout_seconds: float = 2.0):
    """
    Decorator to add timeout protection to health check functions.
    
    Uses threading-based timeout which works in any thread context,
    not just the main thread (unlike signal-based timeouts).
    
    Args:
        timeout_seconds: Maximum time to wait for the function to complete
    
    Returns:
        Decorated function that raises HealthCheckTimeoutError if it takes too long
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Always use threading-based timeout (works in any thread context)
            # Signal-based timeouts only work in the main thread
            import threading
            result_container = [None]
            exception_container = [None]
            
            def target():
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    exception_container[0] = e
            
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)
            
            if thread.is_alive():
                raise HealthCheckTimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            
            if exception_container[0]:
                raise exception_container[0]
            
            return result_container[0]
        
        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable,
    max_retries: int = 4,
    initial_delay: float = 1.0,
    max_delay: float = 8.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
    log_errors: bool = True
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts (default: 4)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 8.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        exceptions: Tuple of exceptions to catch and retry on
        log_errors: Whether to log retry attempts (default: True)
    
    Returns:
        Result of the function call
    
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                if log_errors:
                    logger.warning(
                        f'Retry attempt {attempt + 1}/{max_retries} after {delay:.1f}s: {str(e)}'
                    )
                time.sleep(delay)
                delay = min(delay * backoff_multiplier, max_delay)
            else:
                if log_errors:
                    logger.error(f'All {max_retries + 1} retry attempts failed: {str(e)}')
    
    # All retries exhausted, raise last exception
    if last_exception is not None:
        raise last_exception
    raise Exception("All retries failed but no exception was captured")


def write_heartbeat_with_retry(
    write_func: Callable[[], None],
    service_name: str = "service"
) -> bool:
    """
    Write heartbeat to Redis with retry logic and exponential backoff.
    
    Args:
        write_func: Function that writes the heartbeat (should raise exception on failure)
        service_name: Name of the service for logging
    
    Returns:
        True if heartbeat was written successfully, False otherwise
    """
    try:
        retry_with_backoff(
            func=write_func,
            max_retries=4,
            initial_delay=1.0,
            max_delay=8.0,
            backoff_multiplier=2.0,
            exceptions=(Exception,),
            log_errors=True
        )
        return True
    except Exception as e:
        # Don't crash service if heartbeat write fails, just log
        logger.warning(f'[{service_name}] Failed to write heartbeat after retries: {e}')
        return False


def check_health_with_timeout(
    check_func: Callable[[], Dict[str, Any]],
    timeout_seconds: float = 2.0,
    default_status: str = 'unknown'
) -> Dict[str, Any]:
    """
    Execute a health check function with timeout protection.
    
    Args:
        check_func: Function that performs the health check
        timeout_seconds: Maximum time to wait (default: 2.0)
        default_status: Status to return if check times out (default: 'unknown')
    
    Returns:
        Health check result dictionary with status and optional error message
    """
    try:
        # Use timeout decorator
        @with_timeout(timeout_seconds)
        def timed_check():
            return check_func()
        
        result = timed_check()
        # Ensure result has timeout flag
        if isinstance(result, dict):
            result['timeout'] = False
        return result
    except HealthCheckTimeoutError:
        logger.warning(f'Health check timed out after {timeout_seconds}s')
        return {
            'status': default_status,
            'error': f'Health check timed out after {timeout_seconds}s',
            'timeout': True
        }
    except Exception as e:
        logger.error(f'Health check error: {e}')
        return {
            'status': default_status,
            'error': str(e),
            'timeout': False
        }


def determine_health_status_code(
    checks: Dict[str, Dict[str, Any]],
    critical_checks: Optional[list] = None
) -> tuple[int, str]:
    """
    Determine HTTP status code and overall health status based on check results.
    
    Args:
        checks: Dictionary of check results, each with a 'status' key
        critical_checks: List of check names that are critical (default: None = all checks)
    
    Returns:
        Tuple of (http_status_code, overall_status)
        - 200: All checks healthy
        - 503: Non-critical failures (degraded but recoverable)
        - 500: Critical failures (system broken)
    """
    if critical_checks is None:
        # If not specified, all checks are considered critical
        critical_checks = list(checks.keys())
    
    all_healthy = True
    critical_failed = False
    
    for check_name, check_result in checks.items():
        status = check_result.get('status', 'unknown')
        
        if status != 'healthy':
            all_healthy = False
            
            if check_name in critical_checks:
                critical_failed = True
    
    if all_healthy:
        return 200, 'healthy'
    elif critical_failed:
        return 500, 'unhealthy'  # Critical failure
    else:
        return 503, 'degraded'  # Non-critical failure, degraded but functional
