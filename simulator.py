import requests, time, random

URL = "http://127.0.0.1:7860/api/ingest"
print("Simulator chalu hai... (Ctrl+C se band karo)")

i = 0
while True:          # ← hamesha chalta rahega
    temp = 65.0 if i % 50 == 0 and i != 0 else round(24 + random.uniform(-2,2), 1)
    data = {
        "id": i,
        "temperature": temp,
        "humidity": round(58 + random.uniform(-5,5), 1),
        "pressure": round(1013 + random.uniform(-3,3), 1),
        "device": "simulator"
    }
    requests.post(URL, json=data)
    print(f"Reading {i} bheja: Temp={temp}°C")
    i += 1
    time.sleep(2)