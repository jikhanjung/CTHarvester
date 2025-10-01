# UI Testing Plan for CTHarvester

**Date**: 2025-10-01
**Project**: CTHarvester
**Phase**: UI Testing Implementation
**Status**: 📋 Planning

---

## Executive Summary

This document outlines a comprehensive testing strategy for CTHarvester's UI components. The plan follows a progressive approach, starting with simple, isolated widgets and gradually moving to complex, integrated components.

### Goals
- Achieve **80%+ test coverage** for UI components
- Establish **pytest-qt** testing infrastructure
- Create **reusable test fixtures** and utilities
- Ensure **cross-platform compatibility** (Windows, Linux, macOS)
- Enable **automated UI testing** in CI/CD pipeline

---

## Current State Analysis

### UI Component Inventory

| Component | File | Lines | Complexity | Test Priority |
|-----------|------|-------|------------|---------------|
| VerticalTimeline | ui/widgets/vertical_stack_slider.py | 414 | Low | ⭐⭐⭐ High |
| InfoDialog | ui/dialogs/info_dialog.py | ~100 | Low | ⭐⭐⭐ High |
| ShortcutDialog | ui/dialogs/shortcut_dialog.py | ~150 | Low | ⭐⭐⭐ High |
| SettingsDialog | ui/dialogs/settings_dialog.py | ~400 | Medium | ⭐⭐ Medium |
| ProgressDialog | ui/dialogs/progress_dialog.py | ~600 | Medium | ⭐⭐ Medium |
| ObjectViewer2D | ui/widgets/object_viewer_2d.py | ~300 | Medium | ⭐⭐ Medium |
| MCubeWidget | ui/widgets/mcube_widget.py | ~500 | High | ⭐ Low |
| CTHarvesterMainWindow | ui/main_window.py | ~3000 | Very High | ⭐ Low |
| **Total** | | **~4,800** | | |

### Existing Test Infrastructure
- ✅ **pytest-qt** installed and configured
- ✅ Qt marker defined in `pytest.ini`
- ✅ Basic Qt test example in `test_progress_manager.py`
- ✅ Test markers: `@pytest.mark.qt`, `@pytest.mark.integration`, `@pytest.mark.slow`

### Current Test Coverage
- **UI Components**: 0% (no dedicated UI tests)
- **Core Modules**: ~95% (195 tests)
- **Overall**: ~70% (need UI coverage to reach 80%+)

---

## Testing Strategy

### Phase 1: Foundation (Priority: High, Duration: 1-2 days)

**Objective**: Establish testing infrastructure and test simple widgets

#### 1.1 Test Infrastructure Setup
- Create `tests/ui/` directory structure
- Create `tests/ui/conftest.py` with shared fixtures
- Set up QApplication singleton for test session
- Create utility functions for common test patterns

#### 1.2 Simple Widget Tests
**Target**: VerticalTimeline (414 lines)

**Test Categories**:
1. **Initialization Tests** (5 tests)
   - Default values (min=0, max=100)
   - Custom range initialization
   - Widget properties (size hints, focus policy)
   - Signal connections exist
   - Visual properties (margins, widths)

2. **Value Management Tests** (10 tests)
   - `setLower()` / `setUpper()` / `setCurrent()`
   - `values()` returns correct tuple
   - `setRange()` updates all values
   - `setRangeValues()` updates lower/upper
   - `setValues()` batch update
   - Value clamping to min/max
   - Lower/upper relationship (lower ≤ upper)
   - Current independent of lower/upper
   - Range inversion handling
   - Zero range (min == max)

3. **Signal Emission Tests** (8 tests)
   - `lowerChanged` signal on setLower()
   - `upperChanged` signal on setUpper()
   - `currentChanged` signal on setCurrent()
   - `rangeChanged` signal on range updates
   - Signal NOT emitted when value unchanged
   - Multiple signals on setRange()
   - Signal parameters correct
   - Signal blocking/unblocking

4. **Keyboard Interaction Tests** (7 tests)
   - Up/Down arrow keys (step)
   - PageUp/PageDown keys (page step)
   - Home/End keys (min/max)
   - 'L' key sets lower to current
   - 'U' key sets upper to current
   - Step/page configuration
   - Focus requirement

5. **Mouse Interaction Tests** (8 tests)
   - Click empty area moves current
   - Drag current handle
   - Drag lower handle
   - Drag upper handle
   - Shift+drag moves range (preserves span)
   - Mouse hover tooltips
   - Cursor changes on drag
   - Release resets cursor

6. **Wheel Interaction Tests** (3 tests)
   - Wheel up increments current
   - Wheel down decrements current
   - Ctrl+wheel uses page step

7. **Snap Points Tests** (5 tests)
   - `setSnapPoints()` with tolerance
   - Snap to nearest point within tolerance
   - No snap outside tolerance
   - Snap points sorting
   - Empty snap points list

8. **Edge Cases** (6 tests)
   - Negative range values
   - Very large range (0 to 1,000,000)
   - Single value range (min == max)
   - Reversed range input (max, min) → auto-swap
   - Rapid value updates
   - Widget resize during interaction

**Estimated Tests**: ~50 tests
**Expected Coverage**: 90%+ for VerticalTimeline

---

### Phase 2: Simple Dialogs (Priority: High, Duration: 1-2 days)

**Objective**: Test static, information-display dialogs

#### 2.1 InfoDialog Tests
**Test Categories**:
1. Initialization and display
2. Content rendering (HTML support)
3. Close button functionality
4. Modal behavior
5. Keyboard shortcuts (ESC to close)

**Estimated Tests**: ~10 tests

#### 2.2 ShortcutDialog Tests
**Test Categories**:
1. Initialization with shortcuts data
2. Table rendering (headers, rows)
3. Shortcut display formatting
4. Search/filter functionality (if exists)
5. Close behavior

**Estimated Tests**: ~12 tests

**Phase 2 Total**: ~22 tests

---

### Phase 3: Interactive Dialogs (Priority: Medium, Duration: 2-3 days)

**Objective**: Test dialogs with user input and state changes

#### 3.1 SettingsDialog Tests
**Test Categories**:
1. **Form Input Tests** (10 tests)
   - Load settings from YAML
   - Display current values in UI
   - Modify settings via UI controls
   - Validation (numeric ranges, paths)
   - Reset to defaults
   - Cancel discards changes
   - Save persists to YAML
   - Invalid input handling
   - Required field validation
   - Path browsing (mocked)

2. **UI State Tests** (5 tests)
   - Enable/disable dependent controls
   - Tab navigation
   - Keyboard shortcuts
   - Focus management
   - Dialog size/position persistence

**Estimated Tests**: ~15 tests

#### 3.2 ProgressDialog Tests
**Test Categories**:
1. **Progress Updates** (8 tests)
   - Initialize with task name
   - Update progress value
   - Update progress text
   - Progress bar visual update
   - Percentage display
   - ETA calculation display
   - Speed display
   - Completion detection

2. **Cancellation** (5 tests)
   - Cancel button emits signal
   - Cancel disables button
   - Cancel during operation
   - Cannot cancel after completion
   - Keyboard shortcut (ESC)

3. **Modern vs Classic** (3 tests)
   - ModernProgressDialog initialization
   - Style differences
   - Functionality parity

**Estimated Tests**: ~16 tests

**Phase 3 Total**: ~31 tests

---

### Phase 4: Complex Widgets (Priority: Medium, Duration: 2-3 days)

**Objective**: Test image display and interaction widgets

#### 4.1 ObjectViewer2D Tests
**Test Categories**:
1. **Image Display** (8 tests)
   - Load and display image
   - Image scaling to fit
   - Aspect ratio preservation
   - Empty/null image handling
   - Image format support (BMP, PNG, TIFF)
   - Large image handling
   - Grayscale vs RGB
   - Bit depth handling (8-bit, 16-bit)

2. **Interaction** (7 tests)
   - Mouse hover coordinates
   - Click events
   - Bounding box drawing
   - Crop region selection
   - Zoom in/out
   - Pan/scroll
   - Reset view

3. **Visual Effects** (5 tests)
   - Threshold adjustment
   - Contrast/brightness
   - Invert mode
   - Overlay rendering
   - Cursor styles

**Estimated Tests**: ~20 tests

**Phase 4 Total**: ~20 tests

---

### Phase 5: OpenGL Widget (Priority: Low, Duration: 1-2 days)

**Objective**: Limited testing of 3D rendering widget

#### 5.1 MCubeWidget Tests
**Challenges**:
- OpenGL context requires display (CI limitation)
- Rendering output hard to validate
- Performance-intensive operations

**Test Categories**:
1. **Basic Functionality** (5 tests, CI-skipped)
   - Widget initialization
   - OpenGL context creation
   - Mesh loading (mock data)
   - Rotation/zoom state changes
   - Resource cleanup

2. **Mesh Generation Thread** (8 tests)
   - Thread initialization
   - Progress signals
   - Completion signals
   - Cancellation
   - Error handling
   - Memory management
   - Multiple sequential operations
   - Thread cleanup

**Estimated Tests**: ~13 tests (5 skipped in CI)

**Phase 5 Total**: ~13 tests

---

### Phase 6: Main Window Integration (Priority: Low, Duration: 3-5 days)

**Objective**: Integration tests for main application workflow

#### 6.1 CTHarvesterMainWindow Tests
**Challenges**:
- Very complex (3000+ lines)
- Many dependencies (file I/O, workers, OpenGL)
- Long-running operations
- External file dependencies

**Test Strategy**:
- Focus on **integration scenarios**, not exhaustive unit tests
- Use **mocking extensively** for I/O and workers
- Test **critical user workflows** end-to-end

**Test Categories**:
1. **Initialization** (5 tests)
   - Window creation
   - Menu/toolbar setup
   - Default state
   - Settings loading
   - Recent files list

2. **File Operations** (8 tests, mocked I/O)
   - Open directory
   - Load image stack
   - Thumbnail generation workflow
   - Save cropped images
   - Export 3D model
   - Error handling (invalid paths)
   - Large dataset handling (progress)
   - Cancellation

3. **UI State Management** (6 tests)
   - Enable/disable controls based on state
   - Crop region selection workflow
   - Threshold adjustment
   - Level-of-detail switching
   - Timeline synchronization
   - Settings persistence

4. **Worker Integration** (5 tests)
   - Thumbnail generation worker
   - Progress updates from workers
   - Worker completion handling
   - Worker error handling
   - Multiple workers (sequential)

**Estimated Tests**: ~24 tests

**Phase 6 Total**: ~24 tests

---

## Test Infrastructure Details

### Shared Fixtures (`tests/ui/conftest.py`)

```python
import pytest
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """QApplication singleton for entire test session"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit - pytest-qt handles cleanup

@pytest.fixture
def qtbot(qapp, qtbot):
    """qtbot fixture with QApplication dependency"""
    return qtbot

@pytest.fixture
def temp_settings_file(tmp_path):
    """Create temporary YAML settings file"""
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("""
        language: en
        log_level: INFO
        thumbnail_quality: high
    """)
    return settings_file

@pytest.fixture
def mock_image_stack(tmp_path):
    """Create temporary image stack for testing"""
    from PIL import Image
    import numpy as np

    image_dir = tmp_path / "images"
    image_dir.mkdir()

    for i in range(10):
        img_array = np.ones((100, 100), dtype=np.uint8) * (i * 25)
        img = Image.fromarray(img_array)
        img.save(image_dir / f"slice_{i:04d}.tif")

    return image_dir

@pytest.fixture
def mock_thumbnail_worker(mocker):
    """Mock ThumbnailWorker to avoid actual processing"""
    return mocker.patch('core.thumbnail_worker.ThumbnailWorker')
```

### Test Utilities (`tests/ui/test_utils.py`)

```python
from PyQt5.QtCore import Qt, QPoint

def simulate_mouse_drag(qtbot, widget, start_pos, end_pos):
    """Simulate mouse drag from start to end position"""
    qtbot.mousePress(widget, Qt.LeftButton, pos=start_pos)
    qtbot.mouseMove(widget, pos=end_pos)
    qtbot.mouseRelease(widget, Qt.LeftButton, pos=end_pos)

def wait_for_signal_or_timeout(qtbot, signal, timeout=1000):
    """Wait for signal with timeout, return whether it was emitted"""
    try:
        with qtbot.waitSignal(signal, timeout=timeout):
            pass
        return True
    except:
        return False

def get_widget_center(widget):
    """Get center point of widget"""
    rect = widget.rect()
    return QPoint(rect.width() // 2, rect.height() // 2)
```

---

## Coverage Goals

### Target Coverage by Phase

| Phase | Component | Estimated Tests | Target Coverage |
|-------|-----------|-----------------|-----------------|
| 1 | VerticalTimeline | 50 | 90%+ |
| 2 | InfoDialog, ShortcutDialog | 22 | 85%+ |
| 3 | SettingsDialog, ProgressDialog | 31 | 80%+ |
| 4 | ObjectViewer2D | 20 | 75%+ |
| 5 | MCubeWidget | 13 | 60%+ (OpenGL limited) |
| 6 | MainWindow | 24 | 50%+ (integration focus) |
| **Total** | **All UI** | **~160** | **70-75%** |

### Overall Project Coverage Goal
- Current: ~70% (core modules only)
- After UI tests: **80-85%** (entire project)

---

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml (add to existing)
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.12', '3.13']

    steps:
      - name: Install Qt dependencies (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libxkbcommon-x11-0 \
            libxcb-icccm4 \
            libxcb-image0 \
            libxcb-keysyms1 \
            libxcb-randr0 \
            libxcb-render-util0 \
            libxcb-xinerama0 \
            libxcb-xfixes0 \
            x11-utils \
            xvfb

      - name: Run tests with xvfb (Linux)
        if: runner.os == 'Linux'
        run: xvfb-run pytest tests/ -v --cov=. --cov-report=xml

      - name: Run tests (Windows/macOS)
        if: runner.os != 'Linux'
        run: pytest tests/ -v --cov=. --cov-report=xml

      - name: Run UI tests separately
        run: pytest tests/ui/ -v -m qt --tb=short
```

### Platform-Specific Skip Decorators

```python
import sys
import pytest

# Skip OpenGL tests on CI without display
skip_no_display = pytest.mark.skipif(
    not os.environ.get('DISPLAY') and sys.platform.startswith('linux'),
    reason="No display available (CI environment)"
)

# Skip macOS-specific issues
skip_macos = pytest.mark.skipif(
    sys.platform == 'darwin',
    reason="macOS-specific Qt behavior"
)

@skip_no_display
def test_opengl_widget():
    # OpenGL tests here
    pass
```

---

## Risk Assessment

### High Risk
1. **OpenGL tests on CI**: Limited display support
   - **Mitigation**: Skip OpenGL rendering tests, focus on logic

2. **Platform-specific Qt behavior**: Different OS behaviors
   - **Mitigation**: Platform-specific skips, test on all platforms

3. **Long-running operations**: Thumbnail generation, mesh generation
   - **Mitigation**: Mock workers, use small test datasets

### Medium Risk
1. **File I/O dependencies**: Real file operations
   - **Mitigation**: Use tmp_path fixtures, mock file dialogs

2. **External dependencies**: Image libraries, OpenGL
   - **Mitigation**: Graceful degradation, skip if unavailable

3. **Timing issues**: Qt event loop, signals
   - **Mitigation**: Use pytest-qt waitSignal, appropriate timeouts

### Low Risk
1. **Test maintenance**: UI changes break tests
   - **Mitigation**: Focus on public API, avoid testing internals

---

## Success Metrics

### Quantitative
- ✅ **160+ UI tests** created
- ✅ **80%+ overall coverage** (including UI)
- ✅ **All tests pass** on 3 platforms (Windows, Linux, macOS)
- ✅ **CI pipeline green** with UI tests

### Qualitative
- ✅ **Reusable fixtures** reduce test duplication
- ✅ **Clear test structure** for future maintainability
- ✅ **Documentation** of testing patterns
- ✅ **Fast test execution** (<5 seconds for UI tests)

---

## Timeline

| Phase | Duration | Calendar Days | Dependencies |
|-------|----------|---------------|--------------|
| Phase 1 | 1-2 days | Oct 1-2 | None |
| Phase 2 | 1-2 days | Oct 3-4 | Phase 1 complete |
| Phase 3 | 2-3 days | Oct 5-7 | Phase 2 complete |
| Phase 4 | 2-3 days | Oct 8-10 | Phase 3 complete |
| Phase 5 | 1-2 days | Oct 11-12 | Phase 4 complete |
| Phase 6 | 3-5 days | Oct 13-17 | Phase 5 complete |
| **Total** | **10-17 days** | **Oct 1-17** | Sequential |

### Flexible Milestones
- **Minimum**: Phase 1-2 (foundation + simple widgets) → **+70 tests**
- **Target**: Phase 1-4 (exclude OpenGL + MainWindow) → **+120 tests**
- **Stretch**: All phases complete → **+160 tests**

---

## Next Steps

1. **Get approval** for this testing plan
2. **Create test infrastructure** (Phase 1.1)
   - `tests/ui/` directory
   - `conftest.py` with fixtures
   - `test_utils.py` with helpers
3. **Start Phase 1.2**: VerticalTimeline tests
4. **Iterate** through phases based on priority

---

## References

- **pytest-qt documentation**: https://pytest-qt.readthedocs.io/
- **Qt Test Best Practices**: https://doc.qt.io/qt-5/qtest-overview.html
- **Existing test structure**: `tests/test_progress_manager.py`
- **Widget implementation**: `ui/widgets/vertical_stack_slider.py`

---

**Plan Status**: ✅ Ready for Implementation
**Prepared by**: Claude (AI Assistant)
**Date**: 2025-10-01
