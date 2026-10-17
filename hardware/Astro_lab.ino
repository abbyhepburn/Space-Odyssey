
#include <Arduino.h>
#include <BLE.h>

// Remember when we last received a shake.
unsigned long lastShakeReceived = 0;

// Whether the Pico LED is currently on.
bool ledOn = false;

// Handle a message from either player.
void handleBluetooth(char player, char command) {

    if (command == 'S') {

        Serial.print("SHAKE DETECTED FROM PLAYER ");
        Serial.println(player);

        // Turn on the Pico's built-in LED.
        digitalWrite(LED_BUILTIN, HIGH);

        ledOn = true;
        lastShakeReceived = millis();
    }
}


void setup() {

    Serial.begin(115200);

    while (!Serial && millis() < 5000) {
        delay(10);
    }

    // Configure Pico built-in LED.
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);

    Serial.println("Pico starting...");

    // Start the Bluetooth receiver.
    BLE.begin("AstroLab-Hub");

    Serial.println("Bluetooth ready!");
    Serial.println("Waiting for controller shake...");
}


void loop() {

    // Scan for broadcasts for one second.
    BLEScanReport* devices = BLE.scan(1);

    if (devices != nullptr) {

        // Check each discovered Bluetooth device.
        for (auto& device : *devices) {

            const uint8_t* data = nullptr;

            int length = device.getManufacturerData(&data);

            // Validate the AstroLab packet.
            if (data != nullptr &&
                length >= 6 &&
                data[0] == 0xFF &&
                data[1] == 0xFF &&
                data[2] == 'A' &&
                data[3] == 'L') {

                // Extract the player number and command.
                char player = (char)data[4];
                char command = (char)data[5];

                // Accept either controller.
                if (player == '1' || player == '2') {

                    // Only SHAKE events turn on the LED.
                    if (command == 'S') {
                        handleBluetooth(player, command);
                    }
                }
            }
        }
    }

    // Clear the results before scanning again.
    BLE.clearScan();

    // Turn the LED off after no shake has been
    // received for 1.8 seconds.
    if (ledOn &&
        millis() - lastShakeReceived >= 1800) {
            

        digitalWrite(LED_BUILTIN, LOW);
        ledOn = false;

        Serial.println("LED OFF");
    }
}
