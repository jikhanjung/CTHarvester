Changelog
=========

All notable changes to CTHarvester will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

[1.0.0] - 2025-09-30
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

[0.9.0] - 2025-09-15
--------------------

Added
~~~~~

* Initial modular architecture
* Core business logic extraction
* Basic thumbnail generation
* 3D visualization with Marching Cubes
* Image stack cropping and export

[0.8.0] - 2025-09-01
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