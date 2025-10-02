# CTHarvester - Next Improvements Plan
**Date:** 2025-10-02
**Following:** Code Quality Improvement Plan (067)

## Overview
Following the successful completion of the 7-phase code quality improvement plan, this document outlines the next set of improvements to further enhance code quality, maintainability, and performance.

---

## Phase 1: Type Hints Expansion (Week 1-2, ~10 hours)

### Current State
- Core modules: 46.7% type hint coverage (28/60 functions)
- Target: 80%+ coverage

### Tasks

#### 1.1 Core Module Type Hints (6 hours)
**Files to update:**
- `core/progress_manager.py` (legacy, needs full type hints)
- `core/volume_processor.py` (partial coverage)
- `core/thumbnail_manager.py` (partial coverage)

**Actions:**
- Add return type hints to all public methods
- Add parameter type hints using proper types:
  - Use `Optional[T]` for nullable types
  - Use `List[T]`, `Dict[K, V]` for collections
  - Use `Tuple[T, ...]` for tuples
  - Use `Union[T, U]` sparingly (prefer Optional)
- Add type hints to class attributes using `__init__` annotations

**Example:**
```python
# Before
def process_volume(self, data, settings):
    ...

# After
def process_volume(
    self,
    data: np.ndarray,
    settings: Dict[str, Any]
) -> Tuple[np.ndarray, Dict[str, int]]:
    ...
```

#### 1.2 Utils Module Type Hints (3 hours)
**Files to update:**
- `utils/worker.py` (signals need proper typing)
- `utils/file_utils.py` (complete coverage)

**Actions:**
- Use `PyQt5.QtCore.pyqtSignal` types properly
- Add `Callable` types for callbacks
- Document signal signatures in docstrings

#### 1.3 Validation & Testing (1 hour)
**Actions:**
- Run mypy with stricter settings:
  ```bash
  mypy core/ utils/ --strict --show-error-codes
  ```
- Fix all type errors
- Update `pyproject.toml` to enforce stricter rules:
  ```toml
  [[tool.mypy.overrides]]
  module = ["core.*", "utils.*"]
  disallow_untyped_defs = true
  disallow_any_generics = true
  ```

**Success Criteria:**
- ✅ 80%+ functions have type hints
- ✅ mypy passes with --strict on core/ and utils/
- ✅ No type: ignore comments added

---

## Phase 2: Integration Tests Expansion (Week 2-3, ~12 hours)

### Current State
- Mostly unit tests with mocking
- Few integration tests for full workflows
- Target: Complete workflow coverage

### Tasks

#### 2.1 Thumbnail Workflow Integration Tests (4 hours)
**File:** `tests/integration/test_thumbnail_complete_workflow.py`

**Test scenarios:**
1. **Full thumbnail generation workflow**
   - Load directory → Generate thumbnails → Load results
   - Verify all levels created correctly
   - Check file integrity

2. **Rust fallback scenario**
   - Mock Rust failure → Verify Python fallback
   - Compare results consistency

3. **Large dataset handling**
   - 1000+ images
   - Memory usage monitoring
   - Performance benchmarks

**Example test:**
```python
@pytest.mark.integration
@pytest.mark.slow
def test_complete_thumbnail_workflow_with_fallback():
    """Test complete workflow with Rust failure fallback"""
    # Setup large test dataset
    temp_dir = create_test_images(count=1000, size=(2048, 2048))

    # Force Rust failure
    with patch('ct_thumbnail.build_thumbnails', side_effect=ImportError):
        result = generate_thumbnails(temp_dir)

    # Verify Python fallback succeeded
    assert result['success'] is True
    assert_all_levels_generated(temp_dir)
    assert_memory_within_limits()
```

#### 2.2 UI Integration Tests (4 hours)
**File:** `tests/integration/test_ui_workflows.py`

**Test scenarios:**
1. **Complete UI workflow**
   - Open directory → Generate thumbnails → Navigate → Export
   - Test with real Qt widgets (not mocked)

2. **Settings persistence**
   - Change settings → Close → Reopen → Verify settings

3. **Error recovery**
   - Simulate errors → Verify UI recovery
   - Check progress dialog cleanup

#### 2.3 Export Integration Tests (2 hours)
**File:** `tests/integration/test_export_complete.py`

**Test scenarios:**
1. **OBJ export with real volume data**
   - Load real CT stack
   - Generate mesh
   - Verify OBJ file validity

2. **Image stack export**
   - Export with cropping
   - Verify output quality
   - Check all images exported

#### 2.4 Performance Regression Tests (2 hours)
**File:** `tests/integration/test_performance_benchmarks.py`

**Test scenarios:**
1. **Thumbnail generation speed**
   - Benchmark Rust vs Python
   - Track performance over time
   - Alert on >20% regression

2. **Memory usage**
   - Monitor peak memory
   - Verify no memory leaks
   - Check garbage collection

**Example:**
```python
@pytest.mark.benchmark
def test_thumbnail_generation_performance(benchmark):
    """Benchmark thumbnail generation speed"""
    def setup():
        return create_test_images(count=100)

    def run(temp_dir):
        generate_thumbnails(temp_dir)

    result = benchmark.pedantic(run, setup=setup, rounds=3)

    # Assert performance threshold
    assert result.stats.mean < 30.0  # seconds
```

**Success Criteria:**
- ✅ 15+ integration tests covering full workflows
- ✅ Performance benchmarks established
- ✅ Memory leak detection in place

---

## Phase 3: Performance Profiling Automation (Week 3-4, ~8 hours)

### Current State
- Manual performance testing
- No automated profiling
- Target: Continuous performance monitoring

### Tasks

#### 3.1 Profiling Infrastructure (3 hours)
**File:** `scripts/profile_performance.py`

**Features:**
- CPU profiling with cProfile
- Memory profiling with memory_profiler
- Line-by-line profiling for hotspots
- JSON output for tracking

**Implementation:**
```python
import cProfile
import pstats
from memory_profiler import profile

def profile_thumbnail_generation(directory: str):
    """Profile thumbnail generation performance"""
    profiler = cProfile.Profile()

    profiler.enable()
    generate_thumbnails(directory)
    profiler.disable()

    # Save stats
    stats = pstats.Stats(profiler)
    stats.dump_stats('profile_results.prof')

    # Generate report
    return generate_performance_report(stats)
```

#### 3.2 Performance Metrics Collection (2 hours)
**File:** `scripts/collect_performance_metrics.py`

**Metrics to collect:**
1. **Thumbnail generation:**
   - Images per second
   - Memory usage per image
   - Disk I/O statistics

2. **UI responsiveness:**
   - Frame rate during operations
   - Event loop lag
   - Qt signal/slot overhead

3. **Export operations:**
   - Mesh generation time
   - OBJ write speed
   - Image export throughput

#### 3.3 GitHub Actions Integration (2 hours)
**File:** `.github/workflows/performance-tracking.yml`

**Workflow:**
```yaml
name: Performance Tracking

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run performance benchmarks
        run: |
          python scripts/profile_performance.py
          python scripts/collect_performance_metrics.py

      - name: Compare with baseline
        run: |
          python scripts/compare_performance.py \
            --baseline performance_baseline.json \
            --current performance_current.json \
            --threshold 20

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: performance-results
          path: |
            profile_results.prof
            performance_report.json
```

#### 3.4 Visualization & Reporting (1 hour)
**File:** `scripts/visualize_performance.py`

**Features:**
- Generate performance graphs (matplotlib)
- Historical trend analysis
- Regression detection
- HTML report generation

**Success Criteria:**
- ✅ Automated profiling on every main branch push
- ✅ Performance regression alerts (>20% slowdown)
- ✅ Historical performance tracking
- ✅ Visual performance reports

---

## Phase 4: Advanced Testing Patterns (Week 4, ~5 hours)

### Tasks

#### 4.1 Property-Based Testing (2 hours)
**Install:** `pip install hypothesis`

**File:** `tests/property/test_image_properties.py`

**Test examples:**
```python
from hypothesis import given, strategies as st

@given(
    width=st.integers(min_value=1, max_value=4096),
    height=st.integers(min_value=1, max_value=4096),
    bit_depth=st.sampled_from([8, 16])
)
def test_downsample_preserves_aspect_ratio(width, height, bit_depth):
    """Property: Downsampling preserves aspect ratio"""
    img = create_test_image(width, height, bit_depth)
    downsampled = downsample_image(img, factor=2)

    original_ratio = width / height
    new_ratio = downsampled.shape[1] / downsampled.shape[0]

    assert abs(original_ratio - new_ratio) < 0.01
```

#### 4.2 Mutation Testing (2 hours)
**Install:** `pip install mutmut`

**Configuration:** `.mutmut-config`
```python
def pre_mutation(context):
    # Skip test files
    if 'test_' in context.filename:
        context.skip = True
```

**Run mutation testing:**
```bash
mutmut run --paths-to-mutate=core/,utils/
mutmut results
mutmut html  # Generate report
```

#### 4.3 Snapshot Testing (1 hour)
**Install:** `pip install pytest-snapshot`

**File:** `tests/snapshots/test_ui_snapshots.py`

**Use case:** Verify UI layouts don't change unexpectedly
```python
def test_main_window_layout(snapshot):
    """Snapshot test for main window layout"""
    window = CTHarvesterMainWindow()
    layout_tree = capture_layout_tree(window)

    snapshot.assert_match(layout_tree, 'main_window_layout.json')
```

**Success Criteria:**
- ✅ 10+ property-based tests
- ✅ 80%+ mutation score
- ✅ Key UI layouts snapshot tested

---

## Implementation Timeline

```
Week 1-2: Type Hints Expansion
├── Day 1-3: Core modules
├── Day 4-5: Utils modules
└── Day 6-7: Validation & documentation

Week 2-3: Integration Tests
├── Day 8-9: Thumbnail workflow tests
├── Day 10-11: UI integration tests
├── Day 12: Export tests
└── Day 13-14: Performance benchmarks

Week 3-4: Performance Profiling
├── Day 15-16: Profiling infrastructure
├── Day 17: Metrics collection
├── Day 18-19: CI/CD integration
└── Day 20: Visualization

Week 4: Advanced Testing
├── Day 21-22: Property-based testing
├── Day 23-24: Mutation testing
└── Day 25: Snapshot testing
```

**Total Time: ~35 hours over 4 weeks**

---

## Metrics & Success Criteria

### Overall Goals
- ✅ Type hint coverage: 80%+ (from 46.7%)
- ✅ Integration test count: 15+ new tests
- ✅ Performance monitoring: Automated & continuous
- ✅ Test quality: 80%+ mutation score
- ✅ No performance regressions >20%

### Phase-specific KPIs

**Phase 1:**
- [ ] 80%+ functions typed in core/
- [ ] 80%+ functions typed in utils/
- [ ] mypy --strict passes
- [ ] No type: ignore comments

**Phase 2:**
- [ ] 15+ integration tests
- [ ] Full workflow coverage
- [ ] Performance baselines established
- [ ] Memory leak detection

**Phase 3:**
- [ ] Automated profiling in CI/CD
- [ ] Performance dashboard
- [ ] Regression alerts configured
- [ ] Historical tracking active

**Phase 4:**
- [ ] 10+ property tests
- [ ] 80%+ mutation score
- [ ] UI snapshot tests
- [ ] Advanced testing patterns documented

---

## Risk Management

### Potential Risks
1. **Type hints breaking existing code**
   - Mitigation: Gradual rollout, extensive testing

2. **Integration tests flaky on CI**
   - Mitigation: Use retry mechanisms, proper fixtures

3. **Performance profiling overhead**
   - Mitigation: Run on schedule, not every commit

4. **Mutation testing too slow**
   - Mitigation: Run on schedule, parallel execution

---

## Next Steps

1. **Immediate (This week):**
   - Set up development branch
   - Install additional dependencies
   - Create baseline metrics

2. **Short-term (Week 1-2):**
   - Start Phase 1 (Type hints)
   - Document progress in daily logs

3. **Long-term (Month 2):**
   - Complete all phases
   - Update quality gates
   - Review and iterate

---

**Document Status:** Draft → Review → Approved → In Progress
**Last Updated:** 2025-10-02
**Next Review:** After Phase 1 completion
