"""Rule-based alarm detection and troubleshooting (no ML on purpose)."""
import pandas as pd
from .kpi_analysis import classify

# kpi -> (node, alarm type, possible causes, recommended action)
ALARM_RULES = {
    "attach_success_rate": ("MME", "Attach Failure Spike",
        ["MME/HSS signalling issue", "MME overload", "Subscriber database problem"],
        "Check MME and HSS signalling logs; compare with authentication success."),
    "auth_success_rate": ("HSS", "Authentication Failure",
        ["HSS unavailable", "Subscriber database issue", "Authentication vector/parameter failure"],
        "Check HSS connectivity and authentication logs."),
    "session_success_rate": ("PGW", "Gateway Failure",
        ["PGW overloaded or down", "IP pool exhausted", "APN misconfiguration"],
        "Check PGW status, IP pool utilisation and APN configuration."),
    "call_drop_rate": ("SGW", "High Call Drop Rate",
        ["Radio/handover problems", "SGW instability", "Transport packet loss"],
        "Check SGW alarms, handover stats and transport quality."),
    "latency_ms": ("PGW", "High Latency",
        ["Transport network congestion", "Routing issue", "Overloaded gateway"],
        "Check transport links, run traceroute/ping, review congestion."),
    "packet_loss_pct": ("SGW", "Packet Loss",
        ["Transport/network congestion", "Faulty link or interface errors"],
        "Check interface error counters and link utilisation on S1-U/S5."),
    "throughput_mbps": ("PGW", "Low Throughput",
        ["Backhaul congestion", "Gateway capacity limit"],
        "Check backhaul utilisation and gateway capacity."),
    "mme_cpu_pct": ("MME", "High CPU",
        ["Signalling storm", "Too many attach requests", "Software issue"],
        "Check attach/TAU rate, restart runaway processes, consider load balancing."),
}

SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1}
COLUMNS = ["alarm_id", "node", "type", "severity", "kpi", "value", "causes", "action"]


def detect_alarms(row):
    """Return a DataFrame of active alarms for one KPI row (dict/Series)."""
    out = []
    for kpi, (node, atype, causes, action) in ALARM_RULES.items():
        state = classify(kpi, row[kpi])
        if state != "OK":
            out.append(dict(node=node, type=atype, severity=state, kpi=kpi,
                            value=round(float(row[kpi]), 2), causes=causes, action=action))
    out.sort(key=lambda a: SEVERITY_ORDER[a["severity"]])
    for i, a in enumerate(out, 1):
        a["alarm_id"] = f"ALM{i:03d}"
    return pd.DataFrame(out, columns=COLUMNS)


def troubleshoot(row):
    """Simple if-rules. Returns list of hints."""
    hints = []
    if row["attach_success_rate"] < 95:
        hints.append("Possible MME/HSS signalling issue")
    if row["packet_loss_pct"] > 5:
        hints.append("Possible transport/network congestion")
    if row.get("auth_failures", 0) > 10:
        hints.append("Check HSS authentication service")
    if row["latency_ms"] > 100:
        hints.append("Check transport network or congestion")
    if row["mme_cpu_pct"] > 90:
        hints.append("MME overloaded - check signalling storm / attach rate")
    if row["session_success_rate"] < 93:
        hints.append("Check PGW/SGW session handling and IP pool")
    return hints
