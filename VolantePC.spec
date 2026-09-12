# -*- mode: python ; coding: utf-8 -*-
"""
VolantePC.spec - Especificación PyInstaller para compilar Volante-PC en Windows.
Empaqueta el motor de 100 Hz, la interfaz gráfica PyQt6 Motorsport DDU,
y las bibliotecas DLL de emulación virtual Xbox 360 (vgamepad / ViGEmBus).
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all

# Recolectar todos los binarios, datos e importaciones ocultas de vgamepad
vg_datas, vg_binaries, vg_hidden = collect_all('vgamepad')

datas = [
    ('volante-pc.ico', '.'),
    ('volante-pc.png', '.'),
    ('volante-pc.svg', '.'),
] + vg_datas

binaries = vg_binaries

hiddenimports = [
    'serial',
    'serial.tools.list_ports',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'core',
    'ui',
] + vg_hidden

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy'],
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
    name='VolantePC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sin ventana de consola CMD en segundo plano
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='volante-pc.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VolantePC',
)
