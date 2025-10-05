"""Worker thread utilities for background task execution.

This module provides Qt-based worker thread utilities for executing long-running
tasks in background threads without blocking the UI.

Created during Phase 4 refactoring, extracted from CTHarvester.py.

Classes:
    WorkerSignals: Qt signals for worker thread communication
    Worker: QRunnable wrapper for background task execution

Example:
    >>> def long_task(value):
    ...     return value * 2
    >>> worker = Worker(long_task, 42)
    >>> worker.signals.result.connect(lambda x: print(f"Result: {x}"))
    >>> worker.signals.finished.connect(lambda: print("Done"))
    >>> QThreadPool.globalInstance().start(worker)

Note:
    Workers automatically catch exceptions and emit them via error signal.
    KeyboardInterrupt and SystemExit are allowed to propagate.

See Also:
    PyQt5.QtCore.QThreadPool: Thread pool for worker execution
    PyQt5.QtCore.QRunnable: Base class for Worker
"""

import sys
import traceback
from typing import Any, Callable, Optional, Tuple, Type

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    """Qt signals for communication between worker threads and main thread.

    This class defines the signals that a Worker can emit during execution.
    All signals are thread-safe and can be connected to Qt slots.

    Signals:
        finished: Emitted when worker completes (success or error)
        error: Emitted on exception with (type, value, traceback_string)
        result: Emitted on success with the return value from the worker function
        progress: Emitted during execution with progress percentage (0-100)

    Note:
        PyQt signals cannot have type hints in their definition, but the
        emitted types are documented above.

    Example:
        >>> signals = WorkerSignals()
        >>> signals.result.connect(lambda x: print(f"Got result: {x}"))
        >>> signals.error.connect(lambda e: print(f"Error: {e[1]}"))
        >>> signals.finished.connect(lambda: print("Worker finished"))
    """

    finished = pyqtSignal()  # No arguments
    error = pyqtSignal(tuple)  # Tuple[Type[BaseException], BaseException, str]
    result = pyqtSignal(object)  # Any - the return value of the worker function
    progress = pyqtSignal(int)  # int (0-100)


class Worker(QRunnable):
    """Worker thread for executing tasks in background without blocking UI.

    Inherits from QRunnable to handle worker thread setup, signals, and cleanup.
    Automatically catches exceptions and emits them via signals for safe error handling.

    Args:
        fn: The function to run on the worker thread
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Attributes:
        fn: The callable function to execute
        args: Positional arguments tuple
        kwargs: Keyword arguments dictionary
        signals: WorkerSignals instance for thread communication

    Example:
        >>> def process_data(x, multiplier=2):
        ...     return x * multiplier
        >>> worker = Worker(process_data, 10, multiplier=3)
        >>> worker.signals.result.connect(lambda r: print(f"Result: {r}"))
        >>> worker.signals.error.connect(lambda e: print(f"Error: {e[1]}"))
        >>> worker.signals.finished.connect(lambda: print("Done"))
        >>> QThreadPool.globalInstance().start(worker)

    Note:
        - KeyboardInterrupt and SystemExit are allowed to propagate
        - All other exceptions are caught and emitted via error signal
        - finished signal is always emitted (even on error)
        - Use QThreadPool to manage worker execution
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Initialize the worker with a function and its arguments.

        Args:
            fn: Callable function to execute in background thread
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.fn: Callable[..., Any] = fn
        self.args: Tuple[Any, ...] = args
        self.kwargs: dict[str, Any] = kwargs
        self.signals: WorkerSignals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Execute the worker function with stored arguments.

        This method is called by QThreadPool when the worker is started.
        It executes the function and emits appropriate signals based on the result.

        Signals Emitted:
            - result: On success, with the function's return value
            - error: On exception, with (type, value, traceback_string)
            - finished: Always emitted when execution completes

        Raises:
            KeyboardInterrupt: Propagated to allow user interruption
            SystemExit: Propagated to allow clean shutdown

        Note:
            All other exceptions are caught and emitted via the error signal
            instead of propagating, allowing the UI to handle them gracefully.
        """
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except (KeyboardInterrupt, SystemExit):
            # Allow critical exceptions to propagate
            raise
        except Exception:  # noqa: B036
            # Catch all exceptions but allow KeyboardInterrupt and SystemExit to propagate
            # Worker pattern requires catching all exceptions to emit signals
            exctype: Optional[Type[BaseException]]
            value: Optional[BaseException]
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
