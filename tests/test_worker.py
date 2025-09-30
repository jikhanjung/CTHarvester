"""
Unit tests for utils/worker.py

Tests worker thread utilities for background processing.
"""

import os
import sys
import time

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtCore import QObject, QThreadPool

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    from utils.worker import Worker, WorkerSignals


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestWorkerSignals:
    """Tests for WorkerSignals class"""

    def test_initialization(self):
        """Should initialize with all signals defined"""
        signals = WorkerSignals()

        # Check all signals exist
        assert hasattr(signals, "finished")
        assert hasattr(signals, "error")
        assert hasattr(signals, "result")
        assert hasattr(signals, "progress")

    def test_signals_are_callable(self):
        """Should have callable emit methods"""
        signals = WorkerSignals()

        # All signals should have emit method
        assert callable(signals.finished.emit)
        assert callable(signals.error.emit)
        assert callable(signals.result.emit)
        assert callable(signals.progress.emit)

    def test_finished_signal_emission(self):
        """Should emit finished signal"""
        signals = WorkerSignals()
        emitted = []
        signals.finished.connect(lambda: emitted.append(True))

        signals.finished.emit()
        assert len(emitted) == 1

    def test_result_signal_emission(self):
        """Should emit result signal with data"""
        signals = WorkerSignals()
        results = []
        signals.result.connect(results.append)

        signals.result.emit(42)
        assert results == [42]

        signals.result.emit("test")
        assert results == [42, "test"]

    def test_progress_signal_emission(self):
        """Should emit progress signal with percentage"""
        signals = WorkerSignals()
        progress_values = []
        signals.progress.connect(progress_values.append)

        signals.progress.emit(0)
        signals.progress.emit(50)
        signals.progress.emit(100)

        assert progress_values == [0, 50, 100]

    def test_error_signal_emission(self):
        """Should emit error signal with tuple"""
        signals = WorkerSignals()
        errors = []
        signals.error.connect(errors.append)

        error_info = (ValueError, ValueError("test"), "traceback")
        signals.error.emit(error_info)

        assert len(errors) == 1
        assert errors[0][0] == ValueError
        assert isinstance(errors[0][1], ValueError)


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestWorker:
    """Tests for Worker class"""

    def setup_method(self):
        """Create QThreadPool for testing"""
        self.thread_pool = QThreadPool()

    def teardown_method(self):
        """Wait for all threads to finish"""
        self.thread_pool.waitForDone(5000)  # 5 second timeout

    def test_initialization(self):
        """Should initialize with function and arguments"""

        def test_func(x, y):
            return x + y

        worker = Worker(test_func, 1, 2)

        assert worker.fn == test_func
        assert worker.args == (1, 2)
        assert worker.kwargs == {}
        assert isinstance(worker.signals, WorkerSignals)

    def test_initialization_with_kwargs(self):
        """Should store kwargs correctly"""

        def test_func(x, y=10):
            return x + y

        worker = Worker(test_func, 5, y=20)

        assert worker.fn == test_func
        assert worker.args == (5,)
        assert worker.kwargs == {"y": 20}

    def test_initialization_no_args(self):
        """Should work with no arguments"""

        def test_func():
            return "no args"

        worker = Worker(test_func)

        assert worker.fn == test_func
        assert worker.args == ()
        assert worker.kwargs == {}

    def test_run_successful_execution(self):
        """Should execute function and emit result"""

        def simple_func():
            return 42

        worker = Worker(simple_func)
        results = []
        finished = []

        worker.signals.result.connect(results.append)
        worker.signals.finished.connect(lambda: finished.append(True))

        # Run synchronously for testing
        worker.run()

        assert results == [42]
        assert len(finished) == 1

    def test_run_with_arguments(self):
        """Should pass arguments to function"""

        def add_func(a, b, c=0):
            return a + b + c

        worker = Worker(add_func, 10, 20, c=5)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()

        assert results == [35]

    def test_run_error_handling(self):
        """Should catch exceptions and emit error signal"""

        def error_func():
            raise ValueError("Test error")

        worker = Worker(error_func)
        errors = []
        finished = []

        worker.signals.error.connect(errors.append)
        worker.signals.finished.connect(lambda: finished.append(True))

        worker.run()

        # Should emit error
        assert len(errors) == 1
        assert errors[0][0] == ValueError
        assert "Test error" in str(errors[0][1])
        assert isinstance(errors[0][2], str)  # Traceback string

        # Should still emit finished
        assert len(finished) == 1

    def test_run_finished_always_emitted(self):
        """Should always emit finished signal"""

        def normal_func():
            return "ok"

        def error_func():
            raise RuntimeError("error")

        # Test normal execution
        worker1 = Worker(normal_func)
        finished1 = []
        worker1.signals.finished.connect(lambda: finished1.append(True))
        worker1.run()
        assert len(finished1) == 1

        # Test error execution
        worker2 = Worker(error_func)
        finished2 = []
        worker2.signals.finished.connect(lambda: finished2.append(True))
        worker2.run()
        assert len(finished2) == 1

    def test_run_with_none_result(self):
        """Should handle None result"""

        def none_func():
            return None

        worker = Worker(none_func)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()

        assert results == [None]

    def test_run_with_complex_result(self):
        """Should handle complex return types"""

        def complex_func():
            return {"key": "value", "list": [1, 2, 3]}

        worker = Worker(complex_func)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()

        assert len(results) == 1
        assert results[0] == {"key": "value", "list": [1, 2, 3]}

    def test_multiple_workers(self):
        """Should support multiple workers"""

        def func1():
            return "worker1"

        def func2():
            return "worker2"

        worker1 = Worker(func1)
        worker2 = Worker(func2)

        results1 = []
        results2 = []

        worker1.signals.result.connect(results1.append)
        worker2.signals.result.connect(results2.append)

        worker1.run()
        worker2.run()

        assert results1 == ["worker1"]
        assert results2 == ["worker2"]

    def test_run_with_exception_type(self):
        """Should capture correct exception type"""

        def type_error_func():
            return 1 + "string"  # TypeError

        def zero_div_func():
            return 1 / 0  # ZeroDivisionError

        worker1 = Worker(type_error_func)
        errors1 = []
        worker1.signals.error.connect(errors1.append)
        worker1.run()
        assert errors1[0][0] == TypeError

        worker2 = Worker(zero_div_func)
        errors2 = []
        worker2.signals.error.connect(errors2.append)
        worker2.run()
        assert errors2[0][0] == ZeroDivisionError

    def test_run_with_traceback(self):
        """Should include traceback in error"""

        def nested_error():
            def inner():
                raise RuntimeError("Inner error")

            inner()

        worker = Worker(nested_error)
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        # Check traceback contains function names
        traceback_str = errors[0][2]
        assert "nested_error" in traceback_str
        assert "inner" in traceback_str
        assert "RuntimeError" in traceback_str

    def test_worker_reusability(self):
        """Should be able to run worker multiple times"""
        call_count = []

        def counting_func():
            call_count.append(1)
            return len(call_count)

        worker = Worker(counting_func)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()
        worker.run()

        assert results == [1, 2]
        assert len(call_count) == 2

    def test_lambda_function(self):
        """Should work with lambda functions"""
        worker = Worker(lambda x: x * 2, 21)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()

        assert results == [42]

    def test_class_method_as_callback(self):
        """Should work with class methods"""

        class TestClass:
            def __init__(self):
                self.value = 10

            def method(self, x):
                return self.value + x

        obj = TestClass()
        worker = Worker(obj.method, 5)
        results = []
        worker.signals.result.connect(results.append)

        worker.run()

        assert results == [15]

    def test_empty_exception(self):
        """Should handle exception with no message"""

        def empty_error():
            raise ValueError()

        worker = Worker(empty_error)
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        assert len(errors) == 1
        assert errors[0][0] == ValueError
