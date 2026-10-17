
#include <Arduino.h>
#include <BLE.h>

// Keep the most recent event sequence from each controller.
bool seenSequence[2] = {false, false};
uint8_t lastSequence[2] = {0, 0};

// Print an action in a readable format.
void handleAction(int player, char action) {
  Serial.print("P");
  Serial.print(player);
  Serial.print(" ");

  switch (action) {
    case 'S': Serial.println("SHAKE"); break;
    case 'F': Serial.println("FLICK UP"); break;
    case 'L': Serial.println("TILT LEFT"); break;
    case 'R': Serial.println("TILT RIGHT"); break;
    case 'C': Serial.println("TILT CENTER"); break;
    case 'J': Serial.println("JOYSTICK LEFT"); break;
    case 'K': Serial.println("JOYSTICK RIGHT"); break;
    case 'U': Serial.println("JOYSTICK UP"); break;
    case 'D': Serial.println("JOYSTICK DOWN"); break;
    case 'Z': Serial.println("JOYSTICK CENTER"); break;
    case 'B': Serial.println("BUTTON PRESSED"); break;
    case 'b': Serial.println("BUTTON RELEASED"); break;
    default: return;
  }

  // Eventually, this is where we'll update gameplay.
}

void readControllerPacket(const uint8_t* data, int length) {
  if (length != 7 || data == nullptr) return;

  // Check our custom AstroLab packet signature.
  if (data[0] != 0xFF || data[1] != 0xFF ||
      data[2] != 'A' || data[3] != 'L') {
    return;
  }

  char playerByte = (char)data[4];
  if (playerByte != '1' && playerByte != '2') return;

  int player = playerByte - '0';
  int index = player - 1;

  char action = (char)data[5];
  uint8_t sequence = data[6];

  // Idle packet: nothing to do.
  if (action == 'I') return;

  // Ignore repeated advertisements of the same event.
  if (seenSequence[index] &&
      lastSequence[index] == sequence) {
    return;
  }

  seenSequence[index] = true;
  lastSequence[index] = sequence;

  handleAction(player, action);
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_BUILTIN, OUTPUT);

  Serial.println("AstroLab Pico 2 W starting...");

  BLE.begin("AstroLab-Pico");

  Serial.println("Bluetooth ready!");
  Serial.println("Scanning for P1 and P2...");
}

void loop() {
  // Temporary proof-of-concept:
  // This scan blocks for approximately 1 second.
  auto* results = BLE.scan(1);

  if (results != nullptr) {
    for (auto& device : *results) {
      const uint8_t* data = nullptr;

      int length = device.getManufacturerData(&data);

      readControllerPacket(data, length);
    }
  }

  BLE.clearScan();
}
