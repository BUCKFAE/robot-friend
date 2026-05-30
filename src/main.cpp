#include <Arduino.h>
#include <MathUtils.h>

int ledPin = 13;

void setup() { Serial.begin(9600); }

void loop() {
  Serial.println(add(2, 3));

  digitalWrite(ledPin, HIGH);
  delay(5000);
  Serial.println("LOW");
  digitalWrite(ledPin, LOW);
  delay(100);
}
