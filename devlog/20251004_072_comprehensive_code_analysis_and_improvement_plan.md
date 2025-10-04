# Development Log 072 - Comprehensive Code Analysis & Improvement Plan

**Date:** 2025-10-04
**Type:** Analysis & Planning
**Status:** 📋 **PLANNING**

---

## 📋 Executive Summary

This document presents a comprehensive analysis of the CTHarvester codebase, identifying areas for improvement across code quality, test coverage, architecture, and maintainability. The analysis reveals several high-priority issues including code duplication, low test coverage in critical modules, and high cyclomatic complexity in core components.

### Quick Stats

| Metric | Current Value | Target | Priority |
|--------|--------------|--------|----------|
| **Overall Test Coverage** | 60.94% | 75%+ | 🔴 High |
| **Code Duplication** | ~500 lines | ~150 lines | 🔴 High |
| **Type: ignore count** | 9 | 0 | 🟡 Medium |
| **Mypy errors** | 20 | 0 | 🟡 Medium |
| **Max file complexity** | 145 | <70 | 🟡 Medium |
| **Print statements** | 15 | 0 | 🟢 Low |

---

## 📊 Project Overview

### Codebase Size
- **Total Python files:** 101
- **Source code lines:** ~15,649 (excluding tests)
- **Test files:** 652 tests (648 passing, 4 skipped)
- **Core classes:** 24 (core: 11, ui: 13)

### Module Breakdown

| Module | Files | Coverage | Status |
|--------|-------|----------|--------|
| **core/** | 9 | 62.0% | 🟡 Needs improvement |
| **ui/** | 16 | 69.3% | 🟡 Needs improvement |
| **utils/** | 8 | 66.8% | 🟡 Needs improvement |
| **config/** | 6 | 62.6% | 🟡 Needs improvement |
| **security/** | 2 | 89.9% | ✅ Good |
| **root/** | 4 | 20.0% | 🔴 Critical |

---

## 🔴 Critical Issues

### 1. Zero Test Coverage Modules

**Impact:** High - These modules are completely untested
**Risk:** High - Changes may introduce undetected bugs

| Module | Coverage | Lines | Reason |
|--------|----------|-------|--------|
| `config/i18n.py` | 0% | 120 | No tests for translation manager |
| `config/tooltips.py` | 0% | - | No tests for tooltip configuration |
| `utils/error_messages.py` | 0% | 268 | No tests for error message builder |
| `manage_version.py` | 0% | - | No tests for version management |

#### Recommended Actions

**Priority 1: config/i18n.py**
```python
# Required test cases (estimate: 10-12 tests)
- test_load_supported_language()
- test_load_unsupported_language()
- test_get_system_language()
- test_translation_file_not_found()
- test_translator_installation()
- test_language_name_lookup()
```

**Priority 2: utils/error_messages.py**
```python
# Required test cases (estimate: 15-18 tests)
- test_build_file_not_found_error()
- test_build_permission_denied_error()
- test_build_out_of_memory_error()
- test_from_exception_autodetect()
- test_error_template_variables()
- test_show_error_dialog()
```

**Priority 3: config/tooltips.py**
- Create basic configuration validation tests
- Estimate: 5-8 tests

---

### 2. Low Coverage in Critical Modules

**Impact:** High - Core functionality lacks adequate testing

| Module | Current | Target | Gap | Tests Needed |
|--------|---------|--------|-----|--------------|
| `core/thumbnail_worker.py` | 20.7% | 70% | 49.3% | ~15-20 tests |
| `core/thumbnail_manager.py` | 38.0% | 70% | 32.0% | ~12-15 tests |
| `ui/widgets/object_viewer_2d.py` | 43.8% | 70% | 26.2% | ~10-12 tests |
| `CTHarvester.py` | 44.0% | 60% | 16.0% | ~8-10 tests |
| `ui/dialogs/progress_dialog.py` | 46.9% | 70% | 23.1% | ~8-10 tests |

#### Recommended Actions

**core/thumbnail_worker.py** (Priority: 🔴 High)
- File: `tests/test_thumbnail_worker_extended.py`
- Missing coverage areas:
  - Worker initialization with different parameters
  - Signal emission on success/failure
  - Error handling during image processing
  - Cancellation handling
  - Result formatting and metadata

**core/thumbnail_manager.py** (Priority: 🔴 High)
- File: `tests/test_thumbnail_manager_extended.py`
- Missing coverage areas:
  - Multi-stage sampling logic (stages 1, 2, 3)
  - Time estimation calculations
  - Worker pool management
  - Progress updates and ETA calculation
  - Cancellation propagation

---

### 3. Cursor Management Bug Risk

**Impact:** High - User experience bug
**Location:** `ui/main_window.py` (lines 615, 884, 1080)

**Problem:**
```python
# Current code (UNSAFE)
QApplication.setOverrideCursor(Qt.WaitCursor)
# ... operation that might raise exception
QApplication.restoreOverrideCursor()  # May not be called!
```

**Impact:** If an exception occurs, cursor stays in wait state permanently, requiring application restart.

**Solution:**
```python
# Create utils/ui_utils.py
from contextlib import contextmanager
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

@contextmanager
def wait_cursor():
    """Context manager for safe cursor override.

    Usage:
        with wait_cursor():
            # long operation
    """
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()
```

**Files to update:**
- `ui/main_window.py` (11 occurrences)
- `ui/handlers/export_handler.py` (3 occurrences)

---

## 🟡 High Priority Issues

### 4. Code Duplication (Critical Duplication)

**Total estimated duplication:** ~500 lines → Target: ~150 lines (70% reduction)

#### A. Time Estimation Logic Duplication

**Location:** `core/thumbnail_manager.py:1017-1199`
**Duplicated code:** ~180 lines
**Impact:** Very High - Repeated 3 times for Stage 1, 2, 3

**Current Pattern:**
```python
# Stage 1 (lines 1017-1085)
sample_elapsed = time.time() - (self.sample_start_time or 0)
time_per_image = sample_elapsed / self.sample_size
level1_time = total * time_per_image
level2_time = level1_time * 0.25
# ... format time strings
# ... log results

# Stage 2 (lines 1086-1140) - NEARLY IDENTICAL
# Stage 3 (lines 1141-1199) - NEARLY IDENTICAL
```

**Proposed Solution:**

Create `utils/time_estimator.py`:
```python
class TimeEstimator:
    """Centralized time estimation and formatting."""

    def __init__(self):
        self.stage_samples = {1: 5, 2: 10, 3: 20}
        self.level_reduction_factor = 0.25

    def calculate_eta(
        self,
        elapsed: float,
        completed: int,
        total: int
    ) -> tuple[float, float]:
        """Calculate ETA and time per item.

        Args:
            elapsed: Elapsed time in seconds
            completed: Number of completed items
            total: Total number of items

        Returns:
            (time_per_item, estimated_remaining_seconds)
        """
        if completed == 0:
            return 0.0, 0.0

        time_per_item = elapsed / completed
        remaining = total - completed
        eta = remaining * time_per_item
        return time_per_item, eta

    def format_duration(self, seconds: float) -> str:
        """Format seconds to human-readable string.

        Returns:
            Formatted string like "2.5s", "1m 30s", or "1h 15m"
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"

    def estimate_multi_level_work(
        self,
        base_time: float,
        num_levels: int = 3
    ) -> dict[int, float]:
        """Estimate time for multiple LoD levels.

        Args:
            base_time: Time for level 1 (full resolution)
            num_levels: Number of levels to estimate

        Returns:
            Dictionary mapping level to estimated time
        """
        estimates = {1: base_time}
        for level in range(2, num_levels + 1):
            estimates[level] = estimates[level - 1] * self.level_reduction_factor
        return estimates
```

**Refactoring Estimate:**
- Create utility: 2 hours
- Refactor thumbnail_manager.py: 4 hours
- Add tests: 3 hours
- **Total:** ~1 day

---

#### B. Coordinate Transformation Duplication

**Location:** `ui/widgets/object_viewer_2d.py:145-155`
**Duplicated code:** 4 nearly identical methods

**Current Code:**
```python
def _2canx(self, coord):
    return round((float(coord) / self.image_canvas_ratio) * self.scale)

def _2cany(self, coord):
    return round((float(coord) / self.image_canvas_ratio) * self.scale)

def _2imgx(self, coord):
    return round(((float(coord)) / self.scale) * self.image_canvas_ratio)

def _2imgy(self, coord):
    return round(((float(coord)) / self.scale) * self.image_canvas_ratio)
```

**Proposed Solution:**
```python
def transform_coordinate(
    self,
    coord: float,
    to_canvas: bool = True
) -> int:
    """Transform coordinate between canvas and image space.

    Args:
        coord: Coordinate value
        to_canvas: True for image->canvas, False for canvas->image

    Returns:
        Transformed coordinate (rounded to int)
    """
    if to_canvas:
        return round((float(coord) / self.image_canvas_ratio) * self.scale)
    else:
        return round((float(coord) / self.scale) * self.image_canvas_ratio)

# Backward compatibility (optional)
def _2canx(self, coord):
    return self.transform_coordinate(coord, to_canvas=True)

def _2imgx(self, coord):
    return self.transform_coordinate(coord, to_canvas=False)
```

**Refactoring Estimate:** 2 hours

---

#### C. Image Loading Pattern Duplication

**Locations:** 35+ occurrences across codebase
**Duplicated pattern:**

```python
# Repeated in thumbnail_manager.py, thumbnail_worker.py, file_handler.py, etc.
try:
    with Image.open(file_path) as img:
        if img.mode == "P":
            img = img.convert("L")
        arr = np.array(img)
        # ... process array
except FileNotFoundError:
    logger.warning(f"File not found: {file_path}")
    # ... handle error
except OSError as e:
    logger.error(f"Error loading: {file_path}", exc_info=True)
    # ... handle error
```

**Proposed Solution:**

Add to `utils/image_utils.py`:
```python
from typing import Optional
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ImageLoadError(Exception):
    """Raised when image loading fails."""
    pass

def safe_load_image(
    file_path: str,
    convert_mode: Optional[str] = None,
    as_array: bool = True,
    handle_palette: bool = True
) -> Union[np.ndarray, Image.Image, None]:
    """Load image with standardized error handling.

    Args:
        file_path: Path to image file
        convert_mode: PIL mode to convert to (e.g., 'L', 'RGB')
        as_array: Return as numpy array if True, PIL Image if False
        handle_palette: Auto-convert palette mode to grayscale

    Returns:
        Loaded image as array or PIL Image, or None on error

    Raises:
        ImageLoadError: If loading fails critically

    Example:
        >>> arr = safe_load_image("image.png")
        >>> rgb = safe_load_image("image.png", convert_mode='RGB')
    """
    try:
        with Image.open(file_path) as img:
            # Handle palette mode
            if handle_palette and img.mode == "P":
                img = img.convert("L")

            # Apply conversion if requested
            if convert_mode and img.mode != convert_mode:
                img = img.convert(convert_mode)

            # Return as requested format
            if as_array:
                return np.array(img)
            else:
                return img.copy()

    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return None

    except OSError as e:
        logger.error(f"Error loading image: {file_path}", exc_info=True)
        raise ImageLoadError(f"Failed to load {file_path}") from e

    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}", exc_info=True)
        raise ImageLoadError(f"Unexpected error loading {file_path}") from e
```

**Refactoring Estimate:**
- Create utility function: 2 hours
- Update 35+ call sites: 6 hours
- Add tests: 2 hours
- **Total:** ~1.5 days

---

### 5. High Cyclomatic Complexity

**Impact:** Medium-High - Reduces maintainability and testability

| File | Lines | Methods | Complexity | Status |
|------|-------|---------|------------|--------|
| `ui/widgets/object_viewer_2d.py` | 644 | - | 145 | 🔴 Critical |
| `core/thumbnail_manager.py` | 1,251 | 10 | 127 | 🔴 Critical |
| `ui/main_window.py` | 1,287 | 39 | 92 | 🟡 High |
| `core/thumbnail_generator.py` | 974 | - | 69 | 🟡 High |
| `ui/widgets/mcube_widget.py` | 840 | - | 58 | 🟡 Medium |

**Recommended threshold:** Complexity < 50 per file

#### Refactoring Plan: thumbnail_manager.py

**Current structure:** Single 1,251-line class with complexity 127

**Proposed split:**

1. **ThumbnailCoordinator** (Main orchestrator)
   - Process level coordination
   - Worker pool management
   - Cancellation handling

2. **ThumbnailSampler** (Sampling logic)
   - Stage 1, 2, 3 sampling
   - Time estimation (using new TimeEstimator)
   - Statistics collection

3. **ThumbnailResultCollector** (Result management)
   - Result dictionary management
   - Image array collection
   - Progress tracking

**Estimated breakdown:**
- `ThumbnailCoordinator`: ~400 lines, complexity ~40
- `ThumbnailSampler`: ~350 lines, complexity ~35
- `ThumbnailResultCollector`: ~300 lines, complexity ~30
- Shared utilities: ~150 lines

**Refactoring estimate:** 2-3 days

---

#### Refactoring Plan: object_viewer_2d.py

**Current complexity:** 145 (critical)

**High-complexity areas:**
- Mouse event handling (click, move, wheel)
- Coordinate transformation (already addressed above)
- ROI drawing and management
- Paint event with multiple rendering modes

**Proposed improvements:**
1. Extract coordinate transformation (already planned)
2. Create `ROIManager` helper class
3. Split paint event into smaller rendering methods
4. Extract mouse event state machine

**Refactoring estimate:** 2 days

---

### 6. Type Safety Issues

**Current state:**
- `type: ignore` comments: 9 (down from 28 - good progress! ✅)
- Mypy errors: 20 (need to fix)

#### Critical Mypy Errors

**Location:** `core/thumbnail_manager.py`

```python
# Line 106: Incompatible types in assignment
self.progress_manager.level_work_distribution = level_work_distribution
# Type mismatch: list[dict[str, int | float]] vs dict[int, dict[str, int]] | None

# Line 142, 163: Optional attribute access without None check
self.thumbnail_parent.sample_size  # Item "None" has no attribute
self.thumbnail_parent.measured_images_per_second

# Line 255, 257: Float/int type mismatch
self.progress_manager.start(total_work)  # expects int, got float | int
self.progress_manager.update(value=current_step)  # expects int, got float
```

**Solutions:**

1. Add type guards:
```python
def _update_parent_stats(self, stats: dict) -> None:
    """Update parent statistics if parent exists."""
    if self.thumbnail_parent is None:
        return

    self.thumbnail_parent.sample_size = stats['sample_size']
    self.thumbnail_parent.measured_images_per_second = stats['speed']
```

2. Fix type annotations:
```python
# progress_manager.py
def start(self, total_work: int) -> None:  # Enforce int
    ...

def update(self, value: Optional[int] = None) -> None:  # Enforce int
    ...

# thumbnail_manager.py
level_work_distribution: List[Dict[str, Union[int, float]]] = []
```

**Refactoring estimate:** 1 day

---

## 🟢 Medium Priority Issues

### 7. Print Statements in Source Code

**Count:** 15 print statements in source code
**Logger usage:** 391 (good! ✅)

**Locations to fix:**
```bash
# Find all print statements
grep -n "print(" core/*.py ui/*.py utils/*.py config/*.py
```

**Solution:** Replace with appropriate logger calls
```python
# Before
print(f"Processing {filename}")

# After
logger.info(f"Processing {filename}")
```

**Estimate:** 2 hours

---

### 8. Unimplemented Property-Based Tests

**Location:** `tests/property/test_image_properties.py:22`

```python
@given(
    width=st.integers(min_value=1, max_value=4096),
    height=st.integers(min_value=1, max_value=4096),
)
def test_downsample_preserves_aspect_ratio(self, width, height):
    """Property: Downsampling preserves aspect ratio"""
    # TODO: Implement
    pytest.skip("Template - to be implemented in Phase 4")
```

**Proposed implementation:**
```python
from hypothesis import given
from hypothesis import strategies as st
from utils.image_utils import downsample_image
import numpy as np

@pytest.mark.property
class TestImageProperties:

    @given(
        width=st.integers(min_value=10, max_value=1000),
        height=st.integers(min_value=10, max_value=1000),
        factor=st.integers(min_value=2, max_value=8),
    )
    def test_downsample_preserves_aspect_ratio(self, width, height, factor):
        """Property: Downsampling preserves aspect ratio within rounding error."""
        # Create test image
        img = np.random.randint(0, 256, (height, width), dtype=np.uint8)

        # Downsample
        downsampled = downsample_image(img, factor)

        # Check aspect ratio
        original_ratio = width / height
        new_ratio = downsampled.shape[1] / downsampled.shape[0]

        # Allow for rounding error
        assert abs(original_ratio - new_ratio) < 0.01

    @given(
        width=st.integers(min_value=10, max_value=1000),
        height=st.integers(min_value=10, max_value=1000),
    )
    def test_downsample_reduces_size(self, width, height):
        """Property: Downsampled image is always smaller."""
        img = np.random.randint(0, 256, (height, width), dtype=np.uint8)
        downsampled = downsample_image(img, factor=2)

        assert downsampled.shape[0] <= height // 2 + 1
        assert downsampled.shape[1] <= width // 2 + 1
```

**Estimate:** 4 hours

---

### 9. Cursor Context Manager (Duplication Pattern)

**Pattern found:** 14+ locations
- `ui/main_window.py`: 11 occurrences
- `ui/handlers/export_handler.py`: 3 occurrences

**Current pattern:**
```python
QApplication.setOverrideCursor(Qt.WaitCursor)
try:
    # operation
finally:
    QApplication.restoreOverrideCursor()
```

**Proposed solution:** (Already covered in Critical Issues #3)

---

## 📅 Implementation Roadmap

### Phase 1: Critical Fixes (Week 1) - 5 days

**Goals:**
- Fix cursor management bug
- Add tests for 0% coverage modules
- Implement cursor context manager

**Tasks:**

| Task | Effort | Priority | Deliverable |
|------|--------|----------|-------------|
| Create `utils/ui_utils.py` with `wait_cursor()` | 2h | 🔴 Critical | Context manager |
| Update 14 cursor usage sites | 3h | 🔴 Critical | Bug fix |
| Add tests for `config/i18n.py` | 4h | 🔴 High | 10-12 tests |
| Add tests for `utils/error_messages.py` | 6h | 🔴 High | 15-18 tests |
| Add tests for `config/tooltips.py` | 3h | 🔴 High | 5-8 tests |

**Success Metrics:**
- ✅ Cursor management bug eliminated
- ✅ 0% coverage modules → 70%+ coverage
- ✅ 35-38 new tests added

**Estimated effort:** 18 hours (~2-3 days)

---

### Phase 2: Code Quality Improvements (Week 2-3) - 10 days

**Goals:**
- Reduce code duplication
- Improve type safety
- Increase test coverage of critical modules

**Tasks:**

| Task | Effort | Priority | Deliverable |
|------|--------|----------|-------------|
| Create `utils/time_estimator.py` | 2h | 🔴 High | TimeEstimator class |
| Refactor thumbnail_manager time estimation | 4h | 🔴 High | -180 lines |
| Add tests for TimeEstimator | 3h | 🔴 High | 10-12 tests |
| Create `safe_load_image()` utility | 2h | 🟡 Medium | Image loader |
| Update 35+ image loading sites | 6h | 🟡 Medium | Reduced duplication |
| Add tests for safe_load_image | 2h | 🟡 Medium | 8-10 tests |
| Refactor coordinate transformation | 2h | 🟡 Medium | -20 lines |
| Fix 20 mypy type errors | 8h | 🟡 Medium | Type safety |
| Add tests for thumbnail_worker | 8h | 🔴 High | 15-20 tests |
| Add tests for thumbnail_manager | 8h | 🔴 High | 12-15 tests |
| Replace 15 print statements | 2h | 🟢 Low | Logger usage |

**Success Metrics:**
- ✅ Code duplication reduced by ~300 lines
- ✅ Mypy errors: 20 → 0
- ✅ thumbnail_worker coverage: 20.7% → 70%+
- ✅ thumbnail_manager coverage: 38% → 70%+
- ✅ 55-67 new tests added

**Estimated effort:** 47 hours (~6-7 days)

---

### Phase 3: Architectural Refactoring (Week 4-5) - 10 days

**Goals:**
- Reduce cyclomatic complexity
- Split large files into manageable components
- Improve maintainability

**Tasks:**

| Task | Effort | Priority | Deliverable |
|------|--------|----------|-------------|
| Split thumbnail_manager.py | 16h | 🟡 Medium | 3 classes |
| Add tests for split components | 8h | 🟡 Medium | 20-25 tests |
| Refactor object_viewer_2d.py | 12h | 🟡 Medium | ROIManager + cleanup |
| Add tests for object_viewer | 6h | 🟡 Medium | 10-12 tests |
| Implement property-based tests | 4h | 🟢 Low | Image property tests |
| Update documentation | 4h | 🟢 Low | Devlog + docstrings |

**Success Metrics:**
- ✅ thumbnail_manager complexity: 127 → <50
- ✅ object_viewer_2d complexity: 145 → <70
- ✅ All files < 800 lines
- ✅ 30-37 new tests added

**Estimated effort:** 50 hours (~6-7 days)

---

### Phase 4: Polish & Validation (Week 6) - 5 days

**Goals:**
- Achieve target test coverage
- Validate all changes
- Update documentation

**Tasks:**

| Task | Effort | Priority | Deliverable |
|------|--------|----------|-------------|
| Add missing UI widget tests | 8h | 🟡 Medium | 10-15 tests |
| Integration testing | 6h | 🟡 Medium | Smoke tests |
| Performance regression testing | 4h | 🟢 Low | Benchmarks |
| Code review & cleanup | 4h | 🟢 Low | Clean code |
| Update developer documentation | 4h | 🟢 Low | Docs |
| Final testing & validation | 4h | 🟡 Medium | QA |

**Success Metrics:**
- ✅ Overall coverage: 60.94% → 75%+
- ✅ All modules > 60% coverage
- ✅ No regression in functionality
- ✅ Updated documentation

**Estimated effort:** 30 hours (~4 days)

---

## 📊 Summary & Expected Impact

### Total Effort Estimate

| Phase | Duration | Effort (hours) |
|-------|----------|----------------|
| Phase 1: Critical Fixes | 3 days | 18 |
| Phase 2: Code Quality | 7 days | 47 |
| Phase 3: Refactoring | 7 days | 50 |
| Phase 4: Polish | 4 days | 30 |
| **TOTAL** | **~21 days** | **145 hours** |

### Expected Outcomes

#### Code Quality Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Test Coverage** | 60.94% | 75%+ | +14% |
| **Tests Count** | 648 | ~800 | +152 tests |
| **Code Duplication** | ~500 lines | ~150 lines | -70% |
| **Max Complexity** | 145 | <70 | -52% |
| **Type: ignore** | 9 | 0 | -100% |
| **Mypy errors** | 20 | 0 | -100% |
| **Print statements** | 15 | 0 | -100% |

#### Module Coverage Improvements

| Module | Before | After | Improvement |
|--------|--------|-------|-------------|
| config/i18n.py | 0% | 70%+ | +70% |
| config/tooltips.py | 0% | 70%+ | +70% |
| utils/error_messages.py | 0% | 70%+ | +70% |
| core/thumbnail_worker.py | 20.7% | 70%+ | +49.3% |
| core/thumbnail_manager.py | 38% | 70%+ | +32% |
| ui/widgets/object_viewer_2d.py | 43.8% | 70%+ | +26.2% |

#### Architecture Improvements

1. **New Utility Modules**
   - `utils/time_estimator.py` - Time estimation and formatting
   - `utils/ui_utils.py` - UI helper functions (cursor management)
   - Enhanced `utils/image_utils.py` - Safe image loading

2. **Refactored Components**
   - `core/thumbnail_manager.py` → Split into 3 focused classes
   - `ui/widgets/object_viewer_2d.py` → ROIManager extraction

3. **Eliminated Issues**
   - ✅ Cursor management bug (critical UX issue)
   - ✅ Code duplication (~350 lines removed)
   - ✅ Type safety issues (20 mypy errors fixed)
   - ✅ Untested modules (3 modules at 0% coverage)

---

## 🎯 Success Criteria

### Phase 1 (Week 1)
- [ ] Zero critical bugs (cursor management fixed)
- [ ] Zero modules with 0% coverage
- [ ] All new code has tests

### Phase 2 (Week 2-3)
- [ ] Code duplication reduced by 50%+
- [ ] Mypy passes cleanly (0 errors)
- [ ] Core modules at 70%+ coverage

### Phase 3 (Week 4-5)
- [ ] All files have complexity < 100
- [ ] No file > 1000 lines
- [ ] Architecture documented

### Phase 4 (Week 6)
- [ ] Overall coverage ≥ 75%
- [ ] All tests passing
- [ ] Documentation complete
- [ ] No regressions

---

## 📝 Notes

### Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking changes during refactoring | High | Medium | Comprehensive test suite first |
| Performance regression | Medium | Low | Benchmark before/after |
| Incomplete test coverage | Medium | Medium | Incremental testing per PR |
| Scope creep | Low | Medium | Stick to 4-phase plan |

### Dependencies

- **Required before starting:** None (can start immediately)
- **Blocking issues:** None identified
- **External dependencies:** All tools already in place

### Out of Scope

This plan does NOT include:
- New feature development
- UI/UX changes
- Performance optimization (beyond preventing regression)
- Documentation translation
- Rust integration improvements

---

## 🔗 Related Documents

- [20251003_070_comprehensive_improvement_plan.md](20251003_070_comprehensive_improvement_plan.md) - Previous improvement plan
- [20251003_071_implementation_report.md](20251003_071_implementation_report.md) - Latest implementation status
- [20250930_035_codebase_analysis_and_improvement_plan.md](20250930_035_codebase_analysis_and_improvement_plan.md) - Earlier analysis

---

## ✅ Approval & Next Steps

**Status:** 📋 Awaiting approval

**Next Steps:**
1. Review plan with stakeholders
2. Prioritize phases if time-constrained
3. Create GitHub issues for tracking
4. Begin Phase 1 implementation

**Estimated Start Date:** 2025-10-04
**Estimated Completion:** 2025-10-31 (4 weeks)

---

*This plan represents a comprehensive approach to improving code quality, test coverage, and maintainability while minimizing risk through incremental changes and continuous testing.*
