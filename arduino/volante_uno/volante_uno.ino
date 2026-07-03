/**
 * Volante para PC - Firmware Arduino UNO (Multibotón Optimizado)
 * 
 * Versión optimizada con soporte para 8 botones (Pines del 2 al 9):
 *  - Cero operaciones de punto flotante.
 *  - Ejes empaquetados en un entero de 32 bits (10 bits dir, 10 acel, 10 freno).
 *  - 8 Botones digitales empaquetados en un entero de 16 bits (bits 0-7).
 *  - Envío binario ultra rápido por Serial.write (8 bytes en total).
 */

// Configuración de pines analógicos
const int PIN_DIRECCION = A0;
const int PIN_ACELERADOR = A1;
const int PIN_FRENO = A2;

// Pines digitales para botones (Pines del 2 al 12)
const int NUM_BOTONES = 11;
const int PIN_BOTONES[NUM_BOTONES] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};

// Factor de suavizado para el filtro EMA en punto fijo (escala de 256)
// 90/256 equivale aproximadamente a ALPHA = 0.35
const int32_t ALPHA_FIXED = 90;

// Variables de filtro en punto fijo (escaladas por 256)
int32_t filtradoDireccion = 512L * 256; 
int32_t filtradoAcelerador = 0;
int32_t filtradoFreno = 0;

// Estructura de paquete binario optimizada (8 bytes en total)
struct __attribute__((packed)) VolantePacket {
  uint8_t header1;      // 0xAA (Sincronización)
  uint8_t header2;      // 0x55 (Sincronización)
  uint32_t axes;        // 30 bits: 10 dir, 10 acel, 10 freno. 2 bits padding.
  uint16_t buttons;     // 16 bits para los 8 botones (bits del 0 al 7)
};

VolantePacket packet;

// Intervalo de transmisión en milisegundos (10ms = 100Hz)
const unsigned long INTERVALO_MS = 10;
unsigned long ultimoTiempoTransmision = 0;

// Configuración de pines para el LED RGB
const int PIN_LED_R = A3;
const int PIN_LED_G = A5;
const int PIN_LED_B = A4;

// Brillo objetivo para cada canal (escala de 0 a 100)
uint8_t targetR = 0;
uint8_t targetG = 0;
uint8_t targetB = 0;

// Estado de conexión con la PC
bool pcConnected = false;
unsigned long lastPacketTime = 0;

void setLedColor(uint8_t code) {
  switch (code) {
    case 0: // Apagado
      targetR = 0; targetG = 0; targetB = 0;
      break;
    case 1: // Rojo
      targetR = 100; targetG = 0; targetB = 0;
      break;
    case 2: // Verde
      targetR = 0; targetG = 100; targetB = 0;
      break;
    case 3: // Azul
      targetR = 0; targetG = 0; targetB = 100;
      break;
    case 4: // Amarillo
      targetR = 100; targetG = 100; targetB = 0;
      break;
    case 5: // Violeta
      targetR = 100; targetG = 0; targetB = 100;
      break;
    case 6: // Celeste / Cian
      targetR = 0; targetG = 100; targetB = 100;
      break;
    case 7: // Naranja
      targetR = 100; targetG = 20; targetB = 0;
      break;
    default:
      break;
  }
}

void setup() {
  // Inicialización de la comunicación serie a alta velocidad
  Serial.begin(115200);
  
  // Configurar los pines de los 8 botones con resistencia de pull-up interna
  for (int i = 0; i < NUM_BOTONES; i++) {
    pinMode(PIN_BOTONES[i], INPUT_PULLUP);
  }
  
  // Establecer encabezados estáticos del paquete
  packet.header1 = 0xAA;
  packet.header2 = 0x55;
  packet.axes = 0;
  packet.buttons = 0;

  // Lectura inicial de sensores analógicos escalada por 256
  filtradoDireccion = (int32_t)analogRead(PIN_DIRECCION) << 8;
  filtradoAcelerador = (int32_t)analogRead(PIN_ACELERADOR) << 8;
  filtradoFreno = (int32_t)analogRead(PIN_FRENO) << 8;

  // Configurar pines del LED RGB como salidas
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  
  // Apagar leds inicialmente (HIGH para ánodo común)
  digitalWrite(PIN_LED_R, HIGH);
  digitalWrite(PIN_LED_G, HIGH);
  digitalWrite(PIN_LED_B, HIGH);
  
  // Color inicial (Azul para indicar listo)
  setLedColor(3);
}

void loop() {
  // --- Control de tiempo de vida de la conexión con PC ---
  if (pcConnected && (millis() - lastPacketTime > 5000)) {
    pcConnected = false;
  }

  // --- Lectura de comandos serie para LED RGB (no bloqueante) ---
  while (Serial.available() >= 3) {
      if (Serial.peek() == 0xBB) {
        Serial.read(); // Descartar cabecera 0xBB
        uint8_t b1 = Serial.read();
        uint8_t b2 = Serial.read();
        if (b1 == 0x66) {
          setLedColor(b2);
          pcConnected = true;
          lastPacketTime = millis();
        }
      } else {
        Serial.read(); // Descartar byte desalineado
      }
  }

  // --- Animación de variación de colores si la PC no está conectada ---
  if (!pcConnected) {
    static unsigned long lastFadeTime = 0;
    if (millis() - lastFadeTime >= 30) { // Actualizar tono cada 30ms
      lastFadeTime = millis();
      
      static uint8_t fadeState = 0; // Estado actual (0-5)
      static uint8_t fadeVal = 0;   // Brillo dinámico (0-100)
      
      fadeVal++;
      if (fadeVal > 100) {
        fadeVal = 0;
        fadeState = (fadeState + 1) % 6;
      }
      
      switch (fadeState) {
        case 0: // Rojo -> Amarillo (R=100, G sube)
          targetR = 100; targetG = fadeVal; targetB = 0;
          break;
        case 1: // Amarillo -> Verde (G=100, R baja)
          targetR = 100 - fadeVal; targetG = 100; targetB = 0;
          break;
        case 2: // Verde -> Cian (G=100, B sube)
          targetR = 0; targetG = 100; targetB = fadeVal;
          break;
        case 3: // Cian -> Azul (B=100, G baja)
          targetR = 0; targetG = 100 - fadeVal; targetB = 100;
          break;
        case 4: // Azul -> Magenta (B=100, R sube)
          targetR = fadeVal; targetG = 0; targetB = 100;
          break;
        case 5: // Magenta -> Rojo (R=100, B baja)
          targetR = 100; targetG = 0; targetB = 100 - fadeVal;
          break;
      }
    }
  }

  // --- Ciclo Software-PWM para los leds RGB ---
  static uint8_t pwmCounter = 0;
  pwmCounter++;
  if (pwmCounter >= 100) {
    pwmCounter = 0;
  }
  digitalWrite(PIN_LED_R, pwmCounter < targetR ? LOW : HIGH);
  digitalWrite(PIN_LED_G, pwmCounter < targetG ? LOW : HIGH);
  digitalWrite(PIN_LED_B, pwmCounter < targetB ? LOW : HIGH);

  unsigned long tiempoActual = millis();

  // Lecturas analógicas de 10 bits (0-1023)
  int32_t lecturaRawDireccion = (int32_t)analogRead(PIN_DIRECCION) << 8;
  int32_t lecturaRawAcelerador = (int32_t)analogRead(PIN_ACELERADOR) << 8;
  int32_t lecturaRawFreno = (int32_t)analogRead(PIN_FRENO) << 8;

  // Filtro promedio móvil exponencial (EMA) usando aritmética de enteros rápida
  filtradoDireccion = filtradoDireccion + (((lecturaRawDireccion - filtradoDireccion) * ALPHA_FIXED) >> 8);
  filtradoAcelerador = filtradoAcelerador + (((lecturaRawAcelerador - filtradoAcelerador) * ALPHA_FIXED) >> 8);
  filtradoFreno = filtradoFreno + (((lecturaRawFreno - filtradoFreno) * ALPHA_FIXED) >> 8);

  // Transmisión periódica binaria
  if (tiempoActual - ultimoTiempoTransmision >= INTERVALO_MS) {
    ultimoTiempoTransmision = tiempoActual;

    // Desescalar valores (dividir por 256 mediante desplazamiento de bits)
    int32_t valorDireccion = filtradoDireccion >> 8;
    int32_t valorAcelerador = filtradoAcelerador >> 8;
    int32_t valorFreno = filtradoFreno >> 8;

    // Asegurar límites seguros (0 a 1023)
    uint32_t steer = constrain(valorDireccion, 0, 1023);
    uint32_t accel = constrain(valorAcelerador, 0, 1023);
    uint32_t brake = constrain(valorFreno, 0, 1023);

    // Empaquetar valores analógicos:
    // 10 bits dirección (0-9), 10 bits acel (10-19), 10 bits freno (20-29)
    packet.axes = steer | (accel << 10) | (brake << 20);

    // Leer el estado de los 8 botones físicos (pines 2 al 9)
    // Con INPUT_PULLUP, al presionar da LOW (0). Invertimos el bit: 1 = presionado, 0 = suelto.
    uint16_t buttonsState = 0;
    for (int i = 0; i < NUM_BOTONES; i++) {
      if (digitalRead(PIN_BOTONES[i]) == LOW) {
        buttonsState |= (1 << i);
      }
    }
    packet.buttons = buttonsState;

    // Enviar el paquete binario de 8 bytes de un solo golpe (2 sync, 4 axes, 2 buttons)
    Serial.write((uint8_t*)&packet, sizeof(VolantePacket));
  }
}
