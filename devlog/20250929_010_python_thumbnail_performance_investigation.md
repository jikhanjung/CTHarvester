# Python Thumbnail Generation Performance Investigation

Date: 2025-09-29
Author: Jikhan Jung

## Issue Summary
Python fallback thumbnail generation is taking 8-10 seconds per image pair, which is abnormally slow for 15MB TIFF files on an SSD. This investigation documents the findings and potential causes.

## Environment
- **Platform**: Windows (running via Cursor IDE)
- **Image Location**: D:\Lichas_tif (local SSD)
- **Image Size**: ~15MB per TIFF file
- **Python Version**: 3.11+
- **Current Version**: 0.2.3-alpha.1

## Performance Timeline

### Previous Fix (Commit b51ace9)
- **Date**: 2025-09-27
- **Fix**: Replaced nested for loops with NumPy vectorized operations for 16-bit image downscaling
- **Result**: 20-50x speed improvement reported
- **Status**: Confirmed properly applied in current code (lines 339-355, 383-399)

### Current Performance Issue
Despite the loop fix being properly applied, each thumbnail generation still takes 8-10 seconds:
```
2025-09-29 08:59:29,143 - ThumbnailWorker.run: Completed idx=194 (generated) in 10290.5ms
2025-09-29 08:59:29,171 - ThumbnailWorker.run: Completed idx=193 (generated) in 10465.6ms
```

## Root Cause Analysis

### 1. PIL/Pillow TIFF Loading Performance
**Primary Suspect**: PIL's Image.open() is notoriously slow with large TIFF files, especially:
- 16-bit TIFF images
- Compressed TIFF files
- Large resolution images

**Evidence in Code** (CTHarvester.py lines 276-278, 302-304):
```python
open_start = time.time()
img1 = Image.open(file1_path)  # This could take several seconds for 15MB TIFF
open_time = (time.time() - open_start) * 1000
```

**Each worker performs**:
- 2x Image.open() calls (for two consecutive images)
- Image processing (already optimized with NumPy)
- 1x Image.save() call

### 2. Multithreading Bottlenecks

**Configuration** (lines 612-614):
```python
if self.threadpool.maxThreadCount() < 4:
    self.threadpool.setMaxThreadCount(4)
```

**Problems with current multithreading approach**:

#### a. Python GIL (Global Interpreter Lock)
- Python threads don't truly run in parallel for CPU-bound tasks
- GIL forces sequential execution of Python bytecode
- Only I/O operations can truly parallelize

#### b. Disk I/O Contention
- 4 threads × 2 images each = 8 simultaneous file reads
- Even on SSD, concurrent reads of large files cause:
  - Cache thrashing
  - Queue saturation
  - Increased latency

#### c. Memory Pressure
- Each thread loads 2×15MB images into memory
- 4 threads = potentially 120MB+ in flight
- Memory allocation/deallocation overhead

### 3. Why It's Worse Than Single-Threaded

**Theoretical single-threaded performance**:
- Sequential disk reads (optimal for spinning disks, good for SSDs)
- No GIL contention
- Better CPU cache utilization
- No thread synchronization overhead

**Current multi-threaded reality**:
- Random disk access patterns
- GIL contention between threads
- Thread synchronization overhead
- PIL's potential thread-safety locks

## System State Consideration: Sleep/Resume Impact

### Windows Sleep Mode and Performance Degradation

**User Observation**: The same operation was much faster last week, but the system has been through sleep/resume cycles since then.

**Potential Windows Sleep/Resume Issues**:

1. **Memory Fragmentation**
   - After resume, memory may be fragmented
   - Python/PIL may struggle to allocate contiguous memory blocks
   - Garbage collection may be working harder

2. **Storage Driver State**
   - SSD controllers may not properly resume to full performance mode
   - Power saving states (ASPM, DevSleep) may not fully disengage
   - TRIM operations may be queued but not executed

3. **File System Cache**
   - Windows file cache may be invalidated or corrupted
   - Superfetch/Prefetch data may be stale
   - ReadyBoost cache may need rebuilding

4. **Power Management**
   - CPU may be stuck in lower power states
   - Windows Power Plan may not properly restore to High Performance
   - Thermal throttling due to poor resume from sleep

5. **Background Processes**
   - Windows Search Indexer rebuilding
   - Antivirus doing full scans after resume
   - Windows Updates downloading/installing
   - OneDrive or other sync services catching up

6. **Python/Application Specific**
   - Python interpreter memory leaks accumulating
   - PIL/Pillow internal caches corrupted
   - Thread pool in inconsistent state
   - File handles not properly released

### Diagnostic Steps
1. Check Task Manager for CPU/Disk/Memory usage
2. Run `powercfg /energy` to check power state issues
3. Check Event Viewer for storage-related warnings
4. Monitor disk queue length during operation
5. Check if other applications are also slow

### Recommended Immediate Action
**Reboot the system** - This will:
- Clear memory fragmentation
- Reset all driver states
- Clear file system caches
- Reset power management
- Terminate accumulated background processes
- Give a clean baseline for performance testing

## Potential Solutions

### 1. Reduce Thread Count
```python
self.threadpool.setMaxThreadCount(1)  # or 2 at most
```
- Reduces I/O contention
- Better for sequential processing

### 2. Use tifffile Library
```python
import tifffile
img_array = tifffile.imread(file_path)  # Much faster for TIFF files
```
- Optimized specifically for TIFF files
- Better handling of 16-bit images
- Can be 5-10x faster than PIL for large TIFFs

### 3. Switch to Multiprocessing
```python
from multiprocessing import Pool
# Use processes instead of threads
```
- True parallelism (no GIL)
- Better for CPU-bound operations
- Each process has its own memory space

### 4. Batch Processing
Instead of processing one image pair at a time:
- Load multiple images at once
- Process in batches
- Reduce file open/close overhead

### 5. Memory Mapping
```python
import numpy as np
img_array = np.memmap(file_path, dtype='uint16', mode='r', shape=(height, width))
```
- Avoid loading entire file into memory
- Let OS handle caching

### 6. Pre-load Images
- Load next images while processing current ones
- Use a producer-consumer pattern
- Overlap I/O with computation

## Recommended Action Plan

1. **Quick Test**: Reduce thread pool to 1 thread and measure performance
2. **Library Switch**: Replace PIL with tifffile for TIFF loading
3. **Architecture Change**: Consider multiprocessing for true parallelism
4. **Long-term**: Ensure Rust module is properly compiled and available

## Performance Metrics to Track

- Time per Image.open() call
- Time per image processing (NumPy operations)
- Time per Image.save() call
- Total time per thumbnail
- Memory usage
- Disk I/O patterns

## Conclusion

The slow performance appears to be caused by a combination of:
1. PIL's inefficient TIFF loading
2. Multithreading causing I/O contention rather than helping
3. Python's GIL preventing true parallelism

The irony is that the multithreading implementation, meant to improve performance, may actually be making it worse due to I/O contention and GIL limitations.

## Next Steps

1. Test with reduced thread count (1-2 threads)
2. Profile Image.open() specifically to confirm it's the bottleneck
3. Consider switching to tifffile library
4. Ensure Rust module is working as primary solution