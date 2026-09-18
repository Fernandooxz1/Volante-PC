"""Pruebas unitarias para core/protocol.py."""

import unittest
from core.protocol import (
    CONFIG_BUTTON_KEYS,
    LED_COLORS,
    PIN_NAMES,
    StreamParser,
    encode_led_command,
    unpack_payload,
)


class TestProtocol(unittest.TestCase):

    def test_encode_led_command(self):
        # Nombres de color válidos
        self.assertEqual(encode_led_command("apagado"), bytes([0xBB, 0x66, 0]))
        self.assertEqual(encode_led_command("rojo"), bytes([0xBB, 0x66, 1]))
        self.assertEqual(encode_led_command("verde"), bytes([0xBB, 0x66, 2]))
        self.assertEqual(encode_led_command("azul"), bytes([0xBB, 0x66, 3]))
        self.assertEqual(encode_led_command("amarillo"), bytes([0xBB, 0x66, 4]))
        self.assertEqual(encode_led_command("violeta"), bytes([0xBB, 0x66, 5]))
        self.assertEqual(encode_led_command("celeste"), bytes([0xBB, 0x66, 6]))
        self.assertEqual(encode_led_command("naranja"), bytes([0xBB, 0x66, 7]))

        # Case-insensitivity y espacios
        self.assertEqual(encode_led_command("  ROJO  "), bytes([0xBB, 0x66, 1]))
        self.assertEqual(encode_led_command("AzUl"), bytes([0xBB, 0x66, 3]))

        # Códigos numéricos directos y clamping
        self.assertEqual(encode_led_command(0), bytes([0xBB, 0x66, 0]))
        self.assertEqual(encode_led_command(7), bytes([0xBB, 0x66, 7]))
        self.assertEqual(encode_led_command(-5), bytes([0xBB, 0x66, 0]))
        self.assertEqual(encode_led_command(99), bytes([0xBB, 0x66, 7]))

        # Color desconocido retorna código 0 (apagado)
        self.assertEqual(encode_led_command("inexistente"), bytes([0xBB, 0x66, 0]))

    def test_unpack_payload(self):
        # 10 bits por eje:
        # steer = 512 (0x200), accel = 100 (0x064), brake = 1000 (0x3E8)
        # axes_val = 512 | (100 << 10) | (1000 << 20)
        axes_val = 512 | (100 << 10) | (1000 << 20)
        # Botones: bits 0, 2, 7 activos -> 1 | 4 | 128 = 133
        buttons_val = 1 | (1 << 2) | (1 << 7)

        payload = axes_val.to_bytes(4, byteorder="little") + buttons_val.to_bytes(2, byteorder="little")
        self.assertEqual(len(payload), 6)

        steer, accel, brake, buttons = unpack_payload(payload)

        self.assertEqual(steer, 512)
        self.assertEqual(accel, 100)
        self.assertEqual(brake, 1000)
        self.assertEqual(len(buttons), 11)
        self.assertEqual(buttons[0], 1)
        self.assertEqual(buttons[1], 0)
        self.assertEqual(buttons[2], 1)
        self.assertEqual(buttons[7], 1)
        self.assertEqual(buttons[3], 0)

    def test_unpack_payload_with_clutch(self):
        axes_val = 512 | (100 << 10) | (1000 << 20)
        buttons_val = 1 | (1 << 2)
        clutch_val = 750

        payload = (
            axes_val.to_bytes(4, byteorder="little")
            + buttons_val.to_bytes(2, byteorder="little")
            + clutch_val.to_bytes(2, byteorder="little")
        )
        self.assertEqual(len(payload), 8)

        steer, accel, brake, buttons, clutch = unpack_payload(payload)

        self.assertEqual(steer, 512)
        self.assertEqual(accel, 100)
        self.assertEqual(brake, 1000)
        self.assertEqual(clutch, 750)
        self.assertEqual(len(buttons), 11)
        self.assertEqual(buttons[0], 1)
        self.assertEqual(buttons[2], 1)

    def test_stream_parser_extended_packets_with_clutch(self):
        parser = StreamParser(payload_len=8)

        axes_val = 512 | (256 << 10) | (128 << 20)
        buttons_val = 0x01
        clutch_val = 450
        payload = (
            axes_val.to_bytes(4, byteorder="little")
            + buttons_val.to_bytes(2, byteorder="little")
            + clutch_val.to_bytes(2, byteorder="little")
        )
        packet = bytes([0xAA, 0x55]) + payload

        packets = parser.parse_bytes(packet)
        self.assertEqual(len(packets), 1)
        steer, accel, brake, buttons, clutch = packets[0]
        self.assertEqual(steer, 512)
        self.assertEqual(accel, 256)
        self.assertEqual(brake, 128)
        self.assertEqual(clutch, 450)
        self.assertEqual(buttons[0], 1)

    def test_stream_parser_clean_packets(self):
        parser = StreamParser()

        axes_val = 512 | (256 << 10) | (128 << 20)
        buttons_val = 0x01
        clutch_val = 0
        payload = axes_val.to_bytes(4, byteorder="little") + buttons_val.to_bytes(2, byteorder="little") + clutch_val.to_bytes(2, byteorder="little")
        packet = bytes([0xAA, 0x55]) + payload

        packets = parser.parse_bytes(packet)
        self.assertEqual(len(packets), 1)
        steer, accel, brake, buttons, clutch = packets[0]
        self.assertEqual(steer, 512)
        self.assertEqual(accel, 256)
        self.assertEqual(brake, 128)
        self.assertEqual(buttons[0], 1)
        self.assertEqual(clutch, 0)

    def test_stream_parser_fragmented_and_noise(self):
        parser = StreamParser()

        axes_val = 1023 | (512 << 10) | (0 << 20)
        buttons_val = 0x07  # botones 0, 1, 2 activos
        clutch_val = 0
        payload = axes_val.to_bytes(4, byteorder="little") + buttons_val.to_bytes(2, byteorder="little") + clutch_val.to_bytes(2, byteorder="little")

        # Alimentar con ruido previo y byte por byte
        noisy_stream = bytes([0x00, 0xFF, 0xAA, 0x12, 0xAA, 0xAA, 0x55]) + payload

        all_packets = []
        for b in noisy_stream:
            res = parser.parse_bytes(bytes([b]))
            all_packets.extend(res)

        self.assertEqual(len(all_packets), 1)
        steer, accel, brake, buttons, clutch = all_packets[0]
        self.assertEqual(steer, 1023)
        self.assertEqual(accel, 512)
        self.assertEqual(brake, 0)
        self.assertEqual(buttons[:3], [1, 1, 1])
        self.assertEqual(clutch, 0)

    def test_pin_names_and_keys_consistency(self):
        self.assertEqual(len(PIN_NAMES), 11)
        self.assertEqual(len(CONFIG_BUTTON_KEYS), 11)
        self.assertIn("D2", PIN_NAMES)
        self.assertIn("btn_map_p2", CONFIG_BUTTON_KEYS)


if __name__ == "__main__":
    unittest.main()
