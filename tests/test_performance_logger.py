"""Tests for utils/performance_logger.py"""

import logging
import time

import pytest

from utils.performance_logger import PerformanceTimer, log_performance, log_performance_context


class TestPerformanceTimer:
    """Test PerformanceTimer class"""

    def test_manual_timing(self):
        """Test manual start/stop timing"""
        timer = PerformanceTimer("test_operation")
        timer.start()
        time.sleep(0.01)  # Small delay
        elapsed = timer.stop()

        assert elapsed >= 0.01
        assert timer.start_time is not None
        assert timer.end_time is not None

    def test_context_manager(self):
        """Test timer as context manager"""
        with PerformanceTimer("test_operation") as timer:
            time.sleep(0.01)

        assert timer.start_time is not None
        assert timer.end_time is not None

    def test_stop_without_start(self):
        """Test that stopping without starting raises error"""
        timer = PerformanceTimer("test_operation")
        with pytest.raises(RuntimeError, match="Timer was not started"):
            timer.stop()

    def test_custom_log_level(self):
        """Test timer with custom log level"""
        timer = PerformanceTimer("test_operation", log_level=logging.DEBUG)
        assert timer.log_level == logging.DEBUG
        timer.start()
        timer.stop()


class TestLogPerformanceDecorator:
    """Test log_performance decorator"""

    def test_basic_decorator(self):
        """Test basic decorator usage"""

        @log_performance("test_func")
        def sample_func():
            time.sleep(0.01)
            return "result"

        result = sample_func()
        assert result == "result"

    def test_decorator_with_default_name(self):
        """Test decorator using function name as default"""

        @log_performance()
        def my_function():
            return 42

        result = my_function()
        assert result == 42

    def test_decorator_with_args(self):
        """Test decorator with log_args enabled"""

        @log_performance("test_with_args", log_args=True)
        def func_with_args(x, y, z=10):
            return x + y + z

        result = func_with_args(1, 2, z=3)
        assert result == 6

    def test_decorator_preserves_exception(self):
        """Test that decorator preserves exceptions"""

        @log_performance("failing_func")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

    def test_decorator_custom_log_level(self):
        """Test decorator with custom log level"""

        @log_performance("test_func", log_level=logging.DEBUG)
        def sample_func():
            return "done"

        result = sample_func()
        assert result == "done"

    def test_decorator_with_empty_args(self):
        """Test decorator handles empty args/kwargs"""

        @log_performance(log_args=True)
        def no_args_func():
            return "success"

        result = no_args_func()
        assert result == "success"


class TestLogPerformanceContext:
    """Test log_performance_context context manager"""

    def test_basic_context(self):
        """Test basic context manager usage"""
        with log_performance_context("test_operation"):
            time.sleep(0.01)

    def test_context_with_data(self):
        """Test context manager with additional data"""
        with log_performance_context("batch_process", count=100, size=512):
            time.sleep(0.01)

    def test_context_preserves_exception(self):
        """Test context manager preserves exceptions"""
        with pytest.raises(RuntimeError, match="Test failure"):
            with log_performance_context("failing_operation"):
                raise RuntimeError("Test failure")

    def test_context_logs_on_exception(self):
        """Test context manager logs performance even on exception"""
        try:
            with log_performance_context("error_op", data="test"):
                raise ValueError("Intentional error")
        except ValueError:
            pass  # Expected
