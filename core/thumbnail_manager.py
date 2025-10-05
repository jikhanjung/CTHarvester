"""Thumbnail generation management with progress tracking.

This module provides the ThumbnailManager class which coordinates multithreaded thumbnail
generation for CT image stacks. It manages worker threads, progress tracking, and
result collection.

The module was refactored during Phase 3 architectural improvements to use separate
components for progress tracking and worker management, reducing complexity from 127 to <50.

Typical usage example:

    manager = ThumbnailManager(parent, progress_dialog, threadpool)
    img_arrays, cancelled = manager.process_level(
        level=1,
        from_dir="/path/to/source",
        to_dir="/path/to/output",
        seq_begin=0,
        seq_end=99,
        settings_hash=settings,
        size=256,
        max_size=512,
        global_step=0
    )
"""

import logging
from typing import Any, Dict, Optional

from PyQt5.QtCore import QMutex, QMutexLocker, QObject, Qt, QThread, QThreadPool, pyqtSlot
from PyQt5.QtWidgets import QApplication

from core.progress_manager import ProgressManager
from core.protocols import ProgressDialog, ThumbnailParent
from core.sequential_processor import SequentialProcessor
from core.thumbnail_progress_tracker import ThumbnailProgressTracker
from core.thumbnail_worker import ThumbnailWorker
from core.thumbnail_worker_manager import ThumbnailWorkerManager
from utils.time_estimator import TimeEstimator

logger = logging.getLogger(__name__)


class ThumbnailManager(QObject):
    """Coordinates multithreaded thumbnail generation and progress tracking.

    This class manages the generation of thumbnail images from CT scan slices using
    multiple worker threads. It handles progress updates, ETA calculation, and
    result collection while maintaining thread safety.

    The manager supports both generating new thumbnails and loading existing ones
    from disk, tracking statistics for both operations.

    Attributes:
        parent: Parent window or object containing thumbnail_start_time.
        progress_dialog: Dialog widget for displaying progress updates.
        threadpool: QThreadPool for managing worker threads.
        progress_manager: ProgressManager instance for tracking overall progress.
        total_tasks: Total number of thumbnail generation tasks.
        completed_tasks: Number of completed tasks.
        global_step_counter: Global progress counter across all levels.
        level: Current thumbnail level being processed.
        results: Dictionary mapping task index to generated image array.
        is_cancelled: Flag indicating if processing was cancelled.
        lock: QMutex for thread-safe operations.
        generated_count: Number of thumbnails actually generated.
        loaded_count: Number of thumbnails loaded from existing files.

    Example:
        >>> manager = ThumbnailManager(parent, dialog, QThreadPool.globalInstance())
        >>> images, cancelled = manager.process_level(1, src_dir, dst_dir, 0, 99,
        ...                                           settings, 256, 512, 0)
        >>> if not cancelled:
        ...     print(f"Generated {len(images)} thumbnails")
    """

    def __init__(
        self,
        parent: Optional[ThumbnailParent],
        progress_dialog: Optional[ProgressDialog],
        threadpool: QThreadPool,
        shared_progress_manager: Optional[ProgressManager] = None,
    ):
        """Initialize the thumbnail manager.

        Args:
            parent: Parent window/object containing thumbnail configuration and timing data.
            progress_dialog: Progress dialog for UI updates, or None for headless operation.
            threadpool: QThreadPool instance for managing worker threads.
            shared_progress_manager: Optional ProgressManager to share across multiple
                levels. If None, creates a new instance.
        """
        super().__init__()
        self.thumbnail_parent = parent
        self.progress_dialog = progress_dialog
        self.threadpool = threadpool

        # Use shared progress manager if provided, otherwise create a new one
        if shared_progress_manager:
            self.progress_manager = shared_progress_manager
        else:
            # Create new progress manager as fallback
            self.progress_manager = ProgressManager()
            # Pass weighted work distribution if available from parent
            if self.thumbnail_parent is not None:
                self.progress_manager.level_work_distribution = (
                    self.thumbnail_parent.level_work_distribution  # type: ignore[assignment]
                )
                self.progress_manager.weighted_total_work = (  # type: ignore[assignment]
                    self.thumbnail_parent.weighted_total_work
                )

        # Connect progress manager signals to UI
        if progress_dialog:
            self.progress_manager.progress_updated.connect(
                lambda p: progress_dialog.pb_progress.setValue(p)
            )
            self.progress_manager.eta_updated.connect(lambda eta: self._update_progress_text(eta))

        # Get sample_size from parent if it exists (for first level sampling)
        if hasattr(parent, "sample_size") and parent is not None:
            self.sample_size = parent.sample_size  # type: ignore[union-attr]
        elif parent is None:
            self.sample_size = 0
        else:
            # Fallback: try to read from settings
            try:
                from config.constants import DEFAULT_SAMPLE_SIZE
                from utils.settings_manager import SettingsManager

                settings = SettingsManager()
                self.sample_size = settings.get("thumbnails.sample_size", DEFAULT_SAMPLE_SIZE)
            except (ImportError, KeyError, AttributeError):
                from config.constants import DEFAULT_SAMPLE_SIZE

                self.sample_size = DEFAULT_SAMPLE_SIZE

        # Get inherited speed from parent if available
        initial_speed = None
        if hasattr(parent, "measured_images_per_second") and parent is not None:
            initial_speed = parent.measured_images_per_second  # type: ignore[union-attr]

        # Initialize components (Phase 3 refactoring)
        self.time_estimator = TimeEstimator()
        self.progress_tracker = ThumbnailProgressTracker(
            sample_size=self.sample_size,
            level_weight=1.0,  # Will be updated in process_level
            time_estimator=self.time_estimator,
            initial_speed=initial_speed,
        )
        self.worker_manager = ThumbnailWorkerManager(
            threadpool=self.threadpool,
            progress_tracker=self.progress_tracker,
            progress_dialog=self.progress_dialog,
            level_weight=1.0,  # Will be updated in process_level
        )

        # Legacy compatibility attributes (delegate to components)
        self.level = 0
        self.level_weight = 1.0

        speed_msg = f"{initial_speed:.1f} img/s" if initial_speed else "no inherited speed"
        logger.info(f"ThumbnailManager created: sample_size={self.sample_size}, {speed_msg}")

    # Legacy compatibility properties (delegate to components)
    @property
    def total_tasks(self) -> int:
        """Total number of tasks (for backward compatibility)."""
        return getattr(self, "_total_tasks", 0)

    @total_tasks.setter
    def total_tasks(self, value: int):
        self._total_tasks = value

    @property
    def completed_tasks(self) -> int:
        """Completed tasks counter (delegates to progress_tracker)."""
        return self.progress_tracker.completed_tasks

    @completed_tasks.setter
    def completed_tasks(self, value: int):
        """Set completed tasks (for backward compatibility)."""
        self.progress_tracker.completed_tasks = value

    @property
    def global_step_counter(self) -> float:
        """Global step counter (delegates to worker_manager)."""
        return self.worker_manager.global_step_counter

    @global_step_counter.setter
    def global_step_counter(self, value: float):
        """Set global step counter."""
        self.worker_manager.global_step_counter = value

    @property
    def results(self) -> Dict[int, Any]:
        """Results dictionary (delegates to worker_manager)."""
        return self.worker_manager.results

    @results.setter
    def results(self, value: Dict[int, Any]):
        """Set results dictionary."""
        self.worker_manager.results = value

    @property
    def is_cancelled(self) -> bool:
        """Cancellation flag (delegates to worker_manager)."""
        return self.worker_manager.is_cancelled

    @is_cancelled.setter
    def is_cancelled(self, value: bool):
        """Set cancellation flag."""
        self.worker_manager.is_cancelled = value

    @property
    def generated_count(self) -> int:
        """Number of generated thumbnails (delegates to progress_tracker)."""
        return self.progress_tracker.generated_count

    @generated_count.setter
    def generated_count(self, value: int):
        """Set generated count."""
        self.progress_tracker.generated_count = value

    @property
    def loaded_count(self) -> int:
        """Number of loaded thumbnails (delegates to progress_tracker)."""
        return self.progress_tracker.loaded_count

    @loaded_count.setter
    def loaded_count(self, value: int):
        """Set loaded count."""
        self.progress_tracker.loaded_count = value

    @property
    def is_sampling(self) -> bool:
        """Whether currently sampling (delegates to progress_tracker)."""
        return self.progress_tracker.is_sampling

    @is_sampling.setter
    def is_sampling(self, value: bool):
        """Set sampling flag."""
        self.progress_tracker.is_sampling = value

    @property
    def sample_start_time(self) -> Optional[float]:
        """Sample start timestamp (delegates to progress_tracker)."""
        return self.progress_tracker.sample_start_time

    @sample_start_time.setter
    def sample_start_time(self, value: Optional[float]):
        """Set sample start time."""
        self.progress_tracker.sample_start_time = value

    @property
    def images_per_second(self) -> Optional[float]:
        """Processing speed (delegates to progress_tracker)."""
        return self.progress_tracker.images_per_second

    @images_per_second.setter
    def images_per_second(self, value: Optional[float]):
        """Set processing speed."""
        self.progress_tracker.images_per_second = value

    @property
    def lock(self) -> QMutex:
        """Get thread lock from worker_manager."""
        return self.worker_manager.lock

    def _update_progress_text(self, eta_text):
        """Helper to update progress dialog text"""
        if self.progress_dialog and hasattr(self.progress_dialog, "lbl_detail"):
            detail_text = self.progress_manager.get_detail_text(
                self.level, self.completed_tasks, self.total_tasks
            )
            if eta_text and detail_text:
                self.progress_dialog.lbl_detail.setText(f"{eta_text} - {detail_text}")
            elif detail_text:
                self.progress_dialog.lbl_detail.setText(detail_text)
            elif eta_text:
                self.progress_dialog.lbl_detail.setText(eta_text)

    def _determine_optimal_thread_count(self):
        """Why Python fallback uses single thread

        [Background]
        Python implementation is a backup for the Rust module.
        - Primary: Rust module (2-3 min, true multithreading)
        - Backup: Python fallback (when Rust installation fails)

        [Multithreading Issues]
        While faster on average, unpredictable bottlenecks occur:
        - Most images: 100-200ms (normal)
        - Some images: 10-20 seconds (lock contention, PIL internal issues)
        - Causes: GIL contention, disk I/O contention, PIL/NumPy internal locks

        [Single Thread Choice Rationale]
        1. Predictability: All images process at consistent speed (180-200ms)
        2. Stability: No intermittent freezing
        3. Debuggability: Easy problem tracking
        4. Code Simplicity: Backup implementation prioritizes simplicity
        5. User Experience: Slow but consistent > Fast but occasionally frozen

        [Performance Comparison]
        - Single thread: Stable 9-10 minutes
        - Multi-thread: Average 6-7 min, worst case 30-40 min (some images)

        The goal of backup implementation is "stable operation", not "maximum performance".

        Returns:
            int: 1 (single thread, prioritizing stability and predictability)
        """
        import logging

        logger = logging.getLogger("CTHarvester")

        logger.info(
            "Python fallback: Using single thread for stability "
            "(Rust module is the primary high-performance solution)"
        )

        return 1

    def update_eta_and_progress(self):
        """Update progress bar and ETA display.

        Delegates progress tracking to the centralized ProgressManager, updating
        both the progress value and estimated time to completion. This method
        synchronizes the thumbnail manager's state (sampling status, processing speed)
        with the progress manager before requesting an update.

        The progress manager will emit signals that update the UI progress bar
        and ETA text through connected Qt slots.

        Note:
            This method should be called periodically during thumbnail generation
            to keep the UI responsive and provide accurate progress feedback.
        """
        # Update progress manager state
        if self.is_sampling != self.progress_manager.is_sampling:
            self.progress_manager.set_sampling(self.is_sampling)

        if self.images_per_second:
            self.progress_manager.set_speed(self.images_per_second)

        # Only initialize if not already started (for shared progress manager)
        if not self.progress_manager.total and not self.progress_manager.start_time:
            total_to_use = (
                self.progress_manager.weighted_total_work
                if self.progress_manager.weighted_total_work
                else self.total_tasks
            )
            self.progress_manager.start(int(total_to_use))

        self.progress_manager.update(value=int(self.global_step_counter))

    def process_level_sequential(
        self,
        level,
        from_dir,
        to_dir,
        seq_begin,
        seq_end,
        settings_hash,
        size,
        max_thumbnail_size,
        num_tasks,
    ):
        """Process thumbnails sequentially in a single thread (Python fallback mode).

        This method delegates to SequentialProcessor class which was extracted during
        Phase 4 refactoring to reduce file size and improve modularity.

        Args:
            level: Pyramid level (0=from original images, 1+=from previous thumbnails)
            from_dir: Source directory containing input images
            to_dir: Output directory for generated thumbnails
            seq_begin: Starting sequence number (inclusive)
            seq_end: Ending sequence number (inclusive)
            settings_hash: Dictionary with image metadata ('prefix', 'file_type', 'index_length')
            size: Current thumbnail size in pixels
            max_thumbnail_size: Maximum size to load into memory
            num_tasks: Number of thumbnail pairs to process

        Note:
            This is the Python fallback implementation. The primary implementation
            uses the Rust module with true multithreading for 3-5x better performance.
            Sequential processing takes 9-10 minutes vs 2-3 minutes with Rust.

        Side Effects:
            - Updates self.completed_tasks, self.generated_count, self.loaded_count
            - Updates progress dialog through self.progress_manager
            - Creates thumbnail files in to_dir
            - Stores image arrays in self.results if size < max_thumbnail_size
        """
        # Create sequential processor and transfer state
        processor = SequentialProcessor(
            self.progress_dialog, self.progress_manager, self.thumbnail_parent
        )

        # Transfer state from ThumbnailManager to processor
        processor.global_step_counter = int(self.global_step_counter)
        processor.level_weight = int(self.level_weight)
        processor.is_sampling = self.is_sampling
        processor.sample_size = self.sample_size
        processor.sample_start_time = self.sample_start_time
        processor.images_per_second = self.images_per_second if self.images_per_second else 0.0

        # Process the level
        processor.process_level(
            level,
            from_dir,
            to_dir,
            seq_begin,
            seq_end,
            settings_hash,
            size,
            max_thumbnail_size,
            num_tasks,
        )

        # Transfer state back from processor to ThumbnailManager
        self.results = processor.results
        self.completed_tasks = processor.completed_tasks
        self.generated_count = processor.generated_count
        self.loaded_count = processor.loaded_count
        self.is_cancelled = processor.is_cancelled
        self.global_step_counter = processor.global_step_counter
        self.images_per_second = processor.images_per_second

    def process_level(
        self,
        level,
        from_dir,
        to_dir,
        seq_begin,
        seq_end,
        settings_hash,
        size,
        max_thumbnail_size,
        global_step_offset,
    ):
        """Process a complete thumbnail level using multiple worker threads.

        Orchestrates multithreaded thumbnail generation for a single pyramid level.
        Creates worker threads that process image pairs in parallel, averaging and
        downsampling them to create the next level of the thumbnail pyramid.

        Args:
            level: Pyramid level index (0=from original images, 1+=from previous thumbnails)
            from_dir: Source directory containing input images or thumbnails
            to_dir: Output directory for generated thumbnails
            seq_begin: Starting sequence number (inclusive)
            seq_end: Ending sequence number (inclusive)
            settings_hash: Dictionary with image metadata including 'prefix', 'file_type',
                'index_length' for filename generation
            size: Target thumbnail size in pixels (width and height)
            max_thumbnail_size: Maximum size to keep in memory. Larger thumbnails are
                saved to disk but not loaded into the returned array
            global_step_offset: Starting value for global progress counter, accounting
                for work completed in previous levels

        Returns:
            Tuple[List[np.ndarray], bool]: (thumbnail_arrays, was_cancelled)
                - thumbnail_arrays: List of numpy arrays for thumbnails smaller than
                  max_thumbnail_size, in sequential order
                - was_cancelled: True if user cancelled the operation, False otherwise

        Side Effects:
            - Creates thumbnail files in to_dir (sequential naming: 000000.tif, 000001.tif, ...)
            - Updates progress dialog with ETA and completion percentage
            - Performs multi-stage performance sampling on level 0 to estimate total time
            - Stores performance metrics in parent object for subsequent levels
            - Updates self.generated_count and self.loaded_count statistics

        Example:
            >>> manager = ThumbnailManager(parent, dialog, threadpool)
            >>> thumbnails, cancelled = manager.process_level(
            ...     level=0,
            ...     from_dir="/data/ct_scans/original",
            ...     to_dir="/data/ct_scans/.thumbnails/level_0",
            ...     seq_begin=0,
            ...     seq_end=1513,
            ...     settings_hash={'prefix': 'slice_', 'file_type': 'tif', 'index_length': 4},
            ...     size=512,
            ...     max_thumbnail_size=512,
            ...     global_step_offset=0
            ... )
            >>> if not cancelled:
            ...     print(f"Generated {len(thumbnails)} thumbnail arrays")
        """
        import logging
        import time

        logger = logging.getLogger("CTHarvester")

        level_start_time = time.time()
        logger.info(f"\n=== Starting Level {level+1} Processing ===")
        logger.info(f"From: {from_dir}")
        logger.info(f"To: {to_dir}")
        logger.info(f"Size: {size}x{size}")
        logger.info(f"Range: {seq_begin} to {seq_end}")

        self.level = level
        self.global_step_counter = global_step_offset

        # Get weight factor for this level from level_work_distribution
        # Check both parent and progress_manager for level_work_distribution
        self.level_weight = 1.0  # Default
        level_work_dist = None

        if self.thumbnail_parent is not None:
            level_work_dist = self.thumbnail_parent.level_work_distribution
        elif hasattr(self.progress_manager, "level_work_distribution"):
            # Try to reconstruct from progress_manager's level_work_distribution
            # This is for when parent=None (called from ThumbnailGenerator)
            level_work_dist = self.progress_manager.level_work_distribution  # type: ignore[assignment]

        if level_work_dist:
            # level_work_dist could be list of dicts or list of ints
            if isinstance(level_work_dist, list) and len(level_work_dist) > level:
                if isinstance(level_work_dist[level], dict):
                    # Dict format: {'level': 1, 'images': 757, 'weight': 0.25}
                    for level_info in level_work_dist:
                        if (
                            level_info["level"] == level + 1
                        ):  # level is 0-indexed, but stored as 1-indexed
                            self.level_weight = level_info["weight"]
                            logger.info(
                                f"Level {level+1}: Using weight factor {self.level_weight:.4f}"
                            )
                            break
                else:
                    # For now, use default weight if we only have int list
                    logger.warning(
                        f"Level {level+1}: level_work_distribution is int list, using default weight"
                    )
        self.results.clear()
        self.is_cancelled = False

        # Calculate number of tasks (pairs of images to process)
        # Each task processes 2 images to create 1 thumbnail
        # If odd number, the last image needs special handling
        total_count = seq_end - seq_begin + 1
        num_tasks = (total_count + 1) // 2  # Round up for odd numbers
        self.total_tasks = num_tasks
        self.completed_tasks = 0

        # Enable sampling for level 0 (first level)
        logger.info(f"Sampling check: level={level}, sample_size={self.sample_size}")
        if level == 0 and self.sample_size > 0:
            self.is_sampling = True
            self.sample_start_time = time.time()
            # Tell ProgressManager we're sampling so it shows "Estimating..."
            self.progress_manager.set_sampling(True)
            logger.info(
                f"Level {level+1}: Starting with performance sampling (first {self.sample_size} images)"
            )
        else:
            self.is_sampling = False
            # Not sampling, use any existing speed data
            self.progress_manager.set_sampling(False)
            logger.info(
                f"Not sampling: level={level} (need 0), sample_size={self.sample_size} (need >0)"
            )

        logger.info(
            f"ThumbnailManager.process_level: Starting Level {level+1}, tasks={num_tasks}, offset={global_step_offset}"
        )
        logger.debug(
            f"ThreadPool: maxThreadCount={self.threadpool.maxThreadCount()}, activeThreadCount={self.threadpool.activeThreadCount()}"
        )

        # Determine optimal thread count
        # Balance between performance and stability
        optimal_threads = self._determine_optimal_thread_count()
        if self.threadpool.maxThreadCount() != optimal_threads:
            self.threadpool.setMaxThreadCount(optimal_threads)
            logger.info(f"Set thread pool to {optimal_threads} threads")

        # Wait for any previous level's workers to complete
        if self.threadpool.activeThreadCount() > 0:
            logger.info(
                f"Waiting for {self.threadpool.activeThreadCount()} active threads from previous level to complete..."
            )
            wait_start = time.time()
            while self.threadpool.activeThreadCount() > 0 and time.time() - wait_start < 30:
                QApplication.processEvents()
                from config.constants import PROGRESS_UPDATE_INTERVAL_MS

                QThread.msleep(PROGRESS_UPDATE_INTERVAL_MS)
            if self.threadpool.activeThreadCount() > 0:
                logger.warning(
                    f"Still {self.threadpool.activeThreadCount()} active threads after 30s wait"
                )

        # Create and submit workers
        workers_submitted = 0
        submit_start = time.time()
        logger.info(f"Starting to submit {num_tasks} workers to thread pool")

        for idx in range(num_tasks):
            if self.progress_dialog and self.progress_dialog.is_cancelled:
                self.is_cancelled = True
                break

            seq = seq_begin + (idx * 2)

            # Skip if seq would exceed available images
            if seq > seq_end:
                logger.warning(f"Skipping idx={idx}, seq={seq} exceeds seq_end={seq_end}")
                continue

            # For the last task, check if we have both images
            # If seq+1 > seq_end, the worker will handle it as a single image

            # Create worker with level information and seq_end
            worker = ThumbnailWorker(
                idx,
                seq,
                seq_begin,
                from_dir,
                to_dir,
                settings_hash,
                size,
                max_thumbnail_size,
                self.progress_dialog,
                level,
                seq_end,
            )
            if idx == 0 or idx % 100 == 0:
                logger.debug(
                    f"Creating worker {idx}: seq={seq}, files={worker.filename1}, {worker.filename2}"
                )

            # Connect signals with Qt.QueuedConnection to ensure thread safety
            worker.signals.progress.connect(self.on_worker_progress, Qt.QueuedConnection)  # type: ignore[call-arg,attr-defined]
            worker.signals.result.connect(self.on_worker_result, Qt.QueuedConnection)  # type: ignore[call-arg,attr-defined]
            worker.signals.error.connect(self.on_worker_error, Qt.QueuedConnection)  # type: ignore[call-arg,attr-defined]
            worker.signals.finished.connect(self.on_worker_finished, Qt.QueuedConnection)  # type: ignore[call-arg,attr-defined]

            # Submit to thread pool
            if idx == 0:
                logger.info(f"Submitting first worker to threadpool")
                logger.info(
                    f"Threadpool status before: active={self.threadpool.activeThreadCount()}, max={self.threadpool.maxThreadCount()}"
                )

            self.threadpool.start(worker)
            workers_submitted += 1

            if idx == 0:
                logger.info(
                    f"First worker submitted. Threadpool status after: active={self.threadpool.activeThreadCount()}"
                )

            # Process events periodically to keep UI responsive
            if workers_submitted % 10 == 0 or workers_submitted <= 5:
                QApplication.processEvents()
                # logger.info(f"Submitted {workers_submitted}/{num_tasks} workers, active threads: {self.threadpool.activeThreadCount()}")

        submit_time = time.time() - submit_start
        logger.info(
            f"Submitted {workers_submitted} workers to threadpool in {submit_time*1000:.1f}ms"
        )
        logger.info(
            f"Final threadpool status: active={self.threadpool.activeThreadCount()}, max={self.threadpool.maxThreadCount()}"
        )
        logger.info(f"Waiting for workers to start processing...")

        # Wait for all workers to complete or cancellation
        import time

        start_wait = time.time()
        last_progress_log = time.time()
        last_detailed_log = time.time()
        stalled_count = 0
        last_completed_count = self.completed_tasks

        first_log = True
        while self.completed_tasks < self.total_tasks and not (
            self.progress_dialog and self.progress_dialog.is_cancelled
        ):
            if first_log:
                logger.info(
                    f"Starting main wait loop. Completed: {self.completed_tasks}, Total: {self.total_tasks}"
                )
                first_log = False
            QApplication.processEvents()

            current_time = time.time()

            # Log progress periodically
            if current_time - last_progress_log > 5:  # Every 5 seconds
                active_threads = self.threadpool.activeThreadCount()
                elapsed = current_time - start_wait
                progress_pct = (
                    (self.completed_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0
                )

                logger.debug(
                    f"Level {level+1}: {self.completed_tasks}/{self.total_tasks} ({progress_pct:.1f}%) completed, "
                    f"{active_threads} active threads, elapsed: {elapsed:.1f}s"
                )
                last_progress_log = current_time

                # Check if progress is stalled
                if self.completed_tasks == last_completed_count:
                    stalled_count += 1
                    if stalled_count >= 12:  # No progress for 60 seconds
                        logger.warning(
                            f"Level {level+1}: No progress for 60 seconds. {active_threads} threads still active"
                        )
                        # Log more details every 30 seconds when stalled
                        if current_time - last_detailed_log > 30:
                            logger.info(
                                f"Level {level+1} status: {self.completed_tasks}/{self.total_tasks} tasks completed after {elapsed:.1f}s"
                            )
                            logger.info(
                                f"Consider checking disk I/O performance or available storage space"
                            )
                            last_detailed_log = current_time
                else:
                    stalled_count = 0
                    last_completed_count = self.completed_tasks

            QThread.msleep(10)  # Reduced delay for better responsiveness

        if self.progress_dialog and self.progress_dialog.is_cancelled:
            self.is_cancelled = True
            logger.info(f"ThumbnailManager.process_level: Level {level+1} cancelled by user")

            # Wait a short time for any running workers to complete their current task
            # Note: QThreadPool doesn't have a way to forcibly cancel individual QRunnable tasks
            # but workers will check cancellation status and exit gracefully
            max_wait_time = 2000  # 2 seconds
            wait_time = 0
            while self.completed_tasks < self.total_tasks and wait_time < max_wait_time:
                QApplication.processEvents()
                QThread.msleep(50)
                wait_time += 50

            if self.completed_tasks < self.total_tasks:
                logger.warning(f"Some thumbnail workers may still be running after cancellation")

        # Collect results in order
        img_arrays = []
        for idx in range(num_tasks):
            if idx in self.results and self.results[idx] is not None:
                img_arrays.append(self.results[idx])

        # Log final statistics for this level
        total_time = time.time() - start_wait
        level_total_time = time.time() - level_start_time
        if not self.is_cancelled:
            avg_time_per_task = total_time / self.total_tasks if self.total_tasks > 0 else 0
            tasks_per_second = self.total_tasks / total_time if total_time > 0 else 0
            generation_ratio = (
                self.generated_count / self.total_tasks * 100 if self.total_tasks > 0 else 0
            )

            logger.info(f"\n=== Level {level+1} Complete ===")
            logger.info(f"Tasks completed: {self.completed_tasks}/{self.total_tasks}")
            logger.info(
                f"Generated: {self.generated_count}, Loaded: {self.loaded_count} ({generation_ratio:.1f}% generated)"
            )
            logger.info(f"Images collected: {len(img_arrays)}")
            logger.info(f"Worker time: {total_time:.2f}s")
            logger.info(f"Total level time: {level_total_time:.2f}s (including submission)")
            logger.info(
                f"Average: {avg_time_per_task:.3f}s per task, {tasks_per_second:.1f} tasks/second"
            )

            # Store generation ratio for coefficient calculation decision
            self.generation_ratio = generation_ratio

        return img_arrays, self.is_cancelled

    @pyqtSlot(int)
    def on_worker_progress(self, idx):
        """Handle progress updates from worker threads.

        Qt slot that receives progress signals from ThumbnailWorker threads when they
        start processing a task. Updates the global progress counter and UI display.

        Args:
            idx: Task index of the worker reporting progress

        Thread Safety:
            This method is thread-safe. It uses QMutexLocker to protect shared state
            (global_step_counter) from concurrent access by multiple worker threads.

        Side Effects:
            - Increments global_step_counter by level_weight
            - Updates progress dialog text to "Generating thumbnails"
            - Triggers centralized ETA and progress update
            - Processes Qt events periodically to keep UI responsive
        """
        import logging

        logger = logging.getLogger("CTHarvester")

        with QMutexLocker(self.lock):
            # Increment by weight factor to account for different processing costs per level
            self.global_step_counter = self.global_step_counter + self.level_weight
            current_step = self.global_step_counter

        # Update progress bar
        if self.progress_dialog:
            self.progress_dialog.lbl_text.setText(f"Generating thumbnails")

        # Use centralized ETA and progress update
        # This will call progress_manager.update() which emits progress_updated signal
        # The signal is connected to progress_dialog.pb_progress.setValue() in __init__
        self.update_eta_and_progress()

        # Process events periodically to keep UI responsive
        if current_step % 10 == 0:
            QApplication.processEvents()

        logger.debug(
            f"ThumbnailManager.on_worker_progress: Level {self.level+1}, idx={idx}, step={current_step}"
        )

    @pyqtSlot(object)
    def on_worker_result(self, result):
        """Handle results from worker threads.

        Qt slot that receives result signals from ThumbnailWorker threads when they
        complete processing a thumbnail. Collects results, updates completion counts,
        and performs multi-stage performance sampling on the first level.

        Args:
            result: Tuple of (idx, img_array, was_generated) or legacy (idx, img_array)
                - idx: Task index
                - img_array: Numpy array of thumbnail image, or None if not loaded
                - was_generated: Boolean indicating if thumbnail was newly created (True)
                  or loaded from existing file (False)

        Thread Safety:
            This method is thread-safe. It uses QMutexLocker to protect shared state
            (results dict, completed_tasks, generated_count, loaded_count) from
            concurrent access by multiple worker threads.

        Performance Sampling:
            For level 0, implements a three-stage sampling strategy:
            - Stage 1: After sample_size images, provides initial time estimate
            - Stage 2: After 2×sample_size images, provides refined estimate
            - Stage 3: After 3×sample_size images, finalizes estimate with trend analysis

            This progressive refinement handles variable I/O performance (SSD vs HDD)
            and provides increasingly accurate ETAs as processing continues.

        Side Effects:
            - Stores result in self.results dictionary
            - Increments self.completed_tasks counter
            - Updates self.generated_count or self.loaded_count
            - For level 0 sampling: calculates and logs performance estimates,
              updates parent's performance metrics for subsequent levels
            - Calls update_eta_and_progress() to refresh UI
        """
        import logging
        import time

        logger = logging.getLogger("CTHarvester")

        # Unpack result with generation flag
        if len(result) == 3:
            idx, img_array, was_generated = result
        else:
            # Backward compatibility
            idx, img_array = result
            was_generated = False

        with QMutexLocker(self.lock):
            # Prevent duplicate processing (thread-safe)
            if idx in self.results:
                logger.warning(f"Duplicate result for task {idx}, ignoring")
                return

            self.results[idx] = img_array
            self.completed_tasks += 1

            # Track generation vs loading
            if was_generated:
                self.generated_count += 1
            else:
                self.loaded_count += 1

            # Validate progress bounds BEFORE reading (prevent race condition)
            completed = self.completed_tasks
            total = self.total_tasks

            if completed > total:
                logger.error(f"completed ({completed}) > total ({total}), capping to total")
                self.completed_tasks = total
                completed = total

            # Multi-stage sampling for better accuracy
            # Stage 1: Initial sampling (first sample_size images)
            if self.is_sampling and self.level == 0 and completed == self.sample_size:
                sample_elapsed = time.time() - (self.sample_start_time or 0)
                total_levels = (
                    self.thumbnail_parent.total_levels if self.thumbnail_parent is not None else 1
                )

                # Use TimeEstimator for calculations
                estimate_info = self.time_estimator.format_stage_estimate(
                    stage=1,
                    elapsed=sample_elapsed,
                    sample_size=self.sample_size,
                    total_items=total,
                    num_levels=total_levels,
                )

                logger.info(
                    f"=== Stage 1 Sampling ({self.sample_size} images in {sample_elapsed:.2f}s) ==="
                )
                logger.info(f"Speed: {estimate_info['time_per_image']:.3f}s per image")
                logger.info(
                    f"Initial estimate: {estimate_info['total_estimate_formatted']} ({estimate_info['total_estimate']:.1f}s)"
                )

                # Update ProgressManager with sampled speed - stop showing "Estimating..."
                weighted_speed = (
                    (self.sample_size * self.level_weight) / sample_elapsed
                    if sample_elapsed > 0
                    else 1.0
                )
                self.progress_manager.set_speed(weighted_speed)
                self.progress_manager.set_sampling(False)  # Show actual ETA now

                # Store for comparison
                self.stage1_estimate = estimate_info["total_estimate"]
                self.stage1_speed = estimate_info["time_per_image"]

            # Stage 2: Extended sampling (after 2x sample_size)
            elif self.is_sampling and self.level == 0 and completed == self.sample_size * 2:
                sample_elapsed = time.time() - (self.sample_start_time or 0)
                total_levels = (
                    self.thumbnail_parent.total_levels if self.thumbnail_parent is not None else 1
                )

                # Use TimeEstimator for calculations
                estimate_info = self.time_estimator.format_stage_estimate(
                    stage=2,
                    elapsed=sample_elapsed,
                    sample_size=self.sample_size * 2,
                    total_items=total,
                    num_levels=total_levels,
                )

                logger.info(
                    f"=== Stage 2 Sampling ({self.sample_size * 2} images in {sample_elapsed:.2f}s) ==="
                )
                logger.info(f"Speed: {estimate_info['time_per_image']:.3f}s per image")
                logger.info(
                    f"Revised estimate: {estimate_info['total_estimate_formatted']} ({estimate_info['total_estimate']:.1f}s)"
                )

                # Update ProgressManager with improved speed estimate
                weighted_speed = (
                    (self.sample_size * 2 * self.level_weight) / sample_elapsed
                    if sample_elapsed > 0
                    else 1.0
                )
                self.progress_manager.set_speed(weighted_speed)

                # Compare with stage 1
                if hasattr(self, "stage1_estimate"):
                    diff_percent = (
                        (estimate_info["total_estimate"] - self.stage1_estimate)
                        / self.stage1_estimate
                    ) * 100
                    logger.info(f"Difference from stage 1: {diff_percent:+.1f}%")
                    speed_change = (
                        (estimate_info["time_per_image"] - self.stage1_speed) / self.stage1_speed
                    ) * 100
                    logger.info(f"Speed change: {speed_change:+.1f}%")

                # Store stage 2 results
                self.stage2_estimate = estimate_info["total_estimate"]

            # Stage 3: Final sampling (after 3x sample_size)
            elif self.is_sampling and self.level == 0 and completed >= self.sample_size * 3:
                sample_elapsed = time.time() - (self.sample_start_time or 0)
                total_levels = (
                    self.thumbnail_parent.total_levels if self.thumbnail_parent is not None else 1
                )

                # Calculate weighted units per second
                weighted_units_completed = (self.sample_size * 3) * self.level_weight
                self.images_per_second = (
                    weighted_units_completed / sample_elapsed if sample_elapsed > 0 else 20
                )

                # Use TimeEstimator for calculations
                estimate_info = self.time_estimator.format_stage_estimate(
                    stage=3,
                    elapsed=sample_elapsed,
                    sample_size=self.sample_size * 3,
                    total_items=total,
                    num_levels=total_levels,
                )

                logger.info(
                    f"=== Stage 3 Sampling ({self.sample_size * 3} images in {sample_elapsed:.2f}s) ==="
                )
                logger.info(f"Speed: {estimate_info['time_per_image']:.3f}s per image")
                logger.info(
                    f"Performance sampling complete: {self.images_per_second:.1f} weighted units/second"
                )

                # Final update to ProgressManager with most accurate speed
                self.progress_manager.set_speed(self.images_per_second)

                total_estimate = estimate_info["total_estimate"]

                # Compare all stages
                if hasattr(self, "stage1_estimate") and hasattr(self, "stage2_estimate"):
                    logger.info(
                        f"Estimate progression: Stage1={self.stage1_estimate:.1f}s -> Stage2={self.stage2_estimate:.1f}s -> Stage3={total_estimate:.1f}s"
                    )

                    # If estimates are increasing significantly, apply adjustment
                    if total_estimate > self.stage1_estimate * 1.5:
                        # Trend suggests further slowdown, apply correction
                        trend_factor = total_estimate / self.stage1_estimate
                        adjusted_estimate = total_estimate * (
                            1 + (trend_factor - 1) * 0.3
                        )  # Apply 30% of the trend
                        logger.info(
                            f"Trend adjustment applied: {total_estimate:.1f}s -> {adjusted_estimate:.1f}s"
                        )
                        total_estimate = adjusted_estimate

                storage_type = (
                    "SSD"
                    if self.images_per_second > 10
                    else "HDD" if self.images_per_second > 2 else "Network/Slow"
                )
                drive_label = (
                    f"{self.thumbnail_parent.current_drive}"
                    if self.thumbnail_parent is not None
                    and hasattr(self.thumbnail_parent, "current_drive")
                    else "unknown"
                )
                logger.info(f"Drive {drive_label} estimated as: {storage_type}")

                # Log the final estimated time
                if total_estimate < 60:
                    formatted_estimate = f"{int(total_estimate)}s"
                elif total_estimate < 3600:
                    formatted_estimate = f"{int(total_estimate/60)}m {int(total_estimate%60)}s"
                else:
                    formatted_estimate = (
                        f"{int(total_estimate/3600)}h {int((total_estimate%3600)/60)}m"
                    )
                logger.info(f"=== FINAL ESTIMATED TOTAL TIME: {formatted_estimate} ===")

                # Store sampled estimate for comparison (only if parent is not None)
                if self.thumbnail_parent is not None:
                    self.thumbnail_parent.sampled_estimate_seconds = total_estimate
                    self.thumbnail_parent.sampled_estimate_str = formatted_estimate

                    # Update parent's estimate and save performance data for next levels
                    self.thumbnail_parent.estimated_time_per_image = (
                        1.0 / self.images_per_second if self.images_per_second > 0 else 0.05
                    )
                    self.thumbnail_parent.estimated_total_time = total_estimate
                    self.thumbnail_parent.measured_images_per_second = self.images_per_second  # type: ignore[assignment]

                self.is_sampling = False
                logger.info(f"Multi-stage sampling completed")

            # Always update ETA and progress display
            self.update_eta_and_progress()

        # Just log the result, don't update UI (already done in on_worker_progress)
        logger.debug(
            f"ThumbnailManager.on_worker_result: Level {self.level+1}, completed={completed}/{total}, has_image={img_array is not None}"
        )

    @pyqtSlot(tuple)
    def on_worker_error(self, error_tuple):
        """Handle errors from worker threads.

        Qt slot that receives error signals from ThumbnailWorker threads when they
        encounter exceptions during thumbnail processing. Logs the error details
        for debugging.

        Args:
            error_tuple: Tuple of (exctype, value, traceback_str)
                - exctype: Exception class
                - value: Exception instance
                - traceback_str: Formatted traceback string

        Note:
            Errors are logged but don't stop the overall processing. Other workers
            continue to run, allowing partial completion even when some images fail.
        """
        import logging

        logger = logging.getLogger("CTHarvester")
        exctype, value, traceback_str = error_tuple
        logger.error(f"Thumbnail worker error: {exctype.__name__}: {value}")
        logger.debug(f"Traceback: {traceback_str}")

    @pyqtSlot()
    def on_worker_finished(self):
        """Handle finished signal from worker threads.

        Qt slot that receives finished signals from ThumbnailWorker threads when they
        complete execution (whether successful or not). Currently a placeholder to
        properly handle the Qt signal connection.

        Note:
            The actual result handling is done in on_worker_result(). This slot exists
            to complete the Qt signal/slot pattern and could be extended for cleanup
            operations if needed in the future.
        """
        # This is just a placeholder to properly handle the finished signal
        pass


# Define a custom OpenGL widget using QOpenGLWidget
