"""Pruebas unitarias para el receptor de telemetría UDP de F1 (core/f1_telemetry.py)."""

import struct
import time
import unittest
from core.f1_telemetry import F1TelemetryReceiver, PACKET_ID_CAR_TELEMETRY


def make_f1_packet(
    packet_format: int = 2021,
    player_car_idx: int = 0,
    speed: int = 240,
    gear: int = 6,
    rpm: int = 11200,
    rev_lights_pct: int = 85,
    packet_id: int = PACKET_ID_CAR_TELEMETRY,
) -> bytes:
    """Construye un paquete sintético de telemetría de F1 para pruebas."""
    if packet_format >= 2023:
        header = bytearray(29)
        struct.pack_into("<H", header, 0, packet_format)
        header[5] = packet_id
        header[27] = player_car_idx
    else:
        header = bytearray(24)
        struct.pack_into("<H", header, 0, packet_format)
        header[5] = packet_id
        header[22] = player_car_idx

    car_entry_size = 60
    car_data = bytearray(car_entry_size * 22)
    offset = player_car_idx * car_entry_size

    struct.pack_into("<H", car_data, offset + 0, speed)
    struct.pack_into("<b", car_data, offset + 15, gear)
    struct.pack_into("<H", car_data, offset + 16, rpm)
    car_data[offset + 18] = 1  # DRS
    car_data[offset + 19] = rev_lights_pct

    return bytes(header + car_data)


class TestF1Telemetry(unittest.TestCase):

    def setUp(self):
        self.receiver = F1TelemetryReceiver(port=20778)  # Puerto alternativo para pruebas

    def tearDown(self):
        self.receiver.stop()

    def test_initial_state(self):
        self.assertFalse(self.receiver.is_running)
        self.assertFalse(self.receiver.is_active)
        data = self.receiver.get_telemetry_data()
        self.assertFalse(data["active"])
        self.assertEqual(data["rpm"], 0)
        self.assertIsNone(self.receiver.get_shift_led_color())

    def test_parse_f1_2021_packet(self):
        packet = make_f1_packet(
            packet_format=2021,
            player_car_idx=0,
            speed=285,
            gear=7,
            rpm=11800,
            rev_lights_pct=88,
        )
        success = self.receiver.process_packet(packet)
        self.assertTrue(success)
        self.assertTrue(self.receiver.is_active)

        data = self.receiver.get_telemetry_data()
        self.assertTrue(data["active"])
        self.assertEqual(data["speed"], 285)
        self.assertEqual(data["gear"], 7)
        self.assertEqual(data["rpm"], 11800)
        self.assertEqual(data["rev_lights_percent"], 88)

    def test_parse_f1_2023_packet(self):
        packet = make_f1_packet(
            packet_format=2023,
            player_car_idx=3,
            speed=310,
            gear=8,
            rpm=12500,
            rev_lights_pct=96,
        )
        success = self.receiver.process_packet(packet)
        self.assertTrue(success)
        self.assertTrue(self.receiver.is_active)

        data = self.receiver.get_telemetry_data()
        self.assertEqual(data["speed"], 310)
        self.assertEqual(data["gear"], 8)
        self.assertEqual(data["rpm"], 12500)
        self.assertEqual(data["rev_lights_percent"], 96)

    def test_ignore_other_packets(self):
        # Paquete que no es PacketCarTelemetryData (ej. Packet ID = 1 Session)
        packet = make_f1_packet(packet_id=1)
        success = self.receiver.process_packet(packet)
        self.assertFalse(success)
        self.assertFalse(self.receiver.is_active)

    def test_shift_led_color_thresholds(self):
        # 0% -> None (base color)
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=0))
        self.assertIsNone(self.receiver.get_shift_led_color())

        # 25% (1..40%) -> Verde
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=25))
        self.assertEqual(self.receiver.get_shift_led_color(), "Verde")

        # 55% (41..70%) -> Amarillo
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=55))
        self.assertEqual(self.receiver.get_shift_led_color(), "Amarillo")

        # 80% (71..90%) -> Rojo
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=80))
        self.assertEqual(self.receiver.get_shift_led_color(), "Rojo")

        # 95% (91..100%) -> Azul (punto óptimo de cambio)
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=95))
        self.assertEqual(self.receiver.get_shift_led_color(), "Azul")

    def test_timeout_liveness(self):
        self.receiver.process_packet(make_f1_packet(rev_lights_pct=95))
        self.assertTrue(self.receiver.is_active)
        self.assertEqual(self.receiver.get_shift_led_color(), "Azul")

        # Simular paso del tiempo > 2.0 segundos
        with self.receiver._lock:
            self.receiver._last_packet_time = time.time() - 3.0

        self.assertFalse(self.receiver.is_active)
        self.assertIsNone(self.receiver.get_shift_led_color())

    def test_start_stop_lifecycle(self):
        started = self.receiver.start()
        self.assertTrue(started)
        self.assertTrue(self.receiver.is_running)

        # Iniciar dos veces es idempotente
        self.assertTrue(self.receiver.start())

        self.receiver.stop()
        self.assertFalse(self.receiver.is_running)
