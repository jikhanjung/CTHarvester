"""Automatic initial threshold and ROI detection.

Once the thumbnail pyramid is built, the smallest level is already a complete,
in-memory representation of the whole scan -- typically a few hundred KB. That
makes it cheap to look at the data before the user does anything, and propose
the two settings they would otherwise dial in by hand: an intensity threshold
separating specimen from air, and the region of interest that actually contains
the specimen.

The functions here are deliberately free of Qt and of any window state. They
take a volume and return normalised numbers; mapping those onto a particular
pyramid level's pixel coordinates is the caller's job, because the level in view
can change after detection runs.

Created for the auto-setup feature (devlog 102).
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# The threshold lives in 8-bit space everywhere downstream: object_viewer_2d
# validates `IMAGE_8BIT_MIN <= threshold <= IMAGE_8BIT_MAX` before rendering, and
# the mesh generator compares against it directly. Volumes may be 16-bit, so
# detection scales into this space rather than the volume's own range.
HISTOGRAM_BINS = 256

# Guards. Detection is a convenience; when the data does not clearly separate,
# leaving the existing defaults alone beats confidently proposing nonsense.
MIN_FOREGROUND_FRACTION = 0.001  # below this the "specimen" is probably noise
MAX_FOREGROUND_FRACTION = 0.95  # above this the threshold is not separating anything
MIN_SEPARABILITY = 0.2  # Otsu's eta; near-zero means a unimodal histogram

# Padding added around the detected bounding box, as a fraction of its size, so
# a slightly-too-tight threshold does not clip the specimen's edges.
DEFAULT_MARGIN = 0.05

# A row, column or slice counts as occupied only once this share of it is
# foreground. Plain `mask.any()` is far too eager: a single noise voxel that
# crosses the threshold anywhere drags the bounds out to the full frame, which
# is exactly what a 16-bit scan produces once the histogram rounding at the
# tails is taken into account.
OCCUPANCY_FRACTION = 0.001

# If the proposal ends up covering essentially the whole volume, there was
# nothing to find. Judging the outcome is far more reliable than trying to
# characterise the histogram: Otsu happily splits a unimodal Gaussian with a
# respectable separability score, and only the resulting full-frame ROI gives
# that away.
TRIVIAL_COVERAGE = 0.98


@dataclass(frozen=True)
class AutoSetupResult:
    """Detected initial settings, in units independent of any pyramid level.

    Attributes:
        threshold: Intensity threshold in 8-bit space (0-255), directly usable as
            the threshold slider value.
        roi: (x1, y1, x2, y2) as fractions of image width/height in [0, 1].
        z_range: (lower, upper) as fractions of the slice count in [0, 1],
            inclusive of both ends.
        foreground_fraction: Share of voxels above the threshold. Reported for
            logging and the status line, not used for decisions.
        separability: Otsu's eta for the chosen threshold, in [0, 1]. 1.0 is a
            perfectly bimodal histogram.
    """

    threshold: int
    roi: tuple[float, float, float, float]
    z_range: tuple[float, float]
    foreground_fraction: float
    separability: float

    def roi_coverage(self) -> float:
        """Fraction of the frame area the ROI covers, for display."""
        x1, y1, x2, y2 = self.roi
        return max(0.0, (x2 - x1)) * max(0.0, (y2 - y1))


def to_8bit_histogram(volume: np.ndarray) -> np.ndarray:
    """Build a 256-bin histogram of a volume in 8-bit intensity space.

    Args:
        volume: 3D array (Z, Y, X). Integer dtypes are scaled by their type's
            full range, matching how the viewer downconverts for display;
            floating point is scaled by the observed min/max.

    Returns:
        Array of 256 counts.
    """
    if volume.dtype == np.uint8:
        scaled = volume
    elif np.issubdtype(volume.dtype, np.integer):
        # Scale by the dtype range, not the observed range: the display pipeline
        # does the same, so a threshold picked here means the same thing there.
        type_max = float(np.iinfo(volume.dtype).max)
        scaled = np.clip(volume.astype(np.float64) * 255.0 / type_max, 0, 255).astype(np.uint8)
    else:
        v_min = float(volume.min())
        v_max = float(volume.max())
        if v_max <= v_min:
            return np.zeros(HISTOGRAM_BINS, dtype=np.int64)
        normalised = (volume.astype(np.float64) - v_min) * 255.0 / (v_max - v_min)
        scaled = np.clip(normalised, 0, 255).astype(np.uint8)

    return np.bincount(scaled.ravel(), minlength=HISTOGRAM_BINS).astype(np.int64)


def otsu_threshold(histogram: np.ndarray) -> tuple[int, float] | None:
    """Find the threshold maximising between-class variance (Otsu's method).

    Args:
        histogram: 256 bin counts, as produced by :func:`to_8bit_histogram`.

    Returns:
        ``(threshold, separability)``, where separability is Otsu's eta -- the
        share of total variance explained by the split, in [0, 1]. Returns None
        for an empty or single-valued histogram, where no split exists.
    """
    total = histogram.sum()
    if total == 0:
        return None

    levels = np.arange(HISTOGRAM_BINS, dtype=np.float64)
    counts = histogram.astype(np.float64)

    weight_below = np.cumsum(counts)
    weight_above = total - weight_below

    # A split is only meaningful where both sides are non-empty.
    splittable = (weight_below > 0) & (weight_above > 0)
    if not splittable.any():
        return None

    weighted = levels * counts
    sum_total = weighted.sum()
    sum_below = np.cumsum(weighted)

    mean_below = np.divide(sum_below, weight_below, out=np.zeros_like(sum_below), where=splittable)
    mean_above = np.divide(
        sum_total - sum_below, weight_above, out=np.zeros_like(sum_below), where=splittable
    )

    between_variance = weight_below * weight_above * (mean_below - mean_above) ** 2
    between_variance[~splittable] = -1.0

    # With a gap between the two modes every threshold inside it scores
    # identically, and argmax would return the lowest -- putting the threshold
    # flush against the darker mode, where a little noise flips voxels across
    # it. The middle of the tied run sits in the valley instead.
    best = between_variance.max()
    tied = np.flatnonzero(np.isclose(between_variance, best, rtol=1e-9))
    threshold = int(tied[len(tied) // 2])

    # eta = between-class variance / total variance, both scaled by total^2 so
    # the ratio is dimensionless. A unimodal histogram scores near zero.
    global_mean = sum_total / total
    total_variance = (counts * (levels - global_mean) ** 2).sum() * total
    separability = (
        float(between_variance[threshold] / total_variance) if total_variance > 0 else 0.0
    )

    return threshold, separability


def threshold_in_volume_scale(threshold: int, volume: np.ndarray) -> float:
    """Convert an 8-bit threshold back into the volume's own intensity scale.

    The threshold is chosen on a histogram scaled to 0-255 so that it means the
    same thing as the slider value the user sees. Masking has to happen in the
    volume's native units, which for a 16-bit scan is a different number.

    Args:
        threshold: Threshold in 8-bit space (0-255).
        volume: The volume the threshold will be compared against.

    Returns:
        The equivalent threshold in the volume's dtype scale. Float volumes are
        returned unchanged, matching :func:`to_8bit_histogram`'s min/max
        normalisation only when they already span 0-255; they are rare here and
        the caller treats a miss as "no proposal" via the coverage guards.
    """
    if volume.dtype == np.uint8 or not np.issubdtype(volume.dtype, np.integer):
        return float(threshold)
    return threshold * float(np.iinfo(volume.dtype).max) / 255.0


def _occupied_span(counts: np.ndarray, extent: int, margin: float) -> tuple[float, float] | None:
    """First and last occupied index along one axis, padded, as [0, 1] fractions.

    Args:
        counts: Foreground voxel count per position along the axis.
        extent: Size of the cross-section each count was taken over, used to
            turn ``OCCUPANCY_FRACTION`` into an absolute count.
        margin: Padding as a fraction of the detected span.

    Returns:
        ``(low, high)`` fractions, or None if nothing along the axis is occupied.
    """
    # At least one voxel, so a genuinely thin specimen is not thresholded away.
    minimum = max(1, int(extent * OCCUPANCY_FRACTION))
    occupied = np.flatnonzero(counts >= minimum)
    if occupied.size == 0:
        return None

    low, high = int(occupied[0]), int(occupied[-1]) + 1
    pad = (high - low) * margin
    return max(0.0, (low - pad) / len(counts)), min(1.0, (high + pad) / len(counts))


def detect_initial_settings(
    volume: np.ndarray, margin: float = DEFAULT_MARGIN
) -> AutoSetupResult | None:
    """Propose an initial threshold, ROI and slice range from a small volume.

    Intended to run on the smallest pyramid level right after generation.

    Args:
        volume: 3D array (Z, Y, X), any integer or float dtype.
        margin: Padding around the detected bounds, as a fraction of their size.

    Returns:
        An :class:`AutoSetupResult`, or None when the data does not separate
        clearly enough to propose anything. None is a normal outcome, not an
        error: the caller should leave existing defaults in place.
    """
    if volume is None or not isinstance(volume, np.ndarray):
        logger.debug("Auto-setup skipped: no volume")
        return None

    if volume.ndim != 3 or volume.size == 0:
        logger.debug(
            f"Auto-setup skipped: expected a non-empty 3D volume, got shape {volume.shape}"
        )
        return None

    otsu = otsu_threshold(to_8bit_histogram(volume))
    if otsu is None:
        logger.debug("Auto-setup skipped: histogram has no valid split")
        return None

    threshold, separability = otsu
    if separability < MIN_SEPARABILITY:
        logger.info(
            f"Auto-setup skipped: histogram is not clearly bimodal "
            f"(separability {separability:.3f} < {MIN_SEPARABILITY})"
        )
        return None

    mask = volume > threshold_in_volume_scale(threshold, volume)

    foreground_fraction = float(mask.sum()) / mask.size
    if not MIN_FOREGROUND_FRACTION <= foreground_fraction <= MAX_FOREGROUND_FRACTION:
        logger.info(
            f"Auto-setup skipped: {foreground_fraction:.1%} of voxels above the "
            f"threshold, outside the usable "
            f"{MIN_FOREGROUND_FRACTION:.1%}-{MAX_FOREGROUND_FRACTION:.0%} range"
        )
        return None

    depth, height, width = mask.shape

    # Each axis is reduced to counts over the whole volume, so the bounds ignore
    # isolated voxels rather than being defined by them. Counting the cross
    # section rather than a flattened footprint matters: projecting with any()
    # first would let one stray voxel anywhere in the stack mark a column as
    # occupied, which is the failure mode this is here to prevent. Summing over
    # z also keeps the box covering the specimen at every slice.
    z_range = _occupied_span(mask.sum(axis=(1, 2)), height * width, margin)
    x_span = _occupied_span(mask.sum(axis=(0, 1)), depth * height, margin)
    y_span = _occupied_span(mask.sum(axis=(0, 2)), depth * width, margin)

    if z_range is None or x_span is None or y_span is None:
        logger.info("Auto-setup skipped: foreground is too sparse to bound")
        return None

    roi = (x_span[0], y_span[0], x_span[1], y_span[1])

    result = AutoSetupResult(
        threshold=threshold,
        roi=roi,
        z_range=z_range,
        foreground_fraction=foreground_fraction,
        separability=separability,
    )

    # Nothing worth applying if the proposal is the whole volume. This is the
    # guard that actually catches unstructured data; the separability check
    # above lets a unimodal Gaussian through.
    z_coverage = z_range[1] - z_range[0]
    if result.roi_coverage() >= TRIVIAL_COVERAGE and z_coverage >= TRIVIAL_COVERAGE:
        logger.info(
            f"Auto-setup skipped: proposal covers the whole volume "
            f"({result.roi_coverage():.0%} of frame, {z_coverage:.0%} of slices) "
            f"- nothing to narrow down"
        )
        return None
    logger.info(
        f"Auto-setup: threshold={threshold} (separability {separability:.2f}), "
        f"ROI covers {result.roi_coverage():.0%} of the frame, "
        f"z {z_range[0]:.2f}-{z_range[1]:.2f}, foreground {foreground_fraction:.1%}"
    )
    return result
