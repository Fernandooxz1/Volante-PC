#  Volante para PC con Arduino UNO y Python (Multiplataforma)

[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-blue.svg)](https://github.com)
[![Hardware](https://img.shields.io/badge/Hardware-Arduino%20UNO-00979D.svg)](https://www.arduino.cc)
[![Emulation](https://img.shields.io/badge/Emulation-Xbox%20360%20Virtual%20Controller-107C41.svg)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.8%2B-yellow.svg)](https://www.python.org)

Este proyecto te permite construir tu propio **volante de carreras y pedalera profesional para PC** utilizando un **Arduino UNO**, 3 potenciómetros lineales de 10k $\Omega$, botones digitales, LED RGB de telemetría y un potente panel de control nativo en Python que emula un control virtual de Xbox 360 de ultra baja latencia (100 Hz).

Incluye una **curva de dirección exponencial (Steering Expo)** idéntica a la utilizada en simuladores comerciales de gama alta (Logitech G, Fanatec, Moza) para lograr máxima precisión y estabilidad en rectas sin perder agilidad en curvas cerradas.

---

## Instalación Rápida en Linux (1 Solo Comando)

Clona el repositorio y ejecuta el instalador automático:

```bash
git clone https://github.com/Fernandooxz1/Volante-PC.git
cd Volante-PC
chmod +x install.sh
./install.sh
```

El instalador:
1. Configura automáticamente las reglas `udev` de permisos para el joystick virtual (`/dev/uinput`) y el puerto serie del Arduino (`/dev/ttyUSB*`, `/dev/ttyACM*`).
2. Configura el entorno virtual de Python con todas las librerías necesarias.
3. Compila el binario ejecutable independiente.
4. Instala el acceso directo y el icono de la aplicación en tu sistema para que aparezca en el menú de aplicaciones (`Super` -> **Volante PC**).

---

## Requisitos de Hardware

1. **Arduino UNO** (o clon con chip CH340 / ATmega16U2).
2. **3 Potenciómetros lineales de 10k Ohms**:
   - 1x para el **Volante** (Dirección).
   - 1x para el **Pedal de Acelerador**.
   - 1x para el **Pedal de Freno**.
3. **Pulsadores / Botones** (hasta 11 botones soportados en pines digitales y analógicos).
4. **1x LED RGB de Ánodo Común** (opcional, para indicador de RPM / estado y cambio de presets).
5. **Cables de conexión**, protoboard o placa de soldadura y **cable USB**.

### Esquema de Conexiones

Todos los potenciómetros comparten la línea de alimentación de **5V** y tierra (**GND**) del Arduino UNO. Los pines centrales (*wiper*) se conectan a las entradas analógicas:

| Componente | Pin del Componente | Pin en Arduino UNO |
| :--- | :--- | :--- |
| **GND Común** | Pin Izquierdo potenciómetros | **GND** |
| **5V Común** | Pin Derecho potenciómetros | **5V** o **VCC** |
| **Señal Volante** | Pin Central (Wiper) | **A0** |
| **Señal Acelerador** | Pin Central (Wiper) | **A1** |
| **Señal Freno** | Pin Central (Wiper) | **A2** |
| **Botones Digitales (1 a 11)** | Un pin a Tierra (GND), otro al Pin | **D2..D8, A3, A5, A4, D12** (con `INPUT_PULLUP`) |
| **LED RGB (R, G, B)** | Pines de color (Ánodo Común a 5V) | **D9 (Rojo), D10 (Verde), D11 (Azul)** |

> [!TIP]
> Si el giro del volante o el recorrido de un pedal queda invertido, puedes invertirlo fácilmente desde la interfaz gráfica o intercambiando los cables de 5V y GND en los extremos del potenciómetro.

---

## Instalación y Configuración Manual

### 1. Flashear el Arduino UNO
1. Abre [Arduino IDE](https://www.arduino.cc/en/software) (o PlatformIO).
2. Abre el archivo [arduino/volante_uno/volante_uno.ino](arduino/volante_uno/volante_uno.ino).
3. Selecciona tu placa **Arduino Uno** y el puerto serie correspondiente (`/dev/ttyUSB0`, `/dev/ttyACM0` o `COM3`).
4. Haz clic en **Subir (Upload)**.

### 2. Dependencias del Sistema en Linux

- **Arch Linux / Manjaro / Omarchy**:
  ```bash
  sudo pacman -S --needed python python-pip python-gobject webkit2gtk-4.1 gtk3 jstest-gtk
  ```
- **Ubuntu / Debian / Linux Mint**:
  ```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 jstest-gtk
  ```
- **Fedora**:
  ```bash
  sudo dnf install -y python3 python3-pip python3-gobject webkit2gtk4.1 gtk3 jstest-gtk
  ```

### 3. Permisos de Linux (`udev`)

Crea las reglas de acceso sin necesidad de permisos de superusuario:
```bash
sudo tee /etc/udev/rules.d/99-volante-pc.rules << 'EOF'
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
KERNEL=="ttyUSB*", MODE="0666", GROUP="uucp", TAG+="uaccess"
KERNEL=="ttyACM*", MODE="0666", GROUP="uucp", TAG+="uaccess"
EOF

sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG input,uucp,dialout $USER
sudo modprobe uinput
```

### 4. Configuración en Windows

1. Instala Python 3.8+ desde [python.org](https://www.python.org).
2. Instala las dependencias:
   ```cmd
   pip install -r python/requirements_nativa.txt
   ```
3. **Driver ViGEmBus**: Si ejecutas el programa en Windows sin tener el controlador instalado, la interfaz te mostrará un banner con el botón **"Instalar ViGEmBus"** que ejecutará automáticamente el instalador integrado en `python/web/drivers/ViGEmBus_Setup.exe`.

---

## Ejecución y Modos de Uso

### Opción A: Aplicación Nativa con Dashboard Pro (Recomendado)
Ejecuta la interfaz nativa de escritorio:
```bash
# Si instalaste con install.sh:
volante-pc

# O directamente desde el código fuente:
python3 python/app_nativa.py
```

### Opción B: Dashboard en Navegador Web
Si prefieres correr un servidor web local y abrir el panel en tu navegador:
```bash
python3 python/gui_web.py
```

### Opción C: Modo Consola (Headless)
Para terminales sin entorno gráfico:
```bash
python3 python/emulador_volante.py
```

---

## Calibración y Curva Exponencial

Para evitar que el auto zigzaguee en rectas a altas velocidades, se implementa una **progresión exponencial de dirección**:

$$x_{\text{expo}} = \text{sign}(x) \cdot |x|^{\text{slope}}$$
$$x_{\text{sloped}} = x_{\text{expo}} \cdot \text{sensitivity}$$

* **Pendiente de Eje (Linealidad / Slope)**:
  - Valores entre **`1.4` y `2.0`** proporcionan una zona central ultra suave (ideal para F1 y GT3).
  - Un valor de **`1.0`** ofrece respuesta completamente lineal (1:1).
* **Filtro Anti-Ruido (Anti-Jitter)**:
  - Suaviza las fluctuaciones eléctricas o saltos de potenciómetros desgastados mediante filtro EMA.
* **Calibración de Límites y Centro**:
  - Permite guardar los topes físicos reales (Izquierda, Centro y Derecha) de tu volante y el recorrido de tus pedales.

---

## Compilación del Ejecutable

Para compilar un binario independiente con PyInstaller:

```bash
cd python
pyinstaller --clean --noconfirm VolantePC.spec
```
El ejecutable se generará en `python/dist/VolantePC` (o `VolantePC.exe` en Windows).

---

## Licencia

Proyecto de código abierto bajo licencia MIT. ¡Construye, compite y disfruta! 🏁
