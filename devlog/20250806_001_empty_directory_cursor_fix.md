# Empty Directory Cursor State Fix

## Date: 2025-08-06

## Issue
When opening an empty directory or a directory without valid image files, the application's cursor remained in the wait cursor state instead of returning to the normal arrow cursor.

## Root Cause
In the `open_dir()` function (CTHarvester.py:2015-2076):
- The cursor was set to `WaitCursor` at line 2030
- The cursor was restored to `ArrowCursor` at line 2073
- However, when `sort_file_list_from_dir()` returned `None` for empty/invalid directories, the function would return early at line 2063 without restoring the cursor

## Solution Implemented
1. Added `QApplication.restoreOverrideCursor()` before the early return (line 2063) to ensure the cursor is always restored
2. Added `QMessageBox.warning()` to notify users when no valid image files are found
3. Added `QMessageBox` to the import statements

## Changes Made
- **CTHarvester.py:5**: Added `QMessageBox` to imports
- **CTHarvester.py:2063-2064**: Added cursor restoration and warning message for empty/invalid directories

## Code Changes
```python
# Before
if self.settings_hash is None:
    return

# After  
if self.settings_hash is None:
    QApplication.restoreOverrideCursor()
    QMessageBox.warning(self, self.tr("Warning"), self.tr("No valid image files found in the selected directory."))
    return
```

## Testing Notes
- Test opening an empty directory - cursor should return to normal and warning should appear
- Test opening a directory with non-image files - same behavior expected
- Test opening a valid directory with image files - should work as before

## Additional Fix: BMP 'P' Mode Support

### Issue
BMP files with mode 'P' (palette mode) were causing errors because img1/img2 were not properly converted to grayscale.

### Solution
Added proper handling for 'P' mode images by converting them to 'L' (grayscale) mode:

```python
# Lines 1863-1864 and 1870-1871
elif img1.mode == 'P':
    img1 = img1.convert('L')
    
elif img2.mode == 'P':
    img2 = img2.convert('L')
```

This ensures that palette-based BMP images are properly converted to grayscale before processing, preventing None values and subsequent errors.

## Status
✅ Completed
