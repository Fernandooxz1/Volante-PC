# Volante para PC con Arduino UNO y Python (Multiplataforma)

Este proyecto te permite construir tu propio volante de carreras y pedalera para PC utilizando un **Arduino UNO**, potenciómetros de 10k y un script de Python que emula un control virtual de Xbox 360 en tu computadora.

Esta versión cuenta con una **curva de dirección exponencial (Steering Expo)** similar a la de simuladores comerciales (Logitech G, Fanatec, PlayStation) para lograr la máxima precisión en rectas, además de un sistema auto-contenido para instalar los controladores necesarios en Windows de manera desatendida.

---

## Requisitos de Hardware

1. **Arduino UNO**.
2. **3 Potenciómetros lineales de 10k Ohms**:
   - 1x para el **Volante** (Dirección).
   - 1x para el **Pedal de Acelerador**.
   - 1x para el **Pedal de Freno**.
3. **Cables de conexión** y protoboard (o soldador para montaje final).
4. **Cable USB** para conectar el Arduino a la PC.

### Esquema de Conexiones

Todos los potenciómetros comparten la misma línea de alimentación de **5V** y tierra (**GND**) provistos por el Arduino UNO. Los pines de señal (limpiador/pin central del potenciómetro) se conectan a los pines analógicos de la siguiente manera:

| Componente | Pin del Potenciómetro | Pin en Arduino UNO |
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
2. Abre el archivo [volante_uno.ino](arduino/volante_uno/volante_uno.ino).
3. Selecciona tu placa **Arduino Uno** y el puerto correspondiente en el menú *Herramientas*.
4. Sube (Upload) el programa al Arduino.

### 2. Configurar Python
El script requiere Python 3 y dos librerías principales: `pyserial` y `vgamepad`.

1. Entra a la carpeta del proyecto e instala los requerimientos:
   ```bash
   pip install -r python/requirements.txt
   ```

#### Configuración en Linux (uinput)
Para que el script pueda crear un dispositivo de juego virtual en Linux sin necesidad de permisos de superusuario (`sudo`), debes configurar las reglas de `udev`:

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
4. **Reinicia tu sesión** (cierra sesión y vuelve a entrar) o reinicia la PC para que los cambios tengan efecto.

#### Configuración en Windows (ViGEmBus)
El programa requiere el controlador de mandos virtuales **ViGEmBus** en Windows. 
* **Instalación Desatendida Integrada**: Si ejecutas el programa en Windows sin tener el controlador instalado, la interfaz web y la app nativa te mostrarán un banner rojo informándote del problema. Simplemente haz clic en **"Instalar ViGEmBus"** en la pantalla y la aplicación extraerá y ejecutará de forma automática el instalador oficial integrado en sus recursos (`web/drivers/ViGEmBus_Setup.exe`).

---

## Ejecución del Emulador

El proyecto cuenta con dos interfaces: un **Dashboard Web Profesional** con calibración interactiva de curvas (Recomendado) y el visor clásico por consola.

### Opción A: Dashboard Web Profesional (Recomendado)

Inicia el servidor local y la interfaz web ejecutando:

```bash
python python/gui_web.py
```

El script abrirá automáticamente tu navegador web con un panel de control interactivo de alta fidelidad. Desde allí podrás:
- Auto-detectar y seleccionar el puerto serie del Arduino en tiempo real.
- Cargar presets pre-configurados para F1 23/24, Gran Turismo, NFS, o personalizar el tuyo.
- Configurar visualmente la **sensibilidad, linealidad (curva exponencial), zona muerta de pedales y el filtro de ruido (Jitter)**.
- Monitorear en vivo la curva de respuesta y ver el cursor dinámico conforme giras el volante físico.

### Opción B: Dashboard de la Terminal (Consola)

Si deseas correr el script directamente en la consola sin interfaz gráfica:

```bash
python python/emulador_volante.py
```

---

## Calibración y Curva Exponencial

Para evitar que el auto zigzaguee o "baile" constantemente a la izquierda o derecha en rectas, esta versión implementa una **progresión exponencial de dirección**:

$$x_{\text{expo}} = \text{sign}(x) \cdot |x|^{\text{slope}}$$
$$x_{\text{sloped}} = x_{\text{expo}} \cdot \text{sensitivity}$$

### Cómo ajustarlo desde el Dashboard:
1. **Pendiente de Eje (Linealidad / Slope)**:
   * Valores de **`1.5` a `2.0`** (exponencial) suavizan el centro del volante. Un giro físico del 10% se traducirá en solo un 1% de dirección virtual, dando una precisión milimétrica para mantener el auto recto. A medida que gires más al extremo, la sensibilidad aumenta de forma progresiva.
   * Un valor de **`1.0`** dará una respuesta completamente lineal.
2. **Filtro de Ruido (Anti-Jitter)**:
   * Si tienes un potenciómetro de posiciones que va haciendo "clicks" o escalones (de $0$ a $1022$), sube este slider a un valor entre **`60%` y `75%`**. El filtro EMA suavizará la transición entre los clicks para que la dirección no sea brusca.
3. **Compensación de Zona Muerta (Anti-Deadzone)**:
   * Mantenlo en **`0%`** a menos que el juego requiera superar una zona muerta interna muy grande. Dejarlo activo sin necesidad genera saltos bruscos en el centro de la dirección.

### Verificación del Mando Virtual
* **En Linux**: Puedes probar el joystick virtual utilizando la herramienta gráfica `jstest-gtk` (instálala con `sudo apt install jstest-gtk` o `sudo pacman -S jstest-gtk`).
* **En Windows**: Abre el panel de mandos presionando `Win + R`, escribe `joy.cpl` y dale a Enter. Verás el mando de Xbox 360 emulado en la lista para comprobar los ejes.

---

## Compilación del Ejecutable (`.exe` o Binario)

El proyecto cuenta con un archivo unificado de configuración de compilación multiplataforma: **`VolantePC.spec`**. 

El uso del archivo `.spec` garantiza que las librerías dinámicas y DLLs necesarias (como `ViGEmClient.dll` para Windows) se empaqueten automáticamente de forma correcta.

Para compilarlo en tu sistema (Linux o Windows):

1. Instala PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Compila utilizando el archivo de especificaciones:
   ```bash
   # Posiciónate en la carpeta python/ y compila
   cd python
   pyinstaller --clean --noconfirm VolantePC.spec
   ```
3. El binario autocontenido se generará en la carpeta `python/dist/` junto con:
   * `config_volante.json` (archivo de configuración guardada).
   * La subcarpeta `drivers/` que contiene el instalador de controladores para Windows.
