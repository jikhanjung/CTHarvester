"""
Simple progress tracking module

Provides straightforward linear progress tracking with ETA calculation.
Extracted during Phase 1.1 UI/UX improvements.
"""
from typing import Optional, Callable
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProgressInfo:
    """Progress information"""
    current: int
    total: int
    percentage: float
    eta_seconds: Optional[float]
    elapsed_seconds: float
    speed: float  # items per second

    @property
    def eta_formatted(self) -> str:
        """Format ETA in human-readable form"""
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
        """Format elapsed time in human-readable form"""
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
    """
    Simple and predictable progress tracking

    Features:
    - Linear progress (0-100%)
    - Moving average based ETA
    - Smooth updates
    """

    def __init__(
        self,
        total_items: int,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        smoothing_window: int = 10,
        min_samples_for_eta: int = 5
    ):
        """
        Args:
            total_items: Total number of items to process
            callback: Progress update callback
            smoothing_window: Moving average window size
            min_samples_for_eta: Minimum samples needed for ETA calculation
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
        """
        Update progress

        Args:
            increment: Number of items completed
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
        """Reset progress"""
        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.speed_samples = []

    def get_info(self) -> ProgressInfo:
        """Get current progress information"""
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