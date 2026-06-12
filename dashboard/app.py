import threading
from flask import Flask, render_template, jsonify, request
from ml.detector import readings, anomalies, process_reading

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/ingest", methods=["POST"])
def ingest():
    data = request.get_json()
    process_reading(data)
    return {"ok": True}

@app.route("/api/readings")
def api_readings():
    return jsonify(list(readings)[-100:])

@app.route("/api/anomalies")
def api_anomalies():
    return jsonify(list(anomalies)[-50:])

@app.route("/api/stats")
def api_stats():
    data = list(readings)
    if not data:
        return jsonify({"total":0,"anomalies":0,"rate":0,"latest":None,"status":"waiting"})
    latest = data[-1]
    return jsonify({
        "total":     len(data),
        "anomalies": len(anomalies),
        "rate":      round(len(anomalies)/max(len(data),1)*100,1),
        "latest":    latest,
        "status":    "anomaly" if latest.get("is_anomaly") else "normal",
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)