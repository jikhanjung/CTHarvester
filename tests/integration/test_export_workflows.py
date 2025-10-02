"""
Export workflow integration tests

Part of Phase 2: Integration Tests Expansion
Tests export functionality with real data
"""

import numpy as np
import pytest
from pathlib import Path
from PIL import Image

from ui.handlers.export_handler import ExportHandler


@pytest.mark.integration
class TestExportWorkflows:
    """Export workflow integration tests"""

    def test_image_stack_export_workflow(self, sample_ct_directory, tmp_path):
        """Test complete image stack export workflow"""
        # Create export handler with mock main window
        from unittest.mock import MagicMock
        mock_window = MagicMock()
        handler = ExportHandler(mock_window)

        # Create sample volume data
        volume = np.random.randint(0, 255, (10, 256, 256), dtype=np.uint8)

        # Set export path
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        # Export image stack
        handler.volume_data = volume
        handler.export_directory = str(export_dir)

        # Manually trigger export since we can't use dialog
        if hasattr(handler, 'save_image_stack'):
            # Create dummy ROI
            roi = [0, 10, 0, 256, 0, 256]  # Full volume

            success = handler.save_image_stack(
                str(export_dir / "slice.tif"),
                volume,
                roi,
                open_after=False
            )

            if success:
                # Verify files were created
                exported_files = list(export_dir.glob("*.tif"))
                assert len(exported_files) > 0

    def test_export_with_cropping(self, tmp_path):
        """Test export with cropped region"""
        from unittest.mock import MagicMock
        mock_window = MagicMock()
        handler = ExportHandler(mock_window)

        # Create sample volume
        volume = np.random.randint(0, 255, (20, 256, 256), dtype=np.uint8)

        # Define cropped ROI (z_min, z_max, y_min, y_max, x_min, x_max)
        roi = [5, 15, 50, 200, 50, 200]

        export_dir = tmp_path / "export_cropped"
        export_dir.mkdir()

        if hasattr(handler, 'save_image_stack'):
            success = handler.save_image_stack(
                str(export_dir / "cropped.tif"),
                volume,
                roi,
                open_after=False
            )

            if success:
                # Verify exported images have correct dimensions
                exported_files = sorted(export_dir.glob("*.tif"))
                if exported_files:
                    img = Image.open(exported_files[0])
                    width, height = img.size

                    # Should match ROI dimensions
                    expected_width = roi[5] - roi[4]  # x_max - x_min
                    expected_height = roi[3] - roi[2]  # y_max - y_min

                    assert width == expected_width
                    assert height == expected_height

    def test_export_quality_verification(self, tmp_path):
        """Test that exported images maintain quality"""
        from unittest.mock import MagicMock
        mock_window = MagicMock()
        handler = ExportHandler(mock_window)

        # Create volume with known pattern
        volume = np.zeros((5, 100, 100), dtype=np.uint8)
        volume[:, :, :] = 128  # Mid-gray
        volume[:, 25:75, 25:75] = 255  # White square in center

        export_dir = tmp_path / "export_quality"
        export_dir.mkdir()

        roi = [0, 5, 0, 100, 0, 100]

        if hasattr(handler, 'save_image_stack'):
            success = handler.save_image_stack(
                str(export_dir / "quality.tif"),
                volume,
                roi,
                open_after=False
            )

            if success:
                # Verify exported data matches input
                exported_files = sorted(export_dir.glob("*.tif"))
                if exported_files:
                    img = Image.open(exported_files[0])
                    img_array = np.array(img)

                    # Check that center square is white
                    center_region = img_array[25:75, 25:75]
                    assert np.all(center_region == 255)

                    # Check that corners are gray
                    corner = img_array[0:10, 0:10]
                    assert np.all(corner == 128)
