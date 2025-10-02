"""Shared fixtures for UI integration tests.

This module provides pytest fixtures for UI integration testing with PyQt5.
Fixtures include QApplication setup, sample CT data generation, and main window
initialization for testing complete workflows.
"""

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from pathlib import Path
import numpy as np
from PIL import Image


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for all UI tests.

    Creates a single QApplication instance that is shared across all UI tests
    in the session. This is required for any PyQt5 widget operations.

    Yields:
        QApplication: The application instance

    Note:
        The application is automatically cleaned up at the end of the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Cleanup happens automatically when session ends


@pytest.fixture
def sample_ct_directory(tmp_path):
    """Create sample CT image directory for testing.

    Generates a directory containing 10 synthetic CT slice images (256x256)
    with varying intensity patterns. Each slice has a unique horizontal band
    to make it distinguishable.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        Path: Directory containing test images named slice_0000.tif to slice_0009.tif

    Example:
        >>> def test_something(sample_ct_directory):
        ...     images = list(sample_ct_directory.glob("*.tif"))
        ...     assert len(images) == 10
    """
    ct_dir = tmp_path / "ct_data"
    ct_dir.mkdir()

    # Generate 10 test slices with varying intensity
    for i in range(10):
        # Create gradient image
        img_array = np.linspace(0, 255, 256*256, dtype=np.uint8)
        img_array = img_array.reshape((256, 256))

        # Add unique horizontal band per slice for identification
        band_start = i * 20
        band_end = (i + 1) * 20
        img_array[band_start:band_end, :] = 255

        img = Image.fromarray(img_array)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    return ct_dir


@pytest.fixture
def main_window(qapp, tmp_path):
    """Create MainWindow instance for testing.

    Creates a fresh CTHarvesterMainWindow instance with isolated settings
    in a temporary directory. The window is shown and ready for interaction.

    Args:
        qapp: QApplication fixture
        tmp_path: Temporary directory for settings isolation

    Yields:
        CTHarvesterMainWindow: Initialized main window instance

    Note:
        Window is automatically closed and cleaned up after the test.
        Settings are stored in tmp_path to avoid affecting user settings.

    Example:
        >>> def test_ui(main_window):
        ...     assert main_window.isVisible()
        ...     # Interact with window widgets
    """
    from ui.main_window import CTHarvesterMainWindow
    import os

    # Set temp settings location to isolate from user settings
    os.environ['CTHARVESTER_SETTINGS_DIR'] = str(tmp_path)

    window = CTHarvesterMainWindow()
    window.show()
    QTest.qWaitForWindowExposed(window)

    yield window

    # Cleanup
    window.close()
    qapp.processEvents()


@pytest.fixture
def sample_ct_16bit_directory(tmp_path):
    """Create sample CT image directory with 16-bit depth.

    Similar to sample_ct_directory but generates 16-bit grayscale images
    to test 16-bit image handling workflows.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        Path: Directory containing 10 test 16-bit images
    """
    ct_dir = tmp_path / "ct_data_16bit"
    ct_dir.mkdir()

    for i in range(10):
        # Create 16-bit gradient image
        img_array = np.linspace(0, 65535, 256*256, dtype=np.uint16)
        img_array = img_array.reshape((256, 256))

        # Add unique pattern
        band_start = i * 20
        band_end = (i + 1) * 20
        img_array[band_start:band_end, :] = 65535

        img = Image.fromarray(img_array)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    return ct_dir


@pytest.fixture
def large_ct_dataset(tmp_path):
    """Create larger CT dataset for performance testing.

    Generates 50 images (512x512) for testing performance and progress
    reporting with more realistic data volumes.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        Path: Directory containing 50 test images

    Note:
        This fixture is marked as slow and should only be used in
        performance benchmark tests.
    """
    ct_dir = tmp_path / "large_ct_data"
    ct_dir.mkdir()

    for i in range(50):
        # Create larger gradient image
        img_array = np.linspace(0, 255, 512*512, dtype=np.uint8)
        img_array = img_array.reshape((512, 512))

        # Add checkerboard pattern for more complex data
        img_array[::2, ::2] = (img_array[::2, ::2] * 0.7).astype(np.uint8)
        img_array[1::2, 1::2] = (img_array[1::2, 1::2] * 0.7).astype(np.uint8)

        img = Image.fromarray(img_array)
        img.save(ct_dir / f"slice_{i:04d}.tif")

    return ct_dir
