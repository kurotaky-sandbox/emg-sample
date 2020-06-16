#include <MsTimer2.h>

void emgRead() {
  interrupts();
  long time = millis();
  int value = analogRead(0);
  Serial.print(time);
  Serial.print(" ");
  Serial.print(value * 5.0 / 1023.0);
  Serial.print("\n");
  Serial.read();
}

void setup() {
  Serial.begin(115200);
  MsTimer2::set(10, emgRead); // 10ms間隔で実行
  MsTimer2::start();
}

void loop() {
}
