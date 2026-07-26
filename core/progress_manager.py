"""
ProgressManager - Centralized progress and ETA management

Extracted from CTHarvester.py during Phase 4c refactoring.
"""

import logging
import time

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ProgressManager(QObject):
    """Centralized progress and ETA management"""

    # Signals
    progress_updated = pyqtSignal(int)  # percentage
    eta_updated = pyqtSignal(str)  # ETA text
    detail_updated = pyqtSignal(str)  # detail text

    def __init__(self) -> None:
        super().__init__()
        self.current: int = 0
        self.total: int = 0
        self.start_time: float | None = None
        self.is_sampling: bool = False
        self.speed: float | None = None  # units per second
        self.level_work_distribution: dict[int, dict[str, int]] | None = (
            None  # Store level work info
        )
        self.weighted_total_work: float | None = None  # Store weighted total

    def start(self, total: int) -> None:
        """Initialize progress tracking"""
        self.total = total
        self.current = 0
        # perf_counter, not time(): monotonic, so an NTP step cannot make
        # elapsed go backwards, and high-resolution everywhere. time() advances
        # in ~15.6ms steps on Windows, which made elapsed read exactly 0.0 for
        # any work that finished inside one tick.
        self.start_time = time.perf_counter()
        self.is_sampling = False

    def update(self, value: int | None = None, delta: int = 1) -> None:
        """Update progress by delta or to specific value"""
        if value is not None:
            self.current = value
        else:
            self.current += delta

        percentage = int(self.current / self.total * 100) if self.total > 0 else 0
        self.progress_updated.emit(percentage)

        # Calculate and emit ETA
        eta_text = self.calculate_eta()
        if eta_text:
            self.eta_updated.emit(eta_text)

    def set_sampling(self, is_sampling: bool) -> None:
        """Set whether we're in sampling phase"""
        self.is_sampling = is_sampling
        if is_sampling:
            self.eta_updated.emit("Estimating...")

    def set_speed(self, speed: float) -> None:
        """Set processing speed (units per second)"""
        self.speed = speed

    def calculate_eta(self) -> str:
        """Calculate estimated time of arrival"""
        if self.is_sampling:
            return "Estimating..."

        if self.start_time is None:
            return ""

        # "Completing..." is decided by the work counters alone. It used to sit
        # below the `elapsed <= 0` guard, so a call landing in the same clock
        # tick as start() returned "" for finished work -- routine on Windows,
        # where time.time() advanced in ~15.6ms steps.
        if self.weighted_total_work and self.weighted_total_work > 0:
            weighted_progress = self.current
            remaining_weighted_work = self.weighted_total_work - weighted_progress
            if remaining_weighted_work <= 0:
                return "Completing..."
        else:
            remaining = self.total - self.current
            if remaining <= 0:
                return "Completing..."

        elapsed = time.perf_counter() - self.start_time
        if elapsed <= 0:
            return ""

        # If we have weighted work distribution, the current value is already weighted
        if self.weighted_total_work and self.weighted_total_work > 0:
            # Calculate weighted speed
            weighted_speed = weighted_progress / elapsed

            if weighted_speed > 0:
                remaining_time = remaining_weighted_work / weighted_speed
            else:
                return ""
        else:
            # Fallback to simple calculation
            if self.current > 0:
                actual_speed = self.current / elapsed
                remaining_time = remaining / actual_speed
            else:
                return ""

        # Format time with ETA prefix
        from config.constants import SECONDS_PER_HOUR, SECONDS_PER_MINUTE

        if remaining_time < SECONDS_PER_MINUTE:
            return f"ETA: {int(remaining_time)}s"
        elif remaining_time < SECONDS_PER_HOUR:
            return f"ETA: {int(remaining_time / SECONDS_PER_MINUTE)}m {int(remaining_time % SECONDS_PER_MINUTE)}s"
        else:
            return f"ETA: {int(remaining_time / SECONDS_PER_HOUR)}h {int((remaining_time % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE)}m"

    def get_detail_text(
        self,
        level: int | None = None,
        completed: int | None = None,
        total: int | None = None,
    ) -> str:
        """Get detail text for current state"""
        if level is not None and completed is not None and total is not None:
            return f"Level {level + 1}: {completed}/{total}"
        return ""
