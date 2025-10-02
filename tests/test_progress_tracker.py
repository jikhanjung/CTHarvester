"""
Tests for progress tracking module

Tests SimpleProgressTracker and ProgressInfo classes
"""

import time
from unittest.mock import MagicMock

import pytest

from core.progress_tracker import ProgressInfo, SimpleProgressTracker


@pytest.mark.unit
class TestProgressInfo:
    """Test suite for ProgressInfo dataclass"""

    def test_initialization(self):
        """Test ProgressInfo initialization"""
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=30.0,
            elapsed_seconds=30.0,
            speed=1.67,
        )

        assert info.current == 50
        assert info.total == 100
        assert info.percentage == 50.0
        assert info.eta_seconds == 30.0
        assert info.elapsed_seconds == 30.0
        assert info.speed == 1.67

    def test_eta_formatted_calculating(self):
        """Test ETA formatting when ETA is not available"""
        info = ProgressInfo(
            current=5, total=100, percentage=5.0, eta_seconds=None, elapsed_seconds=1.0, speed=5.0
        )

        assert info.eta_formatted == "Calculating..."

    def test_eta_formatted_seconds(self):
        """Test ETA formatting for seconds"""
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=45.0,
            elapsed_seconds=45.0,
            speed=1.11,
        )

        assert info.eta_formatted == "45s"

    def test_eta_formatted_minutes(self):
        """Test ETA formatting for minutes"""
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=150.0,  # 2m 30s
            elapsed_seconds=150.0,
            speed=0.33,
        )

        assert info.eta_formatted == "2m 30s"

    def test_eta_formatted_hours(self):
        """Test ETA formatting for hours"""
        info = ProgressInfo(
            current=10,
            total=100,
            percentage=10.0,
            eta_seconds=4500.0,  # 1h 15m
            elapsed_seconds=500.0,
            speed=0.02,
        )

        assert info.eta_formatted == "1h 15m"

    def test_elapsed_formatted_seconds(self):
        """Test elapsed time formatting for seconds"""
        info = ProgressInfo(
            current=10,
            total=100,
            percentage=10.0,
            eta_seconds=None,
            elapsed_seconds=45.0,
            speed=0.22,
        )

        assert info.elapsed_formatted == "45s"

    def test_elapsed_formatted_minutes(self):
        """Test elapsed time formatting for minutes"""
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=None,
            elapsed_seconds=150.0,  # 2m 30s
            speed=0.33,
        )

        assert info.elapsed_formatted == "2m 30s"

    def test_elapsed_formatted_hours(self):
        """Test elapsed time formatting for hours"""
        info = ProgressInfo(
            current=90,
            total=100,
            percentage=90.0,
            eta_seconds=None,
            elapsed_seconds=4500.0,  # 1h 15m
            speed=0.02,
        )

        assert info.elapsed_formatted == "1h 15m"

    def test_eta_edge_cases(self):
        """Test ETA formatting edge cases"""
        # Exactly 1 minute
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=60.0,
            elapsed_seconds=60.0,
            speed=0.83,
        )
        assert info.eta_formatted == "1m 0s"

        # Exactly 1 hour
        info = ProgressInfo(
            current=50,
            total=100,
            percentage=50.0,
            eta_seconds=3600.0,
            elapsed_seconds=3600.0,
            speed=0.014,
        )
        assert info.eta_formatted == "1h 0m"

        # Zero seconds
        info = ProgressInfo(
            current=99,
            total=100,
            percentage=99.0,
            eta_seconds=0.5,
            elapsed_seconds=100.0,
            speed=0.99,
        )
        assert info.eta_formatted == "0s"


@pytest.mark.unit
class TestSimpleProgressTracker:
    """Test suite for SimpleProgressTracker"""

    def test_initialization(self):
        """Test tracker initialization"""
        tracker = SimpleProgressTracker(total_items=100)

        assert tracker.total_items == 100
        assert tracker.completed_items == 0
        assert tracker.callback is None
        assert tracker.smoothing_window == 10
        assert tracker.min_samples_for_eta == 5
        assert len(tracker.speed_samples) == 0

    def test_initialization_with_custom_params(self):
        """Test tracker initialization with custom parameters"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(
            total_items=50, callback=callback, smoothing_window=20, min_samples_for_eta=10
        )

        assert tracker.total_items == 50
        assert tracker.callback == callback
        assert tracker.smoothing_window == 20
        assert tracker.min_samples_for_eta == 10

    def test_update_increments_progress(self):
        """Test that update increments progress"""
        tracker = SimpleProgressTracker(total_items=100)

        tracker.update()
        assert tracker.completed_items == 1

        tracker.update(5)
        assert tracker.completed_items == 6

        tracker.update(10)
        assert tracker.completed_items == 16

    def test_update_calculates_percentage(self):
        """Test percentage calculation"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        tracker.update(25)

        info = callback.call_args[0][0]
        assert info.percentage == 25.0

        tracker.update(25)
        info = callback.call_args[0][0]
        assert info.percentage == 50.0

    def test_update_invokes_callback(self):
        """Test that update invokes callback"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        tracker.update()

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert isinstance(info, ProgressInfo)
        assert info.current == 1
        assert info.total == 100

    def test_update_without_callback(self):
        """Test update without callback (should not crash)"""
        tracker = SimpleProgressTracker(total_items=100)

        # Should not crash
        tracker.update()
        assert tracker.completed_items == 1

    def test_speed_calculation(self):
        """Test speed calculation"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback, min_samples_for_eta=1)

        # First update
        time.sleep(0.05)
        tracker.update()
        time.sleep(0.05)

        # Second update
        tracker.update()

        info = callback.call_args[0][0]
        # Speed should be positive (actual value depends on system timing)
        assert info.speed > 0
        # Just verify it's calculating speed, don't check exact value due to timing variations

    def test_eta_calculation_requires_minimum_samples(self):
        """Test that ETA requires minimum samples"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback, min_samples_for_eta=5)

        # First update - not enough samples
        tracker.update()
        info = callback.call_args[0][0]
        assert info.eta_seconds is None

        # Add more updates
        for _ in range(4):
            time.sleep(0.01)
            tracker.update()

        # Now should have ETA (5 samples)
        info = callback.call_args[0][0]
        assert info.eta_seconds is not None

    def test_eta_calculation_with_speed(self):
        """Test ETA calculation based on speed"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback, min_samples_for_eta=1)

        # Simulate work
        for i in range(10):
            time.sleep(0.01)
            tracker.update()

        info = callback.call_args[0][0]

        # Should have ETA
        assert info.eta_seconds is not None
        # Remaining items: 90, speed should be ~100-1000 items/sec
        # ETA should be < 1 second
        assert 0 < info.eta_seconds < 2

    def test_moving_average_smoothing(self):
        """Test moving average window for speed smoothing"""
        tracker = SimpleProgressTracker(total_items=100, smoothing_window=3, min_samples_for_eta=1)

        # Add 5 updates
        for _ in range(5):
            time.sleep(0.01)
            tracker.update()

        # Speed samples should be limited to window size
        assert len(tracker.speed_samples) == 3  # Window size

    def test_reset(self):
        """Test reset functionality"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        # Make some progress
        tracker.update(50)
        assert tracker.completed_items == 50
        assert len(tracker.speed_samples) > 0

        # Reset
        tracker.reset()

        assert tracker.completed_items == 0
        assert len(tracker.speed_samples) == 0
        # Start time should be updated
        assert tracker.start_time <= time.time()

    def test_get_info_without_update(self):
        """Test get_info() retrieves current state without updating"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        tracker.update(25)
        callback.reset_mock()

        # Get info without updating
        info = tracker.get_info()

        # Should return current state
        assert info.current == 25
        assert info.total == 100
        assert info.percentage == 25.0

        # Should not invoke callback
        callback.assert_not_called()

        # Should not increment progress
        assert tracker.completed_items == 25

    def test_get_info_with_no_speed_samples(self):
        """Test get_info() when no speed samples available"""
        tracker = SimpleProgressTracker(total_items=100)

        info = tracker.get_info()

        assert info.speed == 0
        assert info.eta_seconds is None

    def test_elapsed_time_tracking(self):
        """Test elapsed time tracking"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        time.sleep(0.1)
        tracker.update()

        info = callback.call_args[0][0]
        assert info.elapsed_seconds >= 0.1
        assert info.elapsed_seconds < 0.2  # Allow some margin

    def test_completion_scenario(self):
        """Test complete workflow from start to finish"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=10, callback=callback, min_samples_for_eta=2)

        # Simulate processing 10 items
        for i in range(10):
            time.sleep(0.01)
            tracker.update()

        # Final callback should show 100%
        final_info = callback.call_args[0][0]
        assert final_info.current == 10
        assert final_info.total == 10
        assert final_info.percentage == 100.0

        # Should have been called 10 times
        assert callback.call_count == 10

    def test_zero_speed_handling(self):
        """Test handling of zero speed (immediate update)"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        # Update immediately (elapsed time ≈ 0)
        tracker.update()

        info = callback.call_args[0][0]
        # Should handle zero elapsed time gracefully
        assert info.speed >= 0
        assert info.eta_seconds is None  # Can't calculate with zero speed

    def test_large_increment(self):
        """Test updating with large increment"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=1000, callback=callback)

        tracker.update(500)

        info = callback.call_args[0][0]
        assert info.current == 500
        assert info.percentage == 50.0

    def test_callback_receives_correct_info_structure(self):
        """Test that callback receives ProgressInfo with all fields"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        time.sleep(0.01)
        tracker.update(10)

        info = callback.call_args[0][0]

        # Verify all ProgressInfo fields are present
        assert hasattr(info, "current")
        assert hasattr(info, "total")
        assert hasattr(info, "percentage")
        assert hasattr(info, "eta_seconds")
        assert hasattr(info, "elapsed_seconds")
        assert hasattr(info, "speed")
        assert hasattr(info, "eta_formatted")
        assert hasattr(info, "elapsed_formatted")


@pytest.mark.integration
class TestProgressTrackerIntegration:
    """Integration tests for progress tracking"""

    def test_realistic_progress_tracking(self):
        """Test realistic progress tracking scenario"""
        results = []

        def collect_progress(info: ProgressInfo):
            results.append(
                {"percentage": info.percentage, "speed": info.speed, "eta": info.eta_seconds}
            )

        tracker = SimpleProgressTracker(
            total_items=50, callback=collect_progress, min_samples_for_eta=3
        )

        # Simulate processing
        for i in range(50):
            time.sleep(0.005)  # Simulate work
            tracker.update()

        # Verify progress went from 0 to 100%
        assert results[0]["percentage"] == 2.0  # First update: 1/50
        assert results[-1]["percentage"] == 100.0  # Last update: 50/50

        # Verify ETA decreased over time (after initial samples)
        etas_with_values = [r["eta"] for r in results[3:] if r["eta"] is not None]
        if len(etas_with_values) > 1:
            # ETA should generally decrease (allowing some fluctuation)
            assert etas_with_values[-1] < etas_with_values[0]

    def test_speed_averaging(self):
        """Test speed averaging over multiple updates"""
        speeds = []

        def collect_speed(info: ProgressInfo):
            speeds.append(info.speed)

        tracker = SimpleProgressTracker(total_items=20, callback=collect_speed, smoothing_window=5)

        # Variable speed processing
        for i in range(20):
            if i < 10:
                time.sleep(0.01)  # Slower
            else:
                time.sleep(0.001)  # Faster
            tracker.update()

        # Speed should increase in second half
        avg_first_half = sum(speeds[:10]) / 10
        avg_second_half = sum(speeds[10:]) / 10

        # Second half should be faster (though smoothing will dampen the difference)
        assert avg_second_half >= avg_first_half * 0.8  # Allow for smoothing effect

    def test_reset_and_reuse(self):
        """Test resetting and reusing tracker"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=10, callback=callback)

        # First run
        for i in range(10):
            tracker.update()

        assert callback.call_count == 10

        # Reset
        tracker.reset()
        callback.reset_mock()

        # Second run
        for i in range(10):
            tracker.update()

        assert callback.call_count == 10
        final_info = callback.call_args[0][0]
        assert final_info.percentage == 100.0

    def test_concurrent_get_info_and_update(self):
        """Test that get_info() and update() can be used together"""
        callback = MagicMock()
        tracker = SimpleProgressTracker(total_items=100, callback=callback)

        for i in range(10):
            tracker.update()

            # Get info without updating
            info = tracker.get_info()
            assert info.current == i + 1

        # Total updates should be 10 (not 20)
        assert callback.call_count == 10
        assert tracker.completed_items == 10
