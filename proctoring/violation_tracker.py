violations = {
    "face": 0,
    "eye": 0,
    "audio": 0,
    "eye_tracking": 0
}

def log_violation(v_type):
    if v_type in violations:
        violations[v_type] += 1

def get_report():
    total = sum(violations.values())

    risk = "Low"
    if total >= 5:
        risk = "Medium"
    if total >= 10:
        risk = "High"

    return {
        "face": violations["face"],
        "eye": violations["eye"],
        "audio": violations["audio"],
        "eye_tracking": violations["eye_tracking"],
        "total": total,
        "risk": risk
    }