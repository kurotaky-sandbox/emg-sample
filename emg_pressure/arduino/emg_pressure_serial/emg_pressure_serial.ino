#include <MsTimer2.h>

void sensorRead() {
  interrupts();
  int emgValue = analogRead(0);      // A0: EMG
  int pressureValue = analogRead(1); // A1: FSR pressure sensor
  char buf[8];

  // emgValue, pressureValue are 0~1023
  // Python side converts: value * 3.3 / 1023.0 -> 0 ~ 3.3V
  sprintf(buf, "%03x%03x", emgValue, pressureValue);
  Serial.println(buf);
}

void setup() {
  analogReference(EXTERNAL);
  Serial.begin(115200);
  MsTimer2::set(1, sensorRead); // 1ms interval (1kHz)
  MsTimer2::start();
}

void loop() {
}
