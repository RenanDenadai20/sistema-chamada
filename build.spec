# build.spec — PyInstaller spec para gerar o .exe standalone do Sistema de Chamada
# Uso: pyinstaller build.spec

import os
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'icones'), 'icones'),
        (str(ROOT / 'app_icon.ico'), '.'),
        (str(ROOT / 'app_icon.png'), '.'),
        (str(ROOT / 'dados' / 'dados.db'), 'dados_template'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtXml',
        'reportlab.graphics.shapes',
        'reportlab.pdfbase.cidfonts',
        'reportlab.pdfbase.ttfonts',
        'docx',
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
    name='SistemaChamada',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'app_icon.ico'),
)
