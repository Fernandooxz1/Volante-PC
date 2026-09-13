"""
Volante-PC // Dashboard de Telemetría Motorsport para ESP32 (MicroPython).
Recibe paquetes UDP ultraligeros desde la PC por WiFi y muestra los datos
en hardware discreto (7 Segmentos Ánodo Común + Tira NeoPixel 8 LEDs) o pantalla ST7789.

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

discrete_ddu = None
st7789_ddu = None
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


def init_dashboard():
    """Inicializa el hardware según DASHBOARD_TYPE ('discrete' o 'st7789')."""
    global discrete_ddu, st7789_ddu
    dash_type = getattr(config, "DASHBOARD_TYPE", "discrete").lower()

    if dash_type == "discrete":
        try:
            from ddu_discrete import DiscreteDDU

            discrete_ddu = DiscreteDDU(config)
            print("[DDU] Dashboard Discreto activo: 7 Segmentos Ánodo Común + 8 NeoPixels.")
            return discrete_ddu
        except Exception as e:
            print(f"[DDU] Error iniciando hardware discreto: {e}")
            return None

    elif dash_type == "st7789":
        try:
            from ddu_display import DDUDisplay

            st7789_ddu = DDUDisplay(config)
            print("[ST7789] Pantalla IPS 240x240 inicializada correctamente.")
            return st7789_ddu
        except Exception as e:
            print(f"[ST7789] Advertencia: no se pudo iniciar pantalla ({e}).")
            return None

    return None


def main():
    global last_packet_time, discrete_ddu, st7789_ddu

    print("==================================================")
    print("      VOLANTE-PC // ESP32 MOTORSPORT DDU          ")
    print("==================================================")

    init_dashboard()
    ip = init_wifi()

    if st7789_ddu:
        st7789_ddu.show_waiting_screen(ip or "SIN WIFI")

    # Socket UDP
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

                if discrete_ddu:
                    discrete_ddu.update_telemetry(gear_str, speed, revs, drs)
                elif st7789_ddu:
                    st7789_ddu.update(gear_str, speed, rpm, revs, drs)
                else:
                    print(f"[DDU] M: {gear_str} | Vel: {speed:3d} km/h | RPM: {rpm:<5} | Revs: {revs:2d}% | DRS: {drs}")

        except OSError:
            pass

        # Si pasan más de 2.5 segundos sin telemetría, restaurar estado de reposo
        if not waiting_shown and (time.time() - last_packet_time) > 2.5:
            if discrete_ddu:
                discrete_ddu.update_telemetry("N", 0, 0, 0)
            elif st7789_ddu:
                st7789_ddu.show_waiting_screen(ip or "--")
            else:
                print("[DDU] Esperando telemetría de F1...")
            waiting_shown = True

        # Multiplexado de los 7 segmentos (refresco cada ~2ms por dígito)
        if discrete_ddu:
            discrete_ddu.refresh_step()
            time.sleep_ms(2)
        else:
            time.sleep_ms(10)


if __name__ == "__main__":
    main()
