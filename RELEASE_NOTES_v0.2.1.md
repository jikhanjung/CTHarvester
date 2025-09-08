# 🚀 CTHarvester v0.2.1 Release

## ✨ Major Improvements

### 🔧 **Advanced CI/CD Pipeline**
- Implemented reusable build workflows for consistent cross-platform builds
- Added manual release action with custom version tagging
- Automated build numbering system for better tracking
- Support for Windows installer, macOS DMG, and Linux AppImage

### 📦 **Enhanced Version Management**
- Migrated to semantic versioning with full pre-release support (alpha, beta, rc)
- New `manage_version.py` utility with comprehensive version bumping commands
- Safe version parsing using `semver` library
- Complete version management documentation

### 🎨 **UI and Branding Updates**
- Added proper application icons for all platforms
- Dynamic copyright year display (© 2023-2024)
- Improved About dialog with automatic year updates

## 🐛 Bug Fixes

- **Windows**: Fixed Inno Setup installer build failures
- **Linux**: Resolved AppImage icon and desktop entry issues  
- **macOS**: Corrected DMG creation process
- **CI/CD**: Fixed YAML syntax errors in GitHub Actions
- **Build**: Resolved path resolution issues across all platforms

## 📋 Technical Details

- **Supported Platforms**: Windows, macOS, Linux
- **Build Formats**: 
  - Windows: Installer (exe) via Inno Setup
  - macOS: DMG disk image
  - Linux: AppImage
- **Version Format**: Semantic versioning with pre-release support
- **Build System**: PyInstaller with platform-specific packaging

## 📥 Installation

Download the appropriate file for your platform:
- **Windows**: `CTHarvester-Windows-Installer-*.zip` (contains installer)
- **macOS**: `CTHarvester-macOS-Installer-*.dmg`
- **Linux**: `CTHarvester-Linux-*.AppImage`

## 🔄 What's Changed Since v0.2.0

This release focuses on build system reliability and developer experience improvements. The new CI/CD pipeline ensures consistent builds across all platforms, while the enhanced version management system provides better control over releases.

### Key Changes:
- Complete overhaul of GitHub Actions workflows
- Migration from `bump_version.py` to `manage_version.py`
- Implementation of reusable build components
- Addition of proper application icons
- Dynamic copyright year calculation

## 📝 Notes

- First release with fully automated cross-platform builds
- Korean language support temporarily disabled in CI builds (can be enabled locally)
- All builds now include proper application icons

## 🙏 Acknowledgments

Thanks to all contributors and users for their feedback and support!

---

**Full Changelog**: https://github.com/jikhanjung/CTHarvester/compare/v0.2.0...v0.2.1