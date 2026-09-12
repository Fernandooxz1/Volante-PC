"""Pruebas unitarias para core/calibration.py."""

import unittest
from core.calibration import (
    calculate_pedal,
    calculate_steering,
    evaluate_curve_point,
    generate_curve_points,
)


class TestCalibration(unittest.TestCase):

    def test_calculate_steering_center(self):
        val, x_phys, y_out = calculate_steering(
            steer=512,
            steer_min=0,
            steer_center=512,
            steer_max=1023,
            slope=1.0,
            sensitivity=1.0,
            rest_deadzone=0.01,
        )
        self.assertEqual(val, 0)
        self.assertAlmostEqual(x_phys, 0.0)
        self.assertAlmostEqual(y_out, 0.0)

    def test_calculate_steering_full_left_right(self):
        # Giro completo a la izquierda (0)
        val_l, x_l, y_l = calculate_steering(
            steer=0,
            steer_min=0,
            steer_center=512,
            steer_max=1023,
            slope=1.0,
            sensitivity=1.0,
            rest_deadzone=0.01,
        )
        self.assertEqual(val_l, -32767)
        self.assertAlmostEqual(x_l, -1.0)
        self.assertAlmostEqual(y_l, -1.0)

        # Giro completo a la derecha (1023)
        val_r, x_r, y_r = calculate_steering(
            steer=1023,
            steer_min=0,
            steer_center=512,
            steer_max=1023,
            slope=1.0,
            sensitivity=1.0,
            rest_deadzone=0.01,
        )
        self.assertEqual(val_r, 32767)
        self.assertAlmostEqual(x_r, 1.0)
        self.assertAlmostEqual(y_r, 1.0)

    def test_calculate_steering_rest_deadzone(self):
        # Pequeña desviación dentro de la zona muerta de descanso (1%)
        # 512 + 2 = 514 -> x = 2 / 511 ~= 0.0039 < 0.01
        val, x_phys, y_out = calculate_steering(
            steer=514,
            steer_min=0,
            steer_center=512,
            steer_max=1023,
            rest_deadzone=0.01,
        )
        self.assertEqual(val, 0)
        self.assertEqual(y_out, 0.0)

    def test_calculate_steering_anti_deadzone(self):
        # Con anti-deadzone = 0.2, una vez superada la zona muerta de descanso
        val, x_phys, y_out = calculate_steering(
            steer=550,
            steer_min=0,
            steer_center=512,
            steer_max=1023,
            anti_deadzone=0.2,
            rest_deadzone=0.01,
        )
        self.assertGreater(y_out, 0.2)
        self.assertGreater(val, int(0.2 * 32767))

    def test_calculate_pedal_limits_and_deadzone(self):
        # Mínimo exacto
        val, pct = calculate_pedal(raw_val=0, val_min=0, val_max=1023, deadzone=0.1, max_output=255)
        self.assertEqual(val, 0)
        self.assertEqual(pct, 0.0)

        # Dentro de la zona muerta (10%)
        val_dz, pct_dz = calculate_pedal(raw_val=50, val_min=0, val_max=1023, deadzone=0.1, max_output=255)
        self.assertEqual(val_dz, 0)
        self.assertEqual(pct_dz, 0.0)

        # Máximo
        val_max, pct_max = calculate_pedal(raw_val=1023, val_min=0, val_max=1023, deadzone=0.1, max_output=255)
        self.assertEqual(val_max, 255)
        self.assertAlmostEqual(pct_max, 1.0)

    def test_evaluate_and_generate_curve(self):
        points = generate_curve_points(slope=1.85, sensitivity=1.0, anti_deadzone=0.0, num_points=21)
        self.assertEqual(len(points), 21)
        self.assertAlmostEqual(points[0][0], -1.0)
        self.assertAlmostEqual(points[-1][0], 1.0)
        # Monotonía de la curva
        for i in range(len(points) - 1):
            self.assertLessEqual(points[i][1], points[i + 1][1])


if __name__ == "__main__":
    unittest.main()
