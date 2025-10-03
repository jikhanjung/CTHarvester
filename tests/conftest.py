"""
Common test fixtures and utilities for CTHarvester tests.

This module provides shared fixtures, mock objects, and helper functions
used across multiple test files to reduce code duplication.
"""

import os
import shutil
import tempfile

import numpy as np
import pytest
from PIL import Image

# ==============================================================================
# Mock Objects for Testing
# ==============================================================================


class MockLabel:
    """Mock QLabel for testing without Qt dependencies"""

    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class MockProgressBar:
    """Mock QProgressBar for testing without Qt dependencies"""

    def __init__(self):
        self.value = 0
        self.maximum = 100

    def setValue(self, value):
        self.value = value

    def setMaximum(self, maximum):
        self.maximum = maximum


class MockProgressDialog:
    """Mock progress dialog for thumbnail generation testing

    Provides the interface expected by ThumbnailManager and ThumbnailGenerator
    without requiring actual Qt UI components.

    Attributes:
        is_cancelled: Flag to simulate user cancellation
        lbl_text: Mock label for main text
        lbl_status: Mock label for status text
        lbl_detail: Mock label for detail text
        pb_progress: Mock progress bar
        percentage_updates: List tracking progress percentage updates
    """

    def __init__(self, cancelled=False):
        self.is_cancelled = cancelled
        self.lbl_text = MockLabel()
        self.lbl_status = MockLabel()
        self.lbl_detail = MockLabel()
        self.pb_progress = MockProgressBar()
        self.percentage_updates = []


# ==============================================================================
# Common Test Fixtures
# ==============================================================================


@pytest.fixture
def temp_image_dir():
    """Create a temporary directory with test images

    Creates 10 test images (100x100, grayscale, 8-bit) with varying intensities.
    Automatically cleans up the directory after the test.

    Yields:
        str: Path to temporary directory containing test images
    """
    temp_dir = tempfile.mkdtemp()

    # Create 10 test images (100x100, grayscale)
    for i in range(10):
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * (i * 25))
        img.save(os.path.join(temp_dir, f"test_{i:04d}.tif"))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_empty_dir():
    """Create an empty temporary directory

    Useful for testing error handling with missing or empty directories.

    Yields:
        str: Path to empty temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_progress_dialog():
    """Create a mock progress dialog for testing

    Returns:
        MockProgressDialog: Mock dialog that doesn't cancel by default
    """
    return MockProgressDialog(cancelled=False)


@pytest.fixture
def mock_cancelled_progress_dialog():
    """Create a mock progress dialog that simulates immediate cancellation

    Returns:
        MockProgressDialog: Mock dialog with is_cancelled=True
    """
    return MockProgressDialog(cancelled=True)


# ==============================================================================
# Test Data Helpers
# ==============================================================================


def create_test_image(width, height, bit_depth=8, pattern="gradient"):
    """Create a test image with specified parameters

    Args:
        width: Image width in pixels
        height: Image height in pixels
        bit_depth: Bit depth (8 or 16)
        pattern: Pattern type ('gradient', 'solid', 'random')

    Returns:
        PIL.Image: Generated test image
    """
    dtype = np.uint16 if bit_depth == 16 else np.uint8
    max_val = 65535 if bit_depth == 16 else 255

    if pattern == "gradient":
        # Horizontal gradient
        img_array = np.linspace(0, max_val, width, dtype=dtype)
        img_array = np.tile(img_array, (height, 1))
    elif pattern == "solid":
        # Solid middle gray
        img_array = np.full((height, width), max_val // 2, dtype=dtype)
    elif pattern == "random":
        # Random noise
        img_array = np.random.randint(0, max_val + 1, (height, width), dtype=dtype)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")

    return Image.fromarray(img_array)


@pytest.fixture
def create_test_images():
    """Factory fixture for creating test images

    Returns:
        callable: Function that creates test images with custom parameters
    """
    return create_test_image
