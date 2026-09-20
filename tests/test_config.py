"""
Pruebas unitarias para core/config_manager.py.
Verifica la persistencia atómica, carga segura con fallbacks de fábrica,
fusión de configuración y ciclo de vida de presets personalizados.
"""

import json
import os
import threading
import pytest
from core.config_manager import ConfigManager, DEFAULT_CONFIG


@pytest.fixture
def temp_config_path(tmp_path):
    """Provee una ruta temporal aislada para cada prueba."""
    return str(tmp_path / "config_volante_test.json")


def test_config_load_default(temp_config_path):
    """Verifica que al no existir archivo previo, se inicialice con la configuración por defecto."""
    manager = ConfigManager(custom_path=temp_config_path)
    assert manager.get("sensitivity") == DEFAULT_CONFIG["sensitivity"]
    assert manager.get("slope") == DEFAULT_CONFIG["slope"]
    assert "F1 RACING" in manager.get_presets_list()
    assert manager.get("active_preset") == "Personalizado"


def test_config_atomic_save_and_reload(temp_config_path):
    """Verifica la persistencia en disco atómica y la recarga en una nueva instancia."""
    manager = ConfigManager(custom_path=temp_config_path)
    manager.set("sensitivity", 0.77)
    manager.set("slope", 2.45)
    manager.set("led_color", "Rojo")
    success = manager.save()
    assert success is True

    # Verificar que el archivo existe en disco y no quedan archivos temporales residuales
    assert os.path.exists(temp_config_path)
    assert not os.path.exists(temp_config_path + ".tmp")

    # Leer el archivo con un nuevo ConfigManager
    reloaded = ConfigManager(custom_path=temp_config_path)
    assert reloaded.get("sensitivity") == 0.77
    assert reloaded.get("slope") == 2.45
    assert reloaded.get("led_color") == "Rojo"


def test_config_presets_list(temp_config_path):
    """Verifica que los presets de fábrica y 'Personalizado' figuren en la lista."""
    manager = ConfigManager(custom_path=temp_config_path)
    presets = manager.get_presets_list()
    for factory in ("F1 RACING", "F1 RACING CRUCETAS", "RALLY / DRIFT", "SIMULADOR CAMIONES", "Personalizado"):
        assert factory in presets


def test_preset_save_load_lifecycle(temp_config_path):
    """Verifica el ciclo completo de guardar, cargar y restaurar un preset nombrado."""
    manager = ConfigManager(custom_path=temp_config_path)

    # Configurar parámetros específicos
    manager.update({
        "sensitivity": 0.42,
        "slope": 2.8,
        "deadzone": 0.05,
        "filter": 0.35,
        "led_color": "Amarillo",
        "btn_map_p2": "Button A"
    }, auto_save=False)

    preset_name = "DRIFT_PRO_2026"
    saved = manager.save_current_as_preset(preset_name)
    assert saved is True
    assert preset_name in manager.get_presets_list()
    assert manager.get("active_preset") == preset_name

    # Modificar valores en el perfil activo
    manager.update({
        "sensitivity": 1.5,
        "slope": 1.0,
        "led_color": "Azul"
    }, auto_save=True)
    assert manager.get("sensitivity") == 1.5

    # Cargar el preset previamente guardado
    loaded = manager.load_preset(preset_name)
    assert loaded is True
    assert manager.get("sensitivity") == 0.42
    assert manager.get("slope") == 2.8
    assert manager.get("led_color") == "Amarillo"
    assert manager.get("active_preset") == preset_name


def test_preset_deletion(temp_config_path):
    """Verifica la eliminación de un preset y el retorno seguro a 'Personalizado'."""
    manager = ConfigManager(custom_path=temp_config_path)
    preset_name = "PRESET_TEMP"
    manager.save_current_as_preset(preset_name)
    assert preset_name in manager.get_presets_list()

    deleted = manager.delete_preset(preset_name)
    assert deleted is True
    assert preset_name not in manager.get_presets_list()
    assert manager.get("active_preset") == "Personalizado"


def test_invalid_preset_names(temp_config_path):
    """Verifica el rechazo de nombres vacíos o reservados."""
    manager = ConfigManager(custom_path=temp_config_path)
    assert manager.save_current_as_preset("") is False
    assert manager.save_current_as_preset("   ") is False
    assert manager.save_current_as_preset("Personalizado") is False


def test_config_thread_safety(temp_config_path):
    """Verifica que lecturas y escrituras simultáneas en múltiples hilos no generen race conditions."""
    manager = ConfigManager(custom_path=temp_config_path)
    errors = []

    def writer():
        try:
            for i in range(50):
                manager.set("test_key", i)
                manager.save()
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for _ in range(50):
                manager.get("test_key")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(3)] + \
              [threading.Thread(target=reader) for _ in range(3)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_preset_counterpart_detection(temp_config_path):
    """Verifica la detección bidireccional e insensible a mayúsculas de presets contraparte."""
    manager = ConfigManager(custom_path=temp_config_path)
    assert manager.get_preset_counterpart("F1 RACING") == "F1 RACING CRUCETAS"
    assert manager.get_preset_counterpart("F1 RACING CRUCETAS") == "F1 RACING"
    assert manager.get_preset_counterpart("f1 racing") == "F1 RACING CRUCETAS"
    assert manager.get_preset_counterpart("f1 racing crucetas") == "F1 RACING"
    assert manager.get_preset_counterpart("RALLY / DRIFT") is None
    assert manager.get_preset_counterpart("SIMULADOR CAMIONES") is None
    assert manager.get_preset_counterpart("INEXISTENTE") is None
    assert manager.get_preset_counterpart("") is None
    assert manager.get_preset_counterpart("   ") is None


def test_save_preset_syncs_counterpart_steering_and_pedals(temp_config_path):
    """Verifica la sincronización de sintonía compartida preservando modo y color LED en el gemelo."""
    manager = ConfigManager(custom_path=temp_config_path)

    # Configurar valores específicos de dirección y pedales
    manager.set("deadzone", 0.05)
    manager.set("steer_lock_deg", 360)
    manager.set("filter", 0.25)

    # Guardar en "F1 RACING"
    success = manager.save_current_as_preset("F1 RACING")
    assert success is True

    # Verificar que el gemelo "F1 RACING CRUCETAS" fue actualizado pero preserva modo y LED
    crucetas = manager.config["custom_presets"]["F1 RACING CRUCETAS"]
    assert crucetas["deadzone"] == 0.05
    assert crucetas["steer_lock_deg"] == 360
    assert crucetas["filter"] == 0.25
    assert crucetas["mode"] == "Crucetas / D-Pad"
    assert crucetas["led_color"] == "Naranja"
    assert crucetas["f1_telemetry"] is False

    # Modificar deadzone a 0.09 y guardar como "F1 RACING CRUCETAS"
    manager.set("deadzone", 0.09)
    success2 = manager.save_current_as_preset("F1 RACING CRUCETAS")
    assert success2 is True

    # Verificar sincronización hacia "F1 RACING" preservando modo y LED
    f1 = manager.config["custom_presets"]["F1 RACING"]
    assert f1["deadzone"] == 0.09
    assert f1["mode"] == "Conducción"
    assert f1["led_color"] == "Verde"
    assert f1["f1_telemetry"] is True

