# Volante para PC con Arduino UNO y Python (Nativo / Multiplataforma)

[![Platform](https://img.shields.io/badge/Platform-Linux%20(Wayland%2FX11)%20%7C%20Windows-blue.svg)](https://github.com)
[![Hardware](https://img.shields.io/badge/Hardware-Arduino%20UNO-00979D.svg)](https://www.arduino.cc)
[![Emulation](https://img.shields.io/badge/Emulation-Xbox%20360%20Virtual%20Controller-107C41.svg)](https://github.com)
[![UI](https://img.shields.io/badge/UI-PyQt6%20Motorsport%20DDU-black.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://www.python.org)

Suite nativa de emulación de **volante de carreras y pedalera profesional para PC** utilizando un **Arduino UNO**, potenciómetros lineales de 10k $\Omega$, botones digitales, LED RGB de telemetría y un panel de control nativo en **PyQt6 (Qt 6)** de ultra baja latencia (100 Hz reales) inspirado en instrumental de competición (Driver Display Unit).

El motor central está completamente desacoplado de la interfaz gráfica y emula un mando virtual de Xbox 360 de ultra baja latencia con curva de dirección exponencial (Steering Expo), filtrado DSP anti-ruido y asistentes interactivos de calibración y mapeo.

---

## Características Principales

- **100% Nativo (Sin WebKit ni servidores locales)**: Desarrollado en PyQt6 con aceleración por hardware. Fluidez a 60-144+ FPS nativos en Wayland (Hyprland / Sway) y compatibilidad total con Windows.
- **Motor Desacoplado a 100 Hz**: Bucle serial de hardware en hilo independiente sincronizado con `time.perf_counter()`. Cero input lag aunque la ventana esté minimizada.
- **Estética de Competición (Motorsport DDU)**: Fondo OLED Black (`#0B0E14`), diseño limpio, sobrio y sin emojis ni sobrecargas visuales.
- **Personalización de Temas**: Paletas de acento predefinidas (*Cyan Neon, Racing Red, Porsche Acid Green, McLaren Orange, Tokyo Night Violet*) o selector libre de color hexadecimal.
- **Soporte Bilingüe Nativo [EN | ES]**: Alternador instantáneo entre Inglés y Español en la barra superior con persistencia en configuración.
- **Asistente de Mapeo Interactivo ("Press to Map")**:
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

## Instalación Automática en Linux (Arch / Omarchy / Debian / Fedora)

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

## Requisitos de Hardware y Conexiones

1. **Arduino UNO** (o clon con chip CH340 / ATmega16U2).
2. **3 Potenciómetros lineales de 10k Ohms**:
   - 1x para el **Volante** (Dirección) -> Pin **A0**
   - 1x para el **Pedal de Acelerador** -> Pin **A1**
   - 1x para el **Pedal de Freno** -> Pin **A2**
3. **Pulsadores / Botones**: Pines **D2..D8, A3, A5, A4, D12** (con `INPUT_PULLUP`).
4. **1x LED RGB de Ánodo Común**:
   - Rojo -> Pin **D9**
   - Verde -> Pin **D10**
   - Azul -> Pin **D11**
   - Ánodo Común -> **5V**

---

## Arquitectura del Código

```
Volante-PC/
├── core/                                # Motor agnóstico de hardware y matemáticas
│   ├── protocol.py                      # Parser binario de 8 bytes y emisor de comandos LED
│   ├── dsp.py                           # Slew-rate limiter y filtro EMA adaptativo
│   ├── calibration.py                   # Curva exponencial, normalización, zonas muertas
│   ├── gamepad.py                       # Abstracción vgamepad (uinput / ViGEmBus)
│   ├── config_manager.py                # Persistencia atómica de configuración JSON y presets
│   └── engine.py                        # Bucle a 100 Hz en hilo independiente y bus de eventos
├── ui/                                  # Capa de interfaz gráfica nativa PyQt6
│   ├── i18n.py                          # Sistema de internacionalización bilingüe (EN / ES)
│   ├── themes.py                        # Paleta OLED Black, temas de acento y generador QSS
│   ├── widgets/                         # Widgets de telemetría de competición
│   │   ├── wheel_gauge.py               # Volante vectorial con grados
│   │   ├── pedal_bar.py                 # Barras verticales con línea de deadzone
│   │   ├── curve_canvas.py              # Gráfico cartesiano interactivo de curva expo
│   │   ├── button_grid.py               # Píldoras de estado de los 11 pines físicos
│   │   └── led_indicator.py             # Barra de LEDs de modo y sincronización RGB
│   ├── dialogs/                         # Asistentes interactivos
│   │   ├── mapping_wizard.py            # Asistente "Press to Map" (completo e individual)
│   │   ├── calibration_wizard.py        # Asistente de calibración de límites
│   │   └── theme_dialog.py              # Selector visual de colores y temas
│   └── main_window.py                   # Ventana principal integrada estilo DDU
├── tests/                               # Suite de pruebas automatizadas (67 tests)
├── main.py                              # Punto de entrada unificado (--gui, --daemon, --cli)
└── install.sh                           # Instalador para Arch Linux / Omarchy y Debian/Fedora
```

---

## Ejecutar Pruebas Automatizadas

```bash
./python/venv/bin/pytest tests/ -v
```

---

## Licencia

Proyecto de código abierto bajo licencia MIT.
