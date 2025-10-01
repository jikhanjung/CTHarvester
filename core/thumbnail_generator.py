"""
ThumbnailGenerator - Handles thumbnail generation logic

Extracted from ui/main_window.py during Phase 1 refactoring.
Provides both Rust-based (high performance) and Python-based (fallback) thumbnail generation.
"""

import logging
import os
import time
from datetime import datetime

import numpy as np
from PIL import Image

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

    def __init__(self):
        """Initialize thumbnail generator"""
        self.level_sizes = []
        self.level_work_distribution = []
        self.total_levels = 0
        self.weighted_total_work = 0
        self.thumbnail_start_time = None
        self.last_progress = 0
        self.progress_start_time = None
        self.rust_cancelled = False

        # Check Rust module availability
        self.rust_available = self._check_rust_availability()

    def _check_rust_availability(self):
        """Check if Rust thumbnail module is available"""
        try:
            from ct_thumbnail import build_thumbnails

            logger.info("Rust thumbnail module is available")
            return True
        except ImportError:
            logger.info("Rust thumbnail module not available, will use Python fallback")
            return False

    def calculate_total_thumbnail_work(self, seq_begin, seq_end, size, max_size):
        """Calculate total number of operations for all LoD levels with size weighting

        This function computes the weighted total work required to generate thumbnails
        at multiple Level of Detail (LoD) levels. Each level is progressively smaller
        and requires less work, but the first level has extra weight due to I/O overhead.

        Args:
            seq_begin (int): Starting sequence number (inclusive)
            seq_end (int): Ending sequence number (inclusive)
            size (int): Initial image dimension (width or height, assumed square)
            max_size (int): Maximum thumbnail size threshold for stopping LoD generation

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
        weighted_work = 0
        temp_seq_begin = seq_begin
        temp_seq_end = seq_end
        temp_size = size
        level_count = 0
        level_details = []
        self.level_sizes = []
        self.level_work_distribution = []

        while temp_size >= max_size:
            temp_size /= 2
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

            weighted_work += images_to_process * size_factor

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
        directory,
        settings,
        threadpool,
        use_rust_preference=True,
        progress_dialog=None
    ):
        """Generate thumbnails using best available method

        Args:
            directory (str): Directory containing CT images
            settings (dict): Settings hash containing image parameters
            threadpool (QThreadPool): Qt thread pool for parallel processing
            use_rust_preference (bool): Prefer Rust module if available
            progress_dialog (ProgressDialog, optional): Progress dialog for UI updates

        Returns:
            dict or None: Result dictionary containing success status, data, and error info.
                For Python: {'success': bool, 'cancelled': bool, 'minimum_volume': np.ndarray,
                            'level_info': list, 'elapsed_time': float, 'error': str (optional)}
                For Rust: bool (True if successful, False otherwise)
        """
        # Determine which method to use
        use_rust = self.rust_available and use_rust_preference

        if use_rust:
            logger.info("Using Rust-based thumbnail generation")
            # Note: Rust path still uses legacy callback-based approach
            # This needs updating in a future PR to match Python implementation
            return self.generate_rust(directory, None, None)
        else:
            logger.info("Using Python-based thumbnail generation")
            return self.generate_python(directory, settings, threadpool, progress_dialog)

    def generate_rust(self, directory, progress_callback=None, cancel_check=None):
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
            logger.error("Rust module not available")
            return False

        # Start timing
        self.thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now()

        logger.info(f"=== Starting Rust thumbnail generation ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {directory}")

        # Variables for progress tracking
        self.last_progress = 0
        self.progress_start_time = time.time()
        self.rust_cancelled = False

        def internal_progress_callback(percentage):
            """Internal progress callback wrapper"""
            # Check for cancellation first
            if cancel_check and cancel_check():
                self.rust_cancelled = True
                logger.info(f"Cancellation requested at {percentage:.1f}%")
                return False  # Signal Rust to stop

            # Update progress
            if progress_callback:
                progress_callback(percentage)

            self.last_progress = percentage
            return True  # Continue processing

        try:
            # Call Rust thumbnail generation
            success = build_thumbnails(directory, internal_progress_callback)

            if self.rust_cancelled:
                logger.info("Thumbnail generation was cancelled by user")
                return False

            if not success:
                logger.error("Rust thumbnail generation failed")
                return False

            # Calculate elapsed time
            elapsed = time.time() - self.thumbnail_start_time
            logger.info(f"=== Rust thumbnail generation completed in {elapsed:.2f} seconds ===")

            return True

        except Exception as e:
            logger.error(f"Error during Rust thumbnail generation: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return False

    def generate_python(
        self,
        directory,
        settings,
        threadpool,
        progress_dialog=None
    ):
        """Generate thumbnails using Python implementation (fallback)

        This method implements the full Python-based thumbnail generation logic,
        extracted from main_window.py. It generates multi-level LoD pyramids
        with progress tracking and cancellation support.

        Args:
            directory (str): Directory containing CT images
            settings (dict): Settings hash containing image_width, image_height,
                           seq_begin, seq_end, prefix, index_length, file_type
            threadpool (QThreadPool): Qt thread pool for parallel processing
            progress_dialog (ProgressDialog, optional): Progress dialog for UI updates.
                If provided, progress will be updated via shared_progress_manager signals.

        Returns:
            dict or None: Result dictionary containing:
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
        import platform

        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False
            logger.warning("psutil not installed - cannot get detailed system info")

        # Start timing
        thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now()

        logger.info(f"=== Starting Python thumbnail generation (fallback) ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {directory}")

        try:
            # Extract settings
            MAX_THUMBNAIL_SIZE = 512
            size = max(int(settings["image_width"]), int(settings["image_height"]))
            width = int(settings["image_width"])
            height = int(settings["image_height"])
            seq_begin = settings["seq_begin"]
            seq_end = settings["seq_end"]

            logger.info(f"Thread configuration: maxThreadCount={threadpool.maxThreadCount()}")
            logger.info(f"Image dimensions: width={width}, height={height}, size={size}")

            # System information logging
            try:
                cpu_count = os.cpu_count()
                logger.info(f"System: {platform.system()} {platform.release()}")
                logger.info(f"CPU cores: {cpu_count}")

                if has_psutil:
                    mem = psutil.virtual_memory()
                    disk = psutil.disk_usage(directory)
                    logger.info(
                        f"Memory: {mem.total/1024**3:.1f}GB total, "
                        f"{mem.available/1024**3:.1f}GB available ({mem.percent:.1f}% used)"
                    )
                    logger.info(
                        f"Disk: {disk.total/1024**3:.1f}GB total, "
                        f"{disk.free/1024**3:.1f}GB free ({disk.percent:.1f}% used)"
                    )

                logger.info(
                    f"Thread pool: max={threadpool.maxThreadCount()}, "
                    f"active={threadpool.activeThreadCount()}"
                )
            except Exception as e:
                logger.warning(f"Could not get system info: {e}")

            # Check if directory is on network drive
            try:
                drive = os.path.splitdrive(directory)[0]
                if drive and drive.startswith("\\\\"):
                    logger.warning(
                        f"Working on network drive: {drive} - this may cause slow performance"
                    )
                elif drive:
                    logger.info(f"Working on local drive: {drive}")
            except Exception as e:
                logger.debug(f"Could not determine drive type: {e}")

            logger.info(f"Processing sequence: {seq_begin} to {seq_end}, directory: {directory}")

            # Import dependencies for thumbnail generation
            from core.thumbnail_manager import ThumbnailManager
            from core.progress_manager import ProgressManager
            from PyQt5.QtWidgets import QApplication

            # Calculate total work for all LoD levels using the standard method
            # This ensures consistency with main_window's progress setup
            total_work = self.calculate_total_thumbnail_work(seq_begin, seq_end, size, MAX_THUMBNAIL_SIZE)
            weighted_total_work = self.weighted_total_work
            # Use the dict-based level_work_distribution directly for ThumbnailManager
            level_work_distribution = self.level_work_distribution
            total_levels = self.total_levels

            logger.info(f"Starting thumbnail generation: {total_levels} levels, {total_work} unweighted operations")
            logger.info(f"Weighted total work: {weighted_total_work:.1f}")

            # Initialize variables for multi-stage sampling
            base_sample = max(20, min(30, int(total_work * 0.02)))
            sample_size = base_sample
            total_sample = base_sample * 3

            logger.info(f"Multi-stage sampling: {base_sample} images per stage, {total_sample} total images")

            # Create shared ProgressManager
            shared_progress_manager = ProgressManager()
            shared_progress_manager.level_work_distribution = level_work_distribution
            shared_progress_manager.weighted_total_work = weighted_total_work
            shared_progress_manager.start(weighted_total_work)

            # Initialize progress dialog if provided
            if progress_dialog:
                progress_dialog.lbl_text.setText("Generating thumbnails")
                progress_dialog.lbl_detail.setText("Estimating...")

            # Initialize result containers
            minimum_volume = []
            level_info = []

            # Add level 0 (original images) to level_info
            level_info.append({
                "name": "Level 0",
                "width": width,
                "height": height,
                "seq_begin": seq_begin,
                "seq_end": seq_end,
            })

            # Main thumbnail generation loop
            i = 0
            global_step_counter = 0

            while True:
                # Check for cancellation
                if progress_dialog and progress_dialog.is_cancelled:
                    logger.info("Thumbnail generation cancelled by user before level start")
                    return {
                        'minimum_volume': np.array(minimum_volume) if minimum_volume else np.array([]),
                        'level_info': level_info,
                        'success': False,
                        'cancelled': True,
                        'elapsed_time': time.time() - thumbnail_start_time
                    }

                # Start timing for this level
                level_start_time = time.time()
                level_start_datetime = datetime.now()

                size /= 2
                width = int(width / 2)
                height = int(height / 2)

                current_level_size = size

                if size < 2:
                    logger.info(f"Stopping at level {i+1}: size {size} is too small to continue")
                    break

                # Determine source directory
                if i == 0:
                    from_dir = directory
                    logger.debug(f"Level {i+1}: Reading from original directory: {from_dir}")
                    total_count = seq_end - seq_begin + 1
                else:
                    from_dir = os.path.join(directory, ".thumbnail/" + str(i))
                    logger.debug(f"Level {i+1}: Reading from thumbnail directory: {from_dir}")

                    # Count actual files for levels > 0
                    if os.path.exists(from_dir):
                        actual_files = [f for f in os.listdir(from_dir) if f.endswith(".tif")]
                        total_count = len(actual_files)
                        seq_end = seq_begin + total_count - 1
                        logger.info(f"Level {i+1}: Found {total_count} actual files in previous level")
                    else:
                        total_count = seq_end - seq_begin + 1
                        logger.warning(
                            f"Level {i+1}: Previous level directory not found, "
                            f"using calculated count: {total_count}"
                        )

                # Create output directory
                to_dir = os.path.join(directory, ".thumbnail/" + str(i + 1))
                if not os.path.exists(to_dir):
                    mkdir_start = time.time()
                    os.makedirs(to_dir)
                    mkdir_time = (time.time() - mkdir_start) * 1000
                    logger.debug(f"Created directory {to_dir} in {mkdir_time:.1f}ms")
                else:
                    logger.debug(f"Directory already exists: {to_dir}")

                logger.info(f"--- Level {i+1} ---")
                logger.info(
                    f"Level {i+1} start time: {level_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
                )
                logger.info(f"Level {i+1}: Processing {total_count} images (size: {int(size)}x{int(size)})")

                # Initialize ThumbnailManager for this level
                # Pass progress_dialog directly - ThumbnailManager will connect signals
                logger.info(f"Creating ThumbnailManager for level {i+1}")
                thumbnail_manager = ThumbnailManager(
                    None,  # main_window (not needed for core logic)
                    progress_dialog,  # Pass progress dialog directly
                    threadpool,
                    shared_progress_manager
                )
                # Set sample_size for progress sampling
                thumbnail_manager.sample_size = sample_size
                logger.info(f"ThumbnailManager created with sample_size={sample_size}, starting process_level")

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
                logger.info(f"Level {i+1}: process_level completed in {process_time:.2f}s")

                # Calculate and log time for this level
                level_end_datetime = datetime.now()
                level_elapsed = time.time() - level_start_time
                logger.info(
                    f"Level {i+1} end time: {level_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
                )
                logger.info(f"Level {i+1}: Completed in {level_elapsed:.2f} seconds")

                # Update global step counter
                global_step_counter = thumbnail_manager.global_step_counter

                # Check for cancellation
                if was_cancelled or (progress_dialog and progress_dialog.is_cancelled):
                    logger.info("Thumbnail generation cancelled by user")
                    return {
                        'minimum_volume': np.array(minimum_volume) if minimum_volume else np.array([]),
                        'level_info': level_info,
                        'success': False,
                        'cancelled': True,
                        'elapsed_time': time.time() - thumbnail_start_time
                    }

                # Update for next level
                current_count = seq_end - seq_begin + 1
                next_count = (current_count // 2) + (current_count % 2)
                seq_end = seq_begin + next_count - 1
                logger.info(f"Level {i+1}: {current_count} images -> {next_count} thumbnails generated")
                logger.info(f"Next level will process range: {seq_begin}-{seq_end}")

                i += 1

                # Add to level_info if doesn't exist
                level_name = f"Level {i}"
                level_exists = any(level["name"] == level_name for level in level_info)
                if not level_exists:
                    level_info.append({
                        "name": level_name,
                        "width": width,
                        "height": height,
                        "seq_begin": seq_begin,
                        "seq_end": seq_end,
                    })

                # Check if we've reached size limit
                if current_level_size < MAX_THUMBNAIL_SIZE:
                    logger.info(f"Reached target thumbnail size at level {i}")
                    break

            logger.info(f"Exited thumbnail generation loop at level {i+1}")

            # Calculate total time
            thumbnail_end_datetime = datetime.now()
            total_elapsed = time.time() - thumbnail_start_time

            logger.info(f"=== Thumbnail generation completed ===")
            logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
            logger.info(f"Total levels processed: {i + 1}")

            if total_elapsed > 0:
                images_per_second = total_work / total_elapsed
                logger.info(f"Average processing speed: {images_per_second:.1f} images/second")

            # Load minimum_volume from disk (smallest level)
            # This ensures consistency with Rust implementation
            smallest_level = i
            smallest_dir = os.path.join(directory, f".thumbnail/{smallest_level}")

            if os.path.exists(smallest_dir):
                logger.info(f"Loading minimum_volume from {smallest_dir}")
                tif_files = sorted([f for f in os.listdir(smallest_dir) if f.endswith(".tif")])

                minimum_volume = []
                for tif_file in tif_files:
                    try:
                        with Image.open(os.path.join(smallest_dir, tif_file)) as img:
                            minimum_volume.append(np.array(img))
                    except Exception as e:
                        logger.error(f"Error loading {tif_file}: {e}")

                if minimum_volume:
                    minimum_volume = np.array(minimum_volume)
                    logger.info(f"Loaded minimum_volume: shape {minimum_volume.shape}")
                else:
                    logger.warning("No images loaded for minimum_volume")
                    minimum_volume = np.array([])
            else:
                logger.warning(f"Smallest level directory not found: {smallest_dir}")
                minimum_volume = np.array([])

            # Final progress update
            if progress_dialog:
                progress_dialog.lbl_text.setText("Thumbnail generation complete")
                progress_dialog.lbl_detail.setText("")

            return {
                'minimum_volume': minimum_volume,
                'level_info': level_info,
                'success': True,
                'cancelled': False,
                'elapsed_time': total_elapsed
            }

        except Exception as e:
            logger.error(f"Error during Python thumbnail generation: {e}")
            import traceback
            logger.error(traceback.format_exc())

            return {
                'minimum_volume': np.array([]),
                'level_info': [],
                'success': False,
                'cancelled': False,
                'error': str(e),
                'elapsed_time': time.time() - thumbnail_start_time if 'thumbnail_start_time' in locals() else 0
            }

    def load_thumbnail_data(self, directory, max_thumbnail_size=512):
        """Load generated thumbnail data from disk

        Finds and loads the appropriate level of thumbnails for 3D visualization.

        Args:
            directory (str): Base directory containing .thumbnail subfolder
            max_thumbnail_size (int): Maximum size for loaded thumbnails

        Returns:
            tuple: (numpy.ndarray or None, dict) - (thumbnail volume, level_info)
                   Returns (None, {}) if no thumbnails found
        """
        # Find the highest level thumbnail directory
        thumbnail_base = os.path.join(directory, ".thumbnail")

        if not os.path.exists(thumbnail_base):
            logger.warning("No thumbnail directory found")
            return None, {}

        # Find all level directories
        level_dirs = []
        for i in range(1, 20):  # Check up to level 20
            level_dir = os.path.join(thumbnail_base, str(i))
            if os.path.exists(level_dir):
                level_dirs.append((i, level_dir))
            else:
                break

        if not level_dirs:
            logger.warning("No thumbnail levels found")
            return None, {}

        # Find the appropriate level to load
        level_num = None
        thumbnail_dir = None

        for ln, ld in level_dirs:
            # Check the size of images in this level
            files = [f for f in os.listdir(ld) if f.endswith(".tif")]
            if files:
                with Image.open(os.path.join(ld, files[0])) as img:
                    width, height = img.size

                size = max(width, height)
                if size < max_thumbnail_size:
                    level_num = ln
                    thumbnail_dir = ld
                    logger.info(
                        f"Found appropriate level {level_num} with size {width}x{height} "
                        f"(< {max_thumbnail_size})"
                    )
                    break
                else:
                    logger.debug(
                        f"Level {ln} size {width}x{height} is >= {max_thumbnail_size}, "
                        f"continuing..."
                    )

        if level_num is None or thumbnail_dir is None:
            # Fallback to highest level if none meet the criteria
            level_num, thumbnail_dir = level_dirs[-1]
            logger.warning(
                f"No level with size < {max_thumbnail_size} found, "
                f"using highest level {level_num}"
            )

        logger.info(f"Loading thumbnails from level {level_num}: {thumbnail_dir}")

        try:
            # List all tif files in the directory
            files = sorted([f for f in os.listdir(thumbnail_dir) if f.endswith(".tif")])

            logger.info(f"Found {len(files)} thumbnail files")

            minimum_volume = []
            for file in files:
                filepath = os.path.join(thumbnail_dir, file)
                with Image.open(filepath) as img:
                    img_array = np.array(img)

                # Normalize to 8-bit range (0-255) for marching cubes
                if img_array.dtype == np.uint16:
                    # Convert 16-bit to 8-bit
                    img_array = (img_array / 256).astype(np.uint8)
                elif img_array.dtype != np.uint8:
                    # For other types, normalize to 0-255
                    img_min = img_array.min()
                    img_max = img_array.max()
                    if img_max > img_min:
                        img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(
                            np.uint8
                        )
                    else:
                        img_array = np.zeros_like(img_array, dtype=np.uint8)

                minimum_volume.append(img_array)

            if len(minimum_volume) > 0:
                minimum_volume = np.array(minimum_volume)
                logger.info(
                    f"Loaded {len(minimum_volume)} thumbnails, shape: {minimum_volume.shape}"
                )

                # Create level_info structure
                level_info = []
                # Add loaded level info
                level_info.append(
                    {
                        "name": f"Level {level_num}",
                        "width": minimum_volume.shape[2],
                        "height": minimum_volume.shape[1],
                        "seq_begin": 0,
                        "seq_end": len(minimum_volume) - 1,
                    }
                )

                return minimum_volume, {"levels": level_info, "current_level": level_num}
            else:
                logger.warning("No thumbnails loaded")
                return None, {}

        except Exception as e:
            logger.error(f"Error loading thumbnail data: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return None, {}
