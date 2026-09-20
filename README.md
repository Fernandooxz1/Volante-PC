# Volante-PC (DIY Sim Racing Wheel & Pedals)

[![Platform](https://img.shields.io/badge/Platform-Linux%20(Wayland%2FX11)%20%7C%20Windows-blue.svg)](https://github.com)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32-E7352C.svg)](https://www.espressif.com/)
[![Emulation](https://img.shields.io/badge/Emulation-Xbox%20360%20Virtual%20Controller-107C41.svg)](https://github.com)
[![UI](https://img.shields.io/badge/UI-PyQt6-black.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://www.python.org)

Custom DIY sim racing wheel and pedal set built with an **ESP32**, an **AS5600 magnetic angle sensor**, **SS49E Hall-effect sensors** for the pedals, mechanical keyboard switches for wheel buttons, and WS2812B RGB shift lights for telemetry.

The PC side runs a **PyQt6** control panel with a dedicated **100 Hz real-time engine** running in a separate thread. It handles serial communication, filters sensor noise (DSP), applies customizable exponential steering curves, and emulates an **Xbox 360 controller** so it works out of the box with games like Assetto Corsa, F1, and Forza on both **Linux** (Wayland / X11 via `/dev/uinput`) and **Windows** (via ViGEmBus).

---

## What it does

- **100 Hz Threaded Engine**: Serial communication runs in its own thread synchronized with `time.perf_counter()` to keep input latency under 10 ms, even if the window is minimized or busy.
- **Hardware-Accelerated UI**: Built in PyQt6 with clean dark styling, running smoothly on both Linux (Wayland / X11) and Windows.
- **Noise Filtering (DSP)**: Slew-rate limiting combined with an adaptive Exponential Moving Average (EMA) filter to remove sensor jitter without adding noticeable input lag.
- **Steering Curves & Calibration**:
  - Continuous multi-turn tracking with selectable steering lock (from 180° up to 900° / -450° to +450°).
  - Exponential response curves to keep center steering fine and stable while keeping full lock reachable.
  - Interactive calibration wizard for center and physical steering limits, plus pedal deadzones.
- **Button Mapping**: Step-by-step wizard to map physical switches (keyboard switches wired to the ESP32) directly to Xbox controller buttons.
- **Operation Modes**:
  - **Driving Mode**: Standard analog steering, pedals, and mapped wheel buttons.
  - **D-Pad Mode**: Switches steering or side buttons into D-Pad navigation for game menus.
- **Flexible Execution**:
  - Full GUI: `python main.py` or `volante-pc`
  - Background daemon: `volante-pc --daemon` (~15 MB RAM)
  - ASCII Terminal dashboard: `volante-pc --cli`

---

## Hardware Setup

- **Microcontroller**: ESP32 Dev Module
- **Steering**: AS5600 12-bit magnetic angle sensor (I2C: SDA -> GPIO 21, SCL -> GPIO 22)
- **Pedals**: SS49E Hall sensors for throttle (GPIO 32), brake (GPIO 34), and clutch (GPIO 35)
- **Wheel Buttons**: 10 mechanical switches wired to ESP32 GPIO pins
- **Shift Lights**: WS2812B NeoPixel strip (GPIO 13) for RPM / redline shift indicator

Firmware source is located in `microcontroller/esp32/` and can be compiled and flashed with PlatformIO or the Arduino IDE.

---

## Linux Installation (Arch / Debian / Ubuntu / Fedora)

Run the included install script:

```bash
git clone https://github.com/Fernandooxz1/Volante-PC.git
cd Volante-PC
chmod +x install.sh
./install.sh
```

The script:
1. Detects your distro and installs required system packages (`python3-pyqt6`, `python3-venv`, etc.).
2. Sets up `udev` rules so your user can access `/dev/uinput` and USB serial devices without needing `sudo`.
3. Creates the Python virtual environment and installs dependencies.
4. Adds the desktop application launcher and the `volante-pc` command.

---

## Usage

### 1. GUI Panel (Default)
```bash
volante-pc
# or directly:
python main.py
```

### 2. Background Daemon
Runs just the 100 Hz input engine without a GUI:
```bash
volante-pc --daemon
```

### 3. Terminal Dashboard
Real-time ASCII meters inside your terminal:
```bash
volante-pc --cli
```

---

## Project Structure

```
Volante-PC/
├── microcontroller/
│   └── esp32/                           # ESP32 C++ firmware (PlatformIO / Arduino IDE)
│       ├── esp32_wheel.ino              # 100 Hz loop, AS5600, Hall sensors, buttons, NeoPixels
│       └── platformio.ini               # PlatformIO board configuration
├── core/                                # Real-time engine, DSP & gamepad logic
│   ├── protocol.py                      # Binary packet parser (8 bytes at 100 Hz)
│   ├── dsp.py                           # Slew-rate limiter & EMA filter
│   ├── calibration.py                   # Exponential curves, deadzones, multi-turn lock
│   ├── gamepad.py                       # Virtual Xbox 360 gamepad (/dev/uinput & ViGEmBus)
│   ├── config_manager.py                # JSON config persistence & presets
│   ├── engine.py                        # 100 Hz main thread loop
│   ├── f1_telemetry.py                  # UDP telemetry receiver for F1 games
│   └── esp32_bridge.py                  # Telemetry sender to ESP32
├── ui/                                  # PyQt6 user interface
│   ├── widgets/                         # Custom vector widgets (wheel, pedal bars, curve)
│   ├── dialogs/                         # Calibration & mapping wizards
│   ├── themes.py                        # Dark theme styling
│   └── main_window.py                   # Main window
├── tests/                               # Automated test suite (130 tests)
├── install.sh                           # Automatic Linux installer (udev rules & dependencies)
├── requirements.txt                     # Python dependencies
└── main.py                              # Entry point (--gui, --daemon, --cli)
```

---

## Running Tests

All core logic, protocol unpacking, DSP filtering, and UI widgets are covered by automated unit tests:

```bash
pytest tests/
```

---

## License

MIT License.
