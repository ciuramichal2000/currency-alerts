"""Exchange-rate alerts: rules like 'EUR above 4.35 PLN', rates fetched from the NBP API (injectable), history in SQLite,
and each alert fires once when the condition becomes true and again only after it has been false in between."""
import json
import sqlite3
import urllib.request
from typing import Callable, Dict, List, Optional

NBP = "https://api.nbp.pl/api/exchangerates/rates/a/%s/?format=json"


def nbp_fetch(code: str) -> float:
    with urllib.request.urlopen(NBP % code.lower(), timeout=10) as r:
        return float(json.load(r)["rates"][0]["mid"])


class Alerts:
    def __init__(self, path: str = ":memory:", fetch: Callable[[str], float] = nbp_fetch, clock: Callable[[], float] = None):
        import time
        self.db = sqlite3.connect(path)
        self.db.executescript("CREATE TABLE IF NOT EXISTS rules(id INTEGER PRIMARY KEY, code TEXT, op TEXT, threshold REAL, active INTEGER DEFAULT 0);"
                              "CREATE TABLE IF NOT EXISTS history(code TEXT, at REAL, rate REAL);")
        self.fetch, self.clock = fetch, clock or time.time

    def add_rule(self, code: str, op: str, threshold: float) -> int:
        if op not in ("above", "below"):
            raise ValueError("op must be 'above' or 'below'")
        cur = self.db.execute("INSERT INTO rules(code,op,threshold) VALUES(?,?,?)", (code.upper(), op, threshold))
        self.db.commit()
        return cur.lastrowid

    def check(self) -> List[Dict[str, object]]:
        """Fetch each currency once, store it, and return only the alerts that have just become true."""
        rules = self.db.execute("SELECT id, code, op, threshold, active FROM rules").fetchall()
        rates: Dict[str, float] = {}
        fired = []
        for rid, code, op, thr, active in rules:
            if code not in rates:
                rates[code] = self.fetch(code)
                self.db.execute("INSERT INTO history VALUES(?,?,?)", (code, self.clock(), rates[code]))
            met = rates[code] > thr if op == "above" else rates[code] < thr
            if met and not active:
                fired.append({"rule": rid, "code": code, "op": op, "threshold": thr, "rate": rates[code]})
            if met != bool(active):
                self.db.execute("UPDATE rules SET active=? WHERE id=?", (int(met), rid))
        self.db.commit()
        return fired

    def history(self, code: str, limit: int = 30) -> List[Dict[str, float]]:
        return [{"at": a, "rate": r} for a, r in self.db.execute("SELECT at, rate FROM history WHERE code=? ORDER BY at DESC, rowid DESC LIMIT ?", (code.upper(), limit))]

    def stats(self, code: str) -> Optional[Dict[str, float]]:
        row = self.db.execute("SELECT MIN(rate), MAX(rate), AVG(rate), COUNT(*) FROM history WHERE code=?", (code.upper(),)).fetchone()
        return None if not row[3] else {"min": row[0], "max": row[1], "avg": round(row[2], 4), "n": row[3]}
