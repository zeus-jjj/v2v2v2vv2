import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from decorators import (
    log_execution,
    log_errors,
    measure_time,
    cache_result,
    validate_input,
    validate_output
)
from pydantic import BaseModel


class TestAsyncLoggingDecorators:

    @pytest.mark.asyncio
    async def test_log_execution_async_function(self, caplog):
        executed = False

        @log_execution()
        async def async_func():
            nonlocal executed
            await asyncio.sleep(0.01)
            executed = True
            return "result"

        result = await async_func()

        assert result == "result"
        assert executed is True
        assert "Executing 'async_func'" in caplog.text
        assert "completed successfully" in caplog.text

    @pytest.mark.asyncio
    async def test_log_errors_async_catches_exceptions(self, caplog):

        @log_errors(reraise=True)
        async def failing_async():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_async()

        assert "Error in 'failing_async'" in caplog.text

    def test_log_execution_sync_function(self, caplog):

        @log_execution()
        def sync_func():
            return "sync result"

        result = sync_func()

        assert result == "sync result"
        assert "Executing 'sync_func'" in caplog.text


class TestAsyncPerformanceDecorators:

    @pytest.mark.asyncio
    async def test_measure_time_async_measures_actual_execution(self, caplog):

        @measure_time()
        async def slow_async():
            await asyncio.sleep(0.1)
            return "done"

        start = time.time()
        result = await slow_async()
        elapsed = time.time() - start

        assert result == "done"
        assert elapsed >= 0.1
        assert "took" in caplog.text

    @pytest.mark.asyncio
    async def test_measure_time_async_threshold_warning(self, caplog):

        @measure_time(threshold_seconds=0.01)
        async def very_slow_async():
            await asyncio.sleep(0.05)
            return "done"

        await very_slow_async()

        assert "threshold" in caplog.text

    def test_cache_result_sync_function(self):
        call_count = 0

        @cache_result(maxsize=128)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_result_warns_on_async(self, caplog):

        @cache_result()
        async def async_func(x):
            return x * 2

        result = await async_func(5)

        assert result == 10
        assert "doesn't support async" in caplog.text


class TestAsyncValidationDecorators:

    @pytest.mark.asyncio
    async def test_validate_input_async_function(self):

        class InputModel(BaseModel):
            name: str
            age: int

        @validate_input(InputModel)
        async def process_user(data):
            await asyncio.sleep(0.01)
            return data.name

        result = await process_user({"name": "John", "age": 30})

        assert result == "John"

    @pytest.mark.asyncio
    async def test_validate_output_async_function(self):

        class OutputModel(BaseModel):
            result: str
            count: int

        @validate_output(OutputModel)
        async def get_data():
            await asyncio.sleep(0.01)
            return {"result": "success", "count": 5}

        result = await get_data()

        assert result.result == "success"
        assert result.count == 5

    def test_validate_input_sync_function(self):

        class InputModel(BaseModel):
            value: int

        @validate_input(InputModel)
        def process_value(data):
            return data.value * 2

        result = process_value({"value": 10})

        assert result == 20


class TestDecoratorStackingAsync:

    @pytest.mark.asyncio
    async def test_multiple_decorators_on_async_function(self, caplog):

        @measure_time()
        @log_execution()
        @log_errors()
        async def complex_async_func():
            await asyncio.sleep(0.01)
            return "result"

        result = await complex_async_func()

        assert result == "result"
        assert "Executing" in caplog.text
        assert "took" in caplog.text

    @pytest.mark.asyncio
    async def test_decorators_preserve_async_behavior(self):

        @log_execution()
        @measure_time()
        async def concurrent_task(n):
            await asyncio.sleep(0.01)
            return n * 2

        results = await asyncio.gather(
            concurrent_task(1),
            concurrent_task(2),
            concurrent_task(3)
        )

        assert results == [2, 4, 6]
