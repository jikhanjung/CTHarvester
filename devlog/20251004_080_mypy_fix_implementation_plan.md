# Devlog 080: Mypy Error Fix Implementation Plan

**Date:** 2025-10-04
**Status:** 📋 Action Plan Ready
**Previous:** [devlog 079 - Codebase Analysis](./20251004_079_codebase_analysis_recommendations.md)

---

## 📊 Mypy Error Summary

### Current State
```bash
$ mypy ui/main_window.py 2>&1 | wc -l
Total errors when checking main_window.py: 80+ errors
(including transitive dependencies)

$ mypy ui/main_window.py 2>&1 | grep "ui/main_window.py" | wc -l
Direct errors in main_window.py: 21 errors
```

### Error Distribution
1. **Custom QApplication Attributes** - 11 errors (52%)
   - `self.app.language`, `self.app.default_directory`, etc.
   - Root cause: Dynamic attribute assignment in CTHarvester.py:50-53

2. **ProgressDialog Optional Type** - 6 errors (29%)
   - Lines: 684, 733, 897, 914, 932, 952, 986
   - Root cause: `self.progress_dialog: ProgressDialog` should be `Optional[ProgressDialog]`

3. **QCoreApplication None Check** - 2 errors (10%)
   - Lines: 170, 172
   - Root cause: `QApplication.instance()` can return `None`

4. **Other Type Issues** - 2 errors (10%)
   - Line 332: VolumeProcessor argument type
   - Line 799: Optional ndarray `.shape` access
   - Lines 393, 500: Uninitialized attribute type inference
   - Line 1076: Dict assignment from optional

---

## 🎯 Implementation Plan

### Phase 1: Custom QApplication Subclass (45분)

#### Goal
Eliminate 11 mypy errors by creating a proper QApplication subclass with typed attributes.

#### Files to Create
- `ui/ctharvester_app.py` (new file, ~40 lines)

#### Files to Modify
- `CTHarvester.py` (main entry point)
- `ui/main_window.py` (type hints)
- `ui/handlers/settings_handler.py` (type hints)

#### Implementation

**Step 1: Create CTHarvesterApp class**
```python
# ui/ctharvester_app.py
"""Custom QApplication subclass with typed attributes for CTHarvester."""

from PyQt5.QtWidgets import QApplication


class CTHarvesterApp(QApplication):
    """Custom QApplication with CTHarvester-specific attributes.

    This subclass adds typed attributes for settings and preferences,
    eliminating mypy errors from dynamic attribute assignment.

    Attributes:
        language: UI language code ('en', 'ko', etc.)
        default_directory: Default directory for file operations
        remember_geometry: Whether to save/restore window geometry
        remember_directory: Whether to remember last used directory
        use_rust_thumbnail: Whether to use Rust module for thumbnails
    """

    def __init__(self, *args, **kwargs):
        """Initialize CTHarvester application with default settings."""
        super().__init__(*args, **kwargs)

        # Language settings
        self.language: str = "en"

        # Directory settings
        self.default_directory: str = "."
        self.remember_directory: bool = True

        # Window settings
        self.remember_geometry: bool = True

        # Processing settings
        self.use_rust_thumbnail: bool = True
```

**Step 2: Update CTHarvester.py**
```python
# Before
from PyQt5.QtWidgets import QApplication
...
def main():
    app = QApplication(sys.argv)
    app.remember_geometry = True  # Dynamic attribute - mypy error
    app.remember_directory = True
    app.language = "en"
    app.use_rust_thumbnail = True

# After
from ui.ctharvester_app import CTHarvesterApp
...
def main():
    app = CTHarvesterApp(sys.argv)
    # Attributes are now properly typed - no need to set defaults
    # (They're initialized in __init__)
```

**Step 3: Update type hints in main_window.py**
```python
# Before (line ~120)
self.m_app = QApplication.instance()  # Returns QCoreApplication | None

# After
from ui.ctharvester_app import CTHarvesterApp
...
self.m_app = CTHarvesterApp.instance()  # Returns CTHarvesterApp | None
# Or use type annotation:
self.m_app: Optional[CTHarvesterApp] = QApplication.instance()  # type: ignore[assignment]
```

**Step 4: Update settings_handler.py**
```python
# Before (line 39)
self.app = QApplication.instance()  # QCoreApplication | None

# After
from ui.ctharvester_app import CTHarvesterApp
...
self.app = CTHarvesterApp.instance()
# Or with type hint:
self.app: CTHarvesterApp = QApplication.instance()  # type: ignore[assignment]
```

#### Expected Outcome
✅ Eliminates 11 mypy errors related to custom attributes
✅ Improves IDE autocomplete for app attributes
✅ Makes settings attributes explicit and discoverable

---

### Phase 2: ProgressDialog Optional Type (15분)

#### Goal
Fix 6 mypy errors by changing `ProgressDialog` type to `Optional[ProgressDialog]`.

#### Files to Modify
- `ui/main_window.py`

#### Implementation

**Step 1: Update type annotation in __init__**
```python
# Before (line ~150)
self.progress_dialog: ProgressDialog

# After
from typing import Optional
...
self.progress_dialog: Optional[ProgressDialog] = None
```

**Step 2: Add None check before dialog close (if needed)**
Most usage already has checks like `if self.progress_dialog:`, so this should be minimal.

#### Expected Outcome
✅ Eliminates 6 assignment errors (lines 684, 733, 897, 914, 932, 952, 986)
✅ Makes optional nature of progress dialog explicit

---

### Phase 3: QCoreApplication None Checks (5분)

#### Goal
Fix 2 mypy errors by adding None guards.

#### Files to Modify
- `ui/main_window.py`

#### Implementation

```python
# Before (lines 170-172)
lang_code = self.m_app.language
...
self.m_app.installTranslator(translator)

# After
if self.m_app:
    lang_code = self.m_app.language
    ...
    self.m_app.installTranslator(translator)
else:
    logger.warning("QApplication instance not available")
    lang_code = "en"
```

#### Expected Outcome
✅ Eliminates 2 union-attr errors at lines 170, 172
✅ Handles edge case of missing QApplication instance

---

### Phase 4: Remaining Type Issues (15분)

#### Goal
Fix remaining 2 type errors with targeted annotations.

#### Files to Modify
- `ui/main_window.py`

#### Implementation

**Issue 1: VolumeProcessor argument (line 332)**
```python
# Before
volume = self.volume_processor.get_cropped_volume(
    minimum_volume=self.minimum_volume  # Type: Any | None
)

# After
if self.minimum_volume is not None:
    volume = self.volume_processor.get_cropped_volume(
        minimum_volume=self.minimum_volume
    )
```

**Issue 2: Optional ndarray .shape access (line 799)**
```python
# Before
if self.minimum_volume.shape[0] > 0:  # Item "None" has no attribute "shape"

# After
if self.minimum_volume is not None and self.minimum_volume.shape[0] > 0:
```

**Issue 3: Uninitialized attribute (lines 393, 500)**
```python
# Add explicit initialization in __init__ method
self.initialized: bool = False
```

**Issue 4: Dict assignment (line 1076)**
```python
# Before
self.settings_hash: dict[Any, Any] = self.file_handler.analyze_directory(...)

# After
settings_result = self.file_handler.analyze_directory(...)
if settings_result is not None:
    self.settings_hash = settings_result
```

#### Expected Outcome
✅ Eliminates all remaining errors in main_window.py
✅ Adds proper None guards for safety

---

## 📋 Execution Checklist

### Phase 1: Custom QApplication (45min)
- [ ] Create `ui/ctharvester_app.py`
- [ ] Update `CTHarvester.py` imports and main()
- [ ] Update `ui/main_window.py` type hints
- [ ] Update `ui/handlers/settings_handler.py` type hints
- [ ] Run mypy: `mypy ui/main_window.py` (expect ~10 fewer errors)
- [ ] Run tests: `pytest tests/test_main_window.py -v`

### Phase 2: ProgressDialog Optional (15min)
- [ ] Update type annotation in `ui/main_window.py`
- [ ] Run mypy (expect ~6 fewer errors)
- [ ] Run tests

### Phase 3: None Checks (5min)
- [ ] Add None guard at lines 170-172
- [ ] Run mypy (expect ~2 fewer errors)
- [ ] Run tests

### Phase 4: Remaining Fixes (15min)
- [ ] Fix VolumeProcessor argument (line 332)
- [ ] Fix ndarray .shape access (line 799)
- [ ] Initialize `self.initialized` attribute
- [ ] Fix dict assignment (line 1076)
- [ ] Run mypy: `mypy ui/main_window.py` (expect 0 errors)
- [ ] Run full test suite: `pytest tests/ -v`

### Final Validation
- [ ] Run mypy on entire codebase: `mypy .`
- [ ] Run pre-commit hooks: `pre-commit run --all-files`
- [ ] Verify 911 tests still passing
- [ ] Create commit

---

## 📊 Expected Impact

### Before
```
$ mypy ui/main_window.py 2>&1 | grep "ui/main_window.py" | wc -l
21 errors
```

### After
```
$ mypy ui/main_window.py 2>&1 | grep "ui/main_window.py" | wc -l
0 errors
```

### Additional Benefits
- ✅ Proper typing for CTHarvester app attributes
- ✅ Better IDE autocomplete and type hints
- ✅ Explicit optional types for clarity
- ✅ None guards prevent potential runtime errors

---

## 🔗 Related Issues

### Other Files with Similar Patterns

From my analysis, these files also have mypy errors:

1. **ui/widgets/vertical_stack_slider.py** - 14 Qt enum errors
   - Pattern: `Qt.StrongFocus`, `Qt.NoPen`, etc.
   - Fix: `from PyQt5.QtCore import Qt` → Use `Qt.FocusPolicy.StrongFocus` or add `# type: ignore[attr-defined]`

2. **ui/dialogs/info_dialog.py** - 3 errors
   - Line 23: Method assignment
   - Lines 30, 35: Qt.AlignCenter enum

3. **ui/handlers/settings_handler.py** - Will be fixed by Phase 1

These can be addressed in a follow-up task after main_window.py is clean.

---

## 🎯 Next Steps After This Plan

1. **Implement this plan** (80 minutes total)
2. **Fix remaining UI files** (30-45 minutes)
   - vertical_stack_slider.py
   - info_dialog.py
3. **Run full codebase mypy check** (5 minutes)
4. **Document any remaining strategic `# type: ignore` usage** (15 minutes)

---

**Plan Created:** 2025-10-04
**Estimated Total Time:** 80 minutes (1.3 hours)
**Expected Result:** 0 mypy errors in ui/main_window.py
**ROI:** High - Eliminates 21 type errors, improves code quality

---

*This implementation plan provides step-by-step instructions for the high-priority type safety improvements identified in devlog 079.*
