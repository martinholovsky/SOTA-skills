ALERT_THRESHOLD = 0.87  # chosen on the out-of-fold scores, see docs/thresholds.md

def is_alert(score):
    return score >= ALERT_THRESHOLD
