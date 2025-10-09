# Error Recovery and Graceful Degradation

**Created:** Phase 3 (Performance & Robustness)
**Status:** v0.2.3-beta.2

---

## Overview

CTHarvester implements comprehensive error recovery mechanisms to ensure graceful degradation under error conditions. This document describes the error handling architecture, recovery strategies, and best practices.

---

## Error Handling Architecture

### Error Catalog System

**Location:** `ui/errors.py`

The application uses a centralized error catalog with:
- **ErrorCode enum**: Standardized error identifiers
- **ErrorSeverity levels**: CRITICAL, ERROR, WARNING, INFO
- **ERROR_MESSAGES dict**: Complete error message catalog

**Example:**
```python
from ui.errors import show_error, ErrorCode

# Display error to user
show_error(parent_widget, ErrorCode.EMPTY_DIRECTORY)
```

### Exception Hierarchy

**Location:** `core/file_handler.py`

```
FileHandlerError (base)
├── NoImagesFoundError
├── InvalidImageFormatError
└── CorruptedImageError
```

**Usage:**
```python
from core.file_handler import NoImagesFoundError, FileHandler

try:
    file_handler = FileHandler()
    result = file_handler.open_directory(path)
except NoImagesFoundError as e:
    show_error(self, ErrorCode.EMPTY_DIRECTORY)
except FileNotFoundError as e:
    show_error(self, ErrorCode.DIRECTORY_NOT_FOUND)
```

---

## Error Recovery Mechanisms

### 1. File System Errors

#### Permission Errors
**Scenario:** User lacks permissions to access directory/file

**Handling:**
- **Detection:** Catch `PermissionError` in file operations
- **Recovery:** Display clear error message, suggest solutions
- **Logging:** Log full error with traceback

**Example:**
```python
try:
    files = os.listdir(directory)
except PermissionError as e:
    logger.error(f"Permission denied: {directory}", exc_info=True)
    show_error(self, ErrorCode.PERMISSION_DENIED)
    return None
```

#### Disk Space Errors
**Scenario:** Insufficient disk space during file operations

**Handling:**
- **Detection:** Catch `OSError` with errno 28 (ENOSPC)
- **Recovery:** Free up space or choose different location
- **Prevention:** Check available space before large operations

**Example:**
```python
import shutil

try:
    free_space = shutil.disk_usage(output_dir).free
    required_space = estimate_required_space(dataset)

    if free_space < required_space * 1.2:  # 20% safety margin
        show_error(self, ErrorCode.DISK_SPACE_ERROR)
        return
except OSError as e:
    if e.errno == 28:  # ENOSPC
        show_error(self, ErrorCode.DISK_SPACE_ERROR)
```

#### Network Drive Disconnection
**Scenario:** Network drive becomes unavailable during operation

**Handling:**
- **Detection:** Catch `OSError` with errno 53 (network error)
- **Recovery:** Pause operation, prompt user to reconnect
- **Retry:** Allow user to retry after reconnection

**Test Coverage:** `tests/test_error_recovery.py::TestNetworkDriveErrors`

---

### 2. Image Processing Errors

#### Corrupted Image Files
**Scenario:** Image file is corrupted or partially written

**Handling:**
- **Detection:** `CorruptedImageError` from file handler
- **Recovery:** Skip corrupted file, continue with valid images
- **Reporting:** Log which files were skipped

**Example:**
```python
from core.file_handler import CorruptedImageError

try:
    result = file_handler.sort_file_list_from_dir(directory)
except CorruptedImageError as e:
    logger.error(f"Corrupted image detected: {e}")
    show_error(self, ErrorCode.CORRUPTED_FILE)
```

#### Invalid Image Format
**Scenario:** Unsupported or invalid image format

**Handling:**
- **Detection:** `InvalidImageFormatError`
- **Recovery:** Display supported formats to user
- **Prevention:** Validate file extensions before processing

**Test Coverage:** `tests/test_error_recovery.py::TestCorruptImageHandling`

---

### 3. Memory Management

#### Memory Allocation Failures
**Scenario:** Insufficient memory for large dataset

**Handling:**
- **Detection:** Catch `MemoryError`
- **Recovery:** Process in smaller batches
- **Prevention:** Use batch processing for large datasets

**Example:**
```python
try:
    loaded_images = [Image.open(f) for f in files]
except MemoryError:
    logger.error("Memory allocation failed")
    show_error(self, ErrorCode.MEMORY_ALLOCATION_FAILED)
    # Fall back to batch processing
    return process_in_batches(files)
```

#### Garbage Collection
**Best Practice:** Explicitly trigger garbage collection after batch processing

```python
import gc

# Process batch
for batch in batches:
    process_batch(batch)
    gc.collect()  # Free memory between batches
```

**Test Coverage:** `tests/test_error_recovery.py::TestMemoryManagement`

---

### 4. Graceful Degradation

#### Rust Module Unavailable
**Scenario:** Optional Rust thumbnail module not available

**Handling:**
- **Detection:** Check `rust_available` attribute
- **Fallback:** Use Python PIL implementation
- **Performance:** Slower but functional

**Example:**
```python
from core.thumbnail_generator import ThumbnailGenerator

generator = ThumbnailGenerator()
if generator.rust_available:
    logger.info("Using Rust thumbnail generation (fast)")
else:
    logger.info("Using Python thumbnail generation (slower)")
```

**Test Coverage:** `tests/test_error_recovery.py::TestGracefulDegradation`

#### Empty Directories
**Scenario:** User selects directory with no valid images

**Handling:**
- **Detection:** `NoImagesFoundError`
- **Message:** Clear explanation of requirements
- **Guidance:** Suggest checking file formats and naming

---

## Testing Strategy

### Test Coverage

**Location:** `tests/test_error_recovery.py`

**Test Classes:**
- `TestFileSystemErrors`: Permission, OS, file not found errors
- `TestThumbnailGenerationErrors`: Memory, OS errors during processing
- `TestThumbnailLoadingErrors`: Loading from nonexistent/restricted locations
- `TestCorruptImageHandling`: Corrupt and partially corrupt sequences
- `TestNetworkDriveErrors`: Network disconnection and intermittent access
- `TestGracefulDegradation`: Fallback mechanisms

**Total Tests:** 18 error recovery tests (all passing)

### Running Error Recovery Tests

```bash
# Run all error recovery tests
python -m pytest tests/test_error_recovery.py -v

# Run specific test class
python -m pytest tests/test_error_recovery.py::TestFileSystemErrors -v

# Run with detailed output
python -m pytest tests/test_error_recovery.py -v --tb=short
```

---

## Best Practices

### 1. Always Use Specific Exceptions

❌ **Bad:**
```python
try:
    result = operation()
except Exception as e:
    print(f"Error: {e}")
```

✅ **Good:**
```python
try:
    result = operation()
except PermissionError as e:
    logger.error(f"Permission denied: {e}", exc_info=True)
    show_error(self, ErrorCode.PERMISSION_DENIED)
except FileNotFoundError as e:
    logger.error(f"File not found: {e}", exc_info=True)
    show_error(self, ErrorCode.FILE_NOT_FOUND)
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    show_error(self, ErrorCode.UNRECOVERABLE_ERROR)
```

### 2. Log Before Displaying

Always log detailed error before showing user-friendly message:

```python
try:
    risky_operation()
except OSError as e:
    # Log technical details
    logger.error(f"OS error in risky_operation: {e}", exc_info=True)

    # Show user-friendly message
    show_error(self, ErrorCode.FILE_WRITE_ERROR)
```

### 3. Provide Context in Errors

```python
# Include relevant context
logger.error(f"Failed to load image: {image_path}", exc_info=True)

# Not just:
logger.error("Failed to load image")
```

### 4. Clean Up Resources

Always clean up in finally blocks:

```python
file_handle = None
try:
    file_handle = open(path, 'rb')
    process_file(file_handle)
except Exception as e:
    logger.error(f"Error processing file: {e}")
    raise
finally:
    if file_handle:
        file_handle.close()
```

### 5. Validate Early

Validate inputs before expensive operations:

```python
def process_directory(path):
    # Validate first
    if not Path(path).exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if not Path(path).is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    # Then process
    return expensive_operation(path)
```

---

## Error Recovery Checklist

When implementing new features, ensure:

- [ ] All file operations wrapped in try/except
- [ ] Specific exception types caught (not bare `except:`)
- [ ] Errors logged with full traceback (`exc_info=True`)
- [ ] User-friendly error messages displayed
- [ ] Resources cleaned up in `finally` blocks
- [ ] Tests written for error scenarios
- [ ] Error codes added to `ErrorCode` enum if needed
- [ ] Error messages added to `ERROR_MESSAGES` catalog
- [ ] Graceful degradation implemented where possible
- [ ] Memory cleanup with `gc.collect()` after batches

---

## Common Error Scenarios

### Scenario 1: User Opens Invalid Directory

**Flow:**
1. User selects directory
2. `FileHandler.open_directory()` validates path
3. If invalid: raises `FileNotFoundError` or `NotADirectoryError`
4. UI catches exception, displays appropriate error
5. User prompted to select different directory

### Scenario 2: Corrupted Image in Sequence

**Flow:**
1. Processing image sequence
2. `get_image_dimensions()` fails on corrupted file
3. Raises `CorruptedImageError`
4. Option 1: Skip file, continue with others
5. Option 2: Abort operation if first file corrupted
6. User notified of skipped files

### Scenario 3: Out of Memory During Processing

**Flow:**
1. Loading large dataset
2. `MemoryError` raised
3. Clear loaded images: `del images; gc.collect()`
4. Switch to batch processing mode
5. Process in smaller chunks
6. User sees progress but slower performance

### Scenario 4: Network Drive Disconnects

**Flow:**
1. Processing files from network drive
2. `OSError` (errno 53) raised mid-operation
3. Save current state
4. Display reconnection dialog
5. User reconnects drive
6. Resume from last saved state

---

## Performance Impact

### Error Handling Overhead

**Minimal Impact:**
- Try/except blocks: negligible overhead when no exception
- Exception creation: ~1-10μs per exception
- Logging: ~100-500μs per log entry

**Recommendation:** Don't avoid error handling for performance reasons

### Memory Cleanup

**Impact:**
- `gc.collect()`: ~10-100ms depending on object count
- Worth the cost for large datasets
- Use after batch processing, not every iteration

**Example:**
```python
# Good: GC after batch
for batch in large_dataset.batches(size=50):
    process(batch)
    gc.collect()

# Bad: GC every iteration (too frequent)
for item in large_dataset:
    process(item)
    gc.collect()  # Too slow!
```

---

## Debugging Error Recovery

### Enable Detailed Logging

```python
import logging

# Set to DEBUG for detailed error information
logging.basicConfig(level=logging.DEBUG)
```

### Test Error Scenarios

Use mocking to simulate errors:

```python
from unittest.mock import patch

# Simulate permission error
with patch('os.listdir', side_effect=PermissionError("Denied")):
    with pytest.raises(PermissionError):
        file_handler.open_directory(path)
```

### Check Error Catalog

Verify all error codes have messages:

```bash
python -m pytest tests/test_error_recovery.py::TestErrorMessageCatalog -v
```

---

## References

### Related Files

- `ui/errors.py` - Error catalog and display functions
- `core/file_handler.py` - File operation exceptions
- `tests/test_error_recovery.py` - Error recovery tests
- `docs/user_guide/troubleshooting.rst` - User troubleshooting guide

### Related Documentation

- [User Troubleshooting Guide](../user_guide/troubleshooting.rst)
- [Developer Guide](../developer_guide/index.rst)
- [Testing Guide](../developer_guide/testing.rst)

---

## Summary

CTHarvester implements robust error recovery through:

1. **Centralized Error Catalog**: All error messages in one place
2. **Exception Hierarchy**: Specific exceptions for different error types
3. **Graceful Degradation**: Fallbacks when resources unavailable
4. **Comprehensive Testing**: 18 error recovery tests
5. **Clear Logging**: Detailed error logging for debugging
6. **User-Friendly Messages**: Non-technical error descriptions

**Result:** Resilient application that handles errors gracefully and guides users to solutions.

---

**Last Updated:** Phase 3 (Performance & Robustness)
**Test Coverage:** 18 tests, all passing
**Status:** Production ready
