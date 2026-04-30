# proctoring/video_proctoring.py

import os
import time

VIOLATION_FILE = "static/violation_status.txt"
CAPTURE_DIR = "static/captures"

os.makedirs(CAPTURE_DIR, exist_ok=True)

def log_violation(status):
    try:
        with open(VIOLATION_FILE, "w") as f:
            f.write(f"true|{status}|{int(time.time())}")
    except Exception as e:
        print("Error writing violation:", e)


def clear_violation():
    try:
        with open(VIOLATION_FILE, "w") as f:
            f.write(f"false|Normal|{int(time.time())}")
    except:
        pass


# 🔥 THIS replaces your heavy camera logic
def start_video_proctor():
    print("✅ Server-side proctoring started (light mode)")
    print("⚠️ Camera processing moved to frontend")

    # initialize file
    clear_violation()