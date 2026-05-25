# Volante para PC con Arduino Nano (USB-C) y Python

Este proyecto te permite construir tu propio volante de carreras y pedalera para PC utilizando un **Arduino Nano con USB-C**, potenciómetros de 10k y un script de Python que emula un control virtual de Xbox 360 en tu computadora.

---

## Requisitos de Hardware

1. **Arduino Nano** (Preferiblemente con puerto USB-C).
2. **3 Potenciómetros lineales de 10k Ohms**:
   - 1x para el **Volante** (Dirección).
   - 1x para el **Pedal de Acelerador**.
   - 1x para el **Pedal de Freno**.
3. **Cables de conexión** y protoboard (o soldador para montaje final).
4. **Cable USB-C** para conectar el Arduino a la PC.

### Esquema de Conexiones

Todos los potenciómetros comparten la misma línea de alimentación de **5V** y tierra (**GND**) provistos por el Arduino Nano. Los pines de señal (limpiador/pin central del potenciómetro) se conectan a los pines analógicos de la siguiente manera:

| Componente | Pin del Potenciómetro | Pin en Arduino Nano |
| :--- | :--- | :--- |
| **GND Común** | Pin Izquierdo | **GND** |
| **5V Común** | Pin Derecho | **5V** o **VCC** |
| **Señal Volante** | Pin Central (Wiper) | **A0** |
| **Señal Acelerador** | Pin Central (Wiper) | **A1** |
| **Señal Freno** | Pin Central (Wiper) | **A2** |

*Nota: Si la dirección del eje o pedal está invertida en el juego, simplemente intercambia el cable de 5V y GND en los extremos del potenciómetro correspondiente.*

---

## Instalación y Configuración de Software

### 1. Programar el Arduino
1. Abre el IDE de Arduino.
2. Abre el archivo [volante_nano.ino](arduino/volante_nano/volante_nano.ino).
3. Selecciona tu placa **Arduino Nano** y el puerto correspondiente en el menú *Herramientas*.
4. Sube (Upload) el programa al Arduino.
5. Dado que el Arduino ahora transmite en un formato binario altamente optimizado para baja latencia y mínimo consumo de memoria, verás caracteres especiales ("ruido" binario) si abres el *Monitor Serie*. Esto es normal y esperado; el script de Python se encargará de decodificar este flujo de bytes.

### 2. Configurar Python
El script requiere Python 3 y dos librerías principales: `pyserial` y `vgamepad`.

1. Entra a la carpeta del proyecto e instala los requerimientos:
   ```bash
   pip install -r python/requirements.txt
   ```

#### Configuración Especial para Linux (uinput)
Para que el script pueda crear un dispositivo de juego virtual en Linux sin necesidad de permisos de superusuario (`sudo`), debes configurar las reglas de `udev` para el subsistema `uinput`:

1. Agrega tu usuario al grupo `input`:
   ```bash
   sudo usermod -aG input $USER
   ```
2. Crea una regla de udev ejecutando el siguiente comando:
   ```bash
   echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules
   ```
3. Carga el módulo de kernel `uinput` si no está cargado:
   ```bash
   sudo modprobe uinput
   ```
4. **Reinicia tu sesión** (cierra sesión y vuelve a entrar) o reinicia la PC para que los cambios de grupo tengan efecto.

---

## Ejecución del Emulador

Una vez programado el Arduino y configurado el sistema, ejecuta el script de Python:

```bash
python python/emulador_volante.py
```

El script buscará automáticamente el puerto donde está conectado tu Arduino Nano (ej: `/dev/ttyUSB0` o `/dev/ttyACM0`). Si no lo encuentra o tienes múltiples dispositivos, puedes especificar el puerto manualmente:

```bash
python python/emulador_volante.py -p /dev/ttyUSB0
```

### Dashboard Interactivo de la Terminal
Al ejecutarse con éxito, verás una interfaz visual interactiva en la terminal en tiempo real:

```text
===================================================
          EMULADOR DE VOLANTE Y PEDALES PC         
===================================================
Buscando Arduino Nano automáticamente...
-> Encontrado posible Arduino en: /dev/ttyUSB0
Inicializando gamepad virtual de Xbox 360...
¡Gamepad virtual creado correctamente!
Conectándose a /dev/ttyUSB0 a 115200 baudios...
Conectado al Arduino con éxito. Esperando datos...

Volante: [---------O----------]  512 | Acel:   0% | Freno:   0%
```

Al mover el potenciómetro del volante o presionar los pedales, el indicador gráfico `O` se moverá lateralmente y los porcentajes de acelerador y freno se actualizarán dinámicamente con latencia ultra baja.

---

## Calibración y Verificación

### En Linux
Puedes verificar que el joystick virtual es reconocido por el sistema utilizando herramientas GUI como:
- **`jstest-gtk`**: Una herramienta gráfica excelente para calibrar y probar mandos. Instálala con tu gestor de paquetes (ej. `sudo apt install jstest-gtk` o `sudo pacman -S jstest-gtk`).
- También puedes probar desde la consola listando los inputs: `ls /dev/input/by-id/` (debería aparecer un dispositivo de tipo virtual Xbox).

### En Windows
El script de Python también funciona en Windows.
1. Necesitas tener instalado el driver de controladores virtuales [ViGEmBus](https://github.com/ViGEm/ViGEmBus/releases).
2. Ejecuta el script.
3. Abre el menú Ejecutar (`Win + R`), escribe `joy.cpl` y presiona Enter para abrir la configuración de dispositivos de juego de Windows y ver el control de Xbox 360 emulado.
