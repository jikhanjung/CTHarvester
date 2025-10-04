"""Performance logging utilities for CTHarvester.

This module provides decorators and context managers for tracking performance metrics
during critical operations. Performance data is logged with structured information
for later analysis.

Created during Phase 3: Production Readiness improvements.

Typical usage:

    from utils.performance_logger import log_performance, PerformanceTimer

    # Decorator usage
    @log_performance("thumbnail_generation")
    def generate_thumbnails(images):
        ...

    # Context manager usage
    with PerformanceTimer("image_processing"):
        process_images()

    # Manual timing
    timer = PerformanceTimer("manual_operation")
    timer.start()
    # ... do work ...
    elapsed = timer.stop()
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceTimer:
    """Timer for measuring operation performance.

    Can be used as a context manager or manually controlled.

    Example:
        # As context manager
        with PerformanceTimer("my_operation"):
            do_work()

        # Manual control
        timer = PerformanceTimer("my_operation")
        timer.start()
        do_work()
        elapsed = timer.stop()
    """

    def __init__(self, operation_name: str, log_level: int = logging.INFO):
        """Initialize performance timer.

        Args:
            operation_name: Name of the operation being timed
            log_level: Logging level for performance messages (default: INFO)
        """
        self.operation_name = operation_name
        self.log_level = log_level
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop the timer and return elapsed time.

        Returns:
            Elapsed time in seconds

        Raises:
            RuntimeError: If timer was not started
        """
        if self.start_time is None:
            raise RuntimeError("Timer was not started")

        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time

        # Log performance
        logger.log(
            self.log_level,
            f"Performance: {self.operation_name} took {elapsed:.3f}s",
            extra={
                "extra_fields": {
                    "operation": self.operation_name,
                    "duration_seconds": elapsed,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                }
            },
        )

        return elapsed

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


def log_performance(
    operation_name: Optional[str] = None,
    log_level: int = logging.INFO,
    log_args: bool = False,
) -> Callable:
    """Decorator for logging function performance.

    Measures execution time and logs it with optional argument information.

    Args:
        operation_name: Name for the operation (defaults to function name)
        log_level: Logging level for performance messages
        log_args: Whether to log function arguments (default: False)

    Returns:
        Decorated function

    Example:
        @log_performance("thumbnail_generation")
        def generate_thumbnails(count):
            ...

        @log_performance(log_args=True)
        def process_image(filename, size):
            ...
    """

    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()

            # Build extra fields
            extra_fields: Dict[str, Any] = {
                "operation": name,
                "function": func.__name__,
                "module": func.__module__,
            }

            # Add arguments if requested
            if log_args:
                extra_fields["args"] = str(args) if args else None
                extra_fields["kwargs"] = str(kwargs) if kwargs else None

            try:
                result = func(*args, **kwargs)
                # Log successful completion
                elapsed = time.perf_counter() - start
                success_fields = extra_fields.copy()
                success_fields["duration_seconds"] = elapsed
                success_fields["failed"] = False

                logger.log(
                    log_level,
                    f"Performance: {name} took {elapsed:.3f}s",
                    extra={"extra_fields": success_fields},
                )
                return result
            except Exception as e:
                # Log performance even on failure
                elapsed = time.perf_counter() - start
                error_fields = extra_fields.copy()
                error_fields["duration_seconds"] = elapsed
                error_fields["failed"] = True
                error_fields["error"] = str(e)

                logger.log(
                    logging.WARNING,
                    f"Performance: {name} failed after {elapsed:.3f}s: {e}",
                    extra={"extra_fields": error_fields},
                )
                raise

        return wrapper

    return decorator


@contextmanager
def log_performance_context(operation_name: str, **context_data):
    """Context manager for performance logging with custom context data.

    Args:
        operation_name: Name of the operation
        **context_data: Additional context to log (e.g., image_count=100)

    Yields:
        None

    Example:
        with log_performance_context("batch_processing", image_count=100, size=512):
            process_batch()
    """
    start = time.perf_counter()

    extra_fields: Dict[str, Any] = {"operation": operation_name}
    extra_fields.update(context_data)

    try:
        yield
    except Exception as e:
        elapsed = time.perf_counter() - start
        extra_fields["duration_seconds"] = elapsed
        extra_fields["failed"] = True
        extra_fields["error"] = str(e)

        logger.warning(
            f"Performance: {operation_name} failed after {elapsed:.3f}s: {e}",
            extra={"extra_fields": extra_fields},
        )
        raise
    else:
        elapsed = time.perf_counter() - start
        extra_fields["duration_seconds"] = elapsed
        extra_fields["failed"] = False

        logger.info(
            f"Performance: {operation_name} took {elapsed:.3f}s",
            extra={"extra_fields": extra_fields},
        )
