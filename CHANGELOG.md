# Changelog

All notable changes to CTHarvester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added
- **Comprehensive keyboard shortcuts system** (24 shortcuts)
  - File operations: Open directory (Ctrl+O), Save cropped (Ctrl+S), Export (Ctrl+E)
  - View operations: Screenshot (F12)
  - Navigation: Previous/Next image (Ctrl+Left/Right), First/Last (Ctrl+Home/End)
  - Crop operations: Load/Save crop (Ctrl+Shift+L/S), Reset crop (Ctrl+R)
  - Threshold operations: Load/Save threshold (Ctrl+Alt+L/S), Reset threshold (Ctrl+T)
  - Help: Shortcuts help (F1)
  - Settings: Open settings (Ctrl+,)
- **Complete tooltip coverage** (100% on interactive elements)
  - Rich HTML formatting with keyboard shortcuts
  - Consistent styling across all UI elements
- **Professional UI styling system**
  - 8px grid spacing system for consistency
  - Standardized button sizes (32px height, 32x32px icons)
  - Unified color palette (Primary, Danger, Success, Warning, Neutral)
  - Centralized style configuration (`config/ui_style.py`)
- **Enhanced progress feedback**
  - Remaining items counter
  - ETA calculation with sophisticated smoothing
  - Percentage progress display
  - Cancel functionality for long operations
- **Comprehensive user documentation** (2,500+ lines)
  - Troubleshooting guide with 25+ scenarios
  - FAQ with 60+ questions answered
  - Advanced features guide with detailed examples
  - Complete workflow documentation
- **Performance benchmarking infrastructure**
  - Standard benchmark scenarios (Small/Medium/Large/XLarge)
  - 4 performance tests with memory profiling
  - Performance thresholds and validation
  - CI/CD compatible quick tests
- **Stress testing suite** (9 tests)
  - Memory leak detection tests
  - Long-running operation stability tests
  - Resource cleanup verification
  - Concurrent batch processing tests
- **Error recovery testing** (18 tests)
  - File system error handling (permission, OS errors)
  - Image processing errors (corrupt, invalid format)
  - Network drive disconnection scenarios
  - Graceful degradation mechanisms
- **Developer documentation** (1,500+ lines)
  - Error recovery guide (650 lines)
  - Performance guide (850 lines)
  - Best practices and patterns
  - Troubleshooting guides

### Changed
- **UI/UX improvements**
  - Applied consistent 8px grid spacing throughout
  - Standardized button styling and sizing
  - Enhanced progress dialog with remaining items
  - Improved keyboard navigation
- **Documentation organization**
  - Restructured user guide sections
  - Added comprehensive developer guides
  - Created detailed troubleshooting sections
- **Test suite expansion**
  - Total tests: 1,150 (+18 from previous version)
  - Quick tests: 1,133 (< 1 minute)
  - Slow tests: 17 (> 1 minute)
  - Performance tests: 4
  - Stress tests: 9
  - Error recovery tests: 18
  - Coverage maintained at ~91%

### Performance
- **Benchmark results**:
  - Small dataset (10 images, 512×512, 8-bit): < 1s
  - Medium dataset (100 images, 1024×1024, 8-bit): ~7s
  - Large dataset (500 images, 2048×2048, 16-bit): ~188s (3 minutes)
  - Image resize: < 200ms per image
- **Memory efficiency**:
  - Small datasets: < 150 MB
  - Medium datasets: < 200 MB (with batching)
  - Large datasets: < 3 GB (with batching)
  - Memory cleanup: > 50% freed after operations
- **Processing speed**:
  - Thumbnail generation (Rust): ~50ms per image
  - Thumbnail generation (Python): ~100-200ms per image
  - Full processing: ~300-400ms per image
- **Robustness verified**:
  - No memory leaks detected
  - All resources properly cleaned up
  - Stable performance over long operations
  - Linear scaling with dataset size

### Technical Details
- **UI Infrastructure**:
  - `ui/setup/shortcuts_setup.py`: Keyboard shortcut management
  - `config/ui_style.py`: Centralized UI styling
  - `config/tooltips.py`: Tooltip management
  - `tests/test_ui_style.py`: 23 UI style tests
- **Performance Infrastructure**:
  - `tests/benchmarks/benchmark_config.py`: Benchmark scenarios
  - `tests/benchmarks/test_performance.py`: 4 performance tests
  - `tests/benchmarks/test_stress.py`: 9 stress tests
  - `tests/test_error_recovery.py`: 18 error recovery tests
- **Documentation**:
  - `docs/user_guide/troubleshooting.rst`: Troubleshooting guide
  - `docs/user_guide/faq.rst`: Frequently asked questions
  - `docs/user_guide/advanced_features.rst`: Advanced features
  - `docs/developer_guide/error_recovery.md`: Error recovery patterns
  - `docs/developer_guide/performance.md`: Performance characteristics



## [0.2.3-beta.1] - 2025-09-30

### Added
- **Comprehensive test suite** (195 tests with ~95% coverage)
  - Unit tests for core utilities, workers, image processing, security (186 tests)
  - Integration tests for thumbnail generation workflows (9 tests)
  - Test markers for unit, integration, slow, and Qt tests
- **CI/CD pipeline** with GitHub Actions
  - Automated testing on Python 3.12 and 3.13
  - Coverage reporting with Codecov integration
  - Automated builds and releases
- **Project retrospective document**
  - Comprehensive documentation of refactoring journey
  - Detailed test coverage expansion process
  - Lessons learned and best practices
- **Security validation module** (`security/file_validator.py`)
  - Directory traversal attack prevention
  - Path validation and sanitization
  - Secure file operations with FileSecurityError

### Changed
- **Major code refactoring** (Phase 1-4)
  - Modular architecture: config/, core/, ui/, utils/, security/
  - CTHarvester.py reduced from 4,840 lines to 151 lines (-96.6%)
  - Extracted 18 modules with clear separation of concerns
- **Documentation overhaul**
  - README.md expanded with testing section, project structure, contributing guide
  - README.ko.md synchronized with English version
  - Updated badges (Codecov, test count, Python 3.12+)
- **Memory management improvements**
  - Explicit resource cleanup (del statements)
  - Periodic garbage collection every 10 images
  - Try-finally blocks ensuring cleanup
- **Error handling enhancements**
  - Added traceback module import and usage
  - Comprehensive exception handling throughout
  - Finished signals guaranteed in all cases
- **Thread safety improvements**
  - Duplicate result processing prevention
  - Progress rate boundary validation
  - Single-thread strategy documented

### Fixed
- **Critical security vulnerabilities**
  - Directory traversal attack prevention
  - File path validation and sanitization
  - Null byte injection protection
  - Symbolic link traversal prevention
- **Memory leaks**
  - PIL Image objects now explicitly released
  - NumPy arrays properly cleaned up
  - Garbage collection triggered periodically
- **Pillow deprecation warnings** (147 warnings eliminated)
  - Removed deprecated `mode` parameter from Image.fromarray()
  - PIL now auto-detects mode from array dtype and shape
- **Import organization**
  - Added missing traceback module import
  - Updated import paths for new module structure

### Performance
- Test execution: 195 tests in ~2.5 seconds
- Code quality: 95% coverage for core utility modules
- Modules at 100% coverage: utils/common, utils/worker, utils/image_utils

### Technical Details
- **Test infrastructure**:
  - pytest 8.4.2 with pytest-cov, pytest-qt, pytest-timeout
  - AAA pattern (Arrange-Act-Assert)
  - Fixture-based test isolation
  - Platform-specific skip decorators
- **Module structure**:
  - config/: Global constants and configuration
  - core/: Business logic (progress, thumbnail generation)
  - ui/: User interface components (dialogs, widgets)
  - utils/: Reusable utility functions
  - security/: File validation and security checks
  - tests/: Comprehensive test suite
- **CI/CD workflows**:
  - test.yml: Automated testing with coverage
  - build.yml: Development builds on main
  - release.yml: Release builds on version tags


## [0.2.3-alpha.2] - 2025-09-29

### Changed
- Python fallback implementation simplified to use only PIL and NumPy
  - Removed tifffile and OpenCV dependencies for better compatibility
  - Single-threaded processing for predictable performance
  - Focus on code simplicity and maintainability as fallback solution

### Fixed
- Python thumbnail generation performance issues
  - Identified and documented np.array() conversion bottleneck
  - Reduced thread contention by using single thread
  - Improved logging to better track performance issues

### Performance
- Python fallback: ~25-30 minutes for 3000 images (acceptable for backup)
- Rust module remains primary solution: 2-3 minutes (10x faster)


## [0.2.3-alpha.1] - 2025-09-13

### Added
- Multithreading support for thumbnail generation
  - Parallel processing of multiple thumbnails
  - Improved performance for large image stacks

### Changed
- Improved thumbnail generation process
  - Better handling of bounding box scaling
  - More efficient image processing pipeline

### Fixed
- Bounding box scaling issues in thumbnail generation
- Windows Defender false positive by disabling UPX compression
- IndentationError issues in commented-out debug logs
- Thumbnail loading when minimum_volume is empty
- File path handling when loading existing thumbnails


## [0.2.2] - 2025-09-08

### Added
- Centralized logging system (CTLogger.py)
  - Daily log rotation with date-based filenames
  - Configurable log directory under user profile
  - UTF-8 encoding support for better compatibility
  - Automatic fallback to console output if file creation fails
  - Separate error stream to console for critical issues
- Comprehensive error handling throughout CTHarvester.py
  - Try-catch blocks for all file I/O operations
  - Error handling for image processing operations
  - Protected 3D scene manipulations
  - Safe settings load/save operations
  - Robust volume and mesh processing

### Changed
- Replaced all print statements with proper logger calls
  - Debug messages for verbose output
  - Info messages for normal operations
  - Warning messages for potential issues
  - Error messages with full exception details
- Improved error reporting with detailed exception logging

### Fixed
- IndexError in rangeSliderValueChanged when accessing level_info
  - Added boundary checks for array access
  - Validated curr_level_idx before use
  - Protected against uninitialized level_info
- Potential crashes from unhandled exceptions in:
  - File operations (open, save, export)
  - Image processing (thumbnail generation, screenshots)
  - 3D operations (volume updates, mesh generation)
  - Settings persistence


## [0.2.1] - 2025-09-08

### Added
- Comprehensive CI/CD pipeline with GitHub Actions
  - Reusable build workflow (`reusable_build.yml`) for consistent builds across platforms
  - Manual release action for creating releases with custom version tags
  - Support for pre-release versions (alpha, beta, rc)
  - Automated build number management
- Advanced version management system
  - New `manage_version.py` utility replacing `bump_version.py`
  - Semantic versioning with `semver` library support
  - Pre-release version support (alpha, beta, rc stages)
  - `VERSION_MANAGEMENT.md` documentation
- Proper application icons
  - Converted CTHarvester_64.png to icon.ico for Windows
  - Created icon.png for Linux AppImage builds
  - Added `convert_icon.py` utility for PNG to ICO conversion
- Dynamic copyright year display
  - Automatically updates copyright year in About dialog
  - Shows "© 2023-{current_year} Jikhan Jung"

### Changed
- Version management migrated from simple bump script to comprehensive semver-based system
- All GitHub Actions workflows now use centralized reusable build workflow
- Build artifacts properly named with version and build numbers
- Inno Setup configuration uses absolute paths for reliable builds
- Copyright display now uses dynamic year calculation

### Fixed
- Windows installer build issues
  - Corrected file paths for single-file PyInstaller builds
  - Fixed Inno Setup output directory path resolution
  - Disabled Korean language file for CI compatibility
- Linux AppImage build failures
  - Resolved missing icon file errors
  - Fixed desktop entry category validation
  - Always creates placeholder icon when needed
- GitHub Actions YAML syntax errors
  - Replaced heredoc syntax with echo commands
  - Fixed indentation and escaping issues
- Build path issues across all platforms

### Technical Details
- Build system improvements:
  - Windows: ZIP-packaged installer with Inno Setup
  - macOS: DMG creation for distribution
  - Linux: AppImage generation with proper desktop integration
- Version parsing now handles complex version strings safely
- All file paths converted to absolute paths during build process

## [0.2.0] - 2024-12-28

### Added
- Initial centralized version management through `version.py`
- Cross-platform build support (Windows, macOS, Linux)
- Basic GitHub Actions for automated builds

### Changed
- Version information now managed in single source of truth

### Fixed
- Version consistency across all build artifacts
