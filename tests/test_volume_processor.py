"""
Tests for VolumeProcessor class

Tests the volume processing logic extracted from main_window.py
"""

import numpy as np
import pytest

from core.volume_processor import VolumeProcessor


@pytest.mark.unit
class TestVolumeProcessor:
    """Test suite for VolumeProcessor"""

    @pytest.fixture
    def processor(self):
        """Create a VolumeProcessor instance"""
        return VolumeProcessor()

    @pytest.fixture
    def sample_volume(self):
        """Create a sample 3D volume (10x20x30)"""
        return np.arange(6000, dtype=np.uint8).reshape((10, 20, 30))

    @pytest.fixture
    def sample_level_info(self):
        """Create sample LoD level information"""
        return [
            # Level 0: Full resolution
            {"seq_begin": 0, "seq_end": 99, "width": 1024, "height": 1024},
            # Level 1: Half resolution
            {"seq_begin": 0, "seq_end": 49, "width": 512, "height": 512},
            # Level 2: Quarter resolution (smallest)
            {"seq_begin": 0, "seq_end": 24, "width": 256, "height": 256},
        ]

    def test_initialization(self, processor):
        """Test processor initializes correctly"""
        assert processor is not None

    def test_get_cropped_volume_full_range(self, processor, sample_volume, sample_level_info):
        """Test cropping with full range (no cropping)"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=sample_volume,
            level_info=sample_level_info,
            curr_level_idx=2,  # Smallest level
            top_idx=24,  # Full range
            bottom_idx=0,
            crop_box=[0, 0, 256, 256],  # Full image
        )

        # Should return approximately full volume
        assert volume.shape == (10, 20, 30)
        assert len(roi) == 6

    def test_get_cropped_volume_partial(self, processor, sample_volume, sample_level_info):
        """Test cropping with partial range"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=sample_volume,
            level_info=sample_level_info,
            curr_level_idx=2,
            top_idx=12,  # Half slices
            bottom_idx=0,
            crop_box=[0, 0, 128, 128],  # Half size
        )

        # Should return cropped volume
        assert volume.ndim == 3
        assert volume.shape[0] <= 10  # Depth
        assert volume.shape[1] <= 20  # Height
        assert volume.shape[2] <= 30  # Width

    def test_get_cropped_volume_empty_level_info(self, processor, sample_volume):
        """Test with empty level_info"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=sample_volume,
            level_info=[],
            curr_level_idx=0,
            top_idx=5,
            bottom_idx=0,
            crop_box=[0, 0, 10, 10],
        )

        assert volume.size == 0
        assert roi == [0, 0, 0, 0, 0, 0]

    def test_get_cropped_volume_invalid_indices(self, processor, sample_volume, sample_level_info):
        """Test with invalid top/bottom indices"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=sample_volume,
            level_info=sample_level_info,
            curr_level_idx=2,
            top_idx=-1,  # Invalid
            bottom_idx=-1,  # Invalid
            crop_box=[0, 0, 256, 256],
        )

        # Should use full range as fallback
        assert volume.size > 0

    def test_get_cropped_volume_bottom_greater_than_top(
        self, processor, sample_volume, sample_level_info
    ):
        """Test with bottom > top (invalid)"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=sample_volume,
            level_info=sample_level_info,
            curr_level_idx=2,
            top_idx=5,
            bottom_idx=10,  # Invalid: bottom > top
            crop_box=[0, 0, 256, 256],
        )

        # Should use full range as fallback
        assert volume.size > 0

    def test_scale_coordinates_between_levels_down(self, processor):
        """Test scaling coordinates from high to low resolution"""
        # From level 0 (1024x1024) to level 2 (256x256)
        coords = [100, 200, 300]
        scaled = processor.scale_coordinates_between_levels(coords, 0, 2)

        # Should scale down by factor of 4 (2^2)
        assert scaled == [25.0, 50.0, 75.0]

    def test_scale_coordinates_between_levels_up(self, processor):
        """Test scaling coordinates from low to high resolution"""
        # From level 2 (256x256) to level 0 (1024x1024)
        coords = [25, 50, 75]
        scaled = processor.scale_coordinates_between_levels(coords, 2, 0)

        # Should scale up by factor of 4 (2^-(-2))
        assert scaled == [100.0, 200.0, 300.0]

    def test_scale_coordinates_same_level(self, processor):
        """Test scaling within same level"""
        coords = [100, 200, 300]
        scaled = processor.scale_coordinates_between_levels(coords, 1, 1)

        # Should remain unchanged
        assert scaled == [100.0, 200.0, 300.0]

    def test_normalize_coordinates(self, processor):
        """Test normalizing coordinates to [0, 1]"""
        coords = [50, 100, 150]
        dimensions = [100, 200, 300]

        normalized = processor.normalize_coordinates(coords, dimensions)

        assert normalized == [0.5, 0.5, 0.5]

    def test_normalize_coordinates_zero_dimension(self, processor):
        """Test normalizing with zero dimension"""
        coords = [50, 0]
        dimensions = [100, 0]

        normalized = processor.normalize_coordinates(coords, dimensions)

        assert normalized == [0.5, 0.0]

    def test_denormalize_coordinates(self, processor):
        """Test converting normalized coordinates to pixels"""
        norm_coords = [0.5, 0.25, 0.75]
        dimensions = [100, 200, 300]

        pixels = processor.denormalize_coordinates(norm_coords, dimensions)

        assert pixels == [50, 50, 225]

    def test_normalize_denormalize_roundtrip(self, processor):
        """Test that normalize -> denormalize is reversible"""
        original = [50, 100, 150]
        dimensions = [100, 200, 300]

        normalized = processor.normalize_coordinates(original, dimensions)
        restored = processor.denormalize_coordinates(normalized, dimensions)

        assert restored == original

    def test_clamp_indices_valid_range(self, processor):
        """Test clamping with valid indices"""
        bottom, top = processor.clamp_indices(10, 50, 100)

        assert bottom == 10
        assert top == 50

    def test_clamp_indices_out_of_bounds(self, processor):
        """Test clamping with out-of-bounds indices"""
        bottom, top = processor.clamp_indices(-5, 150, 100)

        assert bottom == 0
        assert top == 100

    def test_clamp_indices_bottom_greater_than_top(self, processor):
        """Test clamping when bottom > top"""
        bottom, top = processor.clamp_indices(60, 50, 100)

        # Should adjust top to be at least bottom + 1
        assert bottom == 60
        assert top == 61

    def test_clamp_indices_edge_case_max(self, processor):
        """Test clamping at maximum boundary"""
        bottom, top = processor.clamp_indices(99, 100, 100)

        assert bottom == 99
        assert top == 100

    def test_clamp_crop_box_valid(self, processor):
        """Test clamping crop box within bounds"""
        crop_box = [10, 20, 90, 80]
        clamped = processor.clamp_crop_box(crop_box, 100, 100)

        assert clamped == [10, 20, 90, 80]

    def test_clamp_crop_box_out_of_bounds(self, processor):
        """Test clamping crop box that exceeds bounds"""
        crop_box = [-10, -20, 150, 120]
        clamped = processor.clamp_crop_box(crop_box, 100, 100)

        assert clamped[0] == 0  # x1 clamped to 0
        assert clamped[1] == 0  # y1 clamped to 0
        assert clamped[2] == 100  # x2 clamped to width
        assert clamped[3] == 100  # y2 clamped to height

    def test_clamp_crop_box_zero_size(self, processor):
        """Test clamping when x1 == x2 or y1 == y2"""
        crop_box = [50, 50, 50, 50]
        clamped = processor.clamp_crop_box(crop_box, 100, 100)

        # Should ensure minimum size of 1
        assert clamped[2] > clamped[0]
        assert clamped[3] > clamped[1]

    def test_calculate_cropped_dimensions(self, processor, sample_level_info):
        """Test calculating dimensions of cropped region"""
        dims = processor.calculate_cropped_dimensions(
            level_info=sample_level_info,
            curr_level_idx=0,
            top_idx=50,
            bottom_idx=10,
            crop_box=[100, 200, 300, 400],
        )

        assert dims["depth"] == 41  # 50 - 10 + 1
        assert dims["height"] == 200  # 400 - 200
        assert dims["width"] == 200  # 300 - 100
        assert dims["voxels"] == 41 * 200 * 200

    def test_calculate_cropped_dimensions_empty_level_info(self, processor):
        """Test calculating dimensions with empty level_info"""
        dims = processor.calculate_cropped_dimensions(
            level_info=[], curr_level_idx=0, top_idx=10, bottom_idx=0, crop_box=[0, 0, 10, 10]
        )

        assert dims == {"depth": 0, "height": 0, "width": 0, "voxels": 0}

    def test_validate_volume_valid(self, processor, sample_volume):
        """Test validating a valid volume"""
        result = processor.validate_volume(sample_volume)
        assert result is True

    def test_validate_volume_none(self, processor):
        """Test validating None"""
        result = processor.validate_volume(None)
        assert result is False

    def test_validate_volume_not_numpy(self, processor):
        """Test validating non-numpy array"""
        result = processor.validate_volume([1, 2, 3])
        assert result is False

    def test_validate_volume_empty(self, processor):
        """Test validating empty array"""
        empty = np.array([])
        result = processor.validate_volume(empty)
        assert result is False

    def test_validate_volume_wrong_dimensions(self, processor):
        """Test validating array with wrong dimensions"""
        # 2D array instead of 3D
        array_2d = np.zeros((10, 10))
        result = processor.validate_volume(array_2d)
        assert result is False

        # 4D array
        array_4d = np.zeros((10, 10, 10, 10))
        result = processor.validate_volume(array_4d)
        assert result is False

    def test_get_volume_statistics(self, processor, sample_volume):
        """Test getting volume statistics"""
        stats = processor.get_volume_statistics(sample_volume)

        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats
        assert "shape" in stats
        assert "dtype" in stats

        assert stats["shape"] == (10, 20, 30)
        assert stats["min"] == 0.0
        assert stats["max"] == 255.0  # uint8 wraps around

    def test_get_volume_statistics_invalid(self, processor):
        """Test getting statistics from invalid volume"""
        stats = processor.get_volume_statistics(None)
        assert stats == {}

    @pytest.mark.parametrize(
        "from_level,to_level,factor",
        [
            (0, 1, 0.5),  # Down 1 level
            (0, 2, 0.25),  # Down 2 levels
            (0, 3, 0.125),  # Down 3 levels
            (3, 0, 8.0),  # Up 3 levels
            (1, 2, 0.5),  # Down 1 level from middle
        ],
    )
    def test_scale_coordinates_various_levels(self, processor, from_level, to_level, factor):
        """Test scaling between various LoD levels"""
        coords = [100, 200, 300]
        scaled = processor.scale_coordinates_between_levels(coords, from_level, to_level)

        expected = [c * factor for c in coords]
        assert scaled == expected


@pytest.mark.unit
class TestVolumeProcessorEdgeCases:
    """Edge case tests for VolumeProcessor"""

    @pytest.fixture
    def processor(self):
        return VolumeProcessor()

    def test_get_cropped_volume_with_list_volume(self, processor):
        """Test cropping when minimum_volume is a list"""
        # Create list of arrays (simulating pre-conversion state)
        volume_list = [np.ones((20, 30), dtype=np.uint8) * i for i in range(10)]

        level_info = [{"seq_begin": 0, "seq_end": 9, "width": 30, "height": 20}]

        volume, roi = processor.get_cropped_volume(
            minimum_volume=volume_list,
            level_info=level_info,
            curr_level_idx=0,
            top_idx=9,
            bottom_idx=0,
            crop_box=[0, 0, 30, 20],
        )

        # Should convert list to array and crop
        assert volume.size > 0

    def test_clamp_indices_at_boundary(self, processor):
        """Test clamping at exact boundary"""
        bottom, top = processor.clamp_indices(0, 100, 100)

        assert bottom == 0
        assert top == 100

    def test_single_slice_volume(self, processor):
        """Test processing single-slice volume"""
        single_slice = np.ones((1, 100, 100), dtype=np.uint8)

        result = processor.validate_volume(single_slice)
        assert result is True

        stats = processor.get_volume_statistics(single_slice)
        assert stats["shape"] == (1, 100, 100)

    def test_very_large_coordinates(self, processor):
        """Test with very large coordinate values"""
        coords = [1000000, 2000000, 3000000]
        scaled = processor.scale_coordinates_between_levels(coords, 0, 10)

        # Should scale down by 2^10 = 1024
        assert all(s < c for s, c in zip(scaled, coords))

    def test_negative_coordinates(self, processor):
        """Test with negative coordinates (should clamp to 0)"""
        crop_box = [-10, -20, 50, 60]
        clamped = processor.clamp_crop_box(crop_box, 100, 100)

        assert clamped[0] >= 0
        assert clamped[1] >= 0
        assert clamped[2] <= 100
        assert clamped[3] <= 100

    def test_floating_point_precision(self, processor):
        """Test coordinate operations maintain reasonable precision"""
        coords = [1.23456789, 2.34567890, 3.45678901]

        # Normalize and denormalize
        dimensions = [10, 20, 30]
        normalized = processor.normalize_coordinates(coords, dimensions)
        restored = processor.denormalize_coordinates(normalized, dimensions)

        # Should maintain integer precision after roundtrip
        assert all(int(r) == int(c) for r, c in zip(restored, coords))

    def test_maximum_dimension_crop(self, processor):
        """Test cropping at maximum dimensions"""
        level_info = [{"seq_begin": 0, "seq_end": 99, "width": 1024, "height": 1024}]

        dims = processor.calculate_cropped_dimensions(
            level_info=level_info,
            curr_level_idx=0,
            top_idx=99,
            bottom_idx=0,
            crop_box=[0, 0, 1024, 1024],
        )

        assert dims["depth"] == 100
        assert dims["width"] == 1024
        assert dims["height"] == 1024
        assert dims["voxels"] == 100 * 1024 * 1024

    def test_scale_to_same_level(self, processor):
        """Test scaling coordinates to same level (should be identity)"""
        coords = [100, 200, 300]
        for level in range(5):
            scaled = processor.scale_coordinates_between_levels(coords, level, level)
            assert scaled == [float(c) for c in coords]

    def test_extreme_level_difference(self, processor):
        """Test with extreme level differences"""
        coords = [1024, 2048, 4096]

        # Scale down many levels
        scaled_down = processor.scale_coordinates_between_levels(coords, 0, 15)
        # 2^15 = 32768, so should be very small
        assert all(s < 1 for s in scaled_down)

        # Scale up many levels
        scaled_up = processor.scale_coordinates_between_levels(coords, 15, 0)
        # Should be very large
        assert all(s > 10000 for s in scaled_up)


@pytest.mark.unit
class TestVolumeProcessorCropBoundary:
    """Test suite for crop boundary conditions (off-by-one fix verification)"""

    @pytest.fixture
    def processor(self):
        """Create a VolumeProcessor instance"""
        return VolumeProcessor()

    @pytest.fixture
    def precise_volume(self):
        """Create a volume where each voxel's value is its index for precise testing"""
        # 10x10x10 volume where value = z*100 + y*10 + x
        volume = np.zeros((10, 10, 10), dtype=np.int32)
        for z in range(10):
            for y in range(10):
                for x in range(10):
                    volume[z, y, x] = z * 100 + y * 10 + x
        return volume

    @pytest.fixture
    def simple_level_info(self):
        """Simple level info for boundary testing"""
        return [
            {"seq_begin": 0, "seq_end": 9, "width": 10, "height": 10},
        ]

    def test_crop_includes_exact_boundaries(self, processor, precise_volume, simple_level_info):
        """Verify that crop includes the exact specified boundaries"""
        # Crop X=[0,5], Y=[0,5], Z=[0,5] should include indices 0-4 (5 elements each)
        # In normalized coords: to_x = 5/10 = 0.5
        volume, roi = processor.get_cropped_volume(
            minimum_volume=precise_volume,
            level_info=simple_level_info,
            curr_level_idx=0,
            top_idx=5,  # Z: 0-4 (5 slices)
            bottom_idx=0,
            crop_box=[0, 0, 5, 5],  # X,Y: 0-4 (5 pixels each)
        )

        # Should get 5x5x5 volume
        assert volume.shape == (5, 5, 5), f"Expected (5,5,5), got {volume.shape}"

        # Verify corner values
        assert volume[0, 0, 0] == 0, "Top-left-front corner should be (0,0,0) = 0"
        assert volume[0, 0, 4] == 4, "Top-right-front corner should be (0,0,4) = 4"
        assert volume[0, 4, 0] == 40, "Bottom-left-front corner should be (0,4,0) = 40"
        assert volume[4, 4, 4] == 444, "Bottom-right-back corner should be (4,4,4) = 444"

    def test_crop_full_volume_preserves_all_data(self, processor, precise_volume, simple_level_info):
        """Cropping the entire volume should preserve all data"""
        volume, roi = processor.get_cropped_volume(
            minimum_volume=precise_volume,
            level_info=simple_level_info,
            curr_level_idx=0,
            top_idx=10,  # Full range (seq_end is 9, so top_idx should be 10 for inclusive)
            bottom_idx=0,
            crop_box=[0, 0, 10, 10],  # Full image
        )

        # Should get exact same volume
        assert volume.shape == precise_volume.shape
        assert np.array_equal(volume, precise_volume)

    def test_crop_single_pixel_region(self, processor, precise_volume, simple_level_info):
        """Cropping a single pixel should work correctly"""
        # Crop X=[5,6], Y=[5,6], Z=[5,6] - should give 1x1x1
        volume, roi = processor.get_cropped_volume(
            minimum_volume=precise_volume,
            level_info=simple_level_info,
            curr_level_idx=0,
            top_idx=6,  # Z: 5 (1 slice)
            bottom_idx=5,
            crop_box=[5, 5, 6, 6],  # X,Y: 5 (1 pixel)
        )

        # Should get 1x1x1 volume
        assert volume.shape == (1, 1, 1), f"Expected (1,1,1), got {volume.shape}"
        assert volume[0, 0, 0] == 555, "Single pixel should be (5,5,5) = 555"

    def test_crop_last_pixel_included(self, processor, precise_volume, simple_level_info):
        """Verify the last pixel is included (off-by-one fix)"""
        # Crop to the very last pixel: X=[9,10], Y=[9,10], Z=[9,10]
        volume, roi = processor.get_cropped_volume(
            minimum_volume=precise_volume,
            level_info=simple_level_info,
            curr_level_idx=0,
            top_idx=10,  # Z: 9 (1 slice)
            bottom_idx=9,
            crop_box=[9, 9, 10, 10],  # X,Y: 9 (1 pixel)
        )

        # Should get 1x1x1 volume with the last voxel
        assert volume.shape == (1, 1, 1), f"Expected (1,1,1), got {volume.shape}"
        assert volume[0, 0, 0] == 999, "Last pixel should be (9,9,9) = 999"

    def test_crop_size_matches_roi_specification(self, processor, precise_volume, simple_level_info):
        """Crop size should match user's ROI specification exactly"""
        # User selects X=[2,7] (width=5), Y=[3,8] (height=5), Z=[1,6] (depth=5)
        volume, roi = processor.get_cropped_volume(
            minimum_volume=precise_volume,
            level_info=simple_level_info,
            curr_level_idx=0,
            top_idx=6,  # Z: 1-5 (5 slices)
            bottom_idx=1,
            crop_box=[2, 3, 7, 8],  # X: 2-6, Y: 3-7 (5x5 pixels)
        )

        # Should get exactly 5x5x5 volume
        assert volume.shape == (5, 5, 5), f"Expected (5,5,5), got {volume.shape}"

        # Verify first and last values
        assert volume[0, 0, 0] == 132, "First voxel should be (1,3,2) = 132"
        assert volume[4, 4, 4] == 576, "Last voxel should be (5,7,6) = 576"
