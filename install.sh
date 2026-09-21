#!/bin/bash
# =============================================================================
# Instalador automático de Volante PC para Linux (Arch/Omarchy, Debian/Ubuntu, Fedora)
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

# -----------------------------------------------------------------------------
# 1. Instalar paquetes del sistema necesarios según la distribución
# -----------------------------------------------------------------------------
echo ""
echo "[1/5] Verificando e instalando dependencias del sistema..."

install_system_deps() {
    if command -v pacman &>/dev/null; then
        echo "  Detectado sistema basado en Arch Linux / Omarchy (pacman)..."
        local arch_pkgs=(python python-pip python-pyqt6 base-devel)
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
            else
                echo "  ⚠️ No se detectó sudo. Instala manualmente: pacman -S --needed ${to_install[*]}"
            fi
        else
            echo "  ✓ Paquetes del sistema verificados."
        fi

    elif command -v apt-get &>/dev/null; then
        echo "  Detectado sistema basado en Debian/Ubuntu (apt)..."
        local debian_pkgs=(python3 python3-pip python3-venv python3-pyqt6)
        local missing_pkgs=()
        for pkg in "${debian_pkgs[@]}"; do
            if ! dpkg -s "$pkg" &>/dev/null; then
                missing_pkgs+=("$pkg")
            fi
        done
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
            echo "  ✓ Paquetes del sistema verificados."
        fi

    elif command -v dnf &>/dev/null; then
        echo "  Detectado sistema basado en Fedora / RHEL (dnf)..."
        local fedora_pkgs=(python3 python3-pip python3-pyqt6)
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
            echo "  ✓ Paquetes del sistema verificados."
        fi

    else
        echo "  ℹ️ Distribución no identificada automáticamente. Continuando con la configuración de Python..."
    fi
}
install_system_deps

# -----------------------------------------------------------------------------
# 2. Configurar reglas udev con 0666 y TAG+="uaccess"
# -----------------------------------------------------------------------------
echo ""
echo "[2/5] Configurando permisos de hardware (udev)..."

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

    echo "  Configurando reglas udev para uinput y puertos serie USB..."
    $SUDO_CMD tee /etc/udev/rules.d/99-volante-pc.rules > /dev/null << 'UDEV_EOF'
# Permiso para joystick virtual uinput (acceso directo 0666 y tag uaccess para systemd-logind)
KERNEL=="uinput", MODE="0666", GROUP="input", OPTIONS+="static_node=uinput", TAG+="uaccess"

# Permiso para Arduino / adaptadores USB-Serie (CH340, FTDI, CP2102, ATmega16U2)
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout", TAG+="uaccess"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout", TAG+="uaccess"
KERNEL=="ttyUSB*", MODE="0666", GROUP="uucp", TAG+="uaccess"
KERNEL=="ttyACM*", MODE="0666", GROUP="uucp", TAG+="uaccess"
UDEV_EOF

    $SUDO_CMD udevadm control --reload-rules 2>/dev/null || true
    $SUDO_CMD udevadm trigger 2>/dev/null || true
    $SUDO_CMD modprobe uinput 2>/dev/null || true

    # Agregar usuario a grupos input, dialout y uucp
    $SUDO_CMD usermod -aG input "$TARGET_USER" 2>/dev/null || true
    $SUDO_CMD usermod -aG dialout "$TARGET_USER" 2>/dev/null || true
    $SUDO_CMD usermod -aG uucp "$TARGET_USER" 2>/dev/null || true
    echo "  ✓ Reglas udev (0666, uaccess) y grupos configurados para $TARGET_USER."
}
setup_udev

# -----------------------------------------------------------------------------
# 3. Configurar entorno virtual de Python y dependencias
# -----------------------------------------------------------------------------
echo ""
echo "[3/5] Configurando entorno virtual de Python..."

if [ -d "python/venv" ] && [ ! -f "python/venv/bin/activate" ]; then
    echo "  Detectado entorno virtual previo incompleto. Recreando..."
    rm -rf python/venv 2>/dev/null || sudo rm -rf python/venv 2>/dev/null || true
fi

if [ ! -f "python/venv/bin/activate" ]; then
    echo "  Creando entorno virtual en python/venv..."
    python3 -m venv --system-site-packages python/venv || {
        echo ""
        echo "  ❌ ERROR: No se pudo crear el entorno virtual de Python."
        echo "  Verifica tener instalado python3-venv o python."
        exit 1
    }
fi

echo "  Instalando/actualizando dependencias de Volante-PC..."
python/venv/bin/pip install --upgrade pip --quiet 2>/dev/null || true
python/venv/bin/pip install -r requirements.txt --quiet

# -----------------------------------------------------------------------------
# 4. Crear lanzador binario 'volante-pc'
# -----------------------------------------------------------------------------
echo ""
echo "[4/5] Creando ejecutable y acceso directo..."

mkdir -p "$TARGET_HOME/.local/bin" "$TARGET_HOME/.local/share/applications" "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps"

# Crear wrapper volante-pc
cat << LAUNCHER_EOF > "$TARGET_HOME/.local/bin/volante-pc"
#!/bin/bash
# Volante-PC Launcher Script
if [ -n "\$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
exec "$REPO_DIR/python/venv/bin/python" "$REPO_DIR/main.py" "\$@"
LAUNCHER_EOF

chmod +x "$TARGET_HOME/.local/bin/volante-pc"

# Copiar icono
if [ -f "volante-pc.svg" ]; then
    cp volante-pc.svg "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps/volante-pc.svg"
fi

# -----------------------------------------------------------------------------
# 5. Crear lanzador de escritorio (.desktop)
# -----------------------------------------------------------------------------
echo ""
echo "[5/5] Registrando aplicación en el entorno de escritorio..."

cat << DESKTOP_EOF > "$TARGET_HOME/.local/share/applications/volante-pc.desktop"
[Desktop Entry]
Type=Application
Version=1.0
Name=Volante PC
GenericName=Simracing Wheel Controller
Comment=Panel de control, calibración y telemetría de volante con Arduino
Exec=$TARGET_HOME/.local/bin/volante-pc
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
    chown -R "$TARGET_USER:$TARGET_USER" "$REPO_DIR/python/venv" 2>/dev/null || true
fi

# Actualizar base de datos de aplicaciones e iconos del sistema
update-desktop-database "$TARGET_HOME/.local/share/applications/" 2>/dev/null || true
gtk-update-icon-cache -f -t "$TARGET_HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "======================================================"
echo "  🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "======================================================"
echo ""
echo "Ya puedes iniciar Volante-PC:"
echo "  1. Desde el menú de aplicaciones de tu escritorio (busca 'Volante PC')."
echo "  2. O desde la terminal con: volante-pc"
echo "  3. En modo sin gráficos (daemon): volante-pc --daemon"
echo "  4. En modo terminal interactivo: volante-pc --cli"
echo ""
