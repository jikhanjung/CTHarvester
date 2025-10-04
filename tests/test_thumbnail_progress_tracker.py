"""Tests for core/thumbnail_progress_tracker.py - Progress tracking and sampling.

Part of Phase 3 architectural refactoring (devlog 072)
"""

import time
from unittest.mock import Mock

import pytest

from core.thumbnail_progress_tracker import ThumbnailProgressTracker
from utils.time_estimator import TimeEstimator


class TestThumbnailProgressTracker:
    """Test suite for ThumbnailProgressTracker class"""

    @pytest.fixture
    def tracker(self):
        """Create a basic progress tracker"""
        return ThumbnailProgressTracker(sample_size=5, level_weight=1.0)

    @pytest.fixture
    def tracker_with_speed(self):
        """Create a tracker with initial speed"""
        return ThumbnailProgressTracker(sample_size=5, level_weight=1.0, initial_speed=10.0)

    def test_initialization_basic(self):
        """Test basic initialization"""
        tracker = ThumbnailProgressTracker(sample_size=5, level_weight=1.0)

        assert tracker.sample_size == 5
        assert tracker.level_weight == 1.0
        assert tracker.is_sampling is False
        assert tracker.sample_start_time is None
        assert tracker.images_per_second is None
        assert tracker.completed_tasks == 0
        assert tracker.generated_count == 0
        assert tracker.loaded_count == 0

    def test_initialization_with_initial_speed(self):
        """Test initialization with inherited speed"""
        tracker = ThumbnailProgressTracker(sample_size=5, level_weight=0.25, initial_speed=15.0)

        assert tracker.images_per_second == 15.0
        assert tracker.level_weight == 0.25

    def test_initialization_with_custom_estimator(self):
        """Test initialization with custom TimeEstimator"""
        custom_estimator = TimeEstimator(level_reduction_factor=0.3)
        tracker = ThumbnailProgressTracker(
            sample_size=5, level_weight=1.0, time_estimator=custom_estimator
        )

        assert tracker.time_estimator == custom_estimator
        assert tracker.time_estimator.level_reduction_factor == 0.3

    def test_start_sampling_level_0(self, tracker):
        """Test starting sampling on level 0"""
        tracker.start_sampling(level=0, total_tasks=100)

        assert tracker.is_sampling is True
        assert tracker.sample_start_time is not None
        assert tracker.current_level == 0
        assert tracker.completed_tasks == 0

    def test_start_sampling_level_1(self, tracker):
        """Test that sampling is disabled for level 1+"""
        tracker.start_sampling(level=1, total_tasks=50)

        assert tracker.is_sampling is False
        assert tracker.current_level == 1

    def test_start_sampling_zero_sample_size(self):
        """Test that sampling is disabled when sample_size is 0"""
        tracker = ThumbnailProgressTracker(sample_size=0, level_weight=1.0)
        tracker.start_sampling(level=0, total_tasks=100)

        assert tracker.is_sampling is False

    def test_on_task_completed_generated(self, tracker):
        """Test task completion for generated thumbnail"""
        tracker.on_task_completed(1, 100, was_generated=True)

        assert tracker.completed_tasks == 1
        assert tracker.generated_count == 1
        assert tracker.loaded_count == 0

    def test_on_task_completed_loaded(self, tracker):
        """Test task completion for loaded thumbnail"""
        tracker.on_task_completed(1, 100, was_generated=False)

        assert tracker.completed_tasks == 1
        assert tracker.generated_count == 0
        assert tracker.loaded_count == 1

    def test_on_task_completed_multiple(self, tracker):
        """Test multiple task completions"""
        tracker.on_task_completed(1, 100, was_generated=True)
        tracker.on_task_completed(2, 100, was_generated=False)
        tracker.on_task_completed(3, 100, was_generated=True)

        assert tracker.completed_tasks == 3
        assert tracker.generated_count == 2
        assert tracker.loaded_count == 1

    def test_on_task_completed_bounds_check(self, tracker):
        """Test that task completion is capped at total"""
        tracker.on_task_completed(150, 100, was_generated=True)

        assert tracker.completed_tasks == 100  # Capped

    def test_should_log_stage_not_sampling(self, tracker):
        """Test should_log_stage returns False when not sampling"""
        tracker.is_sampling = False
        tracker.completed_tasks = 5

        assert tracker.should_log_stage() is False

    def test_should_log_stage_wrong_level(self, tracker):
        """Test should_log_stage returns False on non-zero level"""
        tracker.is_sampling = True
        tracker.current_level = 1
        tracker.completed_tasks = 5

        assert tracker.should_log_stage() is False

    def test_should_log_stage_stage_1(self, tracker):
        """Test should_log_stage at stage 1 threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 5  # sample_size

        assert tracker.should_log_stage() is True

    def test_should_log_stage_stage_2(self, tracker):
        """Test should_log_stage at stage 2 threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 10  # sample_size * 2

        assert tracker.should_log_stage() is True

    def test_should_log_stage_stage_3(self, tracker):
        """Test should_log_stage at stage 3 threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 15  # sample_size * 3

        assert tracker.should_log_stage() is True

    def test_should_log_stage_non_threshold(self, tracker):
        """Test should_log_stage returns False at non-threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 7  # Not a stage threshold

        assert tracker.should_log_stage() is False

    def test_get_current_stage_1(self, tracker):
        """Test get_current_stage returns 1 at first threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 5

        assert tracker.get_current_stage() == 1

    def test_get_current_stage_2(self, tracker):
        """Test get_current_stage returns 2 at second threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 10

        assert tracker.get_current_stage() == 2

    def test_get_current_stage_3(self, tracker):
        """Test get_current_stage returns 3 at third threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 15

        assert tracker.get_current_stage() == 3

    def test_get_current_stage_none(self, tracker):
        """Test get_current_stage returns None at non-threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 7

        assert tracker.get_current_stage() is None

    def test_get_stage_info_stage_1(self, tracker):
        """Test get_stage_info for stage 1"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 5
        time.sleep(0.01)  # Small delay for elapsed time

        info = tracker.get_stage_info(total_tasks=100, total_levels=3)

        assert info["stage"] == 1
        assert info["elapsed"] > 0
        assert info["time_per_image"] > 0
        assert info["total_estimate"] > 0
        assert "Stage 1 Sampling" in info["message"]
        assert info["should_stop_sampling"] is False
        assert tracker.stage1_estimate is not None
        assert tracker.stage1_speed is not None

    def test_get_stage_info_stage_2(self, tracker):
        """Test get_stage_info for stage 2"""
        tracker.start_sampling(level=0, total_tasks=100)

        # Simulate stage 1
        tracker.completed_tasks = 5
        time.sleep(0.01)
        info1 = tracker.get_stage_info(total_tasks=100, total_levels=3)

        # Now stage 2
        tracker.completed_tasks = 10
        time.sleep(0.01)
        info2 = tracker.get_stage_info(total_tasks=100, total_levels=3)

        assert info2["stage"] == 2
        assert "Stage 2 Sampling" in info2["message"]
        assert "Difference from stage 1" in info2["message"]
        assert tracker.stage2_estimate is not None

    def test_get_stage_info_stage_3(self, tracker):
        """Test get_stage_info for stage 3 with trend analysis"""
        tracker.start_sampling(level=0, total_tasks=100)

        # Simulate all 3 stages
        tracker.completed_tasks = 5
        time.sleep(0.01)
        tracker.get_stage_info(total_tasks=100, total_levels=3)

        tracker.completed_tasks = 10
        time.sleep(0.01)
        tracker.get_stage_info(total_tasks=100, total_levels=3)

        tracker.completed_tasks = 15
        time.sleep(0.01)
        info3 = tracker.get_stage_info(total_tasks=100, total_levels=3)

        assert info3["stage"] == 3
        assert "Stage 3 Sampling" in info3["message"]
        assert "FINAL ESTIMATED TOTAL TIME" in info3["message"]
        assert info3["should_stop_sampling"] is True
        assert tracker.images_per_second is not None
        assert "final_estimate_formatted" in info3

    def test_get_stage_info_not_at_threshold(self, tracker):
        """Test get_stage_info raises ValueError when not at threshold"""
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = 7  # Not a threshold

        with pytest.raises(ValueError, match="Not at a sampling stage threshold"):
            tracker.get_stage_info(total_tasks=100, total_levels=3)

    def test_get_stage_info_not_started(self, tracker):
        """Test get_stage_info raises ValueError when sampling not started"""
        tracker.is_sampling = True
        tracker.current_level = 0
        tracker.completed_tasks = 5
        tracker.sample_start_time = None  # Not started

        with pytest.raises(ValueError, match="Sampling not started"):
            tracker.get_stage_info(total_tasks=100, total_levels=3)

    def test_finalize_sampling(self, tracker):
        """Test finalize_sampling marks sampling as complete"""
        tracker.is_sampling = True
        tracker.finalize_sampling()

        assert tracker.is_sampling is False

    def test_get_performance_data_basic(self, tracker):
        """Test get_performance_data returns correct data"""
        tracker.completed_tasks = 10
        tracker.generated_count = 7
        tracker.loaded_count = 3
        tracker.images_per_second = 5.0
        tracker.stage1_estimate = 100.0

        data = tracker.get_performance_data()

        assert data["images_per_second"] == 5.0
        assert data["time_per_image"] == 0.2  # 1/5
        assert data["generation_ratio"] == 70.0  # 7/10 * 100
        assert data["generated_count"] == 7
        assert data["loaded_count"] == 3

    def test_get_performance_data_zero_completed(self, tracker):
        """Test get_performance_data with zero completed tasks"""
        data = tracker.get_performance_data()

        assert data["generation_ratio"] == 0.0
        assert data["generated_count"] == 0
        assert data["loaded_count"] == 0

    def test_get_performance_data_no_speed(self, tracker):
        """Test get_performance_data when speed is None"""
        tracker.images_per_second = None
        data = tracker.get_performance_data()

        assert data["time_per_image"] == 0.05  # Default fallback

    def test_estimate_storage_type_ssd(self, tracker):
        """Test storage type estimation for SSD"""
        storage = tracker._estimate_storage_type(15.0)
        assert storage == "SSD"

    def test_estimate_storage_type_hdd(self, tracker):
        """Test storage type estimation for HDD"""
        storage = tracker._estimate_storage_type(5.0)
        assert storage == "HDD"

    def test_estimate_storage_type_slow(self, tracker):
        """Test storage type estimation for slow storage"""
        storage = tracker._estimate_storage_type(1.0)
        assert storage == "Network/Slow"

    def test_estimate_storage_type_none(self, tracker):
        """Test storage type estimation with None"""
        storage = tracker._estimate_storage_type(None)
        assert storage == "Unknown"

    def test_format_final_estimate_seconds(self, tracker):
        """Test final estimate formatting for seconds"""
        result = tracker._format_final_estimate(45)
        assert result == "45s"

    def test_format_final_estimate_minutes(self, tracker):
        """Test final estimate formatting for minutes"""
        result = tracker._format_final_estimate(150)
        assert result == "2m 30s"

    def test_format_final_estimate_hours(self, tracker):
        """Test final estimate formatting for hours"""
        result = tracker._format_final_estimate(7200)
        assert result == "2h 0m"

    def test_format_final_estimate_hours_minutes(self, tracker):
        """Test final estimate formatting for hours and minutes"""
        result = tracker._format_final_estimate(7830)
        assert result == "2h 10m"

    @pytest.mark.parametrize(
        "sample_size,level_weight,expected_threshold",
        [
            (5, 1.0, 5),
            (10, 1.0, 10),
            (3, 0.25, 3),
        ],
    )
    def test_stage_thresholds_parametrized(self, sample_size, level_weight, expected_threshold):
        """Parametrized test for stage thresholds"""
        tracker = ThumbnailProgressTracker(sample_size=sample_size, level_weight=level_weight)
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.completed_tasks = expected_threshold

        assert tracker.should_log_stage() is True
        assert tracker.get_current_stage() == 1

    def test_reset_on_new_level(self, tracker):
        """Test that counters reset when starting new level"""
        # Complete some tasks
        tracker.start_sampling(level=0, total_tasks=100)
        tracker.on_task_completed(10, 100, was_generated=True)

        # Start new level
        tracker.start_sampling(level=1, total_tasks=50)

        assert tracker.completed_tasks == 0
        assert tracker.generated_count == 0
        assert tracker.loaded_count == 0
        assert tracker.current_level == 1
