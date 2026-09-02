"""
SuperEnalotto Engine - Logica di gioco, strategie, verifica.
"""

import csv
import json
import os
import random
import sqlite3
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta

# Costanti
CSV_PATH = "superenalotto.csv"
DB_PATH = "superenalotto.db"
TRACKING_PATH = "tracking.csv"
CONFIG_PATH = "config.json"

# Premi medi ufficiali ADM (fallback)
PREMI_DEFAULT = {2: 5.0, 3: 25.0, 4: 296.0, 5: 25847.0, 5.5: 100000.0, 6: 1000000.0}

# Giorni estrazione (weekday: 0=Lun, 1=Mar, ..., 6=Dom)
DRAW_DOWS = {1, 3, 4, 5}  # Mar, Gio, Ven, Sab


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


class SuperenalottoEngine:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.records = []
        self.stats = {}
        self._init_db()

    def _init_db(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, DB_PATH)
        self.csv_path = os.path.join(base_dir, CSV_PATH)
        self.tracking_path = os.path.join(base_dir, TRACKING_PATH)
        
        self.conn = sqlite3.connect(self.db_path)
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS estrazioni (
                data TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT,
                jolly INT DEFAULT 0, star INT DEFAULT 0,
                p2 REAL DEFAULT 0, p3 REAL DEFAULT 0, p4 REAL DEFAULT 0,
                p5 REAL DEFAULT 0, p5j REAL DEFAULT 0, p6 REAL DEFAULT 0)
        """)
        try:
            c.execute("SELECT p2 FROM estrazioni LIMIT 0")
        except:
            for col in ["p2", "p3", "p4", "p5", "p5j", "p6"]:
                try:
                    c.execute(f"ALTER TABLE estrazioni ADD COLUMN {col} REAL DEFAULT 0")
                except:
                    pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS giocate (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, numeri TEXT,
                somma INT, verificato INT DEFAULT 0, vincita REAL DEFAULT 0)
        """)
        self.conn.commit()
        c.execute("SELECT COUNT(*) FROM estrazioni")
        if c.fetchone()[0] == 0 and os.path.exists(self.csv_path):
            self._import_csv()
        c.execute("SELECT COUNT(*) FROM giocate")
        if c.fetchone()[0] == 0 and os.path.exists(self.tracking_path):
            self._import_tracking()
        self._load_records()

    def _import_csv(self):
        c = self.conn.cursor()
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 9:
                    continue
                try:
                    try:
                        nums = [int(row[2]), int(row[3]), int(row[4]),
                                int(row[5]), int(row[6]), int(row[7])]
                        jolly = int(row[8]) if row[8] else 0
                        star = int(row[9]) if len(row) > 9 and row[9] else 0
                    except:
                        nums = [int(row[4]), int(row[5]), int(row[6]),
                                int(row[7]), int(row[8]), int(row[9])]
                        jolly = int(row[10]) if len(row) > 10 and row[10] else 0
                        star = int(row[11]) if len(row) > 11 and row[11] else 0
                    data_raw = row[0]
                    try:
                        if "/" in data_raw:
                            data_norm = datetime.strptime(data_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                        else:
                            data_norm = datetime.strptime(data_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
                    except:
                        data_norm = data_raw
                    c.execute(
                        "INSERT OR IGNORE INTO estrazioni (data,n1,n2,n3,n4,n5,n6,jolly,star) VALUES (?,?,?,?,?,?,?,?,?)",
                        (data_norm, nums[0], nums[1], nums[2], nums[3], nums[4], nums[5], jolly, star),
                    )
                except:
                    continue
        self.conn.commit()

    def _import_tracking(self):
        c = self.conn.cursor()
        with open(TRACKING_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 6:
                    continue
                try:
                    nums_str = row[4] if len(row) > 4 else ""
                    somma = int(row[5]) if len(row) > 5 and row[5] else 0
                    c.execute(
                        "INSERT INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)",
                        (row[0], nums_str, somma),
                    )
                except:
                    continue
        self.conn.commit()

    def _load_records(self):
        c = self.conn.cursor()
        c.execute("SELECT data, n1, n2, n3, n4, n5, n6, jolly, star FROM estrazioni ORDER BY data")
        self.records = []
        for row in c.fetchall():
            self.records.append({
                "data": row[0],
                "nums": [row[1], row[2], row[3], row[4], row[5], row[6]],
                "jolly": row[7] or 0,
                "star": row[8] or 0,
            })
        self._calc_stats()

    def _calc_stats(self):
        if not self.records:
            self.stats = {}
            return
        sums = [sum(r["nums"]) for r in self.records]
        all_nums = [n for r in self.records for n in r["nums"]]
        num_counts = Counter(all_nums)
        sums_sorted = sorted(sums)
        n = len(sums)
        self.stats = {
            "count": n,
            "mean": sum(sums) / n,
            "median": sums_sorted[n // 2],
            "std": (sum((s - sums_sorted[n // 2]) ** 2 for s in sums) / n) ** 0.5,
            "q1": sums_sorted[n // 4],
            "q3": sums_sorted[3 * n // 4],
            "min": min(sums),
            "max": max(sums),
            "num_counts": dict(num_counts.most_common()),
        }

    def quartile_spread(self):
        """Genera 6 numeri con strategia QuartileSpread."""
        if not self.stats:
            return [random.randint(1, 90) for _ in range(6)]
        q1 = self.stats["q1"]
        q3 = self.stats["q3"]
        nums = []
        ranges = [(1, 23), (23, 45), (45, 67), (67, 90)]
        for _ in range(100):
            candidate = []
            for lo, hi in ranges:
                n = random.randint(lo, hi)
                while n in candidate:
                    n = random.randint(lo, hi)
                candidate.append(n)
            s = sum(candidate)
            if q1 <= s <= q3:
                decades = Counter(n // 10 for n in candidate)
                if max(decades.values()) <= 2 and sum(1 for n in candidate if n > 80) <= 1:
                    return sorted(candidate)
        # fallback
        return sorted(random.sample(range(1, 91), 6))

    def genera_schedine(self, n=1):
        """Genera n schedine con QuartileSpread."""
        return [self.quartile_spread() for _ in range(n)]

    def verifica_giocata(self, data, numeri):
        """Verifica una giocata contro l'estrazione della data. Ritorna (matches, jolly_hit, premio)."""
        c = self.conn.cursor()
        c.execute("SELECT n1,n2,n3,n4,n5,n6,jolly,p2,p3,p4,p5,p5j,p6 FROM estrazioni WHERE data=?", (data,))
        rec = c.fetchone()
        if rec is None:
            return None
        estr_nums = list(rec[:6])
        jolly = rec[6]
        matches = len(set(numeri) & set(estr_nums))
        jolly_hit = jolly in numeri if jolly else False
        # premi reali dal DB o default
        p2, p3, p4, p5, p5j, p6 = rec[7], rec[8], rec[9], rec[10], rec[11], rec[12]
        if matches == 6:
            premio = p6 if p6 > 0 else PREMI_DEFAULT[6]
        elif matches == 5:
            if jolly_hit:
                premio = p5j if p5j > 0 else PREMI_DEFAULT[5.5]
            else:
                premio = p5 if p5 > 0 else PREMI_DEFAULT[5]
        elif matches == 4:
            premio = p4 if p4 > 0 else PREMI_DEFAULT[4]
        elif matches == 3:
            premio = p3 if p3 > 0 else PREMI_DEFAULT[3]
        elif matches == 2:
            premio = p2 if p2 > 0 else PREMI_DEFAULT[2]
        else:
            premio = 0
        return {"matches": matches, "jolly_hit": jolly_hit, "premio": premio}

    def salva_giocata(self, data, numeri, somma):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)",
            (data, "-".join(map(str, numeri)), somma),
        )
        self.conn.commit()

    def verifica_tutte(self, only_unchecked=False):
        c = self.conn.cursor()
        c.execute("SELECT id, data, numeri FROM giocate")
        rows = c.fetchall()
        results = []
        tot_win = 0
        checked = 0
        skipped = 0
        for gid, data, numeri_str in rows:
            try:
                nums = [int(x) for x in numeri_str.split("-") if x]
            except:
                continue
            if len(nums) != 6:
                continue
            if only_unchecked:
                c.execute("SELECT verificato FROM giocate WHERE id=?", (gid,))
                if c.fetchone()[0] == 1:
                    continue
            res = self.verifica_giocata(data, nums)
            if res is None:
                skipped += 1
                continue
            tot_win += res["premio"]
            checked += 1
            c.execute("UPDATE giocate SET verificato=1, vincita=? WHERE id=?", (res["premio"], gid))
            results.append({
                "data": data,
                "numeri": numeri_str,
                "matches": res["matches"],
                "jolly_hit": res["jolly_hit"],
                "premio": res["premio"],
            })
        self.conn.commit()
        return {"checked": checked, "skipped": skipped, "tot_win": tot_win, "results": results}

    def cancella_giocata(self, gid):
        c = self.conn.cursor()
        c.execute("DELETE FROM giocate WHERE id=?", (gid,))
        self.conn.commit()

    def get_giocate(self):
        c = self.conn.cursor()
        c.execute("SELECT id, data, numeri, somma, verificato, vincita FROM giocate ORDER BY id DESC")
        return [
            {"id": r[0], "data": r[1], "numeri": r[2], "somma": r[3],
             "verificato": r[4], "vincita": r[5]}
            for r in c.fetchall()
        ]

    def get_estrazioni_recenti(self, n=20):
        c = self.conn.cursor()
        c.execute("SELECT data, n1, n2, n3, n4, n5, n6, jolly, star FROM estrazioni ORDER BY data DESC LIMIT ?", (n,))
        return [
            {"data": r[0], "numeri": [r[1], r[2], r[3], r[4], r[5], r[6]],
             "jolly": r[7], "star": r[8]}
            for r in c.fetchall()
        ]

    def prossima_estrazione(self):
        today = datetime.now()
        today_dow = today.weekday()
        if today_dow in DRAW_DOWS:
            return today.strftime("%d/%m/%Y")
        for days_ahead in range(1, 8):
            if (today_dow + days_ahead) % 7 in DRAW_DOWS:
                return (today + timedelta(days=days_ahead)).strftime("%d/%m/%Y")
        return "N/A"

    def oggi_estrazione(self):
        return datetime.now().weekday() in DRAW_DOWS

    def close(self):
        if self.conn:
            self.conn.close()
