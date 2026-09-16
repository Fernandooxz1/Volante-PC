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

// --- Pines ---
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22
#define PIN_HALL_ACCEL  32
#define PIN_HALL_VCC    33
#define PIN_HALL_GND    25
#define PIN_HALL_BRAKE  34
#define PIN_NEOPIXEL    13
#define NUM_PIXELS      5

// --- Red WiFi y UDP ---
const char* WIFI_SSID     = "GingerBB";
const char* WIFI_PASSWORD = "sojesussalva";
const uint16_t UDP_PORT   = 20778;
WiFiUDP udp;

// --- Instancia NeoPixel ---
Adafruit_NeoPixel strip(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// --- Protocolo Volante-PC (8 Bytes) ---
struct __attribute__((packed)) VolantePacket {
  uint8_t header1;      // 0xAA
  uint8_t header2;      // 0x55
  uint32_t axes;        // 30 bits de ejes: 10 steer, 10 accel, 10 brake
  uint16_t buttons;     // 16 bits de botones
};

VolantePacket packet;
const unsigned long INTERVALO_SERIAL_MS = 10; // 100 Hz
unsigned long ultimoTiempoSerial = 0;

// --- Filtros EMA en punto fijo (escala 256) ---
const int32_t ALPHA_FIXED = 90; // ~0.35
int32_t filtradoSteer = 512L * 256;
int32_t filtradoAccel = 0;
int32_t filtradoBrake = 0;

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

// --- Actualización de los 5 NeoPixels ---
void updateNeoPixels(uint8_t revs_pct) {
  if (revs_pct < 50) {
    strip.clear();
    strip.show();
    return;
  }

  // Shift Flash a >= 96%
  if (revs_pct >= 96) {
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

  // Escala para 5 LEDs: [50, 65, 78, 88, 94]
  const uint8_t thresholds[5] = {50, 65, 78, 88, 94};
  const uint32_t colors[5] = {
    strip.Color(0, 180, 0),    // Verde 1 (50%)
    strip.Color(0, 180, 0),    // Verde 2 (65%)
    strip.Color(200, 140, 0),  // Amarillo (78%)
    strip.Color(220, 0, 0),    // Rojo (88%)
    strip.Color(0, 40, 240)    // Azul (94% Upshift)
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
  Serial.begin(115200);

  // I2C para AS5600
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);

  // Alimentación y lectura ADC para SS49E
  pinMode(PIN_HALL_VCC, OUTPUT);
  digitalWrite(PIN_HALL_VCC, HIGH); // 3.3V al pin izquierdo
  pinMode(PIN_HALL_GND, OUTPUT);
  digitalWrite(PIN_HALL_GND, LOW);  // 0V al pin central

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_HALL_ACCEL, ADC_11db);
  analogSetPinAttenuation(PIN_HALL_BRAKE, ADC_11db);

  // NeoPixels
  strip.begin();
  strip.setBrightness(180);
  strip.show();

  // Paquete
  packet.header1 = 0xAA;
  packet.header2 = 0x55;

  // WiFi UDP
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  udp.begin(UDP_PORT);
}

void loop() {
  unsigned long now = millis();

  // 1. Recepción UDP de telemetría (desde core/esp32_bridge.py)
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

  // 2. Recepción Serial de fallback (Comando 0xBB 0x66 <color>)
  while (Serial.available() >= 3) {
    if (Serial.peek() == 0xBB) {
      Serial.read();
      if (Serial.read() == 0x66) {
        uint8_t colorCode = Serial.read();
        if (now - lastTelemetryTime > 2000) {
          // Color estático si no hay juego emitiendo UDP
        }
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

    // Volante (AS5600: 0..4095 -> 10 bits: 0..1023)
    uint16_t angleRaw = readAS5600Angle() >> 2;
    int32_t steerFixed = (int32_t)angleRaw << 8;
    filtradoSteer += (((steerFixed - filtradoSteer) * ALPHA_FIXED) >> 8);

    // Acelerador (SS49E: 0..4095 -> 10 bits: 0..1023)
    uint16_t accelRaw = analogRead(PIN_HALL_ACCEL) >> 2;
    int32_t accelFixed = (int32_t)accelRaw << 8;
    filtradoAccel += (((accelFixed - filtradoAccel) * ALPHA_FIXED) >> 8);

    // Freno (Opcional en GPIO 34)
    uint16_t brakeRaw = analogRead(PIN_HALL_BRAKE) >> 2;
    int32_t brakeFixed = (int32_t)brakeRaw << 8;
    filtradoBrake += (((brakeFixed - filtradoBrake) * ALPHA_FIXED) >> 8);

    // Empaquetar valores en 30 bits
    uint32_t steer = constrain(filtradoSteer >> 8, 0, 1023);
    uint32_t accel = constrain(filtradoAccel >> 8, 0, 1023);
    uint32_t brake = constrain(filtradoBrake >> 8, 0, 1023);

    packet.axes = (steer & 0x3FF) | ((accel & 0x3FF) << 10) | ((brake & 0x3FF) << 20);
    packet.buttons = 0;

    Serial.write((uint8_t*)&packet, sizeof(VolantePacket));
  }
}
