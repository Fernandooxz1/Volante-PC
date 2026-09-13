"""
Plantilla de configuración para el Dashboard ESP32 (Volante-PC).
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
# MODO DE DASHBOARD ("discrete" o "st7789")
# ==============================================================================
DASHBOARD_TYPE = "discrete"

# ==============================================================================
# HARDWARE DISCRETO (7 SEGMENTOS + NEOPIXEL WS2812B)
# ==============================================================================
# Pin de datos de la tira de 8 NeoPixels WS2812B
PIN_NEOPIXEL = 13

# 7 Segmentos compartidos (Ánodo Común - con resistencia de 330Ω o 470Ω cada uno)
PIN_SEG_A = 16
PIN_SEG_B = 17
PIN_SEG_C = 18
PIN_SEG_D = 19
PIN_SEG_E = 21
PIN_SEG_F = 22
PIN_SEG_G = 23

# Ánodos Comunes (Habilitación de cada dígito - HIGH para activar)
PIN_DIG_GEAR = 25     # Display de 1 dígito (Marcha)
PIN_DIG_SPEED_1 = 26  # Display 3 dígitos: Centenas km/h
PIN_DIG_SPEED_2 = 27  # Display 3 dígitos: Decenas km/h
PIN_DIG_SPEED_3 = 14  # Display 3 dígitos: Unidades km/h

# ==============================================================================
# PANTALLA IPS 1.3" 240x240 (ST7789 SPI) - Opcional
# ==============================================================================
PIN_SCL = 18
PIN_SDA = 23
PIN_RES = 4
PIN_DC = 16
PIN_CS = 5
PIN_BLK = 17
DISPLAY_ROTATION = 0
