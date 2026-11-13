"""Subscriber provisioning (HSS-style subscriber database) backed by SQLite."""
import sqlite3
from pathlib import Path
import pandas as pd

VALID_STATUS = {"Active", "Inactive", "Blocked"}
VALID_PLAN = {"2G", "3G", "4G"}


class SubscriberDB:
    def __init__(self, db_path="data/lte.db", seed_csv="data/subscribers.csv"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
                imsi TEXT PRIMARY KEY, status TEXT NOT NULL, plan TEXT NOT NULL)""")
            empty = c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0] == 0
        if empty and seed_csv and Path(seed_csv).exists():
            for r in pd.read_csv(seed_csv, dtype=str).itertuples():
                self.add(r.imsi, r.status, r.plan)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _check(imsi, status, plan):
        if not (str(imsi).isdigit() and 6 <= len(str(imsi)) <= 15):
            raise ValueError("IMSI must be 6-15 digits")
        if status not in VALID_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_STATUS)}")
        if plan not in VALID_PLAN:
            raise ValueError(f"Plan must be one of {sorted(VALID_PLAN)}")

    def add(self, imsi, status="Active", plan="4G"):
        self._check(imsi, status, plan)
        try:
            with self._conn() as c:
                c.execute("INSERT INTO subscribers VALUES (?,?,?)", (imsi, status, plan))
        except sqlite3.IntegrityError:
            raise ValueError(f"IMSI {imsi} already exists")

    def remove(self, imsi):
        with self._conn() as c:
            return c.execute("DELETE FROM subscribers WHERE imsi=?", (imsi,)).rowcount > 0

    def set_status(self, imsi, status):
        if status not in VALID_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_STATUS)}")
        with self._conn() as c:
            return c.execute("UPDATE subscribers SET status=? WHERE imsi=?", (status, imsi)).rowcount > 0

    def set_plan(self, imsi, plan):
        if plan not in VALID_PLAN:
            raise ValueError(f"Plan must be one of {sorted(VALID_PLAN)}")
        with self._conn() as c:
            return c.execute("UPDATE subscribers SET plan=? WHERE imsi=?", (plan, imsi)).rowcount > 0

    def get(self, imsi):
        with self._conn() as c:
            row = c.execute("SELECT imsi,status,plan FROM subscribers WHERE imsi=?", (imsi,)).fetchone()
        return dict(zip(("imsi", "status", "plan"), row)) if row else None

    def all(self):
        with self._conn() as c:
            return pd.read_sql_query("SELECT imsi,status,plan FROM subscribers ORDER BY imsi", c)
