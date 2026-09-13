"""
Plantilla de configuración para el Dashboard ESP32 con ST7789 (Volante-PC).
Copia este archivo como config.py y coloca los datos de tu red WiFi.
"""

# ==============================================================================
# CONFIGURACIÓN WIFI
# ==============================================================================
WIFI_SSID = "TU_WIFI_AQUI"
WIFI_PASSWORD = "TU_PASSWORD_AQUI"
UDP_PORT = 20778
WIFI_TIMEOUT_SEC = 15

# ==============================================================================
# PANTALLA IPS 1.3" 240x240 (ST7789 SPI)
# ==============================================================================
# Pines SPI de hardware en ESP32
PIN_SCL = 18   # SCL / SCK (Reloj SPI)
PIN_SDA = 23   # SDA / MOSI (Datos SPI)
PIN_RES = 4    # RES / RST (Reset)
PIN_DC = 16    # DC (Comando / Dato)

# Si tu pantalla tiene 8 pines (tiene CS), usa GPIO 5.
# Si tu pantalla tiene 7 pines (no tiene CS), pon None.
PIN_CS = 5

# Pin para encender la luz de fondo (BLK / BL) con 3.3V (GPIO 17)
PIN_BLK = 17

# Rotación de pantalla: 0, 1 (paisaje), 2 (invertido), 3
DISPLAY_ROTATION = 0
