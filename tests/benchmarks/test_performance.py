"""
Performance benchmarks for CTHarvester

Tests performance characteristics and validates against thresholds.
Created during Phase 3 (Performance & Robustness).
"""

import gc
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.benchmarks.benchmark_config import BenchmarkScenarios, PerformanceThresholds


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    @pytest.fixture
    def temp_test_images(self, tmp_path):
        """Create temporary test images for benchmarking"""

        def _create_images(scenario):
            """Create test images for a scenario"""
            test_dir = tmp_path / f"benchmark_{scenario.name.lower()}"
            test_dir.mkdir(exist_ok=True)

            images = []
            width, height = scenario.image_size

            for i in range(scenario.image_count):
                # Create test image with some variation
                if scenario.bit_depth == 8:
                    img_array = np.random.randint(0, 256, (height, width), dtype=np.uint8)
                else:  # 16-bit
                    img_array = np.random.randint(0, 65536, (height, width), dtype=np.uint16)

                img = Image.fromarray(img_array)
                img_path = test_dir / f"test_{i:04d}.png"
                img.save(img_path)
                images.append(img_path)

            return test_dir, images

        return _create_images

    def test_small_dataset_performance(self, temp_test_images):
        """Test performance with small dataset"""
        scenario = BenchmarkScenarios.SMALL
        test_dir, images = temp_test_images(scenario)

        # Measure memory before
        gc.collect()
        import psutil

        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Time the operation
        start_time = time.time()

        # Load and process images
        loaded_images = []
        for img_path in images:
            img = Image.open(img_path)
            loaded_images.append(np.array(img))

        elapsed = time.time() - start_time

        # Measure memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        # Validate performance
        expected_time = PerformanceThresholds.get_expected_time(scenario, "full")
        expected_mem = PerformanceThresholds.get_expected_memory(scenario)

        # Allow 2x overhead for processing
        assert (
            elapsed < expected_time * 2
        ), f"Too slow: {elapsed:.2f}s vs expected {expected_time:.2f}s"

        # Allow 3x overhead for memory
        assert (
            mem_used < expected_mem * 3
        ), f"Too much memory: {mem_used:.2f}MB vs expected {expected_mem:.2f}MB"

        # Clean up
        loaded_images.clear()
        gc.collect()

    def test_medium_dataset_performance(self, temp_test_images):
        """Test performance with medium dataset"""
        scenario = BenchmarkScenarios.MEDIUM
        test_dir, images = temp_test_images(scenario)

        gc.collect()
        import psutil

        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024

        start_time = time.time()

        # Process in batches to avoid excessive memory
        batch_size = 20
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            for img_path in batch:
                img = Image.open(img_path)
                _ = np.array(img)
            gc.collect()

        elapsed = time.time() - start_time
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_used = mem_after - mem_before

        expected_time = PerformanceThresholds.get_expected_time(scenario, "full")
        expected_mem = PerformanceThresholds.get_expected_memory(scenario)

        # Medium dataset allows 2x time overhead
        assert (
            elapsed < expected_time * 2
        ), f"Too slow: {elapsed:.2f}s vs expected {expected_time:.2f}s"

        # Memory should be reasonable with batching
        assert (
            mem_used < expected_mem
        ), f"Too much memory: {mem_used:.2f}MB vs expected {expected_mem:.2f}MB"

        gc.collect()

    @pytest.mark.slow
    def test_large_dataset_performance(self, temp_test_images):
        """Test performance with large dataset (marked slow for optional testing)"""
        scenario = BenchmarkScenarios.LARGE
        test_dir, images = temp_test_images(scenario)

        gc.collect()
        import psutil

        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024

        start_time = time.time()

        # Process in batches
        batch_size = 50
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            for img_path in batch:
                img = Image.open(img_path)
                _ = np.array(img)
            gc.collect()

        elapsed = time.time() - start_time
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_used = mem_after - mem_before

        expected_time = PerformanceThresholds.get_expected_time(scenario, "full")
        expected_mem = PerformanceThresholds.get_expected_memory(scenario)

        # Large dataset allows 2.5x time overhead
        assert (
            elapsed < expected_time * 2.5
        ), f"Too slow: {elapsed:.2f}s vs expected {expected_time:.2f}s"

        # Memory with batching should be manageable
        assert (
            mem_used < expected_mem * 1.5
        ), f"Too much memory: {mem_used:.2f}MB vs expected {expected_mem:.2f}MB"

        gc.collect()


class TestThumbnailPerformance:
    """Test thumbnail generation performance"""

    def test_image_resize_performance(self, tmp_path):
        """Test basic image resize performance (simulates thumbnail generation)"""
        # Create test images
        test_images = []
        for i in range(10):
            test_img = tmp_path / f"test_{i}.png"
            img_array = np.random.randint(0, 256, (1024, 1024), dtype=np.uint8)
            Image.fromarray(img_array).save(test_img)
            test_images.append(test_img)

        # Time image loading and resizing (core of thumbnail generation)
        iterations = len(test_images)
        start = time.time()

        for img_path in test_images:
            img = Image.open(img_path)
            img.thumbnail((256, 256))
            _ = np.array(img)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        # Should be faster than 200ms per image (Python fallback threshold)
        assert avg_time < 0.2, f"Image processing too slow: {avg_time*1000:.1f}ms per image"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
