
#include <Arduino.h>
#include <BLE.h>
#include <BluetoothLock.h>
#include <btstack.h>
#include "ControllerProtocol.h"

static constexpr uint8_t QUEUE_SIZE = 32;
static constexpr uint32_t CONNECTION_TIMEOUT_MS = 1200; // more forgiving than 500 ms
static constexpr uint32_t MAX_QUEUED_AGE_MS = 500;
static constexpr uint32_t STATE_INTERVAL_MS = 50;

static btstack_packet_callback_registration_t handler;
struct Pending { ControllerPacket packet; uint32_t at; };
static Pending pending[QUEUE_SIZE];
static volatile uint8_t head = 0, tail = 0;

struct Player {
  bool seen = false;
  bool sequenceSeen = false;
  bool online = false;
  uint8_t sequence = 0;
  uint32_t last = 0;
  int8_t forward = 0, steer = 0, tilt = 0;
};
static Player players[2];
static uint32_t sentAt = 0;

// Callback context: only decode and enqueue. No USB Serial printing here.
static void receiveAdvertisement(uint8_t type, uint16_t channel,
                                 uint8_t* packet, uint16_t size) {
  (void)channel;
  if (type != HCI_EVENT_PACKET || size < 2 ||
      hci_event_packet_get_type(packet) != GAP_EVENT_ADVERTISING_REPORT) return;

  const uint8_t* adv = gap_event_advertising_report_get_data(packet);
  const uint8_t length = gap_event_advertising_report_get_data_length(packet);
  for (size_t pos = 0; pos < length;) {
    const size_t field = adv[pos];
    if (!field || pos + 1 + field > length) break;

    ControllerPacket decoded;
    if (adv[pos + 1] == 0xFF && field >= 2 &&
        decodeController(adv + pos + 2, field - 1, decoded)) {
      const uint8_t next = (head + 1) % QUEUE_SIZE;
      if (next != tail) {
        pending[head] = {decoded, millis()};
        head = next;
      }
    }
    pos += field + 1;
  }
}

static void actionLine(uint8_t player, const char* action) {
  Serial.print("REMOTE,P");
  Serial.print(player + 1);
  Serial.print(',');
  Serial.println(action);
}

static void stateLine(uint8_t player, const Player& p) {
  Serial.print("REMOTE,P");
  Serial.print(player + 1);
  Serial.print(",STATE,");
  Serial.print(p.forward / 100.0f, 2);
  Serial.print(',');
  Serial.print(p.steer / 100.0f, 2);
  Serial.print(',');
  Serial.println(p.tilt / 100.0f, 2);
}

static void applyLegacyDirection(Player& p, char action) {
  switch (action) {
    case 'U': p.forward = 100;  p.steer = 0;   break;
    case 'D': p.forward = -100; p.steer = 0;   break;
    case 'J': p.steer = -100;   p.forward = 0; break;
    case 'K': p.steer = 100;    p.forward = 0; break;
    case 'Z': p.forward = 0;    p.steer = 0;   break;
    case 'L': p.tilt = -100; break;
    case 'R': p.tilt = 100;  break;
    case 'C': p.tilt = 0;    break;
    default: break;
  }
}

static void accept(const Pending& entry) {
  const ControllerPacket& e = entry.packet;
  if (e.player >= 2) return;
  Player& p = players[e.player];

  // A gap can mean the ESP stopped advertising OR packets were missed.
  const bool reconnect = !p.seen || (uint32_t)(entry.at - p.last) > CONNECTION_TIMEOUT_MS;
  p.seen = true;
  p.online = true;
  p.last = entry.at;

  // Sequence modulo-256 ordering: delta 1..127 means newer.
  // Avoid replaying stale data on an existing session.
  if (reconnect) {
    p.sequenceSeen = true;
    p.sequence = e.sequence;
    // Never replay a discrete button, shake or flick after reconnect.
    // But DO restore directional state from the first received packet.
    if (e.snapshot) {
      p.forward = e.forward;
      p.steer = e.steer;
      p.tilt = e.tilt;
    } else {
      applyLegacyDirection(p, e.action);
    }
    return;
  }

  if (p.sequenceSeen) {
    const uint8_t delta = uint8_t(e.sequence - p.sequence);
    if (delta == 0 || delta >= 128) return;
  }
  p.sequenceSeen = true;
  p.sequence = e.sequence;

  if (e.snapshot) {
    p.forward = e.forward;
    p.steer = e.steer;
    p.tilt = e.tilt;
  } else {
    applyLegacyDirection(p, e.action);
  }

  switch (e.action) {
    case 'B': actionLine(e.player, "SELECT"); break;
    case 'S': actionLine(e.player, "SHAKE"); break;
    case 'F': actionLine(e.player, "UPWARD_FLICK"); break;
    default: break;
  }
}

void setup() {
  Serial.begin(115200);
  // Do not block waiting for USB Serial; BLE should start even if no laptop is attached.
  if (!BLE.begin("AstroLab-Pico")) {
    // The Arduino-Pico Bluetooth stack must be enabled in IDE settings.
    while (true) delay(1000);
  }
  {
    BluetoothLock lock;
    handler.callback = receiveAdvertisement;
    hci_add_event_handler(&handler);
    // Reuse the API from the user's previously WORKING asynchronous receiver.
    gap_set_scan_params(0, 48, 48, 0);
    gap_start_scan();
  }
  Serial.println("ASTROLAB,READY");
}

void loop() {
  for (uint8_t n = 0; n < QUEUE_SIZE; ++n) {
    Pending entry;
    bool available = false;
    {
      BluetoothLock lock;
      if (tail != head) {
        entry = pending[tail];
        tail = (tail + 1) % QUEUE_SIZE;
        available = true;
      }
    }
    if (!available) break;
    if ((uint32_t)(millis() - entry.at) <= MAX_QUEUED_AGE_MS) accept(entry);
  }

  if ((uint32_t)(millis() - sentAt) >= STATE_INTERVAL_MS && Serial) {
    sentAt = millis();
    for (uint8_t i = 0; i < 2; ++i) {
      Player& p = players[i];
      const bool fresh = p.seen && (uint32_t)(sentAt - p.last) < CONNECTION_TIMEOUT_MS;
      if (!fresh) {
        if (p.online) {
          p.forward = p.steer = p.tilt = 0;
          stateLine(i, p); // Tell Python steering is now neutral.
          actionLine(i, "DISCONNECTED");
          p.online = false;
        }
        continue;
      }
      stateLine(i, p);
    }
  }

  // Compatibility with legacy backend commands. This hub does not process
  // gameplay commands: Python is responsible for actual game rules.
  while (Serial.available()) (void)Serial.read();
  delay(1);
}
