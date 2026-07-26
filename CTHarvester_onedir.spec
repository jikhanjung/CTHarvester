# -*- mode: python ; coding: utf-8 -*-


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
