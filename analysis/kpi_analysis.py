"""Simulated KPI data + KPI health classification."""
import numpy as np
import pandas as pd

# kpi: (label, unit, higher_is_better, warn, crit)
THRESHOLDS = {
    "attach_success_rate":  ("Attach Success Rate", "%", True, 97.0, 95.0),
    "auth_success_rate":    ("Authentication Success", "%", True, 99.0, 97.0),
    "session_success_rate": ("Session Establishment", "%", True, 96.0, 93.0),
    "call_drop_rate":       ("Call Drop Rate", "%", False, 2.5, 5.0),
    "latency_ms":           ("Latency", "ms", False, 60.0, 100.0),
    "packet_loss_pct":      ("Packet Loss", "%", False, 1.5, 5.0),
    "throughput_mbps":      ("Throughput", "Mbps", True, 60.0, 30.0),
    "mme_cpu_pct":          ("MME CPU", "%", False, 75.0, 90.0),
}

FAULTS = {
    "None": None,
    "HSS authentication degradation": "hss",
    "Transport congestion": "transport",
    "MME overload": "mme",
    "PGW gateway failure": "pgw",
}

ICON = {"OK": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}


def classify(kpi, value):
    """Return 'OK' | 'WARNING' | 'CRITICAL'."""
    _, _, higher, warn, crit = THRESHOLDS[kpi]
    if higher:
        return "CRITICAL" if value < crit else "WARNING" if value < warn else "OK"
    return "CRITICAL" if value > crit else "WARNING" if value > warn else "OK"


def generate_kpi_data(hours=24, seed=42, fault=None, end=None):
    """Hourly KPI time series with a daily load pattern. `fault` degrades the last 3 hours."""
    rng = np.random.default_rng(seed)
    end = end or pd.Timestamp.now().floor("h")
    ts = pd.date_range(end=end, periods=hours, freq="h")
    load = 0.5 + 0.5 * np.sin((ts.hour.values - 14) / 24 * 2 * np.pi)   # peaks ~20:00
    n = hours
    df = pd.DataFrame({
        "timestamp": ts,
        "attach_success_rate": 98.4 - 0.8 * load + rng.normal(0, 0.3, n),
        "auth_success_rate": 99.4 - 0.3 * load + rng.normal(0, 0.15, n),
        "session_success_rate": 97.6 - 0.8 * load + rng.normal(0, 0.3, n),
        "call_drop_rate": 1.6 + 0.9 * load + rng.normal(0, 0.2, n),
        "latency_ms": 36 + 14 * load + rng.normal(0, 3, n),
        "packet_loss_pct": 0.7 + 0.7 * load + rng.normal(0, 0.15, n),
        "throughput_mbps": 86 - 12 * load + rng.normal(0, 3, n),
        "active_subscribers": 9000 + 4500 * load + rng.normal(0, 150, n),
        "mme_cpu_pct": 42 + 25 * load + rng.normal(0, 3, n),
    })
    tail = df.index[-3:]
    if fault == "hss":
        df.loc[tail, "auth_success_rate"] -= [6, 11, 14]
        df.loc[tail, "attach_success_rate"] -= [3, 6, 9]
    elif fault == "transport":
        df.loc[tail, "latency_ms"] += [30, 55, 80]
        df.loc[tail, "packet_loss_pct"] += [2, 4, 6]
        df.loc[tail, "throughput_mbps"] -= [20, 40, 55]
    elif fault == "mme":
        df.loc[tail, "mme_cpu_pct"] += [25, 35, 45]
        df.loc[tail, "attach_success_rate"] -= [2, 4, 6]
    elif fault == "pgw":
        df.loc[tail, "session_success_rate"] -= [6, 12, 20]
        df.loc[tail, "call_drop_rate"] += [2, 4, 6]
    for c in ("attach_success_rate", "auth_success_rate", "session_success_rate"):
        df[c] = df[c].clip(lower=0, upper=100)
    df["call_drop_rate"] = df["call_drop_rate"].clip(lower=0)
    df["packet_loss_pct"] = df["packet_loss_pct"].clip(lower=0)
    df["throughput_mbps"] = df["throughput_mbps"].clip(lower=1)
    df["mme_cpu_pct"] = df["mme_cpu_pct"].clip(upper=100)
    df["active_subscribers"] = df["active_subscribers"].round().astype(int)
    attempts = df["active_subscribers"] * 0.05
    df["auth_failures"] = (attempts * (100 - df["auth_success_rate"]) / 100).round().astype(int)
    num = df.select_dtypes("number").columns
    df[num] = df[num].round(2)
    return df


def kpi_summary(row):
    """Latest KPI table for the dashboard."""
    rows = []
    for k, (label, unit, *_r) in THRESHOLDS.items():
        s = classify(k, row[k])
        rows.append({"KPI": label, "Value": f"{row[k]:.1f} {unit}", "Status": ICON[s]})
    rows.append({"KPI": "Active Subscribers", "Value": f"{int(row['active_subscribers']):,}", "Status": ICON["OK"]})
    return pd.DataFrame(rows)
