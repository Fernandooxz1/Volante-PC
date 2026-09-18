#!/usr/bin/env python3
"""
Script de verificación de hardware para ESP32 Standalone (Volante-PC).
Lee en vivo:
- Volante (AS5600)
- Acelerador (SS49E Hall)
- Prueba interactiva de los 5 NeoPixels (RPM Shift Lights)
"""

import os
import sys
import time
import struct
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import serial
from core.engine import auto_detect_arduino_port


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else auto_detect_arduino_port()
    if not port:
        print("❌ No se encontró ningún dispositivo ESP32 conectado.")
        sys.exit(1)

    print(f"🔌 Conectando a {port} a 115200 baud...")
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"❌ Error abriendo puerto: {e}")
        sys.exit(1)

    print("✅ Conectado exitosamente con la ESP32!\n")
    print("---------------------------------------------------------------")
    print(" 🎮 TEST EN VIVO DE SENSORES Y LEDS (Presiona Ctrl+C para salir)")
    print("---------------------------------------------------------------")
    print("Probando barrido de los 8 LEDs NeoPixel...")

    # Barrido progresivo F1 (4 Rojos -> 4 Azules)
    test_levels = [22, 37, 52, 67, 77, 85, 92, 96]
    for pct in test_levels:
        ser.write(bytes([0xBB, 0x77, pct]))
        ser.flush()
        time.sleep(0.35)

    # Destello de cambio de marcha (Shift Flash)
    for _ in range(6):
        ser.write(bytes([0xBB, 0x77, 98]))
        ser.flush()
        time.sleep(0.08)

    # Apagar LEDs
    ser.write(bytes([0xBB, 0x77, 0]))
    ser.flush()
    time.sleep(0.2)

    print("✅ Barrido de 8 LEDs completado.")
    print("Mueve el volante y presiona el pedal para ver las lecturas en vivo:\n")

    min_accel = 1023
    max_accel = 0

    try:
        while True:
            header = ser.read(2)
            if header == b"\xaa\x55":
                payload = ser.read(6)
                if len(payload) == 6:
                    axes, buttons = struct.unpack("<IH", payload)
                    steer = axes & 0x3FF
                    accel = (axes >> 10) & 0x3FF
                    brake = (axes >> 20) & 0x3FF

                    if accel < min_accel: min_accel = accel
                    if accel > max_accel: max_accel = accel

                    # Barra visual para volante (centro ~512)
                    steer_pos = max(0, min(29, int((steer / 1023.0) * 29)))
                    steer_bar = [" "] * 30
                    steer_bar[15] = "|"
                    steer_bar[steer_pos] = "O"
                    steer_str = "".join(steer_bar)

                    # Barra visual para acelerador
                    accel_bars = max(0, min(20, int((accel / 1023.0) * 20)))
                    accel_str = "█" * accel_bars + "░" * (20 - accel_bars)

                    # Botones de la matriz activos (12 posibles)
                    active_btns = [f"B{i+1}" for i in range(12) if (buttons & (1 << i))]
                    btns_str = ",".join(active_btns) if active_btns else "---"

                    sys.stdout.write(
                        f"\r[Vol: {steer:4d} [{steer_str}]] "
                        f"[Pedal: {accel:4d} [{accel_str}]] "
                        f"[Botones: {btns_str:12s}]"
                    )
                    sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\nApagando LEDs y cerrando conexión...")
        ser.write(bytes([0xBB, 0x77, 0]))
        ser.flush()
        ser.close()
        print("Listo.")


if __name__ == "__main__":
    main()
