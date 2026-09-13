"""
Controlador gráfico DDU Motorsport para pantalla IPS 1.3" 240x240 (ST7789 SPI).
Diseñado para alto rendimiento en MicroPython (cero parpadeo, renderizado parcial rápido).
"""

from machine import Pin, SPI
import st7789py as st7789
import font_small

# Colores en formato RGB565 (16 bits)
COLOR_BLACK = 0x0000
COLOR_WHITE = 0xFFFF
COLOR_RED = 0xF800
COLOR_GREEN = 0x07E0
COLOR_BLUE = 0x001F
COLOR_YELLOW = 0xFFE0
COLOR_CYAN = 0x07FF
COLOR_MAGENTA = 0xF81F
COLOR_DARK_GRAY = 0x18C3
COLOR_GRAY = 0x7BEF

SEGMENTS = {
    "0": (1, 1, 1, 1, 1, 1, 0),
    "1": (0, 1, 1, 0, 0, 0, 0),
    "2": (1, 1, 0, 1, 1, 0, 1),
    "3": (1, 1, 1, 1, 0, 0, 1),
    "4": (0, 1, 1, 0, 0, 1, 1),
    "5": (1, 0, 1, 1, 0, 1, 1),
    "6": (1, 0, 1, 1, 1, 1, 1),
    "7": (1, 1, 1, 0, 0, 0, 0),
    "8": (1, 1, 1, 1, 1, 1, 1),
    "9": (1, 1, 1, 1, 0, 1, 1),
    "-": (0, 0, 0, 0, 0, 0, 1),
}


class DDUDisplay:
    """Panel de instrumentos para simulador en pantalla ST7789 240x240."""

    def __init__(self, config):
        self.config = config

        # Inicialización de SPI por hardware (bus 2 = VSPI en ESP32 estándar)
        self.spi = SPI(
            2,
            baudrate=40000000,
            polarity=1,
            phase=1,
            sck=Pin(config.PIN_SCL),
            mosi=Pin(config.PIN_SDA),
        )

        pin_res = Pin(config.PIN_RES, Pin.OUT) if config.PIN_RES is not None else None
        pin_dc = Pin(config.PIN_DC, Pin.OUT)
        pin_cs = Pin(config.PIN_CS, Pin.OUT) if config.PIN_CS is not None else None
        
        self.pin_blk = None
        if getattr(config, "PIN_BLK", None) is not None:
            self.pin_blk = Pin(config.PIN_BLK, Pin.OUT)
            self.pin_blk.value(1)  # 3.3V HIGH para encender backlight

        self.tft = st7789.ST7789(
            self.spi,
            240,
            240,
            reset=pin_res,
            dc=pin_dc,
            cs=pin_cs,
            backlight=self.pin_blk,
            rotation=getattr(config, "DISPLAY_ROTATION", 0),
            color_order=st7789.BGR,
        )

        # Estado previo para redibujo selectivo (dirty rectangles)
        self._last_gear = None
        self._last_speed = None
        self._last_rpm = None
        self._last_revs_lit = -1
        self._last_drs = None

    def clear(self):
        """Limpia la pantalla en negro."""
        self.tft.fill(COLOR_BLACK)
        self._last_gear = None
        self._last_speed = None
        self._last_rpm = None
        self._last_revs_lit = -1
        self._last_drs = None

    def show_waiting_screen(self, ip: str = ""):
        """Muestra la pantalla de espera de telemetría."""
        self.clear()
        # Barra superior decorativa
        self.tft.fill_rect(0, 0, 240, 8, COLOR_CYAN)

        self.tft.text(font_small, "VOLANTE - PC", 70, 50, COLOR_WHITE, COLOR_BLACK)
        self.tft.text(font_small, "MOTORSPORT DDU", 65, 75, COLOR_YELLOW, COLOR_BLACK)

        self.tft.fill_rect(40, 110, 160, 2, COLOR_DARK_GRAY)

        self.tft.text(font_small, "ESPERANDO JUEGO F1...", 35, 130, COLOR_CYAN, COLOR_BLACK)
        if ip:
            self.tft.text(font_small, f"IP: {ip}", 55, 165, COLOR_GREEN, COLOR_BLACK)
            self.tft.text(font_small, f"PUERTO: {self.config.UDP_PORT}", 65, 185, COLOR_GRAY, COLOR_BLACK)

        self.tft.fill_rect(0, 232, 240, 8, COLOR_CYAN)

    def draw_rev_lights(self, rev_pct: int):
        """Dibuja la barra de luces de cambio F1 progresiva en la parte superior (12 LEDs)."""
        clamped = max(0, min(100, rev_pct))
        num_leds = 12
        lit_count = int((clamped / 100.0) * num_leds) if clamped > 0 else 0

        # Si el conteo no cambió y no está en modo parpadeo extremo, saltar
        if lit_count == self._last_revs_lit and clamped < 94:
            return
        self._last_revs_lit = lit_count

        led_w = 16
        led_h = 16
        spacing = 3
        start_x = 7
        y = 6

        # Destello si está en el límite absoluto de revoluciones (> 94%)
        is_flash = (clamped >= 94)

        for i in range(num_leds):
            x = start_x + (i * (led_w + spacing))

            if is_flash:
                # Todo el panel destella en azul/blanco
                color = COLOR_BLUE if (int(clamped * 10) % 2 == 0) else COLOR_WHITE
            elif i < lit_count:
                if i < 4:
                    color = COLOR_GREEN      # 0..3: Verde
                elif i < 7:
                    color = COLOR_YELLOW     # 4..6: Amarillo
                elif i < 10:
                    color = COLOR_RED        # 7..9: Rojo
                else:
                    color = COLOR_MAGENTA    # 10..11: Violeta/Azul
            else:
                color = COLOR_DARK_GRAY      # Apagado

            self.tft.fill_rect(x, y, led_w, led_h, color)

    def _draw_7segment(self, x: int, y: int, w: int, h: int, t: int, char: str, color: int):
        """Dibuja un dígito en estilo 7 segmentos de alta visibilidad."""
        half_h = h // 2

        if char in SEGMENTS:
            a, b, c, d, e, f, g = SEGMENTS[char]
            if a: self.tft.fill_rect(x + t, y, w - 2*t, t, color)
            if b: self.tft.fill_rect(x + w - t, y + t, t, half_h - t, color)
            if c: self.tft.fill_rect(x + w - t, y + half_h, t, half_h - t, color)
            if d: self.tft.fill_rect(x + t, y + h - t, w - 2*t, t, color)
            if e: self.tft.fill_rect(x, y + half_h, t, half_h - t, color)
            if f: self.tft.fill_rect(x, y + t, t, half_h - t, color)
            if g: self.tft.fill_rect(x + t, y + half_h - (t//2), w - 2*t, t, color)
        elif char == "N":
            # Letra N
            self.tft.fill_rect(x, y, t, h, color)
            self.tft.fill_rect(x + w - t, y, t, h, color)
            self.tft.fill_rect(x + t, y + (h//3), w - 2*t, t, color)
        elif char == "R":
            # Letra R
            self.tft.fill_rect(x, y, t, h, color)
            self.tft.fill_rect(x + t, y, w - t, t, color)
            self.tft.fill_rect(x + w - t, y + t, t, half_h - t, color)
            self.tft.fill_rect(x + t, y + half_h, w - t, t, color)
            self.tft.fill_rect(x + w - t, y + half_h, t, half_h, color)

    def draw_gear(self, gear_str: str):
        """Dibuja la marcha actual en formato gigante en el centro de la pantalla."""
        if gear_str == self._last_gear:
            return

        x = 88
        y = 35
        w = 64
        h = 96
        t = 12

        # Borrar marcha anterior
        self.tft.fill_rect(x - 4, y - 4, w + 8, h + 8, COLOR_BLACK)

        # Color según marcha
        if gear_str == "N":
            color = COLOR_GREEN
        elif gear_str == "R":
            color = COLOR_RED
        else:
            color = COLOR_WHITE

        self._draw_7segment(x, y, w, h, t, gear_str, color)
        self._last_gear = gear_str

    def draw_speed(self, speed: int):
        """Dibuja la velocidad en km/h y su etiqueta."""
        if speed == self._last_speed:
            return

        speed_str = f"{min(999, max(0, speed)):3d}"

        # Dígitos de velocidad con 7 segmentos de tamaño mediano
        x_start = 65
        y = 145
        w = 26
        h = 42
        t = 6
        spacing = 8

        # Borrar área de velocidad solo si cambió
        self.tft.fill_rect(x_start - 2, y - 2, (w + spacing) * 3 + 2, h + 4, COLOR_BLACK)

        for idx, ch in enumerate(speed_str):
            if ch.isdigit():
                dx = x_start + (idx * (w + spacing))
                self._draw_7segment(dx, y, w, h, t, ch, COLOR_CYAN)

        # Etiqueta KM/H fija
        self.tft.text(font_small, "KM/H", 175, 158, COLOR_GRAY, COLOR_BLACK)
        self._last_speed = speed

    def draw_bottom_bar(self, rpm: int, drs: int):
        """Dibuja las RPM numéricas y la luz de DRS en la parte inferior."""
        y = 202

        # 1. RPM
        if rpm != self._last_rpm:
            rpm_str = f"RPM: {rpm:<5}"
            self.tft.text(font_small, rpm_str, 20, y, COLOR_WHITE, COLOR_BLACK)
            self._last_rpm = rpm

        # 2. DRS Badge
        if drs != self._last_drs:
            if drs:
                # DRS Activo: Fondo verde brillante con texto negro
                self.tft.fill_rect(155, y - 3, 65, 22, COLOR_GREEN)
                self.tft.text(font_small, " DRS ", 165, y, COLOR_BLACK, COLOR_GREEN)
            else:
                # DRS Inactivo: Marco gris oscuro
                self.tft.fill_rect(155, y - 3, 65, 22, COLOR_BLACK)
                self.tft.rect(155, y - 3, 65, 22, COLOR_DARK_GRAY)
                self.tft.text(font_small, " DRS ", 165, y, COLOR_DARK_GRAY, COLOR_BLACK)
            self._last_drs = drs

    def update(self, gear_str: str, speed: int, rpm: int, revs_pct: int, drs: int):
        """Actualiza todos los elementos del dashboard en un ciclo."""
        self.draw_rev_lights(revs_pct)
        self.draw_gear(gear_str)
        self.draw_speed(speed)
        self.draw_bottom_bar(rpm, drs)
