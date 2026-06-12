/*
 * SmartSense IoT — ESP32 Sensor + MQTT Publisher
 * Sensors : DHT22 (Temp + Humidity) + BMP280 (Pressure)
 * Broker  : HiveMQ public broker (mqtt.eclipseprojects.io)
 *
 * Libraries (install via Arduino Library Manager):
 *   - DHT sensor library  (Adafruit)
 *   - Adafruit BMP280
 *   - PubSubClient        (Nick O'Leary)
 *   - ArduinoJson
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <ArduinoJson.h>

// ─── WiFi credentials ────────────────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ─── MQTT broker (HiveMQ public, free, no account needed) ────────────────────
const char* MQTT_BROKER   = "mqtt.eclipseprojects.io";
const int   MQTT_PORT     = 1883;
const char* MQTT_TOPIC    = "smartsense/sensors";          // publish topic
const char* MQTT_CLIENT   = "smartsense-esp32-001";        // unique client id

// ─── Pin config ───────────────────────────────────────────────────────────────
#define DHT_PIN  4
#define DHT_TYPE DHT22
#define LED_PIN  2   // onboard LED flashes on publish

// ─── Publish interval ─────────────────────────────────────────────────────────
const unsigned long INTERVAL_MS = 5000;   // every 5 seconds

// ─── Objects ──────────────────────────────────────────────────────────────────
DHT            dht(DHT_PIN, DHT_TYPE);
Adafruit_BMP280 bmp;
WiFiClient     wifiClient;
PubSubClient   mqttClient(wifiClient);

unsigned long lastPublish = 0;
int           readingId   = 0;

// ─── WiFi connect ─────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
}

// ─── MQTT connect ─────────────────────────────────────────────────────────────
void connectMQTT() {
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqttClient.connect(MQTT_CLIENT)) {
      Serial.println("connected.");
    } else {
      Serial.printf("failed (rc=%d), retrying in 5s\n", mqttClient.state());
      delay(5000);
    }
  }
}

// ─── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  dht.begin();

  if (!bmp.begin(0x76)) {   // try 0x77 if 0x76 fails
    Serial.println("BMP280 not found — using DHT22 only.");
  }

  connectWiFi();
  connectMQTT();
}

// ─── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastPublish >= INTERVAL_MS) {
    lastPublish = now;

    float temperature = dht.readTemperature();
    float humidity    = dht.readHumidity();
    float pressure    = bmp.readPressure() / 100.0F;   // hPa

    // Validate readings
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("DHT22 read failed — skipping.");
      return;
    }

    // Build JSON payload
    StaticJsonDocument<200> doc;
    doc["id"]          = ++readingId;
    doc["temperature"] = round(temperature * 10) / 10.0;
    doc["humidity"]    = round(humidity * 10) / 10.0;
    doc["pressure"]    = round(pressure * 10) / 10.0;
    doc["device"]      = MQTT_CLIENT;
    doc["ts"]          = millis();

    char payload[200];
    serializeJson(doc, payload);

    if (mqttClient.publish(MQTT_TOPIC, payload)) {
      Serial.printf("[%d] Published: %s\n", readingId, payload);
      digitalWrite(LED_PIN, HIGH);
      delay(100);
      digitalWrite(LED_PIN, LOW);
    } else {
      Serial.println("Publish failed.");
    }
  }
}
