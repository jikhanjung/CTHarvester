# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# SPECPATH is injected by PyInstaller and is this file's directory, i.e. the
# project root. Putting it on sys.path lets the bundle metadata below come from
# version.py and config/constants.py rather than being restated here, where it
# would drift.
sys.path.insert(0, SPECPATH)

from config.constants import PROGRAM_COPYRIGHT, PROGRAM_NAME
from version import __version_info__

# CFBundleShortVersionString must be one to three period-separated integers.
# version.py carries a semver string that is usually a pre-release
# ("0.2.3-beta.4"), which is not a legal value: macOS mis-sorts it and
# notarisation rejects it. The numeric release goes here and the CI build
# number goes in CFBundleVersion, which is the split macOS expects anyway --
# one user-visible version, one monotonic build counter.
BUNDLE_SHORT_VERSION = ".".join(str(part) for part in __version_info__)
BUNDLE_VERSION = os.environ.get("BUILD_NUMBER", "")
if not BUNDLE_VERSION.isdigit():
    # build.py defaults BUILD_NUMBER to the string "local" for developer
    # builds, and CFBundleVersion has the same integers-only rule as above.
    BUNDLE_VERSION = "0"

block_cipher = None


a = Analysis(
    ['CTHarvester.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/icons/*.png', 'resources/icons'),
        ('resources/translations/*.qm', 'resources/translations'),
    ],
    hiddenimports=[
        'superqt', 'PIL', 'PIL.Image', 'scipy', 'scipy.ndimage', 'mcubes', 'numpy',
        'OpenGL', 'OpenGL.GL', 'OpenGL.GLUT', 'OpenGL.GLU',
        # PyOpenGL picks its backend at runtime through OpenGL.plugins, importing
        # the module by dotted name. PyInstaller's static analysis cannot see
        # that, so none of the backends were bundled and the frozen build died
        # during import with "TypeError: 'NoneType' object is not callable" from
        # OpenGL/platform/__init__.py's _load(). All backends are listed rather
        # than the current platform's, because one spec builds all three OSes.
        'OpenGL.platform.glx',      # linux, posix, x11
        'OpenGL.platform.egl',      # wayland, xwayland
        'OpenGL.platform.osmesa',   # software rendering
        'OpenGL.platform.win32',    # nt
        'OpenGL.platform.darwin',   # macOS
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CTHarvester',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX compression to avoid false positives
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/icons/CTHarvester_48_2.png'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # Disable UPX compression to avoid false positives
    upx_exclude=[],
    name='CTHarvester',
)

# macOS .app bundle. BUNDLE returns immediately on Windows and Linux, so this
# needs no platform guard and the one spec still builds all three OSes.
#
# Before this existed, reusable_build.yml assembled the bundle by hand with
# `mkdir Contents/MacOS` + `cp -r dist/*`, which was wrong twice over: the glob
# matched the destination's own .app so the payload was copied into itself
# (the v0.2.3-beta.4 DMG shipped the application twice, 553.9 MB of content for
# a ~277 MB build), and with no Info.plist the executable macOS looks for at
# Contents/MacOS/CTHarvester was the COLLECT *directory*, not a program.
app = BUNDLE(
    coll,
    name=f'{PROGRAM_NAME}.app',
    # The largest icon in the tree is 64x64. PyInstaller converts it to .icns
    # via Pillow, but macOS wants up to 1024x1024 -- the Dock and Finder will
    # upscale this. Worth replacing with a proper multi-resolution source.
    icon='resources/icons/CTHarvester_64_2.png',
    bundle_identifier='com.paleobytes.ctharvester',
    version=BUNDLE_SHORT_VERSION,
    info_plist={
        'CFBundleName': PROGRAM_NAME,
        'CFBundleDisplayName': PROGRAM_NAME,
        'CFBundleShortVersionString': BUNDLE_SHORT_VERSION,
        'CFBundleVersion': BUNDLE_VERSION,
        'NSHumanReadableCopyright': PROGRAM_COPYRIGHT,
        # Without this macOS renders the window at 1x and upscales it, which on
        # a Retina display makes the UI and the CT slice itself look blurry --
        # bad for an application whose whole job is looking at images closely.
        'NSHighResolutionCapable': True,
    },
)
