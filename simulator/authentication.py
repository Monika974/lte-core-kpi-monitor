"""HSS-side checks: authentication and subscriber (profile) validation."""


def authenticate(sub):
    """Step 2 - Authentication (AKA vectors). Fails for unknown IMSI."""
    if sub is None:
        return False, "Unknown IMSI - no authentication vectors in HSS"
    return True, "Authentication vectors OK"


def validate_subscriber(sub, rat="4G"):
    """Step 3 - Subscriber validation (Update Location / profile check)."""
    if sub["status"] == "Blocked":
        return False, "Subscriber barred (Blocked)"
    if sub["status"] != "Active":
        return False, f"Subscriber not active ({sub['status']})"
    if sub["plan"] != rat:
        return False, f"RAT not allowed (plan {sub['plan']}, attaching on {rat})"
    return True, "Subscriber profile valid"
