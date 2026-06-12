"""
SmartSense — ML Anomaly Detector
Subscribes to MQTT, runs Isolation Forest, calls Groq for alert explanation.
"""

import json
import time
import threading
import os
from datetime import datetime
from collections import deque

import numpy as np
import paho.mqtt.client as mqtt
from sklearn.ensemble import IsolationForest
from groq import Groq

# ─── Config ──────────────────────────────────────────────────────────────────
MQTT_BROKER   = "mqtt.eclipseprojects.io"
MQTT_PORT     = 1883
MQTT_TOPIC    = "smartsense/sensors"
# Yeh hona chahiye — key nahi, sirf empty string
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = "llama-3.3-70b-versatile"

# Minimum readings before model starts predicting
WARMUP_COUNT  = 20
# Isolation Forest contamination (expected anomaly fraction)
CONTAMINATION = 0.05

# ─── Shared state (thread-safe via deque + list) ──────────────────────────────
readings       = deque(maxlen=500)   # raw dicts
feature_buffer = deque(maxlen=500)   # [temp, humidity, pressure] rows
anomalies      = []                  # detected anomaly dicts
model          = None
model_lock     = threading.Lock()

groq_client    = Groq(api_key=GROQ_API_KEY)

# ─── Groq alert explanation ───────────────────────────────────────────────────
def get_groq_explanation(reading: dict) -> str:
    prompt = (
        f"You are an IoT monitoring assistant. A sensor anomaly was detected.\n"
        f"Reading: Temperature={reading['temperature']}°C, "
        f"Humidity={reading['humidity']}%, Pressure={reading['pressure']} hPa.\n"
        f"In 2 short sentences: (1) what likely caused this anomaly, "
        f"(2) what action to take."
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq unavailable: {e}"

# ─── Model training / retraining ─────────────────────────────────────────────
def train_model():
    global model
    if len(feature_buffer) < WARMUP_COUNT:
        return
    X = np.array(list(feature_buffer))
    new_model = IsolationForest(
        n_estimators=100,
        contamination=CONTAMINATION,
        random_state=42,
    )
    new_model.fit(X)
    with model_lock:
        model = new_model
    print(f"[ML] Model trained on {len(X)} samples.")

# ─── Predict single reading ───────────────────────────────────────────────────
def predict(reading: dict) -> bool:
    """Returns True if anomaly detected."""
    with model_lock:
        if model is None:
            return False
    x = np.array([[reading["temperature"], reading["humidity"], reading["pressure"]]])
    pred = model.predict(x)   # -1 = anomaly, 1 = normal
    return int(pred[0]) == -1

# ─── MQTT callbacks ───────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected. Subscribed to {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT] Connection failed rc={rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        return

    # Ensure required fields exist
    required = {"temperature", "humidity", "pressure"}
    if not required.issubset(data):
        return

    data["timestamp"] = datetime.utcnow().isoformat()
    data["is_anomaly"] = False

    readings.append(data)
    feature_buffer.append([data["temperature"], data["humidity"], data["pressure"]])

    # Retrain every 20 new readings
    if len(feature_buffer) % 20 == 0:
        threading.Thread(target=train_model, daemon=True).start()

    # Predict
    if predict(data):
        data["is_anomaly"] = True
        explanation = get_groq_explanation(data)
        data["alert_message"] = explanation
        anomalies.append(data)

        print(f"\n⚠  ANOMALY DETECTED at {data['timestamp']}")
        print(f"   Temp={data['temperature']}°C  Hum={data['humidity']}%  "
              f"Press={data['pressure']} hPa")
        print(f"   Groq: {explanation}\n")

        # Trigger email alert (imported from alerts module)
        try:
            from alerts.notify import send_email_alert
            send_email_alert(data, explanation)
        except Exception as e:
            print(f"[Alert] Email failed: {e}")
    else:
        print(f"[OK] T={data['temperature']}°C  H={data['humidity']}%  "
              f"P={data['pressure']} hPa  "
              f"(buffer={len(feature_buffer)}, model={'ready' if model else 'warming up'})")

# ─── Main ─────────────────────────────────────────────────────────────────────
def start_detector():
    client = mqtt.Client(client_id="smartsense-detector")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    print("[SmartSense] Detector started. Waiting for sensor data...")
    client.loop_forever()
def process_reading(data: dict):
    """Direct HTTP se reading process karo (no MQTT)."""
    from datetime import datetime
    data["timestamp"] = datetime.utcnow().isoformat()
    data["is_anomaly"] = False
    readings.append(data)
    feature_buffer.append([data["temperature"], data["humidity"], data["pressure"]])
    
    if len(feature_buffer) % 20 == 0:
        threading.Thread(target=train_model, daemon=True).start()
    
    if predict(data):
        data["is_anomaly"] = True
        explanation = get_groq_explanation(data)
        data["alert_message"] = explanation
        anomalies.append(data)
        print(f"⚠ ANOMALY: Temp={data['temperature']}°C — {explanation}")
    else:
        print(f"[OK] Reading {data.get('id')} — Temp={data['temperature']}°C")
if __name__ == "__main__":
    start_detector()
