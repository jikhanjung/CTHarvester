# UI Integration Tests Implementation Plan

**Date**: 2025-10-02
**Status**: Implementation Plan
**Priority**: High

## Current State

- **Unit Tests**: 485 passing tests for core modules (~95% coverage)
- **Integration Tests**: 9 tests for thumbnail generation workflow
- **UI Tests**: Limited coverage (only vertical timeline widget)
- **Missing**: End-to-end workflow tests with UI interaction

## Gap Analysis

### What's Missing

1. **Thumbnail Generation Workflow**
   - Open directory → Select region → Generate thumbnails → Verify results
   - User cancellation handling
   - Error recovery scenarios

2. **3D Visualization Workflow**
   - Load thumbnails → Set threshold → Generate 3D model → Export
   - Camera interaction testing
   - Marching cubes parameter variations

3. **Export Workflows**
   - Crop and save image stack
   - Export 3D model (STL, PLY, OBJ)
   - File format compatibility

4. **Settings Management**
   - Load/save settings
   - Settings dialog interaction
   - Preference persistence

---

## Proposed Solution: UI Integration Testing Framework

### Architecture

```
tests/
├── integration/
│   ├── conftest.py              # Shared fixtures
│   ├── test_thumbnail_workflow.py
│   ├── test_3d_workflow.py
│   ├── test_export_workflow.py
│   └── test_settings_workflow.py
└── fixtures/
    ├── sample_ct_data/          # Small test dataset
    │   ├── slice_0001.tif       # 10 slices, 256x256
    │   ├── slice_0002.tif
    │   └── ...
    └── expected_outputs/        # Golden files for comparison
```

### Test Infrastructure

#### 1. Qt Test Fixtures

**File**: `tests/integration/conftest.py`
```python
"""Shared fixtures for UI integration tests."""

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from pathlib import Path
import shutil

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for all UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Cleanup
    app.quit()


@pytest.fixture
def sample_ct_directory(tmp_path):
    """Create sample CT image directory for testing.

    Returns:
        Path: Directory containing 10 test images (256x256)
    """
    from PIL import Image
    import numpy as np

    ct_dir = tmp_path / "ct_data"
    ct_dir.mkdir()

    # Generate 10 test slices with varying intensity
    for i in range(10):
        # Create gradient image
        img_array = np.linspace(0, 255, 256*256, dtype=np.uint8)
        img_array = img_array.reshape((256, 256))
        # Add unique pattern per slice
        img_array[i*20:(i+1)*20, :] = 255

        img = Image.fromarray(img_array)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    return ct_dir


@pytest.fixture
def main_window(qapp, tmp_path):
    """Create MainWindow instance for testing.

    Returns:
        CTHarvesterMainWindow: Fresh window instance
    """
    from ui.main_window import CTHarvesterMainWindow

    # Set temp settings location
    import os
    os.environ['CTHARVESTER_SETTINGS_DIR'] = str(tmp_path)

    window = CTHarvesterMainWindow()
    window.show()
    QTest.qWaitForWindowExposed(window)

    yield window

    # Cleanup
    window.close()
    qapp.processEvents()
```

---

## Test Scenarios

### Test 1: Complete Thumbnail Generation Workflow

**File**: `tests/integration/test_thumbnail_workflow.py`
```python
"""Integration tests for thumbnail generation workflow."""

import pytest
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer
from pathlib import Path


@pytest.mark.integration
@pytest.mark.slow
def test_thumbnail_generation_complete_workflow(main_window, sample_ct_directory, qtbot):
    """Test complete workflow: Open → Generate → Verify.

    Steps:
        1. Click "Open dir." button
        2. Select sample CT directory
        3. Wait for file loading
        4. Click "Resample" button
        5. Wait for thumbnail generation
        6. Verify .thumbnail directory created
        7. Verify correct number of thumbnails
        8. Verify thumbnail sizes match expected levels
    """
    # Step 1: Open directory
    with qtbot.waitSignal(main_window.file_loaded, timeout=5000):
        # Simulate clicking "Open dir." button
        open_btn = main_window.findChild(QPushButton, "btnOpenDir")
        assert open_btn is not None

        # Mock file dialog to return test directory
        from unittest.mock import patch
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(sample_ct_directory)
            qtbot.mouseClick(open_btn, Qt.LeftButton)

    # Step 2: Verify files loaded
    assert main_window.file_handler.file_list is not None
    assert len(main_window.file_handler.file_list) == 10

    # Step 3: Generate thumbnails
    with qtbot.waitSignal(main_window.thumbnail_complete, timeout=30000):
        resample_btn = main_window.findChild(QPushButton, "btnResample")
        qtbot.mouseClick(resample_btn, Qt.LeftButton)

    # Step 4: Verify results
    thumbnail_dir = sample_ct_directory / ".thumbnail"
    assert thumbnail_dir.exists()

    # Check level 1 (should have 5 images: 10/2)
    level1_dir = thumbnail_dir / "1"
    assert level1_dir.exists()
    level1_files = list(level1_dir.glob("*.tif"))
    assert len(level1_files) == 5

    # Check level 2 (should have 2-3 images: 5/2)
    level2_dir = thumbnail_dir / "2"
    assert level2_dir.exists()
    level2_files = list(level2_dir.glob("*.tif"))
    assert 2 <= len(level2_files) <= 3


@pytest.mark.integration
def test_thumbnail_generation_with_cancellation(main_window, sample_ct_directory, qtbot):
    """Test user cancelling thumbnail generation mid-process.

    Steps:
        1. Open large directory (or slow I/O simulation)
        2. Start thumbnail generation
        3. Cancel after 1 second
        4. Verify partial thumbnails present
        5. Verify process stopped cleanly
    """
    # Open directory
    with qtbot.waitSignal(main_window.file_loaded, timeout=5000):
        from unittest.mock import patch
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(sample_ct_directory)
            main_window.open_directory()

    # Start thumbnail generation
    resample_btn = main_window.findChild(QPushButton, "btnResample")
    qtbot.mouseClick(resample_btn, Qt.LeftButton)

    # Cancel after 1 second
    def cancel_dialog():
        if main_window.progress_dialog and main_window.progress_dialog.isVisible():
            main_window.progress_dialog.cancel()

    QTimer.singleShot(1000, cancel_dialog)
    qtbot.wait(2000)

    # Verify clean stop (no crashes, threads terminated)
    assert main_window.threadpool.activeThreadCount() == 0


@pytest.mark.integration
def test_thumbnail_generation_error_recovery(main_window, tmp_path, qtbot):
    """Test handling of corrupted images during generation.

    Steps:
        1. Create directory with mix of valid and invalid images
        2. Start thumbnail generation
        3. Verify process continues despite errors
        4. Verify valid thumbnails created
        5. Verify error logged appropriately
    """
    # Create mixed directory
    from PIL import Image
    import numpy as np

    ct_dir = tmp_path / "mixed_data"
    ct_dir.mkdir()

    # 5 valid images
    for i in range(5):
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * i * 50)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    # 2 corrupted images
    (ct_dir / "slice_0005.tif").write_text("corrupted")
    (ct_dir / "slice_0006.tif").write_bytes(b"\x00\x00\x00")

    # 3 more valid images
    for i in range(7, 10):
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * i * 25)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    # Load and process
    with qtbot.waitSignal(main_window.file_loaded, timeout=5000):
        from unittest.mock import patch
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(ct_dir)
            main_window.open_directory()

    # Generate (should handle errors gracefully)
    with qtbot.waitSignal(main_window.thumbnail_complete, timeout=30000):
        resample_btn = main_window.findChild(QPushButton, "btnResample")
        qtbot.mouseClick(resample_btn, Qt.LeftButton)

    # Verify some thumbnails created despite errors
    thumbnail_dir = ct_dir / ".thumbnail"
    assert thumbnail_dir.exists()


@pytest.mark.integration
@pytest.mark.parametrize("image_format", ["tif", "bmp", "png", "jpg"])
def test_thumbnail_generation_various_formats(main_window, tmp_path, image_format, qtbot):
    """Test thumbnail generation with different image formats.

    Args:
        image_format: File extension to test (tif, bmp, png, jpg)
    """
    from PIL import Image
    import numpy as np

    ct_dir = tmp_path / f"data_{image_format}"
    ct_dir.mkdir()

    # Create 6 images in specified format
    for i in range(6):
        img = Image.fromarray(np.ones((128, 128), dtype=np.uint8) * (i * 40))
        img.save(ct_dir / f"slice_{i:04d}.{image_format}")

    # Process
    with qtbot.waitSignal(main_window.file_loaded, timeout=5000):
        from unittest.mock import patch
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(ct_dir)
            main_window.open_directory()

    with qtbot.waitSignal(main_window.thumbnail_complete, timeout=30000):
        resample_btn = main_window.findChild(QPushButton, "btnResample")
        qtbot.mouseClick(resample_btn, Qt.LeftButton)

    # Verify thumbnails created
    thumbnail_dir = ct_dir / ".thumbnail" / "1"
    assert thumbnail_dir.exists()
    thumbnail_files = list(thumbnail_dir.glob("*.tif"))
    assert len(thumbnail_files) == 3  # 6 images -> 3 thumbnails
```

---

### Test 2: 3D Visualization Workflow

**File**: `tests/integration/test_3d_workflow.py`
```python
"""Integration tests for 3D visualization workflow."""

import pytest
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
import numpy as np


@pytest.mark.integration
@pytest.mark.slow
def test_3d_visualization_workflow(main_window, sample_ct_directory, qtbot):
    """Test complete 3D workflow: Load → Set threshold → Generate → Verify.

    Steps:
        1. Load directory with thumbnails
        2. Set crop region (top/bottom markers)
        3. Adjust threshold slider
        4. Generate 3D model
        5. Verify mesh created
        6. Verify vertex/face counts reasonable
    """
    # Setup: Generate thumbnails first
    # ... (similar to thumbnail test)

    # Set crop region
    main_window.set_bottom_marker(2)  # Bottom slice
    main_window.set_top_marker(7)     # Top slice

    # Adjust threshold
    threshold_slider = main_window.findChild(QSlider, "thresholdSlider")
    threshold_slider.setValue(128)
    qtbot.wait(500)  # Wait for update

    # Generate 3D model
    with qtbot.waitSignal(main_window.model_generated, timeout=30000):
        generate_btn = main_window.findChild(QPushButton, "btn3DGenerate")
        qtbot.mouseClick(generate_btn, Qt.LeftButton)

    # Verify mesh created
    assert main_window.mesh_vertices is not None
    assert main_window.mesh_faces is not None
    assert len(main_window.mesh_vertices) > 0
    assert len(main_window.mesh_faces) > 0


@pytest.mark.integration
def test_3d_export_stl(main_window, sample_ct_directory, tmp_path, qtbot):
    """Test exporting 3D model to STL format."""
    # ... Setup and generate 3D model ...

    # Export to STL
    export_path = tmp_path / "output.stl"

    from unittest.mock import patch
    with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
        mock_dialog.return_value = (str(export_path), "STL Files (*.stl)")

        export_btn = main_window.findChild(QPushButton, "btnExport3D")
        qtbot.mouseClick(export_btn, Qt.LeftButton)

    # Verify file created
    assert export_path.exists()
    assert export_path.stat().st_size > 0

    # Verify STL format (basic check)
    content = export_path.read_text()
    assert "solid" in content.lower()
    assert "facet" in content.lower()
```

---

## Performance Benchmarking

### Benchmark Tests

**File**: `tests/integration/test_performance_benchmarks.py`
```python
"""Performance benchmark tests for UI workflows."""

import pytest
import time


@pytest.mark.benchmark
@pytest.mark.slow
def test_thumbnail_generation_performance(main_window, large_ct_dataset, qtbot):
    """Benchmark thumbnail generation on large dataset.

    Acceptance Criteria:
        - 1000 images (512x512) should complete in < 5 minutes
        - Memory usage should stay < 2GB
        - No memory leaks (stable after GC)
    """
    import psutil
    import gc

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024**2  # MB

    start_time = time.time()

    with qtbot.waitSignal(main_window.thumbnail_complete, timeout=300000):  # 5 min
        # ... trigger generation ...
        pass

    duration = time.time() - start_time

    gc.collect()
    final_memory = process.memory_info().rss / 1024**2  # MB

    # Assertions
    assert duration < 300  # < 5 minutes
    assert final_memory - initial_memory < 2048  # < 2GB increase
    assert final_memory < 3072  # < 3GB absolute

    print(f"Performance: {duration:.2f}s, Memory: {final_memory - initial_memory:.2f}MB")
```

---

## Test Execution

### Running Tests

```bash
# Run all integration tests
pytest tests/integration/ -v -m integration

# Run UI tests only (exclude benchmarks)
pytest tests/integration/ -v -m "integration and not benchmark"

# Run with coverage
pytest tests/integration/ -v --cov=ui --cov=core

# Run specific workflow
pytest tests/integration/test_thumbnail_workflow.py -v

# Run benchmarks
pytest tests/integration/ -v -m benchmark
```

### CI/CD Integration

```yaml
# .github/workflows/ui-tests.yml
name: UI Integration Tests

on: [pull_request]

jobs:
  ui-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          sudo apt-get install -y xvfb libxkbcommon-x11-0
          pip install -r requirements.txt
          pip install pytest pytest-qt pytest-cov

      - name: Run UI integration tests
        run: |
          xvfb-run pytest tests/integration/ -v -m "integration and not slow"

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Implementation Checklist

### Phase 1: Infrastructure (1-2 days)
- [ ] Create `tests/integration/` directory structure
- [ ] Implement `conftest.py` with shared fixtures
- [ ] Create sample test dataset (10 images)
- [ ] Set up Qt test infrastructure

### Phase 2: Workflow Tests (3-4 days)
- [ ] Implement thumbnail generation workflow tests
- [ ] Implement 3D visualization workflow tests
- [ ] Implement export workflow tests
- [ ] Implement settings workflow tests

### Phase 3: Error Scenarios (2-3 days)
- [ ] Implement cancellation tests
- [ ] Implement error recovery tests
- [ ] Implement edge case tests

### Phase 4: Performance (1-2 days)
- [ ] Implement performance benchmarks
- [ ] Set up memory profiling
- [ ] Document performance baselines

### Phase 5: CI/CD (1 day)
- [ ] Add UI test workflow to GitHub Actions
- [ ] Configure xvfb for headless testing
- [ ] Set up coverage reporting

---

## Estimated Effort

- **Total Time**: 8-12 days
- **Priority**: High (fills major testing gap)
- **Risk**: Medium (requires Qt test expertise)
- **Dependencies**: pytest-qt, xvfb (Linux), sample datasets

## Success Criteria

- [ ] 90%+ coverage of UI workflows
- [ ] All critical paths tested (open → generate → export)
- [ ] Tests run in CI/CD pipeline
- [ ] Tests complete in < 10 minutes
- [ ] No flaky tests (100% pass rate)
