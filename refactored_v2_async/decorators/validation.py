import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def validate_input(model: Type[BaseModel], param_name: str = None):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            if param_name:
                value = kwargs.get(param_name)
            else:
                value = args[0] if args else None

            if value is None:
                raise ValueError(f"No input to validate in '{func.__name__}'")

            try:
                validated = model(**value) if isinstance(value, dict) else model(*value)

                if param_name:
                    kwargs[param_name] = validated
                else:
                    args = (validated,) + args[1:]

            except ValidationError as e:
                logger.error(f"Validation error in '{func.__name__}': {e}")
                raise

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            if param_name:
                value = kwargs.get(param_name)
            else:
                value = args[0] if args else None

            if value is None:
                raise ValueError(f"No input to validate in '{func.__name__}'")

            try:
                validated = model(**value) if isinstance(value, dict) else model(*value)

                if param_name:
                    kwargs[param_name] = validated
                else:
                    args = (validated,) + args[1:]

            except ValidationError as e:
                logger.error(f"Validation error in '{func.__name__}': {e}")
                raise

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def validate_output(model: Type[BaseModel]):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> BaseModel:
            result = await func(*args, **kwargs)

            try:
                validated = model(**result) if isinstance(result, dict) else model(*result)
                return validated

            except ValidationError as e:
                logger.error(f"Output validation error in '{func.__name__}': {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> BaseModel:
            result = func(*args, **kwargs)

            try:
                validated = model(**result) if isinstance(result, dict) else model(*result)
                return validated

            except ValidationError as e:
                logger.error(f"Output validation error in '{func.__name__}': {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
