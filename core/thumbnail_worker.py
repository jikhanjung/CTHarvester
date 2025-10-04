"""
Thumbnail Worker Module
Handles thumbnail generation in separate threads
"""

import gc
import logging
import os
import sys
import time
import traceback
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageChops
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from security.file_validator import SecureFileValidator
from utils.image_utils import safe_load_image

logger = logging.getLogger("CTHarvester")


class ThumbnailWorkerSignals(QObject):
    """Qt signals for thumbnail worker thread communication.

    Provides typed signals for worker-to-manager communication in the thumbnail
    generation pipeline. These signals are emitted by ThumbnailWorker instances
    and handled by ThumbnailManager slots.

    Signals:
        finished: Emitted when worker completes (success or failure)
        error (tuple): Emitted on exception, carries (exctype, value, traceback_str)
        result (object): Emitted on successful completion, carries
            (idx, img_array, was_generated) tuple where:
            - idx (int): Task index
            - img_array (np.ndarray or None): Thumbnail array if loaded
            - was_generated (bool): True if newly created, False if loaded from disk
        progress (int): Emitted when processing starts, carries task index

    Example:
        >>> worker = ThumbnailWorker(...)
        >>> worker.signals.result.connect(manager.on_worker_result)
        >>> worker.signals.error.connect(manager.on_worker_error)
        >>> worker.signals.finished.connect(manager.on_worker_finished)
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)  # (idx, img_array or None, was_generated)
    progress = pyqtSignal(int)  # idx


class ThumbnailWorker(QRunnable):
    """
    Worker thread for processing individual thumbnail image pairs

    Handles:
    - Loading two consecutive images
    - Averaging them
    - Downscaling by 2x
    - Saving as thumbnail
    - Supporting both 8-bit and 16-bit images
    """

    def __init__(
        self,
        idx: int,
        seq: int,
        seq_begin: int,
        from_dir: str,
        to_dir: str,
        settings_hash: dict,
        size: int,
        max_thumbnail_size: int,
        progress_dialog,
        level: int = 0,
        seq_end: Optional[int] = None,
    ):
        """
        Initialize thumbnail worker

        Args:
            idx: Output index (sequential from 0)
            seq: Input sequence number
            seq_begin: Beginning of sequence range
            from_dir: Source directory
            to_dir: Destination directory
            settings_hash: Settings dictionary with prefix, index_length, file_type
            size: Current pyramid level size
            max_thumbnail_size: Maximum size for loading into memory
            progress_dialog: Progress dialog for cancellation check
            level: Pyramid level (0=original, 1+=thumbnails)
            seq_end: End of sequence range
        """
        super().__init__()

        self.idx = idx
        self.seq = seq
        self.seq_begin = seq_begin
        self.seq_end = seq_end if seq_end is not None else settings_hash.get("seq_end", 999999)
        self.from_dir = from_dir
        self.to_dir = to_dir
        self.settings_hash = settings_hash
        self.size = size
        self.max_thumbnail_size = max_thumbnail_size
        self.progress_dialog = progress_dialog
        self.signals = ThumbnailWorkerSignals()
        self.level = level

        # Generate filenames
        self._generate_filenames()

    def _generate_filenames(self):
        """Generate input and output filenames based on level"""
        if self.level == 0:
            # Level 0: Reading from original images with prefix
            self.filename1 = (
                self.settings_hash["prefix"]
                + str(self.seq).zfill(self.settings_hash["index_length"])
                + "."
                + self.settings_hash["file_type"]
            )
            if self.seq + 1 <= self.seq_end:
                self.filename2 = (
                    self.settings_hash["prefix"]
                    + str(self.seq + 1).zfill(self.settings_hash["index_length"])
                    + "."
                    + self.settings_hash["file_type"]
                )
            else:
                self.filename2 = None  # Odd number of images
        else:
            # Level 1+: Reading from thumbnail directory with simple numbering
            relative_seq = self.seq - self.seq_begin
            self.filename1 = f"{relative_seq:06}.tif"
            if self.seq + 1 <= self.seq_end:
                self.filename2 = f"{relative_seq + 1:06}.tif"
            else:
                self.filename2 = None

        # Output: Always simple sequential numbering
        self.filename3 = os.path.join(self.to_dir, f"{self.idx:06}.tif")

    def _load_image(self, filepath: str) -> Tuple[Optional[Image.Image], bool]:
        """
        Load a single image file

        Args:
            filepath: Path to image file

        Returns:
            (PIL Image, is_16bit flag) or (None, False) on error
        """
        try:
            validated_path = SecureFileValidator.validate_path(filepath, self.from_dir)

            open_start = time.time()
            with Image.open(validated_path) as img_temp:
                # Determine bit depth and copy image
                is_16bit = img_temp.mode in ("I;16", "I;16L", "I;16B")

                if is_16bit:
                    img = img_temp.copy()
                elif img_temp.mode[0] == "I":
                    img = img_temp.convert("L")
                elif img_temp.mode == "P":
                    img = img_temp.convert("L")
                else:
                    img = img_temp.copy()

            open_time = (time.time() - open_start) * 1000
            if self.idx < 5:
                logger.info(f"Opened {os.path.basename(filepath)} in {open_time:.1f}ms")
            else:
                logger.debug(f"Opened {os.path.basename(filepath)} in {open_time:.1f}ms")

            return img, is_16bit

        except OSError as e:
            logger.error(f"Error loading image {filepath}: {e}")
            return None, False

    def _process_single_image(self, img: Image.Image, is_16bit: bool) -> Image.Image:
        """
        Process a single image (for odd number case)

        Args:
            img: PIL Image
            is_16bit: Whether image is 16-bit

        Returns:
            Downscaled PIL Image
        """
        if is_16bit:
            arr = np.array(img, dtype=np.uint16)
            h, w = arr.shape
            new_h, new_w = h // 2, w // 2

            # Downscale by 2x2 averaging
            arr_32 = arr.astype(np.uint32)
            downscaled = (
                arr_32[0 : 2 * new_h : 2, 0 : 2 * new_w : 2]
                + arr_32[0 : 2 * new_h : 2, 1 : 2 * new_w : 2]
                + arr_32[1 : 2 * new_h : 2, 0 : 2 * new_w : 2]
                + arr_32[1 : 2 * new_h : 2, 1 : 2 * new_w : 2]
            ) // 4
            downscaled = downscaled.astype(np.uint16)
            return Image.fromarray(downscaled)
        else:
            return img.resize((img.width // 2, img.height // 2))

    def _process_image_pair_16bit(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Process a pair of 16-bit images

        Args:
            img1: First image
            img2: Second image

        Returns:
            Averaged and downscaled PIL Image
        """
        # Convert to numpy arrays
        arr1 = np.array(img1, dtype=np.uint16)
        arr2 = np.array(img2, dtype=np.uint16)

        # Average the two arrays
        avg_arr = ((arr1.astype(np.uint32) + arr2.astype(np.uint32)) // 2).astype(np.uint16)

        # Downscale by 2x2 averaging
        h, w = avg_arr.shape
        new_h, new_w = h // 2, w // 2

        avg_arr_32 = avg_arr.astype(np.uint32)
        downscaled = (
            avg_arr_32[0 : 2 * new_h : 2, 0 : 2 * new_w : 2]
            + avg_arr_32[0 : 2 * new_h : 2, 1 : 2 * new_w : 2]
            + avg_arr_32[1 : 2 * new_h : 2, 0 : 2 * new_w : 2]
            + avg_arr_32[1 : 2 * new_h : 2, 1 : 2 * new_w : 2]
        ) // 4
        downscaled = downscaled.astype(np.uint16)

        # Clean up large arrays
        del arr1, arr2, avg_arr, avg_arr_32

        return Image.fromarray(downscaled)

    def _process_image_pair_8bit(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Process a pair of 8-bit images

        Args:
            img1: First image
            img2: Second image

        Returns:
            Averaged and downscaled PIL Image
        """
        # Average using PIL
        new_img = ImageChops.add(img1, img2, scale=2.0)
        # Resize to half
        new_img = new_img.resize((img1.width // 2, img1.height // 2))
        return new_img

    @pyqtSlot()
    def run(self):
        """Process a single thumbnail task (main worker thread entry point).

        This is the main execution method for the worker thread. It either loads an
        existing thumbnail from disk or generates a new one by averaging and downsampling
        a pair of input images. The method is designed to run in a QThreadPool.

        Process Flow:
            1. Check for user cancellation
            2. Check if thumbnail already exists on disk
            3. If exists and size < max: load existing thumbnail
            4. If not exists: generate new thumbnail via _generate_thumbnail()
            5. Emit progress and result signals
            6. Handle any exceptions and emit error signal

        Signals Emitted:
            - progress(idx): Emitted when task starts processing
            - result((idx, img_array, was_generated)): Emitted on completion
            - error((exctype, value, traceback)): Emitted on exception
            - finished(): Emitted when worker exits (always)

        Side Effects:
            - May create thumbnail file at self.filename3
            - Logs performance metrics (warnings for slow tasks >5s)
            - Triggers periodic garbage collection

        Thread Safety:
            This method runs in a worker thread. All signal emissions are
            queued through Qt's event system for thread-safe communication.

        Example Output:
            For a typical task processing in 180ms:
            - DEBUG: "Completed idx=42 (loaded) in 180.0ms"
            For a slow task taking 5.2 seconds:
            - WARNING: "SLOW - idx=42 (generated) took 5200.0ms"
        """
        worker_start_time = time.time()

        if self.idx < 5:
            logger.info(
                f"ThumbnailWorker.run: Starting Level {self.level+1} worker "
                f"for idx={self.idx}, seq={self.seq}"
            )
            logger.info(f"  Files: {self.filename1}, {self.filename2}")
            logger.info(f"  From: {self.from_dir}")
            logger.info(f"  To: {self.to_dir}")
            logger.info(f"  Output: {self.filename3}")
        else:
            logger.debug(
                f"ThumbnailWorker.run: Starting Level {self.level+1} worker "
                f"for idx={self.idx}, seq={self.seq}"
            )

        try:
            # Check for cancellation
            if self.progress_dialog.is_cancelled:
                logger.debug(f"ThumbnailWorker.run: Cancelled before start, idx={self.idx}")
                return

            img_array = None
            was_generated = False

            # Check if thumbnail already exists
            if os.path.exists(self.filename3):
                logger.debug(f"Found existing thumbnail: {self.filename3}")
                was_generated = False

                if self.size < self.max_thumbnail_size:
                    img_array = safe_load_image(self.filename3)  # type: ignore[assignment]
                    if img_array is not None:
                        logger.debug(f"Loaded existing thumbnail shape: {img_array.shape}")  # type: ignore[union-attr]
            else:
                # Generate new thumbnail
                if self.progress_dialog.is_cancelled:
                    return

                was_generated = True
                img_array = self._generate_thumbnail()

            # Emit signals
            worker_time = (time.time() - worker_start_time) * 1000
            status = "generated" if was_generated else "loaded"

            if worker_time > 5000:
                logger.warning(f"SLOW - idx={self.idx} ({status}) took {worker_time:.1f}ms")
            elif worker_time > 3000:
                logger.info(f"idx={self.idx} ({status}) took {worker_time:.1f}ms")
            else:
                logger.debug(f"Completed idx={self.idx} ({status}) in {worker_time:.1f}ms")

            self.signals.progress.emit(self.idx)
            self.signals.result.emit((self.idx, img_array, was_generated))

        except Exception as e:
            exctype, value = sys.exc_info()[:2]
            error_trace = traceback.format_exc()
            logger.error(f"Exception in worker {self.idx}: {e}\n{error_trace}")
            self.signals.error.emit((exctype, value, error_trace))
        finally:
            logger.debug(f"Finished worker for idx={self.idx}")
            self.signals.finished.emit()

    def _generate_thumbnail(self) -> Optional[np.ndarray]:
        """
        Generate a new thumbnail from source images

        Returns:
            numpy array if size < max_thumbnail_size, else None
        """
        try:
            # Load first image
            file1_path = os.path.join(self.from_dir, self.filename1)
            if not os.path.exists(file1_path):
                logger.error(f"File not found: {file1_path}")
                return None

            img1, is_16bit1 = self._load_image(file1_path)
            if img1 is None:
                return None

            # Load second image (if exists)
            img2 = None
            is_16bit2 = False
            if self.filename2:
                file2_path = os.path.join(self.from_dir, self.filename2)
                if os.path.exists(file2_path):
                    img2, is_16bit2 = self._load_image(file2_path)

            # Process images
            if img2 is None:
                # Single image (odd number case)
                logger.debug(f"Processing single image at idx={self.idx}")
                new_img = self._process_single_image(img1, is_16bit1)
            elif is_16bit1 and is_16bit2:
                # Both 16-bit
                logger.debug("Processing as 16-bit images")
                new_img = self._process_image_pair_16bit(img1, img2)
            elif is_16bit1 or is_16bit2:
                # Mixed bit depth - convert to 16-bit
                logger.debug("Processing mixed bit depth images")
                if not is_16bit1:
                    arr1 = np.array(img1, dtype=np.uint8).astype(np.uint16) << 8
                    img1 = Image.fromarray(arr1)
                if not is_16bit2:
                    arr2 = np.array(img2, dtype=np.uint8).astype(np.uint16) << 8
                    img2 = Image.fromarray(arr2)
                new_img = self._process_image_pair_16bit(img1, img2)
            else:
                # Both 8-bit
                logger.debug("Processing as 8-bit images")
                new_img = self._process_image_pair_8bit(img1, img2)

            # Save thumbnail
            new_img.save(self.filename3)
            logger.debug(f"Saved thumbnail to {self.filename3}")

            # Return array if needed
            if self.size < self.max_thumbnail_size:
                img_array = np.array(new_img)
                logger.debug(f"Created thumbnail shape: {img_array.shape}")
                return img_array

            return None

        except (OSError, ValueError) as e:
            logger.error(
                f"Error creating thumbnail {self.filename3}: {e}\n{traceback.format_exc()}"
            )
            return None
        finally:
            # Periodic garbage collection
            from config.constants import GARBAGE_COLLECTION_INTERVAL

            if self.idx % GARBAGE_COLLECTION_INTERVAL == 0:
                gc.collect()
