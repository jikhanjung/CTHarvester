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
    hiddenimports=['superqt', 'PIL', 'PIL.Image', 'scipy', 'scipy.ndimage', 'mcubes', 'numpy', 'OpenGL', 'OpenGL.GL', 'OpenGL.GLUT', 'OpenGL.GLU'],
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
    upx=False,  # Disable UPX compression to avoid false positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/icons/CTHarvester_48_2.png'],
)
