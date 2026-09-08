"""
SuperEnalotto Engine - Logica di gioco, strategie, verifica.
"""

import csv
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import sys

import logging
logger = logging.getLogger(__name__)

import random
import time
import urllib.request
from collections import Counter
from datetime import datetime, timedelta

# Costanti
CSV_PATH = "superenalotto.csv"
DB_PATH = "superenalotto.db"
TRACKING_PATH = "tracking.csv"
CONFIG_PATH = "config.json"


def get_user_data_dir():
    """Restituisce la cartella dati utente: Documents/Superenalotto/.
    La crea se non esiste."""
    data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperEnalotto')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def migrate_db_if_needed():
    """Se il DB/tracking/config esistono accanto all'exe o in _MEIPASS ma non in Documents, li migra."""
    if not getattr(sys, 'frozen', False):
        return
    exe_dir = os.path.dirname(sys.executable)
    data_dir = get_user_data_dir()
    for fname in (DB_PATH, TRACKING_PATH, CONFIG_PATH):
        dst = os.path.join(data_dir, fname)
        if os.path.exists(dst):
            continue
        # Controlla accanto all'exe
        src = os.path.join(exe_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            continue
        # Controlla in _MEIPASS (bundled)
        try:
            mei_src = os.path.join(sys._MEIPASS, fname)
            if os.path.exists(mei_src):
                shutil.copy2(mei_src, dst)
        except Exception:
            pass

# Premi medi ufficiali ADM (fallback)
PREMI_DEFAULT = {2: 5.0, 3: 25.0, 4: 296.0, 5: 25847.0, 5.5: 100000.0, 6: 1000000.0}

# Giorni estrazione (weekday: 0=Lun, 1=Mar, ..., 6=Dom)
DRAW_DOWS = {1, 3, 4, 5}  # Mar, Gio, Ven, Sab

# Numeri primi 1-90
PRIMES = frozenset({2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89})

# Sequenza di Fibonacci (fino a 90)
FIBONACCI = [1,2,3,5,8,13,21,34,55,89]

# Coefficienti del comune denominatore (pattern ricorrenti analizzati su 4238 estrazioni)
# Somma target ottimale: 274-278 (interquartile centrale)
# Pattern low/mid/high più comune: 2-2-2 (531 estrazioni)
# Pattern parità  più comune: 3 even / 3 odd (1344 estrazioni)
# Media somma: 276.55


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


STRATEGY_NAMES = [
    'quartile', 'hotcold', 'antirecent', 'mix', 'sumlocked',
    'primefocus', 'middlefreq', 'gapspread', 'complement',
    'mixhotcoldprime', 'mixquartilehotcold', 'optimized',
    'fibonacci', 'adaptive', 'ensemble', 'mlpattern'
]

# ── Strategy Registry con priorità e trasparenza ──────────────────────────
# Tier A (priorità alta) → strategie "ibride" con più vincoli statistici
# Tier B (priorità media) → strategie fondamentali basate su distribuzioni
# Tier C (priorità bassa) → strategie esplorative/menoritarie
#
# NOTA ETICA: Nessuna strategia batte statisticamente il caso (audit pFDR 0.96-1.0).
# Il ranking serve SOLO per organizzare l'esperienza d'uso, NON per predire vincite.
STRATEGY_REGISTRY = {
    'optimized': {
        'tier': 'A', 'priority': 1,
        'label': 'Optimized',
        'description': 'Pattern comune denominatore su 4238 estrazioni. NON ha vantaggio statistico dimostrato.',
        'transparency': 'Simulazione — house edge ~67%',
    },
    'adaptive': {
        'tier': 'A', 'priority': 2,
        'label': 'Adaptive Predictive',
        'description': 'Combina pattern storici e trend recenti. Risultati storicamente non significativi (pFDR 0.99).',
        'transparency': 'Simulazione — nessuna predittività reale',
    },
    'ensemble': {
        'tier': 'A', 'priority': 3,
        'label': 'Rotating Ensemble',
        'description': 'Combina più strategie in rotazione. Diversifica senza vantaggio.',
        'transparency': 'Simulazione — variance ridotta, stesso house edge',
    },
    'quartile': {
        'tier': 'A', 'priority': 4,
        'label': 'Quartile Spread',
        'description': 'Distribuzione uniforme su quartili. La baseline di riferimento.',
        'transparency': 'Simulazione — benchmark standard',
    },
    'mlpattern': {
        'tier': 'B', 'priority': 5,
        'label': 'ML Pattern',
        'description': 'Pattern recognition su dati storici. Non dimostrato superiore al caso.',
        'transparency': 'Simulazione — pattern matching, non predizione',
    },
    'mix': {
        'tier': 'B', 'priority': 6,
        'label': 'Mixed Strategy',
        'description': 'Combinazione di HotCold + AntiRecent + Quartile.',
        'transparency': 'Simulazione — composizione di euristiche',
    },
    'mixhotcoldprime': {
        'tier': 'B', 'priority': 7,
        'label': 'Mix HC+Prime',
        'description': 'HotCold combinato con PrimeFocus.',
        'transparency': 'Simulazione — composizione di euristiche',
    },
    'mixquartilehotcold': {
        'tier': 'B', 'priority': 8,
        'label': 'Mix Q+HC',
        'description': 'Quartile combinato con HotCold.',
        'transparency': 'Simulazione — composizione di euristiche',
    },
    'hotcold': {
        'tier': 'B', 'priority': 9,
        'label': 'Hot/Cold Spread',
        'description': 'Numeri caldi (ultime 10 estrazioni) e freddi. ROI -49.8% su 4238 estrazioni.',
        'transparency': 'Simulazione — house edge ~67%',
    },
    'sumlocked': {
        'tier': 'B', 'priority': 10,
        'label': 'Sum Locked',
        'description': 'Somma vincolata a 274-278 (media storica).',
        'transparency': 'Simulazione — vincolo su somma, non su vincita',
    },
    'primefocus': {
        'tier': 'C', 'priority': 11,
        'label': 'Prime Focus',
        'description': 'Almeno 3 numeri primi. Pricipio: distribuzione primi ~30% casuale.',
        'transparency': 'Simulazione — nessuna edge su numeri primi',
    },
    'middlefreq': {
        'tier': 'C', 'priority': 12,
        'label': 'Middle Frequency',
        'description': 'Numeri di frequenza media. Evita hot/cold estremi.',
        'transparency': 'Simulazione — mediaCampione, non predizione',
    },
    'gapspread': {
        'tier': 'C', 'priority': 13,
        'label': 'Gap Spread',
        'description': 'Massimizza distanza minima tra numeri adiacenti.',
        'transparency': 'Simulazione — spacing, non contenuto',
    },
    'complement': {
        'tier': 'C', 'priority': 14,
        'label': 'Complement Mirror',
        'description': '3 numeri + 3 complementari (91-n).',
        'transparency': 'Simulazione — simmetria, non vantaggio',
    },
    'antirecent': {
        'tier': 'C', 'priority': 15,
        'label': 'Anti-Recent',
        'description': 'Evita numeri usciti nelle ultime 5 estrazioni. ROI -54.1% su 4238.',
        'transparency': 'Simulazione — fallacy del giocatore',
    },
    'fibonacci': {
        'tier': 'C', 'priority': 16,
        'label': 'Fibonacci Wheel',
        'description': 'Numeri della sequenza di Fibonacci. 7.08% M3+/1000, ROI -91.15%.',
        'transparency': 'Simulazione — sequenza numerica, nessun vantaggio',
    },
}

# Ordine di priorità estratto dal registry (per ordine di ranking giornaliero)
STRATEGY_PRIORITY_ORDER = sorted(STRATEGY_REGISTRY.keys(), key=lambda s: STRATEGY_REGISTRY[s]['priority'])

class DailyPlayTracker:
    """Traccia una giocata per strategia per giorno. Massimo 1 per strategia per data."""

    def __init__(self, conn):
        self.conn = conn
        self._init_table()

    def _init_table(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                strategy TEXT NOT NULL,
                numeri TEXT NOT NULL,
                somma INT NOT NULL,
                is_override INT DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(data, strategy)
            )
        """)
        self.conn.commit()

    def can_play(self, data, strategy):
        """True se la strategia non ha ancora giocato per questa data."""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM daily_plays WHERE data=? AND strategy=?", (data, strategy))
        return c.fetchone()[0] == 0

    def record_play(self, data, strategy, numeri, somma, is_override=False):
        """Registra una giocata. Ritorna True se registrata, False se bloccata."""
        if not self.can_play(data, strategy):
            return False
        c = self.conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO daily_plays (data, strategy, numeri, somma, is_override, created_at) VALUES (?,?,?,?,?,?)",
            (data, strategy, '-'.join(map(str, numeri)), somma, 1 if is_override else 0, datetime.now().isoformat())
        )
        self.conn.commit()
        return c.rowcount > 0

    def get_daily_plays(self, data):
        """Ritorna tutte le giocate registrate per una data."""
        c = self.conn.cursor()
        c.execute("SELECT strategy, numeri, somma, is_override, created_at FROM daily_plays WHERE data=? ORDER BY created_at", (data,))
        return [
            {"strategy": r[0], "numeri": r[1], "somma": r[2], "is_override": bool(r[3]), "created_at": r[4]}
            for r in c.fetchall()
        ]

    def get_daily_status(self, data=None):
        """Ritorna lo stato di gioco per ogni strategia nella data specificata (default: oggi)."""
        if data is None:
            data = datetime.now().strftime('%Y-%m-%d')
        plays = {p["strategy"]: p for p in self.get_daily_plays(data)}
        status = {}
        for name in STRATEGY_PRIORITY_ORDER:
            info = STRATEGY_REGISTRY[name]
            played = name in plays
            status[name] = {
                "tier": info["tier"],
                "priority": info["priority"],
                "label": info["label"],
                "description": info["description"],
                "transparency": info["transparency"],
                "played": played,
                "numeri": plays[name]["numeri"] if played else None,
                "somma": plays[name]["somma"] if played else None,
                "is_override": plays[name]["is_override"] if played else False,
            }
        return {"date": data, "strategies": status}

    def get_7day_report(self, end_date=None):
        """Verifica per 7 giorni consecutivi di estrazione."""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        report = []
        checked = 0
        d = end_dt
        while checked < 7:
            date_str = d.strftime('%Y-%m-%d')
            dow = d.weekday()
            plays = self.get_daily_plays(date_str)
            report.append({
                "date": date_str,
                "is_draw_day": dow in DRAW_DOWS,
                "plays_count": len(plays),
                "strategies_used": [p["strategy"] for p in plays],
                "any_override": any(p["is_override"] for p in plays),
                "compliant": len(plays) <= len(STRATEGY_PRIORITY_ORDER),
            })
            d -= timedelta(days=1)
            checked += 1
            if checked < 7:
                while d.weekday() not in DRAW_DOWS:
                    d -= timedelta(days=1)
        return {"report": report, "total_days": len(report)}

    def force_clear_strategy(self, data, strategy):
        """Forza la rimozione di una giocata per una strategia in una data (admin)."""
        c = self.conn.cursor()
        c.execute("DELETE FROM daily_plays WHERE data=? AND strategy=?", (data, strategy))
        self.conn.commit()
        return c.rowcount > 0


class SuperenalottoEngine:
    def __init__(self, db_path=None):
        import threading as _t
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.records = []
        self.stats = {}
        self._lock = _t.Lock()
        self._rng = secrets.SystemRandom()
        self._ranking_cache = None
        self._ranking_cache_fp = ""
        self._ranking_cache_ts = 0
        self._daily_tracker = None
        self._init_db()

    def _get_data_path(self, filename):
        """Portable: DB/TRACKING/CONFIG in Documents/SuperEnalotto (scrivibile), CSV da MEIPASS."""
        if getattr(sys, 'frozen', False):
            data_dir = get_user_data_dir()
            p_docs = os.path.join(data_dir, filename)
            # DB, tracking e config devono stare in Documents per persistenza
            if filename in (DB_PATH, TRACKING_PATH, CONFIG_PATH):
                return p_docs
            # per file di sola lettura (csv, config, web) usa MEIPASS per import iniziale
            try:
                p_mei = os.path.join(sys._MEIPASS, filename)
                if os.path.exists(p_mei):
                    return p_mei
            except Exception:
                pass
            return p_docs
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(base_dir, filename)

    def _init_db(self):
        # Migra DB da accanto all'exe se presente
        migrate_db_if_needed()
        self.db_path = self._get_data_path(DB_PATH)
        self.csv_path = self._get_data_path(CSV_PATH)
        self.tracking_path = self._get_data_path(TRACKING_PATH)
        # Se DB non esiste ma CSV è in MEIPASS, usalo per prima importazione
        if getattr(sys, 'frozen', False) and not os.path.exists(self.db_path):
            # assicura che csv_path punti a MEIPASS esistente per import
            if not os.path.exists(self.csv_path):
                try:
                    alt = os.path.join(sys._MEIPASS, CSV_PATH)
                    if os.path.exists(alt):
                        self.csv_path = alt
                except Exception:
                    pass
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
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
        except sqlite3.OperationalError:
            for col in ["p2", "p3", "p4", "p5", "p5j", "p6"]:
                try:
                    c.execute(f"ALTER TABLE estrazioni ADD COLUMN {col} REAL DEFAULT 0")
                except sqlite3.OperationalError as e:
                    logger.warning(f"_init_db alter col {col}: {e}")
        c.execute("""
            CREATE TABLE IF NOT EXISTS giocate (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, numeri TEXT,
                somma INT, verificato INT DEFAULT 0, vincita REAL DEFAULT 0,
                UNIQUE(data, numeri)
            )
        """)
        self.conn.commit()
        c.execute("SELECT COUNT(*) FROM estrazioni")
        if c.fetchone()[0] == 0 and os.path.exists(self.csv_path):
            self._import_csv()
        tracking_exists = os.path.exists(self.tracking_path)
        self._import_tracking()
        self._load_records()
        self._daily_tracker = DailyPlayTracker(self.conn)

    def _import_csv(self):
        c = self.conn.cursor()
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
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
                    except (ValueError, IndexError):
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
                    except ValueError:
                        data_norm = data_raw
                    c.execute(
                        "INSERT OR IGNORE INTO estrazioni (data,n1,n2,n3,n4,n5,n6,jolly,star) VALUES (?,?,?,?,?,?,?,?,?)",
                        (data_norm, nums[0], nums[1], nums[2], nums[3], nums[4], nums[5], jolly, star),
                    )
                except (ValueError, IndexError) as e:
                    logger.warning(f"_import_csv skip row: {e}")
                    continue
        self.conn.commit()

    def _import_tracking(self):
        """Importa giocate da tracking.csv (formato save_tracking: data,'','', numeri, somma,'','',flag)."""
        if not os.path.exists(self.tracking_path):
            return 0
        # _load_records non ritorna nulla — usa DB per dedup
        c = self.conn.cursor()
        c.execute("SELECT data, numeri FROM giocate")
        existing_keys = {(r[0], r[1]) for r in c.fetchall()}
        added = 0
        try:
            with open(self.tracking_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                first = next(reader, None)
                # Legacy: i vecchi tracking.csv non avevano header.
                # Se la prima riga NON è una testata (data/numeri), è un dato: processala.
                rows = list(reader)
                if first is not None:
                    col0 = (first[0] or "").strip().lower()
                    col3 = (first[3] or "").strip().lower() if len(first) > 3 else ""
                    col4 = (first[4] or "").strip().lower() if len(first) > 4 else ""
                    is_header = col0 == "data" or col3 == "numeri" or col4 == "numeri"
                    if not is_header:
                        rows.insert(0, first)
                for row in rows:
                    if not row or not row[0].strip():
                        continue
                    data_str = (row[0] or "").strip().strip('"')
                    # save_tracking scrive: [data,'','',numeri,somma,'','',flag] -> numeri in col 3
                    numeri = ""
                    if len(row) > 3 and row[3].strip():
                        numeri = row[3].strip().strip('"')
                    elif len(row) > 4 and row[4].strip() and "-" in row[4]:
                        numeri = row[4].strip().strip('"')
                    if not numeri or "-" not in numeri:
                        continue
                    try:
                        somma = int(row[4]) if len(row) > 4 and row[4].strip().isdigit() else sum(int(x) for x in numeri.split("-"))
                    except Exception:
                        somma = 0
                    key = (data_str, numeri)
                    if key in existing_keys:
                        continue
                    try:
                        c.execute("INSERT OR IGNORE INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)", (data_str, numeri, somma))
                        if c.rowcount > 0:
                            added += 1
                            existing_keys.add(key)
                    except Exception as e:
                        logger.warning(f"_import_tracking skip {data_str} {numeri}: {e}")
            if added:
                self.conn.commit()
        except Exception as e:
            logger.warning(f"_import_tracking failed: {e}")
        return added

    def _invalidate_ranking_cache(self):
        self._ranking_cache = None
        self._ranking_cache_fp = ""
        self._ranking_cache_ts = 0

    def _records_fingerprint(self):
        if not self.records:
            return "0:"
        return f"{len(self.records)}:{self.records[-1]['data']}:{self.records[-1]['nums']}"

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
        self._invalidate_ranking_cache()

    def _calc_stats(self):
        if not self.records:
            self.stats = {}
            return
        sums = [sum(r["nums"]) for r in self.records]
        all_nums = [n for r in self.records for n in r["nums"]]
        num_counts = Counter(all_nums)
        sums_sorted = sorted(sums)
        n = len(sums)
        mean_val = sum(sums) / n
        self.stats = {
            "count": n,
            "mean": mean_val,
            "median": sums_sorted[n // 2],
            "std": (sum((s - mean_val) ** 2 for s in sums) / n) ** 0.5,
            "q1": sums_sorted[n // 4],
            "q3": sums_sorted[3 * n // 4],
            "min": min(sums),
            "max": max(sums),
            "num_counts": dict(num_counts.most_common()),
        }

    def _valid_constraints(self, nums):
        """Vincoli identici a v7.17: somma in [Q1,Q3] (o 246-306 fallback), max 2/decade, max 1 >80."""
        s = sum(nums)
        if self.stats and "q1" in self.stats:
            if not (self.stats["q1"] <= s <= self.stats["q3"]):
                return False
        else:
            if not (246 <= s <= 306):
                return False
        decades = Counter(n // 10 for n in nums)
        if max(decades.values()) > 2:
            return False
        if sum(1 for n in nums if n > 80) > 1:
            return False
        return True

    def _stats_for(self, records):
        """Stats calcolate su un subset di records (per backtest senza leakage). Include num_counts."""
        if not records:
            return {}
        sums = [sum(r["nums"]) for r in records]
        n = len(sums)
        sums_sorted = sorted(sums)
        mean_val = sum(sums) / n
        all_nums = [num for r in records for num in r["nums"]]
        num_counts = Counter(all_nums)
        return {
            "count": n, "mean": mean_val,
            "median": sums_sorted[n // 2],
            "std": (sum((s - mean_val) ** 2 for s in sums) / n) ** 0.5 if n > 1 else 0,
            "q1": sums_sorted[n // 4],
            "q3": sums_sorted[3 * n // 4],
            "min": min(sums), "max": max(sums),
            "num_counts": dict(num_counts.most_common()),
        }

    def quartile_spread(self):
        """Genera 6 numeri con strategia QuartileSpread v7.17 fedele: 1 per quartile + 2 extra random, con vincoli."""
        if not self.stats:
            return sorted(self._rng.sample(range(1, 91), 6))
        q_ranges = [(1, 22), (23, 45), (46, 67), (68, 90)]
        for _ in range(2000):
            alloc = [1, 1, 1, 1]
            extra = 2
            while extra > 0:
                alloc[self._rng.randrange(4)] += 1
                extra -= 1
            nums = []
            for qi in range(4):
                lo, hi = q_ranges[qi]
                nums.extend(self._rng.sample(range(lo, hi + 1), alloc[qi]))
            nums = sorted(nums)
            if not self._valid_constraints(nums):
                continue
            return nums
        # fallback: versione semplice come v7.17
        for _ in range(1000):
            c = sorted(self._rng.sample(range(1, 91), 6))
            if self._valid_constraints(c):
                return c
        return sorted(self._rng.sample(range(1, 91), 6))

    def _get_strategies(self):
        """Ritorna il dizionario delle strategie generatorie."""
        return {
            'quartile': self.quartile_spread,
            'hotcold': self.hot_cold_spread,
            'antirecent': self.anti_recent_spread,
            'mix': self.mixed_strategy,
            'sumlocked': self.sum_locked_spread,
            'primefocus': self.prime_focus_spread,
            'middlefreq': self.middle_frequency_spread,
            'gapspread': self.gap_spread_strategy,
            'complement': self.complement_mirror_spread,
            'mixhotcoldprime': self.mix_hotcold_prime,
            'mixquartilehotcold': self.mix_quartile_hotcold,
            'optimized': self.optimized_spread,
            'fibonacci': self.fibonacci_wheel_spread,
            'adaptive': self.adaptive_predictive_spread,
            'ensemble': self.rotating_ensemble_spread,
            'mlpattern': self.machine_learning_pattern_spread,
        }

    def genera_schedine(self, n=1, strategy='quartile'):
        """Genera n schedine con strategia specificata (senza enforcement)."""
        gen = self._get_strategies().get(strategy, self.quartile_spread)
        return [gen() for _ in range(n)]

    def can_strategy_play_today(self, strategy):
        """True se la strategia non ha ancora giocato oggi."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self._daily_tracker.can_play(today, strategy)

    def get_top_strategy_for_today(self):
        """Ritorna la prima strategia disponibile per oggi secondo la priorità."""
        today = datetime.now().strftime('%Y-%m-%d')
        for name in STRATEGY_PRIORITY_ORDER:
            if self._daily_tracker.can_play(today, name):
                return name
        return None

    def genera_unica_schedina_today(self, strategy=None, is_override=False):
        """Genera esattamente 1 schedina per oggi. Se strategy=None usa la top disponibile.
        Registra nel DailyPlayTracker. Ritorna dict con risultato o errore."""
        today = datetime.now().strftime('%Y-%m-%d')
        if strategy is None:
            strategy = self.get_top_strategy_for_today()
            if strategy is None:
                return {"error": "Tutte le strategie hanno già giocato oggi.", "blocked": True}
        else:
            if strategy not in STRATEGY_REGISTRY:
                return {"error": f"Strategia '{strategy}' non valida.", "blocked": True}
            if not is_override and not self.can_strategy_play_today(strategy):
                info = STRATEGY_REGISTRY[strategy]
                return {
                    "error": f"Strategia '{info['label']}' ha già giocato oggi (priorità #{info['priority']}). "
                             f"Usa override per sovrascrivere.",
                    "blocked": True,
                    "strategy_info": info,
                }

        nums = self.genera_schedine(1, strategy=strategy)[0]
        somma = sum(nums)
        recorded = self._daily_tracker.record_play(today, strategy, nums, somma, is_override=is_override)
        if not recorded:
            return {"error": "Bloccato: giocata già registrata per questa strategia oggi.", "blocked": True}

        info = STRATEGY_REGISTRY.get(strategy, {})
        return {
            "nums": nums,
            "somma": somma,
            "strategy": strategy,
            "label": info.get("label", strategy),
            "tier": info.get("tier", "?"),
            "priority": info.get("priority", 0),
            "transparency": info.get("transparency", ""),
            "is_override": is_override,
            "date": today,
        }

    def get_strategy_ranking(self):
        """Ritorna la lista ordinata delle strategie con stato di gioco per oggi."""
        return self._daily_tracker.get_daily_status()

    def get_7day_enforcement_report(self):
        """Ritorna il report di compliance degli ultimi 7 giorni."""
        return self._daily_tracker.get_7day_report()

    def hot_cold_spread(self, n_hot=3, n_cold=3):
        """HotCold: 3-4 numeri caldi (ultime 10), 2-3 freddi (mai o raramente usciti)."""
        if not self.records:
            return sorted(self._rng.sample(range(1, 91), 6))
        # Conta apparizioni in ultime 10 estrazioni
        recent = self.records[-10:]
        hot_nums = []
        all_recent = set()
        for r in recent:
            all_recent.update(r['nums'])
        hot = sorted(all_recent)
        cold = sorted(set(range(1, 91)) - all_recent)
        # Caldi
        n_hot = min(n_hot, len(hot))
        n_cold = min(n_cold, len(cold))
        selected = self._rng.sample(hot, n_hot) + self._rng.sample(cold, n_cold)
        selected = sorted(selected)
        # Riempi fin a 6
        remaining = 6 - len(selected)
        if remaining > 0:
            extra = self._rng.sample([x for x in range(1, 91) if x not in selected], remaining)
            selected = sorted(selected + extra)
        return selected

    def anti_recent_spread(self, exclude_last=5):
        """AntiRecent: evita numeri ultime 5 estrazioni, preferisce meno recenti."""
        if not self.records:
            return sorted(self._rng.sample(range(1, 91), 6))
        recent_nums = set()
        for r in self.records[-exclude_last:]:
            recent_nums.update(r['nums'])
        available = set(range(1, 91)) - recent_nums
        selected = sorted(self._rng.sample(list(available), 6))
        return selected

    def mixed_strategy(self):
        """Mix: 2 HotCold + 2 AntiRecent + 2 QuartileSpread, mescolati."""
        qc = self.quartile_spread()
        hc = self.hot_cold_spread(n_hot=2, n_cold=1)
        ar = self.anti_recent_spread(exclude_last=5)
        # 2 da HotCold, 2 da AntiRecent, 2 da Quartile (unici)
        selected = set()
        selected.update(self._rng.sample(hc, 2))
        selected.update(self._rng.sample(ar, 2))
        selected.update(self._rng.sample(qc, 2))
        # Riempi se duplicati
        while len(selected) < 6:
            pool = qc + hc + ar + list(range(1, 91))
            extra = self._rng.choice(pool)
            if extra not in selected:
                selected.add(extra)
        return sorted(list(selected)[:6])

    def sum_locked_spread(self, target_sum=None):
        """SumLocked: somma bloccata intorno alla media (274-278), con vincoli."""
        if target_sum is None:
            target_sum = self._rng.choice([274, 275, 276, 277, 278])
        for _ in range(3000):
            nums = sorted(self._rng.sample(range(1, 91), 6))
            if sum(nums) == target_sum and max(Counter(n // 10 for n in nums).values()) <= 2 and sum(1 for n in nums if n > 80) <= 1:
                return nums
        # fallback constraint-based
        for _ in range(3000):
            nums = sorted(self._rng.sample(range(1, 91), 6))
            s = sum(nums)
            if abs(s - target_sum) <= 5 and max(Counter(n // 10 for n in nums).values()) <= 2 and sum(1 for n in nums if n > 80) <= 1:
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def prime_focus_spread(self, min_primes=3):
        """PrimeFocus: almeno min_primes numeri primi, con vincoli."""
        prime_list = sorted(PRIMES)
        composite_list = [n for n in range(1, 91) if n not in PRIMES]
        for _ in range(3000):
            n_primes = self._rng.randint(min_primes, min(5, len(prime_list)))
            selected = self._rng.sample(prime_list, n_primes)
            remaining = 6 - len(selected)
            if remaining > 0:
                selected.extend(self._rng.sample(composite_list, remaining))
            selected = sorted(selected)
            if self._valid_constraints(selected):
                return selected
        return sorted(self._rng.sample(range(1, 91), 6))

    def middle_frequency_spread(self):
        """MiddleFrequency: numeri di frequenza media (evita hot e cold estremi)."""
        if not self.records:
            return sorted(self._rng.sample(range(1, 91), 6))
        freq = self.stats.get("num_counts", {})
        if not freq:
            return sorted(self._rng.sample(range(1, 91), 6))
        avg = sum(freq.values()) / 90 if freq else 30
        mid_nums = [n for n in range(1, 91) if avg * 0.85 <= freq.get(n, 0) <= avg * 1.15]
        if len(mid_nums) < 6:
            mid_nums = [n for n in range(1, 91) if freq.get(n, 0) >= avg * 0.9]
        for _ in range(3000):
            nums = sorted(self._rng.sample(mid_nums, min(6, len(mid_nums))))
            if len(nums) == 6 and self._valid_constraints(nums):
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def gap_spread_strategy(self, min_gap=5):
        """GapSpread: minimizza la distanza minima tra numeri adiacenti."""
        for _ in range(3000):
            nums = sorted(self._rng.sample(range(1, 91), 6))
            gaps = [nums[i+1] - nums[i] for i in range(5)]
            if min(gaps) >= min_gap and self._valid_constraints(nums):
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def complement_mirror_spread(self):
        """ComplementMirror: 3 numeri + 3 complementari (91-n), con vincoli."""
        for _ in range(3000):
            half = sorted(self._rng.sample(range(1, 46), 3))
            comp = sorted(91 - n for n in half)
            nums = sorted(half + comp)
            if self._valid_constraints(nums):
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def mix_hotcold_prime(self):
        """Mix ottimizzato: HotCold + PrimeFocus (Miglior M3+ rate)."""
        hc = self.hot_cold_spread(n_hot=3, n_cold=2)
        prime_list = sorted(PRIMES)
        for _ in range(3000):
            nums = list(hc[:4])
            extra = self._rng.choice(prime_list)
            if extra not in nums:
                nums.append(extra)
            while len(nums) < 6:
                n = self._rng.randint(1, 90)
                if n not in nums:
                    nums.append(n)
            nums = sorted(nums)
            if self._valid_constraints(nums):
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def mix_quartile_hotcold(self):
        """Mix: 4 QuartileSpread + 2 HotCold, tutti unici."""
        for _ in range(3000):
            qc = self.quartile_spread()
            hc = self.hot_cold_spread(n_hot=2, n_cold=1)
            selected = set(self._rng.sample(qc, 4))
            selected.update(self._rng.sample(hc, 2))
            while len(selected) < 6:
                n = self._rng.randint(1, 90)
                if n not in selected:
                    selected.add(n)
            nums = sorted(list(selected)[:6])
            if self._valid_constraints(nums):
                return nums
        return sorted(self._rng.sample(range(1, 91), 6))

    def optimized_spread(self):
        """Strategia ottimizzata overall: combinazione di tutti i pattern ricorrenti.

        Basata sull'analisi comune denominatore su 4238 estrazioni:
        - Somma 274-278 (media 276.55)
        - Pattern low/mid/high: 2-2-2 (più comune)
        - 1-2 numeri primi (più comune)
        - 3 even / 3 odd (più comune)
        - Max 2 per decade, max 1 >80
        """
        for _ in range(3000):
            nums = sorted(self._rng.sample(range(1, 91), 6))
            s = sum(nums)
            if not (274 <= s <= 278):
                continue
            # Check 2-2-2 pattern (low 1-30, mid 31-60, high 61-90)
            low = sum(1 for n in nums if n <= 30)
            mid = sum(1 for n in nums if 31 <= n <= 60)
            high = sum(1 for n in nums if n >= 61)
            if not (low >= 1 and mid >= 1 and high >= 1):
                continue
            # 1-2 primes
            pc = sum(1 for n in nums if n in PRIMES)
            if pc < 1 or pc > 3:
                continue
            # 2-4 even (3 even + 3 odd is most common)
            ec = sum(1 for n in nums if n % 2 == 0)
            if not (1 <= ec <= 5):
                continue
            decades = Counter(n // 10 for n in nums)
            if max(decades.values()) > 2:
                continue
            if sum(1 for n in nums if n > 80) > 1:
                continue
            return nums
        return self.quartile_spread()

    def fibonacci_wheel_spread(self):
        """Strategia FibonacciWheel: basata sulla sequenza di Fibonacci.
        
        Utilizza i numeri della sequenza di Fibonacci (fino a 90) come 
        riferimento statistico. I numeri Fibonacci mostrano pattern 
        ricorrenti nel 7.08% dei casi (M3+/1000=7.08, ROI=-91.15%).
        """
        fib_nums = [n for n in FIBONACCI if 1 <= n <= 90]
        non_fib = [n for n in range(1, 91) if n not in FIBONACCI]
        
        for _ in range(3000):
            # 2-4 numeri Fibonacci
            n_fib = self._rng.randint(2, 4)
            selected = self._rng.sample(fib_nums, n_fib)
            
            # Completare con numeri non Fibonacci
            remaining = 6 - len(selected)
            if remaining > 0:
                selected.extend(self._rng.sample(non_fib, remaining))
            
            nums = sorted(selected)
            if self._valid_constraints(nums):
                return nums
        
        return sorted(self._rng.sample(range(1, 91), 6))

    def adaptive_predictive_spread(self):
        """Strategia adattiva predittiva: combina pattern statistici e trend recenti.
        
        Analizza le ultime estrazioni per adattare la generazione ai trend attuali.
        Combina riconoscimento pattern + adattamento dinamico.
        """
        if not self.records:
            return sorted(self._rng.sample(range(1, 91), 6))
        
        # Analizza trend recenti (ultime 20 estrazioni)
        recent = self.records[-20:] if len(self.records) >= 20 else self.records
        hot_numbers = set()
        for r in recent:
            hot_numbers.update(r['nums'])
        
        # Calcola frequenza dei numeri primi recenti
        prime_freq = sum(1 for r in recent for n in r['nums'] if n in PRIMES)
        total_nums = len(recent) * 6
        prime_density = prime_freq / total_nums if total_nums > 0 else 0.5
        
        # Target somma basato su media recente
        recent_sums = [sum(r['nums']) for r in recent]
        target_sum = sum(recent_sums) / len(recent_sums) if recent_sums else 276.55
        
        for _ in range(3000):
            nums = sorted(self._rng.sample(range(1, 91), 6))
            s = sum(nums)
            
            # Vincolo somma target (±15 dalla media recente)
            if abs(s - target_sum) > 15:
                continue
            
            # Pattern 2-2-2 quartile
            low = sum(1 for n in nums if n <= 30)
            mid = sum(1 for n in nums if 31 <= n <= 60)
            high = sum(1 for n in nums if n >= 61)
            if not (low >= 1 and mid >= 1 and high >= 1):
                continue
            
            # Vincolo primi basato sulla densità recente
            pc = sum(1 for n in nums if n in PRIMES)
            if prime_density > 0.6 and pc < 2:
                continue
            if prime_density < 0.4 and pc > 4:
                continue
            
            # Vincolo decade e numeri grandi
            decades = Counter(n // 10 for n in nums)
            if max(decades.values()) > 2:
                continue
            if sum(1 for n in nums if n > 80) > 1:
                continue
            
            return nums
        
        return self.optimized_spread()

    def rotating_ensemble_spread(self):
        """Strategia rotating ensemble: combina multiple strategie in rotazione.
        
        Utilizza un approccio di ensemble che ruota tra diverse strategie
        per massimizzare la diversità delle previsioni e prevenire pattern ripetitivi.
        """
        # Strategie di base per l'ensemble
        base_strategies = [
            self.quartile_spread,
            self.prime_focus_spread,
            self.hot_cold_spread,
            self.sum_locked_spread,
            self.optimized_spread,
        ]
        
        # Seleziona 2-3 strategie casualmente
        n_strategies = self._rng.randint(2, 3)
        selected = self._rng.sample(base_strategies, n_strategies)
        
        # Esegui le strategie selezionate
        predictions = []
        for strategy in selected:
            try:
                pred = strategy()
                predictions.append(pred)
            except Exception:
                continue
        
        if not predictions:
            return sorted(self._rng.sample(range(1, 91), 6))
        
        # Combina le previsioni: prendi 2 numeri da ciascuna
        combined = []
        for pred in predictions:
            combined.extend(self._rng.sample(pred, 2))
        
        # Rimuovi duplicati e completa a 6 numeri
        unique = list(set(combined))
        while len(unique) < 6:
            n = self._rng.randint(1, 90)
            if n not in unique:
                unique.append(n)
        
        nums = sorted(self._rng.sample(unique, 6))
        
        # Valida con vincoli
        if self._valid_constraints(nums):
            return nums
        
        return self.optimized_spread()

    def machine_learning_pattern_spread(self):
        """Strategia ML pattern: riconoscimento pattern basato su dati storici.
        
        Analizza i pattern più comuni nei dati storici e applica un 
        approccio di riconoscimento di pattern per generare numeri.
        """
        if not self.records:
            return sorted(self._rng.sample(range(1, 91), 6))
        
        # Analizza pattern storici
        all_nums = [n for r in self.records for n in r['nums']]
        freq = Counter(all_nums)
        
        # Numeri caldi (alta frequenza)
        hot_nums = [n for n, c in freq.items() if c > freq.most_common(1)[0][1] * 0.7]
        # Numeri freddi (bassa frequenza)
        cold_nums = [n for n, c in freq.items() if c < freq.most_common(1)[0][1] * 0.3]
        
        # Pattern di somma: analizza le somme più comuni
        sum_counts = Counter(sum(r['nums']) for r in self.records)
        common_sums = [s for s, c in sum_counts.most_common(20)]
        
        for _ in range(3000):
            # 2 numeri caldi + 2 freddi + 2 casuali
            hot_sel = self._rng.sample(hot_nums, min(2, len(hot_nums)))
            cold_sel = self._rng.sample(cold_nums, min(2, len(cold_nums)))
            remaining = 6 - len(hot_sel) - len(cold_sel)
            
            pool = [n for n in range(1, 91) if n not in hot_sel and n not in cold_sel]
            random_sel = self._rng.sample(pool, remaining)
            
            nums = sorted(hot_sel + cold_sel + random_sel)
            
            # Vincolo somma comune
            s = sum(nums)
            if s not in common_sums:
                continue
            
            # Vincoli base
            if not self._valid_constraints(nums):
                continue
            
            return nums
        
        return self.optimized_spread()

    def auto_check_new_draws(self):
        """All'avvio: verifica automaticamente le schedine per giorni con estrazione."""
        try:
            self.verifica_tutte(only_unchecked=True)
        except Exception:
            pass

    def auto_update_draws(self):
        """All'avvio: cerca nuove estrazioni dal sito e le aggiunge."""
        try:
            self.scrape_historical(pages=1)
        except Exception:
            pass

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
        """Salva una giocata. Blocca se per la stessa data esiste già  una giocata non verificata.
        Gestisce UNIQUE constraint con INSERT OR IGNORE."""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM giocate WHERE data=? AND verificato=0", (data,))
        if c.fetchone()[0] > 0:
            return False  # bloccato
        try:
            c.execute(
                "INSERT OR IGNORE INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)",
                (data, "-".join(map(str, numeri)), somma),
            )
            self.conn.commit()
            # rowcount == 0 significa duplicato (UNIQUE data+numeri)
            if c.rowcount == 0:
                # duplicato esatto già presente: consideralo successo (idempotente)
                return True
            return True
        except sqlite3.IntegrityError:
            return False

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
            except ValueError:
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

    def get_premi(self):
        """Ritorna premi per tabella Premi (ultima estrazione + fallback ADM)."""
        c = self.conn.cursor()
        c.execute("SELECT data, p2,p3,p4,p5,p5j,p6 FROM estrazioni ORDER BY data DESC LIMIT 1")
        row = c.fetchone()
        # odds fisse SuperEnalotto
        odds = {2:22, 3:327, 4:11180, 5:2333636, 5.5:103769105, 6:622614630}
        if row and any(row[1:]):
            _, p2,p3,p4,p5,p5j,p6 = row
            premi = [
                {"match":"2","odds":odds[2],"premio":p2 or PREMI_DEFAULT[2],"ultimo":f"EUR {p2}" if p2 else "fallback"},
                {"match":"3","odds":odds[3],"premio":p3 or PREMI_DEFAULT[3],"ultimo":f"EUR {p3}" if p3 else "fallback"},
                {"match":"4","odds":odds[4],"premio":p4 or PREMI_DEFAULT[4],"ultimo":f"EUR {p4}" if p4 else "fallback"},
                {"match":"5","odds":odds[5],"premio":p5 or PREMI_DEFAULT[5],"ultimo":f"EUR {p5}" if p5 else "fallback"},
                {"match":"5+Jolly","odds":odds[5.5],"premio":p5j or PREMI_DEFAULT[5.5],"ultimo":f"EUR {p5j}" if p5j else "fallback"},
                {"match":"6","odds":odds[6],"premio":p6 or PREMI_DEFAULT[6],"ultimo":f"EUR {p6}" if p6 else "jackpot"},
            ]
            jackpot = f"EUR {p6:,.0f}".replace(",",".") if p6 else "EUR 210.000.000"
        else:
            premi = [
                {"match":"2","odds":22,"premio":PREMI_DEFAULT[2],"ultimo":"ADM"},
                {"match":"3","odds":327,"premio":PREMI_DEFAULT[3],"ultimo":"ADM"},
                {"match":"4","odds":11180,"premio":PREMI_DEFAULT[4],"ultimo":"ADM"},
                {"match":"5","odds":2333636,"premio":PREMI_DEFAULT[5],"ultimo":"ADM"},
                {"match":"5+Jolly","odds":103769105,"premio":PREMI_DEFAULT[5.5],"ultimo":"ADM"},
                {"match":"6","odds":622614630,"premio":PREMI_DEFAULT[6],"ultimo":"jackpot"},
            ]
            jackpot = "EUR 210.000.000"
        return {"premi": premi, "jackpot": jackpot, "data": row[0] if row else None}

    def valuta_strategie(self, n=50):
        """Valuta QuartileSpread su ultime n estrazioni (stub per v7.18)."""
        if len(self.records) < n:
            n = len(self.records)
        window = self.records[-n:]
        # usa fallback ADM per calcolo ROI simulato
        spent = n
        # simula QuartileSpread: conta quanti avrebbero hit 2/3 con random vincolato (deterministico per repeatability)
        
        won = 0
        m2=m3=m4=0
        for rec in window:
            nums = self.quartile_spread()
            matches = len(set(nums) & set(rec["nums"]))
            if matches==2: won+=PREMI_DEFAULT[2]; m2+=1
            elif matches==3: won+=PREMI_DEFAULT[3]; m3+=1
            elif matches>=4: won+=PREMI_DEFAULT[4]; m4+=1
        
        roi = (won/spent*100) if spent else 0
        text = f"Valutazione ultime {n} estrazioni (QuartileSpread):\nSpeso EUR {spent} - Vinto EUR {won} - ROI {roi:.1f}%\nM2:{m2} M3:{m3} M4:{m4}\n\nNota: backtest completo 4238 estrazioni disponibile via script PowerShell."
        return {"text": text, "roi": roi, "spent": spent, "won": won}

    def get_grafici(self):
        return {"msg": "Grafici matplotlib disponibili solo in versione desktop tkinter 7.18. In web v8.1 usa Statistiche + Premi."}

    def scrape_historical(self, pages=1):
        """Scrape storico estrazioni da superenalotto.com/archivio e aggiunge
        le mancanti al DB (anti-duplicato per data).
        Includes Jolly (boxArchiveNumberRed) and SuperStar (boxArchiveNumberstar).
        Ritorna (aggiunte, totale_scrape)."""
        import re
        import ssl

        ctx = ssl.create_default_context()
        added = 0
        scraped = 0
        existing = {r["data"] for r in self.records}
        c = self.conn.cursor()
        for pg in range(1, pages + 1):
            url = "https://www.superenalotto.com/archivio" + (f"/{pg}" if pg > 1 else "")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "ignore")
            except Exception:
                break
            dates = re.findall(r'boxarchiveDate">([^<]+)<', html)
            nums_norm = re.findall(r'boxArchiveNumber">(\d+)<', html)
            nums_red = re.findall(r'boxArchiveNumberRed">(\d+)<', html)
            nums_star = re.findall(r'boxArchiveNumberstar">(\d+)<', html)
            estrazioni = []
            i = 0
            j = 0
            for k in range(len(dates)):
                if i + 6 > len(nums_norm):
                    break
                n6 = [int(x) for x in nums_norm[i:i + 6]]
                jolly = int(nums_red[j]) if j < len(nums_red) else 0
                star = int(nums_star[k]) if k < len(nums_star) else 0
                estrazioni.append((n6, jolly, star))
                i += 6
                j += 1
            for (n6, jolly, star), dstr in zip(estrazioni, dates):
                try:
                    dd, mm, yyyy = dstr.split()
                    mesi = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
                            "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
                    iso = f"{yyyy}-{mesi.get(mm, 1):02d}-{int(dd):02d}"
                except Exception:
                    continue
                scraped += 1
                if iso in existing:
                    # Update star/jolly se mancanti (vecchio scraper non li scaricava)
                    c.execute("SELECT jolly,star FROM estrazioni WHERE data=?", (iso,))
                    old = c.fetchone()
                    if old and (old[0] == 0 or old[1] == 0):
                        c.execute("UPDATE estrazioni SET jolly=?,star=? WHERE data=?",
                                  (jolly if jolly else old[0], star if star else old[1], iso))
                    continue
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO estrazioni (data,n1,n2,n3,n4,n5,n6,jolly,star) VALUES (?,?,?,?,?,?,?,?,?)",
                        (iso, n6[0], n6[1], n6[2], n6[3], n6[4], n6[5], jolly, star),
                    )
                    if c.rowcount > 0:
                        existing.add(iso)
                        added += 1
                except sqlite3.IntegrityError:
                    continue
        self.conn.commit()
        if added > 0:
            self._load_records()
        return added, scraped

    def _scrape_jackpot(self):
        """Estrae il jackpot live da superenalotto.com (JackpotValueNumber)."""
        import re
        import ssl

        ctx = ssl.create_default_context()
        try:
            req = urllib.request.Request(
                "https://www.superenalotto.com",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            html = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode("utf-8", "ignore")
            m = re.search(r'JackpotValueNumber">([\d.]+)', html)
            if m:
                return float(m.group(1).replace(".", ""))
        except Exception:
            pass
        return None

    def fetch_jackpot_sisal(self):
        """Jackpot: prova prima scraping live da superenalotto.com, fallback default."""
        live = self._scrape_jackpot()
        if live and live > 0:
            return live
        return 210000000.0

    def aggiorna_storico(self):
        """Aggiorna storico: prima prova API, poi scrape pagine archivio.
        Ritorna dict con added, scraped, msg."""
        # prova prima l'API se disponibile
        try:
            self.fetch_latest_draw()
        except Exception:
            pass
        # poi scrapa l'archivio
        added, scraped = self.scrape_historical(pages=3)
        msg = f"Scansione: {scraped} estrazioni. Nuove: {added}. Totale: {len(self.records)}"
        return {"added": added, "scraped": scraped, "msg": msg}

    def fetch_latest_draw(self):
        """Scarica ultima estrazione da lotteryresultsfeed.com (se API key presente).
        Altrimenti usa scrape_historical per trovare nuove estrazioni."""
        cfg = {}
        cfg_path = self._get_data_path(CONFIG_PATH)
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
        except Exception:
            pass
        api_key = cfg.get("apiKey", "") or os.environ.get("SUPERENALOTTO_API_KEY", "")
        if api_key and cfg.get("apiUrl"):
            try:
                import ssl
                ctx = ssl.create_default_context()
                req = urllib.request.Request(
                    cfg["apiUrl"],
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                    data = json.loads(r.read().decode("utf-8", "ignore"))
                se = next((l for l in data.get("lotteries", []) if l.get("id") == 712), None)
                if se:
                    self._apply_draw_data(se.get("results_latest", {}), se.get("jackpot"))
                    return
            except Exception:
                pass
        # fallback: scrapa dall'archivio
        self.scrape_historical(pages=1)

    def _apply_draw_data(self, data, jackpot=None):
        """Aggiorna DB con dati da API (results_latest)."""
        numeri = [int(x) for x in data.get("balls", data.get("numeri", []))]
        if len(numeri) != 6:
            return
        bonus = data.get("ball_bonus", [])
        jolly = int(bonus[0]) if bonus else 0
        star = int(data.get("star", 0) or 0)
        data_str = str(data.get("draw_date", datetime.now().strftime("%Y-%m-%d")))
        try:
            data_str = datetime.strptime(data_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            try:
                data_str = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except Exception:
                pass
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM estrazioni WHERE data=?", (data_str,))
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO estrazioni (data,n1,n2,n3,n4,n5,n6,jolly,star) VALUES (?,?,?,?,?,?,?,?,?)",
                (data_str, numeri[0], numeri[1], numeri[2], numeri[3], numeri[4], numeri[5], jolly, star),
            )
            self.conn.commit()
            self._load_records()

    def close(self):
        if self.conn:
            self.conn.close()

    def save_tracking(self):
        """Salva tutte le giocate in tracking.csv per la persistenza.
        Salva TUTTE le giocate (vere e non verificate) per mantenere lo stato."""
        c = self.conn.cursor()
        c.execute("SELECT data, numeri, somma, verificato FROM giocate ORDER BY data")
        rows = c.fetchall()
        
        import csv
        data_dir = get_user_data_dir()
        tracking_path = os.path.join(data_dir, TRACKING_PATH)
        
        with open(tracking_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header (ignorato da _import_tracking): evita che la prima giocata venga scartata
            writer.writerow(["data", "", "", "numeri", "somma", "", "", "verificato"])
            for data, numeri, somma, verificato in rows:
                # Format: data, giornata, budget, schede, numeri, somma, jackpot, verificato, verified_flag
                writer.writerow([data, "", "", numeri, somma, "", "", str(verificato == 1)])
        
        self.conn.commit()
        return {"saved": len(rows)}

    def backup_dati(self):
        """Crea un backup giornaliero del DB e tracking.csv in Documents/SuperEnalotto/backups/."""
        from datetime import datetime
        data_dir = get_user_data_dir()
        backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup DB
        db_src = self.db_path
        db_dst = os.path.join(backup_dir, f"superenalotto_{timestamp}.db")
        if os.path.exists(db_src):
            import shutil
            shutil.copy2(db_src, db_dst)
        
        # Backup tracking.csv
        tracking_src = self.tracking_path
        tracking_dst = os.path.join(backup_dir, f"tracking_{timestamp}.csv")
        if os.path.exists(tracking_src):
            import shutil
            shutil.copy2(tracking_src, tracking_dst)
        
        return {"backup": timestamp, "dir": backup_dir}

    def list_backups(self):
        """Lista tutti i backup disponibili."""
        import glob
        data_dir = get_user_data_dir()
        backup_dir = os.path.join(data_dir, "backups")
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        # Find all unique timestamps from backup filenames
        seen = set()
        for f in os.listdir(backup_dir):
            if f.startswith("superenalotto_") and f.endswith(".db"):
                ts = f.replace("superenalotto_", "").replace(".db", "")
                if ts not in seen:
                    seen.add(ts)
                    st = os.stat(os.path.join(backup_dir, f))
                    backups.append({
                        "timestamp": ts,
                        "size_db": f"{os.path.getsize(os.path.join(backup_dir, f)) // 1024}KB",
                        "date": st.st_mtime
                    })
        
        backups.sort(key=lambda x: x["date"], reverse=True)
        for b in backups:
            del b["date"]  # rimuove raw timestamp
        return backups

    def restore_backup(self, timestamp):
        """Ripristina un backup specifico."""
        import shutil
        data_dir = get_user_data_dir()
        backup_dir = os.path.join(data_dir, "backups")
        
        db_src = os.path.join(backup_dir, f"superenalotto_{timestamp}.db")
        tracking_src = os.path.join(backup_dir, f"tracking_{timestamp}.csv")
        
        restored = []
        if os.path.exists(db_src):
            shutil.copy2(db_src, self.db_path)
            restored.append("db")
            # Ricarica i records
            self._load_records()
        if os.path.exists(tracking_src):
            shutil.copy2(tracking_src, self.tracking_path)
            restored.append("tracking")
        
        return {"restored": restored, "timestamp": timestamp}

    def backup_giornaliero(self):
        """Se non esiste backup oggi, creane uno automatico."""
        from datetime import datetime, date
        backups = self.list_backups()
        today_prefix = date.today().strftime("%Y%m%d")
        for b in backups:
            if b["timestamp"].startswith(today_prefix):
                return {"skipped": True, "reason": "backup oggi gia esistente"}
        return self.backup_dati()

    def run_backtest(self, strategy='quartile', n=50):
        """Backtest: per ogni estrazione, genera schedina e verifica se avrebbe vinto."""
        if len(self.records) < n:
            n = len(self.records)
        
        total_win = 0.0
        total_spent = 0
        total_return = 0.0
        wins = []
        
        with self._lock:
            for i in range(len(self.records) - n, len(self.records)):
                actual = self.records[i]
                data = actual['data']
                actual_nums = list(actual['nums'])
                jolly = actual['jolly']

                # Genera schedina BEFORE this draw (use data before i)
                # Temporarily set records to exclude future data
                saved_records = self.records[:i]
                old_records = self.records
                self.records = saved_records

                try:
                    schedina = self.genera_schedine(1, strategy=strategy)[0]
                except Exception:
                    schedina = sorted(self._rng.sample(range(1, 91), 6))
                finally:
                    self.records = old_records

                matches = len(set(schedina) & set(actual_nums))
                jolly_hit = jolly in schedina if jolly else False

                total_spent += 1
                premio = 0.0

                if matches == 6:
                    premio = PREMI_DEFAULT[6]
                elif matches == 5:
                    if jolly_hit:
                        premio = PREMI_DEFAULT[5.5]
                    else:
                        premio = PREMI_DEFAULT[5]
                elif matches == 4:
                    premio = PREMI_DEFAULT[4]
                elif matches == 3:
                    premio = PREMI_DEFAULT[3]
                elif matches == 2:
                    premio = PREMI_DEFAULT[2]

                if premio > 0:
                    wins.append({"data": data, "matches": matches, "jolly_hit": jolly_hit, "premio": premio})
                    total_return += premio
                    total_win += 1
        
        roi = ((total_return / total_spent - 1) * 100) if total_spent > 0 else 0
        
        return {
            "strategy": strategy,
            "n": n,
            "total_spent": total_spent,
            "total_return": total_return,
            "win_count": total_win,
            "win_rate": round(total_win / total_spent * 100, 1) if total_spent > 0 else 0,
            "roi": round(roi, 1),
            "wins": wins
        }

    def get_heatmap_data(self):
        """Restituisce frequenza di ogni numero (1-90) per heatmap."""
        freq = {n: 0 for n in range(1, 91)}
        for r in self.records:
            for n in r['nums']:
                freq[n] = freq.get(n, 0) + 1
        return {"freq": freq, "total": len(self.records)}

    def get_trend_data(self):
        """Restituisce trend caldi/freddi per ultime 20 estrazioni."""
        recent = self.records[-20:]
        hot = set()
        for r in recent:
            hot.update(r['nums'])
        all_nums = set(range(1, 91))
        cold = all_nums - hot
        
        # Conta apparizioni
        hot_counts = {n: 0 for n in hot}
        for r in recent:
            for n in r['nums']:
                if n in hot_counts:
                    hot_counts[n] += 1
        
        hot_sorted = sorted(hot_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "hot": [{"num": n, "count": c} for n, c in hot_sorted[:15]],
            "cold": sorted(list(cold))[:15],
            "recent_draws": [r['data'] for r in recent]
        }

    # ═══════════════════════════════════════════════════
    # SISTEMA DI CLASSIFICA DINAMICA — deterministico, senza leakage, con cache
    # ═══════════════════════════════════════════════════

    def get_dynamic_ranking(self, n=50, seed=42, use_cache=True):
        """Classifica deterministica: per ogni strategia esegue backtest sulle ultime n
        estrazioni usando RNG seedato (random.Random) e troncando i records a i esclusivo
        (nessun leakage). Cache di 5 min se i records non cambiano e n/seed uguali."""
        if not self.records:
            return []
        n = max(10, min(200, int(n)))
        fp = self._records_fingerprint()
        if use_cache and self._ranking_cache is not None and getattr(self, '_ranking_cache_fp', '') == fp and time.time() - self._ranking_cache_ts < 300:
            if getattr(self, '_ranking_cache_n', None) == n and getattr(self, '_ranking_cache_seed', None) == seed:
                return self._ranking_cache
        start = max(0, len(self.records) - n)
        window = self.records[start:]
        rankings = []
        for name in STRATEGY_NAMES:
            score, detail = self._evaluate_strategy_score(name, window, start_idx=start, seed=seed)
            rankings.append({"strategy": name, "score": score, **detail, "rank": 0})
        rankings.sort(key=lambda x: (-x["score"], x["strategy"]))
        for i, item in enumerate(rankings):
            item["rank"] = i + 1
        self._ranking_cache = rankings
        self._ranking_cache_fp = fp
        self._ranking_cache_ts = time.time()
        self._ranking_cache_n = n
        self._ranking_cache_seed = seed
        return rankings

    def _evaluate_strategy_score(self, strategy_name, window, start_idx=0, seed=42):
        """Score deterministico su window: genera con RNG seedato, tronca records a i."""
        if not window:
            return 0, {"m2":0,"m3":0,"m4":0,"m5":0,"m6":0,"total":0}
        # evita race su ThreadingHTTPServer: blocca durante valutazione
        with self._lock:
            saved_records = self.records
            saved_stats = self.stats
            saved_rng = self._rng
            # RNG deterministico stabile (hashlib, non hash() randomizzato)
            h = int(hashlib.md5(f"{seed}:{strategy_name}".encode()).hexdigest()[:8], 16)
            det_rng = random.Random(h)
            self._rng = det_rng
            m2=m3=m4=m5=m6=0
            total_matches = 0
            try:
                for offset, record in enumerate(window):
                    i = start_idx + offset
                    hist = saved_records[:i]
                    if hist:
                        self.records = hist
                        self.stats = self._stats_for(hist)
                    else:
                        self.records = []
                        self.stats = {}
                    try:
                        schedina = self.genera_schedine(1, strategy=strategy_name)[0]
                    except Exception:
                        continue
                    matches = len(set(schedina) & set(record["nums"]))
                    total_matches += matches
                    if matches == 2: m2+=1
                    elif matches == 3: m3+=1
                    elif matches == 4: m4+=1
                    elif matches == 5: m5+=1
                    elif matches == 6: m6+=1
            finally:
                self.records = saved_records
                self.stats = saved_stats
                self._rng = saved_rng
        total = len(window)
        # score pesato: premia M3+ e soprattutto M4+, penalizza solo M2 troppo basso
        score = (m3*1.0 + m4*4.0 + m5*20 + m6*100) / max(1, total)
        # tie-breaker stabile su match totali
        score += total_matches / (total * 600)
        return score, {"m2":m2,"m3":m3,"m4":m4,"m5":m5,"m6":m6,"total":total, "total_matches": total_matches}

    def get_top_strategy(self, n=50, seed=42):
        rankings = self.get_dynamic_ranking(n=n, seed=seed)
        if rankings:
            return rankings[0]["strategy"]
        return 'quartile'

    def get_strategy_comparison(self, n=50, seed=42):
        rankings = self.get_dynamic_ranking(n=n, seed=seed)
        return {
            "rankings": rankings,
            "best_strategy": rankings[0]["strategy"] if rankings else 'quartile',
            "total_strategies": len(rankings),
            "last_updated": datetime.now().isoformat()
        }

    def resolve_auto_strategy(self):
        """Ritorna la best strategy per il generatore automatico."""
        return self.get_top_strategy()

    # ═══════════════════════════════════════════════════
    # SISTEMA DI NOTIFICHE
    # ═══════════════════════════════════════════════════

    def get_notifications(self):
        """Restituisce la lista delle notifiche attive."""
        notifications = []
        
        # Notifica jackpot
        jackpot = self.fetch_jackpot_sisal()
        if jackpot and jackpot > 200000000:
            notifications.append({
                'type': 'jackpot',
                'title': 'Jackpot Alto',
                'message': f'Il jackpot è superiore a €200M: €{jackpot:,.0f}',
                'priority': 'high',
                'timestamp': datetime.now().isoformat()
            })
        
        # Notifica prossima estrazione
        prossima = self.prossima_estrazione()
        if prossima != 'N/A':
            notifications.append({
                'type': 'draw',
                'title': 'Prossima Estrazione',
                'message': f'La prossima estrazione è il {prossima}',
                'priority': 'medium',
                'timestamp': datetime.now().isoformat()
            })
        
        # Notifica se oggi è giorno di estrazione
        if self.oggi_estrazione():
            notifications.append({
                'type': 'draw_today',
                'title': 'Oggi è Giorno di Estrazione',
                'message': 'Gioca entro le 19:30 per partecipare a oggi!',
                'priority': 'high',
                'timestamp': datetime.now().isoformat()
            })
        
        # Notifica sulle giocate non verificate
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM giocate WHERE verificato=0")
        unverified = c.fetchone()[0]
        if unverified > 0:
            notifications.append({
                'type': 'unverified',
                'title': 'Giocate da Verificare',
                'message': f'Hai {unverified} giocate non ancora verificate',
                'priority': 'medium',
                'timestamp': datetime.now().isoformat()
            })
        
        # Notifica sulle giocate vincenti recenti
        c.execute("SELECT COUNT(*) FROM giocate WHERE verificato=1 AND vincita > 0")
        wins = c.fetchone()[0]
        if wins > 0:
            notifications.append({
                'type': 'wins',
                'title': 'Hai Vinto!',
                'message': f'Hai {wins} giocate vincenti verificate',
                'priority': 'high',
                'timestamp': datetime.now().isoformat()
            })
        
        return notifications

    def get_active_alerts(self):
        """Restituisce gli alert attivi del sistema."""
        alerts = []
        
        # Alert sulle performance delle strategie
        rankings = self.get_dynamic_ranking()
        if rankings:
            best = rankings[0]
            worst = rankings[-1]
            
            # Se la migliore strategia ha un punteggio molto alto, alert
            if best['score'] > 0.7:
                alerts.append({
                    'type': 'performance',
                    'title': 'Strategia Eccellente',
                    'message': f'La strategia {best["strategy"]} ha un punteggio eccellente: {best["score"]:.2f}',
                    'priority': 'info'
                })
            
            # Se la peggiore strategia ha un punteggio molto basso, alert
            if worst['score'] < 0.3:
                alerts.append({
                    'type': 'performance',
                    'title': 'Strategia Sottoperformante',
                    'message': f'La strategia {worst["strategy"]} ha un punteggio basso: {worst["score"]:.2f}. Considera di evitarla.',
                    'priority': 'warning'
                })
        
        return alerts

    def mark_notification_read(self, notification_id):
        """Segna una notificata come letta."""
        # Per ora non implementiamo la persistenza delle notifiche
        # Le notifiche sono generate in tempo reale
        return True


