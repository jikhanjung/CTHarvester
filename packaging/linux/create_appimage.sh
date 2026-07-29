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
# 64x64, not 256x256: that is the largest icon in the tree, and declaring a
# size the file does not have makes desktops scale it wrongly.
mkdir -p "${APPDIR}/usr/share/icons/hicolor/64x64/apps"

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

# Copy icon.
#
# This used to look for ${PROJECT_ROOT}/icon.png and
# ${PROJECT_ROOT}/CTHarvester_64.png. Both live under resources/icons/, so
# neither path has ever existed and every AppImage built so far fell through to
# the placeholder branch below and shipped a 1x1 transparent pixel as its icon.
# Confirmed by extracting the v0.2.3-beta.4 AppImage: its CTHarvester.png is 69
# bytes, 1x1.
#
# The placeholder is gone with it. A missing icon is a packaging error, and a
# build that quietly substitutes an invisible one is how this went unnoticed
# across every release.
ICON_SRC="${PROJECT_ROOT}/resources/icons/CTHarvester_64_2.png"
if [ ! -f "${ICON_SRC}" ]; then
    echo "Error: icon not found at ${ICON_SRC}"
    exit 1
fi
cp "${ICON_SRC}" "${APPDIR}/usr/share/icons/hicolor/64x64/apps/CTHarvester.png"
cp "${ICON_SRC}" "${APPDIR}/CTHarvester.png"
echo "Icon: ${ICON_SRC} ($(stat -c %s "${ICON_SRC}") bytes)"

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
    # --comp xz rather than the gzip default. Measured on the v0.2.3-beta.4
    # payload (349 MiB uncompressed): gzip 124.2 MiB, xz 102.6 MiB -- 18% off
    # the download for a squashfs that every type-2 AppImage runtime can mount.
    # zstd compresses to 111.6 MiB and decompresses faster, but appimagetool
    # rejects anything other than gzip or xz (src/appimagetool.c), so it is not
    # an option here.
    #
    # The cost is startup: xz decompresses more slowly, and the runtime pages
    # the filesystem in on demand. If launch time becomes the complaint rather
    # than download size, gzip is the one-word revert.
    ARCH=x86_64 appimagetool --comp xz "${APPDIR}" "CTHarvester-Linux-${VERSION}.AppImage"
else
    echo "Error: appimagetool not found. Please install it first."
    exit 1
fi

# Make the AppImage executable
chmod +x "CTHarvester-Linux-${VERSION}.AppImage"

echo "AppImage created successfully: CTHarvester-Linux-${VERSION}.AppImage"
echo "You can test it with: ./CTHarvester-Linux-${VERSION}.AppImage"
