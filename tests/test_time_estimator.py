"""
Tests for utils/time_estimator.py - Time estimation utilities

Part of Phase 2 quality improvement plan (devlog 072)
"""

import pytest

from utils.time_estimator import TimeEstimator


class TestTimeEstimator:
    """Test suite for TimeEstimator class"""

    @pytest.fixture
    def estimator(self):
        """Create a TimeEstimator instance for testing"""
        return TimeEstimator()

    def test_initialization_defaults(self):
        """Test TimeEstimator initialization with defaults"""
        estimator = TimeEstimator()

        assert estimator.stage_samples == {1: 5, 2: 10, 3: 20}
        assert estimator.level_reduction_factor == 0.25

    def test_initialization_custom_values(self):
        """Test TimeEstimator initialization with custom values"""
        custom_samples = {1: 10, 2: 20, 3: 30}
        estimator = TimeEstimator(stage_samples=custom_samples, level_reduction_factor=0.5)

        assert estimator.stage_samples == custom_samples
        assert estimator.level_reduction_factor == 0.5

    def test_calculate_eta_basic(self, estimator):
        """Test basic ETA calculation"""
        time_per_item, eta = estimator.calculate_eta(30.0, 100, 1000)

        assert time_per_item == 0.3  # 30 / 100
        assert eta == 270.0  # (1000 - 100) * 0.3

    def test_calculate_eta_zero_completed(self, estimator):
        """Test ETA calculation with zero completed items"""
        time_per_item, eta = estimator.calculate_eta(10.0, 0, 100)

        assert time_per_item == 0.0
        assert eta == 0.0

    def test_calculate_eta_all_completed(self, estimator):
        """Test ETA calculation when all items are completed"""
        time_per_item, eta = estimator.calculate_eta(100.0, 100, 100)

        assert time_per_item == 1.0  # 100 / 100
        assert eta == 0.0  # (100 - 100) * 1.0

    def test_format_duration_seconds(self, estimator):
        """Test duration formatting for values under 60 seconds"""
        assert estimator.format_duration(0) == "0.0s"
        assert estimator.format_duration(1.5) == "1.5s"
        assert estimator.format_duration(45.7) == "45.7s"
        assert estimator.format_duration(59.9) == "59.9s"

    def test_format_duration_minutes(self, estimator):
        """Test duration formatting for values under 1 hour"""
        assert estimator.format_duration(60) == "1.0m"
        assert estimator.format_duration(90) == "1.5m"
        assert estimator.format_duration(300) == "5.0m"
        assert estimator.format_duration(3599) == "60.0m"

    def test_format_duration_hours(self, estimator):
        """Test duration formatting for values over 1 hour"""
        assert estimator.format_duration(3600) == "1h"
        assert estimator.format_duration(3660) == "1h 1m"
        assert estimator.format_duration(7200) == "2h"
        assert estimator.format_duration(7320) == "2h 2m"
        # 3601 seconds = 1h 0m (minutes part is 0)
        assert estimator.format_duration(3601) == "1h"

    def test_format_duration_negative(self, estimator):
        """Test duration formatting with negative value"""
        assert estimator.format_duration(-10) == "0s"

    def test_estimate_multi_level_work_default(self, estimator):
        """Test multi-level work estimation with default levels"""
        estimates = estimator.estimate_multi_level_work(100.0, 3)

        assert len(estimates) == 3
        assert estimates[1] == 100.0
        assert estimates[2] == 25.0  # 100 * 0.25
        assert estimates[3] == 6.25  # 25 * 0.25

    def test_estimate_multi_level_work_single_level(self, estimator):
        """Test multi-level work estimation with single level"""
        estimates = estimator.estimate_multi_level_work(100.0, 1)

        assert len(estimates) == 1
        assert estimates[1] == 100.0

    def test_estimate_multi_level_work_many_levels(self, estimator):
        """Test multi-level work estimation with many levels"""
        estimates = estimator.estimate_multi_level_work(100.0, 5)

        assert len(estimates) == 5
        assert estimates[1] == 100.0
        assert estimates[2] == 25.0
        assert estimates[3] == 6.25
        assert estimates[4] == pytest.approx(1.5625)
        assert estimates[5] == pytest.approx(0.390625)

    def test_estimate_multi_level_work_custom_factor(self):
        """Test multi-level work estimation with custom reduction factor"""
        estimator = TimeEstimator(level_reduction_factor=0.5)
        estimates = estimator.estimate_multi_level_work(100.0, 3)

        assert estimates[1] == 100.0
        assert estimates[2] == 50.0  # 100 * 0.5
        assert estimates[3] == 25.0  # 50 * 0.5

    def test_calculate_total_multi_level_time(self, estimator):
        """Test calculation of total time for all levels"""
        total = estimator.calculate_total_multi_level_time(100.0, 3)

        # 100 + 25 + 6.25 = 131.25
        assert total == 131.25

    def test_calculate_total_multi_level_time_single_level(self, estimator):
        """Test total time calculation with single level"""
        total = estimator.calculate_total_multi_level_time(100.0, 1)

        assert total == 100.0

    def test_format_stage_estimate_basic(self, estimator):
        """Test complete stage estimate formatting"""
        result = estimator.format_stage_estimate(
            stage=1, elapsed=5.0, sample_size=5, total_items=100, num_levels=3
        )

        assert "time_per_image" in result
        assert "level_estimates" in result
        assert "level_estimates_formatted" in result
        assert "total_estimate" in result
        assert "total_estimate_formatted" in result

        # Check calculated values
        assert result["time_per_image"] == 1.0  # 5.0 / 5
        assert result["level_estimates"][1] == 100.0  # 100 * 1.0
        assert result["level_estimates"][2] == 25.0  # 100 * 0.25
        assert result["level_estimates"][3] == 6.25  # 25 * 0.25
        assert result["total_estimate"] == 131.25

    def test_format_stage_estimate_zero_sample_size(self, estimator):
        """Test stage estimate with zero sample size (fallback)"""
        result = estimator.format_stage_estimate(
            stage=1, elapsed=5.0, sample_size=0, total_items=100, num_levels=3
        )

        # Should use fallback time of 0.05
        assert result["time_per_image"] == 0.05

    def test_format_stage_estimate_formatted_strings(self, estimator):
        """Test that formatted strings are present and valid"""
        result = estimator.format_stage_estimate(
            stage=1, elapsed=10.0, sample_size=10, total_items=200, num_levels=2
        )

        # Check that all levels have formatted strings
        assert isinstance(result["level_estimates_formatted"][1], str)
        assert isinstance(result["level_estimates_formatted"][2], str)
        assert isinstance(result["total_estimate_formatted"], str)

        # Check format (should contain time units)
        assert (
            "m" in result["total_estimate_formatted"] or "s" in result["total_estimate_formatted"]
        )

    def test_format_progress_message(self, estimator):
        """Test progress message formatting"""
        estimate_info = {
            "time_per_image": 0.5,
            "level_estimates": {1: 50.0, 2: 12.5},
            "level_estimates_formatted": {1: "50.0s", 2: "12.5s"},
            "total_estimate": 62.5,
            "total_estimate_formatted": "1.0m",
        }

        message = estimator.format_progress_message(
            stage=1, completed=10, total=100, estimate_info=estimate_info
        )

        assert "Stage 1" in message
        assert "10/100" in message
        assert "1.0m" in message
        assert "complete" in message

    @pytest.mark.parametrize(
        "elapsed,completed,total,expected_time_per,expected_eta",
        [
            (10.0, 10, 100, 1.0, 90.0),
            (50.0, 100, 200, 0.5, 50.0),
            (100.0, 50, 100, 2.0, 100.0),
            (30.0, 150, 300, 0.2, 30.0),
        ],
    )
    def test_calculate_eta_parametrized(
        self, estimator, elapsed, completed, total, expected_time_per, expected_eta
    ):
        """Parametrized test for ETA calculation"""
        time_per_item, eta = estimator.calculate_eta(elapsed, completed, total)

        assert time_per_item == pytest.approx(expected_time_per)
        assert eta == pytest.approx(expected_eta)

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0.0s"),
            (30, "30.0s"),
            (60, "1.0m"),
            (150, "2.5m"),
            (3600, "1h"),
            (3660, "1h 1m"),
            (7200, "2h"),
        ],
    )
    def test_format_duration_parametrized(self, estimator, seconds, expected):
        """Parametrized test for duration formatting"""
        assert estimator.format_duration(seconds) == expected

    def test_stage_samples_attribute(self, estimator):
        """Test that stage_samples attribute is accessible"""
        assert hasattr(estimator, "stage_samples")
        assert isinstance(estimator.stage_samples, dict)
        assert 1 in estimator.stage_samples
        assert 2 in estimator.stage_samples
        assert 3 in estimator.stage_samples

    def test_level_reduction_factor_attribute(self, estimator):
        """Test that level_reduction_factor attribute is accessible"""
        assert hasattr(estimator, "level_reduction_factor")
        assert isinstance(estimator.level_reduction_factor, float)
        assert 0 < estimator.level_reduction_factor <= 1

    def test_immutability_of_default_stage_samples(self):
        """Test that modifying instance doesn't affect class defaults"""
        estimator1 = TimeEstimator()
        estimator1.stage_samples[1] = 999

        estimator2 = TimeEstimator()

        # Second instance should have original default values
        assert estimator2.stage_samples[1] == 5

    def test_estimate_multi_level_work_zero_base_time(self, estimator):
        """Test multi-level estimation with zero base time"""
        estimates = estimator.estimate_multi_level_work(0.0, 3)

        assert all(time == 0.0 for time in estimates.values())

    def test_calculate_total_multi_level_time_zero(self, estimator):
        """Test total time calculation with zero base time"""
        total = estimator.calculate_total_multi_level_time(0.0, 3)

        assert total == 0.0
