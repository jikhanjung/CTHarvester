#!/bin/bash

# CTHarvester AppImage creation script
# Usage: ./create_appimage.sh [version]

VERSION=${1:-"dev"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build_linux"
APPDIR="${BUILD_DIR}/AppDir"

echo "Creating CTHarvester AppImage version: ${VERSION}"
echo "Project root: ${PROJECT_ROOT}"

# Create build directory
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# Clean previous builds
rm -rf AppDir
rm -f *.AppImage

# Create AppDir structure
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# Copy the PyInstaller output
if [ -d "${PROJECT_ROOT}/dist/CTHarvester" ]; then
    echo "Copying onedir build from dist/CTHarvester..."
    cp -r "${PROJECT_ROOT}/dist/CTHarvester/"* "${APPDIR}/usr/bin/"
else
    echo "Error: dist/CTHarvester not found. Please run 'python build.py --onedir' first."
    exit 1
fi

# Ensure the main executable exists and is executable
if [ -f "${APPDIR}/usr/bin/CTHarvester" ]; then
    chmod +x "${APPDIR}/usr/bin/CTHarvester"
else
    echo "Error: CTHarvester executable not found in dist/"
    exit 1
fi

# Copy icon
if [ -f "${PROJECT_ROOT}/icon.png" ]; then
    cp "${PROJECT_ROOT}/icon.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/CTHarvester.png"
    cp "${PROJECT_ROOT}/icon.png" "${APPDIR}/CTHarvester.png"
elif [ -f "${PROJECT_ROOT}/CTHarvester_64.png" ]; then
    cp "${PROJECT_ROOT}/CTHarvester_64.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/CTHarvester.png"
    cp "${PROJECT_ROOT}/CTHarvester_64.png" "${APPDIR}/CTHarvester.png"
else
    echo "Warning: No icon file found, creating placeholder..."
    # Create a minimal placeholder icon
    echo -e '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05|%\xb6b\x00\x00\x00\x00IEND\xaeB`\x82' > "${APPDIR}/CTHarvester.png"
fi

# Create desktop entry
cat > "${APPDIR}/usr/share/applications/CTHarvester.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=CTHarvester
Comment=CT Image Stack Processing Tool
Exec=CTHarvester %F
Icon=CTHarvester
Categories=Education;Science;Graphics;
Terminal=false
StartupNotify=true
MimeType=image/bmp;image/jpeg;image/png;image/tiff;
EOF

# Copy desktop entry to AppDir root for AppImage
cp "${APPDIR}/usr/share/applications/CTHarvester.desktop" "${APPDIR}/CTHarvester.desktop"

# Create AppRun script with proper environment setup
cat > "${APPDIR}/AppRun" << 'EOF'
#!/bin/bash
set -e

# Get the directory where this AppRun script is located
HERE="$(dirname "$(readlink -f "${0}")")"

# Setup environment for the bundled application
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Python environment
export PYTHONHOME="${HERE}/usr"
export PYTHONPATH="${HERE}/usr/lib/python3.12/site-packages:${PYTHONPATH}"

# Qt/OpenGL environment
export QT_PLUGIN_PATH="${HERE}/usr/plugins"
export QML2_IMPORT_PATH="${HERE}/usr/qml"

# Mesa/OpenGL fallback for systems without proper OpenGL
export LIBGL_ALWAYS_SOFTWARE=1

# Disable Qt's built-in high DPI scaling (can cause issues)
export QT_AUTO_SCREEN_SCALE_FACTOR=0

# Execute the main application
exec "${HERE}/usr/bin/CTHarvester" "$@"
EOF

chmod +x "${APPDIR}/AppRun"

# Check for required libraries and copy them if needed
echo "Checking for required libraries..."

# Function to copy library and its dependencies
copy_deps() {
    local lib=$1
    local dest=$2

    if [ -f "$lib" ]; then
        cp -L "$lib" "$dest" 2>/dev/null || true

        # Get dependencies
        ldd "$lib" 2>/dev/null | grep "=> /" | awk '{print $3}' | while read dep; do
            if [ -f "$dep" ] && [ ! -f "$dest/$(basename $dep)" ]; then
                cp -L "$dep" "$dest" 2>/dev/null || true
            fi
        done
    fi
}

# Copy system libraries that might be missing
for lib in /usr/lib/x86_64-linux-gnu/libGL.so* \
           /usr/lib/x86_64-linux-gnu/libGLU.so* \
           /usr/lib/x86_64-linux-gnu/libglut.so* \
           /usr/lib/x86_64-linux-gnu/libxcb*.so* \
           /usr/lib/x86_64-linux-gnu/libX*.so*; do
    copy_deps "$lib" "${APPDIR}/usr/lib"
done

# Create the AppImage
echo "Creating AppImage..."
if command -v appimagetool >/dev/null 2>&1; then
    ARCH=x86_64 appimagetool "${APPDIR}" "CTHarvester-Linux-${VERSION}.AppImage"
else
    echo "Error: appimagetool not found. Please install it first."
    exit 1
fi

# Make the AppImage executable
chmod +x "CTHarvester-Linux-${VERSION}.AppImage"

echo "AppImage created successfully: CTHarvester-Linux-${VERSION}.AppImage"
echo "You can test it with: ./CTHarvester-Linux-${VERSION}.AppImage"
