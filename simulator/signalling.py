"""Signalling log parsing and failure analysis."""
import re

LINE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(\w+)\s*(?:→|->)\s*(\w+)\s*:\s*(.+?)\s*$")

# keyword -> (failure point, probable cause, investigation steps)
FAILURE_RULES = [
    ("Authentication Request Timeout", "MME → HSS (S6a)",
     "HSS unreachable / S6a (Diameter) link down",
     ["Check HSS connectivity and S6a link", "Check HSS service/process status", "Check transport between MME and HSS"]),
    ("Authentication Failure", "HSS Authentication",
     "Subscriber authentication failure",
     ["Check subscriber status", "Check HSS connectivity", "Check authentication parameters (K/OPc, IMSI provisioning)"]),
    ("Update Location Reject", "HSS Subscriber Validation",
     "Subscriber barred, inactive or RAT/plan not allowed",
     ["Check subscriber status (Active/Blocked)", "Check plan/network technology assigned", "Check roaming/RAT restrictions"]),
    ("Create Session Request Timeout", "MME → SGW (S11)",
     "SGW unreachable / S11 interface issue",
     ["Check SGW status and S11 connectivity", "Check SGW CPU/alarms", "Check GTP-C path"]),
    ("Create Session Reject", "SGW → PGW (S5/S8)",
     "PGW rejected session: gateway failure, APN or IP pool problem",
     ["Check PGW alarms and status", "Check APN configuration", "Check IP address pool utilisation"]),
    ("Attach Reject", "MME",
     "Attach rejected by MME (cause not visible in log)",
     ["Check MME logs for reject cause code", "Check MME load/CPU"]),
]


def parse_log(lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    out = []
    for ln in lines:
        m = LINE.match(ln.strip())
        if m:
            out.append(dict(time=m[1], src=m[2], dst=m[3], msg=m[4]))
    return out


def analyse(lines):
    """Return dict: ok, summary, failure_point, cause, steps."""
    events = parse_log(lines)
    if not events:
        return dict(ok=False, summary="NO VALID SIGNALLING FOUND", failure_point="-",
                    cause="Log empty or format not recognised (expected 'HH:MM:SS A → B : Message')", steps=[])
    msgs = [e["msg"] for e in events]
    for key, point, cause, steps in FAILURE_RULES:
        if any(key.lower() in m.lower() for m in msgs):
            return dict(ok=False, summary="ATTACH FAILURE", failure_point=point, cause=cause, steps=steps)
    if any("Attach Accept" in m for m in msgs):
        return dict(ok=True, summary="ATTACH SUCCESS", failure_point="-", cause="-", steps=[])
    last = events[-1]
    return dict(ok=False, summary="ATTACH INCOMPLETE", failure_point=f"{last['src']} → {last['dst']}",
                cause=f"Flow stopped after '{last['msg']}' (no Attach Accept/Reject seen)",
                steps=["Check for message loss or timeout on this interface", "Check peer node status"])
