"""Progress tracking and multi-stage sampling for thumbnail generation.

This module was extracted from ThumbnailManager during Phase 3 architectural refactoring
to reduce complexity and improve maintainability. It handles all aspects of progress tracking,
ETA calculation, and the three-stage performance sampling strategy.

Typical usage:

    tracker = ThumbnailProgressTracker(
        sample_size=5,
        level_weight=1.0,
        time_estimator=TimeEstimator()
    )

    tracker.start_sampling(level=0, total_tasks=757)

    # After each task completion:
    tracker.on_task_completed(
        completed_count=1,
        total_tasks=757,
        was_generated=True
    )

    # Check sampling stages:
    if tracker.should_log_stage():
        info = tracker.get_stage_info(total_levels=3)
        print(info['message'])
"""

import logging
import time
from typing import Any, Dict, Optional

from utils.time_estimator import TimeEstimator

logger = logging.getLogger(__name__)


class ThumbnailProgressTracker:
    """Tracks progress and performs multi-stage sampling for thumbnail generation.

    This class manages progress tracking, ETA calculation, and performance sampling
    during thumbnail generation. It implements a three-stage sampling strategy that
    provides increasingly accurate time estimates as processing continues.

    The three-stage sampling approach handles variable I/O performance (SSD vs HDD)
    by taking measurements at different points:
    - Stage 1: After sample_size images (initial estimate)
    - Stage 2: After 2×sample_size images (refined estimate)
    - Stage 3: After 3×sample_size images (final estimate with trend analysis)

    Attributes:
        sample_size: Number of images to sample at each stage
        level_weight: Weight factor for current level (affects progress calculation)
        time_estimator: TimeEstimator instance for ETA calculations
        is_sampling: Whether currently performing performance sampling
        sample_start_time: Timestamp when sampling started
        images_per_second: Measured processing speed (weighted units per second)
        completed_tasks: Number of tasks completed so far
        generated_count: Number of thumbnails actually generated (not loaded)
        loaded_count: Number of thumbnails loaded from existing files
        stage1_estimate: Total time estimate from stage 1 (seconds)
        stage1_speed: Processing speed from stage 1 (seconds per image)
        stage2_estimate: Total time estimate from stage 2 (seconds)
        current_level: Level being processed (0 = from originals, 1+ = from thumbnails)

    Example:
        >>> tracker = ThumbnailProgressTracker(sample_size=5, level_weight=1.0)
        >>> tracker.start_sampling(level=0, total_tasks=757)
        >>> for i in range(757):
        ...     tracker.on_task_completed(i+1, 757, was_generated=True)
        ...     if tracker.should_log_stage():
        ...         info = tracker.get_stage_info(total_levels=3)
        ...         print(info['message'])
    """

    def __init__(
        self,
        sample_size: int,
        level_weight: float = 1.0,
        time_estimator: Optional[TimeEstimator] = None,
        initial_speed: Optional[float] = None,
    ):
        """Initialize progress tracker.

        Args:
            sample_size: Number of images to sample per stage (e.g., 5)
            level_weight: Weight factor for this level (default: 1.0)
            time_estimator: TimeEstimator instance (creates new if None)
            initial_speed: Initial processing speed from previous level (weighted units/sec)
        """
        self.sample_size = sample_size
        self.level_weight = level_weight
        self.time_estimator = time_estimator or TimeEstimator()

        # Sampling state
        self.is_sampling = False
        self.sample_start_time: Optional[float] = None
        self.images_per_second: Optional[float] = initial_speed

        # Progress tracking
        self.completed_tasks = 0
        self.generated_count = 0
        self.loaded_count = 0

        # Multi-stage sampling data
        self.stage1_estimate: Optional[float] = None
        self.stage1_speed: Optional[float] = None
        self.stage2_estimate: Optional[float] = None

        # Current processing level
        self.current_level = 0

        speed_str = f"{initial_speed:.1f}" if initial_speed is not None else "None"
        logger.debug(
            f"ThumbnailProgressTracker created: sample_size={sample_size}, "
            f"level_weight={level_weight:.4f}, "
            f"initial_speed={speed_str}"
        )

    def start_sampling(self, level: int, total_tasks: int) -> None:
        """Start performance sampling for a level.

        Args:
            level: Level index (0 = from originals, 1+ = from previous thumbnails)
            total_tasks: Total number of tasks to process
        """
        self.current_level = level
        self.completed_tasks = 0
        self.generated_count = 0
        self.loaded_count = 0

        # Only enable sampling for level 0 (first level)
        if level == 0 and self.sample_size > 0:
            self.is_sampling = True
            self.sample_start_time = time.time()
            logger.info(
                f"Level {level+1}: Starting performance sampling "
                f"(first {self.sample_size * 3} images in 3 stages)"
            )
        else:
            self.is_sampling = False
            logger.info(
                f"Level {level+1}: No sampling "
                f"(level={level}, need 0; sample_size={self.sample_size}, need >0)"
            )

    def on_task_completed(
        self, completed_count: int, total_tasks: int, was_generated: bool
    ) -> None:
        """Record task completion and update counters.

        Args:
            completed_count: Total number of completed tasks
            total_tasks: Total number of tasks to process
            was_generated: Whether thumbnail was newly generated (True) or loaded (False)
        """
        self.completed_tasks = completed_count

        if was_generated:
            self.generated_count += 1
        else:
            self.loaded_count += 1

        # Validate bounds
        if self.completed_tasks > total_tasks:
            logger.error(
                f"completed_tasks ({self.completed_tasks}) > total_tasks ({total_tasks}), "
                f"capping to total"
            )
            self.completed_tasks = total_tasks

    def should_log_stage(self) -> bool:
        """Check if we should log a sampling stage.

        Returns:
            True if current completion matches a stage threshold
        """
        if not self.is_sampling or self.current_level != 0:
            return False

        # Check if we've hit a stage threshold
        return self.completed_tasks in [
            self.sample_size,  # Stage 1
            self.sample_size * 2,  # Stage 2
            self.sample_size * 3,  # Stage 3
        ]

    def get_current_stage(self) -> Optional[int]:
        """Get the current sampling stage number.

        Returns:
            Stage number (1, 2, or 3), or None if not at a stage threshold
        """
        if not self.should_log_stage():
            return None

        if self.completed_tasks == self.sample_size:
            return 1
        elif self.completed_tasks == self.sample_size * 2:
            return 2
        elif self.completed_tasks >= self.sample_size * 3:
            return 3

        return None

    def get_stage_info(self, total_tasks: int, total_levels: int = 1) -> Dict[str, Any]:
        """Get detailed information for current sampling stage.

        Args:
            total_tasks: Total number of tasks to process
            total_levels: Total number of pyramid levels

        Returns:
            Dictionary containing:
            - stage: Stage number (1, 2, or 3)
            - elapsed: Elapsed time since sampling started (seconds)
            - time_per_image: Time per image (seconds)
            - total_estimate: Total estimated time (seconds)
            - total_estimate_formatted: Human-readable total time
            - message: Log message summarizing this stage
            - weighted_speed: Processing speed (weighted units per second)
            - should_stop_sampling: Whether to stop sampling after this stage
        """
        stage = self.get_current_stage()
        if stage is None:
            raise ValueError("Not at a sampling stage threshold")

        if self.sample_start_time is None:
            raise ValueError("Sampling not started")

        elapsed = time.time() - self.sample_start_time
        sample_count = self.sample_size * stage

        # Use TimeEstimator for calculations
        estimate_info = self.time_estimator.format_stage_estimate(
            stage=stage,
            elapsed=elapsed,
            sample_size=sample_count,
            total_items=total_tasks,
            num_levels=total_levels,
        )

        # Calculate weighted speed (units per second)
        weighted_speed = (sample_count * self.level_weight) / elapsed if elapsed > 0 else 1.0

        # Build result
        result = {
            "stage": stage,
            "elapsed": elapsed,
            "time_per_image": estimate_info["time_per_image"],
            "total_estimate": estimate_info["total_estimate"],
            "total_estimate_formatted": estimate_info["total_estimate_formatted"],
            "weighted_speed": weighted_speed,
            "should_stop_sampling": False,
        }

        # Build log message
        if stage == 1:
            message = (
                f"=== Stage 1 Sampling ({sample_count} images in {elapsed:.2f}s) ===\n"
                f"Speed: {estimate_info['time_per_image']:.3f}s per image\n"
                f"Initial estimate: {estimate_info['total_estimate_formatted']} "
                f"({estimate_info['total_estimate']:.1f}s)"
            )
            # Store stage 1 data for comparison
            self.stage1_estimate = estimate_info["total_estimate"]
            self.stage1_speed = estimate_info["time_per_image"]

        elif stage == 2:
            message = (
                f"=== Stage 2 Sampling ({sample_count} images in {elapsed:.2f}s) ===\n"
                f"Speed: {estimate_info['time_per_image']:.3f}s per image\n"
                f"Revised estimate: {estimate_info['total_estimate_formatted']} "
                f"({estimate_info['total_estimate']:.1f}s)"
            )

            # Compare with stage 1
            if self.stage1_estimate is not None and self.stage1_speed is not None:
                diff_percent = (
                    (estimate_info["total_estimate"] - self.stage1_estimate) / self.stage1_estimate
                ) * 100
                speed_change = (
                    (estimate_info["time_per_image"] - self.stage1_speed) / self.stage1_speed
                ) * 100
                message += f"\nDifference from stage 1: {diff_percent:+.1f}%"
                message += f"\nSpeed change: {speed_change:+.1f}%"

            # Store stage 2 data
            self.stage2_estimate = estimate_info["total_estimate"]

        else:  # stage == 3
            # Calculate weighted units per second for final speed
            weighted_units_completed = sample_count * self.level_weight
            self.images_per_second = weighted_units_completed / elapsed if elapsed > 0 else 20
            result["weighted_speed"] = self.images_per_second

            total_estimate = estimate_info["total_estimate"]

            # Apply trend adjustment if estimates are increasing
            if (
                self.stage1_estimate is not None
                and self.stage2_estimate is not None
                and total_estimate > self.stage1_estimate * 1.5
            ):
                trend_factor = total_estimate / self.stage1_estimate
                adjusted_estimate = total_estimate * (1 + (trend_factor - 1) * 0.3)
                logger.info(
                    f"Trend adjustment: {total_estimate:.1f}s -> {adjusted_estimate:.1f}s "
                    f"(trend_factor={trend_factor:.2f})"
                )
                total_estimate = adjusted_estimate
                result["total_estimate"] = total_estimate

            # Determine storage type based on speed
            storage_type = self._estimate_storage_type(self.images_per_second)

            message = (
                f"=== Stage 3 Sampling ({sample_count} images in {elapsed:.2f}s) ===\n"
                f"Speed: {estimate_info['time_per_image']:.3f}s per image\n"
                f"Performance sampling complete: {self.images_per_second:.1f} weighted units/second\n"
                f"Estimated storage type: {storage_type}"
            )

            # Show estimate progression
            if self.stage1_estimate is not None and self.stage2_estimate is not None:
                message += (
                    f"\nEstimate progression: "
                    f"Stage1={self.stage1_estimate:.1f}s -> "
                    f"Stage2={self.stage2_estimate:.1f}s -> "
                    f"Stage3={total_estimate:.1f}s"
                )

            # Format final estimate
            formatted_final = self._format_final_estimate(total_estimate)
            message += f"\n=== FINAL ESTIMATED TOTAL TIME: {formatted_final} ==="
            result["final_estimate_formatted"] = formatted_final

            # Mark sampling as complete
            result["should_stop_sampling"] = True

        result["message"] = message
        return result

    def finalize_sampling(self) -> None:
        """Mark sampling as complete."""
        self.is_sampling = False
        logger.info("Multi-stage sampling completed")

    def get_performance_data(self) -> Dict[str, Any]:
        """Get performance data to pass to parent or next level.

        Returns:
            Dictionary with keys:
            - images_per_second: Processing speed (weighted units/sec)
            - time_per_image: Time per image (seconds)
            - total_estimate: Final total time estimate (seconds)
            - total_estimate_formatted: Human-readable total time
            - generation_ratio: Percentage of thumbnails generated vs loaded
        """
        generation_ratio = (
            (self.generated_count / self.completed_tasks * 100) if self.completed_tasks > 0 else 0.0
        )

        time_per_image = (
            1.0 / self.images_per_second
            if self.images_per_second and self.images_per_second > 0
            else 0.05
        )

        return {
            "images_per_second": self.images_per_second,
            "time_per_image": time_per_image,
            "total_estimate": self.stage2_estimate or self.stage1_estimate,
            "generation_ratio": generation_ratio,
            "generated_count": self.generated_count,
            "loaded_count": self.loaded_count,
        }

    def _estimate_storage_type(self, speed: Optional[float]) -> str:
        """Estimate storage type based on processing speed.

        Args:
            speed: Processing speed (weighted units per second)

        Returns:
            Storage type string: "SSD", "HDD", or "Network/Slow"
        """
        if speed is None:
            return "Unknown"
        elif speed > 10:
            return "SSD"
        elif speed > 2:
            return "HDD"
        else:
            return "Network/Slow"

    def _format_final_estimate(self, seconds: float) -> str:
        """Format final time estimate in human-readable form.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted string (e.g., "45s", "5m 30s", "2h 15m")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
