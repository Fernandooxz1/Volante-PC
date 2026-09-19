"""
SteerLockSelector: Selector discreto de bloqueo de grados de giro para Volante-PC.
Reemplaza el deslizador continuo por un conmutador segmentado de 3 posiciones:
- 360° (F1 / Monoplaza)
- 540° (Rally / GT)
- 900° (Calle / Camión)

Dispone de API compatible hacia atrás con QSlider (value(), setValue(), minimum(), maximum(), valueChanged).
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget

try:
    from ui.i18n import tr
except ImportError:
    def tr(key: str) -> str:
        defaults = {
            "sliders.lock_360": "360° F1",
            "sliders.lock_540": "540° Rally",
            "sliders.lock_900": "900° Camión",
        }
        return defaults.get(key, key)


class SteerLockSelector(QFrame):
    """
    Selector segmentado de 3 posiciones (360°, 540°, 900°) para volante de simulación.
    Emite valueChanged(int) al conmutar y ofrece sincronización bidireccional.
    """

    valueChanged = pyqtSignal(int)

    ALLOWED_DEGREES = (360, 540, 900)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("steerLockContainer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_360 = QPushButton(tr("sliders.lock_360"))
        self.btn_540 = QPushButton(tr("sliders.lock_540"))
        self.btn_900 = QPushButton(tr("sliders.lock_900"))

        for btn, val in ((self.btn_360, 360), (self.btn_540, 540), (self.btn_900, 900)):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName(f"steerLockBtn_{val}")
            self.btn_group.addButton(btn, val)
            layout.addWidget(btn)

        self.btn_group.idClicked.connect(self._on_id_clicked)
        self.btn_360.setChecked(True)

    def _on_id_clicked(self, id_val: int) -> None:
        self.valueChanged.emit(id_val)

    def value(self) -> int:
        """Devuelve el valor actual en grados (360, 540 o 900)."""
        val = self.btn_group.checkedId()
        return val if val in self.ALLOWED_DEGREES else 360

    def setValue(self, degrees: int | float) -> None:
        """
        Ajusta el botón activo realizando un snap al grado discreto más próximo.
        Emite valueChanged si el valor seleccionado cambia.
        """
        deg = float(degrees)
        if deg <= 450:
            target = 360
        elif deg <= 720:
            target = 540
        else:
            target = 900

        btn = self.btn_group.button(target)
        if btn is not None:
            prev = self.btn_group.checkedId()
            if not btn.isChecked():
                btn.setChecked(True)
                self.valueChanged.emit(target)
            elif prev != target:
                self.valueChanged.emit(target)

    def minimum(self) -> int:
        """Rango mínimo admitido (360°)."""
        return 360

    def maximum(self) -> int:
        """Rango máximo admitido (900°)."""
        return 900

    def setRange(self, min_val: int, max_val: int) -> None:
        """Compatibilidad no-op con interfaz QSlider."""
        pass

    def retranslate(self) -> None:
        """Actualiza los textos de los botones con el idioma activo."""
        self.btn_360.setText(tr("sliders.lock_360"))
        self.btn_540.setText(tr("sliders.lock_540"))
        self.btn_900.setText(tr("sliders.lock_900"))
