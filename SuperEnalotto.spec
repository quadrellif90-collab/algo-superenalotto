# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec per SuperEnalotto v8.3 (pywebview, portable, Documents/SuperEnalotto)"""

from pathlib import Path

PROJECT_ROOT = Path('.').resolve()

datas = []
for f in ['superenalotto.csv', 'config.json', 'icon.ico', 'tracking.csv']:
    p = PROJECT_ROOT / f
    if p.exists():
        datas.append((str(p), '.'))
# cartella web indispensabile per il frontend
web_dir = PROJECT_ROOT / 'web'
if web_dir.exists():
    datas.append((str(web_dir), 'web'))

a = Analysis(
    [str(PROJECT_ROOT / 'launcher.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'gateway',
        'gateway.engine',
        'gateway.server',
        'ctypes',
        'msvcrt',
        'ssl',
        'urllib.request',
        'urllib.error',
        'urllib.parse',
        'threading',
        'json',
        'sqlite3',
        'csv',
        'datetime',
        'collections',
        'random',
        'webview',
        'webview.platforms.winforms',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'icon.ico'),
)
