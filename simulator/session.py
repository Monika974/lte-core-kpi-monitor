"""Simplified LTE attach procedure: UE -> MME -> HSS -> SGW -> PGW."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .authentication import authenticate, validate_subscriber

STEPS = ["Attach Request", "Authentication", "Subscriber Validation",
         "Session Creation", "IP Allocation"]


class IPPool:
    """Trivial PGW IP pool (10.45.0.2 onwards)."""
    def __init__(self, prefix="10.45.0."):
        self.prefix, self.n = prefix, 1

    def allocate(self):
        self.n += 1
        if self.n > 254:
            raise RuntimeError("IP pool exhausted")
        return f"{self.prefix}{self.n}"


@dataclass
class AttachResult:
    imsi: str
    attached: bool = False
    ip: str = None
    reason: str = ""
    steps: list = field(default_factory=list)   # [(name, ok)]
    log: list = field(default_factory=list)     # signalling lines

    @property
    def status(self):
        return "ATTACHED" if self.attached else "ATTACH FAILED"


def attach(db, imsi, pool, hss_up=True, sgw_up=True, pgw_up=True, start=None):
    t = start or datetime.now()
    res = AttachResult(imsi)

    def emit(src, dst, msg):
        nonlocal t
        res.log.append(f"{t:%H:%M:%S} {src} → {dst} : {msg}")
        t += timedelta(seconds=1)

    def done(name, ok):
        res.steps.append((name, ok))

    emit("UE", "MME", "Attach Request")
    done("Attach Request", True)

    # --- Authentication (MME <-> HSS)
    emit("MME", "HSS", "Authentication Request")
    sub = db.get(imsi)
    if not hss_up:
        emit("MME", "HSS", "Authentication Request Timeout")
        emit("MME", "UE", "Attach Reject")
        res.reason = "HSS unreachable"
        done("Authentication", False)
        return res
    ok, why = authenticate(sub)
    if not ok:
        emit("HSS", "MME", "Authentication Failure")
        emit("MME", "UE", "Attach Reject")
        res.reason = why
        done("Authentication", False)
        return res
    emit("HSS", "MME", "Authentication Response")
    done("Authentication", True)

    # --- Subscriber validation (profile / Update Location)
    emit("MME", "HSS", "Update Location Request")
    ok, why = validate_subscriber(sub, "4G")
    if not ok:
        emit("HSS", "MME", "Update Location Reject")
        emit("MME", "UE", "Attach Reject")
        res.reason = why
        done("Subscriber Validation", False)
        return res
    emit("HSS", "MME", "Update Location Answer")
    done("Subscriber Validation", True)

    # --- Session creation (MME -> SGW -> PGW)
    emit("MME", "SGW", "Create Session Request")
    if not sgw_up:
        emit("MME", "SGW", "Create Session Request Timeout")
        emit("MME", "UE", "Attach Reject")
        res.reason = "SGW unreachable"
        done("Session Creation", False)
        return res
    emit("SGW", "PGW", "Create Session Request")
    if not pgw_up:
        emit("PGW", "SGW", "Create Session Reject")
        emit("MME", "UE", "Attach Reject")
        res.reason = "PGW rejected session (gateway failure)"
        done("Session Creation", False)
        return res
    emit("PGW", "SGW", "Create Session Response")
    emit("SGW", "MME", "Create Session Response")
    done("Session Creation", True)

    # --- IP allocation
    res.ip = pool.allocate()
    done("IP Allocation", True)
    emit("MME", "UE", "Attach Accept")
    res.attached = True
    res.reason = f"UE attached, IP {res.ip}"
    return res
