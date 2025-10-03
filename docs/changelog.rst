Changelog
=========

All notable changes to CTHarvester will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

[0.2.3-beta.2] - 2025-10-03
---------------------------

Added
~~~~~

**Phase 3: Production Readiness - Error Handling & Logging**

* Performance logging utility (``utils/performance_logger.py``)

  * ``PerformanceTimer`` class for manual/context-manager timing
  * ``@log_performance`` decorator for automatic function timing
  * ``log_performance_context`` for custom context data
  * Structured logging with operation metadata

* Improved exception handling across all core modules

  * Specific exception types (MemoryError, OSError, FileNotFoundError, PermissionError)
  * Structured logging with ``exc_info=True`` for automatic traceback
  * Contextual information using ``extra_fields`` for better debugging
  * Better error diagnostics with file paths and operation context

**Phase 2: Type Safety & Testing Infrastructure**

* Protocol definitions for type safety (``core/protocols.py``)

  * ``ThumbnailParent`` protocol for parent objects
  * ``ProgressDialog`` protocol for progress dialog interface
  * Reduced ``type:ignore`` from 28 to 9 (68% reduction)

* Centralized test infrastructure (``tests/conftest.py``)

  * Shared fixtures: ``temp_image_dir``, ``temp_empty_dir``
  * Mock objects: ``MockProgressDialog``, ``MockLabel``, ``MockProgressBar``
  * Reduced code duplication by ~70 lines across test files

* Performance regression tests (``tests/test_performance.py``)

  * 12 benchmark tests for image processing, file I/O, memory usage
  * Performance baselines: downsample <0.1s, averaging <0.05s
  * Memory tracking for large image operations

Changed
~~~~~~~

* Exception handling now uses specific exception types instead of bare ``except Exception``
* Logging uses ``logger.exception()`` for automatic traceback instead of manual ``traceback.format_exc()``
* Test infrastructure centralized in ``conftest.py`` for better reusability
* Improved error messages with structured logging and extra context

Performance
~~~~~~~~~~~

* Performance bottleneck identification with ``@log_performance`` decorator
* Memory footprint tracking for large image operations
* Automatic timing for critical operations

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
