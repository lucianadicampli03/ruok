/*
  RUOK — one ESP32 sketch.
  Reads every sensor, prints one JSON line, runs the ULN2003 stepper,
  buzzer, and status LED. Laptop sends commands on the same USB serial.

  Arduino IDE: Board = ESP32 Dev Module, 115200.
  Library Manager: "DHT sensor library" by Adafruit + "Adafruit Unified Sensor".
  Close Serial Monitor before running Python on the HP.
*/

#include <DHT.h>

// ---- pins (locked) ----
const int PIN_IN1 = 12;
const int PIN_IN2 = 14;
const int PIN_IN3 = 18;
const int PIN_IN4 = 19;
const int PIN_LED = 13;
const int PIN_OBSTACLE = 21;
const int PIN_VIBE = 22;
const int PIN_DHT = 23;
const int PIN_BUZZER = 25;
const int PIN_PIR = 27;
const int PIN_TOUCH = 32;
const int PIN_TRIG = 33;
const int PIN_LIGHT = 34;
const int PIN_ECHO = 35;
const int PIN_RAIN = 36;

// Many IR obstacle boards go LOW when something is in front.
const bool OBSTACLE_ACTIVE_LOW = true;

DHT dht(PIN_DHT, DHT11);

const int STEP_PINS[4] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
// 28BYJ-48 half-step sequence
const int HALF_STEP[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1},
};

enum DriveMode { DRIVE_STOP, DRIVE_APPROACH, DRIVE_FOLLOW, DRIVE_LEFT, DRIVE_RIGHT };
DriveMode drive = DRIVE_STOP;
int stepIndex = 0;
int stepDir = 1;
unsigned long lastStepMs = 0;
unsigned long lastJsonMs = 0;
unsigned long lastDhtMs = 0;
unsigned long lastBeepMs = 0;
unsigned long beepUntil = 0;
unsigned long turnUntil = 0;

float humidity = -1;
float tempC = -1;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);
  pinMode(PIN_IN3, OUTPUT);
  pinMode(PIN_IN4, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_OBSTACLE, INPUT_PULLUP);
  pinMode(PIN_VIBE, INPUT);
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_TOUCH, INPUT);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);
  coilOff();
  dht.begin();
}

void coilOff() {
  for (int i = 0; i < 4; i++) digitalWrite(STEP_PINS[i], LOW);
}

void applyStep() {
  for (int i = 0; i < 4; i++) {
    digitalWrite(STEP_PINS[i], HALF_STEP[stepIndex][i]);
  }
}

void stepOnce() {
  applyStep();
  stepIndex += stepDir;
  if (stepIndex > 7) stepIndex = 0;
  if (stepIndex < 0) stepIndex = 7;
}

int readUltrasonicCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 30000);
  if (us == 0) return -1;
  return (int)(us * 0.0343 / 2.0);
}

int obstacleBlocked() {
  int raw = digitalRead(PIN_OBSTACLE);
  if (OBSTACLE_ACTIVE_LOW) return raw == LOW ? 1 : 0;
  return raw == HIGH ? 1 : 0;
}

void beep(unsigned int ms) {
  beepUntil = millis() + ms;
  digitalWrite(PIN_BUZZER, HIGH);
}

void handleLine(String line) {
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) return;

  // Accept {"cmd":"stop"} or plain: stop
  if (line.indexOf("stop") >= 0 && line.indexOf("approach") < 0) {
    drive = DRIVE_STOP;
    coilOff();
    return;
  }
  if (line.indexOf("approach") >= 0) {
    drive = DRIVE_APPROACH;
    stepDir = 1;
    return;
  }
  if (line.indexOf("follow") >= 0) {
    drive = DRIVE_FOLLOW;
    stepDir = 1;
    return;
  }
  if (line.indexOf("left") >= 0) {
    drive = DRIVE_LEFT;
    stepDir = -1;
    turnUntil = millis() + 800;
    return;
  }
  if (line.indexOf("right") >= 0) {
    drive = DRIVE_RIGHT;
    stepDir = 1;
    turnUntil = millis() + 800;
    return;
  }
  if (line.indexOf("beep") >= 0) {
    beep(120);
    return;
  }
}

void readSerialCommands() {
  static String buf;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      handleLine(buf);
      buf = "";
    } else if (buf.length() < 120) {
      buf += c;
    }
  }
}

void loop() {
  readSerialCommands();
  unsigned long now = millis();

  if (now - lastDhtMs > 2500) {
    lastDhtMs = now;
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    if (!isnan(h)) humidity = h;
    if (!isnan(t)) tempC = t;
  }

  int pir = digitalRead(PIN_PIR);
  int vibe = digitalRead(PIN_VIBE);
  int touch = digitalRead(PIN_TOUCH);
  int blocked = obstacleBlocked();
  int usCm = readUltrasonicCm();
  int light = analogRead(PIN_LIGHT);
  int rain = analogRead(PIN_RAIN);

  // Local safety: never roll into a shin even if the laptop is quiet.
  if (blocked || (usCm > 0 && usCm < 25) || vibe) {
    if (drive != DRIVE_STOP) {
      drive = DRIVE_STOP;
      coilOff();
      beep(80);
    }
  }

  if (now >= beepUntil) digitalWrite(PIN_BUZZER, LOW);

  unsigned int stepDelay = (drive == DRIVE_FOLLOW) ? 4 : 2;
  bool turning = (drive == DRIVE_LEFT || drive == DRIVE_RIGHT);
  if (turning && now > turnUntil) {
    drive = DRIVE_STOP;
    coilOff();
  }

  if (drive != DRIVE_STOP && now - lastStepMs >= stepDelay) {
    lastStepMs = now;
    stepOnce();
  }

  bool talkingRange = (usCm >= 40 && usCm <= 160);
  digitalWrite(PIN_LED, (pir || drive != DRIVE_STOP || talkingRange) ? HIGH : LOW);

  if (now - lastJsonMs >= 200) {
    lastJsonMs = now;
    Serial.print("{\"pir\":");
    Serial.print(pir);
    Serial.print(",\"us_cm\":");
    Serial.print(usCm);
    Serial.print(",\"obstacle\":");
    Serial.print(blocked);
    Serial.print(",\"touch\":");
    Serial.print(touch);
    Serial.print(",\"light\":");
    Serial.print(light);
    Serial.print(",\"rain\":");
    Serial.print(rain);
    Serial.print(",\"humidity\":");
    Serial.print(humidity, 1);
    Serial.print(",\"temp_c\":");
    Serial.print(tempC, 1);
    Serial.print(",\"vibe\":");
    Serial.print(vibe);
    Serial.print(",\"drive\":\"");
    if (drive == DRIVE_APPROACH) Serial.print("approach");
    else if (drive == DRIVE_FOLLOW) Serial.print("follow");
    else if (drive == DRIVE_LEFT) Serial.print("left");
    else if (drive == DRIVE_RIGHT) Serial.print("right");
    else Serial.print("stop");
    Serial.println("\"}");
  }
}
