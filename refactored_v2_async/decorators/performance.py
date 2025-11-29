import asyncio
import time
import logging
from functools import wraps, lru_cache
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


def measure_time(threshold_seconds: float = None):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            if threshold_seconds and elapsed > threshold_seconds:
                logger.warning(
                    f"'{func.__name__}' took {elapsed:.2f}s "
                    f"(threshold: {threshold_seconds}s)"
                )
            else:
                logger.debug(f"'{func.__name__}' took {elapsed:.2f}s")

            return result

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            if threshold_seconds and elapsed > threshold_seconds:
                logger.warning(
                    f"'{func.__name__}' took {elapsed:.2f}s "
                    f"(threshold: {threshold_seconds}s)"
                )
            else:
                logger.debug(f"'{func.__name__}' took {elapsed:.2f}s")

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_result(maxsize: int = 128, typed: bool = False):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            logger.warning(
                f"cache_result doesn't support async functions. "
                f"'{func.__name__}' will not be cached. "
                f"Consider using aiocache or similar."
            )
            return func

        cached_func = lru_cache(maxsize=maxsize, typed=typed)(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = cached_func(*args, **kwargs)

            cache_info = cached_func.cache_info()
            if cache_info.hits > 0:
                hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses) * 100
                logger.debug(
                    f"'{func.__name__}' cache: "
                    f"hits={cache_info.hits}, misses={cache_info.misses}, "
                    f"hit_rate={hit_rate:.1f}%"
                )

            return result

        wrapper.cache_clear = cached_func.cache_clear
        wrapper.cache_info = cached_func.cache_info

        return wrapper

    return decorator
