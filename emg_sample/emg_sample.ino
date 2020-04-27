#include <MsTimer2.h>

void emgRead() {
  interrupts();
  long time = micros();
  int value = analogRead(0);
  Serial.print(time);
  Serial.print(" ");
  Serial.print(value);
  Serial.print("\n");
  Serial.read();
}

void setup() {
  Serial.begin(9600);
  MsTimer2::set(100, emgRead); // 100ms間隔で実行
  MsTimer2::start();
}

void loop() {
}
