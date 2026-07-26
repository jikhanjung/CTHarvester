# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['CTHarvester.py'],
    pathex=[],
    binaries=[],
    datas=[('*.png', '.'), ('*.qm', '.')],
    hiddenimports=[
        # PyOpenGL picks its backend at runtime through OpenGL.plugins, importing
        # the module by dotted name. PyInstaller's static analysis cannot see
        # that, so without these the frozen build dies during import with
        # "TypeError: 'NoneType' object is not callable" from
        # OpenGL/platform/__init__.py's _load(). All backends are listed because
        # one spec builds all three OSes.
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CTHarvester',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['CTHarvester_48_2.png'],
)
