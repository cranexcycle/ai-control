#include <Arduino.h>

#define ENC_A PA0
#define ENC_B PA1

#define ENC2_A PB6
#define ENC2_B PB7

#define LIMIT1 PB0
#define LIMIT2 PB1

#define PHOTO1  PB12
#define PHOTO2  PA4
#define PHOTO3  PA6
#define PHOTO4  PA7

#define MAG1 PB10
#define MAG2 PB9
#define VALVE_UP PA5
#define VALVE_DOWN PB11
#define VALVE_BRAKE1 PB13
#define VALVE_BRAKE2 PB8
#define DIR_VALVE PA2

#define ENC_SCALE 10

volatile int32_t encoderCount = 0;
volatile int32_t encoder2Count = 0;

int32_t lastSent = 0;
int32_t lastSent2 = 0;

unsigned long lastTime = 0;

volatile unsigned long lastInterruptTime = 0;
volatile unsigned long lastInterruptTime2 = 0;

bool systemEnable = false;
bool systemArmed = false;

int lastLS1 = -1, lastLS2 = -1;
int lastP1 = -1, lastP2 = -1, lastP3 = -1, lastP4 = -1;
int32_t lastDebugE1 = 0, lastDebugE2 = 0;

int lastP1_sent = -1, lastP2_sent = -1;
int lastP3_sent = -1, lastP4_sent = -1;

// --- Photo raw debounce (fast, count-based) ---
int p1_raw = 0, p2_raw = 0, p3_raw = 0, p4_raw = 0;
int p1_count = 0, p2_count = 0, p3_count = 0, p4_count = 0;

// --- Photo confirmed output (slow, 2-second hold) ---
int p1_confirmed = 0, p2_confirmed = 0, p3_confirmed = 0, p4_confirmed = 0;

unsigned long p1_high_since = 0, p2_high_since = 0;
unsigned long p3_high_since = 0, p4_high_since = 0;
bool p1_timing = false, p2_timing = false;
bool p3_timing = false, p4_timing = false;

int ls1_raw = 0, ls2_raw = 0;
int ls1_count = 0, ls2_count = 0;

const int DEBOUNCE_COUNT = 3;
const unsigned long PHOTO_HOLD_MS = 2000;

void readEncoder() {
  unsigned long now = micros();
  if (now - lastInterruptTime > 2000) {
    if (digitalRead(ENC_A) == digitalRead(ENC_B)) encoderCount++;
    else encoderCount--;
    lastInterruptTime = now;
  }
}

void readEncoder2() {
  unsigned long now = micros();
  if (now - lastInterruptTime2 > 2000) {
    if (digitalRead(ENC2_A) == digitalRead(ENC2_B)) encoder2Count++;
    else encoder2Count--;
    lastInterruptTime2 = now;
  }
}

// อัปเดต confirmed output ของ photo sensor แต่ละตัว
// raw=1 ต้องค้างนาน 2 วินาที จึงจะ confirmed=1
// raw=0 → confirmed=0 ทันที
void updatePhotoConfirmed(int raw, int &confirmed, bool &timing,
                          unsigned long &high_since, int &last_sent,
                          const char *label) {
  unsigned long now = millis();
  if (raw == 1) {
    if (!timing) {
      timing = true;
      high_since = now;
    } else if ((now - high_since) >= PHOTO_HOLD_MS) {
      if (confirmed != 1) {
        confirmed = 1;
        if (confirmed != last_sent) {
          Serial.print(label);
          Serial.println(confirmed);
          last_sent = confirmed;
        }
      }
    }
  } else {
    timing = false;
    if (confirmed != 0) {
      confirmed = 0;
      if (confirmed != last_sent) {
        Serial.print(label);
        Serial.println(confirmed);
        last_sent = confirmed;
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  pinMode(ENC_A, INPUT_PULLUP);
  pinMode(ENC_B, INPUT_PULLUP);
  pinMode(ENC2_A, INPUT_PULLUP);
  pinMode(ENC2_B, INPUT_PULLUP);
  pinMode(LIMIT1, INPUT_PULLUP);
  pinMode(LIMIT2, INPUT_PULLUP);

  pinMode(PHOTO1, INPUT_PULLUP);
  pinMode(PHOTO2, INPUT_PULLUP);
  pinMode(PHOTO3, INPUT_PULLUP);
  pinMode(PHOTO4, INPUT_PULLUP);

  pinMode(MAG1, OUTPUT);
  pinMode(MAG2, OUTPUT);
  pinMode(VALVE_UP, OUTPUT);
  pinMode(VALVE_DOWN, OUTPUT);
  pinMode(VALVE_BRAKE1, OUTPUT);
  pinMode(VALVE_BRAKE2, OUTPUT);
  pinMode(DIR_VALVE, OUTPUT);

  digitalWrite(MAG1, HIGH);
  digitalWrite(MAG2, HIGH);
  digitalWrite(VALVE_UP, HIGH);
  digitalWrite(VALVE_DOWN, HIGH);
  digitalWrite(VALVE_BRAKE1, HIGH);
  digitalWrite(VALVE_BRAKE2, HIGH);
  digitalWrite(DIR_VALVE, HIGH);

  attachInterrupt(digitalPinToInterrupt(ENC_A), readEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC2_A), readEncoder2, CHANGE);

  Serial.println("READY");
}

void loop() {

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "ARM") {
      systemArmed = true;
      Serial.println("ARMED");
    }

    if (cmd == "DISARM") {
      systemArmed = false;
      systemEnable = false;
      digitalWrite(MAG1, HIGH);
      digitalWrite(MAG2, HIGH);
      digitalWrite(VALVE_UP, HIGH);
      digitalWrite(VALVE_DOWN, HIGH);
      digitalWrite(VALVE_BRAKE1, HIGH);
      digitalWrite(VALVE_BRAKE2, HIGH);
      digitalWrite(DIR_VALVE, HIGH);
      Serial.println("DISARMED");
    }

    if (cmd == "START") {
      if (systemArmed) {
        systemEnable = true;
        Serial.println("SYS:ON");
      } else {
        Serial.println("ERR:NOT_ARMED");
      }
    }

    if (cmd == "STOP") {
      systemEnable = false;
      digitalWrite(MAG1, HIGH);
      digitalWrite(MAG2, HIGH);
      digitalWrite(VALVE_UP, HIGH);
      digitalWrite(VALVE_DOWN, HIGH);
      digitalWrite(VALVE_BRAKE1, HIGH);
      digitalWrite(VALVE_BRAKE2, HIGH);
      digitalWrite(DIR_VALVE, HIGH);
      Serial.println("SYS:OFF");
    }

    if (systemEnable && systemArmed) {
      if (cmd == "MAG1_ON")  digitalWrite(MAG1, LOW);
      if (cmd == "MAG1_OFF") digitalWrite(MAG1, HIGH);
      if (cmd == "MAG2_ON")  digitalWrite(MAG2, LOW);
      if (cmd == "MAG2_OFF") digitalWrite(MAG2, HIGH);
      if (cmd == "UP_ON")    digitalWrite(VALVE_UP, LOW);
      if (cmd == "UP_OFF")   digitalWrite(VALVE_UP, HIGH);
      if (cmd == "DOWN_ON")  digitalWrite(VALVE_DOWN, LOW);
      if (cmd == "DOWN_OFF") digitalWrite(VALVE_DOWN, HIGH);
      if (cmd == "B1_ON")    digitalWrite(VALVE_BRAKE1, LOW);
      if (cmd == "B1_OFF")   digitalWrite(VALVE_BRAKE1, HIGH);
      if (cmd == "B2_ON")    digitalWrite(VALVE_BRAKE2, LOW);
      if (cmd == "B2_OFF")   digitalWrite(VALVE_BRAKE2, HIGH);
      if (cmd == "DIR_ON")   digitalWrite(DIR_VALVE, LOW);
      if (cmd == "DIR_OFF")  digitalWrite(DIR_VALVE, HIGH);
    }
  }

  if (millis() - lastTime >= 20) {

    // --- Limit switches (เหมือนเดิม) ---
    int rLS1 = digitalRead(LIMIT1) == LOW ? 1 : 0;
    int rLS2 = digitalRead(LIMIT2) == LOW ? 1 : 0;

    if (rLS1 != ls1_raw) {
      ls1_count++;
      if (ls1_count >= DEBOUNCE_COUNT) {
        ls1_raw = rLS1;
        ls1_count = 0;
        if (ls1_raw == 1) {
          encoderCount = 0;
          Serial.println("LS1:1");
        }
      }
    } else { ls1_count = 0; }

    if (rLS2 != ls2_raw) {
      ls2_count++;
      if (ls2_count >= DEBOUNCE_COUNT) {
        ls2_raw = rLS2;
        ls2_count = 0;
        if (ls2_raw == 1) {
          encoderCount = -1 * ENC_SCALE;
          Serial.println("LS2:1");
        }
      }
    } else { ls2_count = 0; }

    // --- Encoder (เหมือนเดิม) ---
    int32_t current = encoderCount / ENC_SCALE;
    if (current != lastSent) {
      Serial.print("E1:");
      Serial.println(current);
      lastSent = current;
    }

    int32_t current2 = encoder2Count / ENC_SCALE;
    if (current2 != lastSent2) {
      Serial.print("E2:");
      Serial.println(current2);
      lastSent2 = current2;
    }

    // --- Photo sensors: debounce เร็ว (count) → raw ---
    int r1 = digitalRead(PHOTO1) == LOW ? 1 : 0;
    int r2 = digitalRead(PHOTO2) == LOW ? 1 : 0;
    int r3 = digitalRead(PHOTO3) == LOW ? 1 : 0;
    int r4 = digitalRead(PHOTO4) == LOW ? 1 : 0;

    if (r1 != p1_raw) { p1_count++; if (p1_count >= DEBOUNCE_COUNT) { p1_raw = r1; p1_count = 0; } } else { p1_count = 0; }
    if (r2 != p2_raw) { p2_count++; if (p2_count >= DEBOUNCE_COUNT) { p2_raw = r2; p2_count = 0; } } else { p2_count = 0; }
    if (r3 != p3_raw) { p3_count++; if (p3_count >= DEBOUNCE_COUNT) { p3_raw = r3; p3_count = 0; } } else { p3_count = 0; }
    if (r4 != p4_raw) { p4_count++; if (p4_count >= DEBOUNCE_COUNT) { p4_raw = r4; p4_count = 0; } } else { p4_count = 0; }

    // --- Photo sensors: hold 2 วินาที → confirmed output ---
    updatePhotoConfirmed(p1_raw, p1_confirmed, p1_timing, p1_high_since, lastP1_sent, "P1:");
    updatePhotoConfirmed(p2_raw, p2_confirmed, p2_timing, p2_high_since, lastP2_sent, "P2:");
    updatePhotoConfirmed(p3_raw, p3_confirmed, p3_timing, p3_high_since, lastP3_sent, "P3:");
    updatePhotoConfirmed(p4_raw, p4_confirmed, p4_timing, p4_high_since, lastP4_sent, "P4:");

    // เพิ่มเงื่อนไขบังคับ: ถ้าสถานะ P4 confirmed เป็น 1 ให้ E2 เป็น 0 ตลอดเวลา
    if (p4_confirmed == 1) {
      encoder2Count = 0;
    }

    lastTime = millis();
  }

  int curLS1 = ls1_raw;
  int curLS2 = ls2_raw;
  int curP1  = p1_confirmed;
  int curP2  = p2_confirmed;
  int curP3  = p3_confirmed;
  int curP4  = p4_confirmed;

  int32_t displayE1 = encoderCount / ENC_SCALE;
  int32_t displayE2 = encoder2Count / ENC_SCALE;

  if (displayE1 != lastDebugE1 || displayE2 != lastDebugE2 ||
      curLS1 != lastLS1 || curLS2 != lastLS2 ||
      curP1 != lastP1   || curP2 != lastP2   ||
      curP3 != lastP3   || curP4 != lastP4) {

    Serial.print("DBG | E1:"); Serial.print(displayE1);
    Serial.print(" E2:");      Serial.print(displayE2);
    Serial.print(" | LS1:");   Serial.print(curLS1);
    Serial.print(" LS2:");     Serial.print(curLS2);
    Serial.print(" | P1:");    Serial.print(curP1);
    Serial.print(" P2:");      Serial.print(curP2);
    Serial.print(" P3:");      Serial.print(curP3);
    Serial.print(" P4:");      Serial.println(curP4);

    lastDebugE1 = displayE1;
    lastDebugE2 = displayE2;
    lastLS1 = curLS1; lastLS2 = curLS2;
    lastP1 = curP1;   lastP2 = curP2;
    lastP3 = curP3;   lastP4 = curP4;
  }
}
