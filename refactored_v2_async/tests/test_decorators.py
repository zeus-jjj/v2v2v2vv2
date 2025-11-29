import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import logging

from decorators import (
    async_retry,
    log_execution,
    log_errors,
    validate_input,
    validate_output,
    measure_time,
    cache_result
)
from pydantic import BaseModel, ValidationError


class TestAsyncRetryDecorator:

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        mock_func = AsyncMock(return_value="success")
        decorated = async_retry(max_attempts=3)(mock_func)

        result = await decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        mock_func = AsyncMock(side_effect=[
            ValueError("Error 1"),
            ValueError("Error 2"),
            "success"
        ])

        decorated = async_retry(max_attempts=3, exceptions=(ValueError,))(mock_func)

        result = await decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self):
        mock_func = AsyncMock(side_effect=ValueError("Error"))
        decorated = async_retry(max_attempts=3, exceptions=(ValueError,))(mock_func)

        with pytest.raises(ValueError):
            await decorated()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_only_catches_specified_exceptions(self):
        mock_func = AsyncMock(side_effect=TypeError("Wrong error"))
        decorated = async_retry(max_attempts=3, exceptions=(ValueError,))(mock_func)

        with pytest.raises(TypeError):
            await decorated()

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        mock_func = AsyncMock(side_effect=[
            ValueError("Error"),
            ValueError("Error"),
            "success"
        ])

        decorated = async_retry(
            max_attempts=3,
            base_delay=0.01,
            exponential_base=2.0,
            exceptions=(ValueError,)
        )(mock_func)

        import time
        start = time.time()
        result = await decorated()
        elapsed = time.time() - start

        assert elapsed > 0.01
        assert result == "success"


class TestLoggingDecorators:

    @pytest.mark.asyncio
    async def test_log_execution_async(self, caplog):
        @log_execution(level=logging.INFO)
        async def test_func():
            return "result"

        with caplog.at_level(logging.INFO):
            result = await test_func()

        assert result == "result"
        assert "Executing 'test_func'" in caplog.text
        assert "completed successfully" in caplog.text


class TestPerformanceDecorators:

    @pytest.mark.asyncio
    async def test_measure_time_under_threshold_async(self, caplog):
        @measure_time(threshold_seconds=1.0)
        async def test_func():
            return "done"

        with caplog.at_level(logging.DEBUG):
            result = await test_func()

        assert result == "done"

    def test_cache_result(self):
        call_count = 0

        @cache_result(maxsize=128)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        result2 = expensive_func(5)
        assert result2 == 10
        assert call_count == 1

        result3 = expensive_func(10)
        assert result3 == 20
        assert call_count == 2

    def test_cache_result_cache_info(self):
        @cache_result(maxsize=128)
        def test_func(x):
            return x * 2

        test_func(1)
        test_func(1)
        test_func(2)

        cache_info = test_func.cache_info()
        assert cache_info.hits == 1
        assert cache_info.misses == 2

    def test_cache_result_clear(self):
        @cache_result(maxsize=128)
        def test_func(x):
            return x * 2

        result1 = test_func(5)
        assert result1 == 10

        test_func.cache_clear()

        cache_info = test_func.cache_info()
        assert cache_info.hits == 0
        assert cache_info.misses == 0


class TestValidationDecorators:

    def test_validate_input_success(self):
        class InputModel(BaseModel):
            name: str
            age: int

        @validate_input(InputModel)
        def test_func(data):
            return data.name

        result = test_func({"name": "John", "age": 30})
        assert result == "John"

    def test_validate_input_failure(self):
        class InputModel(BaseModel):
            name: str
            age: int

        @validate_input(InputModel)
        def test_func(data):
            return data.name

        with pytest.raises(ValidationError):
            test_func({"name": "John", "age": "invalid"})

    def test_validate_output_success(self):
        class OutputModel(BaseModel):
            result: str
            count: int

        @validate_output(OutputModel)
        def test_func():
            return {"result": "success", "count": 5}

        result = test_func()
        assert result.result == "success"
        assert result.count == 5

    def test_validate_output_failure(self):
        class OutputModel(BaseModel):
            result: str
            count: int

        @validate_output(OutputModel)
        def test_func():
            return {"result": "success", "count": "invalid"}

        with pytest.raises(ValidationError):
            test_func()
