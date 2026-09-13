"""Pruebas unitarias para el puente de telemetría ESP32 (core/esp32_bridge.py)."""

import time
import unittest
from unittest.mock import MagicMock

from core.esp32_bridge import (
    ESP32Bridge,
    decode_esp32_telemetry,
    encode_esp32_telemetry,
)
from core.f1_telemetry import F1TelemetryReceiver
from tests.test_f1_telemetry import make_f1_packet


class TestESP32Bridge(unittest.TestCase):

    def test_encode_decode_telemetry(self):
        payload = encode_esp32_telemetry(
            rpm=11500,
            gear=6,
            speed=280,
            rev_lights_percent=95,
            drs=1,
        )
        self.assertEqual(len(payload), 9)

        decoded = decode_esp32_telemetry(payload)
        self.assertIsNotNone(decoded)
        rpm, gear, speed, revs, drs = decoded
        self.assertEqual(rpm, 11500)
        self.assertEqual(gear, 6)
        self.assertEqual(speed, 280)
        self.assertEqual(revs, 95)
        self.assertEqual(drs, 1)

    def test_decode_reverse_and_neutral(self):
        # Reversa (-1) y neutral (0)
        p_rev = encode_esp32_telemetry(rpm=4000, gear=-1, speed=15)
        self.assertEqual(decode_esp32_telemetry(p_rev)[1], -1)

        p_neu = encode_esp32_telemetry(rpm=2500, gear=0, speed=0)
        self.assertEqual(decode_esp32_telemetry(p_neu)[1], 0)

    def test_decode_fallback_compatibility(self):
        # Simular paquete antiguo de 5 bytes <HbH
        import struct
        old_packet = struct.pack("<HbH", 9000, 4, 160)
        decoded = decode_esp32_telemetry(old_packet)
        self.assertIsNotNone(decoded)
        rpm, gear, speed, revs, drs = decoded
        self.assertEqual(rpm, 9000)
        self.assertEqual(gear, 4)
        self.assertEqual(speed, 160)
        self.assertEqual(revs, 0)
        self.assertEqual(drs, 0)

    def test_decode_invalid_data(self):
        self.assertIsNone(decode_esp32_telemetry(b""))
        self.assertIsNone(decode_esp32_telemetry(b"1234"))
        self.assertIsNone(decode_esp32_telemetry(b"\x00" * 9))

    def test_bridge_lifecycle_and_send(self):
        bridge = ESP32Bridge(host="127.0.0.1", port=20789, rate_limit_hz=100.0)
        self.assertTrue(bridge.start())
        self.assertTrue(bridge.is_running)

        sent = bridge.send_telemetry(rpm=8000, gear=3, speed=120, rev_lights_percent=50, drs=0)
        self.assertTrue(sent)
        self.assertEqual(bridge.packets_sent, 1)

        bridge.stop()
        self.assertFalse(bridge.is_running)

    def test_bridge_rate_limiting(self):
        # Límite bajo: 5 Hz = 200 ms entre paquetes
        bridge = ESP32Bridge(host="127.0.0.1", port=20790, rate_limit_hz=5.0)
        bridge.start()

        # Primer envío pasa
        self.assertTrue(bridge.send_telemetry(rpm=5000, gear=2, speed=60))
        # Envío inmediato debe ser ignorado por rate limiter
        self.assertFalse(bridge.send_telemetry(rpm=5100, gear=2, speed=62))

        bridge.stop()

    def test_f1_receiver_integration(self):
        mock_bridge = MagicMock()
        receiver = F1TelemetryReceiver(port=20791, esp32_bridge=mock_bridge)

        packet = make_f1_packet(
            speed=255,
            gear=7,
            rpm=12400,
            rev_lights_pct=88,
        )
        processed = receiver.process_packet(packet)
        self.assertTrue(processed)

        mock_bridge.send_telemetry.assert_called_once_with(
            rpm=12400,
            gear=7,
            speed=255,
            rev_lights_percent=88,
            drs=1,
        )
