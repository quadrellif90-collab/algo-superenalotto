"""
SuperEnalotto Engine - Logica di gioco, strategie, verifica.
"""

import csv
import json
import os
import random
import shutil
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


def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


class SuperenalottoEngine:
    def __init__(self, db_path=None):
        import threading as _t
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.records = []
        self.stats = {}
        self._lock = _t.Lock()
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
                    print(f"[WARN] _init_db alter col {col}: {e}")
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
                    print(f"[WARN] _import_csv skip row: {e}")
                    continue
        self.conn.commit()

    def _import_tracking(self):
        c = self.conn.cursor()
        if not os.path.exists(self.tracking_path):
            return
        added = 0
        try:
            # Try utf-8-sig first, fallback to utf-16, utf-8
            content = None
            for enc in ("utf-8-sig", "utf-16", "utf-8"):
                try:
                    with open(self.tracking_path, "r", encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            if content is None:
                print(f"[ERROR] _import_tracking: cannot decode {self.tracking_path}")
                return
            from io import StringIO
            reader = csv.reader(StringIO(content))
            header = next(reader, None)
            for row in reader:
                if not row:
                    continue
                data = (row[0] or '').strip().strip('"') if row[0] else ''
                nums = ''
                if len(row) > 4:
                    nums = (row[4] or '').strip().strip('"')
                somma = 0
                if len(row) > 5 and row[5]:
                    try:
                        somma = int(row[5].strip().strip('"'))
                    except ValueError:
                        somma = 0
                if not data or not nums:
                    continue
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO giocate (data,numeri,somma,verificato,vincita) VALUES (?,?,?,0,0.0)",
                        (data, nums, somma),
                    )
                    added += 1
                except sqlite3.IntegrityError as e:
                    print(f"[WARN] _import_tracking skip row: {e}")
                    continue
        except Exception as e:
            print(f"[ERROR] _import_tracking: {e}")
        self.conn.commit()
        print(f"[TRACKING] Imported {added} giocate da {self.tracking_path}")

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

    def quartile_spread(self):
        """Genera 6 numeri con strategia QuartileSpread v7.17 fedele: 1 per quartile + 2 extra random, con vincoli."""
        if not self.stats:
            return sorted(random.sample(range(1, 91), 6))
        q_ranges = [(1, 22), (23, 45), (46, 67), (68, 90)]
        for _ in range(2000):
            alloc = [1, 1, 1, 1]
            extra = 2
            while extra > 0:
                alloc[random.randrange(4)] += 1
                extra -= 1
            nums = []
            for qi in range(4):
                lo, hi = q_ranges[qi]
                nums.extend(random.sample(range(lo, hi + 1), alloc[qi]))
            nums = sorted(nums)
            if not self._valid_constraints(nums):
                continue
            return nums
        # fallback: versione semplice come v7.17
        for _ in range(1000):
            c = sorted(random.sample(range(1, 91), 6))
            if self._valid_constraints(c):
                return c
        return sorted(random.sample(range(1, 91), 6))

    def genera_schedine(self, n=1):
        """Genera n schedine con QuartileSpread."""
        return [self.quartile_spread() for _ in range(n)]

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
        """Salva una giocata. Blocca se per la stessa data esiste già una giocata non verificata.
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
        random.seed(42)
        won = 0
        m2=m3=m4=0
        for rec in window:
            nums = self.quartile_spread()
            matches = len(set(nums) & set(rec["nums"]))
            if matches==2: won+=PREMI_DEFAULT[2]; m2+=1
            elif matches==3: won+=PREMI_DEFAULT[3]; m3+=1
            elif matches>=4: won+=PREMI_DEFAULT[4]; m4+=1
        random.seed()
        roi = (won/spent*100) if spent else 0
        text = f"Valutazione ultime {n} estrazioni (QuartileSpread):\nSpeso EUR {spent} - Vinto EUR {won} - ROI {roi:.1f}%\nM2:{m2} M3:{m3} M4:{m4}\n\nNota: backtest completo 7226 estrazioni disponibile via script PowerShell."
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
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
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
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
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
        api_key = cfg.get("apiKey", "")
        if api_key and api_key != "[REDACTED]" and cfg.get("apiUrl"):
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
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
        """Salva tutte le giocate non verificate in tracking.csv per la persistenza."""
        c = self.conn.cursor()
        c.execute("SELECT data, numeri, somma, verificato FROM giocate WHERE verificato=0")
        rows = c.fetchall()
        
        if not rows:
            return {"saved": 0}
        
        import csv
        data_dir = get_user_data_dir()
        tracking_path = os.path.join(data_dir, TRACKING_PATH)
        
        with open(tracking_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for data, numeri, somma, verificato in rows:
                writer.writerow([data, "", "", numeri, somma, "", str(verificato == 1)])
        
        self.conn.commit()
        return {"saved": len(rows)}
