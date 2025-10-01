"""
ProgressDialog - Thumbnail generation progress dialog

Extracted from CTHarvester.py during Phase 4 UI refactoring.
"""

import logging
import time
from collections import deque

from PyQt5.QtCore import QPoint, QRect, Qt, QTranslator
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
        import logging
        import time
        from collections import deque

        logger = logging.getLogger("CTHarvester")

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
                eta_text = (
                    f"{int(initial_estimate_seconds/60)}m {int(initial_estimate_seconds%60)}s"
                )
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
        import logging
        import time

        import numpy as np

        logger = logging.getLogger("CTHarvester")

        current_time = time.time()
        self.current_step = step

        if self.total_steps > 0:
            percentage = int((self.current_step / self.total_steps) * 100)
            self.pb_progress.setValue(percentage)

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
            trimmed_times = (
                sorted_times[trim_count:-trim_count]
                if len(sorted_times) > 2 * trim_count
                else sorted_times
            )
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
        current_estimate = np.average(estimates, weights=weights[: len(estimates)])

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
            hours = int(eta_seconds / 3600)
            minutes = int((eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def update_language(self):
        translator = QTranslator()
        translator.load(resource_path("resources/translations/CTHarvester_{}.qm").format(self.m_app.language))
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
            self.speed_label.setText(f"Speed: {1/info.speed:.1f} s/item")
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
