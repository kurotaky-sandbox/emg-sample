#include <ArduinoBLE.h>

BLEService emgService("19B10010-E8F2-537E-4F6C-D104768A1214");
BLEFloatCharacteristic emgACharacteristic("19B10011-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLEFloatCharacteristic emgBCharacteristic("19B10012-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLEFloatCharacteristic emgCCharacteristic("19B10013-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("BLE の初期化に失敗しました。");
    while (1);
  }

  BLE.setDeviceName("ArduinoNanoReservoirEMG");
  BLE.setLocalName("ArduinoNanoReservoirEMG");
  BLE.setAdvertisedService(emgService);

  emgService.addCharacteristic(emgACharacteristic);
  emgService.addCharacteristic(emgBCharacteristic);
  emgService.addCharacteristic(emgCCharacteristic);

  BLE.addService(emgService);

  emgACharacteristic.writeValue(0.0);
  emgBCharacteristic.writeValue(0.0);
  emgCCharacteristic.writeValue(0.0);

  BLE.advertise();
  Serial.println("Bluetooth Advertising...");
}

void loop() {
  BLE.poll();
  int value1 = analogRead(0);
  int value2 = analogRead(1);
  int value3 = analogRead(2);
  float x,y,z;

  x = (value1 * 3.3 / 1023.0);
  y = (value2 * 3.3 / 1023.0);
  z = (value3 * 3.3 / 1023.0);

  emgACharacteristic.writeValue(x);
  emgBCharacteristic.writeValue(y);
  emgCCharacteristic.writeValue(z);
  //Serial.println(x);
  //delay(1);
}

