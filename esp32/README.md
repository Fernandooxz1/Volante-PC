# Dashboard Motorsport ESP32 (Pantalla IPS 1.3" ST7789)

Panel digital de instrumentos (DDU) para simuladores de carreras (F1 2020..2024).
Funciona sobre una **ESP32** con **MicroPython** y una pantalla a color **IPS 1.3" 240x240 con driver ST7789 (SPI)**.

---

## 🏎️ ¿Cómo se conecta la Pantalla a la ESP32?

La pantalla ST7789 usa el bus **SPI por hardware (VSPI)** de la ESP32.

### Tabla de Pines

| Pin Pantalla ST7789 | Pin ESP32 (WROOM / ESP32-S) | Descripción |
| :--- | :--- | :--- |
| **GND** | **GND** | Tierra común |
| **VCC** | **3.3V** | Alimentación (3.3V) |
| **SCL** (o SCK / CLK) | **GPIO 18** | Reloj SPI (Hardware SCK) |
| **SDA** (o MOSI / DIN) | **GPIO 23** | Datos SPI (Hardware MOSI) |
| **RES** (o RST) | **GPIO 4** | Reset |
| **DC** | **GPIO 16** | Control Dato / Comando |
| **CS** (si tiene 8 pines) | **GPIO 5** | Chip Select (*dejar desconectado si tiene 7 pines*) |
| **BLK** (o BL) | **3.3V** (o **GPIO 15**) | Luz de fondo (*directo a 3.3V para brillo fijo*) |

> **Nota sobre versiones de 7 u 8 pines:**
> - Si tu módulo tiene **8 pines**: conecta **CS al GPIO 5**.
> - Si tu módulo tiene **7 pines**: no trae pin CS (está puesto a GND interno en la plaquita). En ese caso no conectas nada y en `config.py` queda `PIN_CS = None`.

---

## ⚙️ Paso 1: Configurar el WiFi

Abre el archivo `config.py` y coloca los datos de tu red:

```python
WIFI_SSID = "Tu_Red_WiFi"          # Nombre de tu red WiFi (2.4 GHz)
WIFI_PASSWORD = "Tu_Password_WiFi"  # Contraseña
```

---

## 🚀 Paso 2: Subir los Archivos a la ESP32

Con la ESP32 conectada por USB (puerto `/dev/ttyUSB1`):

```bash
cd /home/fernando/Work/Volante-PC/esp32

# Copiar driver, fuentes y scripts a la ESP32
mpremote connect /dev/ttyUSB1 cp st7789py.py :st7789py.py
mpremote connect /dev/ttyUSB1 cp font_small.py :font_small.py
mpremote connect /dev/ttyUSB1 cp ddu_display.py :ddu_display.py
mpremote connect /dev/ttyUSB1 cp config.py :config.py
mpremote connect /dev/ttyUSB1 cp main.py :main.py

# Reiniciar la ESP32
mpremote connect /dev/ttyUSB1 reset
```

---

## 🖥️ Interfaz en Pantalla (DDU)

1. **Barra de Shift Lights superior (12 LEDs):**
   - 4 Verdes -> 3 Amarillos -> 3 Rojos -> 2 Violetas / Azules.
   - Destello estroboscópico al 95% de revoluciones (momento óptimo de cambio).
2. **Marcha central gigante:**
   - En estilo digital de alta visibilidad (Verde para "N", Rojo para "R", Blanco para 1-8).
3. **Velocidad digital:**
   - En números grandes en color cian con etiqueta "KM/H".
4. **Zona inferior:**
   - `RPM: 11450` y cartel activo `[DRS]` en verde fosforescente cuando está habilitado.
