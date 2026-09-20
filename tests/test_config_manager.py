"""Pruebas unitarias para core/config_manager.py."""

import os
import tempfile
import unittest
from core.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_default_config_loading(self):
        mgr = ConfigManager(custom_path=self.temp_file.name)
        self.assertEqual(mgr.get("sensitivity"), 1.0)
        self.assertEqual(mgr.get("steer_center"), 512)
        self.assertIn("F1 RACING", mgr.get_presets_list())

    def test_save_and_reload(self):
        mgr = ConfigManager(custom_path=self.temp_file.name)
        mgr.set("slope", 2.45)
        mgr.save()

        mgr2 = ConfigManager(custom_path=self.temp_file.name)
        self.assertEqual(mgr2.get("slope"), 2.45)

    def test_preset_loading_and_saving(self):
        mgr = ConfigManager(custom_path=self.temp_file.name)
        ok = mgr.load_preset("F1 RACING CRUCETAS")
        self.assertTrue(ok)
        self.assertEqual(mgr.get("active_preset"), "F1 RACING CRUCETAS")
        self.assertEqual(mgr.get("led_color"), "Naranja")

        # Guardar preset nuevo
        mgr.set("slope", 3.0)
        saved = mgr.save_current_as_preset("PRO RACER")
        self.assertTrue(saved)
        self.assertIn("PRO RACER", mgr.get_presets_list())

        # Eliminar preset
        deleted = mgr.delete_preset("PRO RACER")
        self.assertTrue(deleted)
        self.assertNotIn("PRO RACER", mgr.get_presets_list())

    def test_preset_counterpart_detection(self):
        mgr = ConfigManager(custom_path=self.temp_file.name)
        # Búsqueda de gemelos registrados
        self.assertEqual(mgr.get_preset_counterpart("F1 RACING"), "F1 RACING CRUCETAS")
        self.assertEqual(mgr.get_preset_counterpart("F1 RACING CRUCETAS"), "F1 RACING")
        # Coincidencia insensible a mayúsculas
        self.assertEqual(mgr.get_preset_counterpart("f1 racing"), "F1 RACING CRUCETAS")
        self.assertEqual(mgr.get_preset_counterpart("f1 racing crucetas"), "F1 RACING")
        # Presets sin contraparte registrada o entradas inválidas
        self.assertIsNone(mgr.get_preset_counterpart("RALLY / DRIFT"))
        self.assertIsNone(mgr.get_preset_counterpart("SIMULADOR CAMIONES"))
        self.assertIsNone(mgr.get_preset_counterpart("INVENTADO"))
        self.assertIsNone(mgr.get_preset_counterpart(""))
        self.assertIsNone(mgr.get_preset_counterpart("   "))

    def test_save_preset_syncs_counterpart_steering_and_pedals(self):
        mgr = ConfigManager(custom_path=self.temp_file.name)

        # Establecer deadzone a 0.05, steer_lock_deg a 360, filter a 0.25
        mgr.set("deadzone", 0.05)
        mgr.set("steer_lock_deg", 360)
        mgr.set("filter", 0.25)

        # Guardar como "F1 RACING"
        ok = mgr.save_current_as_preset("F1 RACING")
        self.assertTrue(ok)

        # Verificar sincronización en "F1 RACING CRUCETAS" preservando modo y color LED
        crucetas = mgr.config["custom_presets"]["F1 RACING CRUCETAS"]
        self.assertEqual(crucetas["deadzone"], 0.05)
        self.assertEqual(crucetas["steer_lock_deg"], 360)
        self.assertEqual(crucetas["filter"], 0.25)
        self.assertEqual(crucetas["mode"], "Crucetas / D-Pad")
        self.assertEqual(crucetas["led_color"], "Naranja")
        self.assertFalse(crucetas["f1_telemetry"])

        # Modificar deadzone a 0.09 y guardar como "F1 RACING CRUCETAS"
        mgr.set("deadzone", 0.09)
        ok2 = mgr.save_current_as_preset("F1 RACING CRUCETAS")
        self.assertTrue(ok2)

        # Verificar sincronización inversa en "F1 RACING" preservando modo y color LED
        f1 = mgr.config["custom_presets"]["F1 RACING"]
        self.assertEqual(f1["deadzone"], 0.09)
        self.assertEqual(f1["mode"], "Conducción")
        self.assertEqual(f1["led_color"], "Verde")
        self.assertTrue(f1["f1_telemetry"])

        # Verificar que con sync_counterpart=False no se propague
        mgr.set("deadzone", 0.15)
        mgr.save_current_as_preset("F1 RACING", sync_counterpart=False)
        self.assertEqual(mgr.config["custom_presets"]["F1 RACING"]["deadzone"], 0.15)
        self.assertEqual(mgr.config["custom_presets"]["F1 RACING CRUCETAS"]["deadzone"], 0.09)

    def test_preset_button_isolation_between_twins(self):
        """Verifica que los botones no se sobreescriban entre presets gemelos (TRUCK vs TRUCK CRUCETAS)."""
        mgr = ConfigManager(custom_path=self.temp_file.name)

        # Configurar preset TRUCK con botones de acción
        mgr.set("mode", "Conducción")
        mgr.set("steer_lock_deg", 900)
        mgr.set("deadzone", 0.08)
        mgr.set("btn_map_p3", "Button RB (Right Shoulder)")
        mgr.set("btn_map_p6", "Button LB (Left Shoulder)")
        mgr.set("btn_map_pa3", "Button R3 (Right Click)")
        mgr.set("btn_map_p12", "Button L3 (Left Click)")
        self.assertTrue(mgr.save_current_as_preset("TRUCK"))

        # Configurar preset TRUCK CRUCETAS con flechas D-Pad
        mgr.set("mode", "Crucetas / D-Pad")
        mgr.set("steer_lock_deg", 900)
        mgr.set("deadzone", 0.08)
        mgr.set("btn_map_p3", "D-Pad UP")
        mgr.set("btn_map_p6", "D-Pad DOWN")
        mgr.set("btn_map_pa3", "D-Pad RIGHT")
        mgr.set("btn_map_p12", "D-Pad LEFT")
        self.assertTrue(mgr.save_current_as_preset("TRUCK CRUCETAS"))

        # Modificar calibración de pedales en TRUCK y guardar
        mgr.load_preset("TRUCK")
        self.assertEqual(mgr.config.get("btn_map_p3"), "Button RB (Right Shoulder)")
        self.assertEqual(mgr.config.get("btn_map_p6"), "Button LB (Left Shoulder)")

        mgr.set("deadzone", 0.04)
        self.assertTrue(mgr.save_current_as_preset("TRUCK", sync_counterpart=True))

        # Verificar que TRUCK CRUCETAS recibió la nueva calibración pero MANTUVO sus flechas D-Pad
        truck_crucetas = mgr.config["custom_presets"]["TRUCK CRUCETAS"]
        self.assertEqual(truck_crucetas["deadzone"], 0.04)
        self.assertEqual(truck_crucetas["btn_map_p3"], "D-Pad UP")
        self.assertEqual(truck_crucetas["btn_map_p6"], "D-Pad DOWN")
        self.assertEqual(truck_crucetas["btn_map_pa3"], "D-Pad RIGHT")
        self.assertEqual(truck_crucetas["btn_map_p12"], "D-Pad LEFT")

        # Cargar TRUCK CRUCETAS y verificar que la configuración activa toma las flechas
        self.assertTrue(mgr.load_preset("TRUCK CRUCETAS"))
        self.assertEqual(mgr.config.get("btn_map_p3"), "D-Pad UP")
        self.assertEqual(mgr.config.get("btn_map_p6"), "D-Pad DOWN")

        # Cargar TRUCK y verificar que la configuración activa retoma los botones de hombro
        self.assertTrue(mgr.load_preset("TRUCK"))
        self.assertEqual(mgr.config.get("btn_map_p3"), "Button RB (Right Shoulder)")
        self.assertEqual(mgr.config.get("btn_map_p6"), "Button LB (Left Shoulder)")


if __name__ == "__main__":
    unittest.main()

