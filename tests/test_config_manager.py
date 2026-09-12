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


if __name__ == "__main__":
    unittest.main()
