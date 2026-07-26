"""Tests for core/auto_setup.py — automatic threshold and ROI detection."""

import numpy as np
import pytest

from core.auto_setup import (
    HISTOGRAM_BINS,
    AutoSetupResult,
    detect_initial_settings,
    otsu_threshold,
    threshold_in_volume_scale,
    to_8bit_histogram,
)


def synthetic_scan(dtype=np.uint8, background=30, foreground=200, seed=0):
    """A 60x100x100 scan: noisy background with a bright cylinder in the middle.

    The cylinder spans x/y 28-72 and z 11-44, so a correct detection lands near
    roi (0.27, 0.27, 0.74, 0.74) and z (0.15, 0.78) once the 5% margin is added.
    """
    rng = np.random.default_rng(seed)
    type_max = np.iinfo(dtype).max
    volume = rng.normal(background, background * 0.25, (60, 100, 100))
    volume = volume.clip(0, type_max).astype(dtype)

    zz, yy, xx = np.ogrid[:60, :100, :100]
    specimen = ((yy - 50) ** 2 + (xx - 50) ** 2 < 22**2) & (zz > 10) & (zz < 45)
    volume[specimen] = (
        rng.normal(foreground, foreground * 0.05, specimen.sum()).clip(0, type_max).astype(dtype)
    )
    return volume


@pytest.mark.unit
class TestToEightBitHistogram:
    """Tests for to_8bit_histogram()."""

    def test_uint8_is_counted_directly(self):
        volume = np.full((2, 3, 4), 7, dtype=np.uint8)
        hist = to_8bit_histogram(volume)

        assert hist.shape == (HISTOGRAM_BINS,)
        assert hist[7] == 24
        assert hist.sum() == 24

    def test_uint16_is_scaled_by_the_dtype_range(self):
        """A 16-bit value maps to the 8-bit bin the display would show it in."""
        volume = np.full((2, 2, 2), 32768, dtype=np.uint16)
        hist = to_8bit_histogram(volume)

        # 32768/65535 * 255 = 127.5 -> bin 127 after truncation
        assert hist[127] == 8

    def test_float_is_normalised_by_observed_range(self):
        volume = np.linspace(-1.0, 1.0, 8, dtype=np.float64).reshape(2, 2, 2)
        hist = to_8bit_histogram(volume)

        assert hist.sum() == 8
        assert hist[0] == 1  # the minimum maps to bin 0
        assert hist[255] == 1  # the maximum maps to bin 255

    def test_constant_float_volume_yields_empty_histogram(self):
        """No range to normalise over; callers treat this as 'no proposal'."""
        hist = to_8bit_histogram(np.full((2, 2, 2), 0.5, dtype=np.float64))

        assert hist.sum() == 0


@pytest.mark.unit
class TestOtsuThreshold:
    """Tests for otsu_threshold()."""

    def test_splits_a_bimodal_histogram_between_the_modes(self):
        hist = np.zeros(HISTOGRAM_BINS, dtype=np.int64)
        hist[20] = 1000
        hist[200] = 1000

        threshold, separability = otsu_threshold(hist)

        assert 20 <= threshold < 200
        assert separability == pytest.approx(1.0, abs=0.01)

    def test_ties_resolve_to_the_middle_of_the_valley(self):
        """Every threshold in the gap scores identically; argmax would pick the
        lowest, leaving it flush against the darker mode where noise flips
        voxels across it."""
        hist = np.zeros(HISTOGRAM_BINS, dtype=np.int64)
        hist[20] = 1000
        hist[200] = 1000

        threshold, _ = otsu_threshold(hist)

        assert threshold == pytest.approx(110, abs=5)

    def test_separability_is_low_for_a_unimodal_histogram(self):
        """A single Gaussian still gets split, but explains little variance."""
        levels = np.arange(HISTOGRAM_BINS)
        hist = (1000 * np.exp(-((levels - 128) ** 2) / (2 * 20**2))).astype(np.int64)

        _, separability = otsu_threshold(hist)

        assert separability < 0.8

    def test_empty_histogram_returns_none(self):
        assert otsu_threshold(np.zeros(HISTOGRAM_BINS, dtype=np.int64)) is None

    def test_single_populated_bin_returns_none(self):
        """One value means there is no split with both sides non-empty."""
        hist = np.zeros(HISTOGRAM_BINS, dtype=np.int64)
        hist[42] = 500

        assert otsu_threshold(hist) is None


@pytest.mark.unit
class TestThresholdInVolumeScale:
    """Tests for threshold_in_volume_scale()."""

    def test_uint8_is_unchanged(self):
        assert threshold_in_volume_scale(65, np.zeros(1, dtype=np.uint8)) == 65

    def test_uint16_is_scaled_up(self):
        result = threshold_in_volume_scale(128, np.zeros(1, dtype=np.uint16))

        assert result == pytest.approx(128 * 65535 / 255)

    def test_float_is_unchanged(self):
        assert threshold_in_volume_scale(100, np.zeros(1, dtype=np.float32)) == 100.0


@pytest.mark.unit
class TestDetectInitialSettings:
    """Tests for detect_initial_settings()."""

    def test_finds_the_specimen(self):
        result = detect_initial_settings(synthetic_scan())

        assert result is not None
        assert 30 < result.threshold < 200, "threshold should separate background from specimen"

        x1, y1, x2, y2 = result.roi
        assert x1 == pytest.approx(0.27, abs=0.05)
        assert y1 == pytest.approx(0.27, abs=0.05)
        assert x2 == pytest.approx(0.74, abs=0.05)
        assert y2 == pytest.approx(0.74, abs=0.05)

        z_lo, z_hi = result.z_range
        assert z_lo == pytest.approx(0.15, abs=0.05)
        assert z_hi == pytest.approx(0.78, abs=0.05)

    def test_16bit_agrees_with_8bit(self):
        """The threshold is reported in slider space, so bit depth must not change it."""
        eight = detect_initial_settings(synthetic_scan(np.uint8, 30, 200))
        sixteen = detect_initial_settings(synthetic_scan(np.uint16, 30 * 257, 200 * 257))

        assert eight is not None and sixteen is not None
        assert eight.threshold == sixteen.threshold
        assert eight.roi == pytest.approx(sixteen.roi, abs=0.02)
        assert eight.z_range == pytest.approx(sixteen.z_range, abs=0.02)

    def test_roi_is_within_bounds(self):
        result = detect_initial_settings(synthetic_scan())

        assert all(0.0 <= v <= 1.0 for v in result.roi)
        assert all(0.0 <= v <= 1.0 for v in result.z_range)
        assert result.roi[0] < result.roi[2]
        assert result.roi[1] < result.roi[3]
        assert result.z_range[0] < result.z_range[1]

    def test_larger_margin_widens_the_proposal(self):
        tight = detect_initial_settings(synthetic_scan(), margin=0.0)
        loose = detect_initial_settings(synthetic_scan(), margin=0.2)

        assert loose.roi[0] < tight.roi[0]
        assert loose.roi[2] > tight.roi[2]
        assert loose.roi_coverage() > tight.roi_coverage()

    def test_a_single_stray_voxel_does_not_widen_the_bounds(self):
        """The bounds come from per-slice counts, not from `any()`.

        A lone voxel over the threshold in a corner of slice 0 used to drag the
        ROI and z-range out to the full volume. 16-bit scans produce exactly
        this via rounding at the histogram tails.
        """
        volume = synthetic_scan()
        clean = detect_initial_settings(volume)

        volume[0, 0, 0] = 255
        with_stray = detect_initial_settings(volume)

        assert with_stray.z_range == pytest.approx(clean.z_range, abs=0.01)
        assert with_stray.roi == pytest.approx(clean.roi, abs=0.01)


@pytest.mark.unit
class TestDetectInitialSettingsGuards:
    """detect_initial_settings() returns None rather than proposing nonsense."""

    def test_none_volume(self):
        assert detect_initial_settings(None) is None

    def test_empty_volume(self):
        assert detect_initial_settings(np.array([])) is None

    def test_two_dimensional_input(self):
        assert detect_initial_settings(np.zeros((10, 10), dtype=np.uint8)) is None

    def test_uniform_volume(self):
        assert detect_initial_settings(np.full((10, 10, 10), 42, dtype=np.uint8)) is None

    def test_unstructured_noise(self):
        """Otsu splits a unimodal Gaussian happily; the coverage guard catches it."""
        noise = np.random.default_rng(1).normal(128, 20, (20, 40, 40))

        assert detect_initial_settings(noise.clip(0, 255).astype(np.uint8)) is None

    def test_nearly_all_foreground(self):
        """A bright volume with a few dark voxels has no useful threshold."""
        volume = np.full((20, 40, 40), 240, dtype=np.uint8)
        volume[0, 0, 0] = 5

        assert detect_initial_settings(volume) is None


@pytest.mark.unit
class TestAutoSetupResult:
    """Tests for the result container."""

    def test_roi_coverage_is_the_area_fraction(self):
        result = AutoSetupResult(
            threshold=100,
            roi=(0.25, 0.0, 0.75, 0.5),
            z_range=(0.0, 1.0),
            foreground_fraction=0.1,
            separability=0.9,
        )

        assert result.roi_coverage() == pytest.approx(0.25)

    def test_roi_coverage_is_never_negative(self):
        result = AutoSetupResult(
            threshold=100,
            roi=(0.75, 0.75, 0.25, 0.25),
            z_range=(0.0, 1.0),
            foreground_fraction=0.1,
            separability=0.9,
        )

        assert result.roi_coverage() == 0.0
