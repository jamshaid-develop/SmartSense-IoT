import requests, time, random

URL = "https://jamshaid-3990-smartsense-iot.hf.space/api/ingest"

print("Permanent simulator chalu hai...")
reading_id = 0
while True:
    reading_id += 1
    temp = 65.0 if reading_id % 100 == 0 else round(24 + random.uniform(-2,2), 1)
    data = {
        "id": reading_id,
        "temperature": temp,
        "humidity": round(58 + random.uniform(-5,5), 1),
        "pressure": round(1013 + random.uniform(-3,3), 1),
        "device": "smartsense-esp32"
    }
    try:
        requests.post(URL, json=data, timeout=10)
        print(f"Reading {reading_id} bheja: Temp={temp}°C")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(5)