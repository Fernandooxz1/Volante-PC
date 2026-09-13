# Dashboard Hardware para ESP32: 7 Segmentos + Tira NeoPixel

Panel digital de telemetría para simulador de carreras con:
1. **1 Display de 7 Segmentos Ánodo Común (Marcha)**.
2. **1 Display de 7 Segmentos de 3 Dígitos Ánodo Común (Velocidad en KM/H)**.
3. **Tira NeoPixel WS2812B de 8 LEDs RGB (Shift Lights / RPM progresivas)**.

---

## ⚡ El Truco del Multiplexado (Solo 12 pines de la ESP32)

Para no desperdiciar pines, los segmentos **A, B, C, D, E, F y G** están **conectados en paralelo** entre los dos displays:

```text
[ Pin GPIO Segmento A ] ────► [ Resistencia 330Ω ] ──┬──► Segmento A Display Marcha (1 dígito)
                                                     └──► Segmento A Display Velocidad (3 dígitos)
(Igual para los segmentos B, C, D, E, F y G)
```

Solo activamos un dígito a la vez a alta frecuencia (125 Hz) encendiendo su pin de Ánodo Común (HIGH).

---

## 🔌 Diagrama de Pines en la ESP32

### 1. Segmentos (Compartidos entre ambos displays)
Colocar **una resistencia de 330Ω o 470Ω** en serie con cada pin de segmento:

| Segmento | Pin ESP32 | Resistencia |
| :---: | :---: | :---: |
| **A** | **GPIO 16** | 330Ω |
| **B** | **GPIO 17** | 330Ω |
| **C** | **GPIO 18** | 330Ω |
| **D** | **GPIO 19** | 330Ω |
| **E** | **GPIO 21** | 330Ω |
| **F** | **GPIO 22** | 330Ω |
| **G** | **GPIO 23** | 330Ω |

---

### 2. Ánodos Comunes (Habilitación de cada dígito)
En Ánodo Común (CA), poner el pin en **HIGH (3.3V)** activa ese dígito:

| Dígito | Pin ESP32 | Función |
| :--- | :---: | :--- |
| **Ánodo Display 1 Dígito** | **GPIO 25** | Marcha (`N`, `R`, `1`..`8`) |
| **Ánodo Dígito 1 (Velocidad)** | **GPIO 26** | Centenas km/h |
| **Ánodo Dígito 2 (Velocidad)** | **GPIO 27** | Decenas km/h |
| **Ánodo Dígito 3 (Velocidad)** | **GPIO 14** | Unidades km/h |

---

### 3. Tira NeoPixel WS2812B (8 LEDs)
| Pin NeoPixel | Pin ESP32 | Notas |
| :--- | :---: | :--- |
| **DIN** (Datos) | **GPIO 13** | Señal de control |
| **VCC** / **+5V** | **VIN** (5V) | Alimentación de los LEDs |
| **GND** | **GND** | Tierra común |

---

## 🚦 Escala de Colores de los 8 LEDs NeoPixel

* **LED 1 y 2:** 🟢 **Verde** (50% a 70% RPM)
* **LED 3 y 4:** 🟡 **Amarillo** (70% a 85% RPM)
* **LED 5 y 6:** 🔴 **Rojo** (85% a 93% RPM)
* **LED 7 y 8:** 🔵 **Azul** (93% a 95% RPM - ¡Punto de cambio!)
* **Corte (> 95% RPM):** ¡Toda la tira parpadea en **Azul/Blanco** (Shift Light Flash estilo F1)!
