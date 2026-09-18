"""
Protocolo de comunicación serial binario para Volante-PC con Arduino UNO.

Estructura del paquete recibido desde Arduino (8 bytes en total a 100 Hz):
- 2 bytes de sincronización: 0xAA 0x55
- 4 bytes (uint32_t little-endian): 30 bits de ejes analógicos (10 steer, 10 accel, 10 brake)
- 2 bytes (uint16_t little-endian): 16 bits de botones digitales (11 botones usados)

Estructura del comando enviado a Arduino (3 bytes):
- 0xBB 0x66 <color_code>
"""

from typing import Dict, List, Optional, Tuple

SYNC_BYTE_1 = 0xAA
SYNC_BYTE_2 = 0x55
PAYLOAD_LEN = 6  # 4 bytes axes + 2 bytes buttons (legacy Arduino)
PAYLOAD_LEN_EXT = 8  # 4 bytes axes + 2 bytes buttons + 2 bytes clutch (ESP32)

PIN_NAMES = ['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'A3', 'A5', 'A4', 'D12']

CONFIG_BUTTON_KEYS = [
    'btn_map_p2',
    'btn_map_p3',
    'btn_map_p4',
    'btn_map_p5',
    'btn_map_p6',
    'btn_map_p7',
    'btn_map_p8',
    'btn_map_pa3',
    'btn_map_pa5',
    'btn_map_pa4',
    'btn_map_p12'
]

LED_COLORS: Dict[str, int] = {
    'apagado': 0, 'off': 0,
    'rojo': 1, 'red': 1,
    'verde': 2, 'green': 2,
    'azul': 3, 'blue': 3,
    'amarillo': 4, 'yellow': 4,
    'violeta': 5, 'violet': 5,
    'celeste': 6, 'cian': 6, 'cyan': 6,
    'naranja': 7, 'orange': 7
}


def encode_led_command(color: str | int) -> bytes:
    """Codifica el comando de 3 bytes para cambiar el color del LED RGB en el Arduino."""
    if isinstance(color, int):
        code = max(0, min(7, color))
    else:
        code = LED_COLORS.get(color.strip().lower(), 0)
    return bytes([0xBB, 0x66, code])


def unpack_payload(payload: bytes) -> Tuple[int, int, int, List[int]] | Tuple[int, int, int, List[int], int]:
    """
    Desempaqueta los bytes de carga útil en:
    - steer_raw (0..1023)
    - accel_raw (0..1023)
    - brake_raw (0..1023)
    - buttons (lista de 11 enteros 0 o 1)
    - clutch_raw (0..1023, presente si len(payload) >= 8)
    """
    axes_val = int.from_bytes(payload[0:4], byteorder='little', signed=False)
    buttons_val = int.from_bytes(payload[4:6], byteorder='little', signed=False)

    steer_raw = axes_val & 0x3FF
    accel_raw = (axes_val >> 10) & 0x3FF
    brake_raw = (axes_val >> 20) & 0x3FF

    buttons = [(buttons_val >> i) & 0x01 for i in range(11)]

    if len(payload) >= 8:
        clutch_raw = int.from_bytes(payload[6:8], byteorder='little', signed=False) & 0x3FF
        return steer_raw, accel_raw, brake_raw, buttons, clutch_raw

    return steer_raw, accel_raw, brake_raw, buttons


class StreamParser:
    """
    Máquina de estados para parsear el flujo continuo de bytes del puerto serie.
    Maneja desincronizaciones, ruido y fragmentación de paquetes.
    Soporta paquetes de longitud configurable (6 bytes legacy u 8 bytes con clutch).
    """
    def __init__(self, payload_len: Optional[int] = None):
        self._payload_len = payload_len
        self._state = 0  # 0: waiting 0xAA, 1: waiting 0x55, 2: reading payload
        self._buffer = bytearray()

    def reset(self) -> None:
        self._state = 0
        self._buffer.clear()

    def parse_bytes(self, chunk: bytes) -> List[Tuple]:
        packets = []
        for b in chunk:
            if self._state == 0:
                if b == SYNC_BYTE_1:
                    self._state = 1
            elif self._state == 1:
                if b == SYNC_BYTE_2:
                    self._state = 2
                    self._buffer.clear()
                elif b == SYNC_BYTE_1:
                    self._state = 1
                else:
                    self._state = 0
            elif self._state == 2:
                # Si estamos en modo auto-detect y ya tenemos 6 bytes, pero llega un sync byte 0xAA
                if self._payload_len is None and len(self._buffer) == 6 and b == SYNC_BYTE_1:
                    packets.append(unpack_payload(bytes(self._buffer)))
                    self._buffer.clear()
                    self._state = 1
                    continue

                self._buffer.append(b)
                target_len = self._payload_len if self._payload_len is not None else PAYLOAD_LEN_EXT
                if len(self._buffer) == target_len:
                    packets.append(unpack_payload(bytes(self._buffer)))
                    self._state = 0
                    self._buffer.clear()

        return packets
