# Comprehensive Project Improvement Plan

**Date**: 2025-10-01
**Session**: #053
**Type**: Analysis & Planning
**Status**: 📋 Planning

## Overview

This document outlines a comprehensive improvement plan based on thorough project analysis and recent bug findings. The plan is organized by priority and includes both immediate fixes and long-term enhancements.

## Executive Summary

**Project Health**: Good ✅
- Strong foundation with 486 tests (~95% core coverage)
- Well-architected modular structure
- Active development with 52 detailed devlog entries

**Areas Needing Attention**:
- Critical bugs in thumbnail generation API
- Repository cleanup needed
- Documentation inconsistencies
- Test organization improvements

---

## 🔴 CRITICAL ISSUES (Immediate Action Required)

### Issue 1: Broken Python Thumbnail Generation API

**Priority**: 🔴 CRITICAL
**Estimated Time**: 2 hours
**Severity**: Breaking change - Public API non-functional

#### Problem Description

After recent refactoring to remove callback-based approach, the public `generate()` method signature is incompatible with the new internal implementation:

**Location**: `core/thumbnail_generator.py:169-191`

```python
# Current (broken):
def generate(self, directory, use_rust_preference=True, progress_callback=None, cancel_check=None):
    if use_rust:
        return self.generate_rust(directory, progress_callback, cancel_check)
    else:
        return self.generate_python(directory, progress_callback, cancel_check)  # ❌ Wrong signature!

# generate_python now expects:
def generate_python(self, directory, settings, threadpool, progress_dialog=None):
```

**Impact**:
- Any caller using `generate(..., use_rust_preference=False)` triggers `TypeError`
- Breaks backward compatibility
- Rust path works, Python fallback path broken

#### Solution Plan

**Option A: Update Public API (Breaking Change)**
```python
def generate(self, directory, settings, threadpool, use_rust_preference=True, progress_dialog=None):
    """Generate thumbnails using best available method

    Args:
        directory (str): Directory containing CT images
        settings (dict): Settings hash with image parameters
        threadpool (QThreadPool): Qt thread pool
        use_rust_preference (bool): Prefer Rust if available
        progress_dialog (ProgressDialog, optional): Progress UI
    """
    if self.rust_available and use_rust_preference:
        return self.generate_rust(directory, progress_dialog)
    else:
        return self.generate_python(directory, settings, threadpool, progress_dialog)
```

**Option B: Maintain Backward Compatibility (Adapter)**
```python
def generate(self, directory, use_rust_preference=True, progress_callback=None, cancel_check=None):
    """Legacy wrapper for backward compatibility"""
    # Extract settings from context or require caller to update
    warnings.warn("Old signature deprecated, use generate_v2()", DeprecationWarning)
    # Provide adapter logic
```

**Recommendation**: Option A (clean break, document migration)

**Files to Update**:
1. `core/thumbnail_generator.py:169-191` - Update signature
2. `ui/main_window.py:817-891` - Already uses new signature ✅
3. `tests/test_thumbnail_generator.py` - Update test cases
4. `docs/api/core.rst` - Update API documentation

**Migration Path for External Callers**:
```python
# Before:
generator.generate(directory, use_rust_preference=False,
                   progress_callback=cb, cancel_check=cc)

# After:
generator.generate_python(directory, settings, threadpool, progress_dialog)
# OR
generator.generate(directory, settings, threadpool,
                   use_rust_preference=False, progress_dialog=pd)
```

---

### Issue 2: Progress Sampling Not Working (ETA Stuck at "Estimating...")

**Priority**: 🔴 HIGH
**Estimated Time**: 1 hour
**Severity**: User experience degradation - No accurate ETA

#### Problem Description

**Location**: `core/thumbnail_generator.py:386-397`

The computed `sample_size` is never passed to `ThumbnailManager`, leaving it at default value 0, which prevents progress sampling from starting.

**Current Code**:
```python
# Line 388-390: Calculate sample sizes
base_sample = max(20, min(30, int(total_work * 0.02)))
sample_size = base_sample
total_sample = base_sample * 3

# Line 492-497: Create ThumbnailManager WITHOUT sample_size
thumbnail_manager = ThumbnailManager(
    None,  # main_window
    progress_dialog,
    threadpool,
    shared_progress_manager
)
# ❌ sample_size never set!
```

**Impact**:
- `ThumbnailManager.sample_size = 0` (default)
- Sampling never starts
- ETA remains "Estimating..." forever
- Users see no time prediction

#### Solution Plan

**Option A: Pass via Constructor**
```python
class ThumbnailManager:
    def __init__(self, parent, progress_dialog, threadpool,
                 shared_progress_manager, sample_size=20):
        self.sample_size = sample_size
```

**Option B: Set After Construction (Quick Fix)**
```python
thumbnail_manager = ThumbnailManager(...)
thumbnail_manager.sample_size = sample_size
```

**Option C: Get from Settings (Best Practice)**
```python
# In ThumbnailManager.__init__:
settings = SettingsManager()
self.sample_size = settings.get('thumbnails.sample_size', 20)
```

**Recommendation**: Combination of B (immediate) and C (proper fix)

**Implementation**:
1. Quick fix in `generate_python()`:
   ```python
   thumbnail_manager = ThumbnailManager(...)
   thumbnail_manager.sample_size = sample_size  # Line 498
   ```

2. Proper fix in `ThumbnailManager.__init__`:
   ```python
   # Read from settings if available
   if hasattr(parent, 'settings'):
       self.sample_size = parent.settings.get('thumbnails.sample_size', 20)
   else:
       self.sample_size = 20  # Default
   ```

**Files to Update**:
1. `core/thumbnail_generator.py:497` - Add `thumbnail_manager.sample_size = sample_size`
2. `core/thumbnail_manager.py:__init__` - Read from settings
3. `tests/test_thumbnail_generator.py` - Verify sampling works
4. `tests/test_thumbnail_manager.py` - Test sample_size handling

**Verification**:
- Generate thumbnails with Python fallback
- Verify ETA shows actual time after sampling completes
- Check logs for "Sampling complete: X.XX weighted units/s"

---

### Issue 3: Failed Thumbnail Generation Not Handled Properly

**Priority**: 🔴 HIGH
**Estimated Time**: 30 minutes
**Severity**: UI corruption on failure

#### Problem Description

**Location**: `ui/main_window.py:900+`

When Python thumbnail generation returns `success=False` (but `cancelled=False`), the code continues to load from disk and initialize UI with empty/invalid data.

**Current Code**:
```python
result = self.thumbnail_generator.generate_python(...)

if result:
    if result.get('cancelled'):
        # Handle cancellation
        pass
    else:
        # ❌ Continues even if success=False!
        self.minimum_volume = result.get('minimum_volume')
        self.level_info = result.get('level_info')
        self.load_thumbnail_data_from_disk()
        self.initializeComboSize()  # Empty combo if data is invalid
```

**Impact**:
- UI shows empty combo boxes
- 3D view may crash or show nothing
- No error message to user
- Confusing user experience

#### Solution Plan

**Implementation**:
```python
result = self.thumbnail_generator.generate_python(...)

if not result:
    # Null result
    self.show_error("Thumbnail generation failed", "Unknown error occurred")
    QApplication.restoreOverrideCursor()
    return

if result.get('cancelled'):
    # User cancelled
    self.show_info("Thumbnail generation cancelled", "Operation was cancelled by user")
    QApplication.restoreOverrideCursor()
    return

if not result.get('success'):
    # Generation failed
    error_msg = result.get('error', 'Thumbnail generation failed')
    self.show_error("Thumbnail generation failed", error_msg)
    QApplication.restoreOverrideCursor()
    return

# Only continue if successful
self.minimum_volume = result.get('minimum_volume')
self.level_info = result.get('level_info')
# ... rest of success handling
```

**Files to Update**:
1. `ui/main_window.py:900-950` - Add failure handling
2. `core/thumbnail_generator.py:621-641` - Ensure error info in result dict
3. `tests/test_integration_thumbnail.py` - Test failure scenarios

**Additional Improvements**:
- Add 'error' field to result dict in `generate_python()`
- Log detailed error information
- Show user-friendly error dialog with suggestions

---

## 🟡 HIGH PRIORITY ISSUES (This Week)

### Issue 4: Repository Cleanup

**Priority**: 🟡 HIGH
**Estimated Time**: 1 hour
**Impact**: Repository hygiene, clarity

#### Files to Remove/Move

**Test Data Files in Root** (should be in test_data/ or ignored):
```bash
# Remove or move to test_data/:
Estaingia_rough_1.tps
Estaingia_rough_2.tps
Phacops_flat_20230619.tps
Tf-20230619.x1y1
M2Preferences_1.png
M2Preferences_2.png
CTHarvester_48.png
CTHarvester_48_2.png
CTHarvester_64.png
CTHarvester_64_2.png
expand.png
shrink.png
move.png
info.png
```

**Orphaned Files**:
```bash
# Remove:
CTScape.spec  # References non-existent CTScape.py
src/lib_final_backup_20250927.rs  # Backup file
check_user_settings.py  # Temporary debug script
```

**Action Plan**:
1. Create `.gitignore` entries for test data patterns
2. `git rm` tracked test files
3. Move useful test data to `test_data/` directory
4. Remove backup and temporary files
5. Update documentation if needed

#### Command Sequence:
```bash
# Create test_data directory
mkdir -p test_data/samples

# Move test data
mv *.tps test_data/samples/
mv *.x1y1 test_data/samples/
mv *Preferences*.png test_data/samples/

# Remove orphaned files
git rm CTScape.spec
git rm src/lib_final_backup_20250927.rs
git rm check_user_settings.py

# Update .gitignore
echo "test_data/" >> .gitignore
echo "check_*.py" >> .gitignore

# Commit
git commit -m "chore: Clean up repository - move test data and remove orphaned files"
```

---

### Issue 5: Documentation Inconsistencies

**Priority**: 🟡 HIGH
**Estimated Time**: 45 minutes
**Impact**: User confusion, incorrect setup

#### 5.1. Python Version Requirement Conflicts

**Current State**:
- `README.md`: "Python 3.12+" (badge and installation instructions)
- `pyproject.toml:13`: `requires-python = ">=3.8"`
- `pytest.ini:2`: `minversion = 3.12`
- CI workflows use Python 3.11

**Decision**: Use Python 3.11+ as minimum
- Modern enough for type hints and async features
- Matches CI configuration
- Reasonable requirement for new users

**Updates Required**:
1. `pyproject.toml:13`: `requires-python = ">=3.11"`
2. `README.md:8`: Update badge to `python-3.11%2B`
3. `README.md:45`: "Python 3.11 or higher"
4. `pytest.ini:2`: `minversion = 3.11`
5. `docs/installation.rst`: Update Python version

#### 5.2. GitHub URLs with Placeholders

**Location**: `pyproject.toml:62-65`

```toml
# Current:
[project.urls]
Homepage = "https://github.com/yourusername/CTHarvester"
Documentation = "https://github.com/yourusername/CTHarvester/wiki"
Repository = "https://github.com/yourusername/CTHarvester"
Issues = "https://github.com/yourusername/CTHarvester/issues"
```

**Update to**:
```toml
[project.urls]
Homepage = "https://github.com/jikhanjung/CTHarvester"
Documentation = "https://jikhanjung.github.io/CTHarvester"
Repository = "https://github.com/jikhanjung/CTHarvester"
Issues = "https://github.com/jikhanjung/CTHarvester/issues"
```

#### 5.3. README References Wrong Script

**Location**: `README.md:115-123`

References `bump_version.py` which doesn't exist. Actual file is `manage_version.py`.

**Update**:
```bash
# Before:
python bump_version.py patch

# After:
python manage_version.py bump patch
```

**Files to Update**:
1. `README.md` - Update all `bump_version.py` references
2. `README.ko.md` - Same updates in Korean version
3. `docs/developer_guide.rst` - Update version management section

---

### Issue 6: Test Organization and Markers

**Priority**: 🟡 HIGH
**Estimated Time**: 2 hours
**Impact**: Better test selection, faster CI

#### Problem

**Current State**:
- 486 tests collected
- Unit marker: 0 tests selected
- Integration marker: 9 tests selected
- Most tests have no markers

**Goal**: Apply markers to all tests for selective running

#### Implementation Plan

**Marker Strategy**:
```python
# Unit tests - Fast, no external dependencies
@pytest.mark.unit
def test_settings_manager_get():
    ...

# Integration tests - Multiple components
@pytest.mark.integration
def test_thumbnail_generation_workflow():
    ...

# UI tests - Requires Qt application
@pytest.mark.ui
def test_settings_dialog_save():
    ...

# Slow tests - Long running (>1s)
@pytest.mark.slow
def test_full_pipeline():
    ...

# Requires optional dependencies
@pytest.mark.skipif(not HAS_PYMCUBES, reason="pymcubes not installed")
def test_mesh_generation():
    ...
```

**Files to Update** (31 test files):

**Unit Tests** (add `@pytest.mark.unit`):
- `tests/test_settings_manager.py`
- `tests/test_file_utils.py`
- `tests/test_common.py`
- `tests/test_image_utils.py`
- `tests/test_worker.py`
- `tests/test_error_message_builder.py`
- `tests/test_progress_manager.py`
- `tests/test_progress_tracker.py`

**Integration Tests** (add `@pytest.mark.integration`):
- `tests/test_integration_thumbnail.py` ✅ (already has it)
- `tests/test_thumbnail_generator.py` - Some tests
- `tests/test_thumbnail_manager.py` - Some tests

**UI Tests** (add `@pytest.mark.ui`):
- `tests/ui/test_dialogs.py`
- `tests/ui/test_interactive_dialogs.py`
- `tests/ui/test_mcube_widget.py`
- `tests/ui/test_object_viewer_2d.py`
- `tests/ui/test_vertical_timeline.py`

**Update pytest.ini**:
```ini
[pytest]
markers =
    unit: Unit tests - fast, isolated
    integration: Integration tests - multiple components
    ui: UI tests - requires Qt application
    slow: Slow tests - may take >1 second
```

**CI Update** (`.github/workflows/test.yml`):
```yaml
# Fast tests (unit only)
- name: Run unit tests
  run: pytest -m unit -v

# All tests except slow
- name: Run integration tests
  run: pytest -m "integration and not slow" -v

# UI tests
- name: Run UI tests
  run: pytest -m ui -v
```

---

### Issue 7: Dependency Management Consolidation

**Priority**: 🟡 HIGH
**Estimated Time**: 1 hour
**Impact**: Consistent environments, easier setup

#### Problem

Three files define dependencies with inconsistencies:
- `requirements.txt` - Runtime dependencies
- `requirements-dev.txt` - Development dependencies
- `pyproject.toml` - Project metadata and build dependencies

**Examples of Inconsistencies**:
```
# requirements.txt
maturin>=1.4.0,<2.0.0

# pyproject.toml build-system
maturin>=1.3.0
```

#### Solution Plan

**Option A: Use pyproject.toml as Single Source of Truth (Modern)**
```toml
[project]
dependencies = [
    "PyQt5>=5.15.0",
    "numpy>=1.24.0",
    "Pillow>=10.0.0",
    # ... all runtime deps
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    # ... all dev deps
]

rust = [
    "maturin>=1.4.0,<2.0.0",
]
```

**Option B: Keep requirements.txt, Generate from pyproject.toml**
```bash
# Install tool
pip install pip-tools

# Generate requirements.txt from pyproject.toml
pip-compile pyproject.toml -o requirements.txt
pip-compile --extra dev pyproject.toml -o requirements-dev.txt
```

**Recommendation**: Option A (modern Python packaging)

**Migration Path**:
1. Move all dependencies to `pyproject.toml`
2. Keep `requirements.txt` for backward compatibility (generate from pyproject.toml)
3. Update installation docs

**Files to Update**:
1. `pyproject.toml` - Add complete dependency lists
2. `requirements.txt` - Simplify or generate
3. `requirements-dev.txt` - Simplify or generate
4. `README.md` - Update installation instructions
5. `docs/installation.rst` - Update installation guide

---

## 🟢 MEDIUM PRIORITY ISSUES (This Month)

### Issue 8: Continue main_window.py Refactoring

**Priority**: 🟢 MEDIUM
**Estimated Time**: 4 hours
**Current**: 1,225 lines (down from 4,840 - 96.6% reduction already!)

**Extraction Targets**:

1. **Menu and Action Setup** (200 lines) → `ui/setup/menu_setup.py`
2. **Toolbar Setup** (100 lines) → `ui/setup/toolbar_setup.py`
3. **Crop Handlers** (150 lines) → `ui/handlers/crop_handler.py`
4. **Volume Handlers** (200 lines) → `ui/handlers/volume_handler.py`
5. **Image Loading** (100 lines) → `ui/handlers/image_handler.py`

**Goal**: Reduce to <800 lines, each handler <300 lines

---

### Issue 9: CI/CD Enhancements

**Priority**: 🟢 MEDIUM
**Estimated Time**: 2 hours

#### 9.1. Pre-commit Hook Verification

Add to `.github/workflows/test.yml`:
```yaml
- name: Verify pre-commit hooks
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

#### 9.2. Documentation Build Check

Add to `.github/workflows/test.yml`:
```yaml
- name: Verify documentation builds
  run: |
    pip install sphinx sphinx-rtd-theme
    cd docs && make html
```

#### 9.3. Code Coverage Thresholds

Update `pytest.ini`:
```ini
[tool:pytest]
addopts =
    --cov=core
    --cov=ui
    --cov=utils
    --cov-report=html
    --cov-report=term
    --cov-fail-under=90
```

---

### Issue 10: Security Enhancements

**Priority**: 🟢 MEDIUM
**Estimated Time**: 3 hours

#### 10.1. Increase Security Test Coverage

**Current**: `security/file_validator.py` at 40.51% coverage

**Target**: 90%+ coverage

**Missing Tests**:
- Symlink handling
- Unicode path handling
- Very long path names
- Special characters in filenames
- Case sensitivity edge cases

#### 10.2. Audit File Operations

**Task**: Ensure all file operations use `FileValidator`

**Files to Audit**:
- `core/thumbnail_generator.py`
- `ui/handlers/export_handler.py`
- `utils/file_utils.py`
- `core/thumbnail_manager.py`

**Pattern to Check**:
```python
# Bad:
with open(user_provided_path) as f:
    ...

# Good:
from security.file_validator import FileValidator
validator = FileValidator()
if validator.validate_path(user_provided_path):
    with open(user_provided_path) as f:
        ...
```

---

## 🔵 LOW PRIORITY ISSUES (When Time Permits)

### Issue 11: Code Quality Improvements

**Priority**: 🔵 LOW
**Estimated Time**: 4-6 hours

#### 11.1. Replace Print Statements with Logging

**Found**: 322 print statements across 25 files

**Key Files**:
- `ui/main_window.py` (5 occurrences)
- `core/thumbnail_manager.py` (1 occurrence)
- `core/thumbnail_generator.py` (1 occurrence)

**Pattern**:
```python
# Before:
print(f"Processing {count} images")

# After:
logger.info(f"Processing {count} images")
```

#### 11.2. Replace Wildcard Imports

**Location**: `ui/widgets/mcube_widget.py:22-23`

```python
# Before:
from OpenGL.GL import *
from OpenGL.GLU import *

# After:
from OpenGL.GL import (
    glClear, glClearColor, glEnable, glDisable,
    glBegin, glEnd, glVertex3f, glColor3f,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LIGHTING, GL_LIGHT0,
    # ... only what's actually used
)
```

#### 11.3. Add Module Docstrings

Add comprehensive module docstrings to:
- `config/` modules
- `utils/` modules
- `security/` modules

**Template**:
```python
"""Module short description.

Longer description of module purpose and contents.

Example:
    >>> from module import Class
    >>> obj = Class()
    >>> obj.method()

Attributes:
    MODULE_CONSTANT: Description

Notes:
    Additional notes about usage
"""
```

---

### Issue 12: Documentation Improvements

**Priority**: 🔵 LOW
**Estimated Time**: 3 hours

#### 12.1. Create Devlog Index

**File**: `devlog/README.md`

```markdown
# Development Log Index

Chronological index of all development sessions.

## Recent Sessions (October 2025)

- [053](20251001_053_comprehensive_improvement_plan.md) - Comprehensive improvement plan
- [052](20251001_052_python_thumbnail_progress_fix.md) - Python thumbnail progress fix
- [051](20251001_051_phase2_python_thumbnail_completion.md) - Phase 2 completion
...

## By Topic

### Architecture & Refactoring
- Session 044, 043, 041

### Testing
- Session 042, 040, 039

### Documentation
- Session 045, 038
```

#### 12.2. Configuration Guide

**File**: `docs/configuration.md`

Document all settings from `config/settings.yaml` with:
- Default values
- Valid ranges
- Use cases
- Examples

#### 12.3. API Documentation Deployment

1. Verify Sphinx build works
2. Enable GitHub Pages (already have workflow)
3. Update README with docs link

---

## IMPLEMENTATION TIMELINE

### Week 1: Critical Fixes

**Day 1-2**:
- ✅ Issue 1: Fix thumbnail generation API
- ✅ Issue 2: Fix progress sampling
- ✅ Issue 3: Add failure handling

**Day 3**:
- ✅ Issue 4: Repository cleanup
- ✅ Issue 5: Documentation fixes
- ✅ Write comprehensive tests

**Day 4-5**:
- ✅ Issue 6: Add test markers
- ✅ Issue 7: Consolidate dependencies
- ✅ Verify all tests pass

### Week 2: High Priority

**Day 1-2**:
- Issue 8: Continue main_window.py refactoring
- Extract 2-3 handlers

**Day 3-4**:
- Issue 9: CI/CD enhancements
- Issue 10: Security improvements

**Day 5**:
- Testing and verification
- Documentation updates

### Month 1: Medium Priority

- Complete Issue 8 (main_window refactoring)
- Complete Issue 9 (CI/CD)
- Complete Issue 10 (Security)

### Ongoing: Low Priority

- Issue 11: Code quality (as time permits)
- Issue 12: Documentation (continuous improvement)

---

## SUCCESS METRICS

### Week 1 Goals:
- ✅ All critical bugs fixed
- ✅ Test suite passes 100%
- ✅ Repository cleaned
- ✅ Documentation accurate

### Week 2 Goals:
- ✅ Test markers applied (100% coverage)
- ✅ CI/CD enhanced with pre-commit and docs checks
- ✅ Security coverage >90%

### Month 1 Goals:
- ✅ main_window.py <800 lines
- ✅ All handlers <300 lines
- ✅ Code coverage >90% across all modules

---

## RISK MITIGATION

### Risks:

1. **Breaking Changes**: API signature changes may break external code
   - Mitigation: Version bump (0.2.3 → 0.3.0), document migration

2. **Test Failures**: Refactoring may introduce regressions
   - Mitigation: Run full test suite after each change

3. **Time Overrun**: Some tasks may take longer than estimated
   - Mitigation: Prioritize critical fixes first, defer low priority

---

## NOTES

- This is a living document - update as work progresses
- Mark completed items with ✅
- Add new issues as discovered
- Link to related commits/PRs

---

## REFERENCES

- Original analysis: Session #053 comprehensive review
- Recent commits: 5425d76, e4e7d57, d2c74d7
- Related issues: GitHub Issues tracker
- Test coverage report: `htmlcov/index.html`
