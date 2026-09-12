@echo off
setlocal enabledelayedexpansion
title Compilar Volante-PC para Windows

echo =======================================================================
echo          COMPILACION DE VOLANTE-PC PARA WINDOWS
echo =======================================================================
echo.

:: 1. Instalar herramientas de compilacion
echo [*] Instalando dependencias de compilacion...
pip install -r ..\requirements.txt pyinstaller pillow cairosvg --quiet

:: 2. Generar icono si no existe
if not exist "..\volante-pc.ico" (
    echo [*] Generando volante-pc.ico...
    python -c "import cairosvg; from PIL import Image; import io; png_data = cairosvg.svg2png(url='..\volante-pc.svg', output_width=256, output_height=256); img = Image.open(io.BytesIO(png_data)); img.save('..\volante-pc.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])"
)

:: 3. Compilar con PyInstaller
echo [*] Compilando ejecutable con PyInstaller...
cd ..
pyinstaller --clean -y VolantePC.spec
if %errorlevel% neq 0 (
    echo [ERROR] Error durante la ejecucion de PyInstaller.
    pause
    exit /b 1
)

:: 4. Compilar instalador con Inno Setup si esta disponible
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo [*] Inno Setup detectado. Compilando instalador VolantePC_Setup.exe...
    %ISCC% windows\installer.iss
    if %errorlevel% equ 0 (
        echo.
        echo [*] EXITO: Instalador generado en dist_installer\VolantePC_Setup.exe
    ) else (
        echo [AVISO] Hubo un error al compilar el instalador con Inno Setup.
    )
) else (
    echo.
    echo [*] Inno Setup 6 no esta instalado en la ruta estandar.
    echo [*] Los archivos listos para ejecutar estan en la carpeta 'dist\VolantePC'.
    echo [*] Puedes instalar Inno Setup desde https://jrsoftware.org/isdl.php para generar el instalador .exe
)

echo.
pause
