#include <Arduino.h>
#include <MathUtils.h>

int ledPin = 13;

void setup() { 
    Serial.begin(9600); 
    Serial.println("Ready for mischief!");
}

boolean ledState = 0;

String formatOnboardState() {
    return (ledState) ? "On" : "Off";
}

void toggleOnboard() {
    digitalWrite(ledPin, ledState);
    Serial.println("Changed LED to " + formatOnboardState());
    ledState = !ledState;
}

void loop() {

    toggleOnboard();

    // Example: use something from lib
    int secondsToDelay = add(1, 1) * 1000;
    delay(secondsToDelay);
}
