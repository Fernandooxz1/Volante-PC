/**
 * Volante para PC - Firmware Arduino Nano (Optimizado)
 * 
 * Versión optimizada:
 *  - Cero operaciones de punto flotante (float) para ahorrar CPU y memoria.
 *  - Empaquetado de bits: Tres lecturas de 10 bits se empaquetan en 30 bits dentro de
 *    un entero de 32 bits (4 bytes) + un encabezado de sincronización de 2 bytes (0xAA55).
 *  - Envío binario ultra rápido por Serial.write (6 bytes en total), reduciendo la latencia
 *    y el uso de memoria comparado con el formateo de texto/ASCII.
 */

// Configuración de pines analógicos
const int PIN_DIRECCION = A0;
const int PIN_ACELERADOR = A1;
const int PIN_FRENO = A2;

// Factor de suavizado para el filtro EMA en punto fijo (escala de 256)
// 90/256 equivale aproximadamente a ALPHA = 0.35
const int32_t ALPHA_FIXED = 90;

// Variables de filtro en punto fijo (escaladas por 256)
int32_t filtradoDireccion = 512 * 256; 
int32_t filtradoAcelerador = 0;
int32_t filtradoFreno = 0;

// Estructura de paquete binario optimizada (6 bytes en total)
struct __attribute__((packed)) VolantePacket {
  uint8_t header1;      // 0xAA (Sincronización)
  uint8_t header2;      // 0x55 (Sincronización)
  uint32_t data : 30;   // 30 bits para: 10 dir, 10 acel, 10 freno
  uint32_t padding : 2; // 2 bits de relleno (0)
};

VolantePacket packet;

// Intervalo de transmisión en milisegundos (10ms = 100Hz)
const unsigned long INTERVALO_MS = 10;
unsigned long ultimoTiempoTransmision = 0;

void setup() {
  // Inicialización de la comunicación serie a alta velocidad
  Serial.begin(115200);
  
  // Establecer encabezados estáticos del paquete
  packet.header1 = 0xAA;
  packet.header2 = 0x55;
  packet.padding = 0;

  // Lectura inicial escalada por 256
  filtradoDireccion = (int32_t)analogRead(PIN_DIRECCION) << 8;
  filtradoAcelerador = (int32_t)analogRead(PIN_ACELERADOR) << 8;
  filtradoFreno = (int32_t)analogRead(PIN_FRENO) << 8;
}

void loop() {
  unsigned long tiempoActual = millis();

  // Lecturas analógicas de 10 bits (0-1023)
  int32_t lecturaRawDireccion = analogRead(PIN_DIRECCION) << 8;
  int32_t lecturaRawAcelerador = analogRead(PIN_ACELERADOR) << 8;
  int32_t lecturaRawFreno = analogRead(PIN_FRENO) << 8;

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

    // Empaquetar valores: 10 bits dirección (0-9), 10 bits acel (10-19), 10 bits freno (20-29)
    packet.data = steer | (accel << 10) | (brake << 20);

    // Enviar el paquete binario de 6 bytes de un solo golpe
    Serial.write((uint8_t*)&packet, sizeof(VolantePacket));
  }
}
