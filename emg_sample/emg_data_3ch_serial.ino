#include <MsTimer2.h>

void emgRead() {
  interrupts();
  long milltime = millis();
  int value1 = analogRead(0);
  int value2 = analogRead(1);
  int value3 = analogRead(2);
  char buf[13];

  // value1~3 は 0~1023
  // valueはProcesing側で 3.3 をかけて、1023.0で割ることで 0 ~ 3.3V に変換
  sprintf(buf, "%03x%03x%03x", value1, value2, value3);
  Serial.println(buf);
}

void setup() {
  analogReference(EXTERNAL);
  Serial.begin(115200);
  MsTimer2::set(1, emgRead); // 1ms間隔で実行
  MsTimer2::start();
}

void loop() {
}
