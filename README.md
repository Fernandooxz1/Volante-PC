# Volante para PC con Arduino UNO y Python (Nativo / Multiplataforma)

[![Platform](https://img.shields.io/badge/Platform-Linux%20(Wayland%2FX11)%20%7C%20Windows-blue.svg)](https://github.com)
[![Hardware](https://img.shields.io/badge/Hardware-Arduino%20UNO-00979D.svg)](https://www.arduino.cc)
[![Emulation](https://img.shields.io/badge/Emulation-Xbox%20360%20Virtual%20Controller-107C41.svg)](https://github.com)
[![UI](https://img.shields.io/badge/UI-PyQt6%20Motorsport%20DDU-black.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://www.python.org)

Aplicacion nativa de emulación de **volante de carreras y pedaler para PC** utilizando un **Arduino UNO**, potenciómetros lineales de 10k $\Omega$, botones digitales, LED RGB de telemetría y un panel de control nativo en **PyQt6 (Qt 6)** de ultra baja latencia (100 Hz).

El motor central está completamente desacoplado de la interfaz gráfica y emula un mando virtual de Xbox 360 de con curva de dirección exponencial, filtrado DSP anti-ruido y asistentes interactivos de calibración y mapeo.

---

## Características Principales

- **100% Nativo**: Desarrollado en PyQt6 con aceleración por hardware. Fluidez a 144+ FPS nativos en Linux (Testeado en Hyprland y GNOME) y compatibilidad total con Windows.
- **Motor desacoplado a 100 Hz**: Bucle serial de hardware en hilo independiente sincronizado con `time.perf_counter()`. Cero input lag aunque la ventana esté minimizada.
- **Estética de Competición (Driver DDU)**: Fondo OLED Black (`#0B0E14`), diseño limpio, sobrio y sin sobrecargas visuales.
- **Personalización de Temas**: Paletas de acento predefinidas (*Cyan Neon, Racing Red, Porsche Acid Green, McLaren Orange, Tokyo Night Violet*) o selector libre de color hexadecimal.
- **Soporte Bilingüe Nativo [EN | ES]**: Alternador instantáneo entre Inglés y Español en la barra superior con persistencia en configuración.
- **Asistente de Mapeo Interactivo ("Mapeo dinamico")**:
  - **Asistente Completo**: Guía paso a paso por todos los controles (*"Presiona el botón para LT"*, detecta el pin en el Arduino y avanza).
  - **Mapeo Individual**: Botón para reasignar cualquier control con una sola pulsación.
- **Asistente de Calibración de Topes**: Calibración visual de topes físicos (Tope Izquierdo, Centro Neutro, Tope Derecho) y recorrido de pedales con detección de potenciómetros invertidos.
- **Widgets Vectoriales**:
  - Volante con rotación suave y lectura digital precisa de grados (`-90.0°` a `+90.0°`).
  - Barras verticales de acelerador y freno con línea punteada de zona muerta y porcentaje.
  - Gráfico cartesiano de la curva exponencial con punto seguidor en tiempo real.
  - Matriz de estado de los 11 pulsadores físicos.
- **Modos de Operación**:
  - **Modo Conducción**: Pedales y dirección operan con control progresivo.
  - **Modo Crucetas / D-Pad**: El volante y pedales se convierten en cruceta digital para navegar cómodamente los menús de cualquier juego.
- **Múltiples Modos de Ejecución**:
  - Interfaz gráfica completa: `volante-pc` o `python main.py`
  - Servicio en segundo plano (Headless): `volante-pc --daemon` (< 15 MB RAM)
  - Consola interactiva: `volante-pc --cli`

---

## Instalación Automática en Linux (Arch / Debian / Fedora)

Clona el repositorio y ejecuta el instalador como usuario normal:

```bash
git clone https://github.com/Fernandooxz1/Volante-PC.git
cd Volante-PC
chmod +x install.sh
./install.sh
```

El instalador:
1. Detecta tu distribución e instala automáticamente paquetes del sistema (`python-pyqt6` en Arch, `python3-pyqt6` en Debian/Ubuntu/Fedora).
2. Configura reglas `udev` con `MODE="0666"` y `TAG+="uaccess"` para `/dev/uinput` y el puerto serie de Arduino.
3. Prepara el entorno virtual de Python con todas las dependencias.
4. Genera el acceso directo en tu menú de aplicaciones y el comando `volante-pc`.

---

## Modos de Uso

### 1. Panel de Control Nativo (Recomendado)
```bash
volante-pc
# O directamente:
python main.py
```

### 2. Modo Segundo Plano (Daemon / Headless)
Ideal para correr el volante sin ventana abierta mientras juegas:
```bash
volante-pc --daemon
```

### 3. Modo Terminal (ASCII Dashboard)
Para terminales sin entorno gráfico:
```bash
volante-pc --cli
```

---

## Requisitos de Hardware y Conexiones (ESP32 Standalone)

La rama `testESP32` utiliza un microcontrolador **ESP32 Dev Module** a 240 MHz con transmisión serie USB directa a 100 Hz (`arduino/esp32_wheel` compilable con PlatformIO):

1. **Volante Multi-Vuelta (Sensor Magnético AS5600)**:
   - Comunicación I2C directa: **SDA $\to$ GPIO 21**, **SCL $\to$ GPIO 22**.
   - Resolución de 12 bits reducida a 10 bits (`0..1023`), con desenrollado multi-vuelta universal (*Continuous Angle Tracking*) en la app.
   - Soporte de 180° a 1080° de giro físico y virtual (360° F1, 540° Rally, 900° Camiones).
2. **Pedalera de 3 Pedales Hall (Sensores SS49E en bloque consecutivo de 5 pines)**:
   - **Freno (Señal)**: **GPIO 34** (ADC1).
   - **Embrague (Señal)**: **GPIO 35** (ADC1).
   - **Acelerador (Señal)**: **GPIO 32** (ADC1).
   - **Alimentación Común (+)**: **GPIO 33 (3.3V)**.
   - **Masa Común (GND)**: **GPIO 25 (0V)**.
3. **Shift Lights de Telemetría (8x NeoPixel WS2812B SMD en cascada)**:
   - Pin de datos `DIN`: **GPIO 13**.
   - Escala progresiva de F1: 4 Rojos (20%, 35%, 50%, 65%) + 4 Azules (75%, 83%, 90%, 95%) con destello de corte Shift Flash ($\ge$ 97%).
4. **Matriz de Botones 4x3 (12 botones físicos)**:
   - **3 Columnas (Salidas con resistencias en serie)**: **GPIO 23, GPIO 26, GPIO 27**.
   - **4 Filas (Entradas con diodos apuntando a filas)**: **GPIO 16, GPIO 17, GPIO 18, GPIO 19** con `INPUT_PULLDOWN`.

---

## Roadmap / Pendientes

- [ ] **Sensores Hall Restantes (2 pedales)**: Implementar y calibrar los otros 2 sensores de efecto Hall SS49E para el **Pedal de Freno** (asignado en GPIO 34) y el **Pedal de Embrague (Clutch)**. *Actualmente solo está operativo el pedal de acelerador.*
- [ ] **Display de 7 Segmentos**: Implementar visualizador de 7 segmentos en la ESP32 para indicador de marcha actual (*Gear: R, N, 1..8*) y velocímetro digital en KM/H con datos de telemetría de juegos (F1 2021 / Assetto Corsa / ETS2).

---

## Arquitectura del Código

```
Volante-PC/
├── arduino/
│   └── esp32_wheel/                     # Firmware unificado ESP32 (PlatformIO / Arduino C++)
│       ├── platformio.ini               # Configuración de build PlatformIO para esp32dev
│       └── esp32_wheel.ino              # Firmware 100 Hz (AS5600, SS49E, Matriz 4x3, 8 NeoPixels)
├── core/                                # Motor agnóstico de hardware y matemáticas
│   ├── protocol.py                      # Parser binario de 8 bytes y emisor serie/UDP
│   ├── dsp.py                           # Slew-rate limiter y filtro EMA adaptativo continuo
│   ├── calibration.py                   # Curva exponencial, normalización continua, bloqueo de grados
│   ├── gamepad.py                       # Abstracción vgamepad (uinput / ViGEmBus)
│   ├── config_manager.py                # Persistencia atómica de configuración JSON y presets
│   └── engine.py                        # Bucle a 100 Hz, desenrollado multi-vuelta y calibración
├── ui/                                  # Capa de interfaz gráfica nativa PyQt6
│   ├── i18n.py                          # Sistema de internacionalización bilingüe (EN / ES)
│   ├── themes.py                        # Paleta black, temas de acento y generador QSS
│   ├── widgets/                         # Widgets de telemetría de competición
│   │   ├── wheel_gauge.py               # Volante vectorial multi-vuelta con marcas dinámicas
│   │   ├── pedal_bar.py                 # Barras verticales con línea de deadzone
│   │   ├── curve_canvas.py              # Gráfico cartesiano interactivo de curva expo
│   │   └── button_grid.py               # Píldoras de estado de pines físicos
│   ├── dialogs/                         # Asistentes interactivos
│   │   ├── mapping_wizard.py            # Asistente de mapeo de botones
│   │   ├── calibration_wizard.py        # Asistente de calibración de límites
│   │   └── theme_dialog.py              # Selector visual de colores y temas
│   └── main_window.py                   # Ventana principal integrada estilo DDU con centrado rápido
├── scripts/                             # Scripts de diagnóstico y prueba de hardware
│   └── test_esp32_hardware.py           # Monitor interactivo en consola para ESP32
├── tests/                               # Suite de pruebas automatizadas (101 tests)
└── main.py                              # Punto de entrada unificado (--gui, --daemon, --cli)
```

---

## Ejecutar Pruebas Automatizadas

```bash
./python/venv/bin/pytest tests/ -v
```

---

## Licencia

Proyecto de código abierto bajo licencia MIT.
