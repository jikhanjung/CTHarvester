"""
Performance regression tests for CTHarvester.

These tests track performance metrics over time to detect regressions.
Measures execution time and memory usage for critical operations.
"""

import os
import tempfile
import time

import numpy as np
import pytest
from PIL import Image

from core.thumbnail_generator import ThumbnailGenerator
from utils.image_utils import (
    average_images,
    downsample_image,
    load_image_as_array,
    save_image_from_array,
)


@pytest.mark.benchmark
class TestImageProcessingPerformance:
    """Performance benchmarks for image processing operations"""

    @pytest.fixture
    def test_image_8bit(self):
        """Create 8-bit test image"""
        return np.random.randint(0, 256, (512, 512), dtype=np.uint8)

    @pytest.fixture
    def test_image_16bit(self):
        """Create 16-bit test image"""
        return np.random.randint(0, 65536, (512, 512), dtype=np.uint16)

    def test_downsample_8bit_performance(self, test_image_8bit):
        """Benchmark downsampling performance for 8-bit images"""
        start = time.perf_counter()

        result = downsample_image(test_image_8bit, factor=2, method="subsample")

        elapsed = time.perf_counter() - start

        assert result.shape == (256, 256)
        assert elapsed < 0.1, f"Downsampling too slow: {elapsed:.3f}s"

    def test_downsample_16bit_performance(self, test_image_16bit):
        """Benchmark downsampling performance for 16-bit images"""
        start = time.perf_counter()

        result = downsample_image(test_image_16bit, factor=2, method="subsample")

        elapsed = time.perf_counter() - start

        assert result.shape == (256, 256)
        assert elapsed < 0.1, f"Downsampling too slow: {elapsed:.3f}s"

    def test_average_images_8bit_performance(self, test_image_8bit):
        """Benchmark image averaging for 8-bit images"""
        img1 = test_image_8bit
        img2 = np.random.randint(0, 256, (512, 512), dtype=np.uint8)

        start = time.perf_counter()
        result = average_images(img1, img2)
        elapsed = time.perf_counter() - start

        assert result.shape == img1.shape
        assert elapsed < 0.05, f"Averaging too slow: {elapsed:.3f}s"

    def test_average_images_16bit_performance(self, test_image_16bit):
        """Benchmark image averaging for 16-bit images"""
        img1 = test_image_16bit
        img2 = np.random.randint(0, 65536, (512, 512), dtype=np.uint16)

        start = time.perf_counter()
        result = average_images(img1, img2)
        elapsed = time.perf_counter() - start

        assert result.shape == img1.shape
        assert elapsed < 0.05, f"Averaging too slow: {elapsed:.3f}s"


@pytest.mark.benchmark
@pytest.mark.slow
class TestThumbnailGenerationPerformance:
    """Performance benchmarks for thumbnail generation"""

    @pytest.fixture
    def small_dataset(self):
        """Create small test dataset (20 images)"""
        temp_dir = tempfile.mkdtemp()

        for i in range(20):
            img_array = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(os.path.join(temp_dir, f"slice_{i:04d}.tif"))

        yield temp_dir

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    def test_work_calculation_performance(self):
        """Benchmark thumbnail work calculation"""
        generator = ThumbnailGenerator()

        start = time.perf_counter()
        result = generator.calculate_total_thumbnail_work(
            seq_begin=0, seq_end=99, size=2048, max_size=256
        )
        elapsed = time.perf_counter() - start

        assert result > 0
        assert elapsed < 0.01, f"Work calculation too slow: {elapsed:.3f}s"

    def test_load_thumbnail_data_performance(self, small_dataset):
        """Benchmark loading existing thumbnails"""
        from PyQt5.QtCore import QThreadPool

        generator = ThumbnailGenerator()

        # First generate thumbnails
        settings = {
            "image_width": "256",
            "image_height": "256",
            "seq_begin": 0,
            "seq_end": 19,
            "prefix": "slice_",
            "index_length": 4,
            "file_type": "tif",
        }

        threadpool = QThreadPool()

        # Generate once
        generator.generate(
            directory=small_dataset,
            settings=settings,
            threadpool=threadpool,
            use_rust_preference=False,
            progress_dialog=None,
        )

        # Benchmark loading
        start = time.perf_counter()
        images, level_info = generator.load_thumbnail_data(
            directory=small_dataset, settings_hash=settings, level=0
        )
        elapsed = time.perf_counter() - start

        assert len(images) > 0
        assert elapsed < 0.5, f"Loading thumbnails too slow: {elapsed:.3f}s"


@pytest.mark.benchmark
class TestFileIOPerformance:
    """Performance benchmarks for file I/O operations"""

    @pytest.fixture
    def temp_file(self):
        """Create temporary file path"""
        fd, path = tempfile.mkstemp(suffix=".tif")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_save_image_8bit_performance(self, temp_file):
        """Benchmark saving 8-bit images"""
        img_array = np.random.randint(0, 256, (512, 512), dtype=np.uint8)

        start = time.perf_counter()
        result = save_image_from_array(img_array, temp_file, compress=False)
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.1, f"Saving 8-bit image too slow: {elapsed:.3f}s"

    def test_save_image_16bit_performance(self, temp_file):
        """Benchmark saving 16-bit images"""
        img_array = np.random.randint(0, 65536, (512, 512), dtype=np.uint16)

        start = time.perf_counter()
        result = save_image_from_array(img_array, temp_file, compress=False)
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.1, f"Saving 16-bit image too slow: {elapsed:.3f}s"

    def test_load_image_8bit_performance(self, temp_file):
        """Benchmark loading 8-bit images"""
        # Create test image
        img_array = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
        save_image_from_array(img_array, temp_file, compress=False)

        start = time.perf_counter()
        result = load_image_as_array(temp_file, target_dtype=np.uint8)
        elapsed = time.perf_counter() - start

        assert result.shape == (512, 512)
        assert elapsed < 0.1, f"Loading 8-bit image too slow: {elapsed:.3f}s"

    def test_load_image_16bit_performance(self, temp_file):
        """Benchmark loading 16-bit images"""
        # Create test image
        img_array = np.random.randint(0, 65536, (512, 512), dtype=np.uint16)
        save_image_from_array(img_array, temp_file, compress=False)

        start = time.perf_counter()
        result = load_image_as_array(temp_file, target_dtype=np.uint16)
        elapsed = time.perf_counter() - start

        assert result.shape == (512, 512)
        assert elapsed < 0.1, f"Loading 16-bit image too slow: {elapsed:.3f}s"


@pytest.mark.benchmark
class TestMemoryUsageTracking:
    """Track memory usage during operations"""

    def test_large_image_memory_footprint(self):
        """Verify memory-efficient handling of large images"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create and process large image (4096x4096, 16-bit = 32MB)
        large_img = np.random.randint(0, 65536, (4096, 4096), dtype=np.uint16)
        downsampled = downsample_image(large_img, factor=2, method="subsample")

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        # Memory increase should be reasonable (< 100MB for 32MB image)
        assert mem_increase < 100, f"Memory increase too large: {mem_increase:.1f}MB"
        assert downsampled.shape == (2048, 2048)

    def test_thumbnail_generation_memory_limit(self, temp_image_dir):
        """Verify thumbnail generation doesn't leak memory"""
        import os

        import psutil
        from PyQt5.QtCore import QThreadPool

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        generator = ThumbnailGenerator()
        settings = {
            "image_width": "100",
            "image_height": "100",
            "seq_begin": 0,
            "seq_end": 9,
            "prefix": "test_",
            "index_length": 4,
            "file_type": "tif",
        }

        threadpool = QThreadPool()

        # Generate thumbnails
        generator.generate(
            directory=temp_image_dir,
            settings=settings,
            threadpool=threadpool,
            use_rust_preference=False,
            progress_dialog=None,
        )

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        # Memory increase should be minimal for 10 small images
        assert mem_increase < 50, f"Memory increase too large: {mem_increase:.1f}MB"
