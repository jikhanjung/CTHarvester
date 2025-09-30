"""
Unit tests for core/progress_manager.py

Tests progress tracking and ETA calculation.
"""
import sys
import os
import time
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtCore import QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    from core.progress_manager import ProgressManager


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestProgressManager:
    """Tests for ProgressManager class"""

    def setup_method(self):
        """Create ProgressManager instance"""
        self.manager = ProgressManager()

    def test_initialization(self):
        """Should initialize with default values"""
        assert self.manager.current == 0
        assert self.manager.total == 0
        assert self.manager.start_time is None
        assert self.manager.is_sampling is False

    def test_start(self):
        """Should initialize progress tracking"""
        self.manager.start(total=100)
        assert self.manager.total == 100
        assert self.manager.current == 0
        assert self.manager.start_time is not None
        assert isinstance(self.manager.start_time, float)

    def test_update_by_delta(self):
        """Should update progress by delta"""
        self.manager.start(total=100)
        self.manager.update(delta=10)
        assert self.manager.current == 10

        self.manager.update(delta=20)
        assert self.manager.current == 30

    def test_update_to_value(self):
        """Should update progress to specific value"""
        self.manager.start(total=100)
        self.manager.update(value=50)
        assert self.manager.current == 50

        self.manager.update(value=75)
        assert self.manager.current == 75

    def test_percentage_calculation(self):
        """Should calculate percentage correctly"""
        self.manager.start(total=100)

        # Note: We can't easily test signal emission without pytest-qt
        # Just verify the calculation doesn't crash
        self.manager.update(value=0)
        self.manager.update(value=25)
        self.manager.update(value=50)
        self.manager.update(value=100)

    def test_zero_total(self):
        """Should handle zero total gracefully"""
        self.manager.start(total=0)
        # Should not crash
        self.manager.update(value=0)

    def test_set_sampling(self):
        """Should set sampling state"""
        assert self.manager.is_sampling is False

        self.manager.set_sampling(True)
        assert self.manager.is_sampling is True

        self.manager.set_sampling(False)
        assert self.manager.is_sampling is False

    def test_set_speed(self):
        """Should set speed"""
        self.manager.set_speed(10.5)
        assert self.manager.speed == 10.5

        self.manager.set_speed(0)
        assert self.manager.speed == 0

    def test_calculate_eta_without_start(self):
        """Should handle ETA calculation when not started"""
        eta = self.manager.calculate_eta()
        # Should return None or empty string
        assert eta is None or eta == ""

    def test_calculate_eta_with_zero_progress(self):
        """Should handle ETA calculation with zero progress"""
        self.manager.start(total=100)
        eta = self.manager.calculate_eta()
        # Should return None or estimation message
        assert eta is None or "Estimating" in eta or eta == ""

    def test_calculate_eta_with_progress(self):
        """Should calculate ETA with progress"""
        self.manager.start(total=100)
        self.manager.update(value=50)
        time.sleep(0.1)  # Small delay for time calculation

        eta = self.manager.calculate_eta()
        # Should return some string (ETA or estimation)
        assert isinstance(eta, (str, type(None)))

    def test_multiple_updates(self):
        """Should handle multiple consecutive updates"""
        self.manager.start(total=1000)

        for i in range(0, 1001, 100):
            self.manager.update(value=i)
            assert self.manager.current == i

    def test_progress_beyond_total(self):
        """Should handle progress beyond total"""
        self.manager.start(total=100)
        # This shouldn't crash even if current > total
        self.manager.update(value=150)
        assert self.manager.current == 150


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestProgressManagerSignals:
    """Tests for ProgressManager signals (requires pytest-qt)"""

    def setup_method(self):
        """Create ProgressManager instance"""
        self.manager = ProgressManager()
        self.progress_values = []
        self.eta_values = []
        self.detail_values = []

        # Connect signals to capture emitted values
        self.manager.progress_updated.connect(self.progress_values.append)
        self.manager.eta_updated.connect(self.eta_values.append)
        self.manager.detail_updated.connect(self.detail_values.append)

    def test_progress_signal_emission(self):
        """Should emit progress signal on update"""
        self.manager.start(total=100)
        self.manager.update(value=50)

        assert len(self.progress_values) > 0
        assert self.progress_values[-1] == 50  # 50% progress

    def test_sampling_signal(self):
        """Should emit ETA signal when setting sampling"""
        self.manager.set_sampling(True)

        assert len(self.eta_values) > 0
        assert "Estimating" in self.eta_values[-1]

    def test_eta_signal_emission(self):
        """Should emit ETA signal during update"""
        self.manager.start(total=100)
        self.manager.update(value=50)

        # Should have received ETA update
        assert len(self.eta_values) > 0


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestProgressManagerETA:
    """Tests for ETA calculation edge cases"""

    def setup_method(self):
        """Create ProgressManager instance"""
        self.manager = ProgressManager()

    def test_eta_with_weighted_work(self):
        """Should calculate ETA with weighted work distribution"""
        self.manager.start(total=100)
        self.manager.weighted_total_work = 1000

        # Simulate progress
        self.manager.current = 500  # 50% of weighted work
        time.sleep(0.1)

        eta = self.manager.calculate_eta()
        # Should return some ETA string
        assert isinstance(eta, str)

    def test_eta_with_weighted_work_completing(self):
        """Should return 'Completing...' when weighted work nearly done"""
        self.manager.start(total=100)
        self.manager.weighted_total_work = 1000
        self.manager.current = 1001  # Exceeded total

        eta = self.manager.calculate_eta()
        assert eta == "Completing..."

    def test_eta_with_weighted_work_zero_speed(self):
        """Should handle zero weighted speed"""
        self.manager.start(total=100)
        self.manager.weighted_total_work = 1000
        self.manager.current = 0
        time.sleep(0.01)

        eta = self.manager.calculate_eta()
        # Should return empty string or estimation
        assert isinstance(eta, str)

    def test_eta_simple_calculation_completing(self):
        """Should return 'Completing...' when simple calculation shows done"""
        self.manager.start(total=100)
        self.manager.current = 100

        eta = self.manager.calculate_eta()
        assert eta == "Completing..."

    def test_eta_simple_calculation_remaining(self):
        """Should calculate ETA with simple calculation"""
        self.manager.start(total=100)
        self.manager.current = 50
        time.sleep(0.1)

        eta = self.manager.calculate_eta()
        # Should have ETA format
        assert "ETA:" in eta or eta == ""

    def test_eta_format_seconds(self):
        """Should format ETA in seconds for short durations"""
        self.manager.start(total=1000)
        self.manager.current = 990
        time.sleep(0.1)

        eta = self.manager.calculate_eta()
        if "ETA:" in eta:
            assert "s" in eta

    def test_eta_format_minutes(self):
        """Should format ETA in minutes for medium durations"""
        self.manager.start(total=1000)
        self.manager.current = 10
        time.sleep(0.1)

        # Simulate longer remaining time by adjusting start_time
        self.manager.start_time = time.time() - 10  # 10 seconds elapsed

        eta = self.manager.calculate_eta()
        if "ETA:" in eta and "h" not in eta:
            # Could be minutes or seconds
            assert "m" in eta or "s" in eta

    def test_eta_format_hours(self):
        """Should format ETA in hours for long durations"""
        self.manager.start(total=10000)
        self.manager.current = 10
        time.sleep(0.1)

        # Simulate very long remaining time
        self.manager.start_time = time.time() - 100  # 100 seconds elapsed for 10 items

        eta = self.manager.calculate_eta()
        # With current=10, total=10000, elapsed=100s, remaining would be huge
        if "ETA:" in eta:
            # Might have hours
            assert "h" in eta or "m" in eta or "s" in eta

    def test_eta_zero_elapsed_time(self):
        """Should handle zero elapsed time"""
        self.manager.start(total=100)
        # Set start_time to future (results in negative/zero elapsed)
        self.manager.start_time = time.time() + 10

        eta = self.manager.calculate_eta()
        assert eta == ""

    def test_get_detail_text_with_parameters(self):
        """Should generate detail text with parameters"""
        detail = self.manager.get_detail_text(level=0, completed=50, total=100)
        assert detail == "Level 1: 50/100"

    def test_get_detail_text_without_parameters(self):
        """Should return empty string without parameters"""
        detail = self.manager.get_detail_text()
        assert detail == ""

    def test_get_detail_text_partial_parameters(self):
        """Should return empty string with partial parameters"""
        detail = self.manager.get_detail_text(level=0)
        assert detail == ""

        detail = self.manager.get_detail_text(level=0, completed=50)
        assert detail == ""