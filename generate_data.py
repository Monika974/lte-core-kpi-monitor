"""Generate sample data/kpi_data.csv and data/alarms.csv (run: python generate_data.py [fault])"""
import sys
from analysis.kpi_analysis import generate_kpi_data, FAULTS
from analysis.alarms import detect_alarms

fault = FAULTS.get(" ".join(sys.argv[1:]), None) if len(sys.argv) > 1 else None
df = generate_kpi_data(hours=24, fault=fault)
df.to_csv("data/kpi_data.csv", index=False)
alarms = detect_alarms(df.iloc[-1])
alarms.assign(causes=alarms["causes"].map("; ".join)).to_csv("data/alarms.csv", index=False)
print(f"Wrote {len(df)} KPI rows and {len(alarms)} alarms")
