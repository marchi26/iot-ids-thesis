#include <Arduino.h>

#include "embedded_model.h"

constexpr int ATTACK_LED_PIN = 25;
constexpr int NORMAL_LED_PIN = 26;

void printFeatures(const float features[IDS_FEATURE_COUNT]) {
  for (int i = 0; i < IDS_FEATURE_COUNT; i++) {
    Serial.print(IDS_FEATURE_NAMES[i]);
    Serial.print("=");
    Serial.print(features[i], 3);
    if (i < IDS_FEATURE_COUNT - 1) {
      Serial.print(", ");
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(ATTACK_LED_PIN, OUTPUT);
  pinMode(NORMAL_LED_PIN, OUTPUT);

  Serial.println();
  Serial.println("================================");
  Serial.println("IoT IDS embedded inference demo");
  Serial.println("Model: quantized binary Logistic Regression");
  Serial.print("Feature count: ");
  Serial.println(IDS_FEATURE_COUNT);
  Serial.print("Sample count: ");
  Serial.println(IDS_SAMPLE_COUNT);
  Serial.print("Export accuracy: ");
  Serial.println(IDS_EXPORT_ACCURACY, 6);
  Serial.print("Export macro F1: ");
  Serial.println(IDS_EXPORT_MACRO_F1, 6);
  Serial.println("Format: sample,expected,predicted,attack_probability");
  Serial.println("================================");
}

void loop() {
  static int sampleIndex = 0;
  const float *features = IDS_TEST_SAMPLES[sampleIndex];
  int expected = IDS_TEST_LABELS[sampleIndex];
  float probability = idsPredictProbability(features);
  int predicted = probability >= IDS_THRESHOLD ? 1 : 0;

  digitalWrite(ATTACK_LED_PIN, predicted == 1 ? HIGH : LOW);
  digitalWrite(NORMAL_LED_PIN, predicted == 0 ? HIGH : LOW);

  Serial.print("sample=");
  Serial.print(sampleIndex);
  Serial.print(" expected=");
  Serial.print(expected == 1 ? "attack" : "normal");
  Serial.print(" predicted=");
  Serial.print(predicted == 1 ? "attack" : "normal");
  Serial.print(" attack_probability=");
  Serial.print(probability, 6);
  Serial.print(" | ");
  printFeatures(features);
  Serial.println();

  Serial.print("plot_probability:");
  Serial.print(probability, 6);
  Serial.print(",plot_predicted:");
  Serial.println(predicted);

  sampleIndex = (sampleIndex + 1) % IDS_SAMPLE_COUNT;
  delay(2000);
}
