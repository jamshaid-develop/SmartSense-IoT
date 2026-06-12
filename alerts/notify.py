"""
SmartSense — Email Alert via smtplib (free, no third-party service)
Uses Gmail SMTP with App Password (2FA must be enabled on your Google account).
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ─── Config (set as environment variables for security) ───────────────────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SENDER_EMAIL  = os.getenv("ALERT_SENDER_EMAIL", "your_gmail@gmail.com")
SENDER_PASS   = os.getenv("ALERT_SENDER_PASS",  "your_app_password")   # Gmail App Password
RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER_EMAIL", "receiver@example.com")

# ─── Email sender ─────────────────────────────────────────────────────────────
def send_email_alert(reading: dict, groq_explanation: str):
    ts   = reading.get("timestamp", datetime.utcnow().isoformat())
    temp = reading.get("temperature", "N/A")
    hum  = reading.get("humidity",    "N/A")
    pres = reading.get("pressure",    "N/A")
    dev  = reading.get("device",      "esp32")

    subject = f"⚠ SmartSense Anomaly — {ts[:19]}"

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <h2 style="color:#c0392b">⚠ Anomaly Detected — SmartSense IoT</h2>
      <table border="1" cellpadding="8" style="border-collapse:collapse">
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Timestamp</td><td>{ts}</td></tr>
        <tr><td>Device</td><td>{dev}</td></tr>
        <tr><td>Temperature</td><td><b>{temp} °C</b></td></tr>
        <tr><td>Humidity</td><td><b>{hum} %</b></td></tr>
        <tr><td>Pressure</td><td><b>{pres} hPa</b></td></tr>
      </table>
      <h3>AI Analysis (Groq)</h3>
      <p style="background:#fff3cd;padding:12px;border-radius:6px">{groq_explanation}</p>
      <hr>
      <small>SmartSense IoT Monitoring System — Academic Project</small>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    print(f"[Alert] Email sent to {RECEIVER_EMAIL}")


# ─── Test standalone ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_reading = {
        "temperature": 65.3,
        "humidity": 12.1,
        "pressure": 980.5,
        "device": "smartsense-esp32-001",
        "timestamp": datetime.utcnow().isoformat(),
    }
    send_email_alert(test_reading, "Unusually high temperature detected — possible sensor fault or overheating. Check device placement and ventilation immediately.")
    print("Test email sent.")
