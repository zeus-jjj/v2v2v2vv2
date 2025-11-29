
import asyncio
import random
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable = None
):

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        logger.error(
                            f"'{func.__name__}' failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    delay = base_delay * (exponential_base ** (attempt - 1)) + random.uniform(0, 0.5)

                    logger.warning(
                        f"'{func.__name__}' failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {delay:.2f}s... Error: {e}"
                    )

                    if on_retry:
                        on_retry(attempt, delay, e)

                    await asyncio.sleep(delay)

            return None

        return wrapper
    return decorator
