"""
Módulo de calibración y modelos matemáticos de respuesta para Volante-PC.
Implementa:
- Normalización asimétrica de límites físicos (izq/centro/der).
- Curva exponencial de dirección (Steering Expo) con control de pendiente y sensibilidad.
- Filtro de zona muerta neutra (Rest Deadzone) y compensación de zona muerta de juegos (Anti-Deadzone).
- Procesamiento de pedales con zonas muertas configurables.
- Generador de puntos para visualización gráfica en tiempo real.
"""

from typing import List, Tuple


def calculate_steering(
    steer: int,
    steer_min: int = 0,
    steer_center: int = 512,
    steer_max: int = 1023,
    slope: float = 1.0,
    sensitivity: float = 1.0,
    anti_deadzone: float = 0.0,
    rest_deadzone: float = 0.01
) -> Tuple[int, float, float]:
    """
    Calcula el valor final del eje de dirección para el gamepad virtual.
    
    :return: Tupla con (valor_int_32767, x_normalizado, y_salida_normalizado)
             valor_int_32767: -32768 a 32767 para el stick virtual de Xbox.
             x_normalizado: -1.0 a 1.0 (posición física relativa al centro).
             y_salida_normalizado: -1.0 a 1.0 (posición después de aplicar expo y anti-deadzone).
    """
    # 1. Normalización asimétrica respecto al centro físico real
    if steer < steer_center:
        range_left = steer_center - steer_min
        x = (steer - steer_center) / range_left if range_left > 0 else 0.0
        x = max(-1.0, min(0.0, x))
    else:
        range_right = steer_max - steer_center
        x = (steer - steer_center) / range_right if range_right > 0 else 0.0
        x = max(0.0, min(1.0, x))

    # 2. Curva Exponencial
    abs_x = abs(x)
    sign = 1.0 if x >= 0 else -1.0
    x_expo = sign * (abs_x ** max(0.1, slope))

    # 3. Escalado por sensibilidad
    x_sloped = max(-1.0, min(1.0, x_expo * sensitivity))

    # 4. Zona muerta física de descanso y Anti-Deadzone
    abs_val = abs(x_sloped)
    sloped_sign = 1.0 if x_sloped >= 0 else -1.0

    if abs_val <= rest_deadzone:
        y_final = 0.0
    else:
        scaled = (abs_val - rest_deadzone) / (1.0 - rest_deadzone)
        scaled = max(0.0, min(1.0, scaled))
        y_final = sloped_sign * (anti_deadzone + (1.0 - anti_deadzone) * scaled)

    # 5. Mapeo a entero de 16 bits firmado (-32768 a 32767)
    val_int = int(round(y_final * 32767))
    val_int = max(-32768, min(32767, val_int))

    return val_int, x, y_final


def calculate_pedal(
    raw_val: int,
    val_min: int = 0,
    val_max: int = 1023,
    deadzone: float = 0.0,
    max_output: int = 255
) -> Tuple[int, float]:
    """
    Calcula la respuesta del acelerador o freno.
    
    :return: (valor_entero_salida, porcentaje_0_a_1)
    """
    range_val = val_max - val_min
    if range_val <= 0:
        return 0, 0.0

    val_norm = (raw_val - val_min) / range_val
    val_norm = max(0.0, min(1.0, val_norm))

    if val_norm <= deadzone:
        return 0, 0.0

    if deadzone >= 0.999:
        val_scaled = 1.0
    else:
        val_scaled = (val_norm - deadzone) / (1.0 - deadzone)

    val_scaled = max(0.0, min(1.0, val_scaled))
    out_int = int(round(val_scaled * max_output))
    out_int = max(0, min(max_output, out_int))

    return out_int, val_scaled


def evaluate_curve_point(
    x: float,
    slope: float = 1.0,
    sensitivity: float = 1.0,
    anti_deadzone: float = 0.0,
    rest_deadzone: float = 0.01
) -> float:
    """Evalúa la salida matemática para un valor de entrada x en [-1.0, 1.0]."""
    abs_x = abs(x)
    sign = 1.0 if x >= 0 else -1.0
    x_expo = sign * (abs_x ** max(0.1, slope))
    x_sloped = max(-1.0, min(1.0, x_expo * sensitivity))

    abs_val = abs(x_sloped)
    sloped_sign = 1.0 if x_sloped >= 0 else -1.0

    if abs_val <= rest_deadzone:
        return 0.0

    scaled = (abs_val - rest_deadzone) / (1.0 - rest_deadzone)
    scaled = max(0.0, min(1.0, scaled))
    return sloped_sign * (anti_deadzone + (1.0 - anti_deadzone) * scaled)


def generate_curve_points(
    slope: float,
    sensitivity: float,
    anti_deadzone: float,
    num_points: int = 100
) -> List[Tuple[float, float]]:
    """Genera una lista de puntos (x, y) para graficar la curva en la interfaz."""
    points = []
    step = 2.0 / (num_points - 1)
    for i in range(num_points):
        x = -1.0 + i * step
        y = evaluate_curve_point(x, slope, sensitivity, anti_deadzone)
        points.append((x, y))
    return points
