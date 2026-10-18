# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('keyboard')
hiddenimports += [
    'pyautogui',
    'pyautogui._pyautogui_win',
    'pyscreeze',
    'pytweening',
    'pymsgbox',
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'win32gui',
    'win32con',
    'win32process',
    'win32api',
    'pywintypes',
]


a = Analysis(
    ['Ascension_Macro.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AscensionMacro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
