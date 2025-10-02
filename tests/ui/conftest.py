"""
Shared fixtures for UI tests

Provides common fixtures and utilities for testing Qt-based UI components.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from PyQt5.QtWidgets import QApplication

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


@pytest.fixture(scope="session")
def qapp():
    """
    QApplication singleton for entire test session.

    pytest-qt creates its own QApplication, but we ensure it's available
    and configured properly for our tests.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit - pytest-qt handles cleanup


@pytest.fixture
def temp_settings_file(tmp_path):
    """
    Create temporary YAML settings file with default values.

    Returns:
        Path: Path to the temporary settings file
    """
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(
        """
# CTHarvester test settings
language: en
log_level: INFO
thumbnail_quality: high
max_thumbnail_size: 256
auto_generate_thumbnails: true
remember_window_geometry: true
recent_files_max: 10
"""
    )
    return settings_file


@pytest.fixture
def mock_image_stack(tmp_path):
    """
    Create temporary image stack for testing.

    Creates a directory with 10 sequential TIFF images (100x100 pixels).
    Each image has increasing brightness from 0 to 225.

    Returns:
        Path: Path to the directory containing test images
    """
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    for i in range(10):
        # Create 8-bit grayscale image with increasing brightness
        img_array = np.ones((100, 100), dtype=np.uint8) * (i * 25)
        img = Image.fromarray(img_array)
        img.save(image_dir / f"slice_{i:04d}.tif")

    return image_dir


@pytest.fixture
def mock_large_image_stack(tmp_path):
    """
    Create larger image stack for performance testing.

    Creates 100 images at 512x512 resolution.

    Returns:
        Path: Path to the directory containing test images
    """
    image_dir = tmp_path / "large_images"
    image_dir.mkdir()

    for i in range(100):
        # Create realistic test data with some variation
        img_array = (np.random.randint(0, 256, (512, 512), dtype=np.uint8) * 0.5 + i * 2).astype(
            np.uint8
        )
        img = Image.fromarray(img_array)
        img.save(image_dir / f"volume_{i:04d}.tif")

    return image_dir


@pytest.fixture
def mock_16bit_image_stack(tmp_path):
    """
    Create 16-bit TIFF image stack for testing high bit-depth support.

    Returns:
        Path: Path to the directory containing 16-bit test images
    """
    image_dir = tmp_path / "images_16bit"
    image_dir.mkdir()

    for i in range(10):
        # Create 16-bit grayscale image
        img_array = np.ones((100, 100), dtype=np.uint16) * (i * 6553)  # 0-65530 range
        img = Image.fromarray(img_array)
        img.save(image_dir / f"hd_{i:04d}.tif")

    return image_dir


@pytest.fixture
def mock_thumbnail_worker(mocker):
    """
    Mock ThumbnailWorker to avoid actual processing during tests.

    Returns:
        Mock: Mocked ThumbnailWorker class
    """
    if not PYQT_AVAILABLE:
        return None
    return mocker.patch("core.thumbnail_worker.ThumbnailWorker")


@pytest.fixture
def mock_mesh_generation_thread(mocker):
    """
    Mock MeshGenerationThread to avoid expensive 3D processing.

    Returns:
        Mock: Mocked MeshGenerationThread class
    """
    if not PYQT_AVAILABLE:
        return None
    return mocker.patch("ui.widgets.mcube_widget.MeshGenerationThread")


@pytest.fixture
def sample_numpy_volume():
    """
    Create sample 3D numpy volume for testing volume processing.

    Returns:
        np.ndarray: 3D array (20x50x50) with gradient values
    """
    # Create simple 3D volume with gradient
    z, y, x = 20, 50, 50
    volume = np.zeros((z, y, x), dtype=np.uint8)

    for i in range(z):
        volume[i] = np.ones((y, x), dtype=np.uint8) * (i * 12)

    return volume


@pytest.fixture
def sample_settings_dict():
    """
    Sample settings dictionary for testing.

    Returns:
        dict: Settings dictionary with common test values
    """
    return {
        "prefix": "slice_",
        "file_type": "tif",
        "seq_begin": 0,
        "seq_end": 9,
        "image_width": 100,
        "image_height": 100,
        "num_slices": 10,
        "max_level": 3,
    }


# Platform-specific skip decorators
skip_no_display = pytest.mark.skipif(
    not os.environ.get("DISPLAY") and sys.platform.startswith("linux"),
    reason="No display available (CI environment)",
)

skip_macos_qt_issue = pytest.mark.skipif(
    sys.platform == "darwin", reason="macOS-specific Qt behavior"
)

skip_windows_only = pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Windows-only test"
)

# Slow test marker (for tests that take >1 second)
slow = pytest.mark.slow


@pytest.fixture(autouse=True)
def mock_message_boxes(monkeypatch):
    """
    Auto-mock all QMessageBox dialogs to prevent blocking in tests.

    This fixture automatically mocks all QMessageBox static methods
    to return sensible default values without user interaction.
    """
    try:
        from PyQt5.QtWidgets import QMessageBox

        # Mock all common QMessageBox static methods
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
        monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)
    except ImportError:
        pass  # PyQt5 not available

    yield
