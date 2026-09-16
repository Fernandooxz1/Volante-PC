"""
Controlador de Dashboard Hardware Discreto para ESP32:
- Tira NeoPixel WS2812B de 8 LEDs RGB (Tacómetro Shift Light)
- 1 Display 7 Segmentos Ánodo Común (Marcha)
- 1 Display 7 Segmentos 3 Dígitos Ánodo Común (Velocidad km/h)
Multiplexado compartido en 7 pines de segmentos + 4 pines de dígitos (11 pines en total).
"""

import time
from machine import Pin
import neopixel

# Tabla de segmentos para Ánodo Común (0 = Encendido / LOW, 1 = Apagado / HIGH)
# Orden: [A, B, C, D, E, F, G]
SEGMENTS_CA = {
    "0": (0, 0, 0, 0, 0, 0, 1),
    "1": (1, 0, 0, 1, 1, 1, 1),
    "2": (0, 0, 1, 0, 0, 1, 0),
    "3": (0, 0, 0, 0, 1, 1, 0),
    "4": (1, 0, 0, 1, 1, 0, 0),
    "5": (0, 1, 0, 0, 1, 0, 0),
    "6": (0, 1, 0, 0, 0, 0, 0),
    "7": (0, 0, 0, 1, 1, 1, 1),
    "8": (0, 0, 0, 0, 0, 0, 0),
    "9": (0, 0, 0, 0, 1, 0, 0),
    "N": (1, 1, 0, 1, 0, 1, 0),  # 'n' minúscula
    "n": (1, 1, 0, 1, 0, 1, 0),
    "R": (1, 1, 1, 1, 0, 1, 0),  # 'r' minúscula
    "r": (1, 1, 1, 1, 0, 1, 0),
    "-": (1, 1, 1, 1, 1, 1, 0),
    " ": (1, 1, 1, 1, 1, 1, 1),  # Apagado total
}

# Colores NeoPixel (R, G, B)
COLOR_OFF = (0, 0, 0)
COLOR_GREEN = (0, 180, 0)
COLOR_YELLOW = (180, 140, 0)
COLOR_RED = (200, 0, 0)
COLOR_BLUE = (0, 0, 220)
COLOR_WHITE = (200, 200, 200)


class DiscreteDDU:
    """Maneja los displays de 7 segmentos multiplexados y la tira de 8 NeoPixels."""

    def __init__(self, config):
        self.config = config

        # 1. Configurar 7 pines de segmentos (salidas)
        self.seg_pins = [
            Pin(config.PIN_SEG_A, Pin.OUT),
            Pin(config.PIN_SEG_B, Pin.OUT),
            Pin(config.PIN_SEG_C, Pin.OUT),
            Pin(config.PIN_SEG_D, Pin.OUT),
            Pin(config.PIN_SEG_E, Pin.OUT),
            Pin(config.PIN_SEG_F, Pin.OUT),
            Pin(config.PIN_SEG_G, Pin.OUT),
        ]
        # Apagar todos los segmentos (HIGH para ánodo común)
        for p in self.seg_pins:
            p.value(1)

        # 2. Configurar 4 pines de selección de dígitos / ánodos (salidas)
        # En Ánodo Común: HIGH activa el dígito, LOW lo apaga
        self.digit_pins = [
            Pin(config.PIN_DIG_GEAR, Pin.OUT),    # Dígito 0: Marcha
            Pin(config.PIN_DIG_SPEED_1, Pin.OUT), # Dígito 1: Centenas km/h
            Pin(config.PIN_DIG_SPEED_2, Pin.OUT), # Dígito 2: Decenas km/h
            Pin(config.PIN_DIG_SPEED_3, Pin.OUT), # Dígito 3: Unidades km/h
        ]
        # Apagar todos los ánodos al inicio (LOW)
        for p in self.digit_pins:
            p.value(0)

        # 3. Configurar tira NeoPixels WS2812B (10 LEDs por defecto)
        self.num_leds = getattr(config, "NEOPIXEL_COUNT", 10)
        self.np = neopixel.NeoPixel(Pin(config.PIN_NEOPIXEL, Pin.OUT), self.num_leds)
        self.clear_leds()

        # Buffers de visualización
        self.chars_to_display = ["N", " ", " ", "0"]
        self._current_digit_idx = 0
        self._flash_state = False
        self._last_flash_time = 0

    def clear_leds(self):
        """Apaga todos los LEDs de la tira."""
        for i in range(self.num_leds):
            self.np[i] = COLOR_OFF
        self.np.write()

    def update_telemetry(self, gear_str: str, speed: int, revs_pct: int, drs: int):
        """Actualiza los valores que deben mostrar los displays y los LEDs."""
        # 1. Marcha
        g_char = gear_str if gear_str in SEGMENTS_CA else "-"

        # 2. Velocidad formateada a 3 dígitos con ceros a la izquierda apagados
        sp = max(0, min(999, int(speed)))
        if sp < 10:
            sp_str = f"  {sp}"
        elif sp < 100:
            sp_str = f" {sp}"
        else:
            sp_str = f"{sp}"

        self.chars_to_display = [g_char, sp_str[0], sp_str[1], sp_str[2]]

        # 3. Actualizar tira de NeoPixels
        self._update_neopixels(revs_pct, drs)

    def _update_neopixels(self, revs_pct: int, drs: int):
        """Mapea el porcentaje de revoluciones en los NeoPixels."""
        clamped = max(0, min(100, revs_pct))

        # Shift Flash cuando se supera el 95% de RPM
        if clamped >= 95:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_flash_time) > 70:
                self._flash_state = not self._flash_state
                self._last_flash_time = now

            flash_color = COLOR_BLUE if self._flash_state else COLOR_WHITE
            for i in range(self.num_leds):
                self.np[i] = flash_color
            self.np.write()
            return

        # Escala progresiva:
        if self.num_leds == 5:
            # 5 LEDs: 2 Verdes (50, 65%), 1 Amarillo (78%), 1 Rojo (88%), 1 Azul (94%)
            thresholds = [50, 65, 78, 88, 94]
            colors = [
                COLOR_GREEN, COLOR_GREEN,
                COLOR_YELLOW,
                COLOR_RED,
                COLOR_BLUE,
            ]
        elif self.num_leds == 10:
            # 10 LEDs: 3 Verdes (50-66%), 3 Amarillos (72-84%), 2 Rojos (88-92%), 2 Azules (95-98%)
            thresholds = [50, 58, 66, 72, 78, 84, 88, 92, 95, 98]
            colors = [
                COLOR_GREEN, COLOR_GREEN, COLOR_GREEN,
                COLOR_YELLOW, COLOR_YELLOW, COLOR_YELLOW,
                COLOR_RED, COLOR_RED,
                COLOR_BLUE, COLOR_BLUE,
            ]
        else:
            # 8 LEDs: 2 Verdes, 2 Amarillos, 2 Rojos, 2 Azules
            thresholds = [50, 60, 70, 78, 85, 90, 93, 95]
            colors = [
                COLOR_GREEN, COLOR_GREEN,
                COLOR_YELLOW, COLOR_YELLOW,
                COLOR_RED, COLOR_RED,
                COLOR_BLUE, COLOR_BLUE,
            ]

        for i in range(self.num_leds):
            if clamped >= thresholds[i]:
                self.np[i] = colors[i]
            else:
                self.np[i] = COLOR_OFF

        self.np.write()

    def refresh_step(self):
        """
        Paso de multiplexado rápido: apaga el dígito anterior, coloca los segmentos
        del nuevo dígito y activa su ánodo. Llamar en el bucle principal con delay de ~2ms.
        """
        # Apagar el ánodo actual para evitar imágenes fantasma (ghosting)
        self.digit_pins[self._current_digit_idx].value(0)

        # Avanzar al siguiente dígito
        self._current_digit_idx = (self._current_digit_idx + 1) % 4
        char = self.chars_to_display[self._current_digit_idx]
        seg_bits = SEGMENTS_CA.get(char, SEGMENTS_CA[" "])

        # Configurar los 7 segmentos (0 = LOW / ON, 1 = HIGH / OFF)
        for pin_obj, bit in zip(self.seg_pins, seg_bits):
            pin_obj.value(bit)

        # Encender el ánodo del dígito seleccionado (HIGH = 3.3V)
        self.digit_pins[self._current_digit_idx].value(1)
