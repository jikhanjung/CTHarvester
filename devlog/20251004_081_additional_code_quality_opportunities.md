# Devlog 081: Additional Code Quality Opportunities

**Date:** 2025-10-04
**Status:** 📋 Optional Improvements
**Previous:** [devlog 080 - Mypy Fix Plan](./20251004_080_mypy_fix_implementation_plan.md)

---

## 🎯 Overview

This document captures additional code quality improvements discovered during the Phase 1-4 completion analysis. These are **lower priority** than the mypy fixes but provide incremental value.

---

## 1. 🔄 Caching Opportunities in Image Loading

### Current State

Image files are loaded from disk repeatedly without caching:

**Location:** `core/thumbnail_worker.py:156-182`
```python
def _load_image(self, filepath: str) -> Tuple[Optional[Image.Image], bool]:
    """Load image - no caching, always reads from disk."""
    with Image.open(validated_path) as img_temp:
        # ... processing ...
        img = img_temp.copy()
    return img, is_16bit
```

**Location:** `utils/image_utils.py:65-110`
```python
def load_image_as_array(image_path: str, target_dtype=None) -> np.ndarray:
    """Load image - no caching, always reads from disk."""
    with Image.open(image_path) as img:
        arr = np.array(img, dtype=target_dtype)
    return arr
```

### Potential Issue

For workflows that repeatedly access the same images:
- **UI thumbnail previews** - May reload same image multiple times during UI updates
- **Volume processing** - Sequential slice loading could benefit from read-ahead cache
- **Export operations** - May re-read thumbnails that were already generated

### Proposed Solution (Optional)

Add LRU cache for frequently accessed images:

```python
# utils/image_cache.py (new file)
from functools import lru_cache
from typing import Optional, Tuple
import numpy as np
from PIL import Image

class ImageCache:
    """Thread-safe LRU cache for image loading.

    Designed for repeated access to small thumbnail images.
    NOT recommended for full-size volumes (memory constraints).
    """

    def __init__(self, max_size_mb: int = 100):
        """Initialize cache with memory limit.

        Args:
            max_size_mb: Maximum cache size in MB (default: 100MB)
        """
        self.max_size_mb = max_size_mb
        self._cache: dict[str, Tuple[np.ndarray, int]] = {}  # path -> (array, size)
        self._total_size_bytes = 0

    def get(self, path: str) -> Optional[np.ndarray]:
        """Get cached image array if available."""
        if path in self._cache:
            return self._cache[path][0]
        return None

    def put(self, path: str, array: np.ndarray) -> None:
        """Cache image array with LRU eviction."""
        size = array.nbytes

        # Evict if adding this would exceed limit
        while self._total_size_bytes + size > self.max_size_mb * 1024 * 1024:
            if not self._cache:
                break  # Cache is empty, item too large
            # Evict oldest entry
            oldest_path = next(iter(self._cache))
            self._evict(oldest_path)

        self._cache[path] = (array, size)
        self._total_size_bytes += size

    def _evict(self, path: str) -> None:
        """Evict specific cache entry."""
        if path in self._cache:
            _, size = self._cache.pop(path)
            self._total_size_bytes -= size

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._total_size_bytes = 0
```

**Usage:**
```python
# In thumbnail_worker.py
class ThumbnailWorker(QRunnable):
    # Class-level cache shared across workers
    _cache = ImageCache(max_size_mb=100)

    def _load_image(self, filepath: str):
        # Check cache first
        cached = self._cache.get(filepath)
        if cached is not None:
            logger.debug(f"Cache hit: {filepath}")
            return Image.fromarray(cached), cached.dtype == np.uint16

        # Load from disk
        img, is_16bit = self._load_image_from_disk(filepath)

        # Cache if small enough
        arr = np.array(img)
        if arr.nbytes < 10 * 1024 * 1024:  # Only cache <10MB images
            self._cache.put(filepath, arr)

        return img, is_16bit
```

### Impact Assessment

**Pros:**
- ✅ Reduces disk I/O for repeated access patterns
- ✅ Speeds up UI responsiveness during thumbnail browsing
- ✅ Memory-bounded with LRU eviction

**Cons:**
- ❌ Adds complexity to image loading paths
- ❌ Memory overhead (100MB default)
- ❌ Thread synchronization needed for cache access
- ❌ May not provide significant benefit for typical workflows (load once, process once)

**Recommendation:** ⚠️ **Low Priority - Measure First**
- Profile actual workload to confirm repeated loads
- If implemented, add metrics to measure cache hit rate
- Consider as optimization only if profiling shows bottleneck

**Estimated Time:** 6 hours (implementation + testing)

---

## 2. 📝 Docstring Examples → Doctest Conversion

### Current State

Many docstrings contain example code with `print()` statements:

**Location:** `core/file_handler.py:103-109`
```python
def analyze_directory(path: str) -> Dict[str, Any]:
    """Analyze image directory.

    Examples:
        >>> settings = analyze_directory("/path/to/images")
        >>> print(f"Found {settings['seq_end'] - settings['seq_begin'] + 1} images")
    """
```

**Location:** `utils/image_utils.py:288-291`
```python
def load_image_with_metadata(image_path: str):
    """Load image and extract metadata.

    Example:
        >>> arr, meta = load_image_with_metadata('slice_0001.tif')
        >>> print(f"{meta['width']}x{meta['height']}, {meta['bit_depth']}-bit")
        2048x2048, 16-bit
    """
```

### Current Status

These `print()` statements in docstrings are **not actual code** - they're documentation examples. They don't trigger flake8 or cause issues.

### Proposed Improvement (Optional)

Convert to executable doctests:

```python
def load_image_with_metadata(image_path: str):
    """Load image and extract metadata.

    Example:
        >>> import tempfile
        >>> from PIL import Image
        >>> import numpy as np
        >>> # Create test image
        >>> with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
        ...     img = Image.fromarray(np.zeros((100, 100), dtype=np.uint8))
        ...     img.save(f.name)
        ...     arr, meta = load_image_with_metadata(f.name)
        ...     meta['width'], meta['height'], meta['bit_depth']
        (100, 100, 8)
    """
```

**Run with:**
```bash
python -m doctest -v utils/image_utils.py
```

### Impact Assessment

**Pros:**
- ✅ Examples become executable tests
- ✅ Documentation stays in sync with code
- ✅ Catches documentation drift

**Cons:**
- ❌ More verbose examples
- ❌ Harder to write (need test data setup)
- ❌ Minimal benefit (examples rarely change)

**Recommendation:** ⚠️ **Very Low Priority - Optional**
- Current docstring examples are clear and sufficient
- Conversion effort outweighs benefit
- Only consider if documentation becomes frequently incorrect

**Estimated Time:** 2 hours (10 files × 12 minutes each)

---

## 3. 🧹 Code Deduplication Opportunities

### Pattern 1: Repeated None Checks in Workers

**Location:** Multiple files in `core/`

```python
# Pattern seen in thumbnail_worker_manager.py, thumbnail_manager.py, etc.
if self.progress_dialog and self.progress_dialog.is_cancelled:
    return True

if self.progress_dialog:
    self.progress_dialog.lbl_text.setText("...")
```

**Potential Improvement:**
```python
# Add to protocols.py or create ui/utils/progress_utils.py
def safe_update_progress(dialog: Optional[ProgressDialog], text: str) -> None:
    """Safely update progress dialog text if dialog exists."""
    if dialog:
        dialog.lbl_text.setText(text)

def check_cancellation(dialog: Optional[ProgressDialog]) -> bool:
    """Check if operation was cancelled via progress dialog."""
    return bool(dialog and dialog.is_cancelled)
```

**Impact:** Low - Saves ~5 lines per usage, but adds indirection

---

### Pattern 2: Image Bit Depth Detection

**Locations:**
- `utils/image_utils.py:25-62` (detect_bit_depth)
- `core/thumbnail_worker.py:161-170` (_load_image bit depth detection)

Both implement similar logic:
```python
if img.mode in ("I;16", "I;16L", "I;16B"):
    bit_depth = 16
elif img.mode in ("L", "RGB", "RGBA"):
    bit_depth = 8
```

**Already Good:** These are separate enough that consolidation may not help.

---

## 4. 🎨 UI Code Organization Opportunities

### Large Widget Files

From devlog 079 analysis:

**File:** `ui/widgets/mcube_widget.py` (836 lines)
**File:** `ui/widgets/object_viewer_2d.py` (743 lines after ROIManager extraction)

### Potential Extractions

#### MCubeWidget (836 lines)

Possible extractions:
1. **MCubeRenderer** - OpenGL rendering logic (~200 lines)
   - `paintGL()`, `draw_box()`, `draw_surface()`, `draw_cutting_planes()`
2. **MCubeInteractionHandler** - Mouse/keyboard events (~150 lines)
   - `mousePressEvent()`, `mouseMoveEvent()`, `wheelEvent()`, `keyPressEvent()`
3. **MCubeState** - State management (~100 lines)
   - Camera position, rotation, zoom, visible faces, plane positions

**Expected Result:** mcube_widget.py → ~400 lines (main coordination)

#### ObjectViewer2D (743 lines after ROI extraction)

Already had one extraction (ROIManager in Phase 4). Additional possibilities:
1. **ImageRenderer** - Pixmap scaling and display (~100 lines)
   - `update_pixmap()`, scaling logic
2. **MouseInteractionHandler** - Mouse event coordination (~150 lines)
   - `mousePressEvent()`, `mouseMoveEvent()`, `mouseReleaseEvent()`

**Expected Result:** object_viewer_2d.py → ~500 lines

### Impact Assessment

**Pros:**
- ✅ Better testability (can test renderer separately)
- ✅ Clearer separation of concerns
- ✅ Easier to maintain each component

**Cons:**
- ❌ More files to navigate
- ❌ Indirection through delegation
- ❌ Risk of breaking existing code
- ❌ Current files are already manageable (<850 lines)

**Recommendation:** ⚠️ **Medium Priority - Consider Later**
- Current sizes are acceptable (Phase 4 already helped)
- Only refactor if actively modifying these files
- Not urgent compared to mypy fixes

**Estimated Time:** 8-12 hours per widget

---

## 5. 🧪 Testing Gaps

### Integration Tests

**Current State:** 911 tests (mostly unit tests)
**Gap:** Limited integration tests for complete workflows

**Potential Additions:**

1. **Full Thumbnail Generation Workflow Test**
   ```python
   def test_thumbnail_generation_complete_workflow():
       """Test complete thumbnail pyramid generation from start to finish."""
       # Setup: Create temporary image sequence
       # Execute: Generate all levels
       # Verify: All levels exist, correct sizes, correct content
   ```

2. **UI Workflow Integration Tests**
   ```python
   def test_main_window_load_analyze_export_workflow():
       """Test full UI workflow: load → analyze → crop → export."""
       # This would catch integration issues between components
   ```

3. **Error Recovery Tests**
   ```python
   def test_thumbnail_generation_with_corrupted_image():
       """Test handling of corrupted input images."""

   def test_thumbnail_generation_with_disk_full():
       """Test graceful degradation when disk is full."""
   ```

**Recommendation:** ⭐ **Medium-High Priority**
- Integration tests provide high value
- Catch issues that unit tests miss
- Especially valuable for UI workflows

**Estimated Time:** 8 hours (10-15 new integration tests)

---

## 6. 📚 Documentation Improvements

### Current State

**Strengths:**
- ✅ Good docstrings on most functions/classes
- ✅ Devlogs document development process
- ✅ Type hints present

**Gaps:**
- ❌ No architecture overview document
- ❌ No API documentation generated (Sphinx)
- ❌ No user guide
- ❌ No developer onboarding guide

### Proposed Documentation

#### 1. Architecture Overview (`docs/architecture.md`)
```markdown
# CTHarvester Architecture

## System Overview
[Diagram showing core, ui, utils, config layers]

## Key Components
- ThumbnailManager: Pyramid generation coordinator
- VolumeProcessor: 3D volume analysis
- ObjectViewer2D: 2D slice viewer with ROI
- MCubeWidget: 3D visualization

## Data Flow
[Diagram showing image → thumbnail → volume → export]
```

#### 2. Sphinx API Documentation
```bash
# Generate HTML documentation
sphinx-quickstart docs/
sphinx-apidoc -o docs/source/ .
make html
```

#### 3. Developer Guide (`docs/developer_guide.md`)
```markdown
# Developer Guide

## Setup
1. Install dependencies
2. Run tests
3. Configure pre-commit hooks

## Code Structure
- core/: Business logic
- ui/: PyQt5 interface
- utils/: Shared utilities
- tests/: Test suite

## Contributing
- Follow PEP 8
- Add tests for new features
- Update docstrings
- Run pre-commit hooks
```

**Recommendation:** ⭐ **Medium Priority**
- Valuable for onboarding and maintenance
- Can be done incrementally
- Sphinx auto-generation is quick (~2 hours)
- Architecture doc provides high value (~4 hours)

**Estimated Time:**
- Sphinx setup: 2 hours
- Architecture diagram: 4 hours
- Developer guide: 3 hours
- User guide: 5 hours
- **Total:** 14 hours

---

## 7. 🔍 Static Analysis Enhancements

### Current Tools

- ✅ mypy (type checking)
- ✅ flake8 (style)
- ✅ black (formatting)
- ✅ isort (import sorting)
- ✅ bandit (security)

### Additional Tools to Consider

#### 1. pylint (Comprehensive Linting)
```bash
pip install pylint
pylint core/ ui/ utils/
```

**Checks:**
- Code smells
- Complexity metrics
- Naming conventions
- Unused variables
- Cyclomatic complexity

**Trade-off:** Very noisy, requires configuration to be useful

#### 2. radon (Complexity Metrics)
```bash
pip install radon
radon cc core/ -a  # Cyclomatic complexity
radon mi core/     # Maintainability index
```

**Output:**
```
core/thumbnail_manager.py
    F 1295:0 ThumbnailManager.process_level_sequential - B (15)
    F 150:0 ThumbnailManager.__init__ - A (3)
    F 200:0 ThumbnailManager.generate_thumbnails - A (5)
```

**Use Case:** Identify overly complex functions for refactoring

#### 3. vulture (Dead Code Detection)
```bash
pip install vulture
vulture core/ ui/ utils/
```

**Output:**
```
ui/widgets/mcube_widget.py:523: unused function 'old_draw_method'  # 60% confidence
```

**Recommendation:** ⚠️ **Low Priority**
- Current tool chain is sufficient
- Additional tools add maintenance burden
- Only add if specific issues arise

**Estimated Time:** 4 hours (setup + baseline + config)

---

## 8. 🚀 Performance Profiling

### Current State

**Known Performance Characteristics:**
- ✅ Rust module for fast thumbnail generation
- ✅ QThreadPool for parallel processing
- ✅ Efficient numpy operations

**Unknowns:**
- ❓ Actual bottlenecks in typical workflows
- ❓ Memory usage patterns
- ❓ Disk I/O vs CPU time ratio

### Proposed Profiling

#### 1. cProfile Analysis
```python
# scripts/profiling/profile_thumbnail_generation.py
import cProfile
import pstats

def profile_thumbnail_workflow():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run typical thumbnail generation
    manager = ThumbnailManager(...)
    manager.generate_thumbnails(...)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

if __name__ == "__main__":
    profile_thumbnail_workflow()
```

#### 2. Memory Profiling
```python
# scripts/profiling/profile_memory.py
from memory_profiler import profile

@profile
def thumbnail_generation_memory():
    # Track memory usage during processing
    pass
```

#### 3. Line Profiling (Detailed)
```bash
pip install line_profiler
kernprof -l -v scripts/profiling/detailed_profile.py
```

**Recommendation:** ⭐ **Low-Medium Priority**
- Only needed if performance issues reported
- Rust module already optimizes bottleneck
- Useful for future optimization work

**Estimated Time:** 6 hours (setup + analysis + documentation)

---

## 📊 Priority Summary

### 🔴 High Priority (Do Soon)
1. **Mypy Fixes** (covered in devlog 080) - 80 minutes
2. **Integration Tests** - 8 hours

### 🟡 Medium Priority (Consider Next Quarter)
3. **Sphinx Documentation** - 2 hours
4. **Architecture Documentation** - 4 hours
5. **Widget Refactoring** (if modifying) - 8-12 hours each

### 🟢 Low Priority (Nice to Have)
6. **Image Caching** (measure first) - 6 hours
7. **Performance Profiling** (if issues arise) - 6 hours
8. **Doctest Conversion** (optional) - 2 hours
9. **Additional Static Analysis** (only if needed) - 4 hours

---

## 🎯 Recommended Next Actions

After completing the mypy fixes (devlog 080):

1. ✅ **Run full test suite** to establish baseline
2. ✅ **Generate Sphinx documentation** (quick win, high value)
3. ✅ **Write 10-15 integration tests** (high ROI for stability)
4. ✅ **Create architecture diagram** (helps onboarding)
5. ⏸️ **Consider widget refactoring** only if actively modifying those files

---

**Analysis Completed:** 2025-10-04
**Total Optional Improvements Identified:** 8 categories
**Estimated Total Effort:** ~55 hours (if doing everything)
**Recommended Subset:** ~25 hours (high + medium priority items)

---

*This analysis complements devlog 079 and 080 by identifying lower-priority improvements that can be addressed incrementally.*
