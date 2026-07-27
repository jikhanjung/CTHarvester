"""
Stress tests for CTHarvester

Tests long-running operations, memory stability, and resource cleanup.
Created during Phase 3 (Performance & Robustness).
"""

import gc
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.benchmarks.benchmark_config import BenchmarkScenarios


class TestLongRunningOperations:
    """Test stability during long-running operations"""

    @pytest.fixture
    def temp_test_images(self, tmp_path):
        """Create temporary test images"""

        def _create_images(count, size=(512, 512), bit_depth=8):
            """Create test images"""
            test_dir = tmp_path / f"stress_test_{count}"
            test_dir.mkdir(exist_ok=True)

            images = []
            width, height = size

            for i in range(count):
                if bit_depth == 8:
                    img_array = np.random.randint(0, 256, (height, width), dtype=np.uint8)
                else:
                    img_array = np.random.randint(0, 65536, (height, width), dtype=np.uint16)

                img = Image.fromarray(img_array)
                img_path = test_dir / f"test_{i:04d}.png"
                img.save(img_path)
                images.append(img_path)

            return test_dir, images

        return _create_images

    def test_repeated_operations(self, temp_test_images):
        """Test repeated load/unload cycles for memory leaks"""
        test_dir, images = temp_test_images(count=20, size=(256, 256))

        import psutil

        process = psutil.Process()

        # Run multiple cycles
        iterations = 5
        memory_measurements = []

        for _i in range(iterations):
            gc.collect()
            mem_before = process.memory_info().rss / 1024 / 1024

            # Load all images
            loaded = []
            for img_path in images:
                img = Image.open(img_path)
                loaded.append(np.array(img))

            # Unload
            loaded.clear()
            gc.collect()

            mem_after = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(mem_after - mem_before)

        # Memory usage should be stable (not growing significantly)
        # Allow some growth but not linear increase
        first_half_avg = sum(memory_measurements[: iterations // 2]) / (iterations // 2)
        second_half_avg = sum(memory_measurements[iterations // 2 :]) / (iterations // 2 + 1)

        # Second half should not use significantly more memory than first half.
        #
        # The absolute slack matters as much as the ratio: with a purely
        # multiplicative bound, a run where RSS never moves gives
        # `0.0 < 0.0 * 1.5`, which is False -- the test failed precisely when
        # the result was perfect. That is what happens on macOS CI and under
        # WSL2, where the allocator does not hand pages back between cycles.
        LEAK_SLACK_MB = 5.0
        assert second_half_avg < first_half_avg * 1.5 + LEAK_SLACK_MB, (
            f"Memory leak detected: {first_half_avg:.1f}MB -> {second_half_avg:.1f}MB"
        )

    @pytest.mark.slow
    def test_continuous_processing(self, temp_test_images):
        """Test continuous processing without crashes"""
        test_dir, images = temp_test_images(count=50, size=(512, 512))

        import psutil

        process = psutil.Process()
        mem_start = process.memory_info().rss / 1024 / 1024

        # Process in batches continuously
        batch_size = 10
        batches_processed = 0

        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]

            # Process batch
            for img_path in batch:
                img = Image.open(img_path)
                img_array = np.array(img)
                # Simulate some processing
                _ = img_array.mean()

            batches_processed += 1
            gc.collect()

        mem_end = process.memory_info().rss / 1024 / 1024
        mem_used = mem_end - mem_start

        # Should have processed all batches
        assert batches_processed == (len(images) + batch_size - 1) // batch_size

        # Memory usage should be reasonable (not accumulating)
        # After GC, should be back to reasonable levels
        assert mem_used < 200, f"Excessive memory usage: {mem_used:.1f}MB"


class TestMemoryStability:
    """Test memory stability and cleanup"""

    def test_memory_cleanup_after_operation(self, tmp_path):
        """Loaded image arrays are released once the last reference is dropped.

        This used to assert that RSS fell back toward the baseline after
        gc.collect(). It does not, reliably, anywhere: returning freed pages to
        the operating system is an allocator decision, and neither glibc nor the
        macOS allocator promises it. The assertion read 0% freed on the macOS
        runners and under WSL2 -- a statement about malloc, not about
        CTHarvester.

        What the test actually means to catch is a leak in our own code: a
        reference cycle or a stray container keeping decoded arrays alive after
        the caller is done with them. Weak references test exactly that, and
        deterministically, on every platform.
        """
        import weakref

        import psutil

        process = psutil.Process()

        gc.collect()
        mem_baseline = process.memory_info().rss / 1024 / 1024

        test_dir = tmp_path / "memory_test"
        test_dir.mkdir()

        images = []
        for i in range(30):
            img_array = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img_path = test_dir / f"test_{i:04d}.png"
            img.save(img_path)
            images.append(img_path)

        loaded = []
        for img_path in images:
            with Image.open(img_path) as img:
                loaded.append(np.array(img))

        # One weak reference per decoded array. They must all die once `loaded`
        # is the only thing holding them and it goes away.
        refs = [weakref.ref(arr) for arr in loaded]
        assert all(r() is not None for r in refs), "arrays died while still referenced"

        mem_loaded = process.memory_info().rss / 1024 / 1024

        loaded.clear()
        del loaded
        gc.collect()

        alive = [i for i, r in enumerate(refs) if r() is not None]
        assert not alive, (
            f"{len(alive)} of {len(refs)} arrays still reachable after the last "
            f"reference was dropped (indices {alive[:5]}...) - something is "
            f"holding them"
        )

        # RSS is reported for diagnostics only, never asserted on. See docstring.
        mem_after_cleanup = process.memory_info().rss / 1024 / 1024
        print(
            f"\nRSS baseline={mem_baseline:.1f}MB loaded={mem_loaded:.1f}MB "
            f"after cleanup={mem_after_cleanup:.1f}MB"
        )

    def test_large_array_cleanup(self):
        """Test cleanup of large numpy arrays"""
        import psutil

        process = psutil.Process()

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Create large array (approximately 800MB)
        # pyflakes does not count the `del large_array` below as a use, but the
        # binding is exactly what holds the allocation this test measures.
        large_array = np.zeros((2048, 2048, 100), dtype=np.uint16)  # noqa: F841
        mem_allocated = process.memory_info().rss / 1024 / 1024

        allocated = mem_allocated - mem_before

        # If memory was actually allocated (OS may delay allocation)
        if allocated > 10:  # At least 10MB allocated
            # Delete and collect
            del large_array
            gc.collect()

            mem_after = process.memory_info().rss / 1024 / 1024

            # Should have freed most of the memory
            freed = mem_allocated - mem_after

            assert freed > allocated * 0.5, (
                f"Large array not properly freed: {freed:.1f}/{allocated:.1f}MB"
            )
        else:
            # Memory not tracked by RSS or OS optimized allocation
            # Just verify deletion doesn't crash
            del large_array
            gc.collect()
            # Test passes if we get here without error


class TestResourceCleanup:
    """Test proper resource cleanup"""

    def test_file_handles_closed(self, tmp_path):
        """Test that file handles are properly closed"""
        # Create test files
        test_files = []
        for i in range(10):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text(f"Test {i}")
            test_files.append(test_file)

        # Open and close files
        handles = []
        for f in test_files:
            # noqa: SIM115 -- holding the handles open is the point. This test
            # checks that files can be deleted once every handle is released,
            # which a context manager per file would close too early to observe.
            handle = open(f)  # noqa: SIM115
            handles.append(handle)

        # Close all
        for h in handles:
            h.close()

        # Should be able to delete files (no handles holding them)
        for f in test_files:
            f.unlink()

        # Verify deleted
        for f in test_files:
            assert not f.exists()

    def test_image_resources_released(self, tmp_path):
        """Test that PIL image resources are released"""
        # Create test image
        test_img = tmp_path / "test.png"
        img_array = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
        Image.fromarray(img_array).save(test_img)

        # Open multiple times
        for _ in range(5):
            img = Image.open(test_img)
            _ = np.array(img)
            img.close()  # Explicitly close

        # Should be able to delete
        test_img.unlink()
        assert not test_img.exists()

    def test_temp_directory_cleanup(self, tmp_path):
        """Test cleanup of temporary directories"""
        # Create nested structure
        test_dir = tmp_path / "test_cleanup"
        test_dir.mkdir()

        for i in range(5):
            subdir = test_dir / f"sub_{i}"
            subdir.mkdir()
            (subdir / "file.txt").write_text("test")

        # Verify created
        assert test_dir.exists()
        assert len(list(test_dir.iterdir())) == 5

        # Cleanup
        import shutil

        shutil.rmtree(test_dir)

        # Verify cleaned up
        assert not test_dir.exists()


class TestConcurrentOperations:
    """Test behavior under concurrent operations"""

    def test_multiple_batch_processing(self, tmp_path):
        """Test processing multiple batches in sequence"""
        # Create test images
        test_dir = tmp_path / "concurrent"
        test_dir.mkdir()

        for i in range(40):
            img_array = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
            Image.fromarray(img_array).save(test_dir / f"test_{i:04d}.png")

        images = sorted(test_dir.glob("*.png"))

        # Process in multiple batches
        batch_size = 10
        results = []

        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            batch_results = []

            for img_path in batch:
                img = Image.open(img_path)
                batch_results.append(np.array(img).mean())

            results.extend(batch_results)
            gc.collect()

        # All images should be processed
        assert len(results) == len(images)

    def test_rapid_creation_deletion(self, tmp_path):
        """Test rapid creation and deletion of objects"""
        import psutil

        process = psutil.Process()

        gc.collect()
        mem_start = process.memory_info().rss / 1024 / 1024

        # Rapidly create and delete
        for _iteration in range(10):
            objects = []

            # Create
            for _i in range(20):
                obj = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
                objects.append(obj)

            # Delete
            objects.clear()
            gc.collect()

        mem_end = process.memory_info().rss / 1024 / 1024

        # Memory should not grow significantly
        mem_growth = mem_end - mem_start
        assert mem_growth < 50, f"Memory grew too much: {mem_growth:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
