"""Pruebas unitarias para core/dsp.py."""

import unittest
from core.dsp import SteeringFilter


class TestDSP(unittest.TestCase):

    def test_initial_sample(self):
        f = SteeringFilter()
        out = f.process(300, 0.5)
        self.assertEqual(out, 300)
        self.assertTrue(f.initialized)

    def test_filter_disabled(self):
        f = SteeringFilter()
        f.process(512, 0.0)
        out = f.process(800, 0.0)
        self.assertEqual(out, 800)

    def test_slew_rate_limiter_and_ema(self):
        f = SteeringFilter()
        f.process(512, 0.8)

        # Salto brusco a 1023 (posible ruido o glitch de potenciómetro gastado)
        filtered = f.process(1023, 0.8)

        # Con filter_strength = 0.8:
        # max_change = 15 + (1 - 0.8) * 35 = 22
        # steer_filtered = 512 + 22 = 534
        # alpha = max(0.05, 1 - 0.8) = 0.2
        # steer_smoothed = 0.2 * 534 + 0.8 * 512 = 106.8 + 409.6 = 516.4 -> 516
        self.assertLess(filtered, 600)
        self.assertGreater(filtered, 512)

    def test_reset(self):
        f = SteeringFilter()
        f.process(1000, 0.5)
        f.reset(512.0)
        self.assertFalse(f.initialized)
        self.assertEqual(f.last_filtered_steer, 512.0)


if __name__ == "__main__":
    unittest.main()
