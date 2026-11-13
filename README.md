# 📡 4G LTE Core Network KPI Monitoring & Troubleshooting Simulator

A Python simulator and Streamlit dashboard that models a simplified 4G LTE core (EPC):
**UE → eNodeB → MME ↔ HSS, SGW, PGW → Internet**. Network events and KPIs are *simulated*;
the goal is to demonstrate subscriber provisioning, signalling/call-flow analysis, KPI monitoring,
alarm detection and rule-based troubleshooting.

> Troubleshooting is intentionally **rule-based** (no ML) - it mirrors how NOC/core engineers reason:
> *Which KPI changed? → Which node? → Check signalling/logs → Probable cause → Action.*

## Features
| # | Feature | Where |
|---|---------|-------|
| 1 | Subscriber provisioning (add/remove, activate/deactivate/block, check status, assign 2G/3G/4G) - SQLite | `simulator/subscriber.py` |
| 2 | LTE attach simulation: Attach Request → Authentication → Subscriber Validation → Session Creation → IP Allocation | `simulator/session.py` |
| 3 | KPI dashboard: attach / auth / session success, call drop, latency, packet loss, throughput, MME CPU, active subscribers (🟢🟡🔴 + trend charts) | `analysis/kpi_analysis.py`, `app.py` |
| 4 | Alarm detection with possible causes + recommended actions | `analysis/alarms.py` |
| 5 | Rule-based troubleshooting engine | `analysis/alarms.py` |
| 6 | Signalling log parser that finds the failure point and probable cause | `simulator/signalling.py` |

You can inject faults (HSS auth degradation, transport congestion, MME overload, PGW failure) from the sidebar
and watch KPIs, alarms and recommendations react.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python generate_data.py          # optional: writes sample data/kpi_data.csv + data/alarms.csv
streamlit run app.py
pytest                           # run tests
```

## LTE attach flow
```
UE → MME : Attach Request
MME → HSS : Authentication Request ; HSS → MME : Authentication Response
MME → HSS : Update Location Request ; HSS → MME : Update Location Answer   (subscriber validation)
MME → SGW → PGW : Create Session Request ; responses back
PGW allocates IP ; MME → UE : Attach Accept   → STATUS: ATTACHED
```

### Failure examples the analyser recognises
| Log shows | Failure point | Probable cause |
|---|---|---|
| Authentication Failure | HSS Authentication | Unknown IMSI / bad auth parameters |
| Authentication Request Timeout | MME → HSS (S6a) | HSS unreachable |
| Update Location Reject | HSS Subscriber Validation | Blocked/inactive subscriber, RAT not allowed |
| Create Session Request Timeout | MME → SGW (S11) | SGW unreachable |
| Create Session Reject | SGW → PGW (S5/S8) | PGW failure / APN / IP pool |

## KPI thresholds
| KPI | Warning | Critical |
|---|---|---|
| Attach success | < 97% | < 95% |
| Authentication success | < 99% | < 97% |
| Session establishment | < 96% | < 93% |
| Call drop rate | > 2.5% | > 5% |
| Latency | > 60 ms | > 100 ms |
| Packet loss | > 1.5% | > 5% |
| Throughput | < 60 Mbps | < 30 Mbps |
| MME CPU | > 75% | > 90% |

## Project structure
```
app.py                 Streamlit dashboard
generate_data.py       sample CSV generator
simulator/             subscriber DB, authentication, attach/session, signalling analysis
analysis/              KPI generation/classification, alarms + troubleshooting rules
data/                  subscribers.csv (seed), kpi_data.csv, alarms.csv
tests/                 pytest suite
screenshots/           add dashboard.png, attach_flow.png, alarms.png here
```

## Tech
Python · Pandas · NumPy · Streamlit · Plotly · SQLite · LTE/EPC · IP networking

## Resume description
Developed a Python-based 4G LTE core network simulator to model subscriber provisioning, authentication,
session establishment and signalling flows across MME, HSS, SGW and PGW components. Built a Streamlit
dashboard to monitor network KPIs including attach success rate, authentication failures, latency, packet loss
and session establishment rate, with rule-based alarm detection and troubleshooting recommendations.

## Possible extensions
Roaming (home vs visited network, S6a/S8), Wireshark/PCAP import, handover (X2/S1) simulation, Docker.
