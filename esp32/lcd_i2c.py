"""
Driver MicroPython para pantallas LCD HD44780 con adaptador I2C (PCF8574).
Compatible con pantallas LCD 1602 (16x2) y 2004 (20x4).
Incluye escaneo automático de dirección I2C (0x27 o 0x3F típicamente).
"""

import time
from machine import I2C

# Comandos HD44780
_LCD_CLR = 0x01
_LCD_HOME = 0x02
_LCD_ENTRY_MODE = 0x04
_LCD_ENTRY_INC = 0x02
_LCD_ON_CTRL = 0x08
_LCD_ON_DISPLAY = 0x04
_LCD_FUNCTION = 0x20
_LCD_FUNCTION_2LINES = 0x08
_LCD_SET_DDRAM_ADDR = 0x80

# Bits de control en PCF8574
_PIN_RS = 0x01
_PIN_RW = 0x02
_PIN_EN = 0x04
_PIN_BL = 0x08  # Backlight


class I2cLcd:
    """Controlador I2C para pantallas de cristal líquido tipo HD44780."""

    def __init__(self, i2c: I2C, i2c_addr: int = 0, num_lines: int = 2, num_columns: int = 16):
        self.i2c = i2c
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.backlight = True

        # Escanear dirección si no fue provista o es 0
        if i2c_addr == 0:
            devices = self.i2c.scan()
            if not devices:
                raise OSError("No se detectó ningún dispositivo I2C en el bus.")
            # Priorizar direcciones típicas de LCD (0x27 o 0x3F)
            if 0x27 in devices:
                self.i2c_addr = 0x27
            elif 0x3F in devices:
                self.i2c_addr = 0x3F
            else:
                self.i2c_addr = devices[0]
        else:
            self.i2c_addr = i2c_addr

        # Secuencia de inicialización en modo 4 bits
        time.sleep_ms(50)
        self._write_nibble(0x30)
        time.sleep_ms(5)
        self._write_nibble(0x30)
        time.sleep_us(150)
        self._write_nibble(0x30)
        time.sleep_ms(1)
        self._write_nibble(0x20)  # Modo 4 bits
        time.sleep_ms(1)

        # Configuración de 2 líneas y fuente 5x8
        lines_flag = _LCD_FUNCTION_2LINES if self.num_lines > 1 else 0
        self._write_byte(_LCD_FUNCTION | lines_flag, is_data=False)
        self._write_byte(_LCD_ON_CTRL | _LCD_ON_DISPLAY, is_data=False)
        self._write_byte(_LCD_CLR, is_data=False)
        time.sleep_ms(2)
        self._write_byte(_LCD_ENTRY_MODE | _LCD_ENTRY_INC, is_data=False)

    def _write_nibble(self, nibble: int, is_data: bool = False) -> None:
        val = nibble & 0xF0
        if is_data:
            val |= _PIN_RS
        if self.backlight:
            val |= _PIN_BL

        # Pulso de Enable
        self.i2c.writeto(self.i2c_addr, bytes([val | _PIN_EN]))
        time.sleep_us(500)
        self.i2c.writeto(self.i2c_addr, bytes([val & ~_PIN_EN]))
        time.sleep_us(100)

    def _write_byte(self, value: int, is_data: bool = False) -> None:
        self._write_nibble(value & 0xF0, is_data)
        self._write_nibble((value << 4) & 0xF0, is_data)

    def clear(self) -> None:
        """Limpia la pantalla."""
        self._write_byte(_LCD_CLR, is_data=False)
        time.sleep_ms(2)

    def home(self) -> None:
        """Mueve el cursor al inicio (0, 0)."""
        self._write_byte(_LCD_HOME, is_data=False)
        time.sleep_ms(2)

    def move_to(self, col: int, row: int) -> None:
        """Posiciona el cursor en la columna (0..N) y fila (0..N)."""
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row >= len(row_offsets):
            row = 0
        addr = col + row_offsets[row]
        self._write_byte(_LCD_SET_DDRAM_ADDR | addr, is_data=False)

    def putstr(self, string: str) -> None:
        """Escribe una cadena de texto en la posición actual."""
        for char in string:
            self._write_byte(ord(char), is_data=True)

    def set_backlight(self, on: bool) -> None:
        """Enciende o apaga la luz de fondo."""
        self.backlight = on
        val = _PIN_BL if on else 0
        self.i2c.writeto(self.i2c_addr, bytes([val]))
