# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SuperEnalotto v8.0"""

import os
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve()

a = Analysis(
    [str(PROJECT_ROOT / 'gateway' / '__main__.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / 'web'), 'web'),
        (str(PROJECT_ROOT / 'superenalotto.csv'), '.'),
        (str(PROJECT_ROOT / 'config.json'), '.'),
        (str(PROJECT_ROOT / 'icon.ico'), '.'),
    ],
    hiddenimports=['gateway', 'gateway.engine', 'gateway.server'],
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
    name='SuperEnalotto',
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
    icon=str(PROJECT_ROOT / 'icon.ico'),
)
