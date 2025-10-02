# Dependency Injection Improvement Plan

**Date**: 2025-10-02
**Status**: ❌ REJECTED - Overkill for current project scale
**Priority**: N/A

## Decision Summary

After review, this plan has been **rejected** as unnecessary complexity.

**Reason for Rejection**:
- Current project is a single desktop application with clear separation of concerns
- Already has 485 passing tests (~95% coverage) without DI
- Introducing Protocol/Adapter/Factory patterns would add 15-20 hours of work for minimal benefit
- Code complexity would increase significantly
- Only beneficial if project scales 2-3x or needs multiple UI framework support

**Verdict**: Keep current straightforward architecture. DI may be reconsidered if:
- CLI version is needed
- Multiple UI framework support required
- Project grows significantly larger

---

## Original Plan (Archived for Reference)

## Current Issues

### 1. Tight Coupling in ThumbnailManager

**Current Implementation** (`core/thumbnail_manager.py`):
```python
class ThumbnailManager:
    def __init__(self, parent, progress_dialog, threadpool, ...):
        self.parent = parent
        self.progress_dialog = progress_dialog  # Direct dependency
        self.threadpool = threadpool
```

**Problems**:
- Direct dependency on `ProgressDialog` makes testing difficult
- Cannot use different progress reporting strategies
- Hard to mock for unit tests
- Violates Dependency Inversion Principle

### 2. MainWindow God Object

**Current Implementation** (`ui/main_window.py`):
```python
class CTHarvesterMainWindow:
    def create_thumbnail_python(self):
        self.thumbnail_manager = ThumbnailManager(
            self,
            self.progress_dialog,  # Tightly coupled
            self.threadpool,
            ...
        )
```

**Problems**:
- MainWindow directly instantiates all dependencies
- Difficult to replace components for testing
- High coupling between UI and business logic

---

## Proposed Solution: Dependency Injection

### Phase 1: Extract Callback Interfaces

#### 1.1 Define Progress Callback Protocol

**New File**: `core/interfaces.py`
```python
"""Interface definitions for dependency injection."""

from typing import Protocol, Callable


class ProgressReporter(Protocol):
    """Interface for progress reporting."""

    def report_progress(self, percentage: float, message: str) -> None:
        """Report progress update.

        Args:
            percentage: Progress percentage (0-100)
            message: Status message to display
        """
        ...

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled by user.

        Returns:
            True if cancelled, False otherwise
        """
        ...


class ETACalculator(Protocol):
    """Interface for ETA calculation."""

    def update_eta(
        self,
        completed: int,
        total: int,
        elapsed_time: float
    ) -> str:
        """Calculate and format ETA.

        Args:
            completed: Number of completed items
            total: Total number of items
            elapsed_time: Elapsed time in seconds

        Returns:
            Formatted ETA string (e.g., "2m 30s")
        """
        ...
```

#### 1.2 Refactor ThumbnailManager to Use Protocols

**Modified**: `core/thumbnail_manager.py`
```python
from typing import Optional
from core.interfaces import ProgressReporter, ETACalculator


class ThumbnailManager:
    """Thumbnail generation manager with dependency injection."""

    def __init__(
        self,
        progress_reporter: ProgressReporter,
        eta_calculator: Optional[ETACalculator] = None,
        threadpool: Optional[QThreadPool] = None,
        parent=None,  # Keep for backwards compatibility
        ...
    ):
        """Initialize with injected dependencies.

        Args:
            progress_reporter: Object implementing ProgressReporter protocol
            eta_calculator: Optional ETA calculator (uses default if None)
            threadpool: Optional thread pool (creates default if None)
            parent: Parent object (deprecated, for backwards compatibility)
        """
        self.progress_reporter = progress_reporter
        self.eta_calculator = eta_calculator or DefaultETACalculator()
        self.threadpool = threadpool or QThreadPool.globalInstance()
        self.parent = parent  # Kept for legacy code

    def update_progress(self, percentage: float, message: str):
        """Update progress using injected reporter."""
        self.progress_reporter.report_progress(percentage, message)

    def check_cancelled(self) -> bool:
        """Check cancellation using injected reporter."""
        return self.progress_reporter.is_cancelled()
```

#### 1.3 Create Adapter for Existing ProgressDialog

**New Class**: `ui/adapters.py`
```python
"""Adapters for integrating legacy components with new interfaces."""

from PyQt5.QtWidgets import QProgressDialog
from core.interfaces import ProgressReporter


class ProgressDialogAdapter(ProgressReporter):
    """Adapter to make QProgressDialog implement ProgressReporter."""

    def __init__(self, dialog: QProgressDialog):
        self.dialog = dialog

    def report_progress(self, percentage: float, message: str) -> None:
        """Report progress to Qt dialog."""
        self.dialog.setValue(int(percentage))
        self.dialog.setLabelText(message)

    def is_cancelled(self) -> bool:
        """Check if dialog was cancelled."""
        return self.dialog.wasCanceled()


# Usage in MainWindow:
from ui.adapters import ProgressDialogAdapter

def create_thumbnail(self):
    adapter = ProgressDialogAdapter(self.progress_dialog)
    manager = ThumbnailManager(
        progress_reporter=adapter,
        threadpool=self.threadpool
    )
```

### Phase 2: Extract File Operations Interface

#### 2.1 Define File Operations Protocol

**Add to**: `core/interfaces.py`
```python
class FileOperations(Protocol):
    """Interface for file system operations."""

    def list_files(
        self,
        directory: str,
        pattern: str
    ) -> list[str]:
        """List files matching pattern."""
        ...

    def read_image(self, path: str) -> np.ndarray:
        """Read image from file."""
        ...

    def write_image(self, path: str, data: np.ndarray) -> None:
        """Write image to file."""
        ...
```

#### 2.2 Benefits
- Easy to create mock file operations for tests
- Can implement caching layer
- Can add validation layer
- Testable without actual file I/O

### Phase 3: Factory Pattern for Complex Objects

#### 3.1 Thumbnail Manager Factory

**New File**: `core/factories.py`
```python
"""Factories for creating configured objects."""

from typing import Optional
from PyQt5.QtCore import QThreadPool
from core.thumbnail_manager import ThumbnailManager
from core.interfaces import ProgressReporter


class ThumbnailManagerFactory:
    """Factory for creating configured ThumbnailManager instances."""

    @staticmethod
    def create(
        progress_reporter: ProgressReporter,
        settings: dict,
        threadpool: Optional[QThreadPool] = None
    ) -> ThumbnailManager:
        """Create a configured ThumbnailManager.

        Args:
            progress_reporter: Progress reporting implementation
            settings: Configuration dictionary
            threadpool: Optional thread pool

        Returns:
            Configured ThumbnailManager instance
        """
        return ThumbnailManager(
            progress_reporter=progress_reporter,
            threadpool=threadpool or QThreadPool.globalInstance(),
            size=settings.get('thumbnail_size', 512),
            max_size=settings.get('max_thumbnail_size', 512),
            sample_size=settings.get('sample_size', 20)
        )


# Usage:
factory = ThumbnailManagerFactory()
manager = factory.create(
    progress_reporter=adapter,
    settings=self.settings
)
```

---

## Testing Benefits

### Before (Tight Coupling):
```python
def test_thumbnail_generation():
    # Need to create actual Qt widgets
    app = QApplication([])
    dialog = QProgressDialog()
    parent = MainWindow()  # Heavy object

    manager = ThumbnailManager(parent, dialog, ...)
    # Hard to verify progress reporting
```

### After (Dependency Injection):
```python
class MockProgressReporter:
    def __init__(self):
        self.progress_calls = []
        self.cancelled = False

    def report_progress(self, percentage, message):
        self.progress_calls.append((percentage, message))

    def is_cancelled(self):
        return self.cancelled


def test_thumbnail_generation():
    # No Qt dependencies needed
    mock_reporter = MockProgressReporter()

    manager = ThumbnailManager(
        progress_reporter=mock_reporter,
        threadpool=None  # Uses global instance
    )

    # Easy to verify behavior
    assert len(mock_reporter.progress_calls) > 0
    assert mock_reporter.progress_calls[0][0] == 0.0
```

---

## Migration Strategy

### Step 1: Add Interfaces (Non-Breaking)
- Create `core/interfaces.py` with Protocol definitions
- Create `ui/adapters.py` with ProgressDialogAdapter
- No existing code breaks

### Step 2: Update ThumbnailManager Constructor (Backwards Compatible)
```python
def __init__(
    self,
    parent=None,  # Deprecated but kept
    progress_dialog=None,  # Deprecated but kept
    threadpool=None,
    progress_reporter: Optional[ProgressReporter] = None,  # New
    **kwargs
):
    # Support both old and new calling conventions
    if progress_reporter is None and progress_dialog is not None:
        # Legacy mode: create adapter
        from ui.adapters import ProgressDialogAdapter
        progress_reporter = ProgressDialogAdapter(progress_dialog)
    elif progress_reporter is None:
        # No progress reporting
        progress_reporter = NullProgressReporter()

    self.progress_reporter = progress_reporter
    # ... rest of init
```

### Step 3: Gradually Update Call Sites
- Update MainWindow to use new style
- Update tests to use mock reporters
- Mark old parameters as deprecated in docstrings

### Step 4: Remove Legacy Support (Future Release)
- Remove deprecated parameters
- Update all call sites
- Simplify constructor

---

## Implementation Checklist

- [ ] Create `core/interfaces.py` with Protocol definitions
- [ ] Create `ui/adapters.py` with ProgressDialogAdapter
- [ ] Add `NullProgressReporter` for headless operation
- [ ] Update `ThumbnailManager.__init__` with backwards compatibility
- [ ] Create unit tests using MockProgressReporter
- [ ] Update MainWindow to use adapter pattern
- [ ] Add factory pattern in `core/factories.py`
- [ ] Document migration guide
- [ ] Add deprecation warnings to old parameters
- [ ] Schedule removal of legacy code

---

## Benefits Summary

### Testability
- ✅ Test business logic without Qt dependencies
- ✅ Easy to create mocks and fakes
- ✅ Fast unit tests (no UI initialization)

### Flexibility
- ✅ Swap progress reporting implementations
- ✅ Support CLI mode with console progress
- ✅ Support batch mode with no progress
- ✅ Easy to add logging or telemetry

### Maintainability
- ✅ Clear separation of concerns
- ✅ Easier to understand dependencies
- ✅ Follows SOLID principles
- ✅ Backwards compatible migration path

### Performance
- ✅ No performance impact (protocols compile to duck typing)
- ✅ Can optimize specific implementations
- ✅ Can add caching layers transparently

---

## Estimated Effort

- **Phase 1 (Interfaces & Adapters)**: 4-6 hours
- **Phase 2 (File Operations)**: 3-4 hours
- **Phase 3 (Factory Pattern)**: 2-3 hours
- **Testing & Documentation**: 4-5 hours
- **Total**: ~15-20 hours

## Risk Assessment

- **Low Risk**: Changes are backwards compatible
- **Low Impact**: Existing functionality unchanged
- **High Value**: Much easier testing and maintenance
- **Recommended**: Implement incrementally over 2-3 PRs
