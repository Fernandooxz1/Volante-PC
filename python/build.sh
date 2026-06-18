#!/bin/bash
# =============================================================================
# Script de compilación de Volante PC - App Nativa para Linux
# Usa PyInstaller para generar un binario ejecutable independiente.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activar entorno virtual si existe para evitar errores de PEP 668 en Linux
if [ -d "venv" ]; then
    echo "Activando entorno virtual local (venv)..."
    source venv/bin/activate
fi

echo "============================================="
echo "  VOLANTE PC - Compilación de App Nativa"
echo "============================================="

# Verificar dependencias
echo ""
echo "[1/4] Verificando dependencias de compilación..."

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 no está instalado."
    exit 1
fi

# Verificar que pyinstaller esté instalado
if ! python3 -m PyInstaller --version &> /dev/null; then
    echo "PyInstaller no encontrado. Instalando..."
    pip install pyinstaller
fi

# Verificar que pywebview esté instalado
python3 -c "import webview" 2>/dev/null || {
    echo "pywebview no encontrado. Instalando..."
    pip install pywebview
}

# Verificar dependencias GTK para pywebview en Linux
echo "[2/4] Verificando dependencias del sistema (GTK + WebKit)..."
python3 -c "
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2
print('  GTK3 + WebKit2 4.1: OK')
" 2>/dev/null || {
    # Intentar con WebKit2 4.0
    python3 -c "
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2
print('  GTK3 + WebKit2 4.0: OK')
" 2>/dev/null || {
        echo ""
        echo "ERROR: No se encontraron las dependencias de GTK/WebKit."
        echo "Instálalas con:"
        echo "  Ubuntu/Debian: sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1 gir1.2-gtk-3.0"
        echo "  Fedora:        sudo dnf install python3-gobject webkit2gtk4.1"
        echo "  Arch:          sudo pacman -S python-gobject webkit2gtk-4.1"
        exit 1
    }
}

# Compilar con PyInstaller
echo "[3/4] Compilando con PyInstaller..."
echo ""

python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name "VolantePC" \
    --add-data "web:web" \
    --add-data "config_volante.json:." \
    --clean \
    --noconfirm \
    app_nativa.py

echo ""
echo "[4/4] Copiando configuración inicial..."

# Copiar config al directorio de distribución
if [ -f "config_volante.json" ]; then
    cp config_volante.json dist/config_volante.json
    echo "  config_volante.json copiado a dist/"
fi

echo ""
echo "============================================="
echo "  ¡COMPILACIÓN EXITOSA!"
echo "============================================="
echo ""
echo "El ejecutable se encuentra en:"
echo "  $SCRIPT_DIR/dist/VolantePC"
echo ""
echo "Para ejecutarlo:"
echo "  cd dist && ./VolantePC"
echo ""
echo "Para crear un acceso directo en el escritorio,"
echo "copia el archivo .desktop al directorio de aplicaciones:"
echo "  cp volante-pc.desktop ~/.local/share/applications/"
echo ""
