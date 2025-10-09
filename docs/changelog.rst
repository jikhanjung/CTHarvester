Changelog
=========

All notable changes to CTHarvester will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

[0.2.3-beta.2] - 2025-10-08
---------------------------

Added
~~~~~

* **Comprehensive keyboard shortcuts system** (24 shortcuts)

  * File operations: Open directory (Ctrl+O), Save cropped (Ctrl+S), Export (Ctrl+E)
  * View operations: Screenshot (F12)
  * Navigation: Previous/Next image (Ctrl+Left/Right), First/Last (Ctrl+Home/End)
  * Crop operations: Load/Save crop (Ctrl+Shift+L/S), Reset crop (Ctrl+R)
  * Threshold operations: Load/Save threshold (Ctrl+Alt+L/S), Reset threshold (Ctrl+T)
  * Help: Shortcuts help (F1)
  * Settings: Open settings (Ctrl+,)

* **Complete tooltip coverage** (100% on interactive elements)

  * Rich HTML formatting with keyboard shortcuts
  * Consistent styling across all UI elements

* **Professional UI styling system**

  * 8px grid spacing system for consistency
  * Standardized button sizes (32px height, 32x32px icons)
  * Unified color palette (Primary, Danger, Success, Warning, Neutral)
  * Centralized style configuration (``config/ui_style.py``)

* **Enhanced progress feedback**

  * Remaining items counter
  * ETA calculation with sophisticated smoothing
  * Percentage progress display
  * Cancel functionality for long operations

* **Comprehensive user documentation** (2,500+ lines)

  * Troubleshooting guide with 25+ scenarios
  * FAQ with 60+ questions answered
  * Advanced features guide with detailed examples
  * Complete workflow documentation

* **Performance benchmarking infrastructure**

  * Standard benchmark scenarios (Small/Medium/Large/XLarge)
  * 4 performance tests with memory profiling
  * Performance thresholds and validation
  * CI/CD compatible quick tests

* **Stress testing suite** (9 tests)

  * Memory leak detection tests
  * Long-running operation stability tests
  * Resource cleanup verification
  * Concurrent batch processing tests

* **Error recovery testing** (18 tests)

  * File system error handling (permission, OS errors)
  * Image processing errors (corrupt, invalid format)
  * Network drive disconnection scenarios
  * Graceful degradation mechanisms

* **Developer documentation** (1,500+ lines)

  * Error recovery guide (650 lines)
  * Performance guide (850 lines)
  * Best practices and patterns
  * Troubleshooting guides

Changed
~~~~~~~

* **UI/UX improvements**

  * Applied consistent 8px grid spacing throughout
  * Standardized button styling and sizing
  * Enhanced progress dialog with remaining items
  * Improved keyboard navigation

* **Documentation organization**

  * Restructured user guide sections
  * Added comprehensive developer guides
  * Created detailed troubleshooting sections

* **Test suite expansion**

  * Total tests: 1,150 (+18 from previous version)
  * Quick tests: 1,133 (< 1 minute)
  * Slow tests: 17 (> 1 minute)
  * Performance tests: 4
  * Stress tests: 9
  * Error recovery tests: 18
  * Coverage maintained at ~91%

Performance
~~~~~~~~~~~

* **Benchmark results**:

  * Small dataset (10 images, 512×512, 8-bit): < 1s
  * Medium dataset (100 images, 1024×1024, 8-bit): ~7s
  * Large dataset (500 images, 2048×2048, 16-bit): ~188s (3 minutes)
  * Image resize: < 200ms per image

* **Memory efficiency**:

  * Small datasets: < 150 MB
  * Medium datasets: < 200 MB (with batching)
  * Large datasets: < 3 GB (with batching)
  * Memory cleanup: > 50% freed after operations

* **Processing speed**:

  * Thumbnail generation (Rust): ~50ms per image
  * Thumbnail generation (Python): ~100-200ms per image
  * Full processing: ~300-400ms per image

* **Robustness verified**:

  * No memory leaks detected
  * All resources properly cleaned up
  * Stable performance over long operations
  * Linear scaling with dataset size

Technical Details
~~~~~~~~~~~~~~~~~

* **UI Infrastructure**:

  * ``ui/setup/shortcuts_setup.py``: Keyboard shortcut management
  * ``config/ui_style.py``: Centralized UI styling
  * ``config/tooltips.py``: Tooltip management
  * ``tests/test_ui_style.py``: 23 UI style tests

* **Performance Infrastructure**:

  * ``tests/benchmarks/benchmark_config.py``: Benchmark scenarios
  * ``tests/benchmarks/test_performance.py``: 4 performance tests
  * ``tests/benchmarks/test_stress.py``: 9 stress tests
  * ``tests/test_error_recovery.py``: 18 error recovery tests

* **CI/CD Infrastructure** (Comprehensive improvements - Score: 95/100):

  * **Security Scanning**:

    * ``.github/workflows/codeql.yml``: CodeQL SAST analysis (weekly + PR)
    * ``.github/workflows/dependency-review.yml``: Dependency vulnerability checks on PRs
    * Enhanced Bandit and pip-audit security scanning

  * **Test Workflows**:

    * ``.github/workflows/test.yml``: Quick tests (1,129 tests, ~30s with parallelization)
    * ``.github/workflows/test-full.yml``: Comprehensive tests (1,150 tests, nightly + tags)
    * Python 3.11, 3.12, 3.13 matrix testing
    * Coverage threshold: 85% (up from 60%)
    * Parallel execution with pytest-xdist (2-3x speedup)

  * **Release Automation**:

    * ``.github/workflows/release.yml``: CHANGELOG.md content extraction
    * ``.github/workflows/update-readme-badges.yml``: Auto-updating test count badges
    * Enhanced release notes with installation guide and docs links

  * **Artifact Management**:

    * Test results: 7-day retention
    * Build artifacts: 14-day retention
    * Security reports: 30-day retention

  * **Documentation**:

    * ``docs/CI_CD_AUDIT.md``: Comprehensive CI/CD audit report
    * ``devlog/20251008_099_cicd_improvements.md``: Implementation details

* **Documentation**:

  * ``docs/user_guide/troubleshooting.rst``: Troubleshooting guide
  * ``docs/user_guide/faq.rst``: Frequently asked questions
  * ``docs/user_guide/advanced_features.rst``: Advanced features
  * ``docs/developer_guide/error_recovery.md``: Error recovery patterns
  * ``docs/developer_guide/performance.md``: Performance characteristics

[0.2.3-beta.1] - 2025-10-01
---------------------------

Added
~~~~~

* Python thumbnail generation fallback when Rust module unavailable
* Comprehensive progress tracking with accurate ETA calculation
* Settings persistence for Rust module preference

Fixed
~~~~~

* Python thumbnail generation progress calculation (now shows correct 88% at Level 1 completion)
* Settings not persisting when "Use Rust module" checkbox changed
* AttributeErrors in Python thumbnail generation
* Progress bar showing incorrect percentages

Changed
~~~~~~~

* Simplified progress tracking architecture (removed callback-based approach)
* Weight calculation now reflects actual data volume ratio (64:8:1)
* Direct signal-based progress updates via ProgressManager

[0.2.3-alpha.1] - 2025-09-27
-----------------------------

Added
~~~~~

* Multi-level LoD pyramid thumbnail generation
* Rust-based high-performance thumbnail module
* Comprehensive testing infrastructure

[0.2.2] - 2025-09-08
--------------------

Added
~~~~~

**Phase 1: UI/UX Improvements**

* Simple linear progress tracking with moving average ETA (``SimpleProgressTracker``)
* Non-blocking 3D mesh generation using background threads
* User-friendly error messages with solutions (``ErrorMessageBuilder``)
* Complete internationalization foundation (``TranslationManager``)
* Comprehensive keyboard shortcuts system (``ShortcutManager``)
* Rich HTML tooltips with shortcuts and descriptions (``TooltipManager``)
* Keyboard shortcuts help dialog

**Phase 2: Settings Management**

* YAML-based settings management (``SettingsManager``)
* Comprehensive settings GUI with 5 tabs:

  * General: Language, theme, window preferences
  * Thumbnails: Size, sample, compression settings
  * Processing: Threads, memory, Rust module
  * Rendering: Threshold, anti-aliasing, FPS
  * Advanced: Logging, export options

* Settings import/export functionality
* Reset to defaults feature
* Platform-independent configuration storage

**Phase 3: Documentation**

* Google-style docstrings for all public APIs
* Sphinx-based API documentation
* Comprehensive user guide
* Developer guide with contribution guidelines
* Installation guide for multiple platforms

Changed
~~~~~~~

* Migrated from QSettings to YAML-based configuration
* Replaced 3-stage progress sampling with simple linear tracking
* Improved progress ETA accuracy with weighted calculations
* Updated all core modules with comprehensive docstrings

Removed
~~~~~~~

* QSettings-based configuration (replaced with YAML)
* Old PreferencesDialog (replaced with SettingsDialog)
* Settings migration code (not needed for fresh installations)
* Complex 3-stage progress sampling

Fixed
~~~~~

* Thread safety issues in thumbnail generation
* Progress tracking inaccuracies
* UI blocking during 3D mesh generation

Security
~~~~~~~~

* Implemented secure file validation (``SecureFileValidator``)
* Added path traversal attack prevention
* Whitelist-based file extension validation

Performance
~~~~~~~~~~~

* 10-50x faster thumbnail generation with Rust module
* Optimized progress tracking with moving averages
* Non-blocking UI operations

[0.2.1] - 2025-09-08
--------------------

Added
~~~~~

* Initial modular architecture
* Core business logic extraction
* Basic thumbnail generation
* 3D visualization with Marching Cubes
* Image stack cropping and export

[0.2.0] - 2025-09-06
--------------------

Added
~~~~~

* Initial release
* Basic CT image loading
* Thumbnail generation (Python only)
* Simple 3D visualization

Notes
-----

Version Numbering
~~~~~~~~~~~~~~~~~

* **Major version (X.0.0)**: Incompatible API changes
* **Minor version (0.X.0)**: New features, backward compatible
* **Patch version (0.0.X)**: Bug fixes, backward compatible

Release Schedule
~~~~~~~~~~~~~~~~

* Major releases: Yearly
* Minor releases: Quarterly
* Patch releases: As needed

Support Policy
~~~~~~~~~~~~~~

* Latest major version: Full support
* Previous major version: Security fixes only
* Older versions: No support

Migration Guides
~~~~~~~~~~~~~~~~

See the developer guide for migration instructions when upgrading between major versions.
