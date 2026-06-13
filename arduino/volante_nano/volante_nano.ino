/**
 * Volante para PC - Firmware Arduino Uno/Nano (Multibotón Optimizado)
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

// Pines digitales para botones (Pines del 2 al 9)
const int NUM_BOTONES = 8;
const int PIN_BOTONES[NUM_BOTONES] = {2, 3, 4, 5, 6, 7, 8, 9};

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
}

void loop() {
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
