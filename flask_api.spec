# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],  # ← Ensure this points to the directory of app.py
    binaries=[],
    datas=[
        ('model_cache/*', 'model_cache'),  # Include Whisper cached models if used
    ],
  hiddenimports=[
    'whisper',
    'whisper.audio',
    'whisper.transcribe',
    'whisper.model',
    'whisper.decoding',
    'torch',
    'torchaudio',
    'numpy',
    'scipy',
    'pydub',
    'tqdm',
],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='flask_api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # ✅ Change to False to hide the terminal window
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='flask_api'
)
