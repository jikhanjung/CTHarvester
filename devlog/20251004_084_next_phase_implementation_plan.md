# Devlog 084: Next Phase Implementation Plan (Phase 4.2-4.4)

**Date:** 2025-10-04
**Status:** 📋 Planning
**Previous:** [devlog 083 - Phase 4 Progress](./20251004_083_phase4_refactoring_progress.md)

---

## 🎯 Overall Goal

Complete the large file refactoring identified in devlog 079:
- **main_window.py:** 1,268 → <800 lines (remove 468 lines)
- **thumbnail_manager.py:** 1,116 → <800 lines (remove 316 lines)

**Total target reduction:** 784 lines across 2 files

---

## 📋 Phase 4.2: ThumbnailCreationHandler Extraction

**Priority:** 🔴 High (Highest ROI)
**Estimated Time:** 6-8 hours
**Target Line Reduction:** ~320 lines from main_window.py

### Rationale

The three largest methods in main_window.py are all thumbnail-related:
1. `create_thumbnail_rust()` - 170 lines
2. `create_thumbnail_python()` - 146 lines
3. `create_thumbnail()` - 31 lines (dispatcher)

**Total:** 347 lines (74% of needed reduction for main_window.py)

### Implementation Steps

#### Step 1: Create Handler Module (1 hour)
**File:** `ui/handlers/thumbnail_creation_handler.py`

**Class Structure:**
```python
class ThumbnailCreationHandler:
    """Handles thumbnail creation using Rust or Python fallback.

    Extracted from CTHarvesterMainWindow during Phase 4.2 refactoring
    to reduce file size and improve separation of concerns.
    """

    def __init__(self, main_window):
        self.window = main_window

    def create_thumbnail(self) -> bool:
        """Dispatcher: Choose Rust or Python implementation."""
        use_rust = self._should_use_rust()
        if use_rust:
            return self.create_thumbnail_rust()
        else:
            return self.create_thumbnail_python()

    def create_thumbnail_rust(self) -> bool:
        """High-performance Rust-based thumbnail generation."""
        # [170 lines from main_window.py]

    def create_thumbnail_python(self) -> bool:
        """Python fallback thumbnail generation."""
        # [146 lines from main_window.py]

    def _should_use_rust(self) -> bool:
        """Check if Rust module is available and preferred."""
        # [Logic from create_thumbnail()]
```

**Dependencies to Handle:**
- `self.edtDirname` → `self.window.edtDirname`
- `self.progress_dialog` → `self.window.progress_dialog`
- `self.thumbnail_start_time` → `self.window.thumbnail_start_time`
- `self.settings_hash` → `self.window.settings_hash`
- `self.level_info` → `self.window.level_info`
- `self.m_app` → `self.window.m_app`

---

#### Step 2: Extract create_thumbnail_rust() (2-3 hours)

**Complexity Factors:**
- Progress dialog integration (callbacks)
- Rust FFI error handling
- State management (thumbnail_start_time, level_info)
- QApplication.processEvents() calls

**Key Changes:**
```python
# Before (in main_window.py)
def create_thumbnail_rust(self):
    self.thumbnail_start_time = time.time()
    dirname = self.edtDirname.text()
    self.progress_dialog = ProgressDialog(self)
    # ... 170 lines ...

# After (in main_window.py)
def create_thumbnail_rust(self):
    return self.thumbnail_creation_handler.create_thumbnail_rust()

# After (in thumbnail_creation_handler.py)
def create_thumbnail_rust(self):
    self.window.thumbnail_start_time = time.time()
    dirname = self.window.edtDirname.text()
    self.window.progress_dialog = ProgressDialog(self.window)
    # ... rest of logic ...
```

**Testing Strategy:**
1. Unit test: Mock Rust module, verify progress callbacks
2. Integration test: Full thumbnail generation flow
3. Manual test: Verify UI updates correctly

---

#### Step 3: Extract create_thumbnail_python() (2-3 hours)

**Complexity Factors:**
- ThumbnailManager integration
- Progress tracking delegation
- Multi-level thumbnail generation
- Error recovery

**Key Refactoring:**
```python
def create_thumbnail_python(self):
    # State setup
    self.window.thumbnail_start_time = time.time()

    # Progress dialog
    self.window.progress_dialog = ProgressDialog(self.window)

    # ThumbnailManager delegation
    manager = ThumbnailManager(
        parent=self.window,
        progress_dialog=self.window.progress_dialog,
        threadpool=self.window.threadpool
    )

    # Process levels
    for level in range(num_levels):
        # [Existing logic]

    return not self.window.progress_dialog.is_cancelled
```

---

#### Step 4: Update main_window.py (1 hour)

**Changes:**
1. Add handler initialization in `__init__()`:
   ```python
   # Initialize thumbnail creation handler (Phase 4.2)
   self.thumbnail_creation_handler = ThumbnailCreationHandler(self)
   ```

2. Replace method bodies:
   ```python
   def create_thumbnail(self):
       return self.thumbnail_creation_handler.create_thumbnail()

   def create_thumbnail_rust(self):
       return self.thumbnail_creation_handler.create_thumbnail_rust()

   def create_thumbnail_python(self):
       return self.thumbnail_creation_handler.create_thumbnail_python()
   ```

3. Or remove methods entirely and update callers:
   ```python
   # Before
   self.create_thumbnail()

   # After
   self.thumbnail_creation_handler.create_thumbnail()
   ```

---

#### Step 5: Testing & Validation (1-2 hours)

**Test Cases:**
1. ✅ Rust thumbnail generation with progress
2. ✅ Python fallback with cancellation
3. ✅ Progress dialog updates
4. ✅ Multi-level thumbnail generation
5. ✅ Error handling (missing directory, disk full)

**Validation:**
```bash
# Run existing tests
python -m pytest tests/test_main_window.py -v

# Check line count
wc -l ui/main_window.py ui/handlers/thumbnail_creation_handler.py

# Expected:
# ~950 ui/main_window.py (was 1,268)
# ~370 ui/handlers/thumbnail_creation_handler.py (new)
```

---

## 📋 Phase 4.3: DirectoryHandler Extraction

**Priority:** 🟡 Medium
**Estimated Time:** 2-3 hours
**Target Line Reduction:** ~80 lines from main_window.py

### Scope

Extract `open_dir()` method (78 lines) to FileHandler or new DirectoryHandler.

**Current Location:** main_window.py:446-523

**Complexity:**
- File dialog interaction
- Settings integration (default_directory, remember_directory)
- Thumbnail loading/generation orchestration
- UI state updates

### Implementation

**Option A: Extend FileHandler**
```python
# In ui/handlers/file_handler.py
class FileHandler:
    def open_directory_ui(self, parent_window):
        """Handle directory opening with UI dialogs."""
        # Extract open_dir() logic here
```

**Option B: New DirectoryHandler**
```python
# New file: ui/handlers/directory_handler.py
class DirectoryHandler:
    def __init__(self, main_window):
        self.window = main_window
        self.file_handler = main_window.file_handler

    def open_directory(self):
        """Open directory with file dialog and load data."""
        # [78 lines from open_dir()]
```

**Recommendation:** Option A (extend FileHandler) - better cohesion

---

## 📋 Phase 4.4: ViewManager Extraction

**Priority:** 🟡 Medium
**Estimated Time:** 4-5 hours
**Target Line Reduction:** ~130 lines from main_window.py

### Scope

Extract view management methods:
1. `update_3D_view()` - 62 lines
2. `comboLevelIndexChanged()` - 62 lines
3. Related helpers (~10-20 lines)

### Implementation

**File:** `ui/handlers/view_manager.py`

**Class Structure:**
```python
class ViewManager:
    """Manages 3D view updates and level switching.

    Coordinates between:
    - mcube_widget (3D visualization)
    - image_label (2D viewer)
    - level selector combo box
    - thumbnail data
    """

    def __init__(self, main_window):
        self.window = main_window

    def update_3d_view(self, update_volume=True):
        """Update 3D mesh visualization."""
        # [62 lines from main_window.py]

    def handle_level_change(self, index):
        """Handle pyramid level change from combo box."""
        # [62 lines from comboLevelIndexChanged()]

    def _load_level_thumbnails(self, level_idx):
        """Load thumbnail data for specific level."""
        # [Helper logic]
```

**Benefits:**
- Clearer separation of view logic
- Easier testing (mock window components)
- Potential for view state caching

---

## 📋 Phase 4.5: Further thumbnail_manager.py Reduction (Optional)

**Priority:** 🟢 Low (Optional)
**Estimated Time:** 4-6 hours
**Target Line Reduction:** ~320 lines from thumbnail_manager.py

### Current State
- **Current:** 1,116 lines
- **Goal:** <800 lines
- **Need to remove:** 316 lines

### Extraction Candidates

#### 1. ETA Calculator (100-150 lines)
Extract ETA calculation logic to dedicated class:

**File:** `core/eta_calculator.py`
```python
class ETACalculator:
    """Calculates and formats ETA for long-running operations."""

    def calculate_eta(self, completed, total, elapsed_time):
        """Calculate estimated time remaining."""

    def format_eta(self, seconds):
        """Format ETA as human-readable string (e.g., '2m 30s')."""
```

#### 2. Progress Coordinator (100-150 lines)
Extract progress coordination to separate class:

**File:** `core/progress_coordinator.py`
```python
class ProgressCoordinator:
    """Coordinates progress updates across multiple levels."""

    def update_global_progress(self, level_progress):
        """Update global progress bar based on weighted levels."""

    def calculate_weighted_progress(self, level_weights):
        """Calculate progress considering pyramid level weights."""
```

#### 3. Sampling Logic (50-100 lines)
Extract performance sampling:

**File:** `core/performance_sampler.py`
```python
class PerformanceSampler:
    """Samples processing performance for ETA estimation."""

    def start_sampling(self, sample_size):
        """Start performance sampling."""

    def record_sample(self, elapsed_time):
        """Record sample timing."""

    def get_throughput(self):
        """Calculate images per second."""
```

---

## 📊 Expected Results

### File Size Reductions

| File | Current | After 4.2 | After 4.3 | After 4.4 | After 4.5 | Goal | Status |
|------|---------|-----------|-----------|-----------|-----------|------|--------|
| **main_window.py** | 1,268 | ~950 | ~870 | ~740 | ~740 | 800 | ✅ Goal Met |
| **thumbnail_manager.py** | 1,116 | 1,116 | 1,116 | 1,116 | ~800 | 800 | ✅ Goal Met |

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `ui/handlers/thumbnail_creation_handler.py` | ~370 | Rust/Python thumbnail generation |
| `ui/handlers/view_manager.py` | ~150 | 3D view and level management |
| `core/eta_calculator.py` | ~120 | ETA calculation (optional) |
| `core/progress_coordinator.py` | ~120 | Progress coordination (optional) |

---

## ⏱️ Time Breakdown

### Phase 4.2: ThumbnailCreationHandler (6-8 hours)
- Step 1: Create handler module - 1h
- Step 2: Extract create_thumbnail_rust - 2-3h
- Step 3: Extract create_thumbnail_python - 2-3h
- Step 4: Update main_window - 1h
- Step 5: Testing - 1-2h

### Phase 4.3: DirectoryHandler (2-3 hours)
- Extract open_dir() - 1-2h
- Update FileHandler - 0.5h
- Testing - 0.5-1h

### Phase 4.4: ViewManager (4-5 hours)
- Create ViewManager - 1h
- Extract update_3D_view - 1.5h
- Extract comboLevelIndexChanged - 1.5h
- Testing - 1h

### Phase 4.5: Further Reduction (4-6 hours, Optional)
- Extract ETA calculator - 1.5-2h
- Extract progress coordinator - 1.5-2h
- Extract performance sampler - 1-2h

**Total Estimated Time:** 16-22 hours (12-16 hours for required phases)

---

## 🎯 Success Criteria

### Phase 4.2 Complete When:
- ✅ main_window.py < 1000 lines
- ✅ ThumbnailCreationHandler fully functional
- ✅ All existing tests pass
- ✅ Mypy clean
- ✅ Rust and Python thumbnail generation work identically

### Phase 4.3 Complete When:
- ✅ main_window.py < 900 lines
- ✅ Directory opening works through FileHandler
- ✅ Settings integration maintained

### Phase 4.4 Complete When:
- ✅ main_window.py < 800 lines ✨ **Goal achieved!**
- ✅ ViewManager handles all 3D view updates
- ✅ Level switching works correctly

### Phase 4.5 Complete When (Optional):
- ✅ thumbnail_manager.py < 800 lines ✨ **Goal achieved!**
- ✅ ETA calculation extracted and tested
- ✅ Progress coordination simplified

---

## 🚨 Risks & Mitigations

### Risk 1: Breaking Existing Functionality
**Probability:** Medium
**Impact:** High

**Mitigation:**
- Run full test suite after each extraction
- Manual testing of thumbnail generation flows
- Keep git commits granular for easy rollback

### Risk 2: State Management Complexity
**Probability:** Medium
**Impact:** Medium

**Mitigation:**
- Document state dependencies clearly
- Use property delegation pattern (established in Phase 4.1)
- Add state validation assertions

### Risk 3: Performance Regression
**Probability:** Low
**Impact:** Medium

**Mitigation:**
- Profile before/after extraction
- Keep delegation overhead minimal
- Monitor thumbnail generation times

### Risk 4: UI Responsiveness
**Probability:** Low
**Impact:** Medium

**Mitigation:**
- Preserve all QApplication.processEvents() calls
- Test progress dialog updates
- Verify cancellation still works

---

## 📋 Implementation Checklist

### Before Starting
- [ ] Review devlog 083 (Phase 4.1 results)
- [ ] Check git status (all clean)
- [ ] Run full test suite (baseline)
- [ ] Profile thumbnail generation (baseline)

### Phase 4.2: ThumbnailCreationHandler
- [ ] Create `ui/handlers/thumbnail_creation_handler.py`
- [ ] Extract `_should_use_rust()` helper
- [ ] Extract `create_thumbnail_rust()` (170 lines)
- [ ] Extract `create_thumbnail_python()` (146 lines)
- [ ] Extract `create_thumbnail()` dispatcher (31 lines)
- [ ] Update main_window.py initialization
- [ ] Replace method bodies or update callers
- [ ] Add type hints and docstrings
- [ ] Run pytest tests/test_main_window.py
- [ ] Run mypy ui/handlers/thumbnail_creation_handler.py
- [ ] Manual test: Rust thumbnail generation
- [ ] Manual test: Python fallback
- [ ] Manual test: Progress cancellation
- [ ] Commit with descriptive message

### Phase 4.3: DirectoryHandler
- [ ] Extend FileHandler with `open_directory_ui()`
- [ ] Extract `open_dir()` logic (78 lines)
- [ ] Update main_window.py delegation
- [ ] Test directory opening
- [ ] Test settings integration
- [ ] Commit

### Phase 4.4: ViewManager
- [ ] Create `ui/handlers/view_manager.py`
- [ ] Extract `update_3D_view()` (62 lines)
- [ ] Extract `comboLevelIndexChanged()` (62 lines)
- [ ] Update main_window.py delegation
- [ ] Test 3D view updates
- [ ] Test level switching
- [ ] Commit

### Phase 4.5: Optional Further Reduction
- [ ] Decide if needed (based on 4.2-4.4 results)
- [ ] Create ETA calculator if needed
- [ ] Create progress coordinator if needed
- [ ] Test and commit

### Final Validation
- [ ] Run full test suite (pytest)
- [ ] Run mypy on all modified files
- [ ] Check flake8 compliance
- [ ] Verify line counts meet goals
- [ ] Update devlog 083 with final results
- [ ] Create completion report (devlog 085)

---

## 🔗 Related Documents

- [devlog 079 - Codebase Analysis](./20251004_079_codebase_analysis_recommendations.md)
- [devlog 083 - Phase 4 Progress](./20251004_083_phase4_refactoring_progress.md)
- [devlog 072 - Comprehensive Plan](./20251004_072_comprehensive_code_analysis_and_improvement_plan.md)

---

## 📝 Notes for Next Session

### Start Here
1. Read this plan (devlog 084)
2. Review Phase 4.1 results (devlog 083)
3. Begin with Phase 4.2 Step 1 (create handler module)

### Quick Start Commands
```bash
# Check current state
wc -l ui/main_window.py core/thumbnail_manager.py
git status
pytest tests/test_main_window.py -v

# Start Phase 4.2
touch ui/handlers/thumbnail_creation_handler.py
# [Edit file with template from above]
```

### Context Preservation
- All Phase 4.1 work committed (3 commits)
- Working tree clean
- 911 tests passing
- Mypy clean in all refactored files

---

**Plan Created:** 2025-10-04
**Next Action:** Implement Phase 4.2 (ThumbnailCreationHandler)
**Expected Outcome:** main_window.py < 800 lines, improved maintainability
