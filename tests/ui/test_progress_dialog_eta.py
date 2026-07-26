"""Characterization tests for ProgressDialog._calculate_eta.

Written *before* refactoring the method, which had no coverage at all: its whole
body was untested. These tests describe what it currently does rather than what
it arguably should, so that a refactor can be shown not to change behaviour.

The method blends three independent ETA estimates (overall average, trimmed
moving average, median velocity), applies rate-limited exponential smoothing,
and formats the result. Each is pinned separately below.

The clock is passed in as ``current_time``, and every other input is plain
instance state, so none of this needs a running event loop or real timing.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QWidget  # noqa: E402

from ui.dialogs.progress_dialog import ProgressDialog  # noqa: E402


@pytest.fixture
def dialog(qtbot):
    """A ProgressDialog with a known, fully-specified ETA state.

    setup_unified_progress() is not used: it stamps the clock, and these tests
    need every input pinned.
    """
    # ProgressDialog positions itself relative to its parent, so it needs a real
    # widget rather than None.
    parent = QWidget()
    qtbot.addWidget(parent)
    dlg = ProgressDialog(parent)
    qtbot.addWidget(dlg)

    dlg.total_steps = 100
    dlg.current_step = 10
    dlg.start_time = 1000.0
    dlg.last_eta_update = 0
    dlg.smoothed_eta = None
    dlg.step_times.clear()
    dlg.velocity_history.clear()
    dlg.step_history = []
    return dlg


@pytest.mark.ui
class TestCalculateEtaEarlyReturns:
    """Cases where no estimate is produced."""

    def test_returns_none_when_work_is_complete(self, dialog):
        dialog.current_step = dialog.total_steps

        assert dialog._calculate_eta(1010.0) is None

    def test_returns_none_when_work_is_over_complete(self, dialog):
        dialog.current_step = dialog.total_steps + 5

        assert dialog._calculate_eta(1010.0) is None

    def test_returns_none_with_no_progress_and_no_history(self, dialog):
        """No elapsed-average, no samples, no velocity: nothing to average."""
        dialog.current_step = 0

        assert dialog._calculate_eta(1010.0) is None


@pytest.mark.ui
class TestCalculateEtaThrottling:
    """The method refuses to recompute more than once per eta_update_interval."""

    def test_within_the_interval_it_reuses_the_smoothed_value(self, dialog):
        dialog.last_eta_update = 1000.0
        dialog.smoothed_eta = 90.0

        # 0.5s later, inside the 1.0s interval
        assert dialog._calculate_eta(1000.5) == "1m 30s"

    def test_within_the_interval_it_does_not_advance_the_clock(self, dialog):
        dialog.last_eta_update = 1000.0
        dialog.smoothed_eta = 90.0

        dialog._calculate_eta(1000.5)

        assert dialog.last_eta_update == 1000.0

    def test_within_the_interval_with_no_previous_value_returns_none(self, dialog):
        dialog.last_eta_update = 1000.0
        dialog.smoothed_eta = None

        assert dialog._calculate_eta(1000.5) is None

    def test_outside_the_interval_it_recomputes_and_stamps(self, dialog):
        dialog.last_eta_update = 1000.0

        dialog._calculate_eta(1002.0)

        assert dialog.last_eta_update == 1002.0


@pytest.mark.ui
class TestCalculateEtaEstimation:
    """The estimate itself, with only one method contributing at a time."""

    def test_overall_average_alone(self, dialog):
        """10 of 100 steps in 10s -> 1s/step -> 90s remaining.

        Only the overall-average method has data, so it is the whole estimate
        and the first smoothed value is taken as-is.
        """
        result = dialog._calculate_eta(1010.0)

        assert dialog.smoothed_eta == pytest.approx(90.0)
        assert result == "1m 30s"

    def test_moving_average_joins_once_there_are_enough_samples(self, dialog):
        """min_samples_for_eta step times pull the estimate toward their mean."""
        dialog.step_times.extend([2.0] * dialog.min_samples_for_eta)

        dialog._calculate_eta(1010.0)

        # overall says 90 (weight .5), trimmed mean of 2.0 x 90 steps = 180 (weight .3)
        expected = (90.0 * 0.5 + 180.0 * 0.3) / 0.8
        assert dialog.smoothed_eta == pytest.approx(expected)

    def test_velocity_joins_once_there_are_five_samples(self, dialog):
        """Median velocity of 5 samples contributes at weight 0.2."""
        dialog.velocity_history.extend([2.0] * 5)

        dialog._calculate_eta(1010.0)

        # overall 90 (weight .5), velocity 90/2.0 = 45 (weight .2)
        expected = (90.0 * 0.5 + 45.0 * 0.2) / 0.7
        assert dialog.smoothed_eta == pytest.approx(expected)

    def test_velocity_is_derived_from_the_last_two_history_entries(self, dialog):
        """step_history feeds velocity_history one sample per call."""
        dialog.step_history = [(1000.0, 0), (1005.0, 10)]

        dialog._calculate_eta(1010.0)

        assert list(dialog.velocity_history) == [pytest.approx(2.0)]

    def test_zero_median_velocity_contributes_nothing(self, dialog):
        """A stalled velocity history must not divide by zero."""
        dialog.velocity_history.extend([0.0] * 5)

        dialog._calculate_eta(1010.0)

        # Only the overall average survives, so the estimate is its raw value.
        assert dialog.smoothed_eta == pytest.approx(90.0)

    def test_non_advancing_history_contributes_no_velocity(self, dialog):
        dialog.step_history = [(1005.0, 10), (1005.0, 10)]

        dialog._calculate_eta(1010.0)

        assert list(dialog.velocity_history) == []


@pytest.mark.ui
class TestCalculateEtaSmoothing:
    """Successive estimates are rate-limited, not jumped to."""

    def test_first_estimate_is_adopted_directly(self, dialog):
        dialog._calculate_eta(1010.0)

        assert dialog.smoothed_eta == pytest.approx(90.0)

    def test_a_large_jump_is_capped_at_20_percent_then_damped_by_ema(self, dialog):
        """Change is clamped to +-20% of the current value, then scaled by ema_alpha."""
        dialog.smoothed_eta = 100.0
        dialog.last_eta_update = 0

        dialog._calculate_eta(1010.0)  # raw estimate 90 -> change -10, under the 20 cap

        assert dialog.smoothed_eta == pytest.approx(100.0 + dialog.ema_alpha * -10.0)

    def test_the_cap_binds_when_the_estimate_moves_far(self, dialog):
        """Raw estimate 90 against a smoothed 1000 is a -910 change, capped to -200."""
        dialog.smoothed_eta = 1000.0
        dialog.last_eta_update = 0

        dialog._calculate_eta(1010.0)

        assert dialog.smoothed_eta == pytest.approx(1000.0 + dialog.ema_alpha * -200.0)


@pytest.mark.ui
class TestCalculateEtaFormatting:
    """Output formatting, pinned at each boundary."""

    @pytest.mark.parametrize(
        "smoothed,expected",
        [
            (45.0, "45s"),
            (59.9, "59s"),
            (60.0, "1m 0s"),
            (90.0, "1m 30s"),
            (3599.0, "59m 59s"),
            (3600.0, "1h 0m"),
            (7350.0, "2h 2m"),
        ],
    )
    def test_formats(self, dialog, smoothed, expected):
        """Exercised through the throttled path, which formats without recomputing."""
        dialog.last_eta_update = 1000.0
        dialog.smoothed_eta = smoothed

        assert dialog._calculate_eta(1000.5) == expected

    def test_the_recomputing_path_formats_hours_too(self, dialog):
        """The throttled and recomputing branches each format independently.

        The other formatting cases above go through the throttled branch; this
        one goes through the recompute branch, which has its own copy of the
        same three-way format.
        """
        dialog.current_step = 1
        dialog.total_steps = 10000
        dialog.start_time = 1000.0

        # 1 step in 10s, 9999 remaining -> ~99990s -> 27h
        assert dialog._calculate_eta(1010.0) == "27h 46m"

    def test_a_smoothed_eta_of_exactly_zero_returns_nothing(self, dialog):
        """Characterizes a quirk, not an endorsement.

        The throttled branch guards with `if self.smoothed_eta:` -- a truthiness
        test -- so a value of exactly 0.0 is indistinguishable from None and the
        caller is told there is no estimate rather than "0s". Reachable whenever
        the smoothed estimate lands on zero between recomputations.
        """
        dialog.last_eta_update = 1000.0
        dialog.smoothed_eta = 0.0

        assert dialog._calculate_eta(1000.5) is None

    def test_a_negative_smoothed_value_clamps_to_zero(self, dialog):
        dialog.last_eta_update = 0
        dialog.smoothed_eta = -5.0
        dialog.current_step = 0  # no estimate, so the stored value is formatted

        # -5 is falsy-safe but negative; max(0, ...) is applied before formatting
        dialog.smoothed_eta = -5.0
        dialog.last_eta_update = 1000.0
        assert dialog._calculate_eta(1000.5) == "0s"
