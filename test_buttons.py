#!/usr/bin/env python3
"""
Test de diagnóstico de hardware en vivo para Volante-PC.
Muestra en tiempo real los bytes recibidos de Arduino y el estado de cada pin.
"""
import sys
import time
import serial
import serial.tools.list_ports

PIN_NAMES = ['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'A3', 'A5', 'A4', 'D12']

PIN_INFO = [
    ("D2", "Volante"),
    ("D3", "Volante"),
    ("D4", "Volante"),
    ("D5", "Volante"),
    ("D6", "Volante"),
    ("D7", "Volante"),
    ("D8", "Volante"),
    ("A3 (o D9)", "Volante"),
    ("A5 (o D10)", "Volante"),
    ("A4 (o D11)", "Volante"),
    ("D12", "Pedalera"),
]

def find_port():
    for p in serial.tools.list_ports.comports():
        if any(x in p.device.lower() for x in ["ttyusb", "ttyacm", "com"]):
            return p.device
    return "/dev/ttyUSB0"

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    print(f"\033[96m=== TEST DE BOTONES Y EJES // VOLANTE-PC ===\033[0m")
    print(f"Abriendo puerto: \033[92m{port}\033[0m a 115200 baudios...\n")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"\033[91mError abriendo {port}: {e}\033[0m")
        sys.exit(1)

    ever_pressed = set()
    packet_count = 0
    start_time = time.time()
    
    try:
        buf = bytearray()
        while True:
            b = ser.read(32)
            if b:
                buf.extend(b)
            
            # Buscar 0xAA 0x55
            while len(buf) >= 8:
                idx = -1
                for i in range(len(buf) - 7):
                    if buf[i] == 0xAA and buf[i+1] == 0x55:
                        idx = i
                        break
                
                if idx == -1:
                    # Guardar último byte por si es 0xAA
                    if len(buf) > 0 and buf[-1] == 0xAA:
                        buf = buf[-1:]
                    else:
                        buf.clear()
                    break
                
                # Consumir hasta el paquete
                pkt = buf[idx:idx+8]
                buf = buf[idx+8:]
                packet_count += 1
                
                axes_val = int.from_bytes(pkt[2:6], 'little')
                buttons_val = int.from_bytes(pkt[6:8], 'little')
                
                steer_raw = axes_val & 0x3FF
                accel_raw = (axes_val >> 10) & 0x3FF
                brake_raw = (axes_val >> 20) & 0x3FF
                
                # Desglosar los 16 bits de botones
                bits = [(buttons_val >> i) & 1 for i in range(16)]
                for i in range(16):
                    if bits[i] == 1:
                        ever_pressed.add(i)
                # Formatear visualización
                btn_status_parts = []
                for i, (p_name, loc) in enumerate(PIN_INFO):
                    if bits[i] == 1:
                        btn_status_parts.append(f"\033[92;1m[{p_name}: ON ({loc})]\033[0m")
                    else:
                        btn_status_parts.append(f"\033[90m[{p_name}: ..]\033[0m")

                # Otros bits (11..15)
                extra_bits = []
                for i in range(11, 16):
                    if bits[i] == 1:
                        extra_bits.append(f"\033[93;1m[Bit{i}: 1]\033[0m")

                ever_str = ", ".join(PIN_INFO[i][0] if i < len(PIN_INFO) else f"Bit{i}" for i in sorted(ever_pressed))

                sys.stdout.write("\033[H\033[2J")
                sys.stdout.write(
                    "========================================================================\n"
                    "        TEST EN VIVO DE SENSORES Y BOTONES (Presiona Ctrl+C para salir)\n"
                    "========================================================================\n"
                    f" Paquetes recibidos: {packet_count} | Frecuencia: {packet_count / max(0.1, time.time() - start_time):.1f} Hz\n"
                    f" Bytes crudos paquete: {[hex(x) for x in pkt]}\n"
                    "------------------------------------------------------------------------\n"
                    f" DIRECCION (A0): {steer_raw:4d}  (0..1023)\n"
                    f" ACELERADOR (A1): {accel_raw:4d} (0..1023)\n"
                    f" FRENO      (A2): {brake_raw:4d} (0..1023)\n"
                    "------------------------------------------------------------------------\n"
                    f" VALOR BOTONES (RAW 16 bits): {buttons_val:5d}  (Hex: {hex(buttons_val)} | Bin: {bin(buttons_val)})\n\n"
                    " ESTADO ACTUAL DE PINES:\n " + "  ".join(btn_status_parts[:6]) + "\n " + "  ".join(btn_status_parts[6:]) + "\n"
                )
                if extra_bits:
                    sys.stdout.write(f" BITS EXTRA ACTIVOS: {' '.join(extra_bits)}\n")
                sys.stdout.write(
                    "------------------------------------------------------------------------\n"
                    f" PINES PULSADOS EN ESTA SESION: {ever_str if ever_str else '(Ninguno aun)'}\n"
                    "========================================================================\n"
                    " NOTA HARDWARE: Los pulsadores usan INPUT_PULLUP (cierran a masa/GND).\n"
                    " Si D12 (pedalera) funciona pero NINGUNO del volante responde, revisa el\n"
                    " cable de GND COMÚN que conecta los pulsadores del volante al Arduino.\n"
                    "========================================================================\n"
                )
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        print("\n\nTest finalizado.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
