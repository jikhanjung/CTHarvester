"""Sequential thumbnail processor for Python fallback mode.

This module provides the SequentialProcessor class which handles thumbnail generation
in a single-threaded manner when the Rust module is unavailable. It was extracted from
ThumbnailManager during Phase 4 refactoring to reduce file size and improve modularity.

Sequential processing is 3-5x slower than Rust multithreaded processing (9-10 minutes vs
2-3 minutes) but provides a stable fallback when dependencies are unavailable.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication

from core.progress_manager import ProgressManager
from core.protocols import ProgressDialog, ThumbnailParent
from utils.image_utils import average_images, downsample_image, safe_load_image

logger = logging.getLogger(__name__)


class SequentialProcessor:
    """Processes thumbnails sequentially in a single thread (Python fallback mode).

    This class provides a stable, predictable alternative to multithreaded processing
    when the high-performance Rust module is unavailable. It processes each thumbnail
    pair one at a time, avoiding GIL contention and threading issues at the cost of
    reduced throughput.

    Attributes:
        progress_dialog: Optional progress dialog for cancellation
        progress_manager: Progress tracking manager
        thumbnail_parent: Parent widget with measured_images_per_second attribute
        results: Dictionary to store processed image arrays
        completed_tasks: Counter for finished tasks
        generated_count: Counter for newly generated thumbnails
        loaded_count: Counter for loaded existing thumbnails
        is_cancelled: Cancellation flag
        global_step_counter: Global progress counter
        level_weight: Weight for progress calculation
        is_sampling: Flag for performance sampling
        sample_size: Number of samples for performance measurement
        sample_start_time: Start time for sampling
        images_per_second: Measured processing speed
    """

    def __init__(
        self,
        progress_dialog: Optional[ProgressDialog],
        progress_manager: ProgressManager,
        thumbnail_parent: Optional[ThumbnailParent],
    ):
        """Initialize the sequential processor.

        Args:
            progress_dialog: Optional dialog for progress updates and cancellation
            progress_manager: Manager for progress tracking
            thumbnail_parent: Parent widget for storing performance metrics
        """
        self.progress_dialog = progress_dialog
        self.progress_manager = progress_manager
        self.thumbnail_parent = thumbnail_parent

        # Result storage
        self.results: Dict[int, np.ndarray] = {}

        # Progress tracking
        self.completed_tasks = 0
        self.generated_count = 0
        self.loaded_count = 0
        self.is_cancelled = False

        # Global progress
        self.global_step_counter = 0
        self.level_weight = 1

        # Performance sampling
        self.is_sampling = False
        self.sample_size = 10
        self.sample_start_time: Optional[float] = None
        self.images_per_second = 0.0

    def process_level(
        self,
        level: int,
        from_dir: str,
        to_dir: str,
        seq_begin: int,
        seq_end: int,
        settings_hash: Dict[str, Any],
        size: int,
        max_thumbnail_size: int,
        num_tasks: int,
    ) -> None:
        """Process thumbnails sequentially in a single thread.

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
        logger.info("Starting sequential processing - no threads")

        seq_start_time = time.time()

        for idx in range(num_tasks):
            if self.progress_dialog and self.progress_dialog.is_cancelled:
                self.is_cancelled = True
                break

            task_start_time = time.time()
            seq = seq_begin + (idx * 2)

            # Generate filenames (same logic as ThumbnailWorker)
            if level == 0:
                # Reading from original images
                filename1 = (
                    settings_hash["prefix"]
                    + str(seq).zfill(settings_hash["index_length"])
                    + "."
                    + settings_hash["file_type"]
                )
                # Check if seq+1 exceeds seq_end
                if seq + 1 <= seq_end:
                    filename2 = (
                        settings_hash["prefix"]
                        + str(seq + 1).zfill(settings_hash["index_length"])
                        + "."
                        + settings_hash["file_type"]
                    )
                else:
                    filename2 = None  # Odd number case
            else:
                # Reading from thumbnail directory - use simple numbering
                relative_seq = seq - seq_begin
                filename1 = f"{relative_seq:06}.tif"
                if seq + 1 <= seq_end:
                    filename2 = f"{relative_seq + 1:06}.tif"
                else:
                    filename2 = None  # Odd number case

            # Output always uses simple sequential numbering
            filename3 = os.path.join(to_dir, f"{idx:06}.tif")

            # Check if thumbnail exists
            img_array = None
            was_generated = False

            if os.path.exists(filename3):
                # Load existing
                if size < max_thumbnail_size:
                    img_array = safe_load_image(filename3)  # type: ignore[assignment]
            else:
                # Generate new thumbnail
                was_generated = True
                file1_path = os.path.join(from_dir, filename1)
                if filename2:
                    file2_path = os.path.join(from_dir, filename2)
                else:
                    file2_path = None

                img_array = self._generate_thumbnail(
                    file1_path, file2_path, filename3, idx, size, max_thumbnail_size
                )

            # Update progress
            self.completed_tasks += 1
            if was_generated:
                self.generated_count += 1
            else:
                self.loaded_count += 1

            # Update progress bar
            self.global_step_counter = self.global_step_counter + self.level_weight
            self.progress_manager.update(value=int(self.global_step_counter))

            # Store result
            if img_array is not None:
                self.results[idx] = img_array  # type: ignore[assignment]

            # Performance logging
            task_time = (time.time() - task_start_time) * 1000
            if task_time > 5000:
                logger.warning(f"SLOW task {idx}: {task_time:.1f}ms")
            elif task_time > 3000:
                logger.info(f"Task {idx}: {task_time:.1f}ms")

            # Update ETA periodically
            from config.constants import PROGRESS_LOG_INITIAL, PROGRESS_LOG_INTERVAL

            if (
                self.completed_tasks % PROGRESS_LOG_INTERVAL == 0
                or self.completed_tasks <= PROGRESS_LOG_INITIAL
            ):
                self.update_eta_and_progress()
                QApplication.processEvents()

            # Performance sampling (for first level)
            if self.is_sampling and self.completed_tasks >= self.sample_size:
                elapsed = time.time() - (self.sample_start_time or 0)
                self.images_per_second = self.level_weight * self.sample_size / elapsed
                self.is_sampling = False
                logger.info(f"Sampling complete: {self.images_per_second:.2f} weighted units/s")
                # Store for parent
                if self.thumbnail_parent is not None and hasattr(
                    self.thumbnail_parent, "measured_images_per_second"
                ):
                    self.thumbnail_parent.measured_images_per_second = self.images_per_second  # type: ignore[assignment]

        seq_total_time = time.time() - seq_start_time
        logger.info(
            f"Sequential processing complete: {self.completed_tasks} tasks in {seq_total_time:.1f}s"
        )
        logger.info(f"Average: {seq_total_time/num_tasks*1000:.1f}ms per task")
        logger.info(f"Generated: {self.generated_count}, Loaded: {self.loaded_count}")

    def _generate_thumbnail(
        self,
        file1_path: str,
        file2_path: Optional[str],
        output_path: str,
        idx: int,
        size: int,
        max_thumbnail_size: int,
    ) -> Optional[np.ndarray]:
        """Generate a thumbnail from one or two source images.

        Args:
            file1_path: Path to first source image
            file2_path: Optional path to second source image
            output_path: Path to save generated thumbnail
            idx: Task index for logging
            size: Current thumbnail size
            max_thumbnail_size: Maximum size to load into memory

        Returns:
            Generated image array if size < max_thumbnail_size, None otherwise
        """
        img_array = None

        try:
            # Load images
            arr1 = None
            arr2 = None

            if os.path.exists(file1_path):
                load1_start = time.time()
                arr1 = safe_load_image(file1_path)
                load1_time = (time.time() - load1_start) * 1000
                if load1_time > 1000:
                    logger.warning(f"SLOW load img1: {load1_time:.1f}ms")

            if file2_path and os.path.exists(file2_path):
                load2_start = time.time()
                arr2 = safe_load_image(file2_path)
                load2_time = (time.time() - load2_start) * 1000
                if load2_time > 1000:
                    logger.warning(f"SLOW load img2: {load2_time:.1f}ms")

            # Average and resize
            if arr1 is not None:  # Process even if arr2 is None (odd number case)
                try:
                    if arr2 is not None:
                        # Both images exist - average them
                        averaged = average_images(arr1, arr2)  # type: ignore[arg-type]
                    else:
                        # Only img1 exists (odd case) - no averaging needed
                        logger.debug(f"Processing single image at idx={idx}")
                        averaged = arr1  # type: ignore[assignment]

                    # Downsample by factor of 2
                    downsampled = downsample_image(averaged, factor=2, method="average")

                    # Convert back to PIL Image and save
                    with Image.fromarray(downsampled) as new_img:
                        new_img.save(output_path)

                    if size < max_thumbnail_size:
                        img_array = downsampled
                except MemoryError:
                    logger.error(
                        "Out of memory creating thumbnail",
                        exc_info=True,
                        extra={
                            "extra_fields": {
                                "error_type": "out_of_memory",
                                "output_file": output_path,
                            }
                        },
                    )
                except OSError:
                    logger.error(
                        f"Error saving thumbnail: {output_path}",
                        exc_info=True,
                        extra={
                            "extra_fields": {
                                "error_type": "thumbnail_save_error",
                                "file": output_path,
                            }
                        },
                    )
                except ValueError:
                    logger.error(
                        "Invalid data processing thumbnail",
                        exc_info=True,
                        extra={"extra_fields": {"error_type": "value_error", "file": output_path}},
                    )
        except MemoryError:
            logger.error(
                "Out of memory in thumbnail processing",
                exc_info=True,
                extra={"extra_fields": {"error_type": "out_of_memory", "idx": idx}},
            )
        except (OSError, ValueError):
            logger.exception(f"Unexpected error in thumbnail processing at idx={idx}")

        return img_array

    def update_eta_and_progress(self) -> None:
        """Update ETA display in progress dialog.

        This is a placeholder that would normally update time estimates.
        In the current implementation, it's called periodically but doesn't
        perform calculations (those are in ThumbnailManager).
        """
        pass
