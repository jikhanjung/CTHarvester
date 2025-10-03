# Development Log 070 - Comprehensive Improvement Plan

**Date:** 2025-10-03
**Related:** [20251002_069_phase1_2_3_complete.md](20251002_069_phase1_2_3_complete.md) (별도 계획)
**Status:** 📋 **PLANNING - NEW IMPROVEMENT TRACK**

---

## 📋 Executive Summary

**Note**: This is a **separate improvement plan** independent from the Phase 1-3 work completed in devlog 069. This plan addresses different areas based on comprehensive codebase analysis.

Comprehensive analysis of CTHarvester codebase identifies **43 improvement opportunities** across code quality, testing, performance, and architecture. This plan prioritizes actionable improvements with clear timelines and success metrics.

### Current State
- ✅ Version: 0.2.3-beta.1
- ✅ Tests: 620 passing (27 integration tests)
- ⚠️ Coverage: 48.84% overall
  - Core modules: 20-77% (needs improvement)
  - Utils modules: 90-100% (excellent)
- ⚠️ Pre-commit hooks: 2 blocking issues (flake8, mypy)

### Goals
- 🎯 **Short-term (2 weeks)**: Fix blocking issues, add critical tests → 65% coverage
- 🎯 **Medium-term (2-3 months)**: Refactor architecture, improve type safety → 80% coverage
- 🎯 **Long-term (6 months)**: Production-ready quality → 90% coverage

---

## 🔍 Analysis Summary

### Codebase Health Assessment

| Category | Status | Priority Issues |
|----------|--------|-----------------|
| **Code Quality** | 🟡 Good | 28× type:ignore, large files (1164 lines) |
| **Architecture** | 🟢 Strong | God object pattern in main_window.py |
| **Testing** | 🔴 Needs Work | 22-38% coverage in core thumbnail modules |
| **Security** | 🟢 Excellent | Well-designed FileSecurityError handling |
| **Performance** | 🟡 Good | Minor inefficiencies, no regression tests |
| **Documentation** | 🟡 Good | Missing examples, Korean comments in security |

**Key Discovery**: Integration tests are comprehensive (27 tests) but lack **depth**:
- ❌ Small test datasets (10 images) → multi-stage sampling untested
- ❌ Heavy Mock usage → Worker internals untested
- ❌ Missing edge cases → sequential mode, error paths untested

---

## 🎯 Phase 1: Critical Fixes (Week 1-2)

**Goal**: Fix blocking issues and improve core module coverage to 65%

### Priority 1: Pre-commit Hook Issues (1-2 hours)

#### Issue #1: Flake8 B010 - setattr with constant
**File**: `core/thumbnail_manager.py:1099-1109`
**Severity**: High (blocking CI)

```python
# Current (Bad)
setattr(self.parent, "sampled_estimate_seconds", total_estimate)
setattr(self.parent, "sampled_estimate_str", formatted_estimate)
setattr(self.parent, "estimated_time_per_image", ...)
setattr(self.parent, "estimated_total_time", total_estimate)
setattr(self.parent, "measured_images_per_second", self.images_per_second)

# Fixed (Good)
if self.parent is not None:
    self.parent.sampled_estimate_seconds = total_estimate
    self.parent.sampled_estimate_str = formatted_estimate
    self.parent.estimated_time_per_image = (
        1.0 / self.images_per_second if self.images_per_second > 0 else 0.05
    )
    self.parent.estimated_total_time = total_estimate
    self.parent.measured_images_per_second = self.images_per_second
```

**Tasks**:
- [ ] Replace 5 setattr calls with direct property access
- [ ] Run flake8 to verify fix
- [ ] Test pre-commit hook passes

**Expected**: Pre-commit hooks unblocked

---

#### Issue #2: Mypy Type Hints
**File**: `utils/image_utils.py:199`, `core/thumbnail_generator.py:222`
**Severity**: Medium

```python
# utils/image_utils.py:199
# Current
def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    with Image.open(image_path) as img:
        return img.size  # Returns Tuple[Any, Any]

# Fixed
def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    with Image.open(image_path) as img:
        width, height = img.size
        return (width, height)  # Explicit int tuple

# core/thumbnail_generator.py:222
# Add explicit return type annotation and fix type mismatches
```

**Tasks**:
- [ ] Fix `get_image_dimensions()` return type
- [ ] Fix `thumbnail_generator.py:222` return type
- [ ] Add `types-PyYAML` to requirements-dev.txt
- [ ] Run mypy to verify

**Expected**: Mypy passes cleanly

---

### Priority 2: Dependency Management (2 hours)

#### Issue #42: Missing Version Pins
**File**: `requirements.txt`
**Severity**: Medium (build reproducibility)

```txt
# Current (Risky)
numpy
pillow
PyQt5

# Fixed (Safe)
numpy>=1.24.0,<2.0.0  # Pin major version
pillow>=10.0.0,<11.0.0
PyQt5>=5.15.0,<6.0.0  # Don't auto-upgrade to Qt6
scipy>=1.10.0,<2.0.0
```

**Tasks**:
- [ ] Add version ranges to all dependencies
- [ ] Test installation in clean environment
- [ ] Update requirements-dev.txt similarly

**Expected**: Reproducible builds

---

#### Issue #43: Security Scanning
**File**: `.github/workflows/security.yml` (new)
**Severity**: Medium

**Tasks**:
- [ ] Create security.yml workflow
- [ ] Add Safety check (dependency vulnerabilities)
- [ ] Add Bandit scan (code security)
- [ ] Schedule weekly runs

**Expected**: Automated security alerts

---

### Priority 3: Test Coverage - Deep Testing (1 week)

**Current Coverage Analysis**:

```
core/thumbnail_manager.py:    38.44% (473 lines, 275 uncovered)
  - Lines 289-472: Sequential mode (184 lines) NEVER TESTED
  - Lines 980-1112: Multi-stage sampling (133 lines) NEVER TESTED

core/thumbnail_worker.py:     20.69% (182 lines, 136 uncovered)
  - Lines 131-443: Worker internals (312 lines) MOCKED, NOT TESTED

core/thumbnail_generator.py:  77.63% (363 lines, 81 uncovered)
  - Lines 275-323: Rust import error paths
  - Lines 631-632, 656-668: Error handling
```

#### Test #1: Large Dataset Integration Test
**Target**: Cover multi-stage sampling (lines 980-1112)

```python
# tests/integration/test_thumbnail_large_dataset.py
@pytest.mark.integration
@pytest.mark.slow
def test_multi_stage_sampling_with_100_images(tmp_path):
    """Test 3-stage sampling with 100 images

    Covers:
    - Stage 1 sampling (20 images)
    - Stage 2 sampling (40 images)
    - Stage 3 sampling (60 images)
    - Trend analysis and ETA adjustment
    """
    # Create 100 test images (512x512)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    for i in range(100):
        img = Image.fromarray(
            np.random.randint(0, 255, (512, 512), dtype=np.uint8)
        )
        img.save(source_dir / f"slice_{i:04d}.tif")

    # Generate thumbnails with real ThumbnailManager
    manager = ThumbnailManager(None, MockProgressDialog(), QThreadPool())

    images, cancelled = manager.process_level(
        level=0,
        from_dir=str(source_dir),
        to_dir=str(tmp_path / "output"),
        seq_begin=0,
        seq_end=99,
        settings_hash={...},
        size=512,
        max_size=128,
        global_step=0
    )

    assert not cancelled
    assert len(images) == 50  # 100 images → 50 thumbnails

    # Verify all 3 stages executed
    # (Check logs or add stage tracking to manager)
```

**Expected Coverage Gain**: +25% for thumbnail_manager.py

---

#### Test #2: Real Worker Execution Test
**Target**: Cover Worker internals (lines 131-443)

```python
# tests/integration/test_thumbnail_worker_real.py
@pytest.mark.integration
def test_thumbnail_worker_real_execution(tmp_path):
    """Test actual Worker execution without mocks

    Covers:
    - Image loading (_load_images)
    - Averaging (_average_images)
    - Downsampling (_downsample_image)
    - File saving (_save_thumbnail)
    - Error handling paths
    """
    # Create 2 source images
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    img1 = Image.fromarray(np.ones((256, 256), dtype=np.uint8) * 100)
    img2 = Image.fromarray(np.ones((256, 256), dtype=np.uint8) * 150)
    img1.save(source_dir / "slice_0000.tif")
    img2.save(source_dir / "slice_0001.tif")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create real worker (NO MOCKS)
    worker = ThumbnailWorker(
        idx=0,
        seq=0,
        seq_begin=0,
        from_dir=str(source_dir),
        to_dir=str(output_dir),
        settings_hash={"prefix": "slice_", "index_length": 4, "file_type": "tif"},
        size=256,
        max_thumbnail_size=128,
        progress_dialog=MockProgressDialog(),
        level=0,
        seq_end=1
    )

    # Collect results
    results = []
    worker.signals.result.connect(lambda r: results.append(r))

    # Execute worker
    worker.run()

    # Verify results
    assert len(results) == 1
    idx, img_array, was_generated = results[0]
    assert idx == 0
    assert img_array is not None
    assert img_array.shape == (128, 128)  # Downsampled
    assert was_generated is True

    # Verify averaging: (100 + 150) / 2 = 125
    assert np.mean(img_array) == pytest.approx(125, abs=5)

    # Verify file saved
    assert (output_dir / "000000.tif").exists()
```

**Expected Coverage Gain**: +60% for thumbnail_worker.py

---

#### Test #3: Sequential Mode Test
**Target**: Cover sequential processing (lines 289-472)

```python
# tests/integration/test_thumbnail_sequential_mode.py
@pytest.mark.integration
def test_sequential_processing_mode(tmp_path):
    """Test non-threaded sequential mode for debugging

    Covers:
    - process_task_sequential() full execution
    - Sequential task processing
    - Progress tracking without threads
    """
    # Small dataset (10 images)
    source_dir = create_test_images(tmp_path, count=10)

    manager = ThumbnailManager(None, MockProgressDialog(), None)  # No threadpool

    # Force sequential mode by directly calling process_task_sequential
    images = manager.process_task_sequential(
        num_tasks=5,
        level=0,
        seq_begin=0,
        seq_end=9,
        from_dir=str(source_dir),
        to_dir=str(tmp_path / "output"),
        settings_hash={...},
        size=256,
        max_size=128
    )

    assert len(images) == 5
```

**Expected Coverage Gain**: +15% for thumbnail_manager.py

---

#### Test #4: Edge Cases
**Target**: Error handling paths

```python
# tests/integration/test_thumbnail_edge_cases.py
@pytest.mark.integration
class TestThumbnailEdgeCases:

    def test_corrupted_image_handling(self, tmp_path):
        """Test graceful handling of corrupted images"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create corrupted TIFF
        (source_dir / "slice_0000.tif").write_bytes(b"NOT A VALID TIFF")

        worker = ThumbnailWorker(...)
        # Should log error but not crash
        worker.run()
        # Verify error signal emitted

    def test_disk_full_scenario(self, tmp_path):
        """Test behavior when output disk is full"""
        # Mock disk full error
        with patch("PIL.Image.Image.save", side_effect=OSError("No space left")):
            worker = ThumbnailWorker(...)
            worker.run()
            # Verify error handling

    def test_permission_denied_output(self, tmp_path):
        """Test read-only output directory"""
        output_dir = tmp_path / "readonly"
        output_dir.mkdir(mode=0o444)  # Read-only

        worker = ThumbnailWorker(..., to_dir=str(output_dir))
        worker.run()
        # Verify permission error handled

    def test_unicode_filenames(self, tmp_path):
        """Test non-ASCII characters in paths"""
        source_dir = tmp_path / "소스이미지"  # Korean
        source_dir.mkdir()
        # Create images with unicode names
        # Verify processing succeeds

    def test_extremely_large_image(self, tmp_path):
        """Test memory handling with 8192x8192 image"""
        # Test memory efficient processing

    def test_empty_directory(self, tmp_path):
        """Test behavior with no images"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        manager = ThumbnailManager(...)
        images, cancelled = manager.process_level(..., from_dir=str(empty_dir))

        assert images == []
        assert not cancelled
```

**Expected Coverage Gain**: +10% across all modules

---

### Phase 1 Summary

**Estimated Effort**: 2 weeks
**Expected Results**:
- ✅ Pre-commit hooks passing
- ✅ Coverage: 48% → 65-70%
  - thumbnail_manager.py: 38% → 70%
  - thumbnail_worker.py: 21% → 80%
  - thumbnail_generator.py: 78% → 85%
- ✅ Dependency security scanning active
- ✅ All critical edge cases tested

---

## 🎯 Phase 2: Architecture Refactoring (Month 2-3)

**Goal**: Improve maintainability and type safety

### Task 1: Reduce type:ignore Usage (3-5 days)

**Current**: 28 occurrences across codebase
**Target**: < 10 occurrences

#### Approach:
1. **Protocol-based Parent Interface** (thumbnail_manager.py)

```python
# Create clear interface for parent objects
from typing import Protocol

class ThumbnailParent(Protocol):
    """Protocol for objects that can be thumbnail parents"""
    sampled_estimate_seconds: float
    sampled_estimate_str: str
    estimated_time_per_image: float
    estimated_total_time: float
    measured_images_per_second: float
    current_drive: str
    total_levels: int
    level_work_distribution: List[Dict[str, Union[int, float]]]
    weighted_total_work: float

class ThumbnailManager(QObject):
    def __init__(
        self,
        parent: Optional[ThumbnailParent],
        progress_dialog: Optional[ProgressDialog],
        threadpool: QThreadPool,
        shared_progress_manager: Optional[ProgressManager] = None
    ):
        self.parent = parent  # No type:ignore needed!
```

2. **Proper Type Annotations** (thumbnail_generator.py)

```python
# Before
def generate_python(self, directory: str, settings, threadpool, progress_dialog=None):  # type: ignore

# After
def generate_python(
    self,
    directory: str,
    settings: Dict[str, Any],
    threadpool: QThreadPool,
    progress_dialog: Optional[ProgressDialog] = None
) -> Optional[Dict[str, Any]]:
```

**Tasks**:
- [ ] Define ThumbnailParent Protocol
- [ ] Add proper type hints to generate_python()
- [ ] Fix remaining type:ignore in thumbnail modules
- [ ] Run mypy --strict to find hidden issues

**Expected**: 28 → 8 type:ignore comments

---

### Task 2: Refactor Large Files (1-2 weeks)

#### 2.1: Split thumbnail_manager.py (1164 lines → 3 files)

**Current Structure**:
```
thumbnail_manager.py (1164 lines)
├── ThumbnailManager class (coordination)
├── Sampling logic (300 lines)
├── Progress tracking (200 lines)
└── UI updates (200 lines)
```

**Proposed Structure**:
```
core/
├── thumbnail_manager.py (300 lines)
│   └── ThumbnailManager (coordination only)
├── thumbnail_sampling.py (200 lines)  # NEW
│   ├── SamplingStrategy (abstract base)
│   ├── MultiStageSampler (3-stage sampling)
│   └── SimpleSampler (fallback)
└── thumbnail_progress.py (200 lines)  # NEW
    └── ThumbnailProgressTracker
        ├── calculate_eta()
        ├── update_ui()
        └── format_time()
```

**Benefits**:
- Single Responsibility Principle
- Easier testing (mock sampling separately)
- Better code organization

**Tasks**:
- [ ] Extract sampling logic to thumbnail_sampling.py
- [ ] Extract progress tracking to thumbnail_progress.py
- [ ] Update imports in thumbnail_manager.py
- [ ] Add tests for new modules
- [ ] Update documentation

---

#### 2.2: Refactor main_window.py (1287 lines)

**Current**: God object controlling everything
**Target**: Delegate to specialized controllers

```python
# ui/controllers/thumbnail_controller.py (NEW)
class ThumbnailController:
    """Handles all thumbnail-related UI logic"""
    def __init__(self, main_window):
        self.window = main_window

    def on_create_thumbnail_clicked(self):
        """Handle thumbnail generation request"""

    def on_thumbnail_progress_update(self, progress):
        """Update thumbnail progress display"""

# ui/controllers/volume_controller.py (NEW)
class VolumeController:
    """Handles volume processing UI logic"""

# ui/controllers/export_controller.py (NEW)
class ExportController:
    """Handles export operations"""
```

**Tasks**:
- [ ] Create controller classes
- [ ] Move methods from main_window to controllers
- [ ] Update main_window to delegate to controllers
- [ ] Add controller tests (easier to test)

**Expected**: main_window.py: 1287 → 500 lines

---

### Task 3: Improve Error Handling (3-5 days)

**Current**: 20+ files with `except Exception`
**Target**: Specific exception handling

```python
# Before (Too broad)
try:
    result = process_image(path)
except Exception as e:
    logger.error(f"Error: {e}")
    return None  # Silent failure

# After (Specific)
try:
    result = process_image(path)
except (OSError, PermissionError) as e:
    logger.error(f"File access error for {path}: {e}", exc_info=True)
    raise  # Let caller decide
except ValueError as e:
    logger.error(f"Invalid image data in {path}: {e}")
    raise
except Exception as e:
    logger.critical(f"Unexpected error processing {path}: {e}", exc_info=True)
    raise  # Re-raise unexpected errors
```

**Tasks**:
- [ ] Audit all `except Exception` blocks
- [ ] Replace with specific exception types
- [ ] Add exception chaining (`raise ... from e`)
- [ ] Document expected exceptions in docstrings
- [ ] Add exception handling tests

---

### Phase 2 Summary

**Estimated Effort**: 2-3 months
**Expected Results**:
- ✅ Type safety: 28 → 8 type:ignore
- ✅ File sizes: Large files split into manageable modules
- ✅ Error handling: Specific exceptions, proper chaining
- ✅ Coverage: 70% → 80%

---

## 🎯 Phase 3: Production Readiness (Month 4-6)

**Goal**: Achieve production-grade quality

### Task 1: Performance Optimization

#### 1.1: Performance Regression Tests

```python
# tests/performance/test_thumbnail_performance.py
@pytest.mark.performance
class TestThumbnailPerformance:

    def test_thumbnail_generation_speed_100_images(self, benchmark):
        """Ensure thumbnail generation meets performance targets"""
        # Generate 100 thumbnails
        result = benchmark(generate_thumbnails, images=100)

        # Should process at least 50 images/second
        assert result.stats.mean < 2.0  # 100 images in < 2 seconds

    def test_memory_usage_large_dataset(self):
        """Ensure memory stays within bounds"""
        import tracemalloc

        tracemalloc.start()
        generate_thumbnails(images=1000)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not exceed 500MB peak
        assert peak < 500 * 1024 * 1024
```

**Tasks**:
- [ ] Add pytest-benchmark
- [ ] Create performance test suite
- [ ] Set up performance CI job
- [ ] Create performance dashboard

---

#### 1.2: Algorithm Optimizations

**Minor inefficiencies identified**:

```python
# utils/image_utils.py:133-138
# Before (Repeated comparisons)
if img1.dtype == np.uint8:
    temp_dtype = np.uint16
elif img1.dtype == np.uint16:
    temp_dtype = np.uint32
else:
    temp_dtype = np.float64

# After (Lookup table)
DTYPE_PROMOTION = {
    np.dtype('uint8'): np.uint16,
    np.dtype('uint16'): np.uint32,
}
temp_dtype = DTYPE_PROMOTION.get(img1.dtype, np.float64)
```

**Tasks**:
- [ ] Optimize dtype checking
- [ ] Cache repeated file path calculations
- [ ] Add memory pooling for large arrays
- [ ] Profile and optimize hot paths

---

### Task 2: Documentation Overhaul

#### 2.1: Complete API Documentation

```python
# Before (Incomplete)
def get_file_list(self, directory_path: str, settings_hash: Dict) -> List[str]:
    """Get sorted list of CT image file paths based on detected pattern"""

# After (Complete)
def get_file_list(self, directory_path: str, settings_hash: Dict) -> List[str]:
    """Get sorted list of CT image file paths based on detected pattern.

    Generates full file paths for a CT image sequence using the pattern
    information from sort_file_list_from_dir(). Handles missing files
    gracefully by logging warnings.

    Args:
        directory_path: Base directory containing CT images. Must exist
            and be readable.
        settings_hash: Dictionary containing pattern information with keys:
            - 'prefix': File name prefix (e.g., 'slice_')
            - 'file_type': Extension without dot (e.g., 'tif')
            - 'seq_begin': First sequence number (e.g., 1)
            - 'seq_end': Last sequence number (e.g., 100)
            - 'index_length': Zero-padding length (e.g., 4 for '0001')

    Returns:
        List of absolute file paths in sequence order. May be shorter
        than seq_end-seq_begin+1 if some files are missing.

    Raises:
        KeyError: If settings_hash is missing required keys.
        ValueError: If sequence range is invalid (begin > end).
        FileSecurityError: If directory path fails security validation.

    Example:
        >>> handler = FileHandler()
        >>> settings = handler.sort_file_list_from_dir('/data/scan1')
        >>> files = handler.get_file_list('/data/scan1', settings)
        >>> len(files)
        100
        >>> files[0]
        '/data/scan1/slice_0001.tif'

    Warning:
        Missing files in the sequence are logged but don't raise errors.
        Check the returned list length if you need all files.

    See Also:
        - sort_file_list_from_dir(): Detects pattern from directory
        - security.file_validator: Path security validation
    """
```

**Tasks**:
- [ ] Add comprehensive docstrings to all public APIs
- [ ] Add usage examples to module docstrings
- [ ] Document thread safety guarantees
- [ ] Translate security module comments to English

---

#### 2.2: Architecture Documentation

Create comprehensive architecture docs:

```
docs/architecture/
├── overview.md                    # High-level architecture
├── thumbnail_pipeline.md          # Thumbnail generation flow
├── threading_model.md             # Thread safety and concurrency
├── error_handling.md              # Exception handling patterns
└── extension_guide.md             # How to add new features
```

**Tasks**:
- [ ] Document system architecture
- [ ] Create sequence diagrams
- [ ] Document design decisions
- [ ] Add developer onboarding guide

---

### Task 3: Property-Based Testing

Use Hypothesis for invariant testing:

```python
from hypothesis import given, strategies as st

@given(
    width=st.integers(min_value=1, max_value=4096),
    height=st.integers(min_value=1, max_value=4096),
    factor=st.integers(min_value=2, max_value=8)
)
def test_downsample_preserves_shape_invariant(width, height, factor):
    """Downsampling should always produce correctly sized output"""
    img = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    result = downsample_image(img, factor=factor, method="subsample")

    expected_h = height // factor
    expected_w = width // factor
    assert result.shape == (expected_h, expected_w)

@given(
    seq_begin=st.integers(min_value=0, max_value=1000),
    seq_end=st.integers(min_value=0, max_value=1000),
)
def test_file_list_ordering_invariant(seq_begin, seq_end):
    """File list should always be sorted regardless of input"""
    if seq_begin > seq_end:
        seq_begin, seq_end = seq_end, seq_begin

    files = get_file_list(directory, {"seq_begin": seq_begin, "seq_end": seq_end, ...})

    # Files should be sorted
    assert files == sorted(files)
```

**Tasks**:
- [ ] Add hypothesis tests for image operations
- [ ] Add hypothesis tests for file operations
- [ ] Add hypothesis tests for progress calculations
- [ ] Configure hypothesis settings in pytest.ini

---

### Phase 3 Summary

**Estimated Effort**: 3-4 months
**Expected Results**:
- ✅ Coverage: 80% → 90%+
- ✅ Performance: Regression tests, benchmarks
- ✅ Documentation: Complete API docs, architecture guide
- ✅ Quality: Property-based testing, production-ready

---

## 📊 Overall Timeline

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Critical Fixes                    [Weeks 1-2]      │
│ ├─ Pre-commit hooks                        [1-2 hours]      │
│ ├─ Dependency management                   [2 hours]        │
│ └─ Deep integration tests                  [1 week]         │
│    Coverage: 48% → 65-70%                                   │
├─────────────────────────────────────────────────────────────┤
│ Phase 2: Architecture Refactoring          [Months 2-3]     │
│ ├─ Reduce type:ignore                      [3-5 days]       │
│ ├─ Split large files                       [1-2 weeks]      │
│ └─ Improve error handling                  [3-5 days]       │
│    Coverage: 70% → 80%                                      │
├─────────────────────────────────────────────────────────────┤
│ Phase 3: Production Readiness              [Months 4-6]     │
│ ├─ Performance optimization                [2 weeks]        │
│ ├─ Documentation overhaul                  [3 weeks]        │
│ └─ Property-based testing                  [1 week]         │
│    Coverage: 80% → 90%+                                     │
└─────────────────────────────────────────────────────────────┘

Total: 6 months to production-ready
Quick wins: 2 weeks to 65% coverage + unblocked CI
```

---

## 🎯 Success Metrics

### Phase 1 (2 weeks)
- [ ] Pre-commit hooks passing ✅
- [ ] Coverage ≥ 65%
  - [ ] thumbnail_manager.py ≥ 70%
  - [ ] thumbnail_worker.py ≥ 80%
  - [ ] thumbnail_generator.py ≥ 85%
- [ ] Dependencies pinned with version ranges
- [ ] Security scanning CI active
- [ ] 5+ new integration tests added

### Phase 2 (3 months)
- [ ] type:ignore count ≤ 10
- [ ] No file > 800 lines
- [ ] Coverage ≥ 80%
- [ ] All exceptions properly typed
- [ ] main_window.py refactored to controllers

### Phase 3 (6 months)
- [ ] Coverage ≥ 90%
- [ ] Performance regression tests active
- [ ] Complete API documentation
- [ ] Property-based tests for core logic
- [ ] Production deployment ready

---

## 🔄 Continuous Improvements

Throughout all phases:

### Code Quality Gates
- [ ] mypy --strict passes
- [ ] flake8 with no warnings
- [ ] black formatting enforced
- [ ] isort import sorting
- [ ] bandit security checks

### CI/CD Pipeline
- [ ] Tests run on every PR
- [ ] Coverage reported to Codecov
- [ ] Performance benchmarks tracked
- [ ] Security scans weekly
- [ ] Automated releases on tag

### Documentation
- [ ] README kept up-to-date
- [ ] CHANGELOG maintained
- [ ] API docs auto-generated
- [ ] Examples tested in CI

---

## 📝 Next Steps

**Immediate Actions** (This Week):
1. [ ] Review and approve this plan
2. [ ] Create GitHub issues for Phase 1 tasks
3. [ ] Fix pre-commit hook issues (2 hours)
4. [ ] Pin dependency versions (2 hours)
5. [ ] Start large dataset test implementation

**Questions to Resolve**:
- Should we tackle sequential mode testing? (Low priority, but adds 15% coverage)
- Korean comments in security module - translate or keep bilingual?
- Rust module testing - how to handle in CI without Rust installed?

---

## 📚 References

- [Previous Plan: 20251002_068_next_improvements_plan.md](20251002_068_next_improvements_plan.md)
- [Phase 1-3 Completion: 20251002_069_phase1_2_3_complete.md](20251002_069_phase1_2_3_complete.md)
- [Code Quality Plan: 20251002_067_code_quality_improvement_plan.md](20251002_067_code_quality_improvement_plan.md)

---

**Status**: 📋 Ready for review and implementation
**Priority**: High - Pre-commit hooks blocking development
**Next Review**: After Phase 1 completion (2 weeks)
