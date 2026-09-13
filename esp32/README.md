# Dashboard Hardware para ESP32: 7 Segmentos + Tira de 10 NeoPixels

Panel digital de telemetría para simulador de carreras con:
1. **1 Display de 7 Segmentos Ánodo Común (Marcha)**.
2. **1 Display de 7 Segmentos de 3 Dígitos Ánodo Común (Velocidad en KM/H)**.
3. **10 LEDs NeoPixel WS2812B 5050 SMD independientes en cascada (Shift Lights / RPM)**.

---

## 💡 ¿Cómo se conectan los 10 NeoPixels separados?

Los LEDs WS2812B funcionan en **cascada (daisy chain)**. Aunque sean plaquitas o LEDs separados, solo se usa **1 solo pin de la ESP32 (GPIO 13)**:

```text
[ Pin GPIO 13 ] ────────► [ DIN ]  LED 1  [ DOUT ] ────┐
                                                       ▼
                                                   [ DIN ]  LED 2  [ DOUT ] ────┐
                                                                                ▼
                                                                            [ DIN ]  LED 3 ... hasta LED 10
```

- **VCC (+5V):** Todos los pines `+5V` / `VCC` de los 10 LEDs van unidos en paralelo al pin **VIN (5V)** de la ESP32.
- **GND:** Todos los pines `GND` de los 10 LEDs van unidos en paralelo al pin **GND** de la ESP32.
- **DATOS (En serie de uno a otro):**
  - **ESP32 GPIO 13** ➔ al pin **`DIN`** del 1° LED.
  - El **`DOUT`** del 1° LED ➔ al **`DIN`** del 2° LED.
  - El **`DOUT`** del 2° LED ➔ al **`DIN`** del 3° LED...
  - ... así sucesivamente hasta el 10° LED (el `DOUT` del 10° queda libre).

---

## 🚦 Escala de Colores para los 10 LEDs de RPM

* **LEDs 1, 2 y 3 (Verdes):** 🟢 50% a 70% RPM (bajas/medias vueltas).
* **LEDs 4, 5 y 6 (Amarillos):** 🟡 70% a 85% RPM (subiendo revoluciones).
* **LEDs 7 y 8 (Rojos):** 🔴 85% a 93% RPM (zona alta).
* **LEDs 9 y 10 (Azules):** 🔵 93% a 95% RPM (¡Punto óptimo de cambio!).
* **Corte (> 95% RPM):** ¡Los 10 LEDs destellan al unísono en **Azul/Blanco** (Shift Light Flash estilo F1 real)!

---

## ⚡ Conexión de los Displays de 7 Segmentos (Ánodo Común)

Los segmentos **A, B, C, D, E, F y G** están **conectados en paralelo** entre los dos displays:

```text
Pin ESP32 Segmento A ──► [Resistencia 330Ω] ──┬──► Pin A del Display de 1 Dígito (Marcha)
                                              └──► Pin A del Display de 3 Dígitos (Velocidad)
(Lo mismo se repite para B, C, D, E, F y G)
```

### Tabla de Pines en la ESP32

#### 1. Segmentos (Compartidos con resistencia de 330Ω o 470Ω cada uno)
| Segmento | Pin ESP32 | Resistencia |
| :---: | :---: | :---: |
| **A** | **GPIO 16** | 330Ω |
| **B** | **GPIO 17** | 330Ω |
| **C** | **GPIO 18** | 330Ω |
| **D** | **GPIO 19** | 330Ω |
| **E** | **GPIO 21** | 330Ω |
| **F** | **GPIO 22** | 330Ω |
| **G** | **GPIO 23** | 330Ω |

#### 2. Ánodos Comunes (Habilitación de cada dígito - Ánodo Común)
| Función | Pin ESP32 | Notas |
| :--- | :---: | :--- |
| **Ánodo Display 1 Dígito (Marcha)** | **GPIO 25** | Muestra `N`, `R`, `1`..`8` |
| **Ánodo Dígito 1 (Velocidad)** | **GPIO 26** | Centenas km/h |
| **Ánodo Dígito 2 (Velocidad)** | **GPIO 27** | Decenas km/h |
| **Ánodo Dígito 3 (Velocidad)** | **GPIO 14** | Unidades km/h |
