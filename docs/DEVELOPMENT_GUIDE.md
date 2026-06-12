# SmartSense IoT — Development Guide

## Architecture Overview

```
[ESP32 + DHT22]  →  MQTT (HiveMQ)  →  [Python Backend on HF Spaces]
                                              │
                                    ┌─────────┴──────────┐
                                [Isolation Forest]   [Groq API]
                                 Anomaly Detection   Alert Text
                                              │
                                    [Flask Dashboard]
                                    live charts + log
                                              │
                                       [Email Alert]
                                        smtplib
```

---

## Part 1 — Hardware Setup

### Components needed
| Component | Purpose | Cost |
|-----------|---------|------|
| ESP32 Dev Board | WiFi + compute | ~$4 |
| DHT22 sensor | Temp + Humidity | ~$2 |
| BMP280 module | Pressure (optional) | ~$2 |
| Breadboard | Wiring | ~$1 |
| Jumper wires | Connections | ~$1 |

### Wiring diagram (text)
```
ESP32 Pin  →  Component
──────────────────────────────────
3.3V       →  DHT22 Pin 1 (VCC)
GND        →  DHT22 Pin 4 (GND)
GPIO 4     →  DHT22 Pin 2 (DATA)
           →  10kΩ resistor between VCC and DATA

3.3V       →  BMP280 VCC
GND        →  BMP280 GND
GPIO 21    →  BMP280 SDA
GPIO 22    →  BMP280 SCL
```

---

## Part 2 — Arduino/ESP32 Setup

### Step 1 — Install Arduino IDE
Download from https://www.arduino.cc/en/software

### Step 2 — Add ESP32 board
1. Open Arduino IDE → File → Preferences
2. Add to "Additional Board URLs":
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Tools → Board Manager → search "esp32" → install **esp32 by Espressif**
4. Select: Tools → Board → ESP32 Arduino → **DOIT ESP32 DEVKIT V1**

### Step 3 — Install Libraries
Open Library Manager (Ctrl+Shift+I) and install:
- `DHT sensor library` by Adafruit
- `Adafruit BMP280 Library`
- `PubSubClient` by Nick O'Leary
- `ArduinoJson` by Benoit Blanchon

### Step 4 — Configure and upload
1. Open `esp32/sensor_mqtt.ino`
2. Edit lines 13–14: set your WiFi SSID and password
3. Connect ESP32 via USB
4. Select port: Tools → Port → COMx (Windows) or /dev/ttyUSBx (Linux)
5. Click Upload (→)
6. Open Serial Monitor at 115200 baud to see output

### Expected Serial output
```
Connecting to WiFi....
WiFi connected. IP: 192.168.1.45
Connecting to MQTT...connected.
[1] Published: {"id":1,"temperature":24.5,"humidity":58.2,"pressure":1013.2,...}
[2] Published: {"id":2,"temperature":24.6,"humidity":58.0,"pressure":1013.1,...}
```

---

## Part 3 — Python Backend Setup (local testing)

### Step 1 — Install dependencies
```bash
pip install flask paho-mqtt scikit-learn numpy groq
```

### Step 2 — Get Groq API key (free)
1. Sign up at https://console.groq.com
2. Create API key → copy it
3. Set environment variable:
   ```bash
   # Linux/Mac
   export GROQ_API_KEY="gsk_your_key_here"
   # Windows
   set GROQ_API_KEY=gsk_your_key_here
   ```

### Step 3 — Configure email alerts
1. Enable 2-Factor Authentication on your Gmail account
2. Go to https://myaccount.google.com/apppasswords
3. Create an App Password for "Mail"
4. Set environment variables:
   ```bash
   export ALERT_SENDER_EMAIL="your_gmail@gmail.com"
   export ALERT_SENDER_PASS="xxxx xxxx xxxx xxxx"   # 16-char app password
   export ALERT_RECEIVER_EMAIL="your_email@example.com"
   ```

### Step 4 — Run dashboard locally
```bash
cd SmartSense
python app.py
```
Open http://localhost:7860 in browser.

### Step 5 — Test without hardware
Run this in a separate terminal to simulate ESP32 sensor data:
```python
import paho.mqtt.client as mqtt
import json, time, random

client = mqtt.Client("test-simulator")
client.connect("mqtt.eclipseprojects.io", 1883)

for i in range(100):
    # Inject anomaly at reading 50
    temp = 65.0 if i == 50 else round(24 + random.uniform(-2, 2), 1)
    payload = {
        "id": i, "temperature": temp,
        "humidity": round(58 + random.uniform(-5, 5), 1),
        "pressure": round(1013 + random.uniform(-3, 3), 1),
        "device": "simulator"
    }
    client.publish("smartsense/sensors", json.dumps(payload))
    print(f"Sent: {payload}")
    time.sleep(2)
```

---

## Part 4 — Deploy to HuggingFace Spaces (free, always-on)

### Step 1 — Create HF Space
1. Go to https://huggingface.co → Sign up (free)
2. Click "New Space"
3. Settings:
   - Space name: `smartsense-iot`
   - SDK: **Gradio** (select this, then we override with Flask)
   - Hardware: **Free CPU**

### Step 2 — Set Secrets
In your Space → Settings → Repository secrets, add:
```
GROQ_API_KEY          = gsk_your_key_here
ALERT_SENDER_EMAIL    = your_gmail@gmail.com
ALERT_SENDER_PASS     = your_app_password
ALERT_RECEIVER_EMAIL  = receiver@example.com
```

### Step 3 — Upload files
Option A (Git):
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/smartsense-iot
cp -r SmartSense/* smartsense-iot/
cd smartsense-iot
git add . && git commit -m "Initial deploy" && git push
```

Option B (Web UI): drag and drop all files in the Files tab.

### Step 4 — Verify deployment
- HF Spaces builds automatically (watch the logs)
- Your dashboard is live at: `https://YOUR_USERNAME-smartsense-iot.hf.space`
- No expiry — free tier runs indefinitely

---

## Part 5 — How the ML Model Works

### Isolation Forest (anomaly detection)
- Trains on the first **20 readings** (warmup period)
- Retrains every **20 new readings** to adapt to baseline drift
- `contamination=0.05` means it expects ~5% of readings to be anomalies
- Returns `-1` for anomaly, `1` for normal

### What triggers an anomaly
Examples that Isolation Forest will catch:
- Temperature spike: 25°C → 65°C
- Humidity drop: 60% → 5% (sensor disconnected)
- Pressure anomaly: 1013 hPa → 950 hPa (weather event)
- Combined drift: multiple metrics slightly off simultaneously

### Groq alert explanation
When an anomaly is detected, the raw readings are sent to Groq's `llama3-8b-8192` model with a short prompt. The model returns a 2-sentence explanation:
1. Likely cause of the anomaly
2. Recommended action

This explanation appears in the dashboard anomaly log and the email alert.

---

## Part 6 — Project File Reference

```
SmartSense/
├── app.py                      HuggingFace Spaces entry point
├── requirements.txt            Python dependencies
├── esp32/
│   └── sensor_mqtt.ino         ESP32 Arduino code (upload this)
├── ml/
│   ├── __init__.py
│   └── detector.py             MQTT subscriber + Isolation Forest + Groq
├── dashboard/
│   ├── app.py                  Flask routes + API endpoints
│   └── templates/
│       └── index.html          Live Plotly dashboard UI
└── alerts/
    ├── __init__.py
    └── notify.py               smtplib email alert
```

---

## Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| DHT22 reads NaN | Check 10kΩ pull-up resistor on DATA pin |
| BMP280 not found | Try I2C address 0x77 instead of 0x76 |
| MQTT not connecting | Check firewall; try port 8883 (TLS) |
| No data in dashboard | Confirm MQTT_TOPIC matches in .ino and detector.py |
| Groq API error | Verify GROQ_API_KEY env variable is set |
| Email not sending | Use Gmail App Password, not your regular Gmail password |
| HF Space crashes | Check build logs; ensure requirements.txt is complete |

---

## Academic Submission Tips

- Screenshot the Serial Monitor output showing live MQTT publishes
- Screenshot the dashboard showing live charts + one detected anomaly
- Screenshot the anomaly email received in your inbox
- In your report: explain Isolation Forest with a simple diagram (training → predict → alert)
- Mention that Groq provides explainable AI alerts — this is a bonus feature

---

*SmartSense IoT — Academic Project | Free Stack: ESP32 + HiveMQ + HuggingFace + Groq*
