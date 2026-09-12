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
