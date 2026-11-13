import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from simulator.subscriber import SubscriberDB
from simulator.session import attach, IPPool
from simulator.signalling import analyse
from analysis.kpi_analysis import generate_kpi_data, classify
from analysis.alarms import detect_alarms, troubleshoot


@pytest.fixture
def db(tmp_path):
    return SubscriberDB(tmp_path / "t.db", os.path.join(os.path.dirname(__file__), "..", "data", "subscribers.csv"))


def test_provisioning(db):
    db.add("404450009999", "Active", "4G")
    assert db.get("404450009999")["plan"] == "4G"
    with pytest.raises(ValueError):
        db.add("404450009999")
    assert db.set_status("404450009999", "Blocked") and db.get("404450009999")["status"] == "Blocked"
    assert db.set_plan("404450009999", "3G")
    assert db.remove("404450009999") and db.get("404450009999") is None
    with pytest.raises(ValueError):
        db.add("abc")


def test_attach_success(db):
    r = attach(db, "404450000001", IPPool())
    assert r.attached and r.ip == "10.45.0.2" and all(ok for _, ok in r.steps) and len(r.steps) == 5
    assert analyse(r.log)["ok"]


@pytest.mark.parametrize("imsi,kwargs,point", [
    ("404450000001", dict(hss_up=False), "MME → HSS (S6a)"),
    ("404450009998", {}, "HSS Authentication"),
    ("404450000003", {}, "HSS Subscriber Validation"),
    ("404450000004", {}, "HSS Subscriber Validation"),
    ("404450000001", dict(sgw_up=False), "MME → SGW (S11)"),
    ("404450000001", dict(pgw_up=False), "SGW → PGW (S5/S8)"),
])
def test_attach_failures(db, imsi, kwargs, point):
    r = attach(db, imsi, IPPool(), **kwargs)
    assert not r.attached
    assert analyse(r.log)["failure_point"] == point


def test_kpis_and_alarms():
    healthy = generate_kpi_data(fault=None).iloc[-1]
    assert (detect_alarms(healthy)["severity"] == "CRITICAL").sum() == 0
    bad = generate_kpi_data(fault="hss").iloc[-1]
    a = detect_alarms(bad)
    assert "HSS" in a["node"].values and "Check HSS authentication service" in troubleshoot(bad)
    assert classify("latency_ms", 150) == "CRITICAL" and classify("latency_ms", 40) == "OK"
