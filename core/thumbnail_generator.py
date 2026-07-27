"""
ThumbnailGenerator - Handles thumbnail generation logic

Extracted from ui/main_window.py during Phase 1 refactoring.
Provides both Rust-based (high performance) and Python-based (fallback) thumbnail generation.
"""

import logging
import os
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import numpy as np
from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QApplication

from core.protocols import ProgressDialog
from utils.image_utils import get_image_dimensions, safe_load_image

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Manages thumbnail generation for CT image stacks

    This class provides intelligent multi-level thumbnail generation with automatic
    fallback between high-performance Rust implementation and pure Python backup.
    It generates Level-of-Detail (LoD) pyramids for efficient multi-scale viewing.

    Features:
        - Dual-mode operation: Rust (high-performance) or Python (portable fallback)
        - Multi-level LoD pyramid generation with automatic downsampling
        - Progress tracking with time estimation and weighted work calculation
        - Cancellation support for long-running operations
        - Automatic mode detection and graceful degradation
        - Memory-efficient processing with streaming support

    Key Concepts:
        - LoD Pyramid: Multiple resolution levels (Level 1 = 1/2, Level 2 = 1/4, etc.)
        - Work Weighting: First level weighted 1.5x due to disk I/O overhead
        - Downsampling: Each level is 2x smaller than previous in each dimension

    Example:
        >>> generator = ThumbnailGenerator()
        >>> # Calculate work for progress tracking
        >>> total_work = generator.calculate_total_thumbnail_work(
        ...     seq_begin=0, seq_end=99, size=2048, max_size=256
        ... )
        >>> # Generate thumbnails
        >>> generator.generate_thumbnails(
        ...     source_dir='/path/to/images',
        ...     target_dir='/path/to/thumbnails',
        ...     settings={'prefix': 'slice_', 'file_type': 'tif', ...},
        ...     progress_callback=lambda p: print(f"Progress: {p}%")
        ... )

    Performance:
        - Rust mode: ~10-50x faster than Python (depends on image size)
        - Python mode: ~50-200 images/second (depends on resolution and CPU)
        - Memory usage: O(single image size) - processes images in streaming fashion

    Thread Safety:
        Instance is NOT thread-safe. Each thread should use its own instance.
        Progress tracking state (self.last_progress, etc.) is not synchronized.
    """

    def __init__(self) -> None:
        """Initialize thumbnail generator"""
        self.level_sizes: list[tuple[int, float, int]] = []
        self.level_work_distribution: list[dict[str, int | float]] = []
        self.total_levels = 0
        self.weighted_total_work: float = 0.0
        self.thumbnail_start_time: float | None = None
        self.last_progress: float = 0.0
        self.progress_start_time: float | None = None
        self.rust_cancelled = False

        # Check Rust module availability
        self.rust_available = self._check_rust_availability()

    def _check_rust_availability(self) -> bool:
        """Check if Rust thumbnail module is available

        Returns:
            bool: True if Rust module available, False otherwise
        """
        try:
            # Deliberately an import, not importlib.util.find_spec: ct_thumbnail
            # is a compiled Rust extension, and find_spec would report it present
            # for a wheel that then fails to load (ABI mismatch, missing shared
            # library). Only an actual import proves it is usable.
            from ct_thumbnail import build_thumbnails  # noqa: F401

        except ImportError:
            logger.info("Rust thumbnail module not available, will use Python fallback")
            return False
        else:
            logger.info("Rust thumbnail module is available")
            return True

    def calculate_total_thumbnail_work(
        self, seq_begin: int, seq_end: int, size: int, max_size: int
    ) -> float:
        """Calculate total number of operations for all LoD levels with size weighting

        This function computes the weighted total work required to generate thumbnails
        at multiple Level of Detail (LoD) levels. Each level is progressively smaller
        and requires less work, but the first level has extra weight due to I/O overhead.

        Args:
            seq_begin: Starting sequence number (inclusive)
            seq_end: Ending sequence number (inclusive)
            size: Initial image dimension (width or height, assumed square)
            max_size: Maximum thumbnail size threshold for stopping LoD generation

        Returns:
            float: Weighted total work units

        Returns:
            int: Total work units (unweighted)

        Side Effects:
            Sets the following instance variables:
            - self.level_sizes (list): Size info at each LoD level
            - self.level_work_distribution (list): Work distribution per level
            - self.total_levels (int): Number of LoD levels
            - self.weighted_total_work (float): Weighted work units

        Note:
            The first level has 1.5x weight because it involves reading from disk,
            while subsequent levels only downsample from memory.
        """
        total_work = 0
        weighted_work: float = 0.0
        temp_seq_begin = seq_begin
        temp_seq_end = seq_end
        temp_size: float = float(size)
        level_count = 0
        level_details = []
        self.level_sizes = []
        self.level_work_distribution = []

        while temp_size >= max_size:
            temp_size = temp_size / 2
            level_count += 1

            # Each level processes half the images from previous level
            images_to_process = (temp_seq_end - temp_seq_begin + 1) // 2 + 1
            total_work += images_to_process

            # Weight based on single image size (area to process per image)
            # Stack total size ratio is 64:8:1, which comes from:
            # (1536²×757) : (768²×379) : (384²×190) = 64 : 8 : 1
            # Per-image weight ratio: 16 : 4 : 1 (from 1536² : 768² : 384²)
            # Using (temp_size/size)² gives correct per-image weight
            size_factor = (temp_size / size) ** 2

            weighted_work = weighted_work + (images_to_process * size_factor)

            level_details.append(
                f"Level {level_count}: {images_to_process} images, "
                f"size={int(temp_size)}px, weight={size_factor:.2f}"
            )
            self.level_sizes.append((level_count, temp_size, images_to_process))
            self.level_work_distribution.append(
                {
                    "level": level_count,
                    "images": images_to_process,
                    "size": int(temp_size),
                    "weight": size_factor,
                }
            )
            temp_seq_end = int((temp_seq_end - temp_seq_begin) / 2) + temp_seq_begin

        # Store total level count for better estimation
        self.total_levels = level_count

        logger.info(f"Thumbnail generation will create {level_count} levels")
        logger.info(f"Total operations: {total_work}, Weighted work: {weighted_work:.1f}")
        for detail in level_details:
            logger.info(f"  {detail}")

        # Return both for compatibility, store weighted for internal use
        self.weighted_total_work = weighted_work
        return total_work

    def generate(
        self,
        directory: str,
        settings: dict[str, Any],
        threadpool: Any,  # QThreadPool
        use_rust_preference: bool = True,
        progress_dialog: Any | None = None,  # ProgressDialog
    ) -> dict[str, Any] | None:
        """Generate thumbnails using best available method

        Args:
            directory: Directory containing CT images
            settings: Settings hash containing image parameters
            threadpool: Qt thread pool for parallel processing
            use_rust_preference: Prefer Rust module if available
            progress_dialog: Progress dialog for UI updates

        Returns:
            Result dictionary containing success status, data, and error info:
                {'success': bool, 'cancelled': bool, 'data': Any,
                'error': Optional[str]}
        """
        # Determine which method to use
        use_rust = self.rust_available and use_rust_preference

        if use_rust:
            logger.info("Using Rust-based thumbnail generation")
            # Create progress callback from progress_dialog
            progress_callback: Callable[[float], None] | None = None
            cancel_check: Callable[[], bool] | None = None

            if progress_dialog:
                # Defined under private names and then assigned, rather than
                # `def progress_callback` shadowing the None above: rebinding a
                # name with `def` inside a branch reads as a redefinition (F811)
                # and hides a genuine one if it ever appears here.
                def _progress_callback(percentage: float) -> None:
                    """Update progress dialog with percentage"""
                    progress_dialog.lbl_text.setText(f"Generating thumbnails: {percentage:.1f}%")
                    progress_dialog.pb_progress.setValue(int(percentage))
                    progress_dialog.update()
                    QApplication.processEvents()

                def _cancel_check() -> bool:
                    """Check if user cancelled via progress dialog"""
                    result: bool = (
                        progress_dialog.is_cancelled
                        if hasattr(progress_dialog, "is_cancelled")
                        else False
                    )
                    return result

                progress_callback = _progress_callback
                cancel_check = _cancel_check

            # Use unified return format
            rust_success = self.generate_rust(directory, progress_callback, cancel_check)

            # Convert legacy bool to unified dict format
            if rust_success:
                return {
                    "success": True,
                    "cancelled": False,
                    "data": None,  # Rust doesn't return thumbnail data
                    "error": None,
                }
            else:
                # Check if it was cancelled or failed
                cancelled = cancel_check() if cancel_check is not None else False
                if not cancelled:
                    # Rust failed but wasn't cancelled - fall back to Python
                    logger.warning("Rust thumbnail generation failed, falling back to Python")
                    return self.generate_python(directory, settings, threadpool, progress_dialog)
                else:
                    return {
                        "success": False,
                        "cancelled": True,
                        "data": None,
                        "error": None,
                    }
        else:
            logger.info("Using Python-based thumbnail generation")
            return self.generate_python(directory, settings, threadpool, progress_dialog)

    def generate_rust(
        self,
        directory: str,
        progress_callback: Callable[[float], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> bool:
        """Generate thumbnails using Rust module

        Args:
            directory (str): Directory containing CT images
            progress_callback (callable): Callback for progress updates
            cancel_check (callable): Function to check if cancelled

        Returns:
            bool: True if successful, False if cancelled or failed
        """
        try:
            from ct_thumbnail import build_thumbnails
        except ImportError:
            logger.exception("Rust module not available")
            return False

        # Start timing
        self.thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now().astimezone()

        logger.info("=== Starting Rust thumbnail generation ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {directory}")

        # Variables for progress tracking
        self.last_progress = 0
        self.progress_start_time = time.time()
        self.rust_cancelled = False

        def internal_progress_callback(percentage: float) -> bool:
            """Internal progress callback wrapper"""
            # Check for cancellation first
            if cancel_check and cancel_check():
                self.rust_cancelled = True
                logger.info(f"Cancellation requested at {percentage:.1f}%")
                return False  # Signal Rust to stop

            # Update progress
            if progress_callback:
                progress_callback(percentage)

            self.last_progress = float(percentage)
            return True  # Continue processing

        try:
            # Call Rust thumbnail generation
            # Note: build_thumbnails returns None on success, raises exception on failure
            build_thumbnails(directory, internal_progress_callback)

            if self.rust_cancelled:
                logger.info("Thumbnail generation was cancelled by user")
                return False

        except ImportError:
            logger.error(
                "Rust module import failed during generation",
                exc_info=True,
                extra={"extra_fields": {"error_type": "rust_import_error"}},
            )
            return False
        except MemoryError:
            logger.error(
                "Out of memory during Rust thumbnail generation",
                exc_info=True,
                extra={"extra_fields": {"error_type": "out_of_memory", "directory": directory}},
            )
            return False
        except OSError:
            logger.error(
                f"File system error during Rust generation: {directory}",
                exc_info=True,
                extra={"extra_fields": {"error_type": "os_error", "directory": directory}},
            )
            return False
        except Exception:
            logger.exception(f"Unexpected error during Rust thumbnail generation: {directory}")
            return False
        else:
            # Reached only when build_thumbnails raised nothing, which is how it
            # reports success -- it returns None either way.
            elapsed = time.time() - (self.thumbnail_start_time or 0)
            logger.info(f"=== Rust thumbnail generation completed in {elapsed:.2f} seconds ===")
            return True

    @staticmethod
    def _log_environment(directory: str, threadpool: QThreadPool) -> None:
        """Log CPU, memory, disk and drive-type context for this run.

        Purely diagnostic: every failure here is swallowed, because a missing
        psutil or an unreadable drive letter must not stop thumbnailing.
        """
        import platform

        try:
            import psutil

            has_psutil = True
        except ImportError:
            has_psutil = False
            logger.warning("psutil not installed - cannot get detailed system info")

        try:
            logger.info(f"System: {platform.system()} {platform.release()}")
            logger.info(f"CPU cores: {os.cpu_count()}")

            if has_psutil:
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage(directory)
                logger.info(
                    f"Memory: {mem.total / 1024**3:.1f}GB total, "
                    f"{mem.available / 1024**3:.1f}GB available ({mem.percent:.1f}% used)"
                )
                logger.info(
                    f"Disk: {disk.total / 1024**3:.1f}GB total, "
                    f"{disk.free / 1024**3:.1f}GB free ({disk.percent:.1f}% used)"
                )

            logger.info(
                f"Thread pool: max={threadpool.maxThreadCount()}, "
                f"active={threadpool.activeThreadCount()}"
            )
        except (AttributeError, ImportError) as e:
            logger.warning(f"Could not get system info: {e}")

        try:
            drive = os.path.splitdrive(directory)[0]
            if drive and drive.startswith("\\\\"):
                logger.warning(
                    f"Working on network drive: {drive} - this may cause slow performance"
                )
            elif drive:
                logger.info(f"Working on local drive: {drive}")
        except (OSError, AttributeError) as e:
            logger.debug(f"Could not determine drive type: {e}")

    @staticmethod
    def _resolve_sample_size(settings: dict[str, Any] | None, total_work: float) -> int:
        """Decide how many images to time before estimating the rest.

        Uses the configured value when there is one, clamped to a sane range;
        otherwise scales with the total work so a small stack is not spent
        entirely on measuring.
        """
        user_sample_size = None
        if settings and isinstance(settings, dict):
            user_sample_size = settings.get("sample_size")

        if user_sample_size is not None:
            from config.constants import MAX_SAMPLE_SIZE, MIN_SAMPLE_SIZE

            base_sample = max(MIN_SAMPLE_SIZE, min(MAX_SAMPLE_SIZE, int(user_sample_size)))
            logger.info(f"Using user-configured sample_size: {base_sample}")
            return base_sample

        from config.constants import (
            ADAPTIVE_SAMPLE_RATIO,
            DEFAULT_ADAPTIVE_SAMPLE_MAX,
            DEFAULT_ADAPTIVE_SAMPLE_MIN,
        )

        base_sample = max(
            DEFAULT_ADAPTIVE_SAMPLE_MIN,
            min(DEFAULT_ADAPTIVE_SAMPLE_MAX, int(total_work * ADAPTIVE_SAMPLE_RATIO)),
        )
        logger.info(f"Auto-calculated sample_size: {base_sample} (2% of {total_work} work)")
        return base_sample

    @staticmethod
    def _prepare_level_dirs(
        directory: str, level: int, seq_begin: int, seq_end: int
    ) -> tuple[str, str, int, int]:
        """Work out where this level reads from and writes to, and how many images.

        Level 0 reads the original directory and trusts the caller's sequence
        range. Later levels read the previous level's output and count what is
        actually on disk, because a level can produce fewer files than predicted
        when the source count was odd.

        Returns:
            (from_dir, to_dir, total_count, seq_end) -- seq_end is returned
            because counting the real files can correct it.
        """
        if level == 0:
            from_dir = directory
            logger.debug(f"Level {level + 1}: Reading from original directory: {from_dir}")
            total_count = seq_end - seq_begin + 1
        else:
            from_dir = os.path.join(directory, ".thumbnail/" + str(level))
            logger.debug(f"Level {level + 1}: Reading from thumbnail directory: {from_dir}")

            if os.path.exists(from_dir):
                actual_files = [f for f in os.listdir(from_dir) if f.endswith(".tif")]
                total_count = len(actual_files)
                seq_end = seq_begin + total_count - 1
                logger.info(
                    f"Level {level + 1}: Found {total_count} actual files in previous level"
                )
            else:
                total_count = seq_end - seq_begin + 1
                logger.warning(
                    f"Level {level + 1}: Previous level directory not found, "
                    f"using calculated count: {total_count}"
                )

        to_dir = os.path.join(directory, ".thumbnail/" + str(level + 1))
        if not os.path.exists(to_dir):
            os.makedirs(to_dir)
            logger.debug(f"Created directory {to_dir}")
        else:
            logger.debug(f"Directory already exists: {to_dir}")

        return from_dir, to_dir, total_count, seq_end

    @staticmethod
    def _cancelled_result(
        minimum_volume: "np.ndarray | list[np.ndarray]",
        level_info: list[dict[str, Any]],
        started_at: float,
    ) -> dict[str, Any]:
        """Build the result dict for a run the user cancelled.

        Whatever levels completed before the cancellation are still returned --
        they are on disk either way, and the caller can display them.
        """
        return {
            "minimum_volume": np.array(minimum_volume) if len(minimum_volume) else np.array([]),
            "level_info": level_info,
            "success": False,
            "cancelled": True,
            "elapsed_time": time.time() - started_at,
        }

    @staticmethod
    def _load_smallest_level(directory: str, level: int) -> np.ndarray:
        """Read the smallest pyramid level back off disk as one 3D array.

        Loaded from disk rather than kept from the loop so the Python and Rust
        paths return the same thing; the Rust module writes files and nothing
        else. An empty array is returned when the directory is missing or holds
        nothing readable, which callers already treat as "no volume".
        """
        smallest_dir = os.path.join(directory, f".thumbnail/{level}")

        if not os.path.exists(smallest_dir):
            logger.warning(f"Smallest level directory not found: {smallest_dir}")
            return np.array([])

        logger.info(f"Loading minimum_volume from {smallest_dir}")
        tif_files = sorted([f for f in os.listdir(smallest_dir) if f.endswith(".tif")])

        slices: list[np.ndarray] = []
        for tif_file in tif_files:
            img_array = safe_load_image(os.path.join(smallest_dir, tif_file))
            if img_array is not None:
                slices.append(img_array)  # type: ignore[arg-type]

        if not slices:
            logger.warning("No images loaded for minimum_volume")
            return np.array([])

        volume = np.array(slices)
        logger.info(f"Loaded minimum_volume: shape {volume.shape}")
        return volume

    def generate_python(
        self,
        directory: str,
        settings: dict[str, Any],
        threadpool: QThreadPool,
        progress_dialog: ProgressDialog | None = None,
    ) -> dict[str, Any] | None:
        """Generate thumbnails using Python implementation (fallback)

        This method implements the full Python-based thumbnail generation logic,
        extracted from main_window.py. It generates multi-level LoD pyramids
        with progress tracking and cancellation support.

        Args:
            directory: Directory containing CT images
            settings: Settings hash containing image_width, image_height,
                     seq_begin, seq_end, prefix, index_length, file_type
            threadpool: Qt thread pool for parallel processing
            progress_dialog: Progress dialog for UI updates.
                If provided, progress will be updated via shared_progress_manager signals.

        Returns:
            Result dictionary containing:
                {
                    'minimum_volume': np.ndarray,
                    'level_info': list,
                    'success': bool,
                    'cancelled': bool,
                    'elapsed_time': float
                }
                Returns None if failed.

        Note:
            This is the fallback implementation used when Rust module is not available.
            Progress tracking works the same way as the original create_thumbnail_python():
            - shared_progress_manager tracks overall progress across all levels
            - ThumbnailManager connects signals to progress_dialog
            - No callbacks needed - Qt signals handle everything
        """
        # Start timing
        thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now().astimezone()

        logger.info("=== Starting Python thumbnail generation (fallback) ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {directory}")

        try:
            # Extract settings
            from config.constants import MAX_THUMBNAIL_SIZE

            size: float = float(max(int(settings["image_width"]), int(settings["image_height"])))
            width = int(settings["image_width"])
            height = int(settings["image_height"])
            seq_begin = settings["seq_begin"]
            seq_end = settings["seq_end"]

            logger.info(f"Thread configuration: maxThreadCount={threadpool.maxThreadCount()}")
            logger.info(f"Image dimensions: width={width}, height={height}, size={size}")

            self._log_environment(directory, threadpool)

            logger.info(f"Processing sequence: {seq_begin} to {seq_end}, directory: {directory}")

            # Import dependencies for thumbnail generation

            from core.progress_manager import ProgressManager
            from core.thumbnail_manager import ThumbnailManager

            # Calculate total work for all LoD levels using the standard method
            # This ensures consistency with main_window's progress setup
            total_work = self.calculate_total_thumbnail_work(
                seq_begin, seq_end, int(size), MAX_THUMBNAIL_SIZE
            )
            weighted_total_work = self.weighted_total_work
            # Use the dict-based level_work_distribution directly for ThumbnailManager
            level_work_distribution = self.level_work_distribution
            total_levels = self.total_levels

            logger.info(
                f"Starting thumbnail generation: {total_levels} levels, {total_work} unweighted operations"
            )
            logger.info(f"Weighted total work: {weighted_total_work:.1f}")

            base_sample = self._resolve_sample_size(settings, total_work)

            sample_size = base_sample
            total_sample = base_sample * 3

            logger.info(
                f"Multi-stage sampling: {base_sample} images per stage, {total_sample} total images"
            )

            # Create shared ProgressManager
            shared_progress_manager = ProgressManager()
            shared_progress_manager.level_work_distribution = level_work_distribution  # type: ignore[assignment]
            shared_progress_manager.weighted_total_work = weighted_total_work
            shared_progress_manager.start(int(weighted_total_work))

            # Initialize progress dialog if provided
            if progress_dialog:
                progress_dialog.lbl_text.setText("Generating thumbnails")
                progress_dialog.lbl_detail.setText("Estimating...")

            # Initialize result containers
            minimum_volume: np.ndarray | list[np.ndarray] = []
            level_info = []

            # Add level 0 (original images) to level_info
            level_info.append(
                {
                    "name": "Level 0",
                    "width": width,
                    "height": height,
                    "seq_begin": seq_begin,
                    "seq_end": seq_end,
                }
            )

            # Main thumbnail generation loop
            i = 0
            global_step_counter: float = 0.0

            while True:
                # Check for cancellation
                if progress_dialog and progress_dialog.is_cancelled:
                    logger.info("Thumbnail generation cancelled by user before level start")
                    return self._cancelled_result(minimum_volume, level_info, thumbnail_start_time)

                # Start timing for this level
                level_start_time = time.time()
                level_start_datetime = datetime.now().astimezone()

                size = size / 2
                width = int(width / 2)
                height = int(height / 2)

                current_level_size = size

                if size < 2:
                    logger.info(f"Stopping at level {i + 1}: size {size} is too small to continue")
                    break

                from_dir, to_dir, total_count, seq_end = self._prepare_level_dirs(
                    directory, i, seq_begin, seq_end
                )

                logger.info(f"--- Level {i + 1} ---")
                logger.info(
                    f"Level {i + 1} start time: {level_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
                )
                logger.info(
                    f"Level {i + 1}: Processing {total_count} images (size: {int(size)}x{int(size)})"
                )

                # Initialize ThumbnailManager for this level
                # Pass progress_dialog directly - ThumbnailManager will connect signals
                logger.info(f"Creating ThumbnailManager for level {i + 1}")
                thumbnail_manager = ThumbnailManager(
                    None,  # main_window (not needed for core logic)
                    progress_dialog,  # Pass progress dialog directly
                    threadpool,
                    shared_progress_manager,
                )
                # Set sample_size for progress sampling
                thumbnail_manager.sample_size = sample_size
                logger.info(
                    f"ThumbnailManager created with sample_size={sample_size}, starting process_level"
                )

                # Process this level
                process_start = time.time()
                level_img_arrays, was_cancelled = thumbnail_manager.process_level(
                    i,
                    from_dir,
                    to_dir,
                    seq_begin,
                    seq_end,
                    settings,
                    size,
                    MAX_THUMBNAIL_SIZE,
                    global_step_counter,
                )
                process_time = time.time() - process_start
                logger.info(f"Level {i + 1}: process_level completed in {process_time:.2f}s")

                # Calculate and log time for this level
                level_end_datetime = datetime.now().astimezone()
                level_elapsed = time.time() - level_start_time
                logger.info(
                    f"Level {i + 1} end time: {level_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
                )
                logger.info(f"Level {i + 1}: Completed in {level_elapsed:.2f} seconds")

                # Update global step counter
                global_step_counter = thumbnail_manager.global_step_counter

                # Check for cancellation
                if was_cancelled or (progress_dialog and progress_dialog.is_cancelled):
                    logger.info("Thumbnail generation cancelled by user")
                    return self._cancelled_result(minimum_volume, level_info, thumbnail_start_time)

                # Update for next level
                current_count = seq_end - seq_begin + 1
                next_count = (current_count // 2) + (current_count % 2)
                seq_end = seq_begin + next_count - 1
                logger.info(
                    f"Level {i + 1}: {current_count} images -> {next_count} thumbnails generated"
                )
                logger.info(f"Next level will process range: {seq_begin}-{seq_end}")

                i += 1

                # Add to level_info if doesn't exist
                level_name = f"Level {i}"
                level_exists = any(level["name"] == level_name for level in level_info)
                if not level_exists:
                    level_info.append(
                        {
                            "name": level_name,
                            "width": width,
                            "height": height,
                            "seq_begin": seq_begin,
                            "seq_end": seq_end,
                        }
                    )

                # Check if we've reached size limit
                if current_level_size < MAX_THUMBNAIL_SIZE:
                    logger.info(f"Reached target thumbnail size at level {i}")
                    break

            logger.info(f"Exited thumbnail generation loop at level {i + 1}")

            # Calculate total time
            thumbnail_end_datetime = datetime.now().astimezone()
            total_elapsed = time.time() - thumbnail_start_time

            logger.info("=== Thumbnail generation completed ===")
            logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(
                f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed / 60:.2f} minutes)"
            )
            logger.info(f"Total levels processed: {i + 1}")

            if total_elapsed > 0:
                images_per_second = total_work / total_elapsed
                logger.info(f"Average processing speed: {images_per_second:.1f} images/second")

            minimum_volume = self._load_smallest_level(directory, i)

            # Final progress update
            if progress_dialog:
                progress_dialog.lbl_text.setText("Thumbnail generation complete")
                progress_dialog.lbl_detail.setText("")

        except MemoryError as e:
            logger.error(
                "Out of memory during Python thumbnail generation",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "error_type": "out_of_memory",
                        "directory": directory,
                        "image_size": f"{settings.get('image_width')}x{settings.get('image_height')}",
                        "image_count": settings.get("seq_end", 0)
                        - settings.get("seq_begin", 0)
                        + 1,
                    }
                },
            )
            return {
                "minimum_volume": np.array([]),
                "level_info": [],
                "success": False,
                "cancelled": False,
                "error": "out_of_memory",
                "error_details": str(e),
                "elapsed_time": (
                    time.time() - thumbnail_start_time if "thumbnail_start_time" in locals() else 0
                ),
            }
        except OSError as e:
            logger.error(
                f"File system error during Python generation: {directory}",
                exc_info=True,
                extra={"extra_fields": {"error_type": "os_error", "directory": directory}},
            )
            return {
                "minimum_volume": np.array([]),
                "level_info": [],
                "success": False,
                "cancelled": False,
                "error": "file_system_error",
                "error_details": str(e),
                "elapsed_time": (
                    time.time() - thumbnail_start_time if "thumbnail_start_time" in locals() else 0
                ),
            }
        except Exception as e:
            logger.exception(f"Unexpected error during Python thumbnail generation: {directory}")
            return {
                "minimum_volume": np.array([]),
                "level_info": [],
                "success": False,
                "cancelled": False,
                "error": "unexpected_error",
                "error_details": str(e),
                "elapsed_time": (
                    time.time() - thumbnail_start_time if "thumbnail_start_time" in locals() else 0
                ),
            }
        else:
            return {
                "minimum_volume": minimum_volume,
                "level_info": level_info,
                "success": True,
                "cancelled": False,
                "elapsed_time": total_elapsed,
            }

    @staticmethod
    def _find_thumbnail_levels(thumbnail_base: str) -> list[tuple[int, str]]:
        """List the contiguous level directories under .thumbnail, in order.

        Stops at the first gap rather than scanning the whole range: levels are
        written consecutively, so a missing one means there are no more.
        """
        from config.constants import MAX_THUMBNAIL_LEVELS

        level_dirs = []
        for i in range(1, MAX_THUMBNAIL_LEVELS):
            level_dir = os.path.join(thumbnail_base, str(i))
            if not os.path.exists(level_dir):
                break
            level_dirs.append((i, level_dir))
        return level_dirs

    @staticmethod
    def _select_thumbnail_level(
        level_dirs: list[tuple[int, str]], max_thumbnail_size: int
    ) -> tuple[int, str]:
        """Pick the first level whose images fit within max_thumbnail_size.

        Levels shrink as the number rises, so the first match is also the
        highest-resolution one that fits. Falls back to the smallest level
        available when even that is too large -- returning nothing would leave
        the caller with no volume at all.
        """
        for level_num, level_dir in level_dirs:
            files = [f for f in os.listdir(level_dir) if f.endswith(".tif")]
            if not files:
                continue

            width, height = get_image_dimensions(os.path.join(level_dir, files[0]))
            if max(width, height) < max_thumbnail_size:
                logger.info(
                    f"Found appropriate level {level_num} with size {width}x{height} "
                    f"(< {max_thumbnail_size})"
                )
                return level_num, level_dir

            logger.debug(
                f"Level {level_num} size {width}x{height} is >= {max_thumbnail_size}, continuing..."
            )

        level_num, level_dir = level_dirs[-1]
        logger.warning(
            f"No level with size < {max_thumbnail_size} found, using highest level {level_num}"
        )
        return level_num, level_dir

    @staticmethod
    def _normalize_to_8bit(img_array: np.ndarray) -> np.ndarray:
        """Scale a slice to uint8, which is what marching cubes expects.

        16-bit is divided down by a fixed factor so every slice keeps the same
        scale; any other non-uint8 dtype is stretched over its own min/max,
        because there is no fixed range to divide by.
        """
        from config.constants import BIT_DEPTH_16_TO_8_DIVISOR, IMAGE_8BIT_MAX

        if img_array.dtype == np.uint8:
            return img_array

        if img_array.dtype == np.uint16:
            return (img_array / BIT_DEPTH_16_TO_8_DIVISOR).astype(np.uint8)

        img_min = img_array.min()
        img_max = img_array.max()
        if img_max <= img_min:
            return np.zeros_like(img_array, dtype=np.uint8)

        stretched: np.ndarray = (
            (img_array - img_min) / (img_max - img_min) * IMAGE_8BIT_MAX
        ).astype(np.uint8)
        return stretched

    def load_thumbnail_data(
        self, directory: str, max_thumbnail_size: int | None = None
    ) -> tuple[np.ndarray | None, dict[str, Any]]:
        """Load generated thumbnail data from disk

        Finds and loads the appropriate level of thumbnails for 3D visualization.

        Args:
            directory: Base directory containing .thumbnail subfolder
            max_thumbnail_size: Maximum size for loaded thumbnails. If None,
                uses DEFAULT_MAX_SIZE from config.

        Returns:
            Tuple of (thumbnail_volume, level_info):
                - thumbnail_volume: 3D numpy array or None if not found
                - level_info: Dictionary with 'levels' and 'current_level' keys
        """
        from config.constants import MAX_THUMBNAIL_SIZE as DEFAULT_MAX_SIZE

        if max_thumbnail_size is None:
            max_thumbnail_size = DEFAULT_MAX_SIZE
        # Find the highest level thumbnail directory
        thumbnail_base = os.path.join(directory, ".thumbnail")

        if not os.path.exists(thumbnail_base):
            logger.warning("No thumbnail directory found")
            return None, {}

        level_dirs = self._find_thumbnail_levels(thumbnail_base)

        if not level_dirs:
            logger.warning("No thumbnail levels found")
            return None, {}

        level_num, thumbnail_dir = self._select_thumbnail_level(level_dirs, max_thumbnail_size)

        logger.info(f"Loading thumbnails from level {level_num}: {thumbnail_dir}")

        try:
            # List all tif files in the directory
            files = sorted([f for f in os.listdir(thumbnail_dir) if f.endswith(".tif")])

            logger.info(f"Found {len(files)} thumbnail files")

            minimum_volume = []
            for file in files:
                filepath = os.path.join(thumbnail_dir, file)
                img_array = safe_load_image(filepath)
                if img_array is None:
                    continue

                minimum_volume.append(self._normalize_to_8bit(img_array))  # type: ignore[arg-type]

            if len(minimum_volume) > 0:
                minimum_volume_array = np.array(minimum_volume)
                logger.info(
                    f"Loaded {len(minimum_volume_array)} thumbnails, shape: {minimum_volume_array.shape}"
                )

                # Create level_info structure
                level_info = []
                # Add loaded level info
                level_info.append(
                    {
                        "name": f"Level {level_num}",
                        "width": minimum_volume_array.shape[2],
                        "height": minimum_volume_array.shape[1],
                        "seq_begin": 0,
                        "seq_end": len(minimum_volume_array) - 1,
                    }
                )

                return minimum_volume_array, {"levels": level_info, "current_level": level_num}
            else:
                logger.warning("No thumbnails loaded")
                return None, {}

        except FileNotFoundError:
            logger.error(
                f"Thumbnail file not found in: {directory}",
                exc_info=True,
                extra={"extra_fields": {"error_type": "file_not_found", "directory": directory}},
            )
            return None, {}
        except PermissionError:
            logger.error(
                f"Permission denied reading thumbnails: {directory}",
                exc_info=True,
                extra={"extra_fields": {"error_type": "permission_denied", "directory": directory}},
            )
            return None, {}
        except OSError:
            logger.error(
                f"OS error loading thumbnails: {directory}",
                exc_info=True,
                extra={"extra_fields": {"error_type": "os_error", "directory": directory}},
            )
            return None, {}
        except Exception:
            logger.exception(f"Unexpected error loading thumbnail data: {directory}")
            return None, {}
