"""4G LTE Core Network KPI Monitoring & Troubleshooting Simulator (Streamlit)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.alarms import detect_alarms, troubleshoot
from analysis.kpi_analysis import FAULTS, ICON, THRESHOLDS, generate_kpi_data, kpi_summary
from simulator.session import IPPool, STEPS, attach
from simulator.signalling import analyse
from simulator.subscriber import SubscriberDB

st.set_page_config(page_title="LTE Core KPI Monitor", page_icon="📡", layout="wide")
st.title("📡 4G LTE Core KPI Monitoring & Troubleshooting Simulator")

if "db" not in st.session_state:
    st.session_state.db = SubscriberDB()
    st.session_state.pool = IPPool()
db, pool = st.session_state.db, st.session_state.pool

# ---------------- Sidebar: network state / fault injection
st.sidebar.header("Network state")
fault_name = st.sidebar.selectbox("Inject KPI fault (last 3 hours)", list(FAULTS))
hours = st.sidebar.slider("History (hours)", 6, 72, 24)
st.sidebar.markdown("**Node availability (attach simulator)**")
hss_up = st.sidebar.checkbox("HSS up", True)
sgw_up = st.sidebar.checkbox("SGW up", True)
pgw_up = st.sidebar.checkbox("PGW up", True)

df = generate_kpi_data(hours=hours, fault=FAULTS[fault_name])
latest = df.iloc[-1]

tab_kpi, tab_alarm, tab_attach, tab_sig, tab_sub = st.tabs(
    ["📊 KPI Dashboard", "🚨 Alarms & Troubleshooting", "🔗 Attach Simulator",
     "📜 Signalling Analysis", "👤 Subscribers"])

# ---------------- KPI dashboard
with tab_kpi:
    st.subheader("Current KPIs")
    st.dataframe(kpi_summary(latest), hide_index=True, width="stretch")
    kpi_key = st.selectbox("KPI trend", list(THRESHOLDS), format_func=lambda k: THRESHOLDS[k][0])
    label, unit, higher, warn, crit = THRESHOLDS[kpi_key]
    fig = px.line(df, x="timestamp", y=kpi_key, markers=True, title=f"{label} ({unit})")
    fig.add_hline(y=warn, line_dash="dot", line_color="orange", annotation_text="warning")
    fig.add_hline(y=crit, line_dash="dot", line_color="red", annotation_text="critical")
    st.plotly_chart(fig, width="stretch")
    st.plotly_chart(px.area(df, x="timestamp", y="active_subscribers", title="Active subscribers"),
                    width="stretch")

# ---------------- Alarms
with tab_alarm:
    alarms = detect_alarms(latest)
    if alarms.empty:
        st.success("No active alarms - network healthy.")
    else:
        st.dataframe(alarms[["alarm_id", "node", "type", "severity", "kpi", "value"]],
                     hide_index=True, width="stretch")
        for _, a in alarms.iterrows():
            box = st.error if a.severity == "CRITICAL" else st.warning
            box(f"**{a.severity} - {a.node}: {a.type}** ({a.kpi} = {a.value})\n\n"
                "**Possible causes:**\n" + "\n".join(f"- {c}" for c in a.causes) +
                f"\n\n**Recommended action:** {a.action}")
    st.subheader("Troubleshooting engine (rule-based)")
    hints = troubleshoot(latest)
    for h in hints:
        st.write(f"➡️ {h}")
    if not hints:
        st.write("No rule triggered.")
    st.caption("Flow: which KPI changed → which node → check signalling/logs → probable cause → action.")

# ---------------- Attach simulator
with tab_attach:
    st.subheader("LTE attach procedure")
    subs = db.all()
    imsi = st.selectbox("Subscriber IMSI", list(subs["imsi"]) + ["404450009999 (unknown)"])
    imsi = imsi.split()[0]
    if st.button("Attach UE", type="primary"):
        st.session_state.last = attach(db, imsi, pool, hss_up, sgw_up, pgw_up)
    res = st.session_state.get("last")
    if res:
        done = dict(res.steps)
        for s in STEPS:
            st.write(("✅ " if done.get(s) else "❌ " if s in done else "⬜ ") + s)
        (st.success if res.attached else st.error)(f"STATUS: {res.status} - {res.reason}")
        st.code("\n".join(res.log))
        st.session_state.sig_text = "\n".join(res.log)

# ---------------- Signalling analysis
with tab_sig:
    st.subheader("Analyse a signalling log")
    samples = {
        "Last attach from simulator": st.session_state.get("sig_text", ""),
        "HSS authentication failure": "08:01:23 UE → MME : Attach Request\n08:01:24 MME → HSS : Authentication Request\n08:01:25 HSS → MME : Authentication Failure",
        "Successful attach": "08:01:23 UE → MME : Attach Request\n08:01:24 MME → HSS : Authentication Request\n08:01:24 HSS → MME : Authentication Response\n08:01:25 MME → SGW : Create Session Request\n08:01:26 SGW → PGW : Create Session Request\n08:01:27 PGW → SGW : Create Session Response\n08:01:28 MME → UE : Attach Accept",
        "PGW rejects session": "08:01:23 UE → MME : Attach Request\n08:01:24 MME → HSS : Authentication Request\n08:01:24 HSS → MME : Authentication Response\n08:01:25 MME → SGW : Create Session Request\n08:01:26 SGW → PGW : Create Session Request\n08:01:27 PGW → SGW : Create Session Reject",
    }
    choice = st.selectbox("Load sample", list(samples))
    text = st.text_area("Signalling log", samples[choice], height=180, key=f"log_{choice}")
    if text.strip():
        r = analyse(text)
        if r["ok"]:
            st.success(f"✅ {r['summary']}")
        else:
            st.error(f"❌ {r['summary']}")
            st.markdown(f"**Failure point:** {r['failure_point']}\n\n**Probable cause:** {r['cause']}")
            if r["steps"]:
                st.markdown("**Recommended investigation:**\n" +
                            "\n".join(f"{i}. {s}" for i, s in enumerate(r["steps"], 1)))

# ---------------- Subscribers
with tab_sub:
    st.subheader("Subscriber provisioning")
    st.dataframe(db.all(), hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Add subscriber**")
        n_imsi = st.text_input("IMSI", "404450000099")
        n_status = st.selectbox("Status", ["Active", "Inactive", "Blocked"], key="ns")
        n_plan = st.selectbox("Plan", ["4G", "3G", "2G"], key="np")
        if st.button("Add"):
            try:
                db.add(n_imsi, n_status, n_plan)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    with c2:
        st.markdown("**Modify / remove / check**")
        sel = st.selectbox("IMSI", list(db.all()["imsi"]), key="sel")
        st.json(db.get(sel) or {})
        s = st.selectbox("New status", ["Active", "Inactive", "Blocked"], key="ms")
        p = st.selectbox("New plan", ["4G", "3G", "2G"], key="mp")
        b1, b2, b3 = st.columns(3)
        if b1.button("Set status"):
            db.set_status(sel, s); st.rerun()
        if b2.button("Set plan"):
            db.set_plan(sel, p); st.rerun()
        if b3.button("Remove"):
            db.remove(sel); st.rerun()
