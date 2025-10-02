# Parallel Image Loading Implementation Plan

**Date**: 2025-10-02
**Status**: ❌ REJECTED - Previously tested and abandoned
**Priority**: N/A
**Performance Gain**: N/A (Negative in practice)

## Decision Summary

After review, this plan has been **rejected** based on previous empirical evidence.

**Reason for Rejection**:
This approach was **already attempted and failed** in September 2025 (see devlog entries 017, 019, 020).

**Problems Discovered During Previous Implementation**:
1. **GIL (Global Interpreter Lock)** - CPU operations cannot parallelize
2. **Disk I/O Contention** - Multiple threads cause random disk access → 10-100x slower seek time
3. **PIL Internal Locks** - Image.open(), copy(), save() experience 10-20 second lock waits
4. **Memory Allocator Contention** - NumPy array allocation locks cause delays
5. **Unpredictable Performance** - Most images process normally, but random ones hang for 10-20 seconds

**Performance Results (3000 images, tested)**:
- Python Multithreaded: Average 6-7 min, **worst case 30-40 min** (unstable)
- Python Single-threaded: Consistent **9-10 min** (stable) ✅
- Rust Multithreaded: **2-3 min** (optimal) ✅

**Current Architecture Decision**:
- **Tier 1 (Primary)**: Rust module with true multithreading
- **Tier 2 (Fallback)**: Python single-thread for stability when Rust unavailable
- Python is a **backup implementation** - goal is "stable operation" not "maximum performance"

**Verdict**: Keep Python implementation single-threaded. Predictable performance > unpredictable speed.

**Reference Documents**:
- `20250930_017_multithreading_bottleneck_analysis.md`
- `20250930_019_threading_strategy_clarification.md`
- `20250930_020_rust_vs_python_io_strategy.md`

---

## Original Plan (Archived for Historical Reference)

## Current Implementation

### Sequential Loading in thumbnail_generator.py

**Location**: `core/thumbnail_generator.py:647-651`
```python
minimum_volume = []
for tif_file in tif_files:
    try:
        with Image.open(os.path.join(smallest_dir, tif_file)) as img:
            minimum_volume.append(np.array(img))
    except (OSError, IOError) as e:
        logger.error(f"Error loading {tif_file}: {e}")
```

**Performance**:
- Loads images one at a time
- I/O bound operation (disk read bottleneck)
- CPU underutilized during disk waits
- ~200ms per image on HDD, ~50ms on SSD

**For 100 images**:
- HDD: 20 seconds
- SSD: 5 seconds

---

## Problem Analysis

### Why Sequential Loading is Slow

1. **I/O Bottleneck**
   - Disk read is blocking
   - CPU idle while waiting for disk
   - Single-threaded I/O limited by disk latency

2. **No Pipelining**
   - Can't decompress while reading
   - Can't convert while decompressing
   - No overlap of operations

3. **Memory Inefficiency**
   - All data loaded before processing begins
   - No streaming capability

### Expected vs Actual Throughput

```
Sequential (1 thread):
  Image 1: [===Read===][==Decode==][=Convert=]
  Image 2:                                      [===Read===][==Decode==][=Convert=]
  Total: 300ms * 100 = 30 seconds

Parallel (4 threads):
  Image 1: [===Read===][==Decode==][=Convert=]
  Image 2: [===Read===][==Decode==][=Convert=]
  Image 3: [===Read===][==Decode==][=Convert=]
  Image 4: [===Read===][==Decode==][=Convert=]
  Image 5:    [===Read===][==Decode==][=Convert=]
  Total: 300ms * 25 = 7.5 seconds (4x faster)
```

---

## Proposed Solutions

### Option 1: ThreadPoolExecutor (Recommended)

**Pros**:
- Built-in to Python standard library
- Simple API, easy to implement
- Good for I/O-bound tasks
- Automatic thread management

**Cons**:
- GIL limits true parallelism for CPU tasks
- Thread overhead for very small images

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import logging
import time

logger = logging.getLogger("CTHarvester")


def load_single_image(file_path: str) -> tuple[str, np.ndarray]:
    """Load a single image file.

    Args:
        file_path: Path to image file

    Returns:
        Tuple of (filename, image_array)

    Raises:
        OSError, IOError: If image cannot be loaded
    """
    from PIL import Image
    import numpy as np

    with Image.open(file_path) as img:
        return (Path(file_path).name, np.array(img))


def load_images_parallel(
    image_dir: Path,
    file_names: list[str],
    max_workers: int = 4,
    progress_callback=None
) -> tuple[list[np.ndarray], dict]:
    """Load images in parallel using ThreadPoolExecutor.

    Args:
        image_dir: Directory containing images
        file_names: List of filenames to load
        max_workers: Maximum number of threads (default: 4)
        progress_callback: Optional callback(completed, total, filename)

    Returns:
        Tuple of:
            - List of numpy arrays in order
            - Stats dict with timing info

    Example:
        >>> files = ["img_0001.tif", "img_0002.tif", ...]
        >>> arrays, stats = load_images_parallel(
        ...     Path("/data/ct"),
        ...     files,
        ...     max_workers=4,
        ...     progress_callback=lambda c, t, f: print(f"{c}/{t}: {f}")
        ... )
    """
    start_time = time.time()
    results = {}
    errors = []

    # Create full paths
    file_paths = [image_dir / fname for fname in file_names]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(load_single_image, str(path)): path
            for path in file_paths
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                filename, img_array = future.result()
                results[filename] = img_array
                completed += 1

                if progress_callback:
                    progress_callback(completed, len(file_names), filename)

            except Exception as e:
                logger.error(f"Failed to load {file_path.name}: {e}")
                errors.append((file_path.name, str(e)))

    # Reconstruct ordered list
    ordered_arrays = []
    for fname in file_names:
        if fname in results:
            ordered_arrays.append(results[fname])
        else:
            logger.warning(f"Missing image: {fname}")
            # Could insert None or skip

    elapsed = time.time() - start_time
    stats = {
        'total_time': elapsed,
        'images_loaded': len(ordered_arrays),
        'images_failed': len(errors),
        'avg_time_per_image': elapsed / len(file_names) if file_names else 0,
        'throughput': len(ordered_arrays) / elapsed if elapsed > 0 else 0,
        'errors': errors
    }

    logger.info(
        f"Loaded {len(ordered_arrays)} images in {elapsed:.2f}s "
        f"({stats['throughput']:.1f} images/sec)"
    )

    return ordered_arrays, stats


# Integration into thumbnail_generator.py:
def load_minimum_volume_parallel(self, smallest_dir, tif_files):
    """Load minimum volume using parallel image loading.

    Replaces the sequential loop at lines 647-651.
    """
    import os
    from pathlib import Path

    # Determine optimal worker count
    import psutil
    cpu_count = psutil.cpu_count(logical=False) or 4
    max_workers = min(cpu_count, 8)  # Cap at 8 threads

    logger.info(f"Loading {len(tif_files)} images with {max_workers} threads")

    def progress_cb(completed, total, filename):
        if completed % 10 == 0 or completed <= 5:
            logger.debug(f"Loaded {completed}/{total}: {filename}")

    arrays, stats = load_images_parallel(
        Path(smallest_dir),
        tif_files,
        max_workers=max_workers,
        progress_callback=progress_cb
    )

    if arrays:
        minimum_volume = np.array(arrays)
        logger.info(f"Loaded minimum_volume: shape {minimum_volume.shape}")
        logger.info(
            f"Performance: {stats['throughput']:.1f} images/sec "
            f"({stats['total_time']:.2f}s total)"
        )
        return minimum_volume
    else:
        logger.error("No thumbnails loaded")
        return None
```

---

### Option 2: ProcessPoolExecutor

**Pros**:
- True parallelism (no GIL)
- Better CPU utilization
- Good for mixed I/O and CPU tasks

**Cons**:
- Higher overhead (process creation)
- More memory usage (each process has own memory)
- Harder to share data (pickling overhead)

**When to Use**:
- Very large images requiring CPU-intensive decoding
- Many CPU cores available (8+)
- Minimal data sharing needed

**Implementation**:
```python
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count


def load_images_process_pool(
    image_dir: Path,
    file_names: list[str],
    max_workers: int = None
) -> list[np.ndarray]:
    """Load images using process pool.

    Uses separate processes to bypass GIL.
    Best for CPU-intensive image decoding.
    """
    if max_workers is None:
        max_workers = cpu_count()

    file_paths = [image_dir / fname for fname in file_names]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Map will preserve order
        results = list(executor.map(load_single_image_worker, file_paths))

    # Extract arrays from results
    arrays = [arr for _, arr in results if arr is not None]
    return arrays


def load_single_image_worker(file_path: Path) -> tuple[str, np.ndarray]:
    """Worker function for process pool.

    Must be picklable (top-level function).
    """
    from PIL import Image
    import numpy as np

    try:
        with Image.open(file_path) as img:
            return (file_path.name, np.array(img))
    except Exception as e:
        return (file_path.name, None)
```

---

### Option 3: asyncio (For Future Consideration)

**Pros**:
- Very lightweight (no thread overhead)
- Excellent for many concurrent I/O operations
- Can handle thousands of concurrent tasks

**Cons**:
- Requires async/await refactoring
- PIL is synchronous (needs ThreadPoolExecutor anyway)
- More complex error handling

**Not Recommended**: PIL/Pillow is synchronous, so asyncio provides no benefit over ThreadPoolExecutor for this use case.

---

## Performance Comparison

### Benchmark Results (Simulated)

**Test Setup**: 100 images, 512x512, 8-bit TIFF

| Method | Time (SSD) | Time (HDD) | Speedup | Memory |
|--------|------------|------------|---------|---------|
| **Sequential** | 5.0s | 20.0s | 1.0x | Baseline |
| **ThreadPool (2)** | 2.8s | 11.5s | 1.8x | +50MB |
| **ThreadPool (4)** | 1.6s | 6.5s | 3.1x | +100MB |
| **ThreadPool (8)** | 1.3s | 5.8s | 3.8x | +150MB |
| **ProcessPool (4)** | 1.8s | 7.0s | 2.8x | +400MB |

**Optimal Configuration**:
- **SSD**: 4 threads (3.1x speedup, reasonable memory)
- **HDD**: 4 threads (3.1x speedup, I/O still bottleneck)
- **Network**: 8 threads (higher latency benefits from more concurrency)

---

## Adaptive Worker Count

### Smart Worker Selection

```python
def determine_optimal_workers(
    image_count: int,
    image_dir: Path,
    available_memory_mb: int
) -> int:
    """Determine optimal number of worker threads.

    Considers:
        - CPU core count
        - Available memory
        - Disk type (SSD vs HDD)
        - Number of images

    Args:
        image_count: Number of images to load
        image_dir: Directory path (for disk type detection)
        available_memory_mb: Available system memory

    Returns:
        Optimal number of worker threads (1-8)
    """
    import psutil

    # Base on CPU cores
    cpu_cores = psutil.cpu_count(logical=False) or 4
    max_workers = min(cpu_cores, 8)  # Cap at 8

    # Reduce if few images
    if image_count < 20:
        max_workers = min(max_workers, 2)
    elif image_count < 50:
        max_workers = min(max_workers, 4)

    # Reduce if low memory
    memory_per_thread_mb = 100  # Estimated
    if available_memory_mb < memory_per_thread_mb * max_workers:
        max_workers = max(1, available_memory_mb // memory_per_thread_mb)

    # Check disk type
    try:
        import platform
        if platform.system() == 'Windows':
            drive = os.path.splitdrive(str(image_dir))[0]
            # Could check if SSD via WMI, but complex
        # On Linux, check /sys/block/*/queue/rotational
        # 0 = SSD, 1 = HDD
    except:
        pass

    logger.info(
        f"Selected {max_workers} workers for {image_count} images "
        f"(CPU cores: {cpu_cores}, available memory: {available_memory_mb}MB)"
    )

    return max_workers
```

---

## Migration Strategy

### Phase 1: Add Parallel Loading Function (Non-Breaking)

1. Add `utils/parallel_loader.py` with parallel loading functions
2. Add comprehensive tests
3. Add benchmarks to measure actual speedup
4. No changes to existing code yet

### Phase 2: Add Configuration Option

```python
# In settings or constants
ENABLE_PARALLEL_LOADING = True  # Feature flag
PARALLEL_LOADING_WORKERS = 4    # Or 'auto'
```

### Phase 3: Integrate into thumbnail_generator.py

```python
def load_minimum_volume(self, smallest_dir, tif_files):
    """Load minimum volume with optional parallel loading."""
    from config.constants import ENABLE_PARALLEL_LOADING

    if ENABLE_PARALLEL_LOADING and len(tif_files) > 10:
        # Use parallel loading for larger datasets
        return self._load_minimum_volume_parallel(smallest_dir, tif_files)
    else:
        # Fall back to sequential for small datasets
        return self._load_minimum_volume_sequential(smallest_dir, tif_files)
```

### Phase 4: Performance Validation

1. Run benchmarks on various datasets
2. Compare memory usage
3. Verify no regressions
4. Document optimal settings

### Phase 5: Enable by Default

1. Set `ENABLE_PARALLEL_LOADING = True` in production
2. Update documentation
3. Add troubleshooting guide

---

## Error Handling

### Robust Error Recovery

```python
def load_images_parallel_robust(
    image_dir: Path,
    file_names: list[str],
    max_workers: int = 4,
    retry_count: int = 2
) -> tuple[list[np.ndarray], dict]:
    """Load images with retry logic and graceful degradation."""
    import time

    results = {}
    errors = {}

    def load_with_retry(file_path: Path, retries: int = retry_count):
        """Try loading with exponential backoff."""
        for attempt in range(retries + 1):
            try:
                with Image.open(file_path) as img:
                    return np.array(img)
            except Exception as e:
                if attempt < retries:
                    wait_time = 2 ** attempt * 0.1  # 0.1s, 0.2s, 0.4s
                    time.sleep(wait_time)
                    logger.warning(
                        f"Retry {attempt+1}/{retries} for {file_path.name}"
                    )
                else:
                    raise e

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(load_with_retry, image_dir / fname): fname
            for fname in file_names
        }

        for future in as_completed(future_to_file):
            fname = future_to_file[future]
            try:
                results[fname] = future.result()
            except Exception as e:
                errors[fname] = str(e)
                logger.error(f"Failed to load {fname} after retries: {e}")

    # Build ordered list, filling gaps with None or interpolation
    ordered = []
    for fname in file_names:
        if fname in results:
            ordered.append(results[fname])
        else:
            # Could interpolate from neighbors or insert None
            logger.warning(f"Skipping missing image: {fname}")

    return ordered, {'errors': errors, 'success': len(results)}
```

---

## Testing Strategy

### Unit Tests

```python
def test_parallel_loading_vs_sequential(tmp_path):
    """Compare parallel vs sequential loading."""
    from PIL import Image
    import numpy as np
    import time

    # Create test images
    ct_dir = tmp_path / "test_data"
    ct_dir.mkdir()

    for i in range(50):
        img = Image.fromarray(np.random.randint(0, 255, (512, 512), dtype=np.uint8))
        img.save(ct_dir / f"img_{i:04d}.tif")

    file_names = [f"img_{i:04d}.tif" for i in range(50)]

    # Sequential
    start = time.time()
    seq_results = []
    for fname in file_names:
        with Image.open(ct_dir / fname) as img:
            seq_results.append(np.array(img))
    seq_time = time.time() - start

    # Parallel
    start = time.time()
    par_results, _ = load_images_parallel(ct_dir, file_names, max_workers=4)
    par_time = time.time() - start

    # Verify same results
    assert len(par_results) == len(seq_results)
    for i in range(len(par_results)):
        np.testing.assert_array_equal(par_results[i], seq_results[i])

    # Check speedup
    speedup = seq_time / par_time
    print(f"Speedup: {speedup:.2f}x (sequential: {seq_time:.2f}s, parallel: {par_time:.2f}s)")
    assert speedup > 1.5  # Expect at least 1.5x speedup


def test_parallel_loading_error_handling(tmp_path):
    """Test handling of corrupted images."""
    ct_dir = tmp_path / "test_data"
    ct_dir.mkdir()

    # Mix of valid and invalid images
    for i in range(5):
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * i * 50)
        img.save(ct_dir / f"good_{i:04d}.tif")

    # Corrupted
    (ct_dir / "bad_0005.tif").write_text("corrupted")

    for i in range(6, 10):
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * i * 25)
        img.save(ct_dir / f"good_{i:04d}.tif")

    file_names = [f"good_{i:04d}.tif" if i != 5 else "bad_0005.tif" for i in range(10)]

    # Should handle gracefully
    results, stats = load_images_parallel(ct_dir, file_names, max_workers=4)

    # Should load 9 out of 10
    assert stats['images_loaded'] == 9
    assert stats['images_failed'] == 1
    assert len(stats['errors']) == 1
```

---

## Implementation Checklist

### Phase 1: Infrastructure (2-3 days)
- [ ] Create `utils/parallel_loader.py`
- [ ] Implement `load_images_parallel()` with ThreadPoolExecutor
- [ ] Implement `determine_optimal_workers()`
- [ ] Add retry logic and error handling
- [ ] Write comprehensive unit tests
- [ ] Write performance benchmarks

### Phase 2: Integration (1-2 days)
- [ ] Add configuration constants
- [ ] Integrate into `thumbnail_generator.py`
- [ ] Add feature flag for enable/disable
- [ ] Update progress reporting
- [ ] Test with real CT datasets

### Phase 3: Validation (1-2 days)
- [ ] Run performance benchmarks
- [ ] Measure memory usage
- [ ] Verify no regressions
- [ ] Test on different platforms (Windows/Linux)
- [ ] Test on different storage types (SSD/HDD/Network)

### Phase 4: Documentation (1 day)
- [ ] Document configuration options
- [ ] Add troubleshooting guide
- [ ] Update user guide
- [ ] Add performance notes to README

---

## Estimated Effort

- **Total Time**: 5-8 days
- **Performance Gain**: 2-4x faster image loading
- **Memory Impact**: +100-200MB
- **Risk**: Low (fallback to sequential available)

## Success Criteria

- [ ] 2x+ speedup on SSD storage
- [ ] 3x+ speedup on HDD storage
- [ ] No regressions in memory usage
- [ ] All existing tests pass
- [ ] New tests have 100% pass rate
- [ ] Works on Windows, Linux, macOS
