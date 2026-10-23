# -*- mode: python ; coding: utf-8 -*-
# Сборка capt_print.exe из исходников этой папки (см. BUILD.txt).
# Build capt_print.exe from the sources in this folder (see BUILD.txt).
#   pyinstaller --clean capt_print.spec
import os
from PyInstaller.utils.hooks import collect_all

here = SPECPATH  # папка, где лежит этот файл / folder of this spec

datas = []
binaries = []
hiddenimports = []
for pkg in ('libusb_package', 'pypdfium2', 'PIL', 'windows_toasts'):
    # windows_toasts импортируется внутри try/except - без collect_all PyInstaller его не находит.
    # windows_toasts is imported inside try/except, so it must be collected explicitly.
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(here, 'capt_print_redmon.py')],
    pathex=[here],
    binaries=binaries,
    datas=datas,
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
    name='capt_print',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # без чёрного окна при печати / no console window while printing
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
