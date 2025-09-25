from PyQt5.QtGui import QIcon, QColor, QPainter, QPen, QPixmap, QPainter, QMouseEvent, QResizeEvent, QImage, QCursor, QFont, QFontMetrics
from PyQt5.QtWidgets import QMainWindow, QApplication, QAbstractItemView, QRadioButton, QComboBox, \
                            QFileDialog, QWidget, QHBoxLayout, QVBoxLayout, QProgressBar, QApplication, \
                            QDialog, QLineEdit, QLabel, QPushButton, QAbstractItemView, \
                            QSizePolicy, QGroupBox, QListWidget, QFormLayout, QCheckBox, QMessageBox, QSlider
from PyQt5.QtCore import Qt, QRect, QPoint, QSettings, QTranslator, QMargins, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QEvent, QThread, QMutex, QMutexLocker
#from PyQt5.QtCore import QT_TR_NOOP as tr
from PyQt5.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from queue import Queue

from vertical_stack_slider import VerticalTimeline

import os, sys, re
from PIL import Image, ImageChops
import numpy as np
import mcubes
from scipy import ndimage  # For interpolation
import math
from copy import deepcopy
import datetime

def value_to_bool(value):
    return value.lower() == 'true' if isinstance(value, str) else bool(value)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

MODE = {}
MODE['VIEW'] = 0
MODE['ADD_BOX'] = 1
MODE['MOVE_BOX'] = 2
MODE['EDIT_BOX'] = 3
MODE['EDIT_BOX_READY'] = 4
MODE['EDIT_BOX_PROGRESS'] = 5
MODE['MOVE_BOX_PROGRESS'] = 6
MODE['MOVE_BOX_READY'] = 7
DISTANCE_THRESHOLD = 10
COMPANY_NAME = "PaleoBytes"
try:
    from version import __version__ as PROGRAM_VERSION
except ImportError:
    PROGRAM_VERSION = "0.2.0"  # Fallback version

PROGRAM_NAME = "CTHarvester"
PROGRAM_AUTHOR = "Jikhan Jung"

# Build-time year for copyright
BUILD_YEAR = 2025  # This will be set during build
PROGRAM_COPYRIGHT = f"© 2023-{BUILD_YEAR} Jikhan Jung"

# Directory setup
USER_PROFILE_DIRECTORY = os.path.expanduser('~')
DEFAULT_DB_DIRECTORY = os.path.join(USER_PROFILE_DIRECTORY, COMPANY_NAME, PROGRAM_NAME)
DEFAULT_STORAGE_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "data/")
DEFAULT_LOG_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "logs/")
DB_BACKUP_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "backups/")

def ensure_directories():
    """Safely create necessary directories with error handling."""
    directories = [
        DEFAULT_DB_DIRECTORY,
        DEFAULT_STORAGE_DIRECTORY,
        DEFAULT_LOG_DIRECTORY,
        DB_BACKUP_DIRECTORY
    ]
    
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Use print here since logger might not be initialized yet
            print(f"Warning: Could not create directory {directory}: {e}")
            # Don't fail completely, let the application try to continue

# Try to create directories on import, but don't fail if it doesn't work
try:
    ensure_directories()
except Exception as e:
    # Use print here since logger might not be initialized yet
    print(f"Warning: Directory initialization failed: {e}")
    pass

# Setup logger
from CTLogger import setup_logger
logger = setup_logger(PROGRAM_NAME)

OBJECT_MODE = 1
VIEW_MODE = 1
PAN_MODE = 2
ROTATE_MODE = 3
ZOOM_MODE = 4
MOVE_3DVIEW_MODE = 5

ROI_BOX_RESOLUTION = 50.0

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        #self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            #traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class ThumbnailWorkerSignals(QObject):
    """Signals for thumbnail worker threads"""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)  # (idx, img_array or None, was_generated)
    progress = pyqtSignal(int)  # idx


class ThumbnailWorker(QRunnable):
    """Worker thread for processing individual thumbnail image pairs"""

    def __init__(self, idx, seq, seq_begin, from_dir, to_dir, settings_hash, size, max_thumbnail_size, progress_dialog, level=0):
        super(ThumbnailWorker, self).__init__()

        self.idx = idx
        self.seq = seq
        self.seq_begin = seq_begin
        self.from_dir = from_dir
        self.to_dir = to_dir
        self.settings_hash = settings_hash
        self.size = size
        self.max_thumbnail_size = max_thumbnail_size
        self.progress_dialog = progress_dialog
        self.signals = ThumbnailWorkerSignals()
        self.level = level  # Track which level this worker belongs to
        
        # Generate filenames
        self.filename1 = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        self.filename2 = self.settings_hash['prefix'] + str(seq+1).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        # Match Rust naming: simple sequential numbering without prefix
        self.filename3 = os.path.join(to_dir, "{:06}.tif".format(idx))

    @pyqtSlot()
    def run(self):
        """Process a single image pair"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"ThumbnailWorker.run: Starting Level {self.level+1} worker for idx={self.idx}, seq={self.seq}")
        
        try:
            # Check for cancellation before starting work
            if self.progress_dialog.is_cancelled:
                logger.debug(f"ThumbnailWorker.run: Cancelled before start, idx={self.idx}")
                return
                
            img_array = None
            was_generated = False  # Track if we generated or loaded

            # Check if thumbnail already exists
            if os.path.exists(self.filename3):
                logger.debug(f"Found existing thumbnail: {self.filename3}")
                was_generated = False  # Loaded from disk
                if self.size < self.max_thumbnail_size:
                    try:
                        img = Image.open(self.filename3)
                        img_array = np.array(img)
                        logger.debug(f"Loaded existing thumbnail shape: {img_array.shape}")
                    except Exception as e:
                        logger.error(f"Error opening existing thumbnail {self.filename3}: {e}")
            else:
                # Check for cancellation before expensive image processing
                if self.progress_dialog.is_cancelled:
                    return
                    
                # Create new thumbnail
                was_generated = True  # We're generating a new thumbnail
                img1 = None
                img1_is_16bit = False
                if os.path.exists(os.path.join(self.from_dir, self.filename1)):
                    try:
                        img1 = Image.open(os.path.join(self.from_dir, self.filename1))
                        # Check if 16-bit image
                        if img1.mode == 'I;16' or img1.mode == 'I;16L' or img1.mode == 'I;16B':
                            img1_is_16bit = True
                            # Keep as 16-bit, don't convert
                        elif img1.mode[0] == 'I':
                            # Some other I mode, convert to L
                            img1 = img1.convert('L')
                        elif img1.mode == 'P':
                            img1 = img1.convert('L')
                        # For L (8-bit grayscale), keep as is
                    except Exception as e:
                        logger.error(f"Error processing image {self.filename1}: {e}")
                        img1 = None

                img2 = None
                img2_is_16bit = False
                if os.path.exists(os.path.join(self.from_dir, self.filename2)):
                    try:
                        img2 = Image.open(os.path.join(self.from_dir, self.filename2))
                        # Check if 16-bit image
                        if img2.mode == 'I;16' or img2.mode == 'I;16L' or img2.mode == 'I;16B':
                            img2_is_16bit = True
                            # Keep as 16-bit, don't convert
                        elif img2.mode[0] == 'I':
                            # Some other I mode, convert to L
                            img2 = img2.convert('L')
                        elif img2.mode == 'P':
                            img2 = img2.convert('L')
                        # For L (8-bit grayscale), keep as is
                    except Exception as e:
                        logger.error(f"Error processing image {self.filename2}: {e}")
                        img2 = None

                # Average two images preserving bit depth
                if img1 is not None and img2 is not None:
                    try:
                        # If both are 16-bit, process as 16-bit
                        if img1_is_16bit and img2_is_16bit:
                            # Process as 16-bit numpy arrays
                            arr1 = np.array(img1, dtype=np.uint16)
                            arr2 = np.array(img2, dtype=np.uint16)

                            # Average the two arrays
                            avg_arr = ((arr1.astype(np.uint32) + arr2.astype(np.uint32)) // 2).astype(np.uint16)

                            # Downscale by 2x2 averaging
                            h, w = avg_arr.shape
                            new_h, new_w = h // 2, w // 2
                            downscaled = np.zeros((new_h, new_w), dtype=np.uint16)

                            for y in range(new_h):
                                for x in range(new_w):
                                    y0, x0 = y * 2, x * 2
                                    # Average 2x2 block
                                    block_sum = (avg_arr[y0, x0].astype(np.uint32) +
                                               avg_arr[y0, x0+1].astype(np.uint32) +
                                               avg_arr[y0+1, x0].astype(np.uint32) +
                                               avg_arr[y0+1, x0+1].astype(np.uint32))
                                    downscaled[y, x] = (block_sum // 4).astype(np.uint16)

                            # Save as 16-bit image
                            new_img_ops = Image.fromarray(downscaled, mode='I;16')
                            new_img_ops.save(self.filename3)

                        # If either is 16-bit, convert both to 16-bit
                        elif img1_is_16bit or img2_is_16bit:
                            # Convert to 16-bit arrays
                            if img1_is_16bit:
                                arr1 = np.array(img1, dtype=np.uint16)
                            else:
                                arr1 = (np.array(img1, dtype=np.uint8).astype(np.uint16) << 8)

                            if img2_is_16bit:
                                arr2 = np.array(img2, dtype=np.uint16)
                            else:
                                arr2 = (np.array(img2, dtype=np.uint8).astype(np.uint16) << 8)

                            # Average the two arrays
                            avg_arr = ((arr1.astype(np.uint32) + arr2.astype(np.uint32)) // 2).astype(np.uint16)

                            # Downscale by 2x2 averaging
                            h, w = avg_arr.shape
                            new_h, new_w = h // 2, w // 2
                            downscaled = np.zeros((new_h, new_w), dtype=np.uint16)

                            for y in range(new_h):
                                for x in range(new_w):
                                    y0, x0 = y * 2, x * 2
                                    # Average 2x2 block
                                    block_sum = (avg_arr[y0, x0].astype(np.uint32) +
                                               avg_arr[y0, x0+1].astype(np.uint32) +
                                               avg_arr[y0+1, x0].astype(np.uint32) +
                                               avg_arr[y0+1, x0+1].astype(np.uint32))
                                    downscaled[y, x] = (block_sum // 4).astype(np.uint16)

                            # Save as 16-bit image
                            new_img_ops = Image.fromarray(downscaled, mode='I;16')
                            new_img_ops.save(self.filename3)

                        else:
                            # Both are 8-bit, use existing method
                            from PIL import ImageChops
                            new_img_ops = ImageChops.add(img1, img2, scale=2.0)
                            # Resize to half
                            new_img_ops = new_img_ops.resize((int(img1.width / 2), int(img1.height / 2)))
                            # Save to temporary directory
                            new_img_ops.save(self.filename3)
                        
                        if self.size < self.max_thumbnail_size:
                            img_array = np.array(new_img_ops)
                            logger.debug(f"Created new thumbnail shape: {img_array.shape}")
                            
                    except Exception as e:
                        logger.error(f"Error creating thumbnail {self.filename3}: {e}")
            
            # Emit progress signal first
            logger.debug(f"ThumbnailWorker.run: Emitting progress for idx={self.idx}")
            self.signals.progress.emit(self.idx)
            # Then emit result with generation flag
            logger.debug(f"ThumbnailWorker.run: Emitting result for idx={self.idx}, has_image={img_array is not None}, was_generated={was_generated}")
            self.signals.result.emit((self.idx, img_array, was_generated))
            
        except Exception as e:
            import traceback
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            # Always emit finished signal
            logger.debug(f"ThumbnailWorker.run: Finished worker for idx={self.idx}")
            self.signals.finished.emit()


class ThumbnailManager(QObject):
    """Manager class to coordinate multiple thumbnail workers and progress tracking"""

    def __init__(self, parent, progress_dialog, threadpool):
        super().__init__()
        self.parent = parent
        self.progress_dialog = progress_dialog
        self.threadpool = threadpool

        # Progress tracking
        self.total_tasks = 0
        self.completed_tasks = 0
        self.global_step_counter = 0
        self.level = 0
        self.results = {}  # idx -> img_array
        self.is_cancelled = False

        # Synchronization
        self.lock = QMutex()

        # Dynamic time estimation
        self.sample_start_time = None
        self.images_per_second = None
        self.is_sampling = False

        # Track actual generation vs loading
        self.generated_count = 0  # Number of thumbnails actually generated
        self.loaded_count = 0      # Number of thumbnails loaded from disk

        # Get sample_size from parent if it exists (for first level sampling)
        self.sample_size = getattr(parent, 'sample_size', 0)

        # Inherit performance data from parent if exists (from previous levels)
        if hasattr(parent, 'measured_images_per_second'):
            self.images_per_second = parent.measured_images_per_second
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"ThumbnailManager created: sample_size={self.sample_size}, inherited speed={self.images_per_second:.1f} img/s")
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"ThumbnailManager created: sample_size={self.sample_size}, no inherited speed")

    def update_eta_and_progress(self):
        """Centralized method to update ETA and progress display"""
        import time
        import logging
        logger = logging.getLogger(__name__)

        if not self.progress_dialog or not hasattr(self.progress_dialog, 'lbl_detail'):
            return

        # Build progress detail text
        detail_text = f"Level {self.level+1}: {self.completed_tasks}/{self.total_tasks}"

        # If still sampling, show "Estimating..."
        if self.is_sampling:
            self.progress_dialog.lbl_detail.setText(f"Estimating... - {detail_text}")
            return

        # If we don't have performance data yet, just show progress
        if self.images_per_second is None:
            self.progress_dialog.lbl_detail.setText(detail_text)
            return

        # Calculate ETA based on current performance and global work amount
        global_total = self.parent.progress_dialog.total_steps if hasattr(self.parent.progress_dialog, 'total_steps') else self.total_tasks
        global_completed = self.global_step_counter  # This is the global counter, not per-level
        global_remaining = global_total - global_completed

        if global_remaining <= 0:
            self.progress_dialog.lbl_detail.setText(f"Completing... - {detail_text}")
            return

        # Calculate blended speed based on global progress
        # Since total_steps already includes weighted work (size-based),
        # we use the speed as-is without level adjustment
        elapsed_time = time.time() - self.parent.thumbnail_start_time if hasattr(self.parent, 'thumbnail_start_time') else 0
        if elapsed_time > 0 and global_completed > 0:
            # Actual speed in weighted units per second
            actual_speed = global_completed / elapsed_time
            # Blend with initial measured speed (also in weighted units)
            progress_ratio = global_completed / global_total if global_total > 0 else 0
            weight = min(0.7, progress_ratio * 0.7)  # Up to 70% weight on actual
            blended_speed = actual_speed * weight + self.images_per_second * (1 - weight)
        else:
            blended_speed = self.images_per_second

        # Calculate remaining time based on weighted work amount
        remaining_time = global_remaining / blended_speed if blended_speed > 0 else 0

        # Format ETA
        if remaining_time < 60:
            eta_text = f"{int(remaining_time)}s"
        elif remaining_time < 3600:
            eta_text = f"{int(remaining_time/60)}m {int(remaining_time%60)}s"
        else:
            eta_text = f"{int(remaining_time/3600)}h {int((remaining_time%3600)/60)}m"

        # Update display
        self.progress_dialog.lbl_detail.setText(f"ETA: {eta_text} - {detail_text}")

        # Log periodically (every 10% of progress)
        if self.completed_tasks % max(1, int(self.total_tasks * 0.1)) == 0:
            logger.debug(f"Progress update: ETA={eta_text}, {detail_text}, speed={blended_speed:.1f} img/s")

    def process_level(self, level, from_dir, to_dir, seq_begin, seq_end, settings_hash, size, max_thumbnail_size, global_step_offset):
        """Process a complete thumbnail level using multiple worker threads"""
        import logging
        import time
        logger = logging.getLogger(__name__)

        self.level = level
        self.global_step_counter = global_step_offset

        # Get weight factor for this level from parent's level_work_distribution
        self.level_weight = 1.0  # Default
        if hasattr(self.parent, 'level_work_distribution'):
            for level_info in self.parent.level_work_distribution:
                if level_info['level'] == level + 1:  # level is 0-indexed, but stored as 1-indexed
                    self.level_weight = level_info['weight']
                    logger.info(f"Level {level+1}: Using weight factor {self.level_weight:.2f}")
                    break
        self.results.clear()
        self.is_cancelled = False

        # Calculate number of tasks
        total_count = seq_end - seq_begin + 1
        num_tasks = int(total_count / 2)
        self.total_tasks = num_tasks
        self.completed_tasks = 0

        # Enable sampling for level 0 (first level)
        logger.info(f"Sampling check: level={level}, sample_size={self.sample_size}")
        if level == 0 and self.sample_size > 0:
            self.is_sampling = True
            self.sample_start_time = time.time()
            logger.info(f"Level {level+1}: Starting with performance sampling (first {self.sample_size} images)")
        else:
            logger.info(f"Not sampling: level={level} (need 0), sample_size={self.sample_size} (need >0)")

        logger.info(f"ThumbnailManager.process_level: Starting Level {level+1}, tasks={num_tasks}, offset={global_step_offset}")
        logger.debug(f"ThreadPool: maxThreadCount={self.threadpool.maxThreadCount()}, activeThreadCount={self.threadpool.activeThreadCount()}")
        
        # Ensure threadpool has enough threads
        if self.threadpool.maxThreadCount() < 4:
            self.threadpool.setMaxThreadCount(4)
            logger.info(f"Increased threadpool max threads to {self.threadpool.maxThreadCount()}")

        # Wait for any previous level's workers to complete
        if self.threadpool.activeThreadCount() > 0:
            logger.info(f"Waiting for {self.threadpool.activeThreadCount()} active threads from previous level to complete...")
            wait_start = time.time()
            while self.threadpool.activeThreadCount() > 0 and time.time() - wait_start < 30:
                QApplication.processEvents()
                QThread.msleep(100)
            if self.threadpool.activeThreadCount() > 0:
                logger.warning(f"Still {self.threadpool.activeThreadCount()} active threads after 30s wait")
        
        # Create and submit workers
        workers_submitted = 0
        for idx in range(num_tasks):
            if self.progress_dialog.is_cancelled:
                self.is_cancelled = True
                break
                
            seq = seq_begin + (idx * 2)
            
            # Create worker with level information
            worker = ThumbnailWorker(
                idx, seq, seq_begin, from_dir, to_dir,
                settings_hash, size, max_thumbnail_size, self.progress_dialog, level
            )
            
            # Connect signals with Qt.QueuedConnection to ensure thread safety
            worker.signals.progress.connect(self.on_worker_progress, Qt.QueuedConnection)
            worker.signals.result.connect(self.on_worker_result, Qt.QueuedConnection) 
            worker.signals.error.connect(self.on_worker_error, Qt.QueuedConnection)
            worker.signals.finished.connect(self.on_worker_finished, Qt.QueuedConnection)
            
            # Submit to thread pool
            self.threadpool.start(worker)
            workers_submitted += 1
            
            # Process events periodically to keep UI responsive
            if workers_submitted % 10 == 0:
                QApplication.processEvents()
                logger.debug(f"Submitted {workers_submitted}/{num_tasks} workers")
        
        logger.info(f"Submitted {workers_submitted} workers to threadpool")
        
        # Wait for all workers to complete or cancellation
        import time
        start_wait = time.time()
        last_progress_log = time.time()
        last_detailed_log = time.time()
        stalled_count = 0
        last_completed_count = self.completed_tasks

        while self.completed_tasks < self.total_tasks and not self.progress_dialog.is_cancelled:
            QApplication.processEvents()

            current_time = time.time()

            # Log progress periodically
            if current_time - last_progress_log > 5:  # Every 5 seconds
                active_threads = self.threadpool.activeThreadCount()
                elapsed = current_time - start_wait
                progress_pct = (self.completed_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0

                logger.debug(f"Level {level+1}: {self.completed_tasks}/{self.total_tasks} ({progress_pct:.1f}%) completed, "
                           f"{active_threads} active threads, elapsed: {elapsed:.1f}s")
                last_progress_log = current_time

                # Check if progress is stalled
                if self.completed_tasks == last_completed_count:
                    stalled_count += 1
                    if stalled_count >= 12:  # No progress for 60 seconds
                        logger.warning(f"Level {level+1}: No progress for 60 seconds. {active_threads} threads still active")
                        # Log more details every 30 seconds when stalled
                        if current_time - last_detailed_log > 30:
                            logger.info(f"Level {level+1} status: {self.completed_tasks}/{self.total_tasks} tasks completed after {elapsed:.1f}s")
                            logger.info(f"Consider checking disk I/O performance or available storage space")
                            last_detailed_log = current_time
                else:
                    stalled_count = 0
                    last_completed_count = self.completed_tasks

            QThread.msleep(10)  # Reduced delay for better responsiveness
        
        if self.progress_dialog.is_cancelled:
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
        if not self.is_cancelled:
            avg_time_per_task = total_time / self.total_tasks if self.total_tasks > 0 else 0
            tasks_per_second = self.total_tasks / total_time if total_time > 0 else 0
            generation_ratio = self.generated_count / self.total_tasks * 100 if self.total_tasks > 0 else 0

            logger.info(f"ThumbnailManager.process_level: Level {level+1} completed successfully")
            logger.info(f"  - Tasks completed: {self.completed_tasks}/{self.total_tasks}")
            logger.info(f"  - Generated: {self.generated_count}, Loaded: {self.loaded_count} ({generation_ratio:.1f}% generated)")
            logger.info(f"  - Images collected: {len(img_arrays)}")
            logger.info(f"  - Total time: {total_time:.2f}s")
            logger.info(f"  - Average: {avg_time_per_task:.3f}s per task, {tasks_per_second:.1f} tasks/second")

            # Store generation ratio for coefficient calculation decision
            self.generation_ratio = generation_ratio
        
        return img_arrays, self.is_cancelled
    
    @pyqtSlot(int)
    def on_worker_progress(self, idx):
        """Handle progress updates from worker threads"""
        import logging
        logger = logging.getLogger(__name__)

        with QMutexLocker(self.lock):
            # Increment by weight factor to account for different processing costs per level
            self.global_step_counter += self.level_weight
            current_step = self.global_step_counter

        # Update progress bar
        self.progress_dialog.lbl_text.setText(f"Generating thumbnails")
        if hasattr(self.parent.progress_dialog, 'total_steps') and self.parent.progress_dialog.total_steps > 0:
            percentage = int((current_step / self.parent.progress_dialog.total_steps) * 100)
            self.progress_dialog.pb_progress.setValue(percentage)

        # Use centralized ETA and progress update
        self.update_eta_and_progress()

        # Process events periodically to keep UI responsive
        if current_step % 10 == 0:
            QApplication.processEvents()

        logger.debug(f"ThumbnailManager.on_worker_progress: Level {self.level+1}, idx={idx}, step={current_step}")
    
    @pyqtSlot(object)
    def on_worker_result(self, result):
        """Handle results from worker threads"""
        import logging
        import time
        logger = logging.getLogger(__name__)

        # Unpack result with generation flag
        if len(result) == 3:
            idx, img_array, was_generated = result
        else:
            # Backward compatibility
            idx, img_array = result
            was_generated = False

        with QMutexLocker(self.lock):
            self.results[idx] = img_array
            self.completed_tasks += 1
            completed = self.completed_tasks
            total = self.total_tasks

            # Track generation vs loading
            if was_generated:
                self.generated_count += 1
            else:
                self.loaded_count += 1

            # Multi-stage sampling for better accuracy
            # Stage 1: Initial sampling (first sample_size images)
            if self.is_sampling and self.level == 0 and completed == self.sample_size:
                sample_elapsed = time.time() - self.sample_start_time
                time_per_image = sample_elapsed / self.sample_size

                # First estimate
                level1_time = total * time_per_image
                total_estimate = level1_time
                remaining_time = level1_time
                for i in range(1, self.parent.total_levels):
                    remaining_time *= 0.25
                    total_estimate += remaining_time

                if total_estimate < 60:
                    formatted = f"{int(total_estimate)}s"
                elif total_estimate < 3600:
                    formatted = f"{int(total_estimate/60)}m {int(total_estimate%60)}s"
                else:
                    formatted = f"{int(total_estimate/3600)}h {int((total_estimate%3600)/60)}m"

                logger.info(f"=== Stage 1 Sampling ({self.sample_size} images in {sample_elapsed:.2f}s) ===")
                logger.info(f"Speed: {time_per_image:.3f}s per image")
                logger.info(f"Initial estimate: {formatted} ({total_estimate:.1f}s)")

                # Store for comparison
                self.stage1_estimate = total_estimate
                self.stage1_speed = time_per_image

            # Stage 2: Extended sampling (after 2x sample_size)
            elif self.is_sampling and self.level == 0 and completed == self.sample_size * 2:
                sample_elapsed = time.time() - self.sample_start_time
                time_per_image = sample_elapsed / (self.sample_size * 2)

                # Second estimate
                level1_time = total * time_per_image
                total_estimate = level1_time
                remaining_time = level1_time
                for i in range(1, self.parent.total_levels):
                    remaining_time *= 0.25
                    total_estimate += remaining_time

                if total_estimate < 60:
                    formatted = f"{int(total_estimate)}s"
                elif total_estimate < 3600:
                    formatted = f"{int(total_estimate/60)}m {int(total_estimate%60)}s"
                else:
                    formatted = f"{int(total_estimate/3600)}h {int((total_estimate%3600)/60)}m"

                logger.info(f"=== Stage 2 Sampling ({self.sample_size * 2} images in {sample_elapsed:.2f}s) ===")
                logger.info(f"Speed: {time_per_image:.3f}s per image")
                logger.info(f"Revised estimate: {formatted} ({total_estimate:.1f}s)")

                # Compare with stage 1
                if hasattr(self, 'stage1_estimate'):
                    diff_percent = ((total_estimate - self.stage1_estimate) / self.stage1_estimate) * 100
                    logger.info(f"Difference from stage 1: {diff_percent:+.1f}%")
                    speed_change = ((time_per_image - self.stage1_speed) / self.stage1_speed) * 100
                    logger.info(f"Speed change: {speed_change:+.1f}%")

                # Store stage 2 results
                self.stage2_estimate = total_estimate

            # Stage 3: Final sampling (after 3x sample_size)
            elif self.is_sampling and self.level == 0 and completed >= self.sample_size * 3:
                sample_elapsed = time.time() - self.sample_start_time

                # Calculate weighted units per second
                weighted_units_completed = (self.sample_size * 3) * self.level_weight
                self.images_per_second = weighted_units_completed / sample_elapsed if sample_elapsed > 0 else 20

                # Calculate time per image from sampling
                time_per_image = sample_elapsed / (self.sample_size * 3)

                # Final estimate
                level1_time = total * time_per_image
                total_estimate = level1_time
                remaining_time = level1_time
                for i in range(1, self.parent.total_levels):
                    remaining_time *= 0.25
                    total_estimate += remaining_time

                logger.info(f"=== Stage 3 Sampling ({self.sample_size * 3} images in {sample_elapsed:.2f}s) ===")
                logger.info(f"Speed: {time_per_image:.3f}s per image")
                logger.info(f"Performance sampling complete: {self.images_per_second:.1f} weighted units/second")

                # Compare all stages
                if hasattr(self, 'stage1_estimate') and hasattr(self, 'stage2_estimate'):
                    logger.info(f"Estimate progression: Stage1={self.stage1_estimate:.1f}s -> Stage2={self.stage2_estimate:.1f}s -> Stage3={total_estimate:.1f}s")

                    # If estimates are increasing significantly, apply adjustment
                    if total_estimate > self.stage1_estimate * 1.5:
                        # Trend suggests further slowdown, apply correction
                        trend_factor = total_estimate / self.stage1_estimate
                        adjusted_estimate = total_estimate * (1 + (trend_factor - 1) * 0.3)  # Apply 30% of the trend
                        logger.info(f"Trend adjustment applied: {total_estimate:.1f}s -> {adjusted_estimate:.1f}s")
                        total_estimate = adjusted_estimate

                storage_type = 'SSD' if self.images_per_second > 10 else 'HDD' if self.images_per_second > 2 else 'Network/Slow'
                drive_label = f"{self.parent.current_drive}" if hasattr(self.parent, 'current_drive') else "unknown"
                logger.info(f"Drive {drive_label} estimated as: {storage_type}")

                # Log the final estimated time
                if total_estimate < 60:
                    formatted_estimate = f"{int(total_estimate)}s"
                elif total_estimate < 3600:
                    formatted_estimate = f"{int(total_estimate/60)}m {int(total_estimate%60)}s"
                else:
                    formatted_estimate = f"{int(total_estimate/3600)}h {int((total_estimate%3600)/60)}m"
                logger.info(f"=== FINAL ESTIMATED TOTAL TIME: {formatted_estimate} ===")

                # Store sampled estimate for comparison
                self.parent.sampled_estimate_seconds = total_estimate
                self.parent.sampled_estimate_str = formatted_estimate

                # Update parent's estimate and save performance data for next levels
                self.parent.estimated_time_per_image = 1.0 / self.images_per_second if self.images_per_second > 0 else 0.05
                self.parent.estimated_total_time = total_estimate
                self.parent.measured_images_per_second = self.images_per_second

                self.is_sampling = False
                logger.info(f"Multi-stage sampling completed")

            # Always update ETA and progress display
            self.update_eta_and_progress()

        # Just log the result, don't update UI (already done in on_worker_progress)
        logger.debug(f"ThumbnailManager.on_worker_result: Level {self.level+1}, completed={completed}/{total}, has_image={img_array is not None}")
    
    @pyqtSlot(tuple)
    def on_worker_error(self, error_tuple):
        """Handle errors from worker threads"""
        import logging
        logger = logging.getLogger(__name__)
        exctype, value, traceback_str = error_tuple
        logger.error(f"Thumbnail worker error: {exctype.__name__}: {value}")
        logger.debug(f"Traceback: {traceback_str}")
    
    @pyqtSlot()
    def on_worker_finished(self):
        """Handle finished signal from worker threads"""
        # This is just a placeholder to properly handle the finished signal
        pass


# Define a custom OpenGL widget using QOpenGLWidget
class MCubeWidget(QGLWidget):
    def __init__(self,parent):
        super().__init__(parent=parent)
        self.setMinimumSize(100,100)
        self.isovalue = 60  # Adjust the isovalue as needed
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.temp_pan_x = 0
        self.temp_pan_y = 0
        self.rotate_x = 0
        self.rotate_y = 0
        self.temp_rotate_x = 0
        self.temp_rotate_y = 0
        self.curr_x = 0
        self.curr_y = 0
        self.down_x = 0
        self.down_y = 0
        self.temp_dolly = 0
        self.dolly = 0
        self.data_mode = OBJECT_MODE
        self.view_mode = VIEW_MODE
        self.auto_rotate = True
        self.is_dragging = False
        #self.setMinimumSize(400,400)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.rotate_timeout)
        self.timer.start()
        self.timer2 = QTimer(self)
        self.timer2.setInterval(50)
        self.timer2.timeout.connect(self.generate_mesh_timeout)
        self.timer2.start()

        self.triangles = []
        self.gl_list_generated = False
        self.parent = parent
        self.parent.set_threed_view(self)

        ''' set up buttons '''
        self.moveButton = QLabel(self)
        self.moveButton.setPixmap(QPixmap(resource_path("move.png")).scaled(15,15))
        self.moveButton.hide()
        self.moveButton.setGeometry(0,0,15,15)
        self.moveButton.mousePressEvent = self.moveButton_mousePressEvent
        self.moveButton.mouseMoveEvent = self.moveButton_mouseMoveEvent
        self.moveButton.mouseReleaseEvent = self.moveButton_mouseReleaseEvent
        self.expandButton = QLabel(self)
        self.expandButton.setPixmap(QPixmap(resource_path("expand.png")).scaled(15,15))
        self.expandButton.hide()
        self.expandButton.setGeometry(15,0,15,15)
        self.expandButton.mousePressEvent = self.expandButton_mousePressEvent
        self.shrinkButton = QLabel(self)
        self.shrinkButton.setPixmap(QPixmap(resource_path("shrink.png")).scaled(15,15))
        self.shrinkButton.hide()
        self.shrinkButton.setGeometry(30,0,15,15)
        self.shrinkButton.mousePressEvent = self.shrinkButton_mousePressEvent
        self.cbxRotation = QCheckBox(self)
        self.cbxRotation.setText("R")
        self.cbxRotation.setChecked(True)
        self.cbxRotation.stateChanged.connect(self.cbxRotation_stateChanged)
        self.cbxRotation.setStyleSheet("QCheckBox { background-color: #323232; color: white; }")        
        self.cbxRotation.hide()
        self.cbxRotation.move(45,0)

        self.curr_slice = None
        self.curr_slice_vertices = []
        self.scale = 0.20
        self.average_coordinates = np.array([0.0,0.0,0.0], dtype=np.float64)
        self.bounding_box = None
        self.roi_box = None
        self.threadpool = QThreadPool()
        #print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        self.vertices = []
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.generate_mesh_under_way = False
        self.adjust_volume_under_way = False
        self.generated_data = None
        self.is_inverse = False

        self.queue = Queue()

    def recalculate_geometry(self):
        #self.scale = self.parent.
        size = min(self.parent.width(),self.parent.height())
        self.scale = round( ( self.width() / size ) * 10.0 ) / 10.0
        #self.resize(int(size*self.scale),int(size*self.scale))

        self.resize_self()
        self.reposition_self()

    def start_generate_mesh(self):
        self.threadpool.start(self.worker)

    def progress_fn(self, n):
        #print("progress_fn")
        return

    def execute_this_fn(self, progress_callback):
        return

        #return "Done."

    def print_output(self, s):
        return

    def thread_complete(self):
        #print("THREAD COMPLETE!")
        self.adjust_volume()
        return

    def expandButton_mousePressEvent(self, event):
        self.scale += 0.1
        self.resize_self()
        self.reposition_self()

    def shrinkButton_mousePressEvent(self, event):
        self.scale -= 0.1
        if self.scale < 0.1:
            self.scale = 0.1
        self.resize_self()
        self.reposition_self()

    def moveButton_mousePressEvent(self, event):
        self.down_x = event.x()
        self.down_y = event.y()
        self.view_mode = MOVE_3DVIEW_MODE

    def moveButton_mouseMoveEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()
        if self.view_mode == MOVE_3DVIEW_MODE:
            self.move(self.x() + self.curr_x - self.down_x, self.y() + self.curr_y - self.down_y)
        #self.reposition_self()

    def moveButton_mouseReleaseEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()
        if self.view_mode == MOVE_3DVIEW_MODE:
            self.move(self.x() + self.curr_x - self.down_x, self.y() + self.curr_y - self.down_y)

        self.view_mode = VIEW_MODE
        # get parent's geometry
        self.reposition_self()

    def reposition_self(self):
        x, y = self.x(), self.y()
        parent_geometry = self.parent.get_pixmap_geometry()
        if parent_geometry is None:
            return
        if y + ( self.height() / 2 ) > parent_geometry.height() / 2 :
            y = parent_geometry.height() - self.height()
        else:
            y = 0
        if x + ( self.width() / 2 ) > parent_geometry.width() / 2 :
            x = parent_geometry.width() - self.width()
        else:
            x = 0
        
        self.move(x, y)                

    def cbxRotation_stateChanged(self):
        self.auto_rotate = self.cbxRotation.isChecked()

    def resize_self(self):
        size = min(self.parent.width(),self.parent.height())
        self.resize(int(size*self.scale),int(size*self.scale))
        #print("resize:",self.parent.width(),self.parent.height())

    def make_box(self, box_coords):
        from_z = box_coords[0]
        to_z = box_coords[1]
        from_y = box_coords[2]
        to_y = box_coords[3]
        from_x = box_coords[4]
        to_x = box_coords[5]

        box_vertex = np.array([
            np.array([from_z, from_y, from_x]),
            np.array([to_z, from_y, from_x]),
            np.array([from_z, to_y, from_x]),
            np.array([to_z, to_y, from_x]),
            np.array([from_z, from_y, to_x]),
            np.array([to_z, from_y, to_x]),
            np.array([from_z, to_y, to_x]),
            np.array([to_z, to_y, to_x])
        ], dtype=np.float64)

        box_edges = [
            [0,1],
            [0,2],
            [0,4],
            [1,3],
            [1,5],
            [2,3],
            [2,6],
            [3,7],
            [4,5],
            [4,6],
            [5,7],
            [6,7]
        ]
        return box_vertex, box_edges

    def update_boxes(self, bounding_box, roi_box,curr_slice_val):
        self.set_bounding_box(bounding_box)
        self.set_roi_box(roi_box)
        self.set_curr_slice(curr_slice_val)

    def adjust_boxes(self):
        # apply roi_displacement to bounding box, roi box, and curr_slice
        self.apply_roi_displacement()
        self.rotate_boxes()
        self.scale_boxes()
        
    def scale_boxes(self):
        factor = 10.0
        self.roi_box_vertices *= self.scale_factor / factor
        self.bounding_box_vertices *= self.scale_factor / factor
        self.curr_slice_vertices *= self.scale_factor / factor
        self.volume_displacement *= self.scale_factor / factor

    def set_bounding_box(self, bounding_box):
        self.original_bounding_box = deepcopy(np.array(bounding_box, dtype=np.float64))
        self.bounding_box = deepcopy(np.array(bounding_box, dtype=np.float64))
        self.bounding_box_vertices, self.bounding_box_edges = self.make_box(self.bounding_box)
        self.original_bounding_box_vertices, self.original_bounding_box_edges = self.make_box(self.original_bounding_box)
    
    def set_curr_slice(self, curr_slice):
        self.curr_slice = curr_slice
        self.original_curr_slice_vertices = np.array([
            [self.curr_slice, self.original_bounding_box_vertices[0][1], self.original_bounding_box_vertices[0][2]],
            [self.curr_slice, self.original_bounding_box_vertices[2][1], self.original_bounding_box_vertices[2][2]],
            [self.curr_slice, self.original_bounding_box_vertices[6][1], self.original_bounding_box_vertices[6][2]],
            [self.curr_slice, self.original_bounding_box_vertices[4][1], self.original_bounding_box_vertices[4][2]]
        ], dtype=np.float64)
        self.curr_slice_vertices = deepcopy(self.original_curr_slice_vertices)

    def set_roi_box(self, roi_box):
        roi_box_width = roi_box[1] - roi_box[0]
        roi_box_height = roi_box[3] - roi_box[2]
        roi_box_depth = roi_box[5] - roi_box[4]
        max_roi_box_dim = max(roi_box_width, roi_box_height, roi_box_depth)
        self.scale_factor = ROI_BOX_RESOLUTION/max_roi_box_dim
        self.original_roi_box = deepcopy(np.array(roi_box, dtype=np.float64))

        self.roi_box = deepcopy(np.array(roi_box, dtype=np.float64))
        self.original_roi_box_vertices, self.original_roi_box_edges = self.make_box(self.original_roi_box)
        self.roi_box_vertices, self.roi_box_edges = self.make_box(self.roi_box)

        self.roi_displacement = deepcopy((self.roi_box_vertices[0]+self.roi_box_vertices[7])/2.0)
        self.volume_displacement = deepcopy((self.roi_box_vertices[7]-self.roi_box_vertices[0])/2.0)

    def apply_roi_displacement(self):
        self.bounding_box_vertices = self.original_bounding_box_vertices - self.roi_displacement
        self.curr_slice_vertices = self.original_curr_slice_vertices - self.roi_displacement
        self.roi_box_vertices = self.original_roi_box_vertices - self.roi_displacement

    def rotate_boxes(self):
        # rotate bounding box and roi box
        for i in range(len(self.bounding_box_vertices)):
            self.bounding_box_vertices[i] = np.array([self.bounding_box_vertices[i][2],self.bounding_box_vertices[i][0],self.bounding_box_vertices[i][1]])
            if self.roi_box is not None:
                self.roi_box_vertices[i] = np.array([self.roi_box_vertices[i][2],self.roi_box_vertices[i][0],self.roi_box_vertices[i][1]])
                pass
        for i in range(len(self.curr_slice_vertices)):
            self.curr_slice_vertices[i] = np.array([self.curr_slice_vertices[i][2],self.curr_slice_vertices[i][0],self.curr_slice_vertices[i][1]])

        return

    def generate_mesh_multithread(self):
        # put current parameters to the queue
        self.queue.put((self.volume, self.isovalue))

    def update_volume(self, volume):
        self.set_volume(volume)
        
    def adjust_volume(self):
        if self.generate_mesh_under_way == True:
            return
        
        if self.generated_data is None:
            return
        
        if self.adjust_volume_under_way == True:
            return
        
        self.adjust_volume_under_way = True
        self.vertices = deepcopy(self.generated_data['vertices'])
        self.triangles = deepcopy(self.generated_data['triangles'])
        self.vertex_normals = deepcopy(self.generated_data['vertex_normals'])

        self.scale_volume()
        self.apply_volume_displacement()
        self.rotate_volume()

        self.adjust_volume_under_way = False

    def set_volume(self, volume):
        self.volume = volume

    def show_buttons(self):
        self.cbxRotation.show()
        self.moveButton.show()
        self.expandButton.show()
        self.shrinkButton.show()

    def generate_mesh(self):
        self.generate_mesh_under_way = True

        max_len = max(self.volume.shape)
        self.scale_factor = 50.0/max_len

        volume = ndimage.zoom(self.volume, self.scale_factor, order=1)
        if self.is_inverse:
            volume = 255 - volume
            isovalue = 255 - self.isovalue
        else:
            isovalue = self.isovalue
        vertices, triangles = mcubes.marching_cubes(volume, isovalue)

        face_normals = []
        for triangle in triangles:
            v0 = vertices[triangle[0]]
            v1 = vertices[triangle[1]]
            v2 = vertices[triangle[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm == 0:
                normal = np.array([0, 0, 0])
            else:
                normal /= np.linalg.norm(normal)
            face_normals.append(normal)

        vertex_normals = np.zeros(vertices.shape)

        # Calculate vertex normals by averaging face normals
        for i, triangle in enumerate(triangles):
            for vertex_index in triangle:
                vertex_normals[vertex_index] += face_normals[i]

        # Normalize vertex normals
        for i in range(len(vertex_normals)):
            if np.linalg.norm(vertex_normals[i]) != 0:
                vertex_normals[i] /= np.linalg.norm(vertex_normals[i])
            else:
                vertex_normals[i] = np.array([0.0, 0.0, 0.0])
        
        self.generated_data = {}
        self.generated_data['vertices'] = vertices
        self.generated_data['triangles'] = triangles
        self.generated_data['vertex_normals'] = vertex_normals

        self.gl_list_generated = False
        self.generate_mesh_under_way = False

    def apply_volume_displacement(self):
        if len(self.vertices) > 0:        
            self.vertices = deepcopy( self.vertices - self.volume_displacement )

    def rotate_volume(self):
        # rotate vertices
        if len(self.vertices) > 0:        
            #print(self.vertices.shape)
            for i in range(len(self.vertices)):
                #print("vertices[i]", i, self.vertices[i])
                self.vertices[i] = np.array([self.vertices[i][2],self.vertices[i][0],self.vertices[i][1]])
                self.vertex_normals[i] = np.array([self.vertex_normals[i][2],self.vertex_normals[i][0],self.vertex_normals[i][1]])

        #print(self.bounding_box_vertices[0])
    def scale_volume(self):
        if len(self.vertices) > 0:        
            self.vertices /= 10.0
        return

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue

    def read_images_from_folder(self,folder):
        images = []
        try:
            for filename in os.listdir(folder):
                try:
                    # read images using Pillow
                    img = Image.open(os.path.join(folder,filename))
                    #img = cv2.imread(os.path.join(folder,filename),0)
                    if img is not None:
                        images.append(np.array(img))
                except Exception as e:
                    logger.error(f"Error reading image {filename}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error accessing folder {folder}: {e}")
            return np.array([])
        return np.array(images)

    def generate_mesh_timeout(self):
        #print("timout2")
        if not self.queue.empty() and self.generate_mesh_under_way == False:
            while not self.queue.empty():
                (volume, isovalue) = self.queue.get()
            self.volume = volume
            self.isovalue = isovalue
            self.worker = Worker(self.generate_mesh) # Any other args, kwargs are passed to the run function
            self.worker.signals.result.connect(self.print_output)
            self.worker.signals.finished.connect(self.thread_complete)
            self.worker.signals.progress.connect(self.progress_fn)
            self.threadpool.start(self.worker)
        self.updateGL()

    def rotate_timeout(self):
        #print("timout1")
        #print("timeout, auto_rotate:", self.auto_rotate)
        if self.auto_rotate == False:
            #print "no rotate"
            return
        if self.is_dragging:
            #print "dragging"
            return

        self.rotate_x += 1
        self.updateGL()

    def mousePressEvent(self, event):
        self.down_x = event.x()
        self.down_y = event.y()
        if event.buttons() == Qt.LeftButton:
            self.view_mode = ROTATE_MODE
        elif event.buttons() == Qt.RightButton:
            self.view_mode = ZOOM_MODE
        elif event.buttons() == Qt.MiddleButton:
            self.view_mode = PAN_MODE

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.curr_x = event.x()
        self.curr_y = event.y()

        if event.button() == Qt.LeftButton:
                self.rotate_x += self.temp_rotate_x
                self.rotate_y += self.temp_rotate_y
                self.rotate_y = 0
                self.temp_rotate_x = 0
                self.temp_rotate_y = 0
        elif event.button() == Qt.RightButton:
            self.dolly += self.temp_dolly 
            self.temp_dolly = 0
        elif event.button() == Qt.MiddleButton:
            self.pan_x += self.temp_pan_x
            self.pan_y += self.temp_pan_y
            self.temp_pan_x = 0
            self.temp_pan_y = 0
        self.view_mode = VIEW_MODE
        self.updateGL()

    def mouseMoveEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()

        if event.buttons() == Qt.LeftButton and self.view_mode == ROTATE_MODE:
            self.is_dragging = True
            self.temp_rotate_x = self.curr_x - self.down_x
            self.temp_rotate_y = self.curr_y - self.down_y
        elif event.buttons() == Qt.RightButton and self.view_mode == ZOOM_MODE:
            self.is_dragging = True
            self.temp_dolly = ( self.curr_y - self.down_y ) / 100.0
        elif event.buttons() == Qt.MiddleButton and self.view_mode == PAN_MODE:
            self.is_dragging = True
            self.temp_pan_x = self.curr_x - self.down_x
            self.temp_pan_y = self.curr_y - self.down_y
        self.updateGL()

    def wheelEvent(self, event):
        self.dolly -= event.angleDelta().y() / 240.0
        self.updateGL()


    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def draw_box(self, box_vertices, box_edges, color=[1.0, 0.0, 0.0]):
        glColor3f(color[0], color[1], color[2])
        v = box_vertices
        glBegin(GL_LINES)
        for e in box_edges:
            for idx in e:
                glVertex3fv(v[idx])
        glEnd()


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()


        glMatrixMode(GL_MODELVIEW)
        glClearColor(0.94,0.94,0.94, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LIGHTING)

        # Set camera position and view
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glTranslatef(0, 0, -5.0 + self.dolly + self.temp_dolly)   # x, y, z 
        glTranslatef((self.pan_x + self.temp_pan_x)/100.0, (self.pan_y + self.temp_pan_y)/-100.0, 0.0)

        # rotate viewpoint
        glRotatef(self.rotate_y + self.temp_rotate_y, 1.0, 0.0, 0.0)
        glRotatef(self.rotate_x + self.temp_rotate_x, 0.0, 1.0, 0.0)

        if len(self.triangles) == 0:
            return

        glClearColor(0.2,0.2,0.2, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        ''' render bounding box '''
        glDisable(GL_LIGHTING)
        if self.bounding_box is not None:
            glLineWidth(1)
            self.draw_box(self.bounding_box_vertices, self.bounding_box_edges, color=[0.0, 0.0, 1.0])

        ''' render roi box '''
        if self.roi_box is not None:
            if not (self.roi_box_vertices == self.bounding_box_vertices).all():
                glLineWidth(2)
                self.draw_box(self.roi_box_vertices, self.roi_box_edges, color=[1.0, 0.0, 0.0])
        glEnable(GL_LIGHTING)

        ''' render 3d model '''
        glColor3f(0.0, 1.0, 0.0)
        if self.gl_list_generated == False:
            self.generate_gl_list()

        self.render_gl_list()

        ''' draw current slice plane '''
        glColor4f(0.0, 1.0, 0.0, 0.5) 
        glBegin(GL_QUADS)
        for vertex in self.curr_slice_vertices:
            glVertex3fv(vertex)
        glEnd()

        return

    def render_gl_list(self):
        if self.gl_list_generated == False:
            return
        glCallList(self.gl_list)
        return

    def generate_gl_list(self):
        self.gl_list = glGenLists(1)
        glNewList(self.gl_list, GL_COMPILE)

        # Render the 3D surface
        glBegin(GL_TRIANGLES)
        
        for triangle in self.triangles:
            for vertex in triangle:
                glNormal3fv(self.vertex_normals[vertex])
                glVertex3fv(self.vertices[vertex])
        glEnd()
        glEndList()
        self.gl_list_generated = True


class InfoDialog(QDialog):
    '''
    InfoDialog shows application information.
    '''
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add title
        title_label = QLabel("<h2>CTHarvester</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add version info
        version_label = QLabel(self.tr("Version {}").format(PROGRAM_VERSION))
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Add description
        desc_label = QLabel(self.tr("CT Image Stack Processing Tool"))
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add copyright
        copyright_label = QLabel(self.tr(PROGRAM_COPYRIGHT))
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # Add GitHub link
        github_label = QLabel('<a href="https://github.com/jikhanjung/CTHarvester">GitHub Repository</a>')
        github_label.setOpenExternalLinks(True)
        github_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(github_label)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Add OK button
        button_layout = QHBoxLayout()
        btn_ok = QPushButton(self.tr("OK"))
        btn_ok.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle(self.tr("About CTHarvester"))
        self.setFixedSize(300, 200)
        self.move(self.parent.pos() + QPoint(150, 150))


class PreferencesDialog(QDialog):
    '''
    PreferencesDialog shows preferences.

    Args:
        None

    Attributes:
        well..
    '''
    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        self.m_app = QApplication.instance()

        self.rbRememberGeometryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
        self.rbRememberGeometryYes.clicked.connect(self.on_rbRememberGeometryYes_clicked)
        self.rbRememberGeometryNo = QRadioButton(self.tr("No"))
        self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
        self.rbRememberGeometryNo.clicked.connect(self.on_rbRememberGeometryNo_clicked)

        self.rbRememberDirectoryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
        self.rbRememberDirectoryYes.clicked.connect(self.on_rbRememberDirectoryYes_clicked)
        self.rbRememberDirectoryNo = QRadioButton(self.tr("No"))
        self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)
        self.rbRememberDirectoryNo.clicked.connect(self.on_rbRememberDirectoryNo_clicked)

        self.gbRememberGeometry = QGroupBox()
        self.gbRememberGeometry.setLayout(QHBoxLayout())
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryYes)
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryNo)

        self.gbRememberDirectory = QGroupBox()
        self.gbRememberDirectory.setLayout(QHBoxLayout())
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryYes)
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryNo)

        self.comboLang = QComboBox()
        self.comboLang.addItem(self.tr("English"))
        self.comboLang.addItem(self.tr("Korean"))
        self.comboLang.currentIndexChanged.connect(self.comboLangIndexChanged)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.setLayout(self.main_layout)
        self.form_layout.addRow(self.tr("Remember Geometry"), self.gbRememberGeometry)
        self.form_layout.addRow(self.tr("Remember Directory"), self.gbRememberDirectory)
        self.form_layout.addRow(self.tr("Language"), self.comboLang)
        self.button_layout = QHBoxLayout()
        self.btnOK = QPushButton(self.tr("OK"))
        self.btnOK.clicked.connect(self.on_btnOK_clicked)
        self.btnCancel = QPushButton(self.tr("Cancel"))
        self.btnCancel.clicked.connect(self.on_btnCancel_clicked)
        self.button_layout.addWidget(self.btnOK)
        self.button_layout.addWidget(self.btnCancel)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos()+QPoint(100,100))

        self.read_settings()

    def on_btnOK_clicked(self):
        self.save_settings()
        self.close()

    def on_btnCancel_clicked(self):
        self.close()

    def on_rbRememberGeometryYes_clicked(self):
        self.m_app.remember_geometry = True

    def on_rbRememberGeometryNo_clicked(self):
        self.m_app.remember_geometry = False

    def on_rbRememberDirectoryYes_clicked(self):
        self.m_app.remember_directory = True

    def on_rbRememberDirectoryNo_clicked(self):
        self.m_app.remember_directory = False

    def comboLangIndexChanged(self, index):
        if index == 0:
            self.m_app.language = "en"
        elif index == 1:
            self.m_app.language = "ko"
        #print("self.language:", self.m_app.language)

    def update_language(self):
        #print("update_language", self.m_app.language)
        translator = QTranslator()
        translator.load(resource_path('CTHarvester_{}.qm').format(self.m_app.language))
        self.m_app.installTranslator(translator)
        
        self.rbRememberGeometryYes.setText(self.tr("Yes"))
        self.rbRememberGeometryNo.setText(self.tr("No"))
        self.rbRememberDirectoryYes.setText(self.tr("Yes"))
        self.rbRememberDirectoryNo.setText(self.tr("No"))
        self.gbRememberGeometry.setTitle("")
        self.gbRememberDirectory.setTitle("")
        self.comboLang.setItemText(0, self.tr("English"))
        self.comboLang.setItemText(1, self.tr("Korean"))
        self.btnOK.setText(self.tr("OK"))
        self.btnCancel.setText(self.tr("Cancel"))
        self.form_layout.labelForField(self.gbRememberGeometry).setText(self.tr("Remember Geometry"))
        self.form_layout.labelForField(self.gbRememberDirectory).setText(self.tr("Remember Directory"))
        self.form_layout.labelForField(self.comboLang).setText(self.tr("Language"))
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.parent.update_language()
        self.parent.update_status()

    def read_settings(self):
        try:
            self.m_app.remember_geometry = value_to_bool(self.m_app.settings.value("Remember geometry", True))
            self.m_app.remember_directory = value_to_bool(self.m_app.settings.value("Remember directory", True))
            self.m_app.language = self.m_app.settings.value("Language", "en")

            self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
            self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
            self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
            self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)

            if self.m_app.language == "en":
                self.comboLang.setCurrentIndex(0)
            elif self.m_app.language == "ko":
                self.comboLang.setCurrentIndex(1)
            self.update_language()
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            # Use default values if settings can't be read
            self.m_app.remember_geometry = True
            self.m_app.remember_directory = True
            self.m_app.language = "en"

    def save_settings(self):
        try:
            self.m_app.settings.setValue("Remember geometry", self.m_app.remember_geometry)
            self.m_app.settings.setValue("Remember directory", self.m_app.remember_directory)
            self.m_app.settings.setValue("Language", self.m_app.language)
            self.update_language()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

class ProgressDialog(QDialog):
    def __init__(self,parent):
        super().__init__()
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.parent = parent
        self.m_app = QApplication.instance()
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos()+QPoint(100,100))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(50,50, 50, 50)

        self.lbl_text = QLabel(self)
        self.lbl_detail = QLabel(self)  # Additional label for ETA
        self.pb_progress = QProgressBar(self)
        self.pb_progress.setValue(0)
        self.stop_progress = False
        self.is_cancelled = False
        
        # Cancel button (visible by default)
        self.btnCancel = QPushButton(self)
        self.btnCancel.setText(self.tr("Cancel"))
        self.btnCancel.clicked.connect(self.set_cancelled)
        
        # Legacy stop button (hidden)
        self.btnStop = QPushButton(self)
        self.btnStop.setText(self.tr("Stop"))
        self.btnStop.clicked.connect(self.set_stop_progress)
        self.btnStop.hide()
        
        self.layout.addWidget(self.lbl_text)
        self.layout.addWidget(self.lbl_detail)
        self.layout.addWidget(self.pb_progress)
        self.layout.addWidget(self.btnCancel)
        self.setLayout(self.layout)
        
        # For time estimation
        self.start_time = None
        self.total_steps = 0
        self.current_step = 0
        
        # Advanced ETA calculation with improved stability
        from collections import deque
        self.step_times = deque(maxlen=100)  # Keep last 100 step times for better averaging
        self.last_update_time = None
        self.smoothed_eta = None  # Exponentially smoothed ETA
        self.ema_alpha = 0.1  # Reduced EMA smoothing factor for more stability (0.1 = 10% new, 90% old)
        self.min_samples_for_eta = 10  # Increased minimum samples before showing ETA
        self.step_history = []  # Store (timestamp, step_number) tuples
        self.last_eta_update = 0  # Track last ETA update time
        self.eta_update_interval = 1.0  # Update ETA at most once per second
        self.velocity_history = deque(maxlen=30)  # Track processing velocity

    def set_cancelled(self):
        self.is_cancelled = True
        self.stop_progress = True
        
    def set_stop_progress(self):
        self.stop_progress = True

    def set_progress_text(self,text_format):
        self.text_format = text_format

    def set_max_value(self,max_value):
        self.max_value = max_value

    def set_curr_value(self,curr_value):
        self.curr_value = curr_value
        self.pb_progress.setValue(int((self.curr_value/float(self.max_value))*100))
        self.lbl_text.setText(self.text_format.format(self.curr_value, self.max_value))
        self.update()
        QApplication.processEvents()

    def setup_unified_progress(self, total_steps, initial_estimate_seconds=None):
        """Setup for unified progress tracking with optional initial estimate"""
        import time
        import logging
        from collections import deque
        logger = logging.getLogger(__name__)

        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.pb_progress.setMaximum(100)
        self.pb_progress.setValue(0)

        # Reset ETA calculation state
        from collections import deque
        self.step_times = deque(maxlen=100)
        self.smoothed_eta = initial_estimate_seconds  # Use provided initial estimate
        self.step_history = []
        self.velocity_history = deque(maxlen=30)
        self.last_eta_update = 0

        # Display initial estimate if provided, otherwise show "Estimating..."
        if initial_estimate_seconds:
            if initial_estimate_seconds < 60:
                eta_text = f"{int(initial_estimate_seconds)}s"
            elif initial_estimate_seconds < 3600:
                eta_text = f"{int(initial_estimate_seconds/60)}m {int(initial_estimate_seconds%60)}s"
            else:
                eta_text = f"{int(initial_estimate_seconds/3600)}h {int((initial_estimate_seconds%3600)/60)}m"
            self.lbl_detail.setText(f"ETA: {eta_text}")
            logger.info(f"ProgressDialog initial ETA: {eta_text} ({initial_estimate_seconds:.1f}s)")
        else:
            self.lbl_detail.setText("Estimating...")
            logger.info("ProgressDialog showing 'Estimating...' until sampling completes")

        logger.info(f"ProgressDialog.setup_unified_progress: total_steps={total_steps}")
        
    def update_unified_progress(self, step, detail_text=""):
        """Update unified progress with sophisticated ETA calculation"""
        import time
        import logging
        import numpy as np
        logger = logging.getLogger(__name__)

        current_time = time.time()
        self.current_step = step

        if self.total_steps > 0:
            percentage = int((self.current_step / self.total_steps) * 100)
            self.pb_progress.setValue(percentage)

            # Record step timing (skip first few for warm-up)
            if self.last_update_time and step > 3:  # Skip first 3 steps for warm-up
                step_duration = current_time - self.last_update_time
                # Filter out outliers (>5x median)
                if len(self.step_times) == 0 or step_duration < np.median(list(self.step_times)) * 5:
                    self.step_times.append(step_duration)
                    self.step_history.append((current_time, step))

            # Don't calculate ETA here - it will be set externally by ThumbnailManager
            # after sampling or periodic updates
            # Just keep the existing text if no new one is provided
            current_text = self.lbl_detail.text()
            if not current_text.startswith("ETA:") and not current_text == "Estimating...":
                # Only calculate if we don't have an externally set ETA
                eta_text = self._calculate_eta(current_time)
                if eta_text:
                    self.lbl_detail.setText(f"ETA: {eta_text} - {detail_text}")
                else:
                    self.lbl_detail.setText(detail_text)
            elif detail_text:
                # Keep existing ETA, just update detail text
                if "ETA:" in current_text:
                    eta_part = current_text.split(" - ")[0] if " - " in current_text else current_text
                    self.lbl_detail.setText(f"{eta_part} - {detail_text}")
                else:
                    self.lbl_detail.setText(f"{current_text} - {detail_text}")
            
            # Log current state
            current_eta = self.lbl_detail.text().split(" - ")[0] if " - " in self.lbl_detail.text() else self.lbl_detail.text()
            logger.debug(f"ProgressDialog.update: step={step}/{self.total_steps}, {percentage}%, {current_eta}, {detail_text}")
            
        self.last_update_time = current_time
        self.update()
        
        # Process events periodically to maintain UI responsiveness
        if step % 10 == 0:  # Every 10 steps
            QApplication.processEvents()
    
    def _calculate_eta(self, current_time):
        """Calculate ETA using multiple methods with improved stability"""
        import numpy as np

        remaining_steps = self.total_steps - self.current_step
        if remaining_steps <= 0:
            return None

        # Don't update ETA too frequently to avoid jitter
        if current_time - self.last_eta_update < self.eta_update_interval:
            # Return last calculated ETA formatted
            if self.smoothed_eta:
                eta_seconds = max(0, self.smoothed_eta)
                if eta_seconds < 60:
                    return f"{int(eta_seconds)}s"
                elif eta_seconds < 3600:
                    return f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
                else:
                    return f"{int(eta_seconds/3600)}h {int((eta_seconds%3600)/60)}m"
            return None

        self.last_eta_update = current_time

        # Calculate current velocity
        if len(self.step_history) >= 2:
            recent_time = self.step_history[-1][0] - self.step_history[-2][0]
            recent_steps = self.step_history[-1][1] - self.step_history[-2][1]
            if recent_time > 0 and recent_steps > 0:
                current_velocity = recent_steps / recent_time
                self.velocity_history.append(current_velocity)

        # Method 1: Stable moving average of step times
        if len(self.step_times) >= self.min_samples_for_eta:
            # Use trimmed mean to remove outliers
            sorted_times = sorted(list(self.step_times))
            trim_count = max(1, len(sorted_times) // 10)  # Trim 10% from each end
            trimmed_times = sorted_times[trim_count:-trim_count] if len(sorted_times) > 2 * trim_count else sorted_times
            avg_step_time = np.mean(trimmed_times) if trimmed_times else np.mean(sorted_times)
            eta_moving_avg = avg_step_time * remaining_steps
        else:
            eta_moving_avg = None

        # Method 2: Overall average from start (most stable)
        if self.current_step > 0:
            elapsed = current_time - self.start_time
            eta_overall = (elapsed / self.current_step) * remaining_steps
        else:
            eta_overall = None

        # Method 3: Smoothed velocity (last 30 velocity samples)
        if len(self.velocity_history) >= 5:
            # Use median velocity for stability
            median_velocity = np.median(list(self.velocity_history))
            if median_velocity > 0:
                eta_velocity = remaining_steps / median_velocity
            else:
                eta_velocity = None
        else:
            eta_velocity = None

        # Combine estimates with weighted average
        estimates = []
        weights = []

        if eta_overall is not None:
            estimates.append(eta_overall)
            weights.append(0.5)  # Most stable, highest weight

        if eta_moving_avg is not None:
            estimates.append(eta_moving_avg)
            weights.append(0.3)  # Second most stable

        if eta_velocity is not None:
            estimates.append(eta_velocity)
            weights.append(0.2)  # Most responsive but less stable

        if not estimates:
            return None

        # Weighted average instead of median for smoother transitions
        current_estimate = np.average(estimates, weights=weights[:len(estimates)])

        # Apply stronger exponential smoothing
        if self.smoothed_eta is None:
            self.smoothed_eta = current_estimate
        else:
            # Limit the change rate to prevent jumps
            max_change_rate = 0.2  # Maximum 20% change per update
            change = current_estimate - self.smoothed_eta
            max_change = self.smoothed_eta * max_change_rate

            if abs(change) > max_change:
                change = max_change if change > 0 else -max_change

            # Apply limited change with EMA
            self.smoothed_eta = self.smoothed_eta + self.ema_alpha * change

        # Format time
        eta_seconds = max(0, self.smoothed_eta)

        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        elif eta_seconds < 3600:
            return f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
        else:
            hours = int(eta_seconds/3600)
            minutes = int((eta_seconds%3600)/60)
            return f"{hours}h {minutes}m"
            
    def update_language(self):
        translator = QTranslator()
        translator.load(resource_path('CTHarvester_{}.qm').format(self.m_app.language))
        self.m_app.installTranslator(translator)
        
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.btnStop.setText(self.tr("Stop"))


class ObjectViewer2D(QLabel):
    def __init__(self, widget):
        super(ObjectViewer2D, self).__init__(widget)
        self.setMinimumSize(512,512)
        self.image_canvas_ratio = 1.0
        self.scale = 1.0
        self.mouse_down_x = 0
        self.mouse_down_y = 0
        self.mouse_curr_x = 0
        self.mouse_curr_y = 0
        self.edit_mode = MODE['ADD_BOX']
        self.orig_pixmap = None
        self.curr_pixmap = None
        self.distance_threshold = self._2imgx(5)
        self.setMouseTracking(True)
        self.object_dialog = None
        self.top_idx = -1
        self.bottom_idx = -1
        self.curr_idx = 0
        self.move_x = 0
        self.move_y = 0
        self.threed_view = None
        self.isovalue = 60
        self.is_inverse = False
        self.reset_crop()

    def get_pixmap_geometry(self):
        if self.curr_pixmap:
            return self.curr_pixmap.rect()

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue
        self.update()

    def set_threed_view(self, threed_view):
        self.threed_view = threed_view

    def reset_crop(self):
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False
        self.canvas_box = None
        # If an image is loaded, default ROI to full image
        if self.orig_pixmap is not None:
            self.set_full_roi()

    def set_full_roi(self):
        if self.orig_pixmap is None:
            return
        self.crop_from_x = 0
        self.crop_from_y = 0
        self.crop_to_x = self.orig_pixmap.width()
        self.crop_to_y = self.orig_pixmap.height()
        # canvas_box will be set on next calculate_resize; ensure it's available now as well
        if self.image_canvas_ratio != 0:
            self.canvas_box = QRect(
                self._2canx(self.crop_from_x),
                self._2cany(self.crop_from_y),
                self._2canx(self.crop_to_x - self.crop_from_x),
                self._2cany(self.crop_to_y - self.crop_from_y),
            )

    def _2canx(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)
    def _2cany(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)
    def _2imgx(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)
    def _2imgy(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)

    def set_mode(self, mode):
        self.edit_mode = mode
        if self.edit_mode == MODE['ADD_BOX']:
            self.setCursor(Qt.CrossCursor)
        elif self.edit_mode in [ MODE['MOVE_BOX'], MODE['MOVE_BOX_READY'], MODE['MOVE_BOX_PROGRESS'] ]:
            self.setCursor(Qt.OpenHandCursor)
        elif self.edit_mode in [ MODE['EDIT_BOX'], MODE['EDIT_BOX_READY'], MODE['EDIT_BOX_PROGRESS'] ]:
            pass
        else:
            self.setCursor(Qt.ArrowCursor)

    def distance_check(self, x, y):
        x = self._2imgx(x)
        y = self._2imgy(y)
        if self.crop_from_x - self.distance_threshold >= x or self.crop_to_x + self.distance_threshold <= x or self.crop_from_y - self.distance_threshold >= y or self.crop_to_y + self.distance_threshold <= y:
            self.edit_x1 = False
            self.edit_x2 = False
            self.edit_y1 = False
            self.edit_y2 = False
            self.inside_box = False
        else:
            if self.crop_from_x + self.distance_threshold <= x and self.crop_to_x - self.distance_threshold >= x \
                and self.crop_from_y + self.distance_threshold <= y and self.crop_to_y - self.distance_threshold >= y:
                self.edit_x1 = False
                self.edit_x2 = False
                self.edit_y1 = False
                self.edit_y2 = False
                self.inside_box = True
                #print("move box ready")
            else:
                self.inside_box = False
            if abs(self.crop_from_x - x) <= self.distance_threshold:
                self.edit_x1 = True
            else:
                self.edit_x1 = False
            if abs(self.crop_to_x - x) <= self.distance_threshold:
                self.edit_x2 = True
            else:
                self.edit_x2 = False
            if abs(self.crop_from_y - y) <= self.distance_threshold:
                self.edit_y1 = True
            else:
                self.edit_y1 = False
            if abs(self.crop_to_y - y) <= self.distance_threshold:
                self.edit_y2 = True
            else:
                self.edit_y2 = False
        self.set_cursor_mode()

    def set_cursor_mode(self):
        if self.edit_x1 and self.edit_y1:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x2 and self.edit_y2:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x1 and self.edit_y2:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x2 and self.edit_y1:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x1 or self.edit_x2:
            self.setCursor(Qt.SizeHorCursor)
        elif self.edit_y1 or self.edit_y2:
            self.setCursor(Qt.SizeVerCursor)
        elif self.inside_box:
            self.setCursor(Qt.OpenHandCursor)
        else: 
            self.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.buttons() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.temp_x2 = self._2imgx(self.mouse_curr_x)
                self.temp_y2 = self._2imgy(self.mouse_curr_y)
            elif self.edit_mode in [ MODE['EDIT_BOX_PROGRESS'], MODE['MOVE_BOX_PROGRESS'] ]:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = self.mouse_curr_x - self.mouse_down_x
                self.move_y = self.mouse_curr_y - self.mouse_down_y
            self.calculate_resize()
        else:
            if self.edit_mode == MODE['EDIT_BOX']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE['EDIT_BOX_READY'])
                elif self.inside_box:
                    self.set_mode(MODE['MOVE_BOX_READY'])
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    pass #self.set_mode(MODE['EDIT_BOX_PROGRESS'])
                elif self.inside_box:
                    self.set_mode(MODE['MOVE_BOX_READY'])
                else:
                    self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['MOVE_BOX_READY']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE['EDIT_BOX_READY'])
                elif self.inside_box == False:
                    self.set_mode(MODE['EDIT_BOX'])
        self.object_dialog.update_status()
        self.repaint()

    def mousePressEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX'] or self.edit_mode == MODE['EDIT_BOX']:
                self.set_mode(MODE['ADD_BOX'])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                if img_x < 0 or img_x > self.orig_pixmap.width() or img_y < 0 or img_y > self.orig_pixmap.height():
                    return
                self.temp_x1 = img_x
                self.temp_y1 = img_y
                self.temp_x2 = img_x
                self.temp_y2 = img_y
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE['EDIT_BOX_PROGRESS'])
            elif self.edit_mode == MODE['MOVE_BOX_READY']:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE['MOVE_BOX_PROGRESS'])
        self.object_dialog.update_status()
        self.repaint()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(ev)
        if self.mouse_down_x == me.x() and self.mouse_down_y == me.y():
            return
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                img_x = self._2imgx(self.mouse_curr_x)
                img_y = self._2imgy(self.mouse_curr_y)
                if img_x < 0 or img_x > self.orig_pixmap.width() or img_y < 0 or img_y > self.orig_pixmap.height():
                    return
                self.crop_from_x = min(self.temp_x1, self.temp_x2)
                self.crop_to_x = max(self.temp_x1, self.temp_x2)
                self.crop_from_y = min(self.temp_y1, self.temp_y2)
                self.crop_to_y = max(self.temp_y1, self.temp_y2)
                self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['EDIT_BOX_PROGRESS']:
                if self.edit_x1:
                    self.crop_from_x = min(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_x2:
                    self.crop_to_x = max(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_y1:
                    self.crop_from_y = min(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                if self.edit_y2:
                    self.crop_to_y = max(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                self.crop_from_x = self.temp_x1 + self._2imgx(self.move_x)
                self.crop_to_x = self.temp_x2 + self._2imgx(self.move_x)
                self.crop_from_y = self.temp_y1 + self._2imgy(self.move_y)
                self.crop_to_y = self.temp_y2 + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE['MOVE_BOX_READY'])

            from_x = min(self.crop_from_x, self.crop_to_x)
            to_x = max(self.crop_from_x, self.crop_to_x)
            from_y = min(self.crop_from_y, self.crop_to_y)
            to_y = max(self.crop_from_y, self.crop_to_y)
            self.crop_from_x = from_x
            self.crop_from_y = from_y
            self.crop_to_x = to_x
            self.crop_to_y = to_y
            self.canvas_box = QRect(self._2canx(from_x), self._2cany(from_y), self._2canx(to_x - from_x), self._2cany(to_y - from_y))
            self.calculate_resize()

        self.object_dialog.update_status()
        self.object_dialog.update_3D_view(True)
        self.repaint()

    def get_crop_area(self, imgxy = False):
        from_x = -1
        to_x = -1
        from_y = -1
        to_y = -1
        if self.edit_mode == MODE['ADD_BOX']:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2))
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            #return [from_x, from_y, to_x, to_y]
        elif self.edit_mode in [ MODE['EDIT_BOX_PROGRESS'], MODE['MOVE_BOX_PROGRESS'] ]:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2)) 
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            if self.edit_x1 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                from_x += self.move_x
            if self.edit_x2 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                to_x += self.move_x
            if self.edit_y1 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                from_y += self.move_y
            if self.edit_y2 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                to_y += self.move_y
        elif self.crop_from_x > -1:
            from_x = self._2canx(min(self.crop_from_x, self.crop_to_x))
            to_x = self._2canx(max(self.crop_from_x, self.crop_to_x))
            from_y = self._2cany(min(self.crop_from_y, self.crop_to_y))
            to_y = self._2cany(max(self.crop_from_y, self.crop_to_y))

        if imgxy == True:
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.orig_pixmap:
                return [ 0,0,self.orig_pixmap.width(),self.orig_pixmap.height()]
            else:
                return [self._2imgx(from_x), self._2imgy(from_y), self._2imgx(to_x), self._2imgy(to_y)]
        else:
            # default to full canvas if ROI not yet defined
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.curr_pixmap:
                return [0, 0, self.curr_pixmap.width(), self.curr_pixmap.height()]
            return [from_x, from_y, to_x, to_y]


    def paintEvent(self, event):
        painter = QPainter(self)
        if self.curr_pixmap is not None:
            painter.drawPixmap(0,0,self.curr_pixmap)

        # overlay: filename, current index, bounds on separate lines
        try:
            file_name = os.path.basename(getattr(self, 'fullpath', '') or '')
        except Exception:
            file_name = ''
        curr_txt = str(self.curr_idx) if isinstance(self.curr_idx, int) else '-'
        low_txt = str(self.bottom_idx) if isinstance(self.bottom_idx, int) and self.bottom_idx >= 0 else '-'
        up_txt  = str(self.top_idx) if isinstance(self.top_idx, int) and self.top_idx >= 0 else '-'
        lines = [
            f"filename: {file_name}",
            f"index: {curr_txt}",
            f"bounds: {low_txt}~{up_txt}",
        ]
        if any(s.strip() for s in lines):
            painter.setRenderHint(QPainter.Antialiasing)
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            fm = QFontMetrics(font)
            pad_x, pad_y, vgap = 8, 4, 2
            tw = max(fm.width(s) for s in lines)
            line_h = fm.height()
            total_h = len(lines) * line_h + (len(lines)-1) * vgap

            # Decide left/right based on 3D preview position. Use top row, opposite x side.
            x_left = 6
            x_right = max(6, self.width() - (tw + pad_x*2) - 6)
            x = x_left
            if self.threed_view is not None:
                try:
                    tv = self.threed_view
                    # treat preview on left half → place overlay on right, else left
                    if tv.x() <= self.width() // 2:
                        x = x_right
                    else:
                        x = x_left
                except Exception:
                    x = x_left
            y = 6
            bg_rect = QRect(x, y, tw + pad_x*2, total_h + pad_y*2)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 140))
            painter.setPen(QPen(QColor(255, 255, 255)))
            tx = x + pad_x
            ty = y + pad_y + fm.ascent()
            for i, s in enumerate(lines):
                painter.drawText(tx, ty + i*(line_h + vgap), s)

        if self.curr_idx > self.top_idx or self.curr_idx < self.bottom_idx:
            painter.setPen(QPen(QColor(128,0,0), 2, Qt.DotLine))
        else:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        [ x1, y1, x2, y2 ] = self.get_crop_area()
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def apply_threshold_and_colorize(self,qt_pixmap, threshold, color=np.array([0, 255, 0], dtype=np.uint8)):
        qt_image = qt_pixmap.toImage()
        width = qt_image.width()
        height = qt_image.height()
        buffer = qt_image.bits()
        buffer.setsize(qt_image.byteCount())
        qt_image_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        
        # Extract the alpha channel (if present)
        if qt_image_array.shape[2] == 4:
            qt_image_array = qt_image_array[:, :, :3]  # Remove the alpha channel

        color = np.array([0, 255, 0], dtype=np.uint8)

        # Check the dtype of image_array
        if qt_image_array.dtype != np.uint8:
            raise ValueError("image_array should have dtype np.uint8")

        # Check the threshold value (example threshold)
        threshold = self.isovalue
        if not 0 <= threshold <= 255:
            raise ValueError("Threshold should be in the range 0-255")
        
        [ x1, y1, x2, y2 ] = self.get_crop_area()
        if x1 == x2 == y1 == y2 == 0:
            # whole pixmap is selected
            x1, x2, y1, y2 = 0, qt_image_array.shape[1], 0, qt_image_array.shape[0]

        if self.is_inverse:
            region_mask = (qt_image_array[y1:y2+1, x1:x2+1, 0] <= threshold)
        else:
            region_mask = (qt_image_array[y1:y2+1, x1:x2+1, 0] > threshold)

        # Apply the threshold and colorize
        qt_image_array[y1:y2+1, x1:x2+1][region_mask] = color

        # Convert the NumPy array back to a QPixmap
        height, width, channel = qt_image_array.shape
        bytes_per_line = 3 * width
        qt_image = QImage(np.copy(qt_image_array.data), width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Convert the QImage to a QPixmap
        modified_pixmap = QPixmap.fromImage(qt_image)
        return modified_pixmap

    def set_image(self,file_path):
        #print("set_image", file_path)
        # check if file exists (try lowercase extension if original doesn't exist)
        actual_path = file_path
        if not os.path.exists(file_path):
            # Try with lowercase extension
            base, ext = os.path.splitext(file_path)
            alt_path = base + ext.lower()
            if os.path.exists(alt_path):
                actual_path = alt_path
            else:
                self.curr_pixmap = None
                self.orig_pixmap = None
                self.crop_from_x = -1
                self.crop_from_y = -1
                self.crop_to_x = -1
                self.crop_to_y = -1
                self.canvas_box = None
                return
        self.fullpath = actual_path
        self.curr_pixmap = self.orig_pixmap = QPixmap(actual_path)

        self.setPixmap(self.curr_pixmap)
        self.calculate_resize()
        # If ROI not yet set, set to full image by default
        if self.crop_from_x < 0 or self.crop_to_x < 0 or self.crop_from_y < 0 or self.crop_to_y < 0:
            self.set_full_roi()
        if self.canvas_box:
            self.crop_from_x = self._2imgx(self.canvas_box.x())
            self.crop_from_y = self._2imgy(self.canvas_box.y())
            self.crop_to_x = self._2imgx(self.canvas_box.x() + self.canvas_box.width())
            self.crop_to_y = self._2imgy(self.canvas_box.y() + self.canvas_box.height())

    def set_top_idx(self, top_idx):
        self.top_idx = top_idx

    def set_curr_idx(self, curr_idx):
        self.curr_idx = curr_idx

    def set_bottom_idx(self, bottom_idx):
        self.bottom_idx = bottom_idx

    def calculate_resize(self):
        #print("objectviewer calculate resize")
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(DISTANCE_THRESHOLD)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()

            self.curr_pixmap = self.orig_pixmap.scaled(int(self.orig_width*self.scale/self.image_canvas_ratio),int(self.orig_width*self.scale/self.image_canvas_ratio), Qt.KeepAspectRatio)
            # Always colorize current slice by threshold. If range not set, treat as full stack
            if self.isovalue > 0:
                if self.bottom_idx < 0 or self.top_idx < 0 or self.bottom_idx > self.top_idx:
                    # default to full range
                    pass
                self.curr_pixmap = self.apply_threshold_and_colorize(self.curr_pixmap, self.isovalue)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.calculate_resize()
        self.object_dialog.mcube_widget.reposition_self()

        if self.canvas_box:
            self.canvas_box = QRect(self._2canx(self.crop_from_x), self._2cany(self.crop_from_y), self._2canx(self.crop_to_x - self.crop_from_x), self._2cany(self.crop_to_y - self.crop_from_y))
        self.threed_view.resize_self()
        return super().resizeEvent(a0)

class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_app = QApplication.instance()

        self.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
        self.setWindowTitle("{} v{}".format(self.tr("CT Harvester"), PROGRAM_VERSION))
        self.setGeometry(QRect(100, 100, 600, 550))
        self.settings_hash = {}
        self.level_info = []
        self.curr_level_idx = 0
        self.prev_level_idx = 0
        self.default_directory = "."
        self.threadpool = QThreadPool()  # Initialize threadpool for multithreading
        logger.info(f"Initialized ThreadPool with maxThreadCount={self.threadpool.maxThreadCount()}")
        self.read_settings()

        margin = QMargins(11,0,11,0)

        # add file open dialog
        self.dirname_layout = QHBoxLayout()
        self.dirname_widget = QWidget()
        self.btnOpenDir = QPushButton(self.tr("Open Directory"))
        self.btnOpenDir.clicked.connect(self.open_dir)
        self.edtDirname = QLineEdit()
        self.edtDirname.setReadOnly(True)
        self.edtDirname.setText("")
        self.edtDirname.setPlaceholderText(self.tr("Select directory to load CT data"))
        self.edtDirname.setMinimumWidth(400)
        self.edtDirname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add checkbox for Rust module
        self.cbxUseRust = QCheckBox(self.tr("Use Rust"))
        self.cbxUseRust.setChecked(True)  # Default to using Rust if available
        self.cbxUseRust.setToolTip(self.tr("Use high-performance Rust module for thumbnail generation"))

        self.dirname_layout.addWidget(self.edtDirname,stretch=1)
        self.dirname_layout.addWidget(self.cbxUseRust,stretch=0)
        self.dirname_layout.addWidget(self.btnOpenDir,stretch=0)
        self.dirname_widget.setLayout(self.dirname_layout)
        self.dirname_layout.setContentsMargins(margin)

        ''' image info layout '''
        self.image_info_layout = QHBoxLayout()
        self.image_info_widget = QWidget()
        self.lblLevel = QLabel(self.tr("Level"))
        self.comboLevel = QComboBox()
        self.comboLevel.currentIndexChanged.connect(self.comboLevelIndexChanged)
        self.edtImageDimension = QLineEdit()
        self.edtImageDimension.setReadOnly(True)
        self.edtImageDimension.setText("")
        self.edtNumImages = QLineEdit()
        self.edtNumImages.setReadOnly(True)
        self.edtNumImages.setText("")
        self.image_info_layout.addWidget(self.lblLevel)
        self.image_info_layout.addWidget(self.comboLevel)
        self.lblSize = QLabel(self.tr("Size"))
        self.lblCount = QLabel(self.tr("Count")) 
        self.image_info_layout.addWidget(self.lblSize)
        self.image_info_layout.addWidget(self.edtImageDimension)
        self.image_info_layout.addWidget(self.lblCount)
        self.image_info_layout.addWidget(self.edtNumImages)
        self.image_info_widget.setLayout(self.image_info_layout)
        #self.image_info_layout2.setSpacing(0)
        self.image_info_layout.setContentsMargins(margin)

        ''' image layout '''
        self.image_widget = QWidget()
        self.image_layout = QHBoxLayout()
        self.image_label = ObjectViewer2D(self.image_widget)
        self.image_label.object_dialog = self
        self.image_label.setMouseTracking(True)
        # Unified timeline slider (replaces single + range sliders)
        self.timeline = VerticalTimeline(0, 0)
        self.timeline.setStep(1, 10)
        self.timeline.setEnabled(False)  # Disable until data is loaded
        self.timeline.currentChanged.connect(self.sliderValueChanged)
        self.timeline.rangeChanged.connect(self.rangeSliderValueChanged)

        self.image_layout.addWidget(self.image_label,stretch=1)
        self.image_layout.addWidget(self.timeline)
        self.image_widget.setLayout(self.image_layout)
        self.image_layout.setContentsMargins(margin)

        self.threshold_slider = QSlider(Qt.Vertical)
        # Ensure full 0-255 range is visible on the labeled slider
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(60)
        self.threshold_slider.setSingleStep(1)
        self.threshold_slider.valueChanged.connect(self.slider2ValueChanged)
        self.threshold_slider.sliderReleased.connect(self.slider2SliderReleased)
        # external numeric readout to avoid any internal 0-99 label limit
        self.threshold_value_label = QLabel(str(self.threshold_slider.value()))
        self.threshold_value_label.setAlignment(Qt.AlignHCenter)
        self.threshold_value_label.setMinimumWidth(30)
        self.threshold_value_label.setStyleSheet("QLabel { color: #202020; }")
        self.threshold_container = QWidget()
        _vl = QVBoxLayout()
        _vl.setContentsMargins(0,0,0,0)
        _vl.setSpacing(4)
        _vl.addWidget(self.threshold_slider)
        _vl.addWidget(self.threshold_value_label)
        self.threshold_container.setLayout(_vl)
        self.image_layout.addWidget(self.threshold_container)

        ''' crop layout '''
        self.crop_layout = QHBoxLayout()
        self.crop_widget = QWidget()
        self.btnSetBottom = QPushButton(self.tr("Set Bottom"))
        self.btnSetBottom.clicked.connect(self.set_bottom)
        self.btnSetTop = QPushButton(self.tr("Set Top"))
        self.btnSetTop.clicked.connect(self.set_top)
        self.btnReset = QPushButton(self.tr("Reset"))
        self.btnReset.clicked.connect(self.reset_crop)
        self.cbxInverse = QCheckBox(self.tr("Inv."))
        self.cbxInverse.stateChanged.connect(self.cbxInverse_stateChanged)
        self.cbxInverse.setChecked(False)

        self.crop_layout.addWidget(self.btnSetBottom,stretch=1)
        self.crop_layout.addWidget(self.btnSetTop,stretch=1)
        self.crop_layout.addWidget(self.btnReset,stretch=1)
        self.crop_layout.addWidget(self.cbxInverse,stretch=0)
        self.crop_widget.setLayout(self.crop_layout)
        self.crop_layout.setContentsMargins(margin)

        ''' status layout '''
        self.status_layout = QHBoxLayout()
        self.status_widget = QWidget()
        self.edtStatus = QLineEdit()
        self.edtStatus.setReadOnly(True)
        self.edtStatus.setText("")
        self.status_layout.addWidget(self.edtStatus)
        self.status_widget.setLayout(self.status_layout)
        #self.status_layout.setSpacing(0)
        self.status_layout.setContentsMargins(margin)

        ''' button layout '''
        self.cbxOpenDirAfter = QCheckBox(self.tr("Open dir. after"))
        self.cbxOpenDirAfter.setChecked(True)
        self.btnSave = QPushButton(self.tr("Save cropped image stack"))
        self.btnSave.clicked.connect(self.save_result)
        self.btnExport = QPushButton(self.tr("Export 3D Model"))
        self.btnExport.clicked.connect(self.export_3d_model)
        self.btnPreferences = QPushButton(QIcon(resource_path('M2Preferences_2.png')), "")
        self.btnPreferences.clicked.connect(self.show_preferences)
        self.btnInfo = QPushButton(QIcon(resource_path('info.png')), "")
        self.btnInfo.clicked.connect(self.show_info)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cbxOpenDirAfter,stretch=0)
        self.button_layout.addWidget(self.btnSave,stretch=1)
        self.button_layout.addWidget(self.btnExport,stretch=1)
        self.button_layout.addWidget(self.btnPreferences,stretch=0)
        self.button_layout.addWidget(self.btnInfo,stretch=0)
        self.button_widget = QWidget()
        self.button_widget.setLayout(self.button_layout)
        self.button_layout.setContentsMargins(margin)

        ''' layouts put together '''
        self.sub_layout = QVBoxLayout()
        self.sub_widget = QWidget()
        #self.right_layout.setSpacing(0)
        self.sub_layout.setContentsMargins(0,0,0,0)
        self.sub_widget.setLayout(self.sub_layout)
        #self.right_layout.addWidget(self.comboSize)
        self.sub_layout.addWidget(self.dirname_widget)
        self.sub_layout.addWidget(self.image_info_widget)
        self.sub_layout.addWidget(self.image_widget)
        self.sub_layout.addWidget(self.crop_widget)
        self.sub_layout.addWidget(self.button_widget)
        self.sub_layout.addWidget(self.status_widget)
        #self.right_layout.addWidget(self.btnSave)

        self.main_layout = QHBoxLayout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)
        self.main_layout.addWidget(self.sub_widget)


        ''' setting up texts'''
        self.status_text_format = self.tr("Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) Estimated stack size: {} MB [{}]")
        self.progress_text_1_1 = self.tr("Saving image stack...")
        self.progress_text_1_2 = self.tr("Saving image stack... {}/{}")
        self.progress_text_2_1 = self.tr("Generating thumbnails (Level {})")
        self.progress_text_2_2 = self.tr("Generating thumbnails (Level {}) - {}/{}")
        self.progress_text_3_1 = self.tr("Loading thumbnails (Level {})")
        self.progress_text_3_2 = self.tr("Loading thumbnails (Level {}) - {}/{}")

        self.setCentralWidget(self.main_widget)

        ''' initialize mcube_widget '''
        self.mcube_widget = MCubeWidget(self.image_label)
        self.mcube_widget.setGeometry(self.mcube_geometry)
        self.mcube_widget.recalculate_geometry()
        #self.mcube_geometry
        self.initialized = False

    def rangeSliderMoved(self):
        return
    
    def rangeSliderPressed(self):
        return

    def cbxInverse_stateChanged(self):
        if self.image_label.orig_pixmap is None:
            return
        self.mcube_widget.is_inverse = self.image_label.is_inverse = self.cbxInverse.isChecked()
        #self.mcube_widget.is_inverse = 
        self.image_label.calculate_resize()
        self.image_label.repaint()
        self.update_3D_view(True)

    def show_preferences(self):
        self.settings_dialog = PreferencesDialog(self)
        self.settings_dialog.setModal(True)
        self.settings_dialog.show()

    def show_info(self):
        self.info_dialog = InfoDialog(self)
        self.info_dialog.setModal(True)
        self.info_dialog.show()

    def update_language(self):
        translator = QTranslator()
        translator.load('CTHarvester_{}.qm'.format(self.m_app.language))
        self.m_app.installTranslator(translator)

        self.setWindowTitle("{} v{}".format(self.tr(PROGRAM_NAME), PROGRAM_VERSION))
        self.btnOpenDir.setText(self.tr("Open Directory"))
        self.edtDirname.setPlaceholderText(self.tr("Select directory to load CT data"))
        self.lblLevel.setText(self.tr("Level"))
        self.btnSetBottom.setText(self.tr("Set Bottom"))
        self.btnSetTop.setText(self.tr("Set Top"))
        self.btnReset.setText(self.tr("Reset"))
        self.cbxOpenDirAfter.setText(self.tr("Open dir. after"))
        self.btnSave.setText(self.tr("Save cropped image stack"))
        self.btnExport.setText(self.tr("Export 3D Model"))
        self.lblCount.setText(self.tr("Count"))
        self.lblSize.setText(self.tr("Size"))
        self.status_text_format = self.tr("Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) Estimated stack size: {} MB [{}]")
        self.progress_text_1_2 = self.tr("Saving image stack... {}/{}")
        self.progress_text_1_1 = self.tr("Saving image stack...")
        self.progress_text_2_1 = self.tr("Generating thumbnails (Level {})")
        self.progress_text_2_2 = self.tr("Generating thumbnails (Level {}) - {}/{}")
        self.progress_text_3_1 = self.tr("Loading thumbnails (Level {})")
        self.progress_text_3_2 = self.tr("Loading thumbnails (Level {}) - {}/{}")

    def set_bottom(self):
        # set lower bound to current index
        _, curr, _ = self.timeline.values()
        self.timeline.setLower(curr)
        self.update_status()
    def set_top(self):
        # set upper bound to current index
        _, curr, _ = self.timeline.values()
        self.timeline.setUpper(curr)
        self.update_status()

    #def resizeEvent(self, a0: QResizeEvent) -> None:
    #    #print("resizeEvent")
    #    return super().resizeEvent(a0)

    def update_3D_view_click(self):
        self.update_3D_view(True)

    def update_3D_view(self, update_volume=True):
        #print("update 3d view")
        volume, roi_box = self.get_cropped_volume()
        
        # Check if volume is empty
        if volume.size == 0:
            logger.warning("Empty volume in update_3D_view, skipping update")
            return
            
        # Calculate bounding box based on current level
        # The minimum_volume is always the smallest level, but we need to scale it
        # based on the current viewing level
        if hasattr(self, 'level_info') and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2 ** level_diff  # Each level is 2x the size of the next
        else:
            # Default to no scaling if level_info is not available
            scale_factor = 1
        
        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape
        
        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor
        
        bounding_box = [0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1]
        
        # Scale the current slice value as well
        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0
        
        self.mcube_widget.update_boxes(bounding_box, roi_box, curr_slice_val)
        self.mcube_widget.adjust_boxes()

        if update_volume:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.mcube_widget.update_volume(volume)
            self.mcube_widget.generate_mesh_multithread()
            QApplication.restoreOverrideCursor()
        self.mcube_widget.adjust_volume()

    def update_curr_slice(self):
        # Check if minimum_volume is initialized
        if not hasattr(self, 'minimum_volume') or self.minimum_volume is None or len(self.minimum_volume) == 0:
            logger.warning("minimum_volume not initialized in update_curr_slice")
            return
            
        # Calculate bounding box based on current level
        if hasattr(self, 'level_info') and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2 ** level_diff
        else:
            scale_factor = 1
        
        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape
        
        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor
        
        bounding_box = [0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1]
        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0
        
        self.update_3D_view(False)

    def get_cropped_volume(self):
        # Check if level_info is initialized and curr_level_idx is valid
        if not hasattr(self, 'level_info') or not self.level_info:
            logger.warning("level_info not initialized in get_cropped_volume")
            # Return empty volume and box
            return np.array([]), [0, 0, 0, 0, 0, 0]
        
        if not hasattr(self, 'curr_level_idx'):
            self.curr_level_idx = 0
        
        # Ensure curr_level_idx is within bounds
        if self.curr_level_idx >= len(self.level_info):
            logger.warning(f"curr_level_idx {self.curr_level_idx} out of bounds, resetting to 0")
            self.curr_level_idx = 0
        
        level_info = self.level_info[self.curr_level_idx]
        seq_begin = level_info['seq_begin']
        seq_end = level_info['seq_end']
        image_count = seq_end - seq_begin + 1

        # get current size
        curr_width = level_info['width']
        curr_height = level_info['height']

        # get top and bottom idx; default to full range if not set
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx
        if top_idx < 0 or bottom_idx < 0 or top_idx < bottom_idx:
            bottom_idx = 0
            top_idx = image_count - 1

        #get current crop box
        crop_box = self.image_label.get_crop_area(imgxy=True)

        # get cropbox coordinates when image width and height is 1
        from_x = crop_box[0] / float(curr_width)
        from_y = crop_box[1] / float(curr_height)
        to_x = crop_box[2] / float(curr_width)
        to_y = crop_box[3] / float(curr_height)

        # get top idx and bottom idx when image count is 1
        top_idx = top_idx / float(image_count)
        bottom_idx = bottom_idx / float(image_count)

        # get cropped volume for smallest size
        smallest_level_info = self.level_info[-1]

        smallest_count = smallest_level_info['seq_end'] - smallest_level_info['seq_begin'] + 1
        bottom_idx = int(bottom_idx * smallest_count)
        top_idx = int(top_idx * smallest_count)
        # clamp
        bottom_idx = max(0, min(bottom_idx, smallest_count-1))
        top_idx = max(0, min(top_idx, smallest_count))
        if top_idx <= bottom_idx:
            top_idx = min(bottom_idx+1, smallest_count)
        from_x = int(from_x * smallest_level_info['width'])
        from_y = int(from_y * smallest_level_info['height'])
        to_x = int(to_x * smallest_level_info['width'])-1
        to_y = int(to_y * smallest_level_info['height'])-1

        # Ensure minimum_volume is a numpy array
        if isinstance(self.minimum_volume, list):
            if len(self.minimum_volume) > 0:
                self.minimum_volume = np.array(self.minimum_volume)
            else:
                logger.error("minimum_volume is empty list")
                return np.array([]), []
        
        volume = self.minimum_volume[bottom_idx:top_idx, from_y:to_y, from_x:to_x]
        
        # Scale ROI box to current level coordinates
        # The ROI is currently in smallest level coordinates, need to scale to current level
        smallest_level_idx = len(self.level_info) - 1
        level_diff = smallest_level_idx - self.curr_level_idx
        scale_factor = 2 ** level_diff
        
        # Scale the ROI coordinates
        scaled_roi = [
            bottom_idx * scale_factor,
            top_idx * scale_factor,
            from_y * scale_factor,
            to_y * scale_factor,
            from_x * scale_factor,
            to_x * scale_factor
        ]
        
        return volume, scaled_roi

    def export_3d_model(self):
        # open dir dialog for save
        #logger.info("export_3d_model method called")
        threed_volume = []

        obj_filename, _ = QFileDialog.getSaveFileName(self, "Save File As", self.edtDirname.text(), "OBJ format (*.obj)")
        if obj_filename == "":
            logger.info("Export cancelled")
            return
        logger.info(f"Exporting 3D model to: {obj_filename}")

        try:
            threed_volume, _ = self.get_cropped_volume()
            isovalue = self.image_label.isovalue
            vertices, triangles = mcubes.marching_cubes(threed_volume, isovalue)

            for i in range(len(vertices)):
                vertices[i] = np.array([vertices[i][2],vertices[i][0],vertices[i][1]])
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to generate 3D mesh: {e}"))
            return


        # write as obj file format
        try:
            with open(obj_filename, 'w') as fh:
                for v in vertices:
                    fh.write('v {} {} {}\n'.format(v[0], v[1], v[2]))
                #for vn in vertex_normals:
                #    fh.write('vn {} {} {}\n'.format(vn[0], vn[1], vn[2]))
                #for f in triangles:
                #    fh.write('f {}/{} {}/{} {}/{}\n'.format(f[0]+1, f[0]+1, f[1]+1, f[1]+1, f[2]+1, f[2]+1))
                for f in triangles:
                    fh.write('f {} {} {}\n'.format(f[0]+1, f[1]+1, f[2]+1))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to save OBJ file: {e}"))
            logger.error(f"Error saving OBJ file: {e}")

    def save_result(self):
        # open dir dialog for save
        #logger.info("save_result method called")
        target_dirname = QFileDialog.getExistingDirectory(self, self.tr('Select directory to save'), self.edtDirname.text())
        if target_dirname == "":
            logger.info("Save cancelled")
            return
        #logger.info(f"Saving results to: {target_dirname}")
        # get crop box info
        from_x = self.image_label.crop_from_x
        from_y = self.image_label.crop_from_y
        to_x = self.image_label.crop_to_x
        to_y = self.image_label.crop_to_y
        # get size idx
        size_idx = self.comboLevel.currentIndex()
        # get filename from level from idx
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx

        current_count = 0
        total_count = top_idx - bottom_idx + 1
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        self.progress_dialog.lbl_text.setText(self.progress_text_1_1)
        self.progress_dialog.pb_progress.setValue(0)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        for i, idx in enumerate(range(bottom_idx, top_idx+1)):
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
            # get full path
            if size_idx == 0:
                orig_dirname = self.edtDirname.text()
            else:
                orig_dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            fullpath = os.path.join(orig_dirname, filename)
            # open image
            try:
                img = Image.open(fullpath)
            except Exception as e:
                logger.error(f"Error opening image {fullpath}: {e}")
                continue
            # crop image
            if from_x > -1:
                img = img.crop((from_x, from_y, to_x, to_y))
            # save image
            img.save(os.path.join(target_dirname, filename))

            self.progress_dialog.lbl_text.setText(self.progress_text_1_2.format(i+1, int(total_count)))
            self.progress_dialog.pb_progress.setValue(int(((i+1)/float(int(total_count)))*100))
            self.progress_dialog.update()
            QApplication.processEvents()

        QApplication.restoreOverrideCursor()
        self.progress_dialog.close()
        self.progress_dialog = None
        if self.cbxOpenDirAfter.isChecked():
            os.startfile(target_dirname)

    def rangeSliderValueChanged(self):
        #print("range slider value changed")
        try:
            # Check if necessary attributes are initialized
            if not hasattr(self, 'level_info') or not self.level_info:
                # This is expected during initialization when sliders are disabled
                return
            
            lo, _, hi = self.timeline.values()
            bottom_idx, top_idx = lo, hi
            self.image_label.set_bottom_idx(bottom_idx)
            self.image_label.set_top_idx(top_idx)
            self.image_label.calculate_resize()
            self.image_label.repaint()
            self.update_3D_view(True)
            self.update_status()
        except Exception as e:
            logger.error(f"Error in rangeSliderValueChanged: {e}")

    def rangeSliderReleased(self):
        #print("range slider released")
        return


    def sliderValueChanged(self):
        if not self.initialized:
            return
        size_idx = self.comboLevel.currentIndex()
        _, curr_image_idx, _ = self.timeline.values()
        if size_idx < 0:
            size_idx = 0

        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + curr_image_idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # Match Rust naming: simple sequential numbering without prefix
            filename = "{:06}.tif".format(curr_image_idx)

        self.image_label.set_image(os.path.join(dirname, filename))
        self.image_label.set_curr_idx(curr_image_idx)
        self.update_curr_slice()

    def reset_crop(self):
        _, curr, _ = self.timeline.values()
        self.image_label.set_curr_idx(curr)
        self.image_label.reset_crop()
        self.timeline.setLower(self.timeline.minimum())
        self.timeline.setUpper(self.timeline.maximum())
        self.canvas_box = None
        self.update_status()

    def update_status(self):
        lo, _, hi = self.timeline.values()
        bottom_idx, top_idx = lo, hi
        [ x1, y1, x2, y2 ] = self.image_label.get_crop_area(imgxy=True)
        count = ( top_idx - bottom_idx + 1 )
        #self.status_format = self.tr("Crop indices: {}~{}    Cropped image size: {}x{}    Estimated stack size: {} MB [{}]")
        status_text = self.status_text_format.format(bottom_idx, top_idx, x2 - x1, y2 - y1, x1, y1, x2, y2, round(count * (x2 - x1 ) * (y2 - y1 ) / 1024 / 1024 , 2), str(self.image_label.edit_mode))
        self.edtStatus.setText(status_text)

    def initializeComboSize(self):
        #logger.info(f"initializeComboSize called, level_info count: {len(self.level_info) if hasattr(self, 'level_info') else 'not set'}")
        self.comboLevel.clear()
        for level in self.level_info:
            self.comboLevel.addItem( level['name'])
            #logger.info(f"Added level: {level['name']}, size: {level['width']}x{level['height']}, seq: {level['seq_begin']}-{level['seq_end']}")

    def comboLevelIndexChanged(self):
        """
        This method is called when the user selects a different level from the combo box.
        It updates the UI with information about the selected level, such as the image dimensions and number of images.
        It also updates the slider and range slider to reflect the number of images in the selected level.
        """
        # Check if level_info is initialized
        if not hasattr(self, 'level_info') or not self.level_info:
            logger.warning("level_info not initialized in comboLevelIndexChanged")
            return
        
        self.prev_level_idx = self.curr_level_idx if hasattr(self, 'curr_level_idx') else 0
        self.curr_level_idx = self.comboLevel.currentIndex()
        
        # Validate curr_level_idx
        if self.curr_level_idx < 0 or self.curr_level_idx >= len(self.level_info):
            logger.warning(f"Invalid curr_level_idx: {self.curr_level_idx}, resetting to 0")
            self.curr_level_idx = 0
            return
        
        level_info = self.level_info[self.curr_level_idx]
        seq_begin = level_info['seq_begin']
        seq_end = level_info['seq_end']

        self.edtImageDimension.setText(str(level_info['width']) + " x " + str(level_info['height']))
        image_count = seq_end - seq_begin + 1
        self.edtNumImages.setText(str(image_count))

        if not self.initialized:
            self.timeline.setRange(0, image_count - 1)
            self.timeline.setLower(0)
            self.timeline.setUpper(image_count - 1)
            self.timeline.setCurrent(0)
            self.timeline.setEnabled(True)  # Enable timeline now that data is loaded
            self.curr_level_idx = 0
            self.prev_level_idx = 0
            self.initialized = True


        level_diff = self.prev_level_idx - self.curr_level_idx
        _, curr_idx, _ = self.timeline.values()
        curr_idx = int(curr_idx * (2 ** level_diff))

        lo, _, hi = self.timeline.values()
        bottom_idx = int(lo * (2 ** level_diff))
        top_idx = int(hi * (2 ** level_diff))

        # apply new range and values to timeline
        self.timeline.setRange(0, image_count - 1)
        # clamp to range
        bottom_idx = max(0, min(bottom_idx, image_count - 1))
        top_idx = max(0, min(top_idx, image_count - 1))
        if bottom_idx > top_idx:
            bottom_idx, top_idx = top_idx, bottom_idx
        curr_idx = max(bottom_idx, min(curr_idx, top_idx))
        self.timeline.setLower(bottom_idx)
        self.timeline.setUpper(top_idx)
        self.timeline.setCurrent(curr_idx)

        self.sliderValueChanged()
        self.update_status()
        self.update_3D_view(True)

    def calculate_total_thumbnail_work(self, seq_begin, seq_end, size, max_size):
        """Calculate total number of operations for all LoD levels with size weighting"""
        import logging
        logger = logging.getLogger(__name__)

        total_work = 0
        weighted_work = 0  # Work weighted by image size
        temp_seq_begin = seq_begin
        temp_seq_end = seq_end
        temp_size = size
        level_count = 0
        level_details = []
        self.level_sizes = []  # Store size info for each level
        self.level_work_distribution = []  # Store work distribution per level

        while temp_size >= max_size:
            temp_size /= 2
            level_count += 1
            # Each level processes half the images from previous level
            images_to_process = (temp_seq_end - temp_seq_begin + 1) // 2 + 1
            total_work += images_to_process

            # Weight by relative image size (smaller images process faster)
            size_factor = (temp_size / size) ** 2  # Quadratic because it's 2D

            # Additional weight for first level due to reading original images from disk
            if level_count == 1:
                size_factor *= 1.5  # First level is 50% slower due to I/O overhead

            weighted_work += images_to_process * size_factor

            level_details.append(f"Level {level_count}: {images_to_process} images, size={int(temp_size)}px, weight={size_factor:.2f}")
            self.level_sizes.append((level_count, temp_size, images_to_process))
            self.level_work_distribution.append({
                'level': level_count,
                'images': images_to_process,
                'size': int(temp_size),
                'weight': size_factor
            })
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
    
    def create_thumbnail(self):
        """
        Creates a thumbnail using Rust module if available and enabled, otherwise falls back to Python implementation.
        """
        import time
        from datetime import datetime

        # Check if user wants to use Rust module
        use_rust_preference = self.cbxUseRust.isChecked() if hasattr(self, 'cbxUseRust') else True

        # Try to use Rust module if preferred
        if use_rust_preference:
            try:
                from ct_thumbnail import build_thumbnails
                use_rust = True
                logger.info("Using Rust-based thumbnail generation")
            except ImportError:
                use_rust = False
                logger.warning("ct_thumbnail module not found, falling back to Python implementation")
        else:
            use_rust = False
            logger.info("Using Python implementation (Rust module disabled by user)")

        if use_rust:
            return self.create_thumbnail_rust()
        else:
            return self.create_thumbnail_python()

    def create_thumbnail_rust(self):
        """
        Creates a thumbnail using Rust-based high-performance module.
        """
        import time
        from datetime import datetime
        from ct_thumbnail import build_thumbnails

        # Start timing
        self.thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now()

        dirname = self.edtDirname.text()

        logger.info(f"=== Starting Rust thumbnail generation ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {dirname}")

        # Initialize progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        # Set initial progress text
        self.progress_dialog.lbl_text.setText(self.tr("Generating thumbnails"))
        self.progress_dialog.lbl_detail.setText(self.tr("Initializing..."))

        # Setup progress bar (0-100%)
        self.progress_dialog.pb_progress.setMinimum(0)
        self.progress_dialog.pb_progress.setMaximum(100)
        self.progress_dialog.pb_progress.setValue(0)

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Variables for progress tracking
        self.last_progress = 0
        self.progress_start_time = time.time()
        self.rust_cancelled = False

        def progress_callback(percentage):
            """Progress callback from Rust module"""
            # Update progress bar
            self.progress_dialog.pb_progress.setValue(int(percentage))

            # Calculate elapsed time and ETA
            elapsed = time.time() - self.progress_start_time
            if percentage > 0 and percentage < 100:
                eta = elapsed * (100 - percentage) / percentage
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta/60)}m {int(eta%60)}s"
                elapsed_str = f"{int(elapsed)}s" if elapsed < 60 else f"{int(elapsed/60)}m {int(elapsed%60)}s"

                # Update detail text
                self.progress_dialog.lbl_detail.setText(
                    f"{percentage:.1f}% - Elapsed: {elapsed_str} - ETA: {eta_str}"
                )
            else:
                self.progress_dialog.lbl_detail.setText(f"{percentage:.1f}%")

            # Check for cancellation
            if self.progress_dialog.is_cancelled:
                self.rust_cancelled = True
                return False  # Signal Rust to stop (if it supports this)

            # Process events to keep UI responsive
            QApplication.processEvents()

            self.last_progress = percentage
            return True

        # Run Rust thumbnail generation with file pattern info
        success = False
        try:
            # Pass the file pattern information to Rust
            prefix = self.settings_hash.get('prefix', '')
            file_type = self.settings_hash.get('file_type', 'tif')
            seq_begin = int(self.settings_hash.get('seq_begin', 0))
            seq_end = int(self.settings_hash.get('seq_end', 0))
            index_length = int(self.settings_hash.get('index_length', 0))

            # Call Rust with pattern parameters
            build_thumbnails(
                dirname,
                progress_callback,
                prefix,
                file_type,
                seq_begin,
                seq_end,
                index_length
            )
            success = True
        except Exception as e:
            logger.error(f"Error during Rust thumbnail generation: {e}")
            QMessageBox.warning(self, self.tr("Warning"),
                               self.tr(f"Rust thumbnail generation failed: {e}\nFalling back to Python implementation."))

        QApplication.restoreOverrideCursor()

        # Calculate total time
        total_elapsed = time.time() - self.thumbnail_start_time
        thumbnail_end_datetime = datetime.now()

        logger.info(f"=== Rust thumbnail generation completed ===")
        logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")

        if success and not self.rust_cancelled:
            # Load the generated thumbnails
            self.load_rust_thumbnail_data()

            # Update progress dialog
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation complete"))
            self.progress_dialog.lbl_detail.setText(f"Completed in {int(total_elapsed)}s")
        else:
            if self.rust_cancelled:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation cancelled"))
            else:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation failed"))

            # Initialize minimum_volume as empty to prevent errors
            if not hasattr(self, 'minimum_volume'):
                self.minimum_volume = []
                logger.warning("Initialized empty minimum_volume after Rust thumbnail generation failure")

        # Close progress dialog
        self.progress_dialog.close()
        self.progress_dialog = None

        # Initialize combo boxes
        self.initializeComboSize()
        self.reset_crop()

        # Trigger initial display
        if self.comboLevel.count() > 0:
            self.comboLevel.setCurrentIndex(0)
            if not self.initialized:
                self.comboLevelIndexChanged()

    def load_rust_thumbnail_data(self):
        """Load generated thumbnail data from Rust module into minimum_volume for 3D visualization"""

        MAX_THUMBNAIL_SIZE = 512  # Must match Python's MAX_THUMBNAIL_SIZE

        # Find the highest level thumbnail directory
        thumbnail_base = os.path.join(self.edtDirname.text(), ".thumbnail")

        if not os.path.exists(thumbnail_base):
            logger.warning("No thumbnail directory found")
            return

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
            return

        # Find the appropriate level to load (first level with size < MAX_THUMBNAIL_SIZE)
        level_num = None
        thumbnail_dir = None

        for ln, ld in level_dirs:
            # Check the size of images in this level
            files = [f for f in os.listdir(ld) if f.endswith('.tif')]
            if files:
                img = Image.open(os.path.join(ld, files[0]))
                width, height = img.size
                img.close()

                size = max(width, height)
                if size < MAX_THUMBNAIL_SIZE:
                    level_num = ln
                    thumbnail_dir = ld
                    logger.info(f"Found appropriate level {level_num} with size {width}x{height} (< {MAX_THUMBNAIL_SIZE})")
                    break
                else:
                    logger.debug(f"Level {ln} size {width}x{height} is >= {MAX_THUMBNAIL_SIZE}, continuing...")

        if level_num is None or thumbnail_dir is None:
            # Fallback to highest level if none meet the criteria
            level_num, thumbnail_dir = level_dirs[-1]
            logger.warning(f"No level with size < {MAX_THUMBNAIL_SIZE} found, using highest level {level_num}")

        logger.info(f"Loading thumbnails from level {level_num}: {thumbnail_dir}")

        try:
            # List all tif files in the directory
            files = sorted([f for f in os.listdir(thumbnail_dir) if f.endswith('.tif')])

            logger.info(f"Found {len(files)} thumbnail files")

            self.minimum_volume = []
            for file in files:
                filepath = os.path.join(thumbnail_dir, file)
                img = Image.open(filepath)
                img_array = np.array(img)

                # Normalize to 8-bit range (0-255) for marching cubes
                # Check if image is 16-bit
                if img_array.dtype == np.uint16:
                    # Convert 16-bit to 8-bit
                    img_array = (img_array / 256).astype(np.uint8)
                elif img_array.dtype != np.uint8:
                    # For other types, normalize to 0-255
                    img_min = img_array.min()
                    img_max = img_array.max()
                    if img_max > img_min:
                        img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                    else:
                        img_array = np.zeros_like(img_array, dtype=np.uint8)

                self.minimum_volume.append(img_array)
                img.close()

            if len(self.minimum_volume) > 0:
                self.minimum_volume = np.array(self.minimum_volume)
                logger.info(f"Loaded {len(self.minimum_volume)} thumbnails, shape: {self.minimum_volume.shape}")

                # Update level_info to match what Python implementation expects
                self.level_info = []

                # Add level 0 (original images) info if we have settings_hash
                if hasattr(self, 'settings_hash'):
                    self.level_info.append({
                        'name': 'Level 0',
                        'width': int(self.settings_hash.get('image_width', 0)),
                        'height': int(self.settings_hash.get('image_height', 0)),
                        'seq_begin': int(self.settings_hash.get('seq_begin', 0)),
                        'seq_end': int(self.settings_hash.get('seq_end', 0))
                    })

                # Add thumbnail levels
                for i, (level_num, level_dir) in enumerate(level_dirs):
                    # Get dimensions from first file in level
                    files = [f for f in os.listdir(level_dir) if f.endswith('.tif')]
                    if files:
                        img = Image.open(os.path.join(level_dir, files[0]))
                        width, height = img.size
                        img.close()

                        self.level_info.append({
                            'name': f"Level {level_num}",
                            'width': width,
                            'height': height,
                            'seq_begin': 0,
                            'seq_end': len(files) - 1
                        })

                # Update 3D view with loaded thumbnails
                bounding_box = self.minimum_volume.shape
                if len(bounding_box) >= 3:
                    # Calculate proper bounding box
                    scaled_depth = bounding_box[0]
                    scaled_height = bounding_box[1]
                    scaled_width = bounding_box[2]

                    scaled_bounding_box = np.array([0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1])

                    try:
                        _, curr, _ = self.timeline.values()
                        denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
                        curr_slice_val = curr / denom * scaled_depth
                    except Exception:
                        curr_slice_val = 0

                    self.mcube_widget.update_boxes(scaled_bounding_box, scaled_bounding_box, curr_slice_val)
                    self.mcube_widget.adjust_boxes()
                    self.mcube_widget.update_volume(self.minimum_volume)
                    self.mcube_widget.generate_mesh()
                    self.mcube_widget.adjust_volume()
                    self.mcube_widget.show_buttons()

                    # Ensure the 3D widget doesn't cover the main image
                    self.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
                    self.mcube_widget.recalculate_geometry()

        except Exception as e:
            logger.error(f"Error loading Rust thumbnails: {e}")

    # Keep existing Python implementation as fallback
    def create_thumbnail_python(self):
        #logger.info("Starting thumbnail creation")
        """
        Creates a thumbnail of the image sequence by downsampling the images and averaging them.
        The resulting thumbnail is saved in a temporary directory and used to generate a mesh for visualization.
        This is the original Python implementation kept as fallback.
        """
        import time
        from datetime import datetime

        # Start timing for entire thumbnail generation
        self.thumbnail_start_time = time.time()  # Store as instance variable for access in ThumbnailManager
        thumbnail_start_time = self.thumbnail_start_time  # Keep local variable for backward compatibility
        thumbnail_start_datetime = datetime.now()

        MAX_THUMBNAIL_SIZE = 512
        size =  max(int(self.settings_hash['image_width']), int(self.settings_hash['image_height']))
        width = int(self.settings_hash['image_width'])
        height = int(self.settings_hash['image_height'])
        logger.info(f"=== Starting Python thumbnail generation (fallback) ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Image dimensions: width={width}, height={height}, size={size}")

        i = 0
        # create temporary directory for thumbnail
        dirname = self.edtDirname.text()

        self.minimum_volume = []
        seq_begin = self.settings_hash['seq_begin']
        seq_end = self.settings_hash['seq_end']
        logger.info(f"Processing sequence: {seq_begin} to {seq_end}, directory: {dirname}")
        
        # Calculate total work amount for all LoD levels
        total_work = self.calculate_total_thumbnail_work(seq_begin, seq_end, size, MAX_THUMBNAIL_SIZE)

        # Don't show initial estimate - will show "Estimating..." instead
        estimated_seconds = None  # Will be calculated after sampling
        time_estimate = "Estimating..."  # Show this initially

        # Store initial estimates for comparison at the end
        self.initial_estimate_seconds = 0  # No initial estimate since we're using sampling
        self.initial_estimate_str = time_estimate
        self.sampled_estimate_seconds = None  # Will be updated after sampling
        self.sampled_estimate_str = None

        logger.info(f"Starting thumbnail generation: {self.total_levels} levels, {total_work} operations")
        logger.info(f"Initial estimate: {time_estimate} (will be refined after sampling)")

        current_count = 0
        global_step_counter = 0  # Track overall progress

        # Variables for dynamic time estimation
        # For 3-stage sampling, we need at least 3x the base sample size
        base_sample = max(20, min(30, int(total_work * 0.02)))  # Base: 20-30 images
        self.sample_size = base_sample  # This is the base unit for each stage
        total_sample = base_sample * 3  # Total samples across all stages
        logger.info(f"Multi-stage sampling: {base_sample} images per stage, {total_sample} total images")
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        
        # Setup unified progress with weighted work amount
        # Use weighted_total_work if available for accurate progress tracking
        progress_total = self.weighted_total_work if hasattr(self, 'weighted_total_work') else total_work
        self.progress_dialog.setup_unified_progress(progress_total, None)  # Pass None to show "Estimating..."
        self.progress_dialog.lbl_text.setText(self.tr("Generating thumbnails"))
        self.progress_dialog.lbl_detail.setText("Estimating...")

        # Pass level work distribution to progress dialog for better ETA calculation
        if hasattr(self, 'level_work_distribution'):
            self.progress_dialog.level_work_distribution = self.level_work_distribution
            self.progress_dialog.weighted_total_work = self.weighted_total_work
        
        QApplication.setOverrideCursor(Qt.WaitCursor)

        while True:
            # Start timing for this level
            level_start_time = time.time()
            level_start_datetime = datetime.now()

            size /= 2
            width = int(width / 2)
            height = int(height / 2)

            if i == 0:
                from_dir = dirname
            else:
                from_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i))

            total_count = seq_end - seq_begin + 1

            # create thumbnail
            to_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i+1))
            if not os.path.exists(to_dir):
                os.makedirs(to_dir)
            last_count = 0

            logger.info(f"--- Level {i+1} ---")
            logger.info(f"Level {i+1} start time: {level_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"Level {i+1}: Processing {total_count} images (size: {int(size)}x{int(size)})")

            # Initialize thumbnail manager for multithreaded processing
            # Always create a new thumbnail manager to ensure it uses the current progress_dialog
            self.thumbnail_manager = ThumbnailManager(self, self.progress_dialog, self.threadpool)

            # Use multithreaded processing for this level
            level_img_arrays, was_cancelled = self.thumbnail_manager.process_level(
                i, from_dir, to_dir, seq_begin, seq_end,
                self.settings_hash, size, MAX_THUMBNAIL_SIZE, global_step_counter
            )

            # Calculate and log time for this level
            level_end_datetime = datetime.now()
            level_elapsed = time.time() - level_start_time
            logger.info(f"Level {i+1} end time: {level_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"Level {i+1}: Completed in {level_elapsed:.2f} seconds")

            # Update global step counter based on actual progress made
            global_step_counter = self.thumbnail_manager.global_step_counter

            # Add collected images to minimum_volume if within size limit
            if size < MAX_THUMBNAIL_SIZE:
                for img_array in level_img_arrays:
                    self.minimum_volume.append(img_array)
                logger.info(f"Level {i+1}: Added {len(level_img_arrays)} images to minimum_volume")
            
            # Check for cancellation
            if was_cancelled or self.progress_dialog.is_cancelled:
                logger.info("Thumbnail generation cancelled by user")
                break
            
            # Set last_count for next level calculation (assume successful processing)
            last_count = 0
                
            i+= 1
            seq_end = int((seq_end - seq_begin) / 2) + seq_begin + last_count
            
            # Only add to level_info if this level doesn't already exist
            level_name = f"Level {i}"
            level_exists = any(level['name'] == level_name for level in self.level_info)
            if not level_exists:
                self.level_info.append( {'name': level_name, 'width': width, 'height': height, 'seq_begin': seq_begin, 'seq_end': seq_end} )
                #logger.info(f"Added new level to level_info: {level_name}")
            else:
                pass  #logger.info(f"Level {level_name} already exists in level_info, skipping")
            if size < MAX_THUMBNAIL_SIZE:
                #logger.info(f"Reached thumbnail size limit. Total images collected: {len(self.minimum_volume)}")
                if len(self.minimum_volume) > 0:
                    self.minimum_volume = np.array(self.minimum_volume)
                    bounding_box = self.minimum_volume.shape
                    #logger.info(f"Final volume shape: {bounding_box}")
                    # Check if we have a valid 3D volume
                    if len(bounding_box) >= 3:
                        # Calculate proper bounding box for current level
                        smallest_level_idx = len(self.level_info) - 1
                        level_diff = smallest_level_idx - self.curr_level_idx
                        scale_factor = 2 ** level_diff
                        
                        scaled_depth = bounding_box[0] * scale_factor
                        scaled_height = bounding_box[1] * scale_factor
                        scaled_width = bounding_box[2] * scale_factor
                        
                        scaled_bounding_box = np.array([0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1])
                        try:
                            _, curr, _ = self.timeline.values()
                            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
                            curr_slice_val = curr / denom * scaled_depth
                        except Exception:
                            curr_slice_val = 0

                        self.mcube_widget.update_boxes(scaled_bounding_box, scaled_bounding_box, curr_slice_val)
                        self.mcube_widget.adjust_boxes()
                        self.mcube_widget.update_volume(self.minimum_volume)
                        self.mcube_widget.generate_mesh()
                        self.mcube_widget.adjust_volume()
                        self.mcube_widget.show_buttons()
                        
                        # Ensure the 3D widget doesn't cover the main image
                        self.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
                        self.mcube_widget.recalculate_geometry()
                    else:
                        logger.warning(f"Invalid volume shape: {bounding_box}. Expected 3D array.")
                else:
                    logger.warning("No volume data collected for thumbnail generation")
                break
            
        QApplication.restoreOverrideCursor()

        # Calculate and log total time for entire thumbnail generation
        thumbnail_end_datetime = datetime.now()
        total_elapsed = time.time() - thumbnail_start_time

        logger.info(f"=== Thumbnail generation completed ===")
        logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
        logger.info(f"Total levels processed: {i + 1}")
        if total_elapsed > 0:
            images_per_second = total_work / total_elapsed if 'total_work' in locals() else 0
            logger.info(f"Average processing speed: {images_per_second:.1f} images/second")

        # Compare estimated vs actual time
        logger.info(f"=== Time Estimation Accuracy ===")
        if self.initial_estimate_seconds > 0:
            logger.info(f"Initial estimate (before sampling): {self.initial_estimate_str} ({self.initial_estimate_seconds:.1f}s)")
            initial_accuracy = (1 - abs(self.initial_estimate_seconds - total_elapsed) / total_elapsed) * 100 if total_elapsed > 0 else 0
            logger.info(f"Initial estimate accuracy: {initial_accuracy:.1f}%")
        else:
            logger.info(f"No initial estimate was provided (used sampling instead)")

        if self.sampled_estimate_str:
            logger.info(f"Estimate after sampling: {self.sampled_estimate_str} ({self.sampled_estimate_seconds:.1f}s)")
            sampled_accuracy = (1 - abs(self.sampled_estimate_seconds - total_elapsed) / total_elapsed) * 100 if total_elapsed > 0 else 0
            logger.info(f"Sampling estimate accuracy: {sampled_accuracy:.1f}%")

        actual_time_str = f"{int(total_elapsed)}s" if total_elapsed < 60 else f"{int(total_elapsed/60)}m {int(total_elapsed%60)}s"
        logger.info(f"Actual time taken: {actual_time_str} ({total_elapsed:.1f}s)")

        # Calculate overall generation statistics
        total_generated = 0
        total_loaded = 0
        if hasattr(self, 'thumbnail_manager'):
            total_generated = self.thumbnail_manager.generated_count
            total_loaded = self.thumbnail_manager.loaded_count
            generation_percentage = total_generated / (total_generated + total_loaded) * 100 if (total_generated + total_loaded) > 0 else 0
            logger.info(f"Overall: {total_generated} generated, {total_loaded} loaded ({generation_percentage:.1f}% generated)")

        # No longer saving coefficients - real-time sampling provides better accuracy
        # Each run measures actual performance including all variables:
        # - Drive speed (SSD/HDD/Network)
        # - Image dimensions
        # - Bit depth (8-bit, 16-bit, etc.)
        # - File format and compression
        # - Current CPU load
        # - Available memory
        if hasattr(self, 'weighted_total_work') and self.weighted_total_work > 0:
            actual_coefficient = total_elapsed / self.weighted_total_work
            logger.info(f"Actual performance: {actual_coefficient:.3f}s per weighted unit")
            logger.info(f"This varies based on image size, bit depth, drive speed, and system load")

        # Show completion or cancellation message
        if self.progress_dialog.is_cancelled:
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation cancelled"))
            self.progress_dialog.lbl_detail.setText("")
            logger.info("Thumbnail generation was cancelled by user")
        else:
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation complete"))
            self.progress_dialog.lbl_detail.setText("")

        self.progress_dialog.close()
        self.progress_dialog = None
        
        # If minimum_volume is still empty, try to load from the smallest existing thumbnail
        if len(self.minimum_volume) == 0:
            logger.info("minimum_volume is empty, trying to load from existing thumbnails")
            
            # Find the highest numbered thumbnail directory that exists
            thumbnail_base = os.path.join(self.edtDirname.text(), ".thumbnail")
            if os.path.exists(thumbnail_base):
                level_dirs = []
                for i in range(1, 10):  # Check up to level 9
                    level_dir = os.path.join(thumbnail_base, str(i))
                    if os.path.exists(level_dir):
                        level_dirs.append((i, level_dir))
                    else:
                        break
                
                if level_dirs:
                    # Use the highest level (smallest images)
                    level_num, thumbnail_dir = level_dirs[-1]
                    #logger.info(f"Loading thumbnails from level {level_num}: {thumbnail_dir}")
                    
                    try:
                        # List all image files in the directory
                        files = sorted([f for f in os.listdir(thumbnail_dir) 
                                      if f.endswith('.' + self.settings_hash['file_type'])])
                        
                        #logger.info(f"Found {len(files)} files in {thumbnail_dir}")
                        
                        for file in files:
                            filepath = os.path.join(thumbnail_dir, file)
                            img = Image.open(filepath)
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
                                    img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                                else:
                                    img_array = np.zeros_like(img_array, dtype=np.uint8)

                            self.minimum_volume.append(img_array)
                            img.close()

                        if len(self.minimum_volume) > 0:
                            self.minimum_volume = np.array(self.minimum_volume)
                            #logger.info(f"Loaded {len(self.minimum_volume)} thumbnails, shape: {self.minimum_volume.shape}")
                            
                            # Update 3D view
                            bounding_box = self.minimum_volume.shape
                            if len(bounding_box) >= 3:
                                # Calculate proper bounding box for current level
                                smallest_level_idx = len(self.level_info) - 1
                                level_diff = smallest_level_idx - self.curr_level_idx
                                scale_factor = 2 ** level_diff
                                
                                scaled_depth = bounding_box[0] * scale_factor
                                scaled_height = bounding_box[1] * scale_factor
                                scaled_width = bounding_box[2] * scale_factor
                                
                                scaled_bounding_box = np.array([0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1])
                                try:
                                    _, curr, _ = self.timeline.values()
                                    denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
                                    curr_slice_val = curr / denom * scaled_depth
                                except Exception:
                                    curr_slice_val = 0
                                
                                self.mcube_widget.update_boxes(scaled_bounding_box, scaled_bounding_box, curr_slice_val)
                                self.mcube_widget.adjust_boxes()
                                self.mcube_widget.update_volume(self.minimum_volume)
                                self.mcube_widget.generate_mesh()
                                self.mcube_widget.adjust_volume()
                                self.mcube_widget.show_buttons()
                                
                                # Ensure the 3D widget doesn't cover the main image
                                self.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
                                self.mcube_widget.recalculate_geometry()
                    except Exception as e:
                        logger.error(f"Error loading existing thumbnails: {e}")
        
        self.initializeComboSize()
        self.reset_crop()
        
        # Trigger initial display by setting combo index if items exist
        if self.comboLevel.count() > 0:
            #logger.info("Triggering initial display by setting combo index to 0")
            self.comboLevel.setCurrentIndex(0)
            # If comboLevelIndexChanged doesn't trigger, call it manually
            if not self.initialized:
                #logger.info("Manually calling comboLevelIndexChanged")
                self.comboLevelIndexChanged()

    def slider2ValueChanged(self, value):
            """
            Updates the isovalue of the image label and mcube widget based on the given slider value,
            and recalculates the image label's size.
            
            Args:
                value (float): The new value of the slider.
            """
            #print("value:", value)
            # update external readout to reflect 0-255 range accurately
            if hasattr(self, 'threshold_value_label'):
                self.threshold_value_label.setText(str(int(value)))
            self.image_label.set_isovalue(value)
            self.mcube_widget.set_isovalue(value)
            self.image_label.calculate_resize()
    
    def slider2SliderReleased(self):
        self.update_3D_view(True)

    def sort_file_list_from_dir(self, directory_path):
        # Step 1: Get a list of all files in the directory
        #directory_path = "/path/to/your/directory"  # Replace with the path to your directory
        all_files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

        # Step 2: Regular expression pattern
        pattern = r'^(.*?)(\d+)\.(\w+)$'

        ct_stack_files = []
        matching_files = []
        other_files = []
        prefix_hash = {}
        extension_hash = {}
        settings_hash = {}

        for file in all_files:
            if re.match(pattern, file):
                matching_files.append(file)
                if re.match(pattern, file).group(1) in prefix_hash:
                    prefix_hash[re.match(pattern, file).group(1)] += 1
                else:
                    prefix_hash[re.match(pattern, file).group(1)] = 1
                if re.match(pattern, file).group(3) in extension_hash:
                    extension_hash[re.match(pattern, file).group(3)] += 1
                else:
                    extension_hash[re.match(pattern, file).group(3)] = 1

            else:
                other_files.append(file)

        # determine prefix
        max_prefix_count = 0
        max_prefix = ""
        for prefix in prefix_hash:
            if prefix_hash[prefix] > max_prefix_count:
                max_prefix_count = prefix_hash[prefix]
                max_prefix = prefix
        
        #logger.info(f"Detected prefixes: {list(prefix_hash.keys())[:5]}")
        #logger.info(f"Most common prefix: '{max_prefix}' with {max_prefix_count} files")

        # determine extension
        max_extension_count = 0
        max_extension = ""
        for extension in extension_hash:
            if extension_hash[extension] > max_extension_count:
                max_extension_count = extension_hash[extension]
                max_extension = extension
        
        #logger.info(f"Most common extension: '{max_extension}' with {max_extension_count} files")

        if matching_files:
            for file in matching_files:
                if re.match(pattern, file).group(1) == max_prefix and re.match(pattern, file).group(3) == max_extension:
                    ct_stack_files.append(file)

        # Determine the pattern if needed further
        if ct_stack_files:
            # If there are CT stack files, we can determine some common patterns
            # Here as an example, we are just displaying the prefix of the first matched file
            # This can be expanded upon based on specific needs
            first_file = ct_stack_files[0]
            last_file = ct_stack_files[-1]
            imagefile_name = os.path.join(directory_path, first_file)
            # get width and height
            try:
                img = Image.open(imagefile_name)
                width, height = img.size
            except Exception as e:
                logger.error(f"Error opening image {imagefile_name}: {e}")
                return None


            match1 = re.match(pattern, first_file)
            match2 = re.match(pattern, last_file)

            if match1 and match2:
                start_index = match1.group(2)
                end_index = match2.group(2)
            image_count = int(match2.group(2)) - int(match1.group(2)) + 1
            number_of_images = len(ct_stack_files)
            seq_length = len(match1.group(2))

            settings_hash['prefix'] = max_prefix
            settings_hash['image_width'] = width
            settings_hash['image_height'] = height
            settings_hash['file_type'] = max_extension
            settings_hash['index_length'] = seq_length
            settings_hash['seq_begin'] = start_index
            settings_hash['seq_end'] = end_index
            settings_hash['index_length'] = int(settings_hash['index_length'])
            settings_hash['seq_begin'] = int(settings_hash['seq_begin'])
            settings_hash['seq_end'] = int(settings_hash['seq_end'])

            return settings_hash
        else:
            return None
        


    def open_dir(self):
            """
            Opens a directory dialog to select a directory containing image files and log files.
            Parses the log file to extract settings information and updates the UI accordingly.
            """
            print("open_dir method called")
            #logger.info("=" * 60)
            logger.info("open_dir method called - START")
            #logger.info("=" * 60)
            
            # Check current state
            if hasattr(self, 'minimum_volume'):
                pass
                #logger.info(f"Current minimum_volume state: type={type(self.minimum_volume)}, len={len(self.minimum_volume) if isinstance(self.minimum_volume, (list, np.ndarray)) else 'N/A'}")
            else:
                pass  #logger.info("minimum_volume not yet initialized")
            
            ddir = QFileDialog.getExistingDirectory(self, self.tr("Select directory"), self.m_app.default_directory)
            if ddir:
                logger.info(f"Selected directory: {ddir}")
                self.edtDirname.setText(ddir)
                self.m_app.default_directory = os.path.dirname(ddir)
            else:
                logger.info("Directory selection cancelled")
                return
            
            #logger.info("Resetting settings_hash and image_file_list")
            self.settings_hash = {}
            self.initialized = False
            image_file_list = []
            QApplication.setOverrideCursor(Qt.WaitCursor)

            try:
                files = [f for f in os.listdir(ddir) if os.path.isfile(os.path.join(ddir, f))]
                #logger.info(f"Found {len(files)} files in directory")
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to read directory: {e}"))
                logger.error(f"Failed to read directory: {e}")
                return

            log_files_found = 0
            for file in files:
                # get extension
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                    pass #image_file_list.append(file)
                elif ext == '.log':
                    log_files_found += 1
                    try:
                        settings = QSettings(os.path.join(ddir, file), QSettings.IniFormat)
                        prefix = settings.value("File name convention/Filename Prefix")
                        if not prefix:
                            continue
                        if file != prefix + ".log":
                            continue
                        
                        logger.info(f"Found valid log file: {file}")
                        self.settings_hash['prefix'] = settings.value("File name convention/Filename Prefix")
                        self.settings_hash['image_width'] = settings.value("Reconstruction/Result Image Width (pixels)")
                        self.settings_hash['image_height'] = settings.value("Reconstruction/Result Image Height (pixels)")
                        self.settings_hash['file_type'] = settings.value("Reconstruction/Result File Type")
                        self.settings_hash['index_length'] = settings.value("File name convention/Filename Index Length")
                        self.settings_hash['seq_begin'] = settings.value("Reconstruction/First Section")
                        self.settings_hash['seq_end'] = settings.value("Reconstruction/Last Section")
                        self.settings_hash['image_width'] = int(self.settings_hash['image_width'])
                        self.settings_hash['image_height'] = int(self.settings_hash['image_height'])
                        self.settings_hash['index_length'] = int(self.settings_hash['index_length'])
                        self.settings_hash['seq_begin'] = int(self.settings_hash['seq_begin'])
                        self.settings_hash['seq_end'] = int(self.settings_hash['seq_end'])
                        self.edtNumImages.setText(str(self.settings_hash['seq_end'] - self.settings_hash['seq_begin'] + 1))
                        self.edtImageDimension.setText(str(self.settings_hash['image_width']) + " x " + str(self.settings_hash['image_height']))
                    except Exception as e:
                        logger.error(f"Error reading log file {file}: {e}")
                        continue

            #logger.info(f"Log files found: {log_files_found}")
            
            if 'prefix' not in self.settings_hash:
                #logger.info("No valid log file found, trying to detect image sequence...")
                self.settings_hash = self.sort_file_list_from_dir(ddir)
                if self.settings_hash is None:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(self, self.tr("Warning"), self.tr("No valid image files found in the selected directory."))
                    logger.warning("No valid image files found")
                    return
                logger.info(f"Detected image sequence: prefix={self.settings_hash.get('prefix')}, range={self.settings_hash.get('seq_begin')}-{self.settings_hash.get('seq_end')}")

            for seq in range(self.settings_hash['seq_begin'], self.settings_hash['seq_end']+1):
                filename = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                image_file_list.append(filename)
            
            #logger.info(f"Created image list with {len(image_file_list)} files")
            #logger.info(f"First image: {image_file_list[0] if image_file_list else 'None'}")
            
            self.original_from_idx = 0
            self.original_to_idx = len(image_file_list) - 1
            
            # Try to load the first image
            if image_file_list:
                first_image_path = os.path.join(ddir, image_file_list[0])
                #logger.info(f"Trying to load first image: {first_image_path}")
                
                # Check if file exists (case-insensitive on Windows)
                actual_path = None
                if os.path.exists(first_image_path):
                    actual_path = first_image_path
                else:
                    # Try with lowercase extension
                    base, ext = os.path.splitext(first_image_path)
                    alt_path = base + ext.lower()
                    if os.path.exists(alt_path):
                        actual_path = alt_path
                        #logger.info(f"Found file with lowercase extension: {alt_path}")
                
                if actual_path:
                    #logger.info(f"Image file exists: {actual_path}")
                    try:
                        pixmap = QPixmap(actual_path)
                        if pixmap.isNull():
                            logger.error(f"QPixmap is null for {actual_path}")
                        else:
                            #logger.info(f"Successfully loaded pixmap, size: {pixmap.width()}x{pixmap.height()}")
                            self.image_label.setPixmap(pixmap.scaledToWidth(512))
                    except Exception as e:
                        logger.error(f"Error loading initial image: {e}")
                else:
                    logger.error(f"Image file does not exist: {first_image_path} (also tried lowercase extension)")
            self.level_info = []
            self.level_info.append( {'name': 'Original', 'width': self.settings_hash['image_width'], 'height': self.settings_hash['image_height'], 'seq_begin': self.settings_hash['seq_begin'], 'seq_end': self.settings_hash['seq_end']} )
            
            # Check for existing thumbnail directories and populate level_info
            thumbnail_base = os.path.join(self.edtDirname.text(), ".thumbnail")
            if os.path.exists(thumbnail_base):
                logger.info(f"Found existing thumbnail directory: {thumbnail_base}")
                level_idx = 1
                while True:
                    level_dir = os.path.join(thumbnail_base, str(level_idx))
                    if not os.path.exists(level_dir):
                        break
                    
                    # Get first image from this level to determine dimensions
                    try:
                        files = sorted([f for f in os.listdir(level_dir) if f.endswith(('.' + self.settings_hash['file_type']))])
                        if files:
                            first_img_path = os.path.join(level_dir, files[0])
                            img = Image.open(first_img_path)
                            width, height = img.size
                            img.close()
                            
                            # Calculate sequence range for this level
                            seq_begin = self.settings_hash['seq_begin']
                            seq_end = seq_begin + len(files) - 1
                            
                            self.level_info.append({
                                'name': f"Level {level_idx}",
                                'width': width,
                                'height': height,
                                'seq_begin': seq_begin,
                                'seq_end': seq_end
                            })
                            #logger.info(f"Added level {level_idx}: {width}x{height}, {len(files)} images")
                    except Exception as e:
                        logger.error(f"Error reading thumbnail level {level_idx}: {e}")
                        break
                    
                    level_idx += 1
            
            QApplication.restoreOverrideCursor()
            logger.info(f"Successfully loaded directory with {len(image_file_list)} images")
            #logger.info(f"Level info count: {len(self.level_info)}")
            #logger.info("Calling create_thumbnail...")
            self.create_thumbnail()
            #logger.info(f"After create_thumbnail, minimum_volume type: {type(self.minimum_volume) if hasattr(self, 'minimum_volume') else 'not set'}")
            if hasattr(self, 'minimum_volume'):
                if isinstance(self.minimum_volume, list):
                    pass
                    #logger.info(f"minimum_volume is list with length: {len(self.minimum_volume)}")
                elif isinstance(self.minimum_volume, np.ndarray):
                    pass  #logger.info(f"minimum_volume is numpy array with shape: {self.minimum_volume.shape}")

    def read_settings(self):
            """
            Reads the application settings and updates the corresponding values in the application object.
            """
            try:
                settings = self.m_app.settings

                self.m_app.remember_directory = value_to_bool(settings.value("Remember directory", True))
                if self.m_app.remember_directory:
                    self.m_app.default_directory = settings.value("Default directory", ".")
                else:
                    self.m_app.default_directory = "."

                self.m_app.remember_geometry = value_to_bool(settings.value("Remember geometry", True))
                if self.m_app.remember_geometry:
                    self.setGeometry(settings.value("MainWindow geometry", QRect(100, 100, 600, 550)))
                    self.mcube_geometry = settings.value("mcube_widget geometry", QRect(0, 0, 150, 150))
                else:
                    self.setGeometry(QRect(100, 100, 600, 550))
                    self.mcube_geometry = QRect(0, 0, 150, 150)
                self.m_app.language = settings.value("Language", "en")

                # Read Rust module preference
                use_rust_default = value_to_bool(settings.value("Use Rust Module", True))
                if hasattr(self, 'cbxUseRust'):
                    self.cbxUseRust.setChecked(use_rust_default)

            except Exception as e:
                logger.error(f"Error reading main window settings: {e}")
                # Set defaults if reading fails
                self.m_app.remember_directory = True
                self.m_app.default_directory = "."
                self.m_app.remember_geometry = True
                self.setGeometry(QRect(100, 100, 600, 550))
                self.mcube_geometry = QRect(0, 0, 150, 150)
                self.m_app.language = "en"
                if hasattr(self, 'cbxUseRust'):
                    self.cbxUseRust.setChecked(True)

    def save_settings(self):
            """
            Saves the current application settings to persistent storage.
            If the 'remember_directory' setting is enabled, saves the default directory.
            If the 'remember_geometry' setting is enabled, saves the main window and mcube widget geometries.
            """
            try:
                if self.m_app.remember_directory:
                    self.m_app.settings.setValue("Default directory", self.m_app.default_directory)
                if self.m_app.remember_geometry:
                    self.m_app.settings.setValue("MainWindow geometry", self.geometry())
                    self.m_app.settings.setValue("mcube_widget geometry", self.mcube_widget.geometry())

                # Save Rust module preference
                if hasattr(self, 'cbxUseRust'):
                    self.m_app.settings.setValue("Use Rust Module", self.cbxUseRust.isChecked())

            except Exception as e:
                logger.error(f"Error saving main window settings: {e}")

    def closeEvent(self, event):
        """
        This method is called when the user closes the application window.
        It saves the current settings and accepts the close event.
        """
        logger.info("Application closing")
        self.save_settings()
        event.accept()
        

if __name__ == "__main__":
    #logger.info(f"Starting {PROGRAM_NAME} v{PROGRAM_VERSION}")
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
    app.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,COMPANY_NAME, PROGRAM_NAME)

    translator = QTranslator(app)
    app.language = app.settings.value("Language", "en")
    translator.load(resource_path("CTHarvester_{}.qm".format(app.language)))
    app.installTranslator(translator)

    # Create instance of CTHarvesterMainWindow
    myWindow = CTHarvesterMainWindow()

    # Show the main window
    myWindow.show()
    #logger.info(f"{PROGRAM_NAME} main window displayed")

    # Enter the event loop (start the application)
    app.exec_()
    #logger.info(f"{PROGRAM_NAME} terminated")

'''
pyinstaller --onefile --noconsole --add-data "*.png;." --add-data "*.qm;." --icon="CTHarvester_48_2.png" CTHarvester.py
pyinstaller --onedir --noconsole --icon="CTHarvester_64.png" --noconfirm CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
linguist

'''
