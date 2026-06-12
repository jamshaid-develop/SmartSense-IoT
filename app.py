"""
HuggingFace Spaces entry point.
HF Spaces runs app.py at the repo root — this file imports the dashboard app.
Set these Secrets in HF Spaces settings:
  GROQ_API_KEY
  ALERT_SENDER_EMAIL
  ALERT_SENDER_PASS
  ALERT_RECEIVER_EMAIL
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dashboard"))

from dashboard.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
