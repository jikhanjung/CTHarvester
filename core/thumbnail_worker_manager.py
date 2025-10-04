"""Worker management and callback handling for thumbnail generation.

This module was extracted from ThumbnailManager during Phase 3 architectural refactoring
to reduce complexity and improve maintainability. It handles worker thread creation,
signal/slot connections, result collection, and thread-safe callback handling.

Typical usage:

    worker_manager = ThumbnailWorkerManager(
        threadpool=QThreadPool.globalInstance(),
        progress_tracker=tracker,
        progress_dialog=dialog
    )

    # Create and submit workers
    for idx in range(num_tasks):
        worker = ThumbnailWorker(...)
        worker_manager.submit_worker(worker)

    # Wait for completion
    worker_manager.wait_for_completion(total_tasks=100)

    # Collect results
    results = worker_manager.get_ordered_results()
"""

import logging
import time
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QMutex, QMutexLocker, QObject, Qt, QThread, QThreadPool, pyqtSlot
from PyQt5.QtWidgets import QApplication

from core.protocols import ProgressDialog
from core.thumbnail_progress_tracker import ThumbnailProgressTracker
from core.thumbnail_worker import ThumbnailWorker

logger = logging.getLogger(__name__)


class ThumbnailWorkerManager(QObject):
    """Manages thumbnail generation worker threads and result collection.

    This class handles the lifecycle of ThumbnailWorker threads, including:
    - Worker creation and submission to thread pool
    - Qt signal/slot connections for progress, results, and errors
    - Thread-safe result collection
    - Worker completion tracking
    - Cancellation handling

    Attributes:
        threadpool: QThreadPool for managing worker threads
        progress_tracker: ThumbnailProgressTracker for progress updates
        progress_dialog: Dialog for UI updates and cancellation checking
        results: Dictionary mapping task index to generated image array
        lock: QMutex for thread-safe result access
        is_cancelled: Flag indicating if processing was cancelled
        global_step_counter: Global progress counter (weighted)
        level_weight: Weight factor for current level
        workers_submitted: Count of workers submitted to thread pool

    Example:
        >>> manager = ThumbnailWorkerManager(threadpool, tracker, dialog)
        >>> for idx in range(100):
        ...     worker = ThumbnailWorker(...)
        ...     manager.submit_worker(worker)
        >>> manager.wait_for_completion(total_tasks=100)
        >>> results = manager.get_ordered_results()
    """

    def __init__(
        self,
        threadpool: QThreadPool,
        progress_tracker: ThumbnailProgressTracker,
        progress_dialog: Optional[ProgressDialog],
        level_weight: float = 1.0,
    ):
        """Initialize worker manager.

        Args:
            threadpool: QThreadPool instance for managing workers
            progress_tracker: ThumbnailProgressTracker for progress tracking
            progress_dialog: Dialog for UI updates (or None for headless)
            level_weight: Weight factor for this level (default: 1.0)
        """
        super().__init__()
        self.threadpool = threadpool
        self.progress_tracker = progress_tracker
        self.progress_dialog = progress_dialog
        self.level_weight = level_weight

        # Result collection
        self.results: Dict[int, Any] = {}
        self.lock = QMutex()

        # State tracking
        self.is_cancelled = False
        self.global_step_counter: float = 0.0
        self.workers_submitted = 0

        logger.debug(f"ThumbnailWorkerManager created: level_weight={level_weight:.4f}")

    def submit_worker(self, worker: ThumbnailWorker) -> None:
        """Submit a worker to the thread pool with signal connections.

        Args:
            worker: ThumbnailWorker instance to submit
        """
        # Connect signals with Qt.QueuedConnection for thread safety
        worker.signals.progress.connect(self.on_worker_progress, Qt.QueuedConnection)
        worker.signals.result.connect(self.on_worker_result, Qt.QueuedConnection)
        worker.signals.error.connect(self.on_worker_error, Qt.QueuedConnection)
        worker.signals.finished.connect(self.on_worker_finished, Qt.QueuedConnection)

        # Submit to thread pool
        self.threadpool.start(worker)
        self.workers_submitted += 1

    def wait_for_completion(
        self,
        total_tasks: int,
        progress_log_interval: int = 5,
        stall_threshold: int = 60,
    ) -> bool:
        """Wait for all workers to complete or cancellation.

        Args:
            total_tasks: Total number of tasks to complete
            progress_log_interval: Seconds between progress log messages (default: 5)
            stall_threshold: Seconds without progress before warning (default: 60)

        Returns:
            True if cancelled, False if completed normally
        """
        start_wait = time.time()
        last_progress_log = time.time()
        last_detailed_log = time.time()
        stalled_count = 0
        last_completed_count = self.progress_tracker.completed_tasks

        first_log = True
        while (
            self.progress_tracker.completed_tasks < total_tasks and not self._check_cancellation()
        ):
            if first_log:
                logger.info(
                    f"Waiting for workers: {self.progress_tracker.completed_tasks}/{total_tasks}"
                )
                first_log = False

            QApplication.processEvents()

            current_time = time.time()

            # Log progress periodically
            if current_time - last_progress_log > progress_log_interval:
                active_threads = self.threadpool.activeThreadCount()
                elapsed = current_time - start_wait
                progress_pct = (
                    (self.progress_tracker.completed_tasks / total_tasks * 100)
                    if total_tasks > 0
                    else 0
                )

                logger.debug(
                    f"{self.progress_tracker.completed_tasks}/{total_tasks} "
                    f"({progress_pct:.1f}%) completed, "
                    f"{active_threads} active threads, elapsed: {elapsed:.1f}s"
                )
                last_progress_log = current_time

                # Check if progress is stalled
                if self.progress_tracker.completed_tasks == last_completed_count:
                    stalled_count += 1
                    if stalled_count >= (stall_threshold // progress_log_interval):
                        logger.warning(
                            f"No progress for {stall_threshold} seconds. "
                            f"{active_threads} threads still active"
                        )
                        # Log details every 30 seconds when stalled
                        if current_time - last_detailed_log > 30:
                            logger.info(
                                f"Status: {self.progress_tracker.completed_tasks}/"
                                f"{total_tasks} tasks after {elapsed:.1f}s"
                            )
                            logger.info("Check disk I/O performance or storage space")
                            last_detailed_log = current_time
                else:
                    stalled_count = 0
                    last_completed_count = self.progress_tracker.completed_tasks

            QThread.msleep(10)

        # Handle cancellation
        if self._check_cancellation():
            self.is_cancelled = True
            logger.info("Processing cancelled by user")

            # Wait briefly for running workers to complete
            max_wait_time = 2000  # 2 seconds
            wait_time = 0
            while self.progress_tracker.completed_tasks < total_tasks and wait_time < max_wait_time:
                QApplication.processEvents()
                QThread.msleep(50)
                wait_time += 50

            if self.progress_tracker.completed_tasks < total_tasks:
                logger.warning("Some workers may still be running after cancellation")

            return True

        return False

    def get_ordered_results(self, total_tasks: int) -> List[Any]:
        """Collect results in sequential order.

        Args:
            total_tasks: Total number of tasks

        Returns:
            List of image arrays in sequential order
        """
        img_arrays = []
        for idx in range(total_tasks):
            if idx in self.results and self.results[idx] is not None:
                img_arrays.append(self.results[idx])

        return img_arrays

    def clear_results(self) -> None:
        """Clear all collected results."""
        self.results.clear()

    def set_global_step_offset(self, offset: float) -> None:
        """Set the starting value for global progress counter.

        Args:
            offset: Starting progress value
        """
        self.global_step_counter = offset

    @pyqtSlot(int)
    def on_worker_progress(self, idx: int) -> None:
        """Handle progress updates from worker threads.

        Qt slot called when worker starts processing. Updates global progress
        counter and triggers UI update.

        Args:
            idx: Task index of the worker reporting progress

        Thread Safety:
            Uses QMutexLocker to protect global_step_counter from concurrent access.
        """
        with QMutexLocker(self.lock):
            # Increment by weight factor
            self.global_step_counter += self.level_weight
            current_step = self.global_step_counter

        # Update UI
        if self.progress_dialog:
            self.progress_dialog.lbl_text.setText("Generating thumbnails")

        # Process events periodically
        if int(current_step) % 10 == 0:
            QApplication.processEvents()

        logger.debug(f"Worker progress: idx={idx}, step={current_step:.1f}")

    @pyqtSlot(object)
    def on_worker_result(self, result: Any) -> None:
        """Handle results from worker threads.

        Qt slot called when worker completes processing. Collects result,
        updates progress tracker, and handles sampling stages.

        Args:
            result: Tuple of (idx, img_array, was_generated) or (idx, img_array)

        Thread Safety:
            Uses QMutexLocker to protect results dict and progress tracker.
        """
        # Unpack result
        if len(result) == 3:
            idx, img_array, was_generated = result
        else:
            # Backward compatibility
            idx, img_array = result
            was_generated = False

        with QMutexLocker(self.lock):
            # Prevent duplicate processing
            if idx in self.results:
                logger.warning(f"Duplicate result for task {idx}, ignoring")
                return

            self.results[idx] = img_array

            # Update progress tracker
            completed = self.progress_tracker.completed_tasks + 1
            # Total will be passed from manager
            self.progress_tracker.on_task_completed(
                completed_count=completed,
                total_tasks=self.progress_tracker.completed_tasks + 1000,  # Temp value
                was_generated=was_generated,
            )

        logger.debug(
            f"Worker result: idx={idx}, has_image={img_array is not None}, "
            f"generated={was_generated}"
        )

    @pyqtSlot(tuple)
    def on_worker_error(self, error_tuple: tuple) -> None:
        """Handle errors from worker threads.

        Qt slot called when worker encounters an exception. Logs error details.

        Args:
            error_tuple: Tuple of (exctype, value, traceback_str)

        Note:
            Errors are logged but don't stop processing. Other workers continue.
        """
        exctype, value, traceback_str = error_tuple
        logger.error(f"Worker error: {exctype.__name__}: {value}")
        logger.debug(f"Traceback: {traceback_str}")

    @pyqtSlot()
    def on_worker_finished(self) -> None:
        """Handle finished signal from worker threads.

        Qt slot called when worker completes (success or failure).
        Currently a placeholder for future cleanup operations.
        """
        pass

    def _check_cancellation(self) -> bool:
        """Check if user has cancelled the operation.

        Returns:
            True if cancelled, False otherwise
        """
        if self.progress_dialog is None:
            return False

        return self.progress_dialog.is_cancelled
