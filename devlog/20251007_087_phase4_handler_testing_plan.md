# Devlog 087: Phase 4 Handler Testing Implementation Plan

**Date:** 2025-10-07
**Status:** 🎯 Planning
**Previous:** [devlog 086 - Test Coverage Analysis](./20251004_086_test_coverage_analysis.md)

---

## 🎯 Objective

Implement comprehensive unit tests for Phase 4 handler modules to achieve 80-90% direct test coverage and address critical testing gaps identified in devlog 086.

---

## 📋 Current Status

### Test Coverage Gap
- **Total Phase 4 Code:** 1,076 lines across 4 modules
- **Current Direct Coverage:** 0%
- **Current Indirect Coverage:** Partial (via integration tests)
- **Target Coverage:** 80-90%

### Modules to Test
| Module | Lines | Tests Needed | Priority | Time Est. |
|--------|-------|--------------|----------|-----------|
| `ThumbnailCreationHandler` | 423 | 20-25 | 🔴 Critical | 4-5h |
| `SequentialProcessor` | 348 | 15-20 | 🔴 Critical | 3-4h |
| `ViewManager` | 165 | 15-18 | 🔴 High | 3-4h |
| `DirectoryOpenHandler` | 140 | 12-15 | 🟡 Medium | 2-3h |

**Total Estimated:** 62-78 tests, 12-16 hours

---

## 🚀 Implementation Plan

### Phase 1: ThumbnailCreationHandler (Priority 1)
**File:** `tests/test_thumbnail_creation_handler.py`
**Estimated:** 20-25 tests, 4-5 hours

#### Test Categories

1. **Initialization (2 tests)**
   - `test_initialization_with_main_window()`
   - `test_initialization_validates_window()`

2. **Rust/Python Selection Logic (4 tests)**
   - `test_create_thumbnail_uses_rust_when_available()`
   - `test_create_thumbnail_falls_back_to_python_when_rust_missing()`
   - `test_create_thumbnail_respects_force_python_flag()`
   - `test_rust_availability_detection()`

3. **Rust Implementation (6 tests)**
   - `test_create_thumbnail_rust_success()`
   - `test_create_thumbnail_rust_progress_callbacks()`
   - `test_create_thumbnail_rust_cancellation()`
   - `test_create_thumbnail_rust_error_handling()`
   - `test_create_thumbnail_rust_fallback_on_error()`
   - `test_create_thumbnail_rust_callback_coordination()`

4. **Python Implementation (6 tests)**
   - `test_create_thumbnail_python_success()`
   - `test_create_thumbnail_python_progress_tracking()`
   - `test_create_thumbnail_python_cancellation()`
   - `test_create_thumbnail_python_error_handling()`
   - `test_create_thumbnail_python_level_coordination()`
   - `test_create_thumbnail_python_sequential_processor_integration()`

5. **Progress Dialog Integration (4 tests)**
   - `test_progress_dialog_creation()`
   - `test_progress_dialog_updates()`
   - `test_progress_dialog_cleanup_on_completion()`
   - `test_progress_dialog_cleanup_on_cancellation()`

6. **State Management (3 tests)**
   - `test_state_cleanup_after_success()`
   - `test_state_cleanup_after_failure()`
   - `test_minimum_volume_update()`

#### Mocking Strategy
```python
@pytest.fixture
def mock_rust_module(monkeypatch):
    """Mock ct_thumbnail Rust module."""
    mock_module = MagicMock()

    def mock_build_thumbnails(dir_path, callback, *args):
        for i in range(0, 101, 20):
            if not callback(i):
                return False
        return True

    mock_module.build_thumbnails = mock_build_thumbnails
    monkeypatch.setitem(sys.modules, 'ct_thumbnail', mock_module)
    return mock_module

@pytest.fixture
def mock_sequential_processor(monkeypatch):
    """Mock SequentialProcessor for Python path."""
    mock_processor = MagicMock()
    mock_processor.process_level.return_value = {
        'thumbnail': np.ones((100, 100, 100), dtype=np.uint8),
        'processed': 100,
        'skipped': 0
    }
    return mock_processor
```

---

### Phase 2: SequentialProcessor (Priority 2)
**File:** `tests/test_sequential_processor.py`
**Estimated:** 15-20 tests, 3-4 hours

#### Test Categories

1. **Initialization (3 tests)**
   - `test_initialization_with_valid_parameters()`
   - `test_initialization_validates_image_list()`
   - `test_initialization_validates_dimensions()`

2. **Basic Processing (4 tests)**
   - `test_process_level_basic_workflow()`
   - `test_process_level_returns_correct_shape()`
   - `test_process_level_handles_single_image()`
   - `test_process_level_handles_empty_list()`

3. **Progress Tracking (4 tests)**
   - `test_progress_tracking_accuracy()`
   - `test_progress_callback_invocation()`
   - `test_eta_calculation()`
   - `test_performance_sampling()`

4. **Cancellation (3 tests)**
   - `test_cancellation_mid_processing()`
   - `test_cancellation_cleanup()`
   - `test_cancellation_via_callback()`

5. **Error Handling (4 tests)**
   - `test_error_handling_corrupt_image()`
   - `test_error_handling_permission_denied()`
   - `test_error_handling_disk_full()`
   - `test_error_handling_invalid_image_format()`

6. **Edge Cases (2 tests)**
   - `test_memory_efficiency_with_large_volume()`
   - `test_result_dictionary_accuracy()`

#### Mocking Strategy
```python
@pytest.fixture
def mock_image_loader(monkeypatch):
    """Mock image loading for faster tests."""
    def mock_load(path):
        return np.random.randint(0, 255, (100, 100), dtype=np.uint8)

    monkeypatch.setattr('PIL.Image.open', lambda p: MagicMock(
        convert=lambda mode: MagicMock(
            resize=lambda size: np.random.randint(0, 255, size, dtype=np.uint8)
        )
    ))
```

---

### Phase 3: ViewManager (Priority 3)
**File:** `tests/test_view_manager.py`
**Estimated:** 15-18 tests, 3-4 hours

#### Test Categories

1. **Initialization (2 tests)**
   - `test_initialization_with_main_window()`
   - `test_initialization_validates_dependencies()`

2. **update_3d_view Tests (8 tests)**
   - `test_update_3d_view_basic()`
   - `test_update_3d_view_with_volume_update()`
   - `test_update_3d_view_without_volume_update()`
   - `test_update_3d_view_missing_minimum_volume()`
   - `test_update_3d_view_level_scaling_calculation()`
   - `test_update_3d_view_bounding_box_calculation()`
   - `test_update_3d_view_timeline_synchronization()`
   - `test_update_3d_view_error_handling()`

3. **update_3d_view_with_thumbnails Tests (5 tests)**
   - `test_update_3d_view_with_thumbnails_basic()`
   - `test_update_3d_view_with_thumbnails_missing_volume()`
   - `test_update_3d_view_with_thumbnails_bounding_box()`
   - `test_update_3d_view_with_thumbnails_mesh_generation()`
   - `test_update_3d_view_with_thumbnails_geometry_adjustment()`

4. **Calculation Tests (3 tests)**
   - `test_scale_factor_calculation_single_level()`
   - `test_scale_factor_calculation_multi_level()`
   - `test_curr_slice_value_calculation()`

#### Mocking Strategy
```python
@pytest.fixture
def mock_main_window_for_view():
    """Mock main window with view-related state."""
    window = MagicMock()
    window.minimum_volume = np.ones((100, 100, 100), dtype=np.uint8)
    window.level_info = [
        {"name": "Level 0", "width": 800, "height": 800, "depth": 100},
        {"name": "Level 1", "width": 400, "height": 400, "depth": 50},
    ]
    window.curr_level_idx = 0
    window.mcube_widget = MagicMock()
    window.timeline = MagicMock()
    window.timeline.minimum.return_value = 0
    window.timeline.maximum.return_value = 99
    return window
```

---

### Phase 4: DirectoryOpenHandler (Priority 4)
**File:** `tests/test_directory_open_handler.py`
**Estimated:** 12-15 tests, 2-3 hours

#### Test Categories

1. **Initialization (2 tests)**
   - `test_initialization_with_main_window()`
   - `test_initialization_validates_dependencies()`

2. **Dialog Handling (3 tests)**
   - `test_open_directory_shows_dialog()`
   - `test_open_directory_uses_last_directory_setting()`
   - `test_open_directory_cancellation()`

3. **Directory Validation (4 tests)**
   - `test_open_directory_valid_ct_stack()`
   - `test_open_directory_no_images_warning()`
   - `test_open_directory_permission_error()`
   - `test_open_directory_invalid_path()`

4. **UI Updates (4 tests)**
   - `test_ui_state_reset_on_open()`
   - `test_ui_updates_image_info()`
   - `test_ui_updates_level_info()`
   - `test_first_image_preview_loaded()`

5. **Integration (2 tests)**
   - `test_thumbnail_generation_triggered()`
   - `test_settings_persistence()`

#### Mocking Strategy
```python
@pytest.fixture
def mock_file_dialog(monkeypatch):
    """Mock QFileDialog for directory selection."""
    test_dir = "/fake/test/directory"

    def mock_get_existing_directory(parent, caption, directory, options):
        return test_dir

    monkeypatch.setattr(
        QFileDialog,
        'getExistingDirectory',
        mock_get_existing_directory
    )
    return test_dir
```

---

## 📊 Success Criteria

### Quantitative Metrics
- ✅ 62-78 new tests added
- ✅ All tests passing
- ✅ 80-90% coverage of Phase 4 handler code
- ✅ Total test count: 1,134-1,150 tests

### Qualitative Metrics
- ✅ All critical error paths tested
- ✅ Cancellation scenarios covered
- ✅ Mock isolation validated
- ✅ No integration test dependencies

---

## 🛠️ Implementation Approach

### Test Development Workflow

1. **Create Test File**
   ```bash
   touch tests/test_[module_name].py
   ```

2. **Write Test Template**
   ```python
   """Tests for [ModuleName] (Phase X.X)."""

   import pytest
   from unittest.mock import MagicMock, patch
   from [module_path] import [ClassName]

   class Test[ClassName]:
       """Unit tests for [ClassName]."""

       @pytest.fixture
       def handler(self, mock_main_window):
           """Create handler instance."""
           return [ClassName](mock_main_window)
   ```

3. **Implement Tests Incrementally**
   - Write 5-6 tests at a time
   - Run tests: `pytest tests/test_[module].py -v`
   - Fix any issues
   - Repeat until category complete

4. **Verify Coverage**
   ```bash
   pytest tests/test_[module].py --cov=[module_path] --cov-report=term-missing
   ```

### Common Fixtures

```python
# conftest.py additions
@pytest.fixture
def mock_main_window():
    """Mock main window with common state."""
    window = MagicMock()
    window.image_dir = "/fake/directory"
    window.file_handler = MagicMock()
    window.thumbnail_manager = MagicMock()
    window.settings_handler = MagicMock()
    return window

@pytest.fixture
def mock_progress_dialog():
    """Mock progress dialog."""
    dialog = MagicMock()
    dialog.was_cancelled = False
    dialog.update_progress = MagicMock()
    return dialog
```

---

## ⏱️ Time Allocation

### Day 1: ThumbnailCreationHandler (4-5 hours)
- Setup fixtures and mocks (1h)
- Initialization + Selection tests (1h)
- Rust implementation tests (1.5h)
- Python implementation tests (1h)
- Progress + State tests (0.5h)

### Day 2: SequentialProcessor (3-4 hours)
- Setup fixtures and mocks (0.5h)
- Basic processing tests (1h)
- Progress tracking tests (1h)
- Cancellation tests (0.5h)
- Error handling + edge cases (1h)

### Day 3: ViewManager (3-4 hours)
- Setup fixtures and mocks (0.5h)
- update_3d_view tests (2h)
- update_3d_view_with_thumbnails tests (1h)
- Calculation tests (0.5h)

### Day 4: DirectoryOpenHandler (2-3 hours)
- Setup fixtures and mocks (0.5h)
- Dialog + validation tests (1h)
- UI update tests (1h)
- Integration tests (0.5h)

---

## 🎯 Expected Outcomes

### Test Suite Growth
| Phase | Tests Before | Tests After | Change |
|-------|--------------|-------------|--------|
| Phase 1 | 1,072 | 1,092-1,097 | +20-25 |
| Phase 2 | 1,092-1,097 | 1,107-1,117 | +15-20 |
| Phase 3 | 1,107-1,117 | 1,122-1,135 | +15-18 |
| Phase 4 | 1,122-1,135 | 1,134-1,150 | +12-15 |

### Coverage Improvement
| Module | Before | After | Improvement |
|--------|--------|-------|-------------|
| ThumbnailCreationHandler | 0% | 85-90% | +85-90% |
| SequentialProcessor | 0% | 80-85% | +80-85% |
| ViewManager | 0% | 80-85% | +80-85% |
| DirectoryOpenHandler | 0% | 85-90% | +85-90% |

---

## 📝 Documentation Updates

After implementation, update:
1. `README.md` - Update test count badge
2. `devlog/README.md` - Add entry for this devlog
3. Create completion report: `devlog/20251007_088_phase4_testing_completion.md`

---

## 🔗 Related Documents

- [devlog 086 - Test Coverage Analysis](./20251004_086_test_coverage_analysis.md)
- [devlog 085 - Phase 4 Completion Report](./20251004_085_phase4_completion_report.md)
- [devlog 084 - Phase 4 Implementation Plan](./20251004_084_next_phase_implementation_plan.md)

---

**Plan Created:** 2025-10-07
**Target Completion:** 2025-10-11 (4 days)
**Next Action:** Begin Phase 1 - ThumbnailCreationHandler tests
