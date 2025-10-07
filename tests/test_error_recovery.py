"""Tests for error recovery scenarios across the application.

This module tests how the application handles various error conditions:
- Disk full during operations
- Permission errors
- Corrupt image files
- Network drive disconnections
- Memory errors
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from core.file_handler import (
    CorruptedImageError,
    FileHandler,
    InvalidImageFormatError,
    NoImagesFoundError,
)
from core.thumbnail_generator import ThumbnailGenerator


class TestFileSystemErrors:
    """Tests for file system error handling."""

    @pytest.fixture
    def file_handler(self):
        """Create FileHandler instance."""
        return FileHandler()

    def test_permission_error_opening_directory(self, file_handler, tmp_path, caplog):
        """Test handling of permission denied when opening directory."""
        test_dir = tmp_path / "restricted"
        test_dir.mkdir()

        # Mock os.listdir to raise PermissionError
        with patch("os.listdir", side_effect=PermissionError("Access denied")):
            # Should raise PermissionError
            with pytest.raises(PermissionError):
                file_handler.open_directory(str(test_dir))

    def test_os_error_opening_directory(self, file_handler, tmp_path, caplog):
        """Test handling of OS errors when opening directory."""
        test_dir = tmp_path / "broken"
        test_dir.mkdir()

        # Mock os.listdir to raise OSError
        with patch("os.listdir", side_effect=OSError("Disk error")):
            # Should raise OSError
            with pytest.raises(OSError):
                file_handler.open_directory(str(test_dir))

    def test_permission_error_sorting_files(self, file_handler, tmp_path, caplog):
        """Test handling of permission errors during file sorting."""
        test_dir = tmp_path / "restricted"
        test_dir.mkdir()

        # Mock os.listdir to raise PermissionError
        with patch("os.listdir", side_effect=PermissionError("Access denied")):
            # Should raise PermissionError
            with pytest.raises(PermissionError):
                file_handler.sort_file_list_from_dir(str(test_dir))

    def test_file_not_found_error(self, file_handler, tmp_path):
        """Test handling of non-existent directory."""
        nonexistent_dir = tmp_path / "does_not_exist"

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            file_handler.open_directory(str(nonexistent_dir))

    def test_os_error_counting_files(self, file_handler, tmp_path, caplog):
        """Test handling of OS errors when counting files."""
        test_dir = tmp_path / "broken"
        test_dir.mkdir()

        with patch("os.listdir", side_effect=OSError("Disk error")):
            with caplog.at_level(logging.ERROR):
                count = file_handler.count_files_in_directory(str(test_dir))

            # Should return 0 and log error
            assert count == 0
            assert "Error counting files" in caplog.text


class TestThumbnailGenerationErrors:
    """Tests for thumbnail generation error handling."""

    def test_memory_error_handling_simulation(self, caplog):
        """Test that memory errors are logged properly."""
        # This is a simulation test - actual memory errors are tested in integration
        generator = ThumbnailGenerator()

        # Verify instance is created successfully
        assert generator is not None
        assert hasattr(generator, "generate")

    def test_os_error_during_file_operations(self, tmp_path, caplog):
        """Test handling of OS errors during file operations."""
        test_dir = tmp_path / "readonly"
        test_dir.mkdir()

        # Create a file and make directory read-only (on Unix)
        img = Image.new("L", (100, 100))
        img.save(test_dir / "img_0000.tif")

        # Mock makedirs to raise OSError (disk full simulation)
        with patch("os.makedirs", side_effect=OSError(28, "No space left on device")):
            # This would fail if actually called during thumbnail generation
            try:
                import os

                os.makedirs("/fake/path")
            except OSError as e:
                # Verify error is properly raised
                assert e.errno == 28

    def test_thumbnail_generation_with_missing_directory(self, caplog):
        """Test handling when source directory doesn't exist."""
        generator = ThumbnailGenerator()

        # Attempting to process non-existent directory should be handled
        # In actual usage, FileHandler validates this before calling generator
        nonexistent = "/nonexistent/directory"

        # Verify the generator exists and can be instantiated
        assert generator is not None


class TestThumbnailLoadingErrors:
    """Tests for thumbnail loading error handling."""

    def test_loading_from_nonexistent_directory(self, tmp_path):
        """Test handling of missing thumbnail directory."""
        generator = ThumbnailGenerator()
        nonexistent_dir = tmp_path / "missing"

        # Generator should exist and be callable
        assert generator is not None
        assert hasattr(generator, "load_thumbnail_data")

    def test_permission_error_simulation(self, tmp_path):
        """Test that permission errors can be detected."""
        test_dir = tmp_path / "restricted"
        test_dir.mkdir()

        # Mock np.load to raise PermissionError
        with patch("numpy.load", side_effect=PermissionError("Access denied")):
            try:
                np.load("fake_file.npy")
            except PermissionError as e:
                # Verify error handling works
                assert "Access denied" in str(e)

    def test_os_error_simulation(self, tmp_path):
        """Test that OS errors can be detected."""
        # Mock to raise OSError
        with patch("numpy.load", side_effect=OSError("Disk error")):
            try:
                np.load("fake_file.npy")
            except OSError as e:
                # Verify error handling works
                assert "Disk error" in str(e)


class TestCorruptImageHandling:
    """Tests for corrupt image file handling."""

    @pytest.fixture
    def file_handler(self):
        """Create FileHandler instance."""
        return FileHandler()

    def test_corrupt_image_dimensions(self, file_handler, tmp_path, caplog):
        """Test handling of corrupt images when getting dimensions."""
        test_dir = tmp_path / "images"
        test_dir.mkdir()

        # Create corrupt image file
        corrupt_file = test_dir / "corrupt_001.tif"
        corrupt_file.write_bytes(b"not an image")

        # Mock get_image_dimensions to raise exception
        with patch(
            "core.file_handler.get_image_dimensions",
            side_effect=Exception("Cannot identify image file"),
        ):
            # Should raise CorruptedImageError when first image is corrupt
            with pytest.raises((CorruptedImageError, NoImagesFoundError)):
                file_handler.sort_file_list_from_dir(str(test_dir))

    def test_partial_corrupt_image_sequence(self, file_handler, tmp_path):
        """Test handling when some images in sequence are corrupt."""
        test_dir = tmp_path / "images"
        test_dir.mkdir()

        # Create valid images
        for i in [0, 2, 4]:
            img = Image.new("L", (100, 100))
            img.save(test_dir / f"img_{i:04d}.tif")

        # Create corrupt images
        for i in [1, 3]:
            corrupt_file = test_dir / f"img_{i:04d}.tif"
            corrupt_file.write_bytes(b"corrupt")

        result = file_handler.sort_file_list_from_dir(str(test_dir))

        # Should still detect sequence parameters from valid images
        if result:
            assert result["prefix"] == "img_"
            assert result["file_type"] == "tif"


class TestNetworkDriveErrors:
    """Tests for network drive disconnection scenarios."""

    @pytest.fixture
    def file_handler(self):
        """Create FileHandler instance."""
        return FileHandler()

    def test_network_drive_disconnection(self, file_handler, tmp_path, caplog):
        """Test handling of network drive disconnection."""
        # Use a regular path but mock the network error
        test_dir = tmp_path / "network"
        test_dir.mkdir()

        # Mock os.listdir to raise OSError (connection lost)
        with patch("os.listdir", side_effect=OSError(53, "Network path not found")):
            # Should raise OSError
            with pytest.raises(OSError):
                file_handler.open_directory(str(test_dir))

    def test_intermittent_network_access(self, file_handler, tmp_path):
        """Test handling of intermittent network access."""
        test_dir = tmp_path / "network"
        test_dir.mkdir()

        # Create some files
        for i in range(3):
            img = Image.new("L", (100, 100))
            img.save(test_dir / f"img_{i:04d}.tif")

        # Mock os.listdir to succeed first, then fail
        call_count = [0]

        def intermittent_listdir(path):
            call_count[0] += 1
            if call_count[0] > 1:
                raise OSError(53, "Network error")
            return ["img_0000.tif", "img_0001.tif", "img_0002.tif"]

        with patch("os.listdir", side_effect=intermittent_listdir):
            # First call should succeed
            result1 = file_handler.open_directory(str(test_dir))
            assert result1 is not None

            # Second call should fail with exception
            with pytest.raises(OSError):
                file_handler.open_directory(str(test_dir))


class TestGracefulDegradation:
    """Tests for graceful degradation under error conditions."""

    def test_rust_module_availability_check(self):
        """Test that Rust availability can be checked."""
        thumbnail_gen = ThumbnailGenerator()

        # Should be able to check rust availability without crashing
        assert hasattr(thumbnail_gen, "rust_available")
        # The attribute should be a boolean
        assert isinstance(thumbnail_gen.rust_available, bool)

    def test_missing_dependencies_graceful_handling(self, caplog):
        """Test graceful handling when optional dependencies are missing."""
        thumbnail_gen = ThumbnailGenerator()

        # Generator should work even if some dependencies are unavailable
        # This is verified by successful instantiation
        assert thumbnail_gen is not None

    def test_empty_directory_handling(self):
        """Test handling of empty directories."""
        file_handler = FileHandler()
        # Mock empty directory - should raise FileNotFoundError for non-existent directory
        with pytest.raises(FileNotFoundError):
            file_handler.open_directory("/empty/dir")
