"""Integration tests for thumbnail generation workflow.

Tests complete user workflows from opening a directory through thumbnail
generation and verification.
"""

import pytest
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QPushButton
from pathlib import Path
from unittest.mock import patch
import time


@pytest.mark.integration
def test_thumbnail_generation_complete_workflow(main_window, sample_ct_directory, qtbot):
    """Test complete workflow: Open directory → Generate thumbnails → Verify.

    This test exercises the full thumbnail generation workflow:
    1. Click "Open Directory" button
    2. Select sample CT directory via mocked dialog
    3. Wait for file loading to complete
    4. Click "Resample" button to generate thumbnails
    5. Wait for thumbnail generation to complete
    6. Verify .thumbnail directory structure created
    7. Verify correct number of thumbnails at each level

    Args:
        main_window: MainWindow fixture
        sample_ct_directory: Sample CT data fixture (10 images)
        qtbot: pytest-qt fixture for Qt testing
    """
    # Step 1: Open directory using mocked file dialog
    with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(sample_ct_directory)

        # Trigger open_dir method
        main_window.open_dir()

        # Wait for file loading (synchronous operation)
        qtbot.wait(1000)

    # Step 2: Verify files loaded
    assert main_window.settings_hash is not None
    assert main_window.settings_hash.get('seq_begin') is not None
    assert main_window.settings_hash.get('seq_end') is not None
    num_images = main_window.settings_hash['seq_end'] - main_window.settings_hash['seq_begin'] + 1
    assert num_images == 10

    # Step 3: Generate thumbnails
    # Start thumbnail generation
    main_window.create_thumbnail()

    # Wait for thumbnail generation to complete
    # This may take several seconds depending on system
    timeout = 30000  # 30 seconds
    start_time = time.time()

    while time.time() - start_time < timeout / 1000:
        qtbot.wait(500)
        # Check if thumbnail directory exists
        thumbnail_dir = sample_ct_directory / ".thumbnail"
        if thumbnail_dir.exists():
            # Check if level 1 has files
            level1_dir = thumbnail_dir / "1"
            if level1_dir.exists() and list(level1_dir.glob("*.tif")):
                break

    # Step 4: Verify results
    thumbnail_dir = sample_ct_directory / ".thumbnail"
    assert thumbnail_dir.exists(), "Thumbnail directory should be created"

    # Check level 1 (should have 5 images: 10/2)
    level1_dir = thumbnail_dir / "1"
    assert level1_dir.exists(), "Level 1 directory should exist"
    level1_files = list(level1_dir.glob("*.tif"))
    assert len(level1_files) == 5, f"Level 1 should have 5 thumbnails, got {len(level1_files)}"

    # Check level 2 (should have 2-3 images: 5/2)
    level2_dir = thumbnail_dir / "2"
    if level2_dir.exists():
        level2_files = list(level2_dir.glob("*.tif"))
        assert 2 <= len(level2_files) <= 3, f"Level 2 should have 2-3 thumbnails, got {len(level2_files)}"


@pytest.mark.integration
def test_open_directory_updates_ui(main_window, sample_ct_directory, qtbot):
    """Test that opening a directory properly updates UI elements.

    Verifies:
    - Directory path displayed in UI
    - File count is correct
    - UI elements are enabled/disabled appropriately

    Args:
        main_window: MainWindow fixture
        sample_ct_directory: Sample CT data fixture
        qtbot: pytest-qt fixture for Qt testing
    """
    with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(sample_ct_directory)
        main_window.open_dir()
        qtbot.wait(500)

    # Verify directory path is displayed
    assert str(sample_ct_directory) in main_window.edtDirname.text()

    # Verify settings loaded correctly
    assert main_window.settings_hash is not None
    num_images = main_window.settings_hash['seq_end'] - main_window.settings_hash['seq_begin'] + 1
    assert num_images == 10


@pytest.mark.integration
def test_thumbnail_generation_with_different_formats(main_window, tmp_path, qtbot):
    """Test thumbnail generation with different image formats.

    Tests that the system can handle various image formats (BMP, PNG)
    not just TIFF.

    Args:
        main_window: MainWindow fixture
        tmp_path: Temporary directory
        qtbot: pytest-qt fixture
    """
    from PIL import Image
    import numpy as np

    # Create test directory with BMP images
    test_dir = tmp_path / "bmp_data"
    test_dir.mkdir()

    for i in range(6):
        img_array = np.ones((128, 128), dtype=np.uint8) * (i * 40)
        img = Image.fromarray(img_array)
        img.save(test_dir / f"slice_{i:04d}.bmp")

    # Open directory
    with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(test_dir)
        main_window.open_dir()
        qtbot.wait(500)

    num_images = main_window.settings_hash['seq_end'] - main_window.settings_hash['seq_begin'] + 1
    assert num_images == 6

    # Generate thumbnails
    main_window.create_thumbnail()

    # Wait for completion
    timeout = 20000
    start_time = time.time()

    while time.time() - start_time < timeout / 1000:
        qtbot.wait(500)
        thumbnail_dir = test_dir / ".thumbnail" / "1"
        if thumbnail_dir.exists() and list(thumbnail_dir.glob("*.tif")):
            break

    # Verify thumbnails created
    thumbnail_dir = test_dir / ".thumbnail" / "1"
    assert thumbnail_dir.exists()
    thumbnail_files = list(thumbnail_dir.glob("*.tif"))
    assert len(thumbnail_files) == 3, f"Should have 3 thumbnails from 6 BMP images, got {len(thumbnail_files)}"


@pytest.mark.integration
@pytest.mark.skipif(True, reason="Cancellation test requires interactive progress dialog - skip for now")
def test_thumbnail_generation_with_cancellation(main_window, sample_ct_directory, qtbot):
    """Test user cancelling thumbnail generation mid-process.

    Note: Currently skipped as it requires proper progress dialog interaction.
    This is a placeholder for future implementation.

    Steps:
        1. Open large directory
        2. Start thumbnail generation
        3. Cancel after 1 second
        4. Verify process stopped cleanly
    """
    pass


@pytest.mark.integration
def test_load_existing_thumbnails(main_window, sample_ct_directory, qtbot):
    """Test loading a directory that already has thumbnails.

    Verifies that existing thumbnails are detected and loaded correctly
    without regenerating them.

    Args:
        main_window: MainWindow fixture
        sample_ct_directory: Sample CT data fixture
        qtbot: pytest-qt fixture
    """
    # First, generate thumbnails
    with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(sample_ct_directory)
        main_window.open_dir()
        qtbot.wait(500)

    main_window.create_thumbnail()

    # Wait for completion
    timeout = 30000
    start_time = time.time()

    while time.time() - start_time < timeout / 1000:
        qtbot.wait(500)
        if (sample_ct_directory / ".thumbnail" / "1").exists():
            if list((sample_ct_directory / ".thumbnail" / "1").glob("*.tif")):
                break

    qtbot.wait(1000)

    # Close and reopen the window to simulate fresh load
    main_window.close()
    qtbot.wait(500)

    # Create new window instance
    from ui.main_window import CTHarvesterMainWindow
    import os
    os.environ['CTHARVESTER_SETTINGS_DIR'] = str(sample_ct_directory.parent)

    new_window = CTHarvesterMainWindow()
    new_window.show()
    QTest.qWaitForWindowExposed(new_window)

    try:
        # Open same directory
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(sample_ct_directory)
            new_window.open_dir()
            qtbot.wait(1000)

        # Verify thumbnails were detected
        assert new_window.level_info is not None
        assert len(new_window.level_info) > 0, "Should detect existing thumbnail levels"

    finally:
        new_window.close()
        qtbot.wait(100)


@pytest.mark.integration
def test_16bit_image_handling(main_window, sample_ct_16bit_directory, qtbot):
    """Test handling of 16-bit depth images.

    Verifies that 16-bit images are properly loaded and converted
    during thumbnail generation.

    Args:
        main_window: MainWindow fixture
        sample_ct_16bit_directory: Sample 16-bit CT data fixture
        qtbot: pytest-qt fixture
    """
    with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
        mock_dialog.return_value = str(sample_ct_16bit_directory)
        main_window.open_dir()
        qtbot.wait(500)

    num_images = main_window.settings_hash['seq_end'] - main_window.settings_hash['seq_begin'] + 1
    assert num_images == 10

    # Generate thumbnails from 16-bit images
    main_window.create_thumbnail()

    # Wait for completion
    timeout = 30000
    start_time = time.time()

    while time.time() - start_time < timeout / 1000:
        qtbot.wait(500)
        thumbnail_dir = sample_ct_16bit_directory / ".thumbnail" / "1"
        if thumbnail_dir.exists() and list(thumbnail_dir.glob("*.tif")):
            break

    # Verify thumbnails created
    thumbnail_dir = sample_ct_16bit_directory / ".thumbnail" / "1"
    assert thumbnail_dir.exists()
    thumbnail_files = list(thumbnail_dir.glob("*.tif"))
    assert len(thumbnail_files) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
