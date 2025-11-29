import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


def log_execution(level: int = logging.INFO):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = func.__name__
            logger.log(level, f"Executing '{func_name}'...")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"'{func_name}' completed successfully")
                return result
            except Exception as e:
                logger.log(level, f"'{func_name}' failed with error: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = func.__name__
            logger.log(level, f"Executing '{func_name}'...")
            try:
                result = func(*args, **kwargs)


                if asyncio.iscoroutine(result):
                    result.close()
                    raise TypeError(
                        f"Async function '{func_name}' was called without await. "
                        "Use 'await {func_name}()' or ensure it's decorated correctly."
                    )

                logger.log(level, f"'{func_name}' completed successfully")
                return result
            except Exception as e:
                logger.log(level, f"'{func_name}' failed with error: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_errors(level: int = logging.ERROR, reraise: bool = True):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.log(
                    level,
                    f"Error in '{func.__name__}': {e}",
                    exc_info=True
                )
                if reraise:
                    raise
                return None

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log(
                    level,
                    f"Error in '{func.__name__}': {e}",
                    exc_info=True
                )
                if reraise:
                    raise
                return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
