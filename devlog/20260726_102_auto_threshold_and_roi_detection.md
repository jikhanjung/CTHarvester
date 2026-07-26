# Devlog 102: Automatic Threshold and ROI Detection — Seeding Initial Settings from the Pyramid

**Date:** 2026-07-26
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Complete
**Previous:** [devlog 101 - Ruff Migration and CI Recovery](./20260726_101_ruff_migration_and_ci_recovery.md)

---

## 🎯 Overview

Feature request: once the thumbnail pyramid finishes, use the smallest level to
detect a sensible intensity threshold and propose a region of interest, so the
user starts from something close to what they want instead of from the defaults.

The timing makes this nearly free. When generation completes, the smallest level
is already in memory as `minimum_volume` — a complete representation of the whole
scan in a few hundred KB. Detection is one pass over it, with no extra I/O.

Two settings were seeded before this change and both were guesses: the threshold
slider started at a hardcoded 60, and the ROI at the full frame with the full
slice range.

**Decisions taken up front** (both confirmed with the requester):

- **Apply directly as initial values**, rather than showing a confirmation
  dialog. The existing Reset button already restores the full frame, so the
  proposal is trivially undoable, and a dialog on every directory open would be
  a click to dismiss far more often than a click to accept.
- **Threshold + XY ROI + Z slice range**, all three. They fall out of the same
  mask, so covering all three costs nothing beyond covering one, and the slice
  range is the most tedious of the three to set by hand.

---

## 🔧 Implementation

### `core/auto_setup.py` — detection, free of Qt

The module takes a volume and returns numbers. It deliberately knows nothing
about windows or widgets, and returns the ROI and slice range as **fractions in
[0, 1]** rather than pixels: detection runs on the smallest pyramid level, while
the viewer displays whichever level is selected, so the caller does the mapping
at apply time.

```python
@dataclass(frozen=True)
class AutoSetupResult:
    threshold: int                              # 0-255, slider space
    roi: tuple[float, float, float, float]      # x1, y1, x2, y2 as fractions
    z_range: tuple[float, float]                # lower, upper as fractions
    foreground_fraction: float
    separability: float
```

**Threshold — Otsu's method** on a 256-bin histogram. The 8-bit space is not a
choice: `object_viewer_2d` validates `IMAGE_8BIT_MIN <= threshold <=
IMAGE_8BIT_MAX` before rendering and the mesh generator compares against the
same number, so the threshold must mean the same thing the slider means. 16-bit
volumes are scaled into that space for the histogram, and the chosen threshold
is scaled back to the volume's own units for masking.

**ROI and slice range** — the bounding box of the thresholded mask, padded by a
margin (5% of the detected span) so a slightly-too-tight threshold does not clip
the specimen's edges.

### Wiring

`ObjectViewer2D.set_roi_from_fractions()` converts to the displayed level's
pixel coordinates, mirroring the existing `set_full_roi()`.

`ThumbnailCreationHandler._apply_auto_setup()` runs after the level combo is
populated and selected — the ROI needs the displayed image to exist — and before
the 3D view is built, so the mesh renders at the detected threshold rather than
the default. Both the Rust and Python generation paths call it.

The threshold slider's `valueChanged` signal already propagates the isovalue to
the 2D viewer and the mesh widget, so setting the slider is the whole story
there.

The status line reports what happened:

```
Auto-detected: threshold 87, ROI 62% of frame, slices 14-233
```

It is written after `update_status()`, which would otherwise overwrite it, and
survives until the user touches anything — which is exactly as long as it is
useful.

---

## 🐛 Two defects the tests caught

Both were found by running detection against synthetic scans in 8-bit and 16-bit
and comparing, not by reading the code.

### A single stray voxel dragged the bounds to the full frame

The first implementation took bounds from `mask.any(axis=...)`. That is far too
eager: one voxel anywhere over the threshold marks its whole row, column or
slice as occupied.

It showed up as the 16-bit and 8-bit results disagreeing on an otherwise
identical scan:

| | z_range (8-bit) | z_range (16-bit) |
|---|---|---|
| before | (0.15, 0.78) | **(0.01, 0.79)** |
| after | (0.15, 0.78) | (0.15, 0.78) |

The cause is rounding in the histogram tails: scaling 16-bit values into 256 bins
puts a handful of background voxels on the wrong side of the threshold, and
`any()` promoted them to bounds.

Bounds now come from **counts over the whole volume** per position along each
axis, with a position counting as occupied only above `OCCUPANCY_FRACTION`
(0.1%) of its cross-section. Counting the cross-section rather than a flattened
footprint matters — projecting with `any()` first and counting after would let
one stray voxel anywhere in the stack mark a column as occupied, which is the
failure mode being fixed.

A regression test pins it: inject a lone bright voxel at `[0, 0, 0]` and the
bounds must not move.

### Otsu happily splits pure noise

Unstructured Gaussian noise produced a confident-looking proposal, with
separability (Otsu's η) of **0.64** — well above any threshold that would still
accept real data. Trying to characterise the histogram is the wrong approach
here: Otsu always finds *a* split, and a unimodal distribution scores
respectably.

The reliable signal is the **outcome**. Noise produces an ROI covering the whole
frame and a slice range covering everything — a proposal identical to the
defaults. The guard now rejects on that, and it catches the case cleanly.

The separability check is kept as a cheap first filter, but it is not what makes
this work.

### Also: threshold ties resolve to the valley, not its edge

With a gap between the two modes, every threshold inside the gap scores
identically, and `np.argmax` returns the lowest — putting the threshold flush
against the darker mode, where a little noise flips voxels across it. Ties now
resolve to the middle of the tied run. For a histogram with spikes at 20 and 200
that moves the threshold from 20 to ~110.

Noticed because a wiring test asserted `20 < threshold` and got exactly 20. The
original answer was not *wrong* — `volume > 20` does separate that data — but it
sat on the boundary by construction.

---

## 🚦 When it declines

Detection returning None is a normal outcome, not an error; the caller leaves the
existing defaults in place. It declines when:

| Condition | Reason |
|---|---|
| No volume / not 3D / empty | Nothing to analyse |
| Histogram has no valid split | Single-valued volume |
| Separability < 0.2 | Clearly unimodal |
| Foreground outside 0.1%–95% | Threshold is not separating anything |
| Foreground too sparse to bound | No axis has an occupied span |
| ROI and Z both ≥ 98% coverage | Proposal equals the defaults |

The apply step is equally defensive: a non-array `minimum_volume` (the failure
paths set it to a plain list) is skipped, and if the viewer has no image yet the
threshold is still applied and the message simply omits the ROI.

---

## 📁 Files Changed

| File | Change |
|---|---|
| `core/auto_setup.py` | New — detection, no Qt dependency |
| `tests/test_auto_setup.py` | New — 25 tests |
| `ui/widgets/object_viewer_2d.py` | `set_roi_from_fractions()` |
| `ui/handlers/thumbnail_creation_handler.py` | `_apply_auto_setup()`, called from both generation paths |
| `tests/test_thumbnail_creation_handler.py` | 6 wiring tests |

---

## 🧪 Verification

- Full suite including slow and benchmark tests: **1268 passed, 5 skipped**
  (was 1236 — 32 new tests)
- `ruff check` and `ruff format --check` clean; mypy clean
- Detection verified against synthetic scans in 8-bit and 16-bit, which now agree
  exactly on threshold, ROI and slice range
- Guard cases verified individually: uniform, pure noise, empty, 2D, None,
  nearly-all-foreground

Not verified: behaviour on a real CT dataset. The synthetic scans model a bright
specimen in a noisy background, which is the intended case, but real scans bring
beam hardening, ring artefacts and support material that no synthetic test here
reproduces. The guards are written to decline rather than propose badly, so the
failure mode should be "no proposal" rather than "wrong proposal" — worth
confirming on real data.

---

## 💡 Lessons

1. **Judge the outcome, not the input.** Every attempt to detect "is this
   histogram bimodal?" was fragile. Asking "is the resulting proposal different
   from the defaults?" caught the noise case immediately and needs no tuning.

2. **`any()` is almost never the right reducer for bounds.** It gives a single
   outlier the same authority as the entire specimen. Counting and applying a
   floor costs one extra operation and removes a whole class of sensitivity.

3. **Testing two paths against each other finds what testing one cannot.** The
   16-bit bug was invisible in isolation — the result looked plausible. It only
   became obviously wrong next to the 8-bit result for the same scan.

4. **Ties in an argmax are a design decision.** The lowest index is rarely the
   intended answer; it is just what the function returns.

---

**Next:** confirm the thresholds and margins against real scans, and consider
exposing `analysis.auto_setup` as a setting if the automatic application ever
gets in the way.
