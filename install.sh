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

# Determinar el usuario y directorio home reales (incluso si se ejecutó con sudo)
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME=$(getent passwd "$TARGET_USER" 2>/dev/null | cut -d: -f6)
[ -z "$TARGET_HOME" ] && TARGET_HOME="$HOME"

echo "Instalando para el usuario: $TARGET_USER ($TARGET_HOME)"

# 1. Instalar paquetes del sistema necesarios según la distribución
echo ""
echo "[1/6] Verificando dependencias del sistema..."
install_system_deps() {
    if command -v apt-get &>/dev/null; then
        echo "  Detectado sistema basado en Debian/Ubuntu (apt)..."
        local missing_pkgs=()
        for pkg in python3 python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0; do
            if ! dpkg -s "$pkg" &>/dev/null; then
                missing_pkgs+=("$pkg")
            fi
        done
        if ! dpkg -s "gir1.2-webkit2-4.1" &>/dev/null && ! dpkg -s "gir1.2-webkit2-4.0" &>/dev/null; then
            missing_pkgs+=("gir1.2-webkit2-4.1")
        fi

        if [ ${#missing_pkgs[@]} -gt 0 ]; then
            echo "  Instalando paquetes faltantes: ${missing_pkgs[*]}..."
            if [ "$EUID" -eq 0 ]; then
                apt-get update && apt-get install -y "${missing_pkgs[@]}"
            elif command -v sudo &>/dev/null; then
                sudo apt-get update && sudo apt-get install -y "${missing_pkgs[@]}"
            else
                echo "  ⚠️ No se detectó sudo. Instala manualmente: sudo apt update && sudo apt install -y ${missing_pkgs[*]}"
            fi
        else
            echo "  ✓ Todas las dependencias del sistema están instaladas."
        fi
    elif command -v pacman &>/dev/null; then
        echo "  Detectado sistema basado en Arch Linux (pacman)..."
        local arch_pkgs=(python python-pip python-gobject webkit2gtk-4.1 gtk3)
        local to_install=()
        for pkg in "${arch_pkgs[@]}"; do
            if ! pacman -Q "$pkg" &>/dev/null; then
                to_install+=("$pkg")
            fi
        done
        if [ ${#to_install[@]} -gt 0 ]; then
            echo "  Instalando paquetes faltantes: ${to_install[*]}..."
            if [ "$EUID" -eq 0 ]; then
                pacman -S --needed --noconfirm "${to_install[@]}"
            elif command -v sudo &>/dev/null; then
                sudo pacman -S --needed --noconfirm "${to_install[@]}"
            fi
        else
            echo "  ✓ Todas las dependencias del sistema están instaladas."
        fi
    elif command -v dnf &>/dev/null; then
        echo "  Detectado sistema Fedora/RHEL (dnf)..."
        local fedora_pkgs=(python3 python3-pip python3-gobject webkit2gtk4.1 gtk3)
        local to_install=()
        for pkg in "${fedora_pkgs[@]}"; do
            if ! rpm -q "$pkg" &>/dev/null; then
                to_install+=("$pkg")
            fi
        done
        if [ ${#to_install[@]} -gt 0 ]; then
            echo "  Instalando paquetes faltantes: ${to_install[*]}..."
            if [ "$EUID" -eq 0 ]; then
                dnf install -y "${to_install[@]}"
            elif command -v sudo &>/dev/null; then
                sudo dnf install -y "${to_install[@]}"
            fi
        else
            echo "  ✓ Todas las dependencias del sistema están instaladas."
        fi
    else
        echo "  Distribución no identificada automáticamente. Continuando con la configuración de Python..."
    fi
}
install_system_deps

# 2. Configurar reglas de udev para uinput y Arduino Serial
echo ""
echo "[2/6] Configurando permisos de sistema (udev)..."
setup_udev() {
    local SUDO_CMD=""
    if [ "$EUID" -ne 0 ]; then
        if command -v sudo &>/dev/null; then
            if [ -t 0 ] || sudo -n true 2>/dev/null; then
                SUDO_CMD="sudo"
            else
                echo "  ℹ️ Sudo requiere contraseña interactiva. Omitiendo actualización de udev en este entorno."
                return 0
            fi
        else
            echo "  ⚠️ No se detectó sudo ni permisos de root. Configura los permisos udev manualmente."
            return 0
        fi
    fi

    echo "  Configurando reglas udev para joystick virtual y puerto serie..."
    $SUDO_CMD tee /etc/udev/rules.d/99-volante-pc.rules > /dev/null << 'UDEV_EOF'
# Permiso para mando virtual uinput (modo 0666 y uaccess para uso inmediato sin reiniciar sesión)
KERNEL=="uinput", MODE="0666", GROUP="input", OPTIONS+="static_node=uinput", TAG+="uaccess"

# Permiso para Arduino / conversores USB-Serie (CH340, FTDI, CP2102, ATmega16U2)
KERNEL=="ttyUSB*", MODE="0666", GROUP="uucp", TAG+="uaccess"
KERNEL=="ttyACM*", MODE="0666", GROUP="uucp", TAG+="uaccess"
UDEV_EOF

    $SUDO_CMD udevadm control --reload-rules 2>/dev/null || true
    $SUDO_CMD udevadm trigger 2>/dev/null || true
    $SUDO_CMD modprobe uinput 2>/dev/null || true
    
    # Agregar usuario a los grupos necesarios
    $SUDO_CMD usermod -aG input "$TARGET_USER" 2>/dev/null || true
    $SUDO_CMD usermod -aG dialout "$TARGET_USER" 2>/dev/null || true
    $SUDO_CMD usermod -aG uucp "$TARGET_USER" 2>/dev/null || true
    echo "  ✓ Reglas udev y permisos de usuario configurados para $TARGET_USER."
}
setup_udev

# 3. Configurar entorno virtual de Python y dependencias
echo ""
echo "[3/6] Configurando entorno de Python y dependencias..."

# Si existe un venv corrupto o roto (sin activate o sin pip), limpiarlo
if [ -d "python/venv" ] && [ ! -f "python/venv/bin/activate" ]; then
    echo "  Detectado entorno virtual previo incompleto. Recreando..."
    rm -rf python/venv 2>/dev/null || sudo rm -rf python/venv 2>/dev/null || true
fi

if [ ! -f "python/venv/bin/activate" ]; then
    echo "  Creando entorno virtual en python/venv..."
    python3 -m venv --system-site-packages python/venv || {
        echo ""
        echo "  ❌ ERROR: No se pudo crear el entorno virtual de Python."
        echo "  Verifica tener instalado el paquete correspondiente a tu distribución:"
        echo "    Ubuntu/Debian: sudo apt install python3-venv"
        echo "    Fedora:        sudo dnf install python3"
        echo "    Arch Linux:    sudo pacman -S python"
        exit 1
    }
fi

echo "  Instalando librerías de Python requeridas..."
python/venv/bin/pip install --upgrade pip --quiet 2>/dev/null || true
python/venv/bin/pip install -r python/requirements_nativa.txt pyinstaller

# 4. Compilar el binario ejecutable
echo ""
echo "[4/6] Compilando aplicación nativa..."
bash python/build.sh

# 5. Instalar ejecutable, icono y lanzador de escritorio
echo ""
echo "[5/6] Instalando en el sistema de $TARGET_USER..."
mkdir -p "$TARGET_HOME/.local/bin" "$TARGET_HOME/.local/share/applications" "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps"

# Copiar binario
cp python/dist/VolantePC "$TARGET_HOME/.local/bin/volante-pc"
chmod +x "$TARGET_HOME/.local/bin/volante-pc"

# Copiar icono
if [ -f "volante-pc.svg" ]; then
    cp volante-pc.svg "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps/volante-pc.svg"
fi

# Crear lanzador .desktop
cat << DESKTOP_EOF > "$TARGET_HOME/.local/share/applications/volante-pc.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=Volante PC
GenericName=Emulador de Volante de Carreras
Comment=Panel de calibración y emulador de volante con Arduino
Exec=env WEBKIT_DISABLE_DMABUF_RENDERER=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 $TARGET_HOME/.local/bin/volante-pc
Icon=volante-pc
Terminal=false
Categories=Game;HardwareSettings;
Keywords=volante;wheel;racing;arduino;gamepad;xbox;joystick;simracing;
StartupNotify=true
DESKTOP_EOF

chmod +x "$TARGET_HOME/.local/share/applications/volante-pc.desktop"

# Si el script se ejecutó con sudo, restaurar la propiedad de los archivos al usuario real
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.local/bin/volante-pc" "$TARGET_HOME/.local/share/applications/volante-pc.desktop" "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps/volante-pc.svg" 2>/dev/null || true
    chown -R "$TARGET_USER:$TARGET_USER" "$REPO_DIR/python/venv" "$REPO_DIR/python/build" "$REPO_DIR/python/dist" 2>/dev/null || true
fi

# 6. Actualizar base de datos de aplicaciones
echo ""
echo "[6/6] Actualizando menús de aplicaciones..."
update-desktop-database "$TARGET_HOME/.local/share/applications/" 2>/dev/null || true
gtk-update-icon-cache -f -t "$TARGET_HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "======================================================"
echo "  🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "======================================================"
echo ""
echo "Ya puedes abrir 'Volante PC':"
echo "  1. Desde el menú de aplicaciones de tu escritorio (busca 'Volante PC')."
echo "  2. O desde la terminal con el comando: volante-pc"
echo ""
echo "Nota: Si tu terminal no encuentra 'volante-pc', asegúrate de tener"
echo "      ~/.local/bin en tu PATH o abre una nueva ventana de terminal."
echo ""
