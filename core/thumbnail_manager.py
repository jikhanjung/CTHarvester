"""
ThumbnailManager - Thumbnail generation management with progress tracking

Extracted from CTHarvester.py during Phase 4c refactoring.
"""
import os
import time
import logging
from PyQt5.QtCore import QObject, QMutex, QMutexLocker, pyqtSlot, QThreadPool
from PyQt5.QtWidgets import QApplication

from core.thumbnail_worker import ThumbnailWorker, ThumbnailWorkerSignals
from core.progress_manager import ProgressManager


logger = logging.getLogger(__name__)


class ThumbnailManager(QObject):
    """Manager class to coordinate multiple thumbnail workers and progress tracking"""

    def __init__(self, parent, progress_dialog, threadpool, shared_progress_manager=None):
        super().__init__()
        self.parent = parent
        self.progress_dialog = progress_dialog
        self.threadpool = threadpool

        # Use shared progress manager if provided, otherwise create a new one
        if shared_progress_manager:
            self.progress_manager = shared_progress_manager
        else:
            # Create new progress manager as fallback
            self.progress_manager = ProgressManager()
            # Pass weighted work distribution if available
            if hasattr(parent, 'level_work_distribution'):
                self.progress_manager.level_work_distribution = parent.level_work_distribution
            if hasattr(parent, 'weighted_total_work'):
                self.progress_manager.weighted_total_work = parent.weighted_total_work

        # Connect progress manager signals to UI
        if progress_dialog:
            self.progress_manager.progress_updated.connect(
                lambda p: progress_dialog.pb_progress.setValue(p)
            )
            self.progress_manager.eta_updated.connect(
                lambda eta: self._update_progress_text(eta)
            )

        # Progress tracking (legacy compatibility)
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
            logger = logging.getLogger('CTHarvester')
            logger.info(f"ThumbnailManager created: sample_size={self.sample_size}, inherited speed={self.images_per_second:.1f} img/s")
        else:
            import logging
            logger = logging.getLogger('CTHarvester')
            logger.info(f"ThumbnailManager created: sample_size={self.sample_size}, no inherited speed")

    def _update_progress_text(self, eta_text):
        """Helper to update progress dialog text"""
        if self.progress_dialog and hasattr(self.progress_dialog, 'lbl_detail'):
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
        """
        Python 폴백에서 단일 스레드를 사용하는 이유

        [배경]
        Python 구현은 Rust 모듈의 백업입니다.
        - 주력: Rust 모듈 (2-3분, 진정한 멀티스레드)
        - 보조: Python 폴백 (Rust 설치 실패 시)

        [멀티스레드 문제]
        평균적으로는 더 빠르지만, 예측 불가능한 병목이 발생:
        - 대부분 이미지: 100-200ms (정상)
        - 일부 이미지: 10-20초 (락 경합, PIL 내부 문제)
        - 원인: GIL 경합, 디스크 I/O 경합, PIL/NumPy 내부 락

        [단일 스레드 선택 이유]
        1. 예측 가능성: 모든 이미지가 일정한 속도 (180-200ms)
        2. 안정성: 간헐적 멈춤 현상 없음
        3. 디버깅 용이성: 문제 추적 쉬움
        4. 코드 단순성: 백업 구현은 단순함 우선
        5. 사용자 경험: 느리지만 일정 > 빠르지만 가끔 멈춤

        [성능 비교]
        - 단일 스레드: 안정적으로 9-10분
        - 멀티 스레드: 평균 6-7분, 최악 30-40분 (일부 이미지에서)

        백업 구현의 목표는 "최고 성능"이 아니라 "안정적 작동"입니다.

        Returns:
            int: 1 (단일 스레드, 안정성과 예측 가능성 우선)
        """
        import logging
        logger = logging.getLogger('CTHarvester')

        logger.info(
            "Python fallback: Using single thread for stability "
            "(Rust module is the primary high-performance solution)"
        )

        return 1

    def update_eta_and_progress(self):
        """Delegate to centralized progress manager"""
        # Update progress manager state
        if self.is_sampling != self.progress_manager.is_sampling:
            self.progress_manager.set_sampling(self.is_sampling)

        if self.images_per_second:
            self.progress_manager.set_speed(self.images_per_second)

        # Only initialize if not already started (for shared progress manager)
        if not self.progress_manager.total and not self.progress_manager.start_time:
            total_to_use = self.progress_manager.weighted_total_work if self.progress_manager.weighted_total_work else self.total_tasks
            self.progress_manager.start(total_to_use)

        self.progress_manager.update(value=self.global_step_counter)

    def process_level_sequential(self, level, from_dir, to_dir, seq_begin, seq_end, settings_hash, size, max_thumbnail_size, num_tasks):
        """Process thumbnails sequentially without threadpool - no threading issues"""
        import logging
        import time
        from PIL import Image
        import numpy as np
        import os

        logger = logging.getLogger('CTHarvester')
        logger.info("Starting sequential processing - no threads")

        seq_start_time = time.time()

        for idx in range(num_tasks):
            if self.progress_dialog.is_cancelled:
                self.is_cancelled = True
                break

            task_start_time = time.time()
            seq = seq_begin + (idx * 2)

            # Generate filenames (same logic as ThumbnailWorker)
            if level == 0:
                # Reading from original images
                filename1 = settings_hash['prefix'] + str(seq).zfill(settings_hash['index_length']) + "." + settings_hash['file_type']
                # Check if seq+1 exceeds seq_end
                if seq + 1 <= seq_end:
                    filename2 = settings_hash['prefix'] + str(seq+1).zfill(settings_hash['index_length']) + "." + settings_hash['file_type']
                else:
                    filename2 = None  # Odd number case
            else:
                # Reading from thumbnail directory - use simple numbering
                relative_seq = seq - seq_begin
                filename1 = "{:06}.tif".format(relative_seq)
                if seq + 1 <= seq_end:
                    filename2 = "{:06}.tif".format(relative_seq + 1)
                else:
                    filename2 = None  # Odd number case

            # Output always uses simple sequential numbering
            filename3 = os.path.join(to_dir, "{:06}.tif".format(idx))

            # Check if thumbnail exists
            img_array = None
            was_generated = False

            if os.path.exists(filename3):
                # Load existing
                if size < max_thumbnail_size:
                    try:
                        with Image.open(filename3) as img:
                            img_array = np.array(img)
                    except Exception as e:
                        logger.error(f"Error loading thumbnail {filename3}: {e}")
            else:
                # Generate new thumbnail
                was_generated = True
                file1_path = os.path.join(from_dir, filename1)
                if filename2:
                    file2_path = os.path.join(from_dir, filename2)
                else:
                    file2_path = None

                img1 = None
                img2 = None
                new_img = None

                try:
                    # Load images
                    if os.path.exists(file1_path):
                        try:
                            load1_start = time.time()
                            img1 = Image.open(file1_path)
                            load1_time = (time.time() - load1_start) * 1000
                            if load1_time > 1000:
                                logger.warning(f"SLOW load img1: {load1_time:.1f}ms")
                            if img1.mode == 'P':
                                img1 = img1.convert('L')
                        except Exception as e:
                            logger.error(f"Error loading {filename1}: {e}")

                    if file2_path and os.path.exists(file2_path):
                        try:
                            load2_start = time.time()
                            img2 = Image.open(file2_path)
                            load2_time = (time.time() - load2_start) * 1000
                            if load2_time > 1000:
                                logger.warning(f"SLOW load img2: {load2_time:.1f}ms")
                            if img2.mode == 'P':
                                img2 = img2.convert('L')
                        except Exception as e:
                            logger.error(f"Error loading {filename2}: {e}")

                    # Average and resize
                    if img1:  # Process even if img2 is None (odd number case)
                        try:
                            # Use numpy-based processing to preserve 16-bit depth
                            from utils.image_utils import average_images, downsample_image

                            arr1 = np.array(img1)

                            if img2:
                                # Both images exist - average them
                                arr2 = np.array(img2)
                                averaged = average_images(arr1, arr2)
                            else:
                                # Only img1 exists (odd case) - no averaging needed
                                logger.debug(f"Processing single image at idx={idx}")
                                averaged = arr1

                            # Downsample by factor of 2
                            downsampled = downsample_image(averaged, factor=2, method='average')

                            # Convert back to PIL Image and save
                            new_img = Image.fromarray(downsampled)
                            new_img.save(filename3)

                            if size < max_thumbnail_size:
                                img_array = downsampled
                        except Exception as e:
                            logger.error(f"Error creating thumbnail: {e}")
                finally:
                    # Ensure all image resources are released
                    if img1 is not None:
                        img1.close()
                    if img2 is not None:
                        img2.close()
                    if new_img is not None:
                        new_img.close()

            # Update progress
            self.completed_tasks += 1
            if was_generated:
                self.generated_count += 1
            else:
                self.loaded_count += 1

            # Update progress bar
            self.global_step_counter += self.level_weight
            self.progress_manager.update(value=self.global_step_counter)

            # Store result
            if img_array is not None:
                self.results[idx] = img_array

            # Performance logging
            task_time = (time.time() - task_start_time) * 1000
            if task_time > 5000:
                logger.warning(f"SLOW task {idx}: {task_time:.1f}ms")
            elif task_time > 3000:
                logger.info(f"Task {idx}: {task_time:.1f}ms")

            # Update ETA periodically
            if self.completed_tasks % 10 == 0 or self.completed_tasks <= 5:
                self.update_eta_and_progress()
                QApplication.processEvents()

            # Performance sampling (for first level)
            if self.is_sampling and self.completed_tasks >= self.sample_size:
                elapsed = time.time() - self.sample_start_time
                self.images_per_second = self.level_weight * self.sample_size / elapsed
                self.is_sampling = False
                logger.info(f"Sampling complete: {self.images_per_second:.2f} weighted units/s")
                # Store for parent
                if hasattr(self.parent, 'measured_images_per_second'):
                    self.parent.measured_images_per_second = self.images_per_second

        seq_total_time = time.time() - seq_start_time
        logger.info(f"Sequential processing complete: {self.completed_tasks} tasks in {seq_total_time:.1f}s")
        logger.info(f"Average: {seq_total_time/num_tasks*1000:.1f}ms per task")
        logger.info(f"Generated: {self.generated_count}, Loaded: {self.loaded_count}")

    def process_level(self, level, from_dir, to_dir, seq_begin, seq_end, settings_hash, size, max_thumbnail_size, global_step_offset):
        """Process a complete thumbnail level using multiple worker threads"""
        import logging
        import time
        logger = logging.getLogger('CTHarvester')

        level_start_time = time.time()
        logger.info(f"\n=== Starting Level {level+1} Processing ===")
        logger.info(f"From: {from_dir}")
        logger.info(f"To: {to_dir}")
        logger.info(f"Size: {size}x{size}")
        logger.info(f"Range: {seq_begin} to {seq_end}")

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
            logger.info(f"Level {level+1}: Starting with performance sampling (first {self.sample_size} images)")
        else:
            self.is_sampling = False
            # Not sampling, use any existing speed data
            self.progress_manager.set_sampling(False)
            logger.info(f"Not sampling: level={level} (need 0), sample_size={self.sample_size} (need >0)")

        logger.info(f"ThumbnailManager.process_level: Starting Level {level+1}, tasks={num_tasks}, offset={global_step_offset}")
        logger.debug(f"ThreadPool: maxThreadCount={self.threadpool.maxThreadCount()}, activeThreadCount={self.threadpool.activeThreadCount()}")
        
        # Determine optimal thread count
        # Balance between performance and stability
        optimal_threads = self._determine_optimal_thread_count()
        if self.threadpool.maxThreadCount() != optimal_threads:
            self.threadpool.setMaxThreadCount(optimal_threads)
            logger.info(f"Set thread pool to {optimal_threads} threads")

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
        submit_start = time.time()
        logger.info(f"Starting to submit {num_tasks} workers to thread pool")

        for idx in range(num_tasks):
            if self.progress_dialog.is_cancelled:
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
                idx, seq, seq_begin, from_dir, to_dir,
                settings_hash, size, max_thumbnail_size, self.progress_dialog, level, seq_end
            )
            if idx == 0 or idx % 100 == 0:
                logger.debug(f"Creating worker {idx}: seq={seq}, files={worker.filename1}, {worker.filename2}")
            
            # Connect signals with Qt.QueuedConnection to ensure thread safety
            worker.signals.progress.connect(self.on_worker_progress, Qt.QueuedConnection)
            worker.signals.result.connect(self.on_worker_result, Qt.QueuedConnection) 
            worker.signals.error.connect(self.on_worker_error, Qt.QueuedConnection)
            worker.signals.finished.connect(self.on_worker_finished, Qt.QueuedConnection)
            
            # Submit to thread pool
            if idx == 0:
                logger.info(f"Submitting first worker to threadpool")
                logger.info(f"Threadpool status before: active={self.threadpool.activeThreadCount()}, max={self.threadpool.maxThreadCount()}")

            self.threadpool.start(worker)
            workers_submitted += 1

            if idx == 0:
                logger.info(f"First worker submitted. Threadpool status after: active={self.threadpool.activeThreadCount()}")
            
            # Process events periodically to keep UI responsive
            if workers_submitted % 10 == 0 or workers_submitted <= 5:
                QApplication.processEvents()
                #logger.info(f"Submitted {workers_submitted}/{num_tasks} workers, active threads: {self.threadpool.activeThreadCount()}")
        
        submit_time = time.time() - submit_start
        logger.info(f"Submitted {workers_submitted} workers to threadpool in {submit_time*1000:.1f}ms")
        logger.info(f"Final threadpool status: active={self.threadpool.activeThreadCount()}, max={self.threadpool.maxThreadCount()}")
        logger.info(f"Waiting for workers to start processing...")

        # Wait for all workers to complete or cancellation
        import time
        start_wait = time.time()
        last_progress_log = time.time()
        last_detailed_log = time.time()
        stalled_count = 0
        last_completed_count = self.completed_tasks

        first_log = True
        while self.completed_tasks < self.total_tasks and not self.progress_dialog.is_cancelled:
            if first_log:
                logger.info(f"Starting main wait loop. Completed: {self.completed_tasks}, Total: {self.total_tasks}")
                first_log = False
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
        level_total_time = time.time() - level_start_time
        if not self.is_cancelled:
            avg_time_per_task = total_time / self.total_tasks if self.total_tasks > 0 else 0
            tasks_per_second = self.total_tasks / total_time if total_time > 0 else 0
            generation_ratio = self.generated_count / self.total_tasks * 100 if self.total_tasks > 0 else 0

            logger.info(f"\n=== Level {level+1} Complete ===")
            logger.info(f"Tasks completed: {self.completed_tasks}/{self.total_tasks}")
            logger.info(f"Generated: {self.generated_count}, Loaded: {self.loaded_count} ({generation_ratio:.1f}% generated)")
            logger.info(f"Images collected: {len(img_arrays)}")
            logger.info(f"Worker time: {total_time:.2f}s")
            logger.info(f"Total level time: {level_total_time:.2f}s (including submission)")
            logger.info(f"Average: {avg_time_per_task:.3f}s per task, {tasks_per_second:.1f} tasks/second")

            # Store generation ratio for coefficient calculation decision
            self.generation_ratio = generation_ratio

        return img_arrays, self.is_cancelled
    
    @pyqtSlot(int)
    def on_worker_progress(self, idx):
        """Handle progress updates from worker threads"""
        import logging
        logger = logging.getLogger('CTHarvester')

        with QMutexLocker(self.lock):
            # Increment by weight factor to account for different processing costs per level
            self.global_step_counter += self.level_weight
            current_step = self.global_step_counter

        # Update progress bar
        self.progress_dialog.lbl_text.setText(f"Generating thumbnails")
        # Update progress bar percentage using progress manager's data
        if self.progress_manager.total > 0:
            percentage = int((current_step / self.progress_manager.total) * 100)
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
        logger = logging.getLogger('CTHarvester')

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
            completed = self.completed_tasks
            total = self.total_tasks

            # Track generation vs loading
            if was_generated:
                self.generated_count += 1
            else:
                self.loaded_count += 1

            # Validate progress bounds (prevent overflow/underflow)
            if completed > total:
                logger.error(f"completed ({completed}) > total ({total}), capping to total")
                self.completed_tasks = total
                completed = total

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

                # Update ProgressManager with sampled speed - stop showing "Estimating..."
                weighted_speed = (self.sample_size * self.level_weight) / sample_elapsed if sample_elapsed > 0 else 1.0
                self.progress_manager.set_speed(weighted_speed)
                self.progress_manager.set_sampling(False)  # Show actual ETA now

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

                # Update ProgressManager with improved speed estimate
                weighted_speed = (self.sample_size * 2 * self.level_weight) / sample_elapsed if sample_elapsed > 0 else 1.0
                self.progress_manager.set_speed(weighted_speed)

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

                # Final update to ProgressManager with most accurate speed
                self.progress_manager.set_speed(self.images_per_second)

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
        logger = logging.getLogger('CTHarvester')
        exctype, value, traceback_str = error_tuple
        logger.error(f"Thumbnail worker error: {exctype.__name__}: {value}")
        logger.debug(f"Traceback: {traceback_str}")
    
    @pyqtSlot()
    def on_worker_finished(self):
        """Handle finished signal from worker threads"""
        # This is just a placeholder to properly handle the finished signal
        pass


# Define a custom OpenGL widget using QOpenGLWidget
