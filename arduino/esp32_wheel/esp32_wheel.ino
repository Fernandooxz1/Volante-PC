/**
 * Volante-PC // Firmware Unificado ESP32 (Arduino C++)
 * Rama: testESP32
 * 
 * Hardware:
 * - AS5600 (I2C: GPIO 21 SDA, GPIO 22 SCL) -> Volante (10 bits)
 * - SS49E Hall (ADC1: GPIO 36) -> Acelerador (10 bits)
 * - 5 NeoPixels WS2812B (GPIO 13) -> Tacómetro RPM / Shift Light
 * - Transmisión serie binaria a 100 Hz (0xAA 0x55 <axes> <buttons>) hacia PC
 * - Recepción de telemetría por WiFi UDP (puerto 20778) y comandos Serial
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_NeoPixel.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// --- Pines ---
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22
#define PIN_HALL_ACCEL  32  // Pedal Acelerador (ADC1)
#define PIN_HALL_BRAKE  34  // Pedal Freno (ADC1)
#define PIN_HALL_CLUTCH 35  // Pedal Embrague / Clutch (ADC1)
#define PIN_HALL_VCC    33  // Alimentación 3.3V para pedales Hall
#define PIN_HALL_GND    25  // Masa GND para pedales Hall
#define PIN_NEOPIXEL        13
#define NUM_PIXELS          8
#define NEOPIXEL_BRIGHTNESS 40  // CAMBIAR BRILLO DE NEOPIXELS

// --- Matriz de Botones 4x3 (4 Filas x 3 Columnas = 12 botones) ---
// Diodos apuntan hacia las entradas (Filas) con resistencias en las columnas.
#define MATRIX_ACTIVE_HIGH  true // true: Columna HIGH -> Fila PULLDOWN lee HIGH al presionar
const uint8_t ROW_PINS[4] = {16, 17, 18, 19}; // 4 Entradas (Filas)
const uint8_t COL_PINS[3] = {23, 26, 27};     // 3 Salidas (Columnas con resistencias)

// --- Red WiFi y UDP ---
const char* WIFI_SSID     = "GingerBB";
const char* WIFI_PASSWORD = "sojesussalva";
const uint16_t UDP_PORT   = 20778;
WiFiUDP udp;

// --- Instancia NeoPixel ---
Adafruit_NeoPixel strip(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// --- Protocolo Volante-PC (10 Bytes: 2 Header + 8 Payload) ---
struct __attribute__((packed)) VolantePacket {
  uint8_t header1;      // 0xAA
  uint8_t header2;      // 0x55
  uint32_t axes;        // 30 bits de ejes: 10 steer, 10 accel, 10 brake
  uint16_t buttons;     // 16 bits de botones
  uint16_t clutch;      // 10 bits de embrague (0..1023)
};

VolantePacket packet;
const unsigned long INTERVALO_SERIAL_MS = 10; // 100 Hz
unsigned long ultimoTiempoSerial = 0;

// --- Procesador Inteligente de Sensor Hall SS49E para Pedales ---
// Diseñado específicamente para imanes físicamente distantes:
// 1. Sobremuestreo 32x en ADC de 12 bits para reducir drásticamente el ruido de lectura (< 1.5 cuentas).
// 2. Calibración automática y seguimiento suave del reposo (baseline) para compensar deriva térmica.
// 3. Detección bidireccional automática (funciona sin importar la polaridad N o S del imán).
// 4. Curva de respuesta temprana (potencia 0.55 / raíz) para contrarrestar la caída 1/d^3 del campo magnético:
//    detecta el pedal de inmediato al empezar a pisarlo, aumentando el recorrido activo útil.
// 5. Span adaptativo ultra sensible: arranca con umbral bajo (~115 mV) y se expande dinámicamente si el
//    recorrido mecánico entrega mayor señal, garantizando 0..1023 completo sin saturaciones.
// --- Procesador de Alta Estabilidad para Sensores Hall SS49E ---
// 1. Sobremuestreo 32x en el ADC de 12 bits nativo del ESP32 (0..4095) para eliminar ruido eléctrico.
// 2. Filtro exponencial continuo (EMA) para una señal suave y sólida sin latencia.
// 3. Conversión de 12 bits (0..4095) a 10 bits (0..1023) para el protocolo serie de Volante-PC.
struct HallPedal {
  uint8_t pin;
  int32_t filteredFixed; // punto fijo escala 256 en resolución de 12 bits
  bool initialized;

  void init(uint8_t p) {
    pin = p;
    filteredFixed = 0;
    initialized = false;
  }

  uint16_t readOversampled() {
    uint32_t sum = 0;
    for (int i = 0; i < 32; i++) {
      sum += analogRead(pin);
      delayMicroseconds(2);
    }
    return (uint16_t)(sum / 32);
  }

  void calibrateBaseline(int samples = 32) {
    // Mantener compatibilidad con comando serial 0xBB 0x88
    uint32_t sum = 0;
    for (int i = 0; i < samples; i++) {
      sum += readOversampled();
      delay(2);
    }
    filteredFixed = (int32_t)(sum / samples) << 8;
    initialized = true;
  }

  uint16_t process() {
    uint16_t raw12 = readOversampled();
    if (!initialized) {
      filteredFixed = (int32_t)raw12 << 8;
      initialized = true;
    }

    // Filtro EMA rápido a 100 Hz (alpha = 90/256 ≈ 0.35)
    const int32_t ALPHA = 90;
    int32_t currentFixed = (int32_t)raw12 << 8;
    filteredFixed += (((currentFixed - filteredFixed) * ALPHA) >> 8);

    uint16_t rawFiltered12 = (uint16_t)(filteredFixed >> 8);

    // Escalar de 12 bits (0..4095) a 10 bits (0..1023) para el protocolo
    uint16_t raw10 = rawFiltered12 >> 2;
    return constrain(raw10, 0, 1023);
  }
};

HallPedal hallAccel;
HallPedal hallBrake;
HallPedal hallClutch;

// --- Estado de Telemetría ---
uint8_t currentRevPercent = 0;
unsigned long lastTelemetryTime = 0;
bool flashState = false;
unsigned long lastFlashTime = 0;

// --- Lectura AS5600 por I2C (12 bits -> 0..4095) ---
uint16_t readAS5600Angle() {
  Wire.beginTransmission(0x36);
  Wire.write(0x0C); // RAW_ANGLE High Register
  if (Wire.endTransmission(false) != 0) {
    return 2048; // Centro si falla
  }
  Wire.requestFrom((uint8_t)0x36, (uint8_t)2);
  if (Wire.available() >= 2) {
    uint16_t high = Wire.read() & 0x0F;
    uint16_t low = Wire.read();
    return (high << 8) | low;
  }
  return 2048;
}

// --- Actualización de los 8 NeoPixels ---
void updateNeoPixels(uint8_t revs_pct) {
  if (revs_pct < 20) {
    strip.clear();
    strip.show();
    return;
  }

  // Shift Flash a >= 97%
  if (revs_pct >= 97) {
    unsigned long now = millis();
    if (now - lastFlashTime > 70) {
      flashState = !flashState;
      lastFlashTime = now;
    }
    uint32_t colorFlash = flashState ? strip.Color(0, 40, 240) : strip.Color(220, 220, 220);
    for (int i = 0; i < NUM_PIXELS; i++) strip.setPixelColor(i, colorFlash);
    strip.show();
    return;
  }

  // Escala Progresiva F1 (4 Rojos + 4 Azules):
  // 4 Rojos: 20%, 35%, 50%, 65%
  // 4 Azules: 75%, 83%, 90%, 95%
  const uint8_t thresholds[8] = {20, 35, 50, 65, 75, 83, 90, 95};
  const uint32_t colors[8] = {
    strip.Color(220, 0, 0),    // Rojo 1 (20%)
    strip.Color(220, 0, 0),    // Rojo 2 (35%)
    strip.Color(220, 0, 0),    // Rojo 3 (50%)
    strip.Color(220, 0, 0),    // Rojo 4 (65%)
    strip.Color(0, 0, 220),   // Azul 1 (75%)
    strip.Color(0, 0, 220),   // Azul 2 (83%)
    strip.Color(0, 0, 220),   // Azul 3 (90%)
    strip.Color(0, 0, 220)    // Azul 4 (95% Upshift)
  };

  for (int i = 0; i < NUM_PIXELS; i++) {
    if (revs_pct >= thresholds[i]) {
      strip.setPixelColor(i, colors[i]);
    } else {
      strip.setPixelColor(i, strip.Color(0, 0, 0));
    }
  }
  strip.show();
}

void setup() {
  // Desactivar detector de caídas de tensión (Brownout) para evitar reinicios por consumo pico
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);

  // Apagar WiFi para ahorrar ~300mA de consumo pico (usamos USB directo a 100 Hz)
  WiFi.mode(WIFI_OFF);

  // I2C para AS5600
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);

  // Alimentación dedicada para los 3 sensores Hall (GPIO 33 a 3.3V, GPIO 25 a 0V)
  pinMode(PIN_HALL_VCC, OUTPUT);
  digitalWrite(PIN_HALL_VCC, HIGH);
  pinMode(PIN_HALL_GND, OUTPUT);
  digitalWrite(PIN_HALL_GND, LOW);

  // Configuración de resolución y atenuación ADC1 (0..3.3V) para los 3 pedales Hall
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_HALL_ACCEL, ADC_11db);
  analogSetPinAttenuation(PIN_HALL_BRAKE, ADC_11db);
  analogSetPinAttenuation(PIN_HALL_CLUTCH, ADC_11db);

  hallAccel.init(PIN_HALL_ACCEL);
  hallBrake.init(PIN_HALL_BRAKE);
  hallClutch.init(PIN_HALL_CLUTCH);

  // Calibrar líneas de base de reposo de los 3 pedales
  delay(100);
  hallAccel.calibrateBaseline(32);
  hallBrake.calibrateBaseline(32);
  hallClutch.calibrateBaseline(32);

  // NeoPixels
  strip.begin();
  strip.setBrightness(NEOPIXEL_BRIGHTNESS);
  strip.clear();
  strip.show();

  // Configuración de la Matriz 4x3
  for (int r = 0; r < 4; r++) {
    pinMode(ROW_PINS[r], MATRIX_ACTIVE_HIGH ? INPUT_PULLDOWN : INPUT_PULLUP);
  }
  for (int c = 0; c < 3; c++) {
    pinMode(COL_PINS[c], OUTPUT);
    digitalWrite(COL_PINS[c], MATRIX_ACTIVE_HIGH ? LOW : HIGH);
  }

  // Paquete
  packet.header1 = 0xAA;
  packet.header2 = 0x55;
}

void loop() {
  unsigned long now = millis();

  // 1. Recepción UDP de telemetría (desde core/esp32_bridge.py si hay WiFi)
  int packetSize = udp.parsePacket();
  if (packetSize >= 9) {
    uint8_t udpBuffer[16];
    udp.read(udpBuffer, sizeof(udpBuffer));
    if (udpBuffer[0] == 0xAA && udpBuffer[1] == 0x55) {
      currentRevPercent = udpBuffer[7]; // rev_lights_percent
      lastTelemetryTime = now;
      updateNeoPixels(currentRevPercent);
    }
  }

  // 2. Recepción Serial de telemetría y comandos por cable USB
  while (Serial.available() >= 3) {
    if (Serial.peek() == 0xBB) {
      Serial.read(); // Consume 0xBB
      uint8_t cmd = Serial.read();
      if (cmd == 0x77) {
        // Telemetría directa de RPM por USB: 0xBB 0x77 <rev_pct>
        uint8_t rev_pct = Serial.read();
        currentRevPercent = rev_pct;
        lastTelemetryTime = now;
        updateNeoPixels(currentRevPercent);
      } else if (cmd == 0x66) {
        // Comando de color estático / heartbeat
        uint8_t colorCode = Serial.read();
        if (now - lastTelemetryTime > 2000) {
          if (colorCode == 0) {
            strip.clear();
            strip.show();
          } else {
            uint32_t c = strip.Color(0, 0, 180); // Azul
            if (colorCode == 1) c = strip.Color(180, 0, 0); // Rojo
            else if (colorCode == 2) c = strip.Color(0, 180, 0); // Verde
            for (int i = 0; i < NUM_PIXELS; i++) strip.setPixelColor(i, c);
            strip.show();
          }
        }
      } else if (cmd == 0x88) {
        // Comando 0xBB 0x88: Recalibrar reposo de los 3 pedales Hall
        hallAccel.calibrateBaseline(32);
        hallBrake.calibrateBaseline(32);
        hallClutch.calibrateBaseline(32);
      } else {
        Serial.read();
      }
    } else {
      Serial.read();
    }
  }

  // Si pasan más de 2 segundos sin telemetría, apagar LEDs
  if (now - lastTelemetryTime > 2000 && currentRevPercent != 0) {
    currentRevPercent = 0;
    updateNeoPixels(0);
  }

  // 3. Lectura de Sensores y transmisión a 100 Hz
  if (now - ultimoTiempoSerial >= INTERVALO_SERIAL_MS) {
    ultimoTiempoSerial = now;

    // Volante (AS5600: 0..4095 -> 10 bits: 0..1023 digital directo I2C)
    // Se envía directo sin filtro lineal para permitir el salto circular instantáneo 1023 <-> 0 (desenrollado multi-vuelta)
    uint16_t angleRaw = readAS5600Angle() >> 2;
    uint32_t steer = constrain(angleRaw, 0, 1023);

    // Pedales Hall SS49E (Oversampling 32x + compensación no lineal magnética de amplio alcance)
    uint32_t accel = hallAccel.process();
    uint32_t brake = hallBrake.process();
    uint32_t clutch = hallClutch.process();

    // Escaneo de Matriz 4x3 (12 botones)
    uint16_t matrixButtons = 0;
    for (int c = 0; c < 3; c++) {
      digitalWrite(COL_PINS[c], MATRIX_ACTIVE_HIGH ? HIGH : LOW);
      delayMicroseconds(5); // Estabilización
      for (int r = 0; r < 4; r++) {
        bool pressed = (digitalRead(ROW_PINS[r]) == (MATRIX_ACTIVE_HIGH ? HIGH : LOW));
        if (pressed) {
          int btnIndex = (r * 3) + c; // Botón 0 a 11
          matrixButtons |= (1 << btnIndex);
        }
      }
      digitalWrite(COL_PINS[c], MATRIX_ACTIVE_HIGH ? LOW : HIGH);
    }

    packet.axes = (steer & 0x3FF) | ((accel & 0x3FF) << 10) | ((brake & 0x3FF) << 20);
    packet.buttons = matrixButtons;
    packet.clutch = clutch & 0x3FF;

    Serial.write((uint8_t*)&packet, sizeof(VolantePacket));
  }
}
