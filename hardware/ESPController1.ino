// Controllers use same sketch with slight chages with name (player #, and sensor type)
// Controller 1 with MPU 6050
// Controller 2 with MPU 9250

#include <Arduino.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEAdvertising.h>
#include <math.h>

//-------------------Controller Definitions--------------------------------------------

#define PLAYER_ID 1   
#define SENSOR_TYPE 6050

// Uncommment when uploading to controller 2 and vice versa 

// #define PLAYER_ID 2 
// #define SENSOR_TYPE 9250

//------------------------------------------------------------------------------------
#define I2C_SDA 21
#define I2C_SCL 22
#define JOY_X 34
#define JOY_Y 35
#define JOY_SW 25
#define SENSOR_ADDRESS 0x68

#if PLAYER_ID != 1 && PLAYER_ID != 2
#error PLAYER_ID must be 1 or 2
#endif

// Sampling and gesture tuning. Look at Serial Monitor before adjusting.
static const uint32_t SAMPLE_MS = 20;                 // 50 Hz
static const float SHAKE_ACCEL_THRESHOLD = 4.5f;     // m/s^2 change in norm
static const float SHAKE_RELEASE_THRESHOLD = 2.2f;
static const uint32_t SHAKE_WINDOW_MS = 600;
static const uint32_t PEAK_GAP_MS = 90;
static const uint32_t SHAKE_COOLDOWN_MS = 750;
static const float FLICK_DELTA_THRESHOLD = 8.0f;     // m/s^2 from calibrated rest
static const float FLICK_RESET_THRESHOLD = 3.2f;
static const uint32_t FLICK_COOLDOWN_MS = 850;
static const uint32_t AFTER_FLICK_SHAKE_BLOCK_MS = 300;
static const float TILT_ENTER_DEGREES = 26.0f;
static const float TILT_EXIT_DEGREES = 16.0f;
static const int JOY_ENTER = 850;
static const int JOY_EXIT = 620;
static const uint32_t BUTTON_DEBOUNCE_MS = 40;
static const uint32_t AD_EVENT_MS = 240;
static const uint32_t AD_IDLE_REFRESH_MS = 1400;
static const uint32_t DEBUG_RAW_INTERVAL_MS = 0;    // 0=no raw logs; 500=every 0.5 sec

// Upward direction depends on board installation and grip.
// 0 means sensor X, 1 sensor Y, 2 sensor Z. Change SIGN if upside-down.
static const int FLICK_AXIS = 1;
static const int FLICK_SIGN = 1;

static BLEAdvertising* bleAdvertising = nullptr;
struct Message { char action; uint8_t seq; };
static Message messages[32];
static uint8_t queueHead=0, queueTail=0, queueCount=0, sequenceNumber=0;
static Message advertised = {'I', 0};
static uint32_t advertisementStarted = 0, idleRefreshed = 0;

static int joyCenterX=2048, joyCenterY=2048;
static float neutralRoll=0, flickRest=0;
static char tiltState='C', joystickState='Z';
static bool rawButton=HIGH, stableButton=HIGH;
static uint32_t buttonRawChanged=0;
static uint32_t sampledAt=0, lastShake=0, lastFlick=0, peakAt=0, shakeStart=0;
static uint32_t rawLoggedAt=0, sensorErrors=0;
static bool shakeAbove=false, flickAbove=false;
static uint8_t shakePeaks=0;
static bool sensorOK=false;

struct Motion {
  float ax,ay,az;          // acceleration in m/s^2
  float gx,gy,gz;          // gyro rad/s (diagnostics / future use)
};

// Raw I2C registers compatible with the MPU6050 register map.
static bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(SENSOR_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static bool readRegisters(uint8_t reg, uint8_t* buf, uint8_t len) {
  Wire.beginTransmission(SENSOR_ADDRESS);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)SENSOR_ADDRESS, len) != len) return false;
  for (uint8_t i=0;i<len;i++) buf[i] = Wire.read();
  return true;
}

static int16_t signed16(const uint8_t* b) {
  return (int16_t)((uint16_t(b[0]) << 8) | uint16_t(b[1]));
}

static bool readMotion(Motion& m) {
  uint8_t data[14];
  // ACCEL_XOUT_H..GYRO_ZOUT_L, includes two temperature bytes.
  if (!readRegisters(0x3B, data, sizeof(data))) return false;
  // Select ±2g (16384 LSB/g), ±250 dps (131 LSB/dps).
  constexpr float ACCEL_SCALE = 9.80665f / 16384.0f;
  constexpr float GYRO_SCALE = (PI / 180.0f) / 131.0f;
  m.ax = signed16(data+0)*ACCEL_SCALE;
  m.ay = signed16(data+2)*ACCEL_SCALE;
  m.az = signed16(data+4)*ACCEL_SCALE;
  m.gx = signed16(data+8)*GYRO_SCALE;
  m.gy = signed16(data+10)*GYRO_SCALE;
  m.gz = signed16(data+12)*GYRO_SCALE;
  return true;
}

static float flickAxis(const Motion& m) {
  return FLICK_AXIS == 0 ? m.ax : (FLICK_AXIS == 2 ? m.az : m.ay);
}

static bool startSensor() {
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000); // conservative: better clone compatibility
  // Wake, choose clock, select known measurement ranges and filtering.
  if (!writeRegister(0x6B, 0x00)) return false; // PWR_MGMT_1: wake
  delay(80);
  if (!writeRegister(0x1C, 0x00)) return false; // ACCEL_CONFIG ±2g
  if (!writeRegister(0x1B, 0x00)) return false; // GYRO_CONFIG ±250 dps
  if (!writeRegister(0x1A, 0x03)) return false; // DLPF_CFG ~44 Hz (MPU6050)
  uint8_t id=0;
  if (readRegisters(0x75,&id,1)) Serial.printf("WHO_AM_I=0x%02X (diagnostic only)\n",id);
  Motion probe;
  return readMotion(probe);
}

static void broadcast(const Message& m) {
  const char raw[7] = {(char)0xFF,(char)0xFF,'A','L',
    (char)('0'+PLAYER_ID),m.action,(char)m.seq};
  BLEAdvertisementData payload;
  payload.setFlags(0x06);
  payload.setManufacturerData(String(raw, sizeof(raw))); // preserves zero bytes
  bleAdvertising->stop();
  bleAdvertising->setAdvertisementData(payload);
  bleAdvertising->start();
  advertised=m;
  advertisementStarted=millis();
  if (m.action=='I') idleRefreshed=advertisementStarted;
}

static void sendEvent(char action) {
  if (queueCount == 32) {
    Serial.printf("WARNING: event queue full, missed %c\n", action);
    return;
  }
  Message next={action,(uint8_t)(++sequenceNumber)};
  messages[queueTail]=next;
  queueTail=(queueTail+1)%32;
  queueCount++;
  Serial.printf("P%d action=%c seq=%u\n",PLAYER_ID,action,next.seq);
}

static void serviceBLE() {
  uint32_t now=millis();
  if ((uint32_t)(now-advertisementStarted) < AD_EVENT_MS) return;
  if (queueCount) {
    Message next=messages[queueHead];
    queueHead=(queueHead+1)%32;
    queueCount--;
    broadcast(next);
  } else if (advertised.action!='I' ||
             (uint32_t)(now-idleRefreshed) >= AD_IDLE_REFRESH_MS) {
    broadcast({'I',sequenceNumber});
  }
}

static bool calibrate() {
  Serial.println("CALIBRATE: keep remote STILL and joystick CENTERED...");
  int64_t sumX=0, sumY=0;
  float sumRoll=0, sumFlick=0;
  const int n=80;
  for (int i=0;i<n;i++) {
    Motion m;
    if (!readMotion(m)) return false;
    sumX += analogRead(JOY_X);
    sumY += analogRead(JOY_Y);
    sumRoll += atan2f(m.ax,m.az)*180.0f/PI;
    sumFlick += flickAxis(m);
    delay(15);
  }
  joyCenterX=sumX/n;
  joyCenterY=sumY/n;
  neutralRoll=sumRoll/n;
  flickRest=sumFlick/n;
  Serial.printf("CAL OK: joystick=(%d,%d) roll=%.1f flickRest=%.2f\n",
    joyCenterX,joyCenterY,neutralRoll,flickRest);
  return true;
}

static void sampleMotion() {
  Motion m;
  if (!readMotion(m)) {
    sensorErrors++;
    if (sensorErrors == 1 || sensorErrors % 100 == 0)
      Serial.printf("WARNING: sensor read failures=%lu\n", (unsigned long)sensorErrors);
    return;
  }
  const uint32_t now=millis();
  const float mag=sqrtf(m.ax*m.ax+m.ay*m.ay+m.az*m.az);
  const float change=fabsf(mag-9.80665f);

  // Detect an upward burst ABOVE the startup resting acceleration.
  const float impulse=(flickAxis(m)-flickRest)*FLICK_SIGN;
  if (impulse < FLICK_RESET_THRESHOLD) flickAbove=false;
  if (!flickAbove && impulse > FLICK_DELTA_THRESHOLD &&
      (uint32_t)(now-lastFlick) >= FLICK_COOLDOWN_MS) {
    sendEvent('F');
    lastFlick=now;
    flickAbove=true;
    shakePeaks=0;
    shakeAbove=true; // avoid using this initial impulse as a shake peak
  }

  // Shake = two peaks in the time window, with separation and cooldown.
  if (change < SHAKE_RELEASE_THRESHOLD) shakeAbove=false;
  if (change > SHAKE_ACCEL_THRESHOLD && !shakeAbove &&
      (uint32_t)(now-lastFlick) > AFTER_FLICK_SHAKE_BLOCK_MS &&
      (uint32_t)(now-peakAt) >= PEAK_GAP_MS) {
    shakeAbove=true;
    if (shakePeaks==0 || (uint32_t)(now-shakeStart)>SHAKE_WINDOW_MS) {
      shakePeaks=0;
      shakeStart=now;
    }
    shakePeaks++;
    peakAt=now;
    if (shakePeaks>=2 && (uint32_t)(now-lastShake)>=SHAKE_COOLDOWN_MS) {
      sendEvent('S');
      lastShake=now;
      shakePeaks=0;
    }
  }
  if (shakePeaks && (uint32_t)(now-shakeStart)>SHAKE_WINDOW_MS) shakePeaks=0;

  // Relative roll; only reliable while not accelerating rapidly.
  if (change < 2.0f) {
    float roll=atan2f(m.ax,m.az)*180.0f/PI-neutralRoll;
    // Normalize wraparound to [-180,+180].
    while (roll>180) roll-=360;
    while (roll< -180) roll+=360;
    char newTilt=tiltState;
    if (tiltState=='L') { if (roll > -TILT_EXIT_DEGREES) newTilt='C'; }
    else if (tiltState=='R') { if (roll < TILT_EXIT_DEGREES) newTilt='C'; }
    else {
      if (roll < -TILT_ENTER_DEGREES) newTilt='L';
      else if (roll > TILT_ENTER_DEGREES) newTilt='R';
    }
    if (newTilt!=tiltState) { tiltState=newTilt; sendEvent(tiltState); }
  }

  if (DEBUG_RAW_INTERVAL_MS &&
      (uint32_t)(now-rawLoggedAt)>=DEBUG_RAW_INTERVAL_MS) {
    rawLoggedAt=now;
    Serial.printf("RAW ax=%.2f ay=%.2f az=%.2f delta=%.2f flick=%.2f gyro=%.2f,%.2f,%.2f\n",
      m.ax,m.ay,m.az,change,impulse,m.gx,m.gy,m.gz);
  }
}

static void sampleJoystick() {
  int x=analogRead(JOY_X)-joyCenterX;
  int y=analogRead(JOY_Y)-joyCenterY;
  char direction='Z';
  if (joystickState=='J' && x < -JOY_EXIT) direction='J';
  else if (joystickState=='K' && x > JOY_EXIT) direction='K';
  else if (joystickState=='U' && y < -JOY_EXIT) direction='U';
  else if (joystickState=='D' && y > JOY_EXIT) direction='D';
  else if (x < -JOY_ENTER) direction='J';
  else if (x > JOY_ENTER) direction='K';
  else if (y < -JOY_ENTER) direction='U';
  else if (y > JOY_ENTER) direction='D';
  if (direction!=joystickState) { joystickState=direction; sendEvent(direction); }

  bool readButton=digitalRead(JOY_SW);
  uint32_t now=millis();
  if (readButton!=rawButton) { rawButton=readButton; buttonRawChanged=now; }
  if (readButton!=stableButton && (uint32_t)(now-buttonRawChanged)>=BUTTON_DEBOUNCE_MS) {
    stableButton=readButton;
    sendEvent(stableButton==LOW?'B':'b');
  }
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.printf("AstroLab DIRECT I2C Controller P%d starting...\n",PLAYER_ID);
  pinMode(JOY_SW,INPUT_PULLUP);
  analogReadResolution(12);
  sensorOK=startSensor();
  if (!sensorOK) {
    Serial.println("ERROR: 0x68 raw register setup/read failed. Check power and SDA21/SCL22.");
    // Keep running to permit joystick tests even without sensor.
  } else if (!calibrate()) {
    Serial.println("ERROR: calibration failed; motion events disabled.");
    sensorOK=false;
  }
  char name[24];
  snprintf(name,sizeof(name),"AstroLab-Remote-%d",PLAYER_ID);
  BLEDevice::init(name);
  bleAdvertising=BLEDevice::getAdvertising();
  broadcast({'I',sequenceNumber});
  Serial.println("BLE advertising enabled; 7-byte payload FF FF A L player action sequence.");
  Serial.println("Perform gestures; watch 'P1 action=X seq=N' logs.");
}

void loop() {
  uint32_t now=millis();
  if ((uint32_t)(now-sampledAt)>=SAMPLE_MS) {
    sampledAt=now;
    if (sensorOK) sampleMotion();
    sampleJoystick();
  }
  serviceBLE();
  delay(1);
}