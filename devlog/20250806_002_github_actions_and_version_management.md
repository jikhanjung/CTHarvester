# GitHub Actions CI/CD Setup, Version Management, and UI Enhancements

## Date: 2025-08-06

## Overview
Comprehensive CI/CD pipeline setup with GitHub Actions, centralized version management system implementation, and UI improvements including Info Dialog addition for CTHarvester project.

## Major Changes

### 1. GitHub Actions Workflows Setup

#### Created Workflows
- **`.github/workflows/test.yml`** - Automated testing pipeline
  - Runs on main/develop branches and PRs
  - Tests on Python 3.12 and 3.13
  - Includes Qt/OpenGL dependencies for GUI testing
  - Uses xvfb for headless GUI testing

- **`.github/workflows/build.yml`** - Development build pipeline
  - Triggers on main branch pushes only (not on tags)
  - Builds for Windows, macOS, and Linux
  - Creates development builds with build numbers

- **`.github/workflows/release.yml`** - Release pipeline
  - Triggers only on version tags (v*.*.*)
  - Creates official releases with installers
  - Automatically uploads release assets to GitHub

#### Additional GitHub Configuration
- **`.github/dependabot.yml`** - Automated dependency updates
- **`.github/PULL_REQUEST_TEMPLATE.md`** - Standardized PR template

### 2. Version Management System

#### Version Files
- **`version.py`** - Single source of truth for version (currently 0.2.0)
  ```python
  __version__ = "0.2.0"
  __version_info__ = tuple(map(int, __version__.split('.')))
  ```

- **`bump_version.py`** - Version management utility
  - Supports major/minor/patch version bumps
  - Updates version.py automatically
  - Optional git tag creation
  - Changelog management

#### Version Integration
- Modified `CTHarvester.py` to import version from `version.py`
- Updated InfoDialog to display dynamic version
- Version automatically injected into builds

### 3. Build System Enhancement

#### Build Automation
- **`build.py`** - Unified build script
  - PyInstaller executable generation
  - InnoSetup installer creation (Windows)
  - Template-based ISS file generation
  - Build number support from CI/CD

#### InnoSetup Configuration
- **`InnoSetup/CTHarvester.iss.template`** - Template with `{{VERSION}}` placeholder
- Dynamic ISS generation at build time
- Installation under `PaleoBytes\CTHarvester` directory
- Consistent with Modan2 project structure

### 4. UI Improvements

#### Info Dialog Addition
- Created `InfoDialog` class for application information
- Added info button with `info.png` icon
- Displays version, copyright, and GitHub link
- Button positioned next to preferences button

#### Bug Fixes
- Fixed cursor state issue when opening empty directories
  - Added `QApplication.restoreOverrideCursor()` before early return
  - Added warning message for directories without valid images
  - Imported QMessageBox for warning dialogs

### 5. Test Infrastructure

#### Basic Test Suite
- **`tests/test_basic.py`** - Foundation tests
  - Module import verification
  - Dependency checking (PyQt5, PIL, numpy, scipy, pymcubes)
- **`tests/__init__.py`** - Test package initialization

### 6. Project Configuration

#### Requirements Management
- **`requirements.txt`** - Python dependencies
  ```
  pyqt5
  pyopengl
  pyopengl-accelerate
  superqt
  pillow
  numpy
  pymcubes
  scipy
  ```

#### Licensing
- **`LICENSE`** - MIT License
- **`icon.ico`** - Application icon placeholder

### 7. Workflow Optimization (Following Modan2 Pattern)

#### Clear Workflow Separation
- **test.yml**: All code changes testing
- **build.yml**: Main branch development builds (removed tag trigger)
- **release.yml**: Version tag releases only

#### Template Processing Improvement
- Moved template processing into `build.py`
- Removed separate `generate_iss.py` file
- Creates temporary ISS files during build
- Automatic cleanup after build completion

## Technical Details

### CI/CD Pipeline Flow
1. **Development**: Push to main → test.yml + build.yml
2. **Release**: Tag push (v*.*.*) → release.yml only
3. No duplicate builds on version tags

### Build Process Flow
1. `build.py` executes
2. `prepare_inno_setup_template()` processes template
3. Temporary ISS file created with version injected
4. PyInstaller builds executable
5. InnoSetup creates installer (Windows)
6. Temporary files cleaned up

### Version Management Flow
1. Edit version using `bump_version.py [major|minor|patch]`
2. Version updated in `version.py`
3. All builds automatically use new version
4. Optional git tag and changelog update

## Files Modified
- CTHarvester.py (version import, info dialog, cursor fix)
- Created entire .github/ directory structure
- Created build system files (build.py, bump_version.py, version.py)
- Created InnoSetup template and configuration
- Created test infrastructure

## Files Created
- `.github/workflows/test.yml`
- `.github/workflows/build.yml`
- `.github/workflows/release.yml`
- `.github/dependabot.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `version.py`
- `bump_version.py`
- `build.py`
- `InnoSetup/CTHarvester.iss.template`
- `tests/test_basic.py`
- `tests/__init__.py`
- `LICENSE`
- `icon.ico`

## Files Removed
- `generate_iss.py` (functionality moved to build.py)

## Next Steps
- Replace `icon.ico` with actual application icon
- Add more comprehensive tests
- Consider adding code coverage reporting
- Add actual sample data for distribution
- Update GitHub repository URL references

## Notes
- Build system now consistent with Modan2 project
- PaleoBytes product family structure maintained
- Korean language support included in InnoSetup
- Python 3.12 and 3.13 compatibility tested

## Status
✅ Completed - Full CI/CD pipeline operational with centralized version management
