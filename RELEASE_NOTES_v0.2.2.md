# 🚀 CTHarvester v0.2.2 Release

## ✨ Major Improvements

### 📝 **Centralized Logging System**
- Implemented professional logging infrastructure with CTLogger module
- Daily log rotation with date-based filenames for better organization
- Logs stored in user profile directory (`~/PaleoBytes/CTHarvester/logs/`)
- UTF-8 encoding support for international characters
- Automatic fallback to console output if file creation fails
- Separate error stream to console for critical issues

### 🛡️ **Comprehensive Error Handling**
- Added robust try-catch blocks throughout the application
- Protected all file I/O operations from crashes
- Safe image processing with proper error recovery
- Bulletproof 3D scene manipulations
- Graceful handling of settings load/save failures
- Improved stability for volume and mesh processing

### 🔍 **Enhanced Debugging and Monitoring**
- Replaced all print statements with structured logger calls
- Four-level logging hierarchy:
  - Debug: Verbose operational details
  - Info: Normal application flow
  - Warning: Potential issues that don't stop execution
  - Error: Critical problems with full exception details
- Better traceability for troubleshooting issues

## 🐛 Bug Fixes

### **Critical IndexError Resolution**
- Fixed crash when adjusting range slider in 3D view
- Added comprehensive boundary checks for array access
- Validated index values before accessing level_info
- Protected against uninitialized data structures

### **Stability Improvements**
- Eliminated potential crashes from unhandled exceptions
- Fixed issues in file operations (open, save, export)
- Resolved image processing errors (thumbnails, screenshots)
- Corrected 3D operation failures (volume updates, mesh generation)
- Fixed settings persistence problems

## 📋 Technical Details

- **Logging Directory**: `~/PaleoBytes/CTHarvester/logs/`
- **Log Format**: `CTHarvester.YYYYMMDD.log`
- **Error Handling**: Comprehensive try-catch coverage
- **Compatibility**: All platforms (Windows, macOS, Linux)

## 📥 Installation

Download the appropriate file for your platform:
- **Windows**: `CTHarvester-Windows-Installer-*.zip` (contains installer)
- **macOS**: `CTHarvester-macOS-Installer-*.dmg`
- **Linux**: `CTHarvester-Linux-*.AppImage`

## 🔄 What's Changed Since v0.2.1

This release focuses on stability and reliability improvements. The new logging system provides better visibility into application behavior, while comprehensive error handling ensures the application remains stable even when encountering unexpected conditions.

### Key Improvements:
- **Reliability**: Application no longer crashes from unhandled exceptions
- **Debuggability**: Detailed logs help diagnose issues quickly
- **User Experience**: Graceful error recovery instead of abrupt crashes
- **Maintainability**: Structured logging makes development easier

## 📝 Notes

- Logs are automatically rotated daily to prevent disk space issues
- Old print statements have been completely replaced with proper logging
- Error messages now include full stack traces for debugging
- The application continues running even when non-critical errors occur

## 🙏 Acknowledgments

Thanks to all users who reported issues and helped improve CTHarvester's stability!

---

**Full Changelog**: https://github.com/jikhanjung/CTHarvester/compare/v0.2.1...v0.2.2