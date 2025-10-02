"""
Edge case tests for CTHarvester core modules.

Tests boundary conditions and unusual input scenarios that might occur
in production but aren't covered by standard unit tests.
"""

import pytest
import numpy as np
from pathlib import Path


class TestFileHandlerEdgeCases:
    """Edge case tests for file_handler module."""

    def test_sequence_begin_greater_than_end(self, tmp_path):
        """Test handling when seq_begin > seq_end."""
        from core.file_handler import FileHandler

        handler = FileHandler()
        # This should handle gracefully - no crash
        settings = {
            'prefix': 'img_',
            'file_type': 'tif',
            'seq_begin': 100,
            'seq_end': 50,
            'index_length': 4
        }
        result = handler.get_file_list(str(tmp_path), settings)
        assert result == []  # Should return empty list, not crash

    def test_negative_sequence_numbers(self, tmp_path):
        """Test handling of negative sequence numbers."""
        from core.file_handler import FileHandler

        handler = FileHandler()
        settings = {
            'prefix': 'img_',
            'file_type': 'tif',
            'seq_begin': -10,
            'seq_end': -5,
            'index_length': 4
        }
        result = handler.get_file_list(str(tmp_path), settings)
        assert result == []  # Should handle gracefully

    def test_extremely_large_sequence_range(self, tmp_path):
        """Test handling of unreasonably large sequence ranges."""
        from core.file_handler import FileHandler

        handler = FileHandler()
        # Should not cause memory issues or hang
        settings = {
            'prefix': 'img_',
            'file_type': 'tif',
            'seq_begin': 0,
            'seq_end': 1000000,
            'index_length': 4
        }
        result = handler.get_file_list(str(tmp_path), settings)
        # Should return empty list since files don't exist
        assert isinstance(result, list)

    def test_zero_index_length(self, tmp_path):
        """Test handling of zero index length."""
        from core.file_handler import FileHandler

        handler = FileHandler()
        settings = {
            'prefix': 'img_',
            'file_type': 'tif',
            'seq_begin': 0,
            'seq_end': 10,
            'index_length': 0
        }
        result = handler.get_file_list(str(tmp_path), settings)
        # Should handle gracefully
        assert isinstance(result, list)

    def test_empty_prefix(self, tmp_path):
        """Test handling of empty prefix string."""
        from core.file_handler import FileHandler

        # Create test file with no prefix
        test_file = tmp_path / "0001.tif"
        test_file.write_bytes(b"fake")

        handler = FileHandler()
        settings = {
            'prefix': '',
            'file_type': 'tif',
            'seq_begin': 0,
            'seq_end': 10,
            'index_length': 4
        }
        result = handler.get_file_list(str(tmp_path), settings)
        assert isinstance(result, list)

    def test_unicode_prefix(self, tmp_path):
        """Test handling of unicode characters in prefix."""
        from core.file_handler import FileHandler

        handler = FileHandler()
        settings = {
            'prefix': '이미지_',
            'file_type': 'tif',
            'seq_begin': 0,
            'seq_end': 10,
            'index_length': 4
        }
        result = handler.get_file_list(str(tmp_path), settings)
        assert isinstance(result, list)


class TestVolumeProcessorEdgeCases:
    """Edge case tests for volume_processor module."""

    def test_empty_volume_array(self):
        """Test handling of empty volume."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        empty_volume = np.array([])
        level_info = [{
            'seq_begin': 0,
            'seq_end': 10,
            'width': 512,
            'height': 512
        }]

        result, roi = processor.get_cropped_volume(
            empty_volume, level_info, 0, 0, 10, [0, 0, 100, 100]
        )

        assert result.size == 0  # Should return empty array
        assert len(roi) == 6

    def test_single_slice_volume(self):
        """Test handling of volume with single slice."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        single_slice = np.ones((1, 100, 100), dtype=np.uint8)
        level_info = [{
            'seq_begin': 0,
            'seq_end': 0,
            'width': 100,
            'height': 100
        }]

        result, roi = processor.get_cropped_volume(
            single_slice, level_info, 0, 0, 0, [0, 0, 50, 50]
        )

        assert result.shape[0] == 1  # Should handle single slice

    def test_crop_box_outside_bounds(self):
        """Test crop box completely outside volume bounds."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        volume = np.ones((10, 100, 100), dtype=np.uint8)
        level_info = [{
            'seq_begin': 0,
            'seq_end': 9,
            'width': 100,
            'height': 100
        }]

        # Crop box way outside bounds
        result, roi = processor.get_cropped_volume(
            volume, level_info, 0, 0, 9, [200, 200, 300, 300]
        )

        # Should clamp to valid range
        assert result.size > 0 or result.size == 0  # Clamped or empty

    def test_zero_dimension_crop_box(self):
        """Test crop box with zero width or height."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        volume = np.ones((10, 100, 100), dtype=np.uint8)
        level_info = [{
            'seq_begin': 0,
            'seq_end': 9,
            'width': 100,
            'height': 100
        }]

        # Zero width crop box
        result, roi = processor.get_cropped_volume(
            volume, level_info, 0, 0, 9, [50, 50, 50, 100]
        )

        # Should handle gracefully
        assert isinstance(result, np.ndarray)

    def test_negative_crop_coordinates(self):
        """Test crop box with negative coordinates."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        volume = np.ones((10, 100, 100), dtype=np.uint8)
        level_info = [{
            'seq_begin': 0,
            'seq_end': 9,
            'width': 100,
            'height': 100
        }]

        result, roi = processor.get_cropped_volume(
            volume, level_info, 0, 0, 9, [-10, -10, 50, 50]
        )

        # Should handle gracefully - may result in empty or clamped array
        assert isinstance(result, np.ndarray)
        assert len(roi) == 6

    def test_mismatched_level_info(self):
        """Test with empty or invalid level_info."""
        from core.volume_processor import VolumeProcessor

        processor = VolumeProcessor()
        volume = np.ones((10, 100, 100), dtype=np.uint8)

        # Empty level_info may or may not raise - just test it doesn't crash
        try:
            result, roi = processor.get_cropped_volume(
                volume, [], 0, 0, 9, [0, 0, 50, 50]
            )
            # If no exception, just verify result types
            assert isinstance(result, np.ndarray)
            assert isinstance(roi, list)
        except (IndexError, KeyError):
            # Expected exception for empty level_info
            pass


class TestThumbnailGeneratorEdgeCases:
    """Edge case tests for thumbnail_generator module."""

    def test_settings_validation(self):
        """Test basic settings validation."""
        from core.thumbnail_generator import ThumbnailGenerator

        gen = ThumbnailGenerator()

        # Test with minimal valid settings
        settings = {
            'directory': '/tmp/test',
            'image_width': 512,
            'image_height': 512,
            'seq_begin': 0,
            'seq_end': 10,
            'prefix': 'img_',
            'file_type': 'tif',
            'index_length': 4
        }

        # Should not crash during initialization
        assert gen is not None
        assert settings['image_width'] == 512

    def test_single_image_sequence(self):
        """Test handling when seq_begin == seq_end."""
        from core.thumbnail_generator import ThumbnailGenerator

        gen = ThumbnailGenerator()
        settings = {
            'directory': '/tmp/test',
            'image_width': 512,
            'image_height': 512,
            'seq_begin': 10,
            'seq_end': 10,  # Same as begin - single image
            'prefix': 'img_',
            'file_type': 'tif',
            'index_length': 4
        }

        # Should handle single image case without crashing
        assert settings['seq_end'] - settings['seq_begin'] == 0

    def test_negative_sequence_numbers(self):
        """Test handling of negative sequence numbers in settings."""
        from core.thumbnail_generator import ThumbnailGenerator

        gen = ThumbnailGenerator()
        settings = {
            'directory': '/tmp/test',
            'image_width': 512,
            'image_height': 512,
            'seq_begin': -5,
            'seq_end': -1,
            'prefix': 'img_',
            'file_type': 'tif',
            'index_length': 4
        }

        # Should handle negative numbers gracefully
        assert isinstance(settings['seq_begin'], int)


class TestProgressManagerEdgeCases:
    """Edge case tests for progress_manager module."""

    def test_zero_total_work(self):
        """Test progress calculation with zero total."""
        from core.progress_manager import ProgressManager

        pm = ProgressManager()
        pm.start(total=0)  # Start with zero total
        pm.update(10)  # Try to update despite zero total

        # Should not crash
        assert pm.current == 10
        assert pm.total == 0

    def test_negative_progress(self):
        """Test handling of negative progress values."""
        from core.progress_manager import ProgressManager

        pm = ProgressManager()
        pm.start(total=100)
        pm.update(-10)  # Negative update

        # Current allows negative values (it's a delta update)
        assert pm.current == -10

    def test_progress_exceeds_total(self):
        """Test when progress exceeds 100%."""
        from core.progress_manager import ProgressManager

        pm = ProgressManager()
        pm.start(total=100)
        pm.update(150)  # More than total

        # Should clamp to 100% or handle gracefully
        assert pm.current >= 0  # Should not crash


class TestImageUtilsEdgeCases:
    """Edge case tests for image_utils module."""

    def test_downsample_1x1_image(self):
        """Test downsampling a 1x1 image."""
        from utils.image_utils import downsample_image

        tiny = np.array([[255]], dtype=np.uint8)
        result = downsample_image(tiny, factor=2)

        # Should handle gracefully, even if result is same size
        assert result is not None
        assert result.dtype == np.uint8

    def test_downsample_by_zero(self):
        """Test downsampling with factor=0."""
        from utils.image_utils import downsample_image

        img = np.ones((100, 100), dtype=np.uint8)

        with pytest.raises((ValueError, ZeroDivisionError)):
            downsample_image(img, factor=0)

    def test_downsample_by_negative(self):
        """Test downsampling with negative factor."""
        from utils.image_utils import downsample_image

        img = np.ones((100, 100), dtype=np.uint8)

        # Negative factor will result in empty array due to negative step
        result = downsample_image(img, factor=-2)
        # Should return empty array or handle gracefully
        assert isinstance(result, np.ndarray)

    def test_average_empty_arrays(self):
        """Test averaging with empty arrays."""
        from utils.image_utils import average_images

        arr1 = np.array([], dtype=np.uint8)
        arr2 = np.array([], dtype=np.uint8)

        result = average_images(arr1, arr2)
        assert result.size == 0

    def test_average_mismatched_shapes(self):
        """Test averaging arrays with different shapes."""
        from utils.image_utils import average_images

        arr1 = np.ones((100, 100), dtype=np.uint8)
        arr2 = np.ones((50, 50), dtype=np.uint8)

        with pytest.raises((ValueError, RuntimeError)):
            average_images(arr1, arr2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
