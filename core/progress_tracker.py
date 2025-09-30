"""Simple progress tracking module.

This module provides straightforward linear progress tracking with ETA (Estimated Time of Arrival)
calculation using moving averages for smooth and predictable progress updates.

The module was extracted during Phase 1.1 UI/UX improvements to simplify the complex 3-stage
sampling progress calculation previously used.

Typical usage example:

    def progress_callback(info: ProgressInfo):
        print(f"Progress: {info.percentage:.1f}% - ETA: {info.eta_formatted}")

    tracker = SimpleProgressTracker(total_items=100, callback=progress_callback)
    for i in range(100):
        # Do some work
        tracker.update()  # Update progress by 1
"""
from typing import Optional, Callable
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProgressInfo:
    """Progress information container.

    This dataclass holds all information about current progress state, including
    completion metrics, timing estimates, and processing speed.

    Attributes:
        current: Number of items completed so far.
        total: Total number of items to process.
        percentage: Completion percentage (0-100).
        eta_seconds: Estimated time to completion in seconds, or None if not yet calculated.
        elapsed_seconds: Time elapsed since start in seconds.
        speed: Processing speed in items per second.
    """
    current: int
    total: int
    percentage: float
    eta_seconds: Optional[float]
    elapsed_seconds: float
    speed: float  # items per second

    @property
    def eta_formatted(self) -> str:
        """Format ETA in human-readable form.

        Returns:
            A formatted string like "5s", "2m 30s", or "1h 15m". Returns "Calculating..."
            if ETA is not yet available.
        """
        if self.eta_seconds is None:
            return "Calculating..."

        if self.eta_seconds < 60:
            return f"{int(self.eta_seconds)}s"
        elif self.eta_seconds < 3600:
            minutes = int(self.eta_seconds / 60)
            seconds = int(self.eta_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.eta_seconds / 3600)
            minutes = int((self.eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    @property
    def elapsed_formatted(self) -> str:
        """Format elapsed time in human-readable form.

        Returns:
            A formatted string like "5s", "2m 30s", or "1h 15m".
        """
        if self.elapsed_seconds < 60:
            return f"{int(self.elapsed_seconds)}s"
        elif self.elapsed_seconds < 3600:
            minutes = int(self.elapsed_seconds / 60)
            seconds = int(self.elapsed_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.elapsed_seconds / 3600)
            minutes = int((self.elapsed_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class SimpleProgressTracker:
    """Simple and predictable progress tracking.

    This class provides linear progress tracking (0-100%) with moving average based ETA
    calculation. It's designed to provide smooth and predictable progress updates without
    complex multi-stage sampling.

    The tracker uses a moving average window to smooth out speed fluctuations and provide
    more stable ETA predictions. ETA calculation begins only after collecting minimum
    required samples to avoid wild initial estimates.

    Attributes:
        total_items: Total number of items to process.
        callback: Optional callback function invoked on each update.
        smoothing_window: Size of moving average window for speed calculation.
        min_samples_for_eta: Minimum speed samples needed before calculating ETA.
        completed_items: Number of items completed so far.
        start_time: Unix timestamp when tracking started.
        last_update_time: Unix timestamp of last update.
        speed_samples: List of recent speed samples for moving average.

    Example:
        >>> def on_progress(info: ProgressInfo):
        ...     print(f"{info.percentage:.1f}% - ETA: {info.eta_formatted}")
        >>> tracker = SimpleProgressTracker(100, callback=on_progress)
        >>> for i in range(100):
        ...     time.sleep(0.1)  # Simulate work
        ...     tracker.update()
    """

    def __init__(
        self,
        total_items: int,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        smoothing_window: int = 10,
        min_samples_for_eta: int = 5
    ):
        """Initialize the progress tracker.

        Args:
            total_items: Total number of items to process. Must be > 0.
            callback: Optional callback function that receives ProgressInfo on each update.
            smoothing_window: Size of moving average window (default: 10). Larger values
                provide more stable but less responsive ETA updates.
            min_samples_for_eta: Minimum speed samples needed before calculating ETA
                (default: 5). Prevents unreliable initial estimates.

        Raises:
            ValueError: If total_items <= 0.
        """
        self.total_items = total_items
        self.callback = callback
        self.smoothing_window = smoothing_window
        self.min_samples_for_eta = min_samples_for_eta

        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # Speed tracking (for moving average)
        self.speed_samples = []

    def update(self, increment: int = 1):
        """Update progress by specified number of items.

        This method should be called each time work is completed. It updates internal
        counters, recalculates speed and ETA, and invokes the callback if provided.

        Args:
            increment: Number of items completed in this update (default: 1). Must be > 0.

        Raises:
            ValueError: If increment <= 0 or would cause completed_items to exceed total_items.

        Note:
            The callback is invoked synchronously, so long-running callbacks will delay
            the update operation.
        """
        self.completed_items += increment

        # Current time
        now = time.time()
        elapsed = now - self.start_time

        # Calculate speed (items/sec)
        if elapsed > 0:
            current_speed = self.completed_items / elapsed

            # Add to moving average
            self.speed_samples.append(current_speed)
            if len(self.speed_samples) > self.smoothing_window:
                self.speed_samples.pop(0)

            # Average speed
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
        else:
            avg_speed = 0

        # Percentage
        percentage = (self.completed_items / self.total_items) * 100

        # Calculate ETA
        remaining_items = self.total_items - self.completed_items
        if avg_speed > 0 and len(self.speed_samples) >= self.min_samples_for_eta:
            eta_seconds = remaining_items / avg_speed
        else:
            eta_seconds = None

        # Create ProgressInfo
        info = ProgressInfo(
            current=self.completed_items,
            total=self.total_items,
            percentage=percentage,
            eta_seconds=eta_seconds,
            elapsed_seconds=elapsed,
            speed=avg_speed
        )

        # Invoke callback
        if self.callback:
            self.callback(info)

        self.last_update_time = now

    def reset(self):
        """Reset progress tracking to initial state.

        Resets all counters and timing information, allowing the tracker to be reused
        for a new operation without creating a new instance.
        """
        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.speed_samples = []

    def get_info(self) -> ProgressInfo:
        """Get current progress information without updating.

        Returns:
            ProgressInfo: Current progress state including completion percentage, ETA,
                elapsed time, and processing speed.

        Note:
            Unlike update(), this method does not modify state or invoke callbacks.
            It's useful for querying current status without affecting progress tracking.
        """
        elapsed = time.time() - self.start_time
        percentage = (self.completed_items / self.total_items) * 100

        if self.speed_samples:
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
            remaining_items = self.total_items - self.completed_items
            eta_seconds = remaining_items / avg_speed if avg_speed > 0 else None
        else:
            avg_speed = 0
            eta_seconds = None

        return ProgressInfo(
            current=self.completed_items,
            total=self.total_items,
            percentage=percentage,
            eta_seconds=eta_seconds,
            elapsed_seconds=elapsed,
            speed=avg_speed
        )