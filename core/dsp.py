"""
Procesamiento Digital de Señales (DSP) para Volante-PC.
Implementa limitador de variación (Slew Rate Limiter) y filtro de media móvil exponencial (EMA)
para suprimir el ruido y vibraciones (jitter) producidos por potenciómetros con desgaste.
"""


class SteeringFilter:
    """
    Filtro híbrido paso bajo con limitador de pendiente (slew rate limiter)
    y filtro exponencial (EMA) adaptativo.
    """
    def __init__(self):
        self.last_filtered_steer: float = 512.0
        self.initialized: bool = False

    def reset(self, initial_value: float = 512.0) -> None:
        """Reinicia el estado del filtro a un valor neutral conocido."""
        self.last_filtered_steer = float(initial_value)
        self.initialized = False

    def process(self, steer: int, filter_strength: float) -> int:
        """
        Procesa el valor del sensor de dirección (0..1023) aplicando el filtro anti-ruido.
        
        :param steer: Valor crudo del sensor (0..1023).
        :param filter_strength: Fuerza del filtro (0.0 a 0.9). Si es 0.0, no filtra.
        :return: Valor filtrado y suavizado (0..1023).
        """
        if not self.initialized:
            self.last_filtered_steer = float(steer)
            self.initialized = True
            return steer

        if filter_strength <= 0.001:
            self.last_filtered_steer = float(steer)
            return steer

        # 1. Slew Rate Limiter: Limita el salto máximo por muestra según la fuerza
        max_change = 15.0 + (1.0 - filter_strength) * 35.0
        diff = float(steer) - self.last_filtered_steer

        if abs(diff) > max_change:
            step = max_change if diff > 0 else -max_change
            steer_filtered = self.last_filtered_steer + step
        else:
            steer_filtered = float(steer)

        # 2. Filtro Exponencial (EMA)
        alpha = max(0.05, 1.0 - filter_strength)
        steer_smoothed = alpha * steer_filtered + (1.0 - alpha) * self.last_filtered_steer

        self.last_filtered_steer = steer_smoothed
        return int(round(steer_smoothed))
