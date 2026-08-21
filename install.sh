#!/bin/bash
# =============================================================================
# Instalador automático de Volante PC para Linux
# =============================================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "======================================================"
echo "    🏎️  INSTALADOR DE VOLANTE PC (LINUX) 🏎️"
echo "======================================================"
echo ""

# 1. Configurar reglas de udev para uinput y Arduino Serial
echo "[1/5] Configurando permisos de sistema (udev)..."
if command -v sudo &> /dev/null; then
    echo "Configurando reglas udev para joystick virtual y puerto serie..."
    sudo tee /etc/udev/rules.d/99-volante-pc.rules > /dev/null << 'UDEV_EOF'
# Permiso para mando virtual uinput
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"

# Permiso para Arduino / conversores USB-Serie (CH340, FTDI, CP2102, ATmega16U2)
KERNEL=="ttyUSB*", MODE="0666", GROUP="uucp", TAG+="uaccess"
KERNEL=="ttyACM*", MODE="0666", GROUP="uucp", TAG+="uaccess"
UDEV_EOF

    sudo udevadm control --reload-rules && sudo udevadm trigger || true
    sudo modprobe uinput 2>/dev/null || true
    
    # Agregar usuario al grupo input si existe
    sudo usermod -aG input "$USER" 2>/dev/null || true
    # Agregar usuario al grupo serial correspondiente
    sudo usermod -aG dialout "$USER" 2>/dev/null || true
    sudo usermod -aG uucp "$USER" 2>/dev/null || true
    echo "  ✓ Reglas udev y permisos configurados."
else
    echo "  ⚠️ No se detectó sudo. Asegúrate de configurar permisos en /dev/uinput y /dev/ttyUSB* manualmente."
fi

# 2. Configurar entorno virtual de Python y dependencias
echo ""
echo "[2/5] Configurando entorno de Python y dependencias..."
if [ ! -d "python/venv" ]; then
    python3 -m venv --system-site-packages python/venv
fi

source python/venv/bin/activate
pip install -r python/requirements_nativa.txt pyinstaller

# 3. Compilar el binario ejecutable
echo ""
echo "[3/5] Compilando aplicación nativa..."
bash python/build.sh

# 4. Instalar ejecutable, icono y lanzador de escritorio
echo ""
echo "[4/5] Instalando en el sistema..."
mkdir -p ~/.local/bin ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps

# Copiar binario
cp python/dist/VolantePC ~/.local/bin/volante-pc
chmod +x ~/.local/bin/volante-pc

# Copiar icono
if [ -f "volante-pc.svg" ]; then
    cp volante-pc.svg ~/.local/share/icons/hicolor/scalable/apps/volante-pc.svg
fi

# Copiar lanzador .desktop
cat << 'DESKTOP_EOF' > ~/.local/share/applications/volante-pc.desktop
[Desktop Entry]
Type=Application
Version=1.0
Name=Volante PC
GenericName=Emulador de Volante de Carreras
Comment=Panel de calibración y emulador de volante con Arduino
Exec=env WEBKIT_DISABLE_DMABUF_RENDERER=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 /home/$USER/.local/bin/volante-pc
Icon=volante-pc
Terminal=false
Categories=Game;HardwareSettings;
Keywords=volante;wheel;racing;arduino;gamepad;xbox;joystick;simracing;
StartupNotify=true
DESKTOP_EOF

# Reemplazar variable $USER en el .desktop
sed -i "s|\$USER|$USER|g" ~/.local/share/applications/volante-pc.desktop
chmod +x ~/.local/share/applications/volante-pc.desktop

# 5. Actualizar base de datos de aplicaciones
echo ""
echo "[5/5] Actualizando menús de aplicaciones..."
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true

echo ""
echo "======================================================"
echo "  🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "======================================================"
echo ""
echo "Ya puedes abrir 'Volante PC' desde tu menú de aplicaciones"
echo "o ejecutando el comando: volante-pc"
echo ""
