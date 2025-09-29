# Changelog

All notable changes to CTHarvester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).




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