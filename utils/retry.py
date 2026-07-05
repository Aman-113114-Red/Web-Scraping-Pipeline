"""
Retry Utility
=============
Provides a configurable retry decorator with exponential back-off.

Usage
-----
    from utils.retry import retry

    @retry(max_retries=3, delay=2)
    def unreliable_call():
        ...
"""

import time
import functools
from typing import Any, Callable, Optional, Tuple, Type

from utils.logger import get_logger

logger = get_logger(__name__)


def retry(
    max_retries: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """
    Decorator that retries a function on failure with exponential back-off.

    Parameters
    ----------
    max_retries : int, optional
        Maximum number of retry attempts. Defaults to ``Settings.MAX_RETRIES``.
    delay : float, optional
        Initial delay between retries in seconds. Defaults to ``Settings.RETRY_DELAY``.
    backoff_factor : float
        Multiplier applied to the delay after each retry.
    exceptions : tuple
        Tuple of exception types that should trigger a retry.

    Returns
    -------
    Callable
        Decorated function with retry logic.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular import at module level
            from config.settings import Settings

            _max_retries = max_retries if max_retries is not None else Settings.MAX_RETRIES
            _delay = delay if delay is not None else Settings.RETRY_DELAY
            current_delay = _delay

            last_exception: Optional[BaseException] = None

            for attempt in range(1, _max_retries + 2):  # +1 for the initial attempt
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt <= _max_retries:
                        logger.warning(
                            "Attempt %d/%d for %s failed: %s — retrying in %.1fs",
                            attempt,
                            _max_retries + 1,
                            func.__name__,
                            str(exc),
                            current_delay,
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            "All %d attempts for %s exhausted. Last error: %s",
                            _max_retries + 1,
                            func.__name__,
                            str(exc),
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator
