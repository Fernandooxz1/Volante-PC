# Guía Definitiva de Montaje y Cableado: Dashboard ESP32
### Simulador F1 / Volante-PC (Hardware Discreto)

Esta guía detalla paso a paso cómo armar el panel digital de telemetría partiendo desde cero, con todos los componentes sobre la mesa y sin un solo cable conectado.

---

## 📋 1. Lista de Materiales

| Componente | Cantidad | Especificaciones / Notas |
| :--- | :---: | :--- |
| **Placa ESP32** | 1 | NodeMCU ESP32 (30 o 38 pines, con MicroPython instalado) |
| **Display 7 Segmentos 1 Dígito** | 1 | **Ánodo Común**, Verde, 0.56" (Indica Marcha: `N`, `r`, `1`..`8`) |
| **Display 7 Segmentos 3 Dígitos** | 1 | **Ánodo Común**, Verde, 0.56" (Indica Velocidad en KM/H) |
| **LEDs WS2812B 5050 SMD** | 8 | Plaquitas individuales (Tacómetro Shift Light) |
| **Resistencias** | 7 | **330 Ω** (Naranja-Naranja-Marrón) o 470 Ω (Amarillo-Violeta-Marrón) |
| **Protoboard(s)** | 1 o 2 | O placa perforada si se va a soldar |
| **Cables Jumper Dupont** | ~25 | Macho-Macho y Macho-Hembra |
| **Cable USB** | 1 | Micro-USB o USB-C (según tu ESP32) para datos y alimentación |

---

## 🔍 2. Paso 0: Entendiendo y Probando los Displays

### ¿Qué significa "Ánodo Común"?
* Cada segmento del display es un LED interno.
* En **Ánodo Común**, el polo positivo (**+**) de todos los LEDs de ese dígito está unido internamente a un único pin: el **Ánodo**.
* **Para encender un segmento:** El pin de Ánodo debe recibir **3.3V (HIGH)** y el pin del segmento debe ir a **0V / GND (LOW)** a través de una resistencia.
* **Para apagar un dígito completo:** Se pone su pin de Ánodo en **0V / LOW**.

```text
               Ánodo del Dígito (+3.3V)
                         ▲
                         │
        ┌────────┬───────┴────────┬────────┐
        ▼ (LED)  ▼ (LED)          ▼ (LED)  ▼ (LED)
       Seg A    Seg B            Seg F    Seg G
        │        │                │        │
      [330Ω]   [330Ω]           [330Ω]   [330Ω]
        ▼        ▼                ▼        ▼
     GPIO 16  GPIO 17          GPIO 22  GPIO 23
    (0V = ON) (0V = ON)       (0V = ON) (0V = ON)
```

### Distribución física de los 7 Segmentos:
```text
          -- A --
         |       |
         F       B
         |       |
          -- G --
         |       |
         E       C
         |       |
          -- D --   (DP: punto decimal)
```

### Cómo se ven la Marcha Neutral ('N') y Marcha Atrás ('R'):
En un display de 7 segmentos numérico se utilizan letras minúsculas:
* **Neutro (`n`):** Se encienden los segmentos **C**, **E** y **G**.
* **Reversa (`r`):** Se encienden los segmentos **E** y **G**.
* **Marchas `1` a `8`:** Dígitos normales estándar.

---

### Prueba Rápida con Multímetro o Pila (Antes de cablear)
Para asegurarte de qué pin es cuál en tus displays:
1. Pon tu multímetro en modo **Prueba de Diodos** (o usa una pila botón CR2032 de 3V con una resistencia de 1k).
2. Coloca la punta **ROJA (+)** en el pin Ánodo del display.
3. Toca con la punta **NEGRA (-)** cada uno de los otros pines: verás encenderse individualmente cada segmento en verde.
4. Anota cuál pin enciende A, B, C, D, E, F y G.

#### Pinout estándar Display 1 Dígito (10 pines):
```text
               VISTA FRONTAL
               ┌──────────┐
          (10) │   --A--  │ (6)
           (9) │ F|     |B│ (7)
      ÁNODO(8) │   --G--  │ (8) ÁNODO
           (7) │ E|     |C│ (9)
           (6) │   --D--  │ (10)
               └────[DP]──┘
                1  2  3  4  5
```
* **Pines 3 y 8:** Ánodos Comunes (están unidos internamente; basta conectar uno solo).
* **Pin 7:** Segmento A
* **Pin 6:** Segmento B
* **Pin 4:** Segmento C
* **Pin 2:** Segmento D
* **Pin 1:** Segmento E
* **Pin 9:** Segmento F
* **Pin 10:** Segmento G
* **Pin 5:** Punto Decimal (DP, no lo usamos)

#### Pinout típico Display 3 Dígitos (11 o 12 pines):
* Tiene **3 pines de Ánodo** (uno para cada dígito: `DIG1` = centenas, `DIG2` = decenas, `DIG3` = unidades).
* Los pines de segmentos **A, B, C, D, E, F, G** ya vienen puenteados internamente entre los 3 dígitos dentro del módulo.

---

## 🚦 3. Paso 1: Armado de la Tira de 8 NeoPixels (Shift Lights)

Usaremos exactamente **8 LEDs individuales** en hilera horizontal:
* **LEDs 1 y 2 (Verdes):** 50% a 70% RPM.
* **LEDs 3 y 4 (Amarillos):** 70% a 85% RPM.
* **LEDs 5 y 6 (Rojos):** 85% a 93% RPM.
* **LEDs 7 y 8 (Azules):** 93% a 95% RPM.
* **Corte (> 95% RPM):** ¡Destello Shift Flash (Azul/Blanco)!

### Conexión Eléctrica:
Los LEDs WS2812B se conectan con **alimentación en paralelo** y **datos en cascada (daisy chain)**:

```text
               ┌──► VCC de los 8 LEDs unidos en paralelo al pin VIN (5V) del ESP32
               └──► GND de los 8 LEDs unidos en paralelo al pin GND del ESP32

[ ESP32: GPIO 13 ] ────► [ DIN ] LED 1 [ DOUT ] ────┐
                                                    ▼
                                                [ DIN ] LED 2 [ DOUT ] ────┐
                                                                           ▼
                                                                       [ DIN ] LED 3 ... hasta LED 8
```

1. **Alimentación (+5V / VCC):**
   * Une el pad `+5V` o `VCC` de los 8 LEDs entre sí y conéctalos al pin **VIN (5V)** del ESP32.
   * *(Importante: Usar VIN / 5V, NO usar 3V3 para los LEDs para evitar sobrecalentar el regulador).*
2. **Masa (GND):**
   * Une el pad `GND` de los 8 LEDs entre sí y conéctalos al pin **GND** del ESP32.
3. **Línea de Datos (En cascada):**
   * Pin **GPIO 13** del ESP32 ➔ al pin **DIN** (Data In) del **LED 1**.
   * Pin **DOUT** (Data Out) del **LED 1** ➔ al pin **DIN** del **LED 2**.
   * Pin **DOUT** del **LED 2** ➔ al pin **DIN** del **LED 3**.
   * Pin **DOUT** del **LED 3** ➔ al pin **DIN** del **LED 4**.
   * Pin **DOUT** del **LED 4** ➔ al pin **DIN** del **LED 5**.
   * Pin **DOUT** del **LED 5** ➔ al pin **DIN** del **LED 6**.
   * Pin **DOUT** del **LED 6** ➔ al pin **DIN** del **LED 7**.
   * Pin **DOUT** del **LED 7** ➔ al pin **DIN** del **LED 8**.
   * El pin **DOUT del LED 8 queda libre**.

---

## ⚡ 4. Paso 2: Bus Compartido de Segmentos (Pines A..G + 7 Resistencias)

Para no gastar 28 pines de la ESP32, los segmentos **A, B, C, D, E, F y G** se unen entre ambos displays:

```text
ESP32 GPIO ──► [ Resistencia 330Ω ] ──┬──► Pin de Segmento en Display 1 Dígito (Marcha)
                                      └──► Pin de Segmento en Display 3 Dígitos (Velocidad)
```

Coloca las **7 resistencias de 330 Ω** en tu protoboard y realiza las siguientes conexiones:

| Segmento | Pin ESP32 | Resistencia | Conectar a: |
| :---: | :---: | :---: | :--- |
| **A** | **GPIO 16** | 330 Ω | Pin **A** (Display 1 díg.) **Y** Pin **A** (Display 3 díg.) |
| **B** | **GPIO 17** | 330 Ω | Pin **B** (Display 1 díg.) **Y** Pin **B** (Display 3 díg.) |
| **C** | **GPIO 18** | 330 Ω | Pin **C** (Display 1 díg.) **Y** Pin **C** (Display 3 díg.) |
| **D** | **GPIO 19** | 330 Ω | Pin **D** (Display 1 díg.) **Y** Pin **D** (Display 3 díg.) |
| **E** | **GPIO 21** | 330 Ω | Pin **E** (Display 1 díg.) **Y** Pin **E** (Display 3 díg.) |
| **F** | **GPIO 22** | 330 Ω | Pin **F** (Display 1 díg.) **Y** Pin **F** (Display 3 díg.) |
| **G** | **GPIO 23** | 330 Ω | Pin **G** (Display 1 díg.) **Y** Pin **G** (Display 3 díg.) |

> [!TIP]
> En la protoboard, clava la resistencia entre el cable que viene del ESP32 y una pista libre. De esa misma pista sacas dos cables jumpers: uno al Display 1 y otro al Display 3.

---

## 💡 5. Paso 3: Control de Ánodos (Selección de Dígito)

Los ánodos comunes determinan **qué display y qué dígito se enciende en cada instante de milisegundos**.
Estos pines van **directos** desde el ESP32 (NO llevan resistencia, pues la resistencia ya está en los segmentos):

| Función | Pin ESP32 | Conexión Física |
| :--- | :---: | :--- |
| **Marcha (Gear)** | **GPIO 25** | Pin **Ánodo** del Display de 1 Dígito |
| **Velocidad: Centenas** | **GPIO 26** | Pin **Ánodo Dígito 1** del Display de 3 Dígitos |
| **Velocidad: Decenas** | **GPIO 27** | Pin **Ánodo Dígito 2** del Display de 3 Dígitos |
| **Velocidad: Unidades** | **GPIO 14** | Pin **Ánodo Dígito 3** del Display de 3 Dígitos |

---

## 🗺️ 6. Resumen General del Pinout en la ESP32

```text
                          ESP32 NodeMCU
                           ┌─────────┐
                           │   USB   │
                           ├─────────┤
                           │         │
                           │         │
           (Shift Light)   │ 13   14 │ (Ánodo Velocidad Unidades)
                           │ GND  27 │ (Ánodo Velocidad Decenas)
     (Segmento A - 330Ω)   │ 16   26 │ (Ánodo Velocidad Centenas)
     (Segmento B - 330Ω)   │ 17   25 │ (Ánodo Marcha)
                           │         │
     (Segmento C - 330Ω)   │ 18   23 │ (Segmento G - 330Ω)
     (Segmento D - 330Ω)   │ 19   22 │ (Segmento F - 330Ω)
     (Segmento E - 330Ω)   │ 21  TXD │
                           │ 3V3 RXD │
               (5V LEDs)   │ VIN GND │ (Masa común LEDs)
                           └─────────┘
```

Total de pines utilizados: **12 pines GPIO + VIN + GND**.

---

## ✅ 7. Paso 4: Checklist de Seguridad Antes de Enchufar

Antes de conectar el cable USB a la computadora:
- [ ] **Sin corto en alimentación:** Con el multímetro en continuidad (pitido), mide entre **VIN** y **GND**. NO debe pitar.
- [ ] **Voltaje de LEDs:** Comprueba que el cable positivo de los NeoPixels va a **VIN** (5V) y **NO a 3V3**.
- [ ] **Dirección de datos NeoPixel:** Confirma que el pin de la ESP32 (GPIO 13) entra a **DIN** del primer LED, y que los siguientes van de **DOUT ➔ DIN**.
- [ ] **Resistencias en su lugar:** Confirma que los 7 pines de segmentos (16, 17, 18, 19, 21, 22, 23) tienen sus resistencias puestas y no van directos.

---

## 🚀 8. Paso 5: Puesta en Marcha y Pruebas

1. **Conecta la ESP32 a la PC** con el cable USB.
2. La ESP32 iniciará MicroPython y cargará automáticamente `main.py`.
3. **¿Qué deberías ver de inmediato?**
   * Conexión a WiFi (`192.168.0.21`).
   * Display de Marcha: Mostrará la letra **`n`** (Neutral).
   * Display de Velocidad: Mostrará el número **`0`** en el último dígito (los otros dos apagados).
   * Tira NeoPixel: Apagada (esperando aceleración).
4. **Abrir el software en la PC:**
   * En tu terminal de Linux:
     ```bash
     cd ~/Work/Volante-PC
     python3 main.py
     ```
   * O abre la interfaz gráfica / simulador (F1 2020/2023, Assetto Corsa, etc.).
5. **Comportamiento en pista:**
   * Al poner 1ª marcha: El display de 1 dígito cambiará a **`1`**.
   * Al acelerar el auto: La velocidad subirá en tiempo real (`  0` ➔ ` 45` ➔ `230`).
   * A partir del 50% de RPM: Se encenderán progresivamente los LEDs verdes, amarillos, rojos y azules.
   * Al llegar al 95% de RPM: La barra completa destellará para avisar el cambio de marcha.

---

## 🔧 9. Diagnóstico de Problemas Típicos (Troubleshooting)

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| **Un segmento no prende nunca** | Cable flojo o falso contacto en la protoboard. | Revisa el cable jumper y la resistencia de ese segmento específico. |
| **Un segmento queda siempre prendido** | Cortocircuito a GND en ese pin de segmento. | Separa los pines en la protoboard para evitar contacto entre pistas contiguas. |
| **Los números salen distorsionados** | Cables de segmentos intercambiados (ej: A por B). | Usa la tabla de la Sección 4 y verifica cable por cable. |
| **La velocidad se muestra en el display de marcha** | Cables de ánodos intercambiados. | Revisa GPIO 25 (Marcha) vs GPIO 26, 27, 14. |
| **Los NeoPixels no prenden o parpadean descontrolados** | Masa GND no compartida, o DIN conectado a DOUT al revés. | Asegura que el GND de los LEDs esté firmemente unido al GND del ESP32. Revisa la flecha DIN/DOUT. |
| **Los números parpadean muy rápido** | Normal en cámaras de celular (multiplexado a 125 Hz). | Para el ojo humano se ve estático y continuo. |
