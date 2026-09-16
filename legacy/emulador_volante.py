#!/usr/bin/env python3
import sys
import time
import argparse
import serial
import serial.tools.list_ports
import vgamepad as vg

BUTTON_MAP = {
    "Button Start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "Button Back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "Button A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "Button B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "Button X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Button Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "Button LB (Left Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "Button RB (Right Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "Button L3 (Left Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "Button R3 (Right Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "D-Pad UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "D-Pad DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "D-Pad LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "D-Pad RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    "Ninguno": None,
}

# Mapeo por defecto de los 11 pines de botones digitales (bits 0 a 10 en protocolo binario)
# Corresponde a los pines: D2, D3, D4, D5, D6, D7, D8, A3, A5, A4, D12
DEFAULT_BUTTON_MAPPING = [
    vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,            # Bit 0 (D2): Back
    vg.XUSB_BUTTON.XUSB_GAMEPAD_START,           # Bit 1 (D3): Start
    vg.XUSB_BUTTON.XUSB_GAMEPAD_B,               # Bit 2 (D4): B
    vg.XUSB_BUTTON.XUSB_GAMEPAD_X,               # Bit 3 (D5): X
    vg.XUSB_BUTTON.XUSB_GAMEPAD_A,               # Bit 4 (D6): A
    vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,               # Bit 5 (D7): Y
    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,  # Bit 6 (D8): RB
    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,   # Bit 7 (A3): LB
    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,      # Bit 8 (A5): L3
    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,     # Bit 9 (A4): R3
    None,                                        # Bit 10 (D12): Sin asignar / Reservado
]


def find_arduino_port():
    """Busca puertos serie disponibles que puedan ser el Arduino UNO."""
    ports = serial.tools.list_ports.comports()
    arduino_ports = []
    
    for port in ports:
        # Buscar en descripción o hardware ID nombres típicos
        desc = port.description.lower()
        hwid = port.hwid.lower()
        if "arduino" in desc or "ch340" in desc or "usb" in desc or "ttyacm" in port.device.lower() or "ttyusb" in port.device.lower():
            arduino_ports.append(port.device)
            
    if arduino_ports:
        return arduino_ports[0]
    return None

def draw_dashboard(steer, accel, brake):
    """Dibuja una barra de estado visual en la consola."""
    # Barra de dirección: volante
    width = 20
    center = width // 2
    pos = int((steer / 1023.0) * width)
    pos = max(0, min(width - 1, pos))
    
    bar_list = ["-"] * width
    bar_list[center] = "|"
    bar_list[pos] = "O"
    steer_bar = "".join(bar_list)
    
    # Porcentajes de pedales
    pct_accel = int((accel / 1023.0) * 100)
    pct_brake = int((brake / 1023.0) * 100)
    
    # Colores ANSI para terminal
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    
    sys.stdout.write(
        f"\rVolante: [{BLUE}{steer_bar}{RESET}] {steer:4d} | "
        f"Acel: {GREEN}{pct_accel:3d}%{RESET} | "
        f"Freno: {RED}{pct_brake:3d}%{RESET}   "
    )
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Emulador de Volante PC usando Arduino UNO y vgamepad.")
    parser.add_argument("-p", "--port", type=str, help="Puerto serie específico (ej: /dev/ttyUSB0, COM3). Auto-detecta por defecto.")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Velocidad en baudios (default: 115200).")
    args = parser.parse_args()

    print("\033[95m===================================================\033[0m")
    print("\033[95m          EMULADOR DE VOLANTE Y PEDALES PC         \033[0m")
    print("\033[95m===================================================\033[0m")

    # Selección de puerto serie
    port = args.port
    if not port:
        print("Buscando Arduino UNO automáticamente...")
        port = find_arduino_port()
        if port:
            print(f"-> Encontrado posible Arduino en: \033[92m{port}\033[0m")
        else:
            print("\033[91mNo se auto-detectó ningún dispositivo compatible.\033[0m")
            # Mostrar todos los puertos disponibles
            all_ports = [p.device for p in serial.tools.list_ports.comports()]
            if all_ports:
                print(f"Puertos disponibles en el sistema: {', '.join(all_ports)}")
            print("Por favor, especifica el puerto usando: python emulador_volante.py -p <puerto>")
            sys.exit(1)

    # Inicializar dispositivo virtual vgamepad
    print("Inicializando gamepad virtual de Xbox 360...")
    try:
        gamepad = vg.VX360Gamepad()
        print("\033[92m¡Gamepad virtual creado correctamente!\033[0m")
    except Exception as e:
        print(f"\033[91mError al crear el gamepad virtual: {e}\033[0m")
        print("\nSi estás en Linux, asegúrate de que tienes permisos de escritura en /dev/uinput:")
        print("  1. Ejecuta: sudo usermod -aG input $USER")
        print("  2. Configura reglas de udev (ver README.md para más detalles).")
        print("  3. O ejecuta el script como superusuario (no recomendado): sudo python emulador_volante.py")
        sys.exit(1)

    # Conectar al puerto serie
    print(f"Conectándose a {port} a {args.baud} baudios...")
    try:
        ser = serial.Serial(port, args.baud, timeout=1.0)
        # Limpiar buffers
        ser.reset_input_buffer()
        print("\033[92mConectado al Arduino con éxito. Esperando datos...\033[0m\n")
    except Exception as e:
        print(f"\033[91mError de conexión serie: {e}\033[0m")
        sys.exit(1)

    # Bucle principal de lectura binaria y de baja latencia
    pressed_buttons = set()
    try:
        while True:
            try:
                # Buscar encabezado de sincronización de 2 bytes (0xAA, 0x55)
                # ser.read(1) es bloqueante hasta recibir un byte (o timeout), lo que ahorra CPU
                b1 = ser.read(1)
                if b1 == b'\xaa':
                    b2 = ser.read(1)
                    if b2 == b'\x55':
                        # Leer los 6 bytes del paquete de datos empaquetados (4 de ejes + 2 de botones)
                        data_bytes = ser.read(6)
                        if len(data_bytes) == 6:
                            # Desempaquetar el entero de 32 bits (little-endian) y los botones
                            val = int.from_bytes(data_bytes[0:4], byteorder='little')
                            buttons_val = int.from_bytes(data_bytes[4:6], byteorder='little')
                            
                            # Extraer campos de 10 bits
                            steer = val & 0x3FF
                            accel = (val >> 10) & 0x3FF
                            brake = (val >> 20) & 0x3FF

                            # Limitar rangos analógicos por seguridad
                            steer = max(0, min(1023, steer))
                            accel = max(0, min(1023, accel))
                            brake = max(0, min(1023, brake))

                            # --- MAPEO DE EJES A MANDO XBOX 360 ---

                            # 1. Dirección: 0-1023 a Eje X del Stick Izquierdo (-32768 a 32767)
                            val_eje_x = int((steer / 1023.0) * 65535) - 32768
                            val_eje_x = max(-32768, min(32767, val_eje_x))
                            gamepad.left_joystick(x_value=val_eje_x, y_value=0)

                            # 2. Acelerador: 0-1023 a Gatillo Derecho RT (0 a 255)
                            val_accel = int((accel / 1023.0) * 255)
                            val_accel = max(0, min(255, val_accel))
                            gamepad.right_trigger(value=val_accel)

                            # 3. Freno: 0-1023 a Gatillo Izquierdo LT (0 a 255)
                            val_brake = int((brake / 1023.0) * 255)
                            val_brake = max(0, min(255, val_brake))
                            gamepad.left_trigger(value=val_brake)

                            # 4. Botones digitales: determinar botones activos y reconciliar
                            active_buttons = set()
                            for bit_idx, btn in enumerate(DEFAULT_BUTTON_MAPPING):
                                if btn is not None and ((buttons_val >> bit_idx) & 0x01):
                                    active_buttons.add(btn)

                            # Reconciliación: soltar botones liberados y presionar nuevos
                            to_release = pressed_buttons - active_buttons
                            for btn in to_release:
                                gamepad.release_button(button=btn)

                            to_press = active_buttons - pressed_buttons
                            for btn in to_press:
                                gamepad.press_button(button=btn)

                            pressed_buttons = active_buttons

                            # Aplicar cambios al control virtual
                            gamepad.update()

                            # Mostrar estado gráfico en la terminal
                            draw_dashboard(steer, accel, brake)

            except Exception as e:
                print(f"\n\033[91mError procesando datos: {e}\033[0m")
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n\033[93mDeteniendo emulación por petición del usuario...\033[0m")
    finally:
        # Liberar botones presionados y restablecer gamepad virtual
        if 'gamepad' in locals() and gamepad is not None:
            try:
                for btn in pressed_buttons:
                    gamepad.release_button(button=btn)
                gamepad.reset()
                gamepad.update()
            except Exception:
                pass
        # Cerrar puerto y limpiar
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Puerto serie cerrado.")
        print("Finalizado.")

if __name__ == "__main__":
    main()
