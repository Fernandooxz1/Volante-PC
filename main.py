#!/usr/bin/env python3
"""
Volante-PC: Punto de entrada unificado para Linux y Windows.

Soporta:
1. Modo Gráfico PyQt6 Motorsport DDU (Predeterminado): python main.py
2. Modo Daemon / Background Headless (<15MB RAM):      python main.py --daemon
3. Modo Consola / Terminal ASCII Dashboard:           python main.py --cli
"""

import argparse
import os
import signal
import sys
import time

# Configuración automática para entornos Wayland / Hyprland en Linux
if sys.platform.startswith("linux") and "WAYLAND_DISPLAY" in os.environ:
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")


def run_daemon(port: str | None = None) -> None:
    """Ejecuta el motor en segundo plano sin dependencias de GUI (<15MB RAM)."""
    from core.config_manager import ConfigManager
    from core.engine import Engine, auto_detect_arduino_port
    from core.gamepad import check_gamepad_prerequisites

    print("[Volante-PC] Iniciando en modo Daemon / Headless...")
    can_init, msg = check_gamepad_prerequisites()
    if not can_init:
        print(f"[ADVERTENCIA] {msg}")

    config_mgr = ConfigManager()
    selected_port = port or auto_detect_arduino_port()
    engine = Engine(config_manager=config_mgr, port=selected_port)
    engine.start()

    print(f"[Volante-PC] Motor activo a 100 Hz. Puerto: {selected_port or 'Autodetección'}")
    print("[Volante-PC] Presiona Ctrl+C para detener el daemon.")

    running = True

    def handle_signal(sig, frame):
        nonlocal running
        print("\n[Volante-PC] Señal recibida. Deteniendo motor...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while running:
            time.sleep(1.0)
    finally:
        engine.stop()
        print("[Volante-PC] Motor detenido. Saliendo.")


def run_cli_dashboard(port: str | None = None) -> None:
    """Ejecuta el dashboard interactivo ASCII en terminal."""
    from core.config_manager import ConfigManager
    from core.engine import Engine, auto_detect_arduino_port
    from core.protocol import PIN_NAMES

    config_mgr = ConfigManager()
    selected_port = port or auto_detect_arduino_port()
    engine = Engine(config_manager=config_mgr, port=selected_port)
    engine.start()

    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Ocultar cursor y limpiar pantalla
    sys.stdout.write("\033[?25l\033[2J")
    sys.stdout.flush()

    try:
        while running:
            snap = engine.get_telemetry()

            # Visualización de barra de dirección (-90° a +90°)
            steer_chars = 30
            center_idx = steer_chars // 2
            norm_x = snap.steer_phys_norm  # -1.0 a 1.0
            steer_pos = int(center_idx + (norm_x * center_idx))
            steer_pos = max(0, min(steer_chars - 1, steer_pos))

            steer_bar = [" "] * steer_chars
            steer_bar[center_idx] = "|"
            steer_bar[steer_pos] = "O"
            steer_bar_str = "".join(steer_bar)

            # Barras de acelerador y freno
            throttle_bars = int(snap.throttle_pct * 20)
            throttle_str = "█" * throttle_bars + "░" * (20 - throttle_bars)

            brake_bars = int(snap.brake_pct * 20)
            brake_str = "█" * brake_bars + "░" * (20 - brake_bars)

            # Pulsadores
            btn_states = []
            for i, pin in enumerate(PIN_NAMES):
                val = snap.raw_buttons[i] if i < len(snap.raw_buttons) else 0
                state_char = "X" if val == 1 else " "
                btn_states.append(f"{pin}:[{state_char}]")
            buttons_str = " ".join(btn_states)

            status_color = "\033[92m" if snap.status == "connected" else "\033[91m"
            reset_color = "\033[0m"

            dashboard = (
                "\033[H"  # Volver al inicio de pantalla sin parpadear
                "================================================================================\n"
                "           🏎️  VOLANTE-PC // TERMINAL TELEMETRY DASHBOARD (100 HZ)\n"
                "================================================================================\n"
                f" Estado: {status_color}[{snap.status.upper()}]{reset_color} en {snap.active_port or '--'} | Modo: {snap.mode} | Preset: {snap.preset}\n"
                f" Gamepad Virtual: [{'OK' if snap.gamepad_connected else 'ERROR'}] | Frecuencia: {snap.loop_hz:.0f} Hz\n"
                "--------------------------------------------------------------------------------\n"
                f" DIRECCIÓN:  [{steer_bar_str}] {snap.steer_angle:+6.1f}° (ADC: {snap.raw_steer:4d})\n"
                f" ACELERADOR: [{throttle_str}] {snap.throttle_pct * 100:5.1f}% (ADC: {snap.raw_accel:4d})\n"
                f" FRENO:      [{brake_str}] {snap.brake_pct * 100:5.1f}% (ADC: {snap.raw_brake:4d})\n"
                "--------------------------------------------------------------------------------\n"
                f" BOTONES: {buttons_str}\n"
                "--------------------------------------------------------------------------------\n"
                " Presiona Ctrl+C para salir.\n"
            )

            sys.stdout.write(dashboard)
            sys.stdout.flush()
            time.sleep(0.05)  # 20 Hz de refresco en terminal
    finally:
        sys.stdout.write("\033[?25h\033[2J\033[H")  # Restaurar cursor y limpiar pantalla
        sys.stdout.flush()
        engine.stop()
        print("[Volante-PC] Dashboard cerrado.")


def run_gui(port: str | None = None) -> None:
    """Ejecuta la aplicación gráfica principal PyQt6 Motorsport DDU."""
    from PyQt6.QtWidgets import QApplication
    from core.engine import Engine
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Volante-PC")
    app.setOrganizationName("VolantePC")

    engine = Engine(port=port)
    engine.start()

    window = MainWindow(engine=engine)
    window.show()

    exit_code = app.exec()
    engine.stop()
    sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Volante-PC Simracing Controller - Panel de Control y Emulador de Hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                  # Inicia la interfaz gráfica completa PyQt6
  python main.py --daemon         # Ejecuta solo el motor de baja latencia sin GUI (<15MB RAM)
  python main.py --cli            # Muestra el panel interactivo en terminal ASCII
  python main.py --port /dev/ttyACM0  # Conecta directamente al puerto indicado
        """,
    )
    parser.add_argument(
        "--daemon",
        "--headless",
        action="store_true",
        help="Ejecuta el emulador en segundo plano sin abrir la interfaz gráfica.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Ejecuta el dashboard ASCII de telemetría en vivo en la terminal.",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=str,
        default=None,
        help="Puerto serie específico del Arduino (ej. /dev/ttyUSB0, /dev/ttyACM0 o COM3).",
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(port=args.port)
    elif args.cli:
        run_cli_dashboard(port=args.port)
    else:
        run_gui(port=args.port)


if __name__ == "__main__":
    main()
