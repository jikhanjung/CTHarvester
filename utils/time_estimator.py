"""Time estimation and formatting utilities.

This module provides centralized time estimation and formatting functionality
to reduce code duplication in thumbnail generation and other long-running operations.

Created during Phase 2 of quality improvement plan (devlog 072).
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TimeEstimator:
    """Centralized time estimation and formatting for long-running operations.

    This class provides methods for:
    - Calculating ETA (Estimated Time of Arrival) for operations
    - Formatting durations in human-readable format
    - Estimating multi-level work (e.g., thumbnail pyramids)

    Example:
        >>> estimator = TimeEstimator()
        >>> time_per_item, eta = estimator.calculate_eta(30.0, 100, 1000)
        >>> print(estimator.format_duration(eta))
        '4m 30s'
    """

    # Default stage sample sizes for thumbnail generation
    DEFAULT_STAGE_SAMPLES = {1: 5, 2: 10, 3: 20}

    # Level reduction factor for LoD (Level of Detail) pyramids
    LEVEL_REDUCTION_FACTOR = 0.25

    def __init__(
        self,
        stage_samples: Optional[Dict[int, int]] = None,
        level_reduction_factor: float = 0.25,
    ):
        """Initialize TimeEstimator.

        Args:
            stage_samples: Dictionary mapping stage number to sample size.
                          Default: {1: 5, 2: 10, 3: 20}
            level_reduction_factor: Factor for estimating lower LoD levels.
                                   Default: 0.25 (each level takes 25% of previous)
        """
        self.stage_samples = stage_samples or self.DEFAULT_STAGE_SAMPLES.copy()
        self.level_reduction_factor = level_reduction_factor

    def calculate_eta(self, elapsed: float, completed: int, total: int) -> Tuple[float, float]:
        """Calculate ETA and time per item based on current progress.

        Args:
            elapsed: Elapsed time in seconds
            completed: Number of completed items
            total: Total number of items to process

        Returns:
            Tuple of (time_per_item, estimated_remaining_seconds)
            Returns (0.0, 0.0) if completed is 0

        Example:
            >>> estimator = TimeEstimator()
            >>> time_per, eta = estimator.calculate_eta(30.0, 100, 1000)
            >>> print(f"Time per item: {time_per:.2f}s, ETA: {eta:.0f}s")
            Time per item: 0.30s, ETA: 270s
        """
        if completed == 0:
            return 0.0, 0.0

        time_per_item = elapsed / completed
        remaining = total - completed
        eta = remaining * time_per_item

        return time_per_item, eta

    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string like "2.5s", "1m 30s", or "1h 15m"

        Example:
            >>> estimator = TimeEstimator()
            >>> estimator.format_duration(45.5)
            '45.5s'
            >>> estimator.format_duration(90)
            '1.5m'
            >>> estimator.format_duration(3661)
            '1h 1m'
        """
        if seconds < 0:
            return "0s"

        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours}h"

    def estimate_multi_level_work(self, base_time: float, num_levels: int = 3) -> Dict[int, float]:
        """Estimate time for multiple LoD (Level of Detail) levels.

        Each successive level is estimated to take level_reduction_factor
        of the previous level's time (default 25%).

        Args:
            base_time: Time estimate for level 1 (full resolution)
            num_levels: Number of levels to estimate (default: 3)

        Returns:
            Dictionary mapping level number to estimated time

        Example:
            >>> estimator = TimeEstimator()
            >>> estimates = estimator.estimate_multi_level_work(100.0, 3)
            >>> estimates
            {1: 100.0, 2: 25.0, 3: 6.25}
        """
        estimates = {1: base_time}

        for level in range(2, num_levels + 1):
            estimates[level] = estimates[level - 1] * self.level_reduction_factor

        return estimates

    def calculate_total_multi_level_time(self, base_time: float, num_levels: int = 3) -> float:
        """Calculate total time for all LoD levels.

        Args:
            base_time: Time estimate for level 1
            num_levels: Number of levels

        Returns:
            Total estimated time for all levels

        Example:
            >>> estimator = TimeEstimator()
            >>> total = estimator.calculate_total_multi_level_time(100.0, 3)
            >>> total
            131.25
        """
        estimates = self.estimate_multi_level_work(base_time, num_levels)
        return sum(estimates.values())

    def format_stage_estimate(
        self,
        stage: int,
        elapsed: float,
        sample_size: int,
        total_items: int,
        num_levels: int = 3,
    ) -> Dict[str, Any]:
        """Format a complete stage estimate with all levels.

        This is a convenience method that combines ETA calculation,
        multi-level estimation, and formatting.

        Args:
            stage: Stage number (1, 2, or 3)
            elapsed: Elapsed time for sampling
            sample_size: Number of items in sample
            total_items: Total number of items to process
            num_levels: Number of LoD levels

        Returns:
            Dictionary containing:
                - time_per_image: Time per item
                - level_estimates: Dict mapping level to time estimate
                - level_estimates_formatted: Dict mapping level to formatted string
                - total_estimate: Total time for all levels
                - total_estimate_formatted: Formatted total time

        Example:
            >>> estimator = TimeEstimator()
            >>> result = estimator.format_stage_estimate(1, 5.0, 5, 100, 3)
            >>> result['total_estimate_formatted']
            '2m 11s'
        """
        # Calculate base time per image
        time_per_image = elapsed / sample_size if sample_size > 0 else 0.05

        # Calculate level 1 total time
        level1_time = total_items * time_per_image

        # Estimate all levels
        level_estimates = self.estimate_multi_level_work(level1_time, num_levels)

        # Format all level estimates
        level_estimates_formatted = {
            level: self.format_duration(time) for level, time in level_estimates.items()
        }

        # Calculate and format total
        total_estimate = sum(level_estimates.values())
        total_estimate_formatted = self.format_duration(total_estimate)

        return {
            "time_per_image": time_per_image,
            "level_estimates": level_estimates,
            "level_estimates_formatted": level_estimates_formatted,
            "total_estimate": total_estimate,
            "total_estimate_formatted": total_estimate_formatted,
        }

    def format_progress_message(
        self,
        stage: int,
        completed: int,
        total: int,
        estimate_info: Dict[str, Any],
    ) -> str:
        """Format a progress message for display.

        Args:
            stage: Stage number
            completed: Number of completed items
            total: Total items
            estimate_info: Dictionary from format_stage_estimate()

        Returns:
            Formatted progress message

        Example:
            >>> estimator = TimeEstimator()
            >>> estimate = estimator.format_stage_estimate(1, 5.0, 5, 100, 3)
            >>> msg = estimator.format_progress_message(1, 5, 100, estimate)
            >>> print(msg)
            Stage 1: 5/100 complete. Est: 2m 11s total
        """
        total_formatted = estimate_info["total_estimate_formatted"]
        return f"Stage {stage}: {completed}/{total} complete. Est: {total_formatted} total"
