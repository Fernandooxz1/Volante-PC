"""
Unit and integration tests for PyQt6 dialogs:
- MappingWizardDialog (Guided Full Wizard)
- SingleButtonMapperDialog (Quick Single Mapper)
- CalibrationWizardDialog (Limits & Pedals)
- ThemeDialog (Presets, Custom Color, Language Toggle)
"""

import os
import sys
import tempfile
import time
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

# Ensure QApplication instance
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


from core.config_manager import ConfigManager
from core.engine import Engine
from ui.dialogs.mapping_wizard import (
    MappingWizardDialog,
    SingleButtonMapperDialog,
    TARGET_CONTROLS,
)
from ui.dialogs.calibration_wizard import CalibrationWizardDialog
from ui.dialogs.theme_dialog import ThemeDialog, PRESET_COLORS


@pytest.fixture
def temp_config_file():
    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    temp_file.write("{}")
    temp_file.close()
    yield temp_file.name
    try:
        os.remove(temp_file.name)
    except OSError:
        pass


@pytest.fixture
def config_manager(temp_config_file):
    return ConfigManager(custom_path=temp_config_file)


@pytest.fixture
def engine(config_manager):
    return Engine(config_manager=config_manager, auto_reconnect=False)


def test_target_controls_list():
    expected = [
        "Left Trigger (LT) - Brake",
        "Right Trigger (RT) - Throttle",
        "Steering Wheel Axis",
        "Button A",
        "Button B",
        "Button X",
        "Button Y",
        "Button LB",
        "Button RB",
        "Button Start",
        "Button Back",
        "D-Pad UP",
        "D-Pad DOWN",
        "D-Pad LEFT",
        "D-Pad RIGHT",
    ]
    assert TARGET_CONTROLS == expected


def test_mapping_wizard_flow(qapp, config_manager, engine):
    dialog = MappingWizardDialog(engine=engine, config_manager=config_manager)
    assert dialog.isModal()
    assert dialog._current_step_index == 0
    assert dialog.lbl_action_name.text() == "LEFT TRIGGER (LT) - BRAKE"

    # Step 0: Brake Axis
    engine._emit_input_event("axis", "brake", 700)
    qapp.processEvents()
    assert config_manager.get("brake_target") == "Left Trigger (LT)"

    # Step 1: Throttle Axis
    dialog._advance_step()
    qapp.processEvents()
    time.sleep(0.4)
    engine._emit_input_event("axis", "accel", 800)
    qapp.processEvents()
    assert config_manager.get("accel_target") == "Right Trigger (RT)"

    # Step 2: Steering Wheel Axis
    dialog._advance_step()
    qapp.processEvents()
    time.sleep(0.4)
    engine._emit_input_event("axis", "steer", 900)
    qapp.processEvents()
    assert config_manager.get("steer_target") == "Left Stick X"

    # Step 3: Button A
    dialog._advance_step()
    qapp.processEvents()
    time.sleep(0.4)
    engine._emit_input_event("button", "D6", 1)
    qapp.processEvents()
    assert config_manager.get("btn_map_p6") == "Button A"

    # Step navigation: Skip and Back
    dialog._advance_step()
    qapp.processEvents()
    assert dialog._current_step_index == 4  # Button B
    dialog._on_btn_skip_clicked()
    qapp.processEvents()
    assert dialog._current_step_index == 5  # Button X
    dialog._on_btn_back_clicked()
    qapp.processEvents()
    assert dialog._current_step_index == 4

    dialog.close()


def test_single_button_mapper(qapp, config_manager, engine):
    dialog = SingleButtonMapperDialog(
        target_action="Button X",
        engine=engine,
        config_manager=config_manager
    )
    assert dialog.isModal()
    assert dialog.target_action == "Button X"

    engine._emit_input_event("button", "D5", 1)
    qapp.processEvents()

    assert config_manager.get("btn_map_p5") == "Button X"
    assert dialog.mapped_pin == "Pin D5"
    dialog.close()


def test_calibration_wizard_flow(qapp, config_manager, engine):
    dialog = CalibrationWizardDialog(engine=engine, config_manager=config_manager)
    assert dialog._current_step == 0

    # Step 1: Left limit
    dialog.set_sensor_values(steer=40, accel=0, brake=0)
    qapp.processEvents()
    dialog._on_action_1_clicked()
    qapp.processEvents()
    assert dialog.saved_steer_left == 40

    # Step 2: Center position
    dialog._on_next_step()
    qapp.processEvents()
    assert dialog._current_step == 1
    dialog.set_sensor_values(steer=510, accel=0, brake=0)
    qapp.processEvents()
    dialog._on_action_1_clicked()
    qapp.processEvents()
    assert dialog.saved_steer_center == 510

    # Step 3: Right limit
    dialog._on_next_step()
    qapp.processEvents()
    assert dialog._current_step == 2
    dialog.set_sensor_values(steer=990, accel=0, brake=0)
    qapp.processEvents()
    dialog._on_action_1_clicked()
    qapp.processEvents()
    assert dialog.saved_steer_right == 990

    # Step 4: Pedals
    dialog._on_next_step()
    qapp.processEvents()
    assert dialog._current_step == 3
    dialog.set_sensor_values(steer=510, accel=10, brake=15)
    qapp.processEvents()
    dialog._on_action_1_clicked()  # Rest limits
    qapp.processEvents()
    assert dialog.saved_accel_min == 10
    assert dialog.saved_brake_min == 15

    dialog.set_sensor_values(steer=510, accel=1010, brake=15)
    qapp.processEvents()
    dialog._on_action_2_clicked()  # Throttle max
    assert dialog.saved_accel_max == 1010

    dialog.set_sensor_values(steer=510, accel=10, brake=995)
    qapp.processEvents()
    dialog._on_action_3_clicked()  # Brake max
    assert dialog.saved_brake_max == 995

    # Step 5: Summary and Commit
    dialog._on_next_step()
    qapp.processEvents()
    assert dialog._current_step == 4

    dialog._on_save_config_clicked()
    qapp.processEvents()

    assert config_manager.get("steer_min") == 40
    assert config_manager.get("steer_center") == 510
    assert config_manager.get("steer_max") == 990
    assert config_manager.get("accel_min") == 10
    assert config_manager.get("accel_max") == 1010
    assert config_manager.get("brake_min") == 15
    assert config_manager.get("brake_max") == 995
    assert config_manager.get("invert_steer") is False
    dialog.close()


def test_calibration_wizard_span_validation(qapp, config_manager, engine):
    """Verifica que el asistente de calibración rechaza guardar valores con rango cero o insuficiente."""
    config_manager.set("steer_min", 100)
    config_manager.set("steer_max", 900)
    config_manager.save()

    dialog = CalibrationWizardDialog(engine=engine, config_manager=config_manager)
    # Simular limites iguales (amplitud 0)
    dialog.saved_steer_left = 500
    dialog.saved_steer_center = 500
    dialog.saved_steer_right = 500
    dialog.saved_accel_min = 200
    dialog.saved_accel_max = 200
    dialog.saved_brake_min = 300
    dialog.saved_brake_max = 300

    dialog._current_step = 4
    dialog._update_step_ui()
    qapp.processEvents()

    # Intentar guardar
    dialog._on_save_config_clicked()
    qapp.processEvents()

    # La configuracion previa no debe haberse corrompido
    assert config_manager.get("steer_min") == 100
    assert config_manager.get("steer_max") == 900
    # El dialogo debe seguir abierto (no aceptado) y mostrar error
    assert "ERROR" in dialog.lbl_feedback.text()
    dialog.close()



def test_theme_dialog(qapp, config_manager):
    dialog = ThemeDialog(config_manager=config_manager)
    assert dialog.isModal()

    # Verify presets
    assert len(dialog.preset_cards) == 5
    preset_names = [p[0] for p in PRESET_COLORS]
    for expected_name in ["Cyan Neon", "Racing Red", "Porsche Acid Green", "McLaren Orange", "Tokyo Night Violet"]:
        assert expected_name in preset_names

    # Test preset selection
    dialog._on_preset_clicked("#76FF03")
    qapp.processEvents()
    assert dialog.current_accent == "#76FF03"

    # Test language toggle
    dialog.rb_lang_en.setChecked(True)
    qapp.processEvents()
    assert dialog.current_lang == "en"
    assert "PREFERENCES" in dialog.lbl_main_title.text().upper()

    dialog.rb_lang_es.setChecked(True)
    qapp.processEvents()
    assert dialog.current_lang == "es"
    assert "PREFERENCIAS" in dialog.lbl_main_title.text().upper()

    # Test Save
    dialog._on_save_clicked()
    qapp.processEvents()
    assert config_manager.get_theme_accent() == "#76FF03"
    assert config_manager.get_language() == "es"
    dialog.close()


def test_zero_emojis_in_dialog_files():
    import re
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    dialogs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "dialogs")
    for fname in os.listdir(dialogs_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(dialogs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_pattern.findall(content)
                assert len(matches) == 0, f"Found emoji in {fname}: {matches}"
