VIOLATION_FILE = "static/violation_status.txt"

def log_violation(status):
    with open(VIOLATION_FILE, "w") as f:
        f.write(f"true|{status}")

def clear_violation():
    with open(VIOLATION_FILE, "w") as f:
        f.write("false|Normal")