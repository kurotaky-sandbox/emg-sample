#include <MsTimer2.h>

void emgRead() {
  interrupts();
  long time = millis();
  int value = analogRead(0);
  int value2 = analogRead(1);
  Serial.print(time);
  Serial.print(" ");
  Serial.print(value * 3.3 / 1023.0);
  Serial.print(" ");
  Serial.print(value2 * 3.3 / 1023.0);
  Serial.print("\n");
  Serial.read();
}

void setup() {
  analogReference(EXTERNAL);
  Serial.begin(115200);
  MsTimer2::set(1, emgRead); // 1ms間隔で実行
  MsTimer2::start();
}

void loop() {
}
