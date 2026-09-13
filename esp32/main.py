"""
Volante-PC // Dashboard de Telemetría Motorsport para ESP32 (MicroPython).
Recibe paquetes UDP ultraligeros desde la PC por WiFi y muestra los datos
en tiempo real en una pantalla IPS 1.3" ST7789 (240x240 SPI) o en consola.

Protocolo Volante-PC (9 bytes):
- Sync: 0xAA 0x55
- RPM: uint16
- Marcha: int8 (-1=R, 0=N, 1..8)
- Velocidad: uint16
- RevLights%: uint8 (0..100)
- DRS: uint8 (0=Off, 1=On)
"""

import socket
import struct
import time
import network

import config

display = None
last_packet_time = 0


def init_wifi():
    """Conecta la ESP32 a la red WiFi configurada."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan.ifconfig()[0]

    print(f"[WiFi] Conectando a '{config.WIFI_SSID}'...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > config.WIFI_TIMEOUT_SEC:
            print("[WiFi] ERROR: Tiempo de espera agotado. Verifica SSID y Password en config.py.")
            return None
        time.sleep_ms(300)

    ip = wlan.ifconfig()[0]
    print(f"[WiFi] Conectado exitosamente! IP asignada: {ip}")
    return ip


def init_display():
    """Inicializa la pantalla ST7789 IPS 240x240."""
    global display
    try:
        from ddu_display import DDUDisplay

        display = DDUDisplay(config)
        print("[ST7789] Pantalla IPS 240x240 inicializada correctamente.")
        return display
    except Exception as e:
        print(f"[ST7789] Advertencia: no se pudo iniciar pantalla ({e}). Modo consola activo.")
        display = None
        return None


def main():
    global last_packet_time, display

    print("==================================================")
    print("  VOLANTE-PC // ESP32 MOTORSPORT DDU (ST7789 IPS) ")
    print("==================================================")

    ddu = init_display()
    ip = init_wifi()

    if ddu:
        ddu.show_waiting_screen(ip or "SIN WIFI")

    # Crear socket UDP en el puerto configurado
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.setblocking(False)

    print(f"[UDP] Escuchando telemetría en el puerto {config.UDP_PORT}...")

    waiting_shown = True

    while True:
        try:
            data, _ = sock.recvfrom(32)
            if data:
                # 1. Paquete Volante-PC (9 bytes: 0xAA 0x55 <BBHbHBB)
                if len(data) >= 9 and data[0] == 0xAA and data[1] == 0x55:
                    _, _, rpm, gear, speed, revs, drs = struct.unpack_from("<BBHbHBB", data, 0)
                # 2. Fallback compatibilidad (5 bytes: <HbH)
                elif len(data) == 5:
                    rpm, gear, speed = struct.unpack_from("<HbH", data, 0)
                    revs = 0
                    drs = 0
                else:
                    continue

                # Formatear marcha
                if gear == -1:
                    gear_str = "R"
                elif gear == 0:
                    gear_str = "N"
                else:
                    gear_str = str(gear)

                last_packet_time = time.time()
                waiting_shown = False

                if ddu:
                    ddu.update(gear_str, speed, rpm, revs, drs)
                else:
                    # Salida por consola serial si no hay pantalla conectada
                    print(f"[DDU] M: {gear_str} | Vel: {speed:3d} km/h | RPM: {rpm:<5} | Revs: {revs:2d}% | DRS: {drs}")

        except OSError:
            pass

        # Si pasan más de 2.5 segundos sin telemetría, volver a pantalla de espera
        if not waiting_shown and (time.time() - last_packet_time) > 2.5:
            if ddu:
                ddu.show_waiting_screen(ip or "--")
            else:
                print("[DDU] Esperando telemetría de F1...")
            waiting_shown = True

        time.sleep_ms(10)  # ~100 Hz de sondeo UDP de baja latencia


if __name__ == "__main__":
    main()
