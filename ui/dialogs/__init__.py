"""
Dialog components for Volante-PC.
Includes input mapping wizard, pedal and steering calibration wizard, and theme customization dialog.
All dialogs follow a clean, high-contrast, minimalist motorsport aesthetic with zero emojis.
"""

from ui.dialogs.mapping_wizard import MappingWizardDialog, SingleButtonMapperDialog
from ui.dialogs.calibration_wizard import CalibrationWizardDialog
from ui.dialogs.theme_dialog import ThemeDialog

__all__ = [
    "MappingWizardDialog",
    "SingleButtonMapperDialog",
    "CalibrationWizardDialog",
    "ThemeDialog",
]
