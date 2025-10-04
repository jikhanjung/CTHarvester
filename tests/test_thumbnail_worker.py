"""
Tests for core/thumbnail_worker.py - Thumbnail generation worker

Part of Phase 2 quality improvement plan (devlog 072)
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from core.thumbnail_worker import ThumbnailWorker, ThumbnailWorkerSignals


class TestThumbnailWorkerSignals:
    """Test suite for ThumbnailWorkerSignals class"""

    def test_signals_initialization(self):
        """Test ThumbnailWorkerSignals has all required signals"""
        signals = ThumbnailWorkerSignals()

        assert hasattr(signals, "finished")
        assert hasattr(signals, "error")
        assert hasattr(signals, "result")
        assert hasattr(signals, "progress")


class TestThumbnailWorker:
    """Test suite for ThumbnailWorker class"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and destination directories"""
        with tempfile.TemporaryDirectory() as src_dir:
            with tempfile.TemporaryDirectory() as dst_dir:
                yield src_dir, dst_dir

    @pytest.fixture
    def mock_progress_dialog(self):
        """Create a mock progress dialog"""
        dialog = Mock()
        dialog.is_cancelled = False
        return dialog

    @pytest.fixture
    def basic_settings(self):
        """Basic settings hash for testing"""
        return {
            "prefix": "img_",
            "index_length": 4,
            "file_type": "tif",
        }

    def test_initialization_basic(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test ThumbnailWorker initialization with basic parameters"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
            level=0,
        )

        assert worker.idx == 0
        assert worker.seq == 0
        assert worker.seq_begin == 0
        assert worker.from_dir == src_dir
        assert worker.to_dir == dst_dir
        assert worker.size == 256
        assert worker.max_thumbnail_size == 512
        assert worker.level == 0
        assert hasattr(worker, "signals")

    def test_initialization_with_seq_end(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test ThumbnailWorker initialization with seq_end parameter"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=5,
            seq=10,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
            level=1,
            seq_end=99,
        )

        assert worker.seq_end == 99
        assert worker.level == 1

    def test_filename_generation_even_index(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test filename generation for even index (paired images)"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        # Even index should generate two input filenames
        assert worker.filename1 is not None
        assert worker.filename2 is not None
        assert "img_0000.tif" in worker.filename1
        assert "img_0001.tif" in worker.filename2
        assert worker.filename3.endswith("000000.tif")

    def test_filename_generation_odd_index(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test filename generation for odd index at sequence end"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=50,
            seq=100,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
            seq_end=100,  # Last image
        )

        # Odd case at end: only one input file
        assert worker.filename1 is not None
        assert worker.filename2 is None

    def test_load_image_success_8bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _load_image with 8-bit image"""
        src_dir, dst_dir = temp_dirs

        # Create a test 8-bit image
        img_path = os.path.join(src_dir, "img_0000.tif")
        test_img = Image.new("L", (100, 100), 128)
        test_img.save(img_path)

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        img, is_16bit = worker._load_image(img_path)

        assert img is not None
        assert is_16bit is False
        assert img.mode == "L"

    def test_load_image_success_16bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _load_image with 16-bit image"""
        src_dir, dst_dir = temp_dirs

        # Create a test 16-bit image
        img_path = os.path.join(src_dir, "img_0000.tif")
        arr = np.ones((100, 100), dtype=np.uint16) * 1000
        test_img = Image.fromarray(arr)
        test_img.save(img_path)

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        img, is_16bit = worker._load_image(img_path)

        assert img is not None
        assert is_16bit is True

    def test_load_image_file_not_found(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _load_image with non-existent file"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        img_path = os.path.join(src_dir, "nonexistent.tif")
        img, is_16bit = worker._load_image(img_path)

        assert img is None
        assert is_16bit is False

    def test_process_single_image_8bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _process_single_image with 8-bit image"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        # Create 100x100 image
        test_img = Image.new("L", (100, 100), 128)
        result = worker._process_single_image(test_img, is_16bit=False)

        # Should be downscaled to 50x50
        assert result.size == (50, 50)

    def test_process_single_image_16bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _process_single_image with 16-bit image"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        # Create 100x100 16-bit image
        arr = np.ones((100, 100), dtype=np.uint16) * 1000
        test_img = Image.fromarray(arr)
        result = worker._process_single_image(test_img, is_16bit=True)

        # Should be downscaled to 50x50
        assert result.size == (50, 50)

    def test_process_image_pair_16bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _process_image_pair_16bit"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        # Create two 100x100 16-bit images
        arr1 = np.ones((100, 100), dtype=np.uint16) * 1000
        arr2 = np.ones((100, 100), dtype=np.uint16) * 2000
        img1 = Image.fromarray(arr1)
        img2 = Image.fromarray(arr2)

        result = worker._process_image_pair_16bit(img1, img2)

        # Should be averaged and downscaled to 50x50
        assert result.size == (50, 50)

    def test_process_image_pair_8bit(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test _process_image_pair_8bit"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        # Create two 100x100 8-bit images
        img1 = Image.new("L", (100, 100), 100)
        img2 = Image.new("L", (100, 100), 200)

        result = worker._process_image_pair_8bit(img1, img2)

        # Should be averaged and downscaled to 50x50
        assert result.size == (50, 50)

    def test_signals_attribute(self, temp_dirs, mock_progress_dialog, basic_settings):
        """Test worker has signals attribute of correct type"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=0,
            seq=0,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        assert isinstance(worker.signals, ThumbnailWorkerSignals)

    @pytest.mark.parametrize(
        "idx,seq,expected_filename1,expected_filename2",
        [
            (0, 0, "img_0000.tif", "img_0001.tif"),
            (1, 2, "img_0002.tif", "img_0003.tif"),
            (5, 10, "img_0010.tif", "img_0011.tif"),
        ],
    )
    def test_filename_generation_parametrized(
        self,
        temp_dirs,
        mock_progress_dialog,
        basic_settings,
        idx,
        seq,
        expected_filename1,
        expected_filename2,
    ):
        """Parametrized test for filename generation"""
        src_dir, dst_dir = temp_dirs

        worker = ThumbnailWorker(
            idx=idx,
            seq=seq,
            seq_begin=0,
            from_dir=src_dir,
            to_dir=dst_dir,
            settings_hash=basic_settings,
            size=256,
            max_thumbnail_size=512,
            progress_dialog=mock_progress_dialog,
        )

        assert expected_filename1 in worker.filename1
        assert expected_filename2 in worker.filename2
