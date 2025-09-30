import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    """Test that the main module can be imported"""
    try:
        import CTHarvester

        assert True
    except ImportError:
        assert False, "Failed to import CTHarvester module"


def test_requirements():
    """Test that required packages are installed"""
    required_packages = [
        "PyQt5",
        "PIL",
        "numpy",
        "scipy",
        "mcubes",  # Package name is 'mcubes', not 'pymcubes'
    ]

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            assert False, f"Required package {package} is not installed"

    assert True


def test_security_module_basic():
    """Smoke test: Security validator basic functionality"""
    import pytest

    from security.file_validator import FileSecurityError, SecureFileValidator

    # Valid filename should pass
    try:
        SecureFileValidator.validate_filename("test.tif")
        assert True
    except FileSecurityError:
        assert False, "Valid filename rejected"

    # Directory traversal should fail
    with pytest.raises(FileSecurityError):
        SecureFileValidator.validate_filename("../etc/passwd")

    # Null byte should fail
    with pytest.raises(FileSecurityError):
        SecureFileValidator.validate_filename("safe.txt\x00.exe")


def test_image_utils_basic():
    """Smoke test: Image utilities basic functionality"""
    try:
        import numpy as np
        from PIL import Image

        from utils.image_utils import (
            average_images,
            detect_bit_depth,
            downsample_image,
            load_image_as_array,
            save_image_from_array,
        )

        # Create temporary test image
        temp_dir = tempfile.mkdtemp()
        try:
            # Create 8-bit test image
            img_array = np.ones((100, 100), dtype=np.uint8) * 128
            img = Image.fromarray(img_array)
            test_path = os.path.join(temp_dir, "test.tif")
            img.save(test_path)

            # Test bit depth detection
            depth = detect_bit_depth(test_path)
            assert depth == 8, f"Expected bit depth 8, got {depth}"

            # Test image loading
            loaded = load_image_as_array(test_path)
            assert loaded.shape == (100, 100), f"Expected shape (100, 100), got {loaded.shape}"

            # Test downsampling
            downsampled = downsample_image(loaded, factor=2)
            assert downsampled.shape == (
                50,
                50,
            ), f"Expected shape (50, 50), got {downsampled.shape}"

            # Test averaging
            arr1 = np.ones((10, 10), dtype=np.uint8) * 100
            arr2 = np.ones((10, 10), dtype=np.uint8) * 200
            averaged = average_images(arr1, arr2)
            assert np.all(averaged == 150), "Image averaging failed"

            # Test saving
            output_path = os.path.join(temp_dir, "output.tif")
            result = save_image_from_array(loaded, output_path)
            assert result is True, "Image save failed"
            assert os.path.exists(output_path), "Output file not created"

        finally:
            shutil.rmtree(temp_dir)

        assert True

    except ImportError:
        # PIL not available, skip test
        pass


def test_progress_manager_basic():
    """Smoke test: Progress manager basic functionality"""
    from core.progress_manager import ProgressManager

    # Create progress manager
    pm = ProgressManager()

    # Start tracking
    pm.start(total=100)

    # Initial state
    assert pm.current == 0
    assert pm.total == 100

    # Update progress
    pm.update(delta=1)
    assert pm.current == 1

    pm.update(delta=9)
    assert pm.current == 10

    # Check progress calculation
    assert pm.total > 0, "Total should be set"
    assert 0 <= pm.current <= pm.total, f"Invalid current: {pm.current}"


def test_file_utils_basic():
    """Smoke test: File utilities basic functionality"""
    from utils.file_utils import (
        create_thumbnail_directory,
        find_image_files,
        format_file_size,
        parse_filename,
    )

    # Create temporary directory with test files
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test image files
        test_files = ["image_0001.tif", "image_0002.tif", "image_0003.png"]
        for filename in test_files:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("test")

        # Test file discovery
        found = find_image_files(temp_dir)
        assert len(found) == 3, f"Expected 3 files, found {len(found)}"

        # Test filename parsing
        prefix, number, ext = parse_filename("image_0042.tif")
        assert prefix == "image_", f"Expected prefix 'image_', got '{prefix}'"
        assert number == 42, f"Expected number 42, got {number}"
        assert ext == "tif", f"Expected ext 'tif', got '{ext}'"

        # Test thumbnail directory creation
        thumb_dir = create_thumbnail_directory(temp_dir, level=1)
        assert os.path.exists(thumb_dir), "Thumbnail directory not created"
        assert ".thumbnail" in thumb_dir, "Thumbnail directory name incorrect"

        # Test file size formatting
        size_str = format_file_size(1024)
        assert "KB" in size_str or "B" in size_str, f"Invalid size format: {size_str}"

    finally:
        shutil.rmtree(temp_dir)

    assert True
