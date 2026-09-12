@echo off
setlocal enabledelayedexpansion
title Instalador de Volante-PC para Windows

echo =======================================================================
echo          VOLANTE-PC // INSTALADOR AUTOMATICO PARA WINDOWS
echo =======================================================================
echo.

:: 1. Comprobar instalacion de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python en el sistema.
    echo Por favor descarga e instala Python 3.10 o superior desde:
    echo   https://www.python.org/downloads/
    echo IMPORTANTE: Marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo [*] %PY_VER% detectado.

:: 2. Crear y configurar entorno virtual
if not exist "venv" (
    echo [*] Creando entorno virtual (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo [*] Entorno virtual existente detectado.
)

:: 3. Instalar dependencias
echo [*] Actualizando pip e instalando dependencias (PyQt6, pyserial, vgamepad)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al instalar las dependencias de requirements.txt.
    pause
    exit /b 1
)
echo [*] Dependencias instaladas correctamente.

:: 4. Verificar e instalar ViGEmBus (Driver Xbox 360)
echo [*] Verificando controlador ViGEmBus (Xbox 360 virtual)...
set DRIVER_EXISTS=0
if exist "%SystemRoot%\System32\drivers\ViGEmBus.sys" set DRIVER_EXISTS=1
if exist "%SystemRoot%\Sysnative\drivers\ViGEmBus.sys" set DRIVER_EXISTS=1

if "!DRIVER_EXISTS!"=="0" (
    echo [!] ViGEmBus no detectado. Iniciando instalacion silenciosa del controlador...
    if exist "windows\drivers\ViGEmBus_Setup.exe" (
        start /wait "" "windows\drivers\ViGEmBus_Setup.exe" /passive /norestart
        echo [*] Controlador ViGEmBus instalado.
    ) else (
        echo [AVISO] No se encontro windows\drivers\ViGEmBus_Setup.exe.
        echo Puedes descargarlo desde: https://github.com/nefarius/ViGEmBus/releases
    )
) else (
    echo [*] Controlador ViGEmBus detectado en el sistema.
)

:: 5. Crear acceso directo en el Escritorio
echo [*] Creando acceso directo en el Escritorio...
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Volante-PC.lnk')); " ^
    "$s.TargetPath = [System.IO.Path]::Combine('%SCRIPT_DIR%', 'venv\Scripts\pythonw.exe'); " ^
    "$s.Arguments = '\"' + [System.IO.Path]::Combine('%SCRIPT_DIR%', 'main.py') + '\"'; " ^
    "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
    "$s.IconLocation = [System.IO.Path]::Combine('%SCRIPT_DIR%', 'volante-pc.ico'); " ^
    "$s.Description = 'Volante-PC Simracing Controller'; " ^
    "$s.Save()"

if %errorlevel% equ 0 (
    echo [*] Acceso directo 'Volante-PC' creado con exito en el Escritorio.
) else (
    echo [AVISO] No se pudo crear el acceso directo de forma automatica.
)

echo.
echo =======================================================================
echo  INSTALACION COMPLETADA CON EXITO
echo =======================================================================
echo  1. Conecta tu Arduino UNO por USB a la PC.
echo  2. Haz doble clic en el acceso directo 'Volante-PC' en tu Escritorio.
echo =======================================================================
echo.
pause
