"""
ProgressDialog - Thumbnail generation progress dialog

Extracted from CTHarvester.py during Phase 4 UI refactoring.
"""

import logging
import time
from collections import deque

from PyQt5.QtCore import QPoint, QRect, QTranslator
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.progress_tracker import ProgressInfo
from utils.common import resource_path

logger = logging.getLogger(__name__)


class ProgressDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.parent = parent
        self.m_app = QApplication.instance()
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos() + QPoint(100, 100))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(50, 50, 50, 50)

        self.lbl_text = QLabel(self)
        self.lbl_detail = QLabel(self)  # Additional label for ETA
        self.lbl_remaining = QLabel(self)  # Label for remaining time (Phase 2.2.4)
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
        self.layout.addWidget(self.lbl_remaining)
        self.layout.addWidget(self.pb_progress)
        self.layout.addWidget(self.btnCancel)
        self.setLayout(self.layout)

        # For time estimation
        self.start_time = None
        self.total_steps = 0
        self.current_step = 0

        # Advanced ETA calculation with improved stability
        self.step_times = deque(maxlen=100)  # Keep last 100 step times for better averaging
        self.last_update_time = None
        self.smoothed_eta = None  # Exponentially smoothed ETA
        self.ema_alpha = (
            0.1  # Reduced EMA smoothing factor for more stability (0.1 = 10% new, 90% old)
        )
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

    def set_progress_text(self, text_format):
        self.text_format = text_format

    def set_max_value(self, max_value):
        self.max_value = max_value

    def set_curr_value(self, curr_value):
        self.curr_value = curr_value
        self.pb_progress.setValue(int((self.curr_value / float(self.max_value)) * 100))
        self.lbl_text.setText(self.text_format.format(self.curr_value, self.max_value))
        self.update()
        QApplication.processEvents()

    def setup_unified_progress(self, total_steps, initial_estimate_seconds=None):
        """Setup for unified progress tracking with optional initial estimate"""
        logger = logging.getLogger("CTHarvester")

        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.pb_progress.setMaximum(100)
        self.pb_progress.setValue(0)

        # Reset ETA calculation state
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
                eta_text = (
                    f"{int(initial_estimate_seconds / 60)}m {int(initial_estimate_seconds % 60)}s"
                )
            else:
                eta_text = f"{int(initial_estimate_seconds / 3600)}h {int((initial_estimate_seconds % 3600) / 60)}m"
            self.lbl_detail.setText(f"ETA: {eta_text}")
            logger.info(f"ProgressDialog initial ETA: {eta_text} ({initial_estimate_seconds:.1f}s)")
        else:
            self.lbl_detail.setText("Estimating...")
            logger.info("ProgressDialog showing 'Estimating...' until sampling completes")

        logger.info(f"ProgressDialog.setup_unified_progress: total_steps={total_steps}")

    def update_unified_progress(self, step, detail_text=""):
        """Update unified progress with sophisticated ETA calculation"""
        import numpy as np

        logger = logging.getLogger("CTHarvester")

        current_time = time.time()
        self.current_step = step

        if self.total_steps > 0:
            percentage = int((self.current_step / self.total_steps) * 100)
            self.pb_progress.setValue(percentage)

            # Update remaining items count (Phase 2.2.4)
            remaining = self.total_steps - self.current_step
            self.lbl_remaining.setText(f"Remaining: {remaining:,} / {self.total_steps:,} items")

            # Record step timing (skip first few for warm-up)
            if self.last_update_time and step > 3:  # Skip first 3 steps for warm-up
                step_duration = current_time - self.last_update_time
                # Filter out outliers (>5x median)
                if (
                    len(self.step_times) == 0
                    or step_duration < np.median(list(self.step_times)) * 5
                ):
                    self.step_times.append(step_duration)
                    self.step_history.append((current_time, step))

            # Don't calculate ETA here - it will be set externally by ThumbnailManager
            # after sampling or periodic updates
            # Just keep the existing text if no new one is provided
            current_text = self.lbl_detail.text()
            if not current_text.startswith("ETA:") and current_text != "Estimating...":
                # Only calculate if we don't have an externally set ETA
                eta_text = self._calculate_eta(current_time)
                if eta_text:
                    self.lbl_detail.setText(f"ETA: {eta_text} - {detail_text}")
                else:
                    self.lbl_detail.setText(detail_text)
            elif detail_text:
                # Keep existing ETA, just update detail text
                if "ETA:" in current_text:
                    eta_part = (
                        current_text.split(" - ")[0] if " - " in current_text else current_text
                    )
                    self.lbl_detail.setText(f"{eta_part} - {detail_text}")
                else:
                    self.lbl_detail.setText(f"{current_text} - {detail_text}")

            # Log current state
            current_eta = (
                self.lbl_detail.text().split(" - ")[0]
                if " - " in self.lbl_detail.text()
                else self.lbl_detail.text()
            )
            logger.debug(
                f"ProgressDialog.update: step={step}/{self.total_steps}, {percentage}%, {current_eta}, {detail_text}"
            )

        self.last_update_time = current_time
        self.update()

        # Process events periodically to maintain UI responsiveness
        from config.constants import PROGRESS_UPDATE_STEP_INTERVAL

        if step % PROGRESS_UPDATE_STEP_INTERVAL == 0:
            QApplication.processEvents()

    @staticmethod
    def _format_eta(eta_seconds):
        """Render a duration as the coarsest two units that fit."""
        eta_seconds = max(0, eta_seconds)
        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        if eta_seconds < 3600:
            return f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
        return f"{int(eta_seconds / 3600)}h {int((eta_seconds % 3600) / 60)}m"

    def _record_velocity(self):
        """Append one velocity sample from the last two step_history entries."""
        if len(self.step_history) < 2:
            return

        recent_time = self.step_history[-1][0] - self.step_history[-2][0]
        recent_steps = self.step_history[-1][1] - self.step_history[-2][1]
        if recent_time > 0 and recent_steps > 0:
            self.velocity_history.append(recent_steps / recent_time)

    def _eta_from_step_times(self, remaining_steps):
        """Estimate from a trimmed mean of recent per-step times, or None.

        Trimmed because a single slow image -- a cache miss, a stalled disk --
        otherwise drags the whole average with it.
        """
        import numpy as np

        if len(self.step_times) < self.min_samples_for_eta:
            return None

        sorted_times = sorted(self.step_times)
        trim_count = max(1, len(sorted_times) // 10)  # 10% off each end
        trimmed_times = (
            sorted_times[trim_count:-trim_count]
            if len(sorted_times) > 2 * trim_count
            else sorted_times
        )
        avg_step_time = np.mean(trimmed_times) if trimmed_times else np.mean(sorted_times)
        return avg_step_time * remaining_steps

    def _eta_from_elapsed(self, current_time, remaining_steps):
        """Estimate from the average rate since the start, or None.

        The most stable of the three, because it cannot be moved much by any
        single step.
        """
        if self.current_step <= 0:
            return None

        elapsed = current_time - self.start_time
        return (elapsed / self.current_step) * remaining_steps

    def _eta_from_velocity(self, remaining_steps):
        """Estimate from the median recent velocity, or None.

        The most responsive of the three; median rather than mean so one
        outlying sample cannot swing it.
        """
        import numpy as np

        if len(self.velocity_history) < 5:
            return None

        median_velocity = np.median(list(self.velocity_history))
        if median_velocity <= 0:
            return None
        return remaining_steps / median_velocity

    def _smooth_eta(self, current_estimate):
        """Fold a new estimate into self.smoothed_eta, rate-limited.

        A raw ETA jumps around enough to be unreadable, so each update may move
        the displayed value by at most 20%, and even that is damped by the EMA.
        """
        if self.smoothed_eta is None:
            self.smoothed_eta = current_estimate
            return

        max_change = self.smoothed_eta * 0.2
        change = current_estimate - self.smoothed_eta
        if abs(change) > max_change:
            change = max_change if change > 0 else -max_change

        self.smoothed_eta = self.smoothed_eta + self.ema_alpha * change

    def _calculate_eta(self, current_time):
        """Calculate ETA by blending three estimates, smoothed and formatted.

        Returns None when there is nothing to estimate: no work left, or no
        method has enough data yet.
        """
        import numpy as np

        remaining_steps = self.total_steps - self.current_step
        if remaining_steps <= 0:
            return None

        # Recomputing on every step makes the number flicker; between updates
        # the previously smoothed value is re-formatted instead.
        if current_time - self.last_eta_update < self.eta_update_interval:
            # Truthiness, not `is not None`: a smoothed value of exactly 0.0
            # reads as "no estimate" here. Pinned by the tests as existing
            # behaviour rather than fixed blind.
            if self.smoothed_eta:
                return self._format_eta(self.smoothed_eta)
            return None

        self.last_eta_update = current_time
        self._record_velocity()

        # Weights: steadiest method first, most responsive last.
        candidates = [
            (self._eta_from_elapsed(current_time, remaining_steps), 0.5),
            (self._eta_from_step_times(remaining_steps), 0.3),
            (self._eta_from_velocity(remaining_steps), 0.2),
        ]
        estimates = [value for value, _ in candidates if value is not None]
        weights = [weight for value, weight in candidates if value is not None]

        if not estimates:
            return None

        self._smooth_eta(np.average(estimates, weights=weights))
        return self._format_eta(self.smoothed_eta)

    def update_language(self):
        translator = QTranslator()
        translator.load(
            resource_path("resources/translations/CTHarvester_{}.qm").format(self.m_app.language)
        )
        self.m_app.installTranslator(translator)

        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.btnStop.setText(self.tr("Stop"))


class ModernProgressDialog(QDialog):
    """
    Modern and clean progress dialog

    Improvements over ProgressDialog:
    - Single progress bar
    - Clear ETA display
    - Current/total count display
    - Speed display
    - Simpler interface using ProgressInfo

    Created during Phase 1.1 UI/UX improvements.
    """

    def __init__(self, parent=None, title="Processing"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)

        self.is_cancelled = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        self.title_label = QLabel("Processing thumbnails...")
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """
        )
        layout.addWidget(self.progress_bar)

        # Detail information
        info_layout = QHBoxLayout()

        # Current/total
        self.count_label = QLabel("0 / 0")
        info_layout.addWidget(self.count_label)

        info_layout.addStretch()

        # Speed
        self.speed_label = QLabel("Speed: -")
        info_layout.addWidget(self.speed_label)

        info_layout.addStretch()

        # Elapsed time
        self.elapsed_label = QLabel("Elapsed: 0s")
        info_layout.addWidget(self.elapsed_label)

        info_layout.addStretch()

        # ETA
        self.eta_label = QLabel("ETA: Calculating...")
        info_layout.addWidget(self.eta_label)

        layout.addLayout(info_layout)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_progress(self, info: ProgressInfo):
        """
        Update progress display

        Args:
            info: ProgressInfo object
        """
        # Progress percentage
        self.progress_bar.setValue(int(info.percentage))

        # Count
        self.count_label.setText(f"{info.current:,} / {info.total:,}")

        # Speed
        if info.speed > 1:
            self.speed_label.setText(f"Speed: {info.speed:.1f} items/s")
        elif info.speed > 0:
            self.speed_label.setText(f"Speed: {1 / info.speed:.1f} s/item")
        else:
            self.speed_label.setText("Speed: -")

        # Elapsed time
        self.elapsed_label.setText(f"Elapsed: {info.elapsed_formatted}")

        # ETA
        self.eta_label.setText(f"ETA: {info.eta_formatted}")

    def cancel(self):
        """Cancel button clicked"""
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.title_label.setText("Cancelling, please wait...")

    def set_title(self, title: str):
        """Set dialog title text"""
        self.title_label.setText(title)
