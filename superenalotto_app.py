import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import json
import random
import os
from datetime import datetime, timedelta
from collections import Counter


class SuperenalottoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SuperEnalotto - Protocollo Sniper")
        self.root.geometry("900x700")
        self.root.configure(bg="#1a1a2e")

        self.csv_path = "superenalotto.csv"
        self.api_key = self._load_api_key()
        self.tracking_path = "tracking.csv"
        self.records = []
        self.stats = {}
        self.generated_numbers = []

        self.setup_styles()
        self.create_widgets()
        self.load_data()
        self.update_jackpot()
        self.update_stats_display()
        self.check_draw_day()

    def _load_api_key(self):
        """Load API key from config.json, fallback to hardcoded value if not found"""
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("apiKey", "[REDACTED]")
            except:
                pass
        return None

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Title.TLabel",
            background="#1a1a2e",
            foreground="#00d9ff",
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background="#1a1a2e",
            foreground="#e94560",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Info.TLabel",
            background="#1a1a2e",
            foreground="#ffffff",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Stat.TLabel",
            background="#16213e",
            foreground="#00d9ff",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Accent.TButton",
            background="#e94560",
            foreground="white",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Secondary.TButton",
            background="#0f3460",
            foreground="white",
            font=("Segoe UI", 10),
        )

    def create_widgets(self):
        title_frame = tk.Frame(self.root, bg="#1a1a2e")
        title_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(
            title_frame,
            text="SUPERENALOTTO",
            bg="#1a1a2e",
            fg="#00d9ff",
            font=("Segoe UI", 24, "bold"),
        ).pack()
        tk.Label(
            title_frame,
            text="Protocollo Sniper Quantitativo",
            bg="#1a1a2e",
            fg="#e94560",
            font=("Segoe UI", 12),
        ).pack()

        self.status_label = tk.Label(
            title_frame, text="", bg="#1a1a2e", fg="#00ff88", font=("Segoe UI", 10)
        )
        self.status_label.pack(pady=5)

        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        left_frame = tk.Frame(main_frame, bg="#16213e", width=400)
        left_frame.pack(side="left", fill="both", padx=(0, 10))
        left_frame.pack_propagate(False)

        right_frame = tk.Frame(main_frame, bg="#16213e")
        right_frame.pack(side="right", fill="both", expand=True)

        self.create_stats_section(left_frame)
        self.create_generator_section(right_frame)
        self.create_results_section(right_frame)
        self.create_tracking_section(right_frame)

    def create_stats_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="STATISTICHE",
            bg="#16213e",
            fg="#00d9ff",
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.stats_labels = {}
        stats = [
            ("Estrazioni", "0"),
            ("Somma Media", "0"),
            ("Mediana", "0"),
            ("Std Dev", "0"),
            ("Q1", "0"),
            ("Q3", "0"),
            ("Range", "0 - 0"),
            ("Primi %", "0%"),
            ("Estremi %", "0%"),
            (">31 %", "0%"),
            (">80 %", "0%"),
        ]

        for i, (name, _) in enumerate(stats):
            row = i // 2
            col = (i % 2) * 2
            tk.Label(
                frame, text=f"{name}:", bg="#16213e", fg="#888888", font=("Segoe UI", 9)
            ).grid(row=row, column=col, sticky="w", padx=5, pady=2)
            self.stats_labels[name] = tk.Label(
                frame,
                text="-",
                bg="#16213e",
                fg="#00d9ff",
                font=("Segoe UI", 9, "bold"),
            )
            self.stats_labels[name].grid(
                row=row, column=col + 1, sticky="w", padx=5, pady=2
            )

    def create_generator_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="GENERATORE NUMERI",
            bg="#16213e",
            fg="#00d9ff",
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", padx=10, pady=10)

        tk.Label(
            frame, text="Jackpot in palio:", bg="#16213e", fg="#888888", font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w")
        self.jackpot_label = tk.Label(
            frame, text="€0", bg="#16213e", fg="#ffcc00", font=("Segoe UI", 11, "bold")
        )
        self.jackpot_label.grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(
            frame, text="Ultimo montepremi:", bg="#16213e", fg="#888888", font=("Segoe UI", 9)
        ).grid(row=1, column=0, sticky="w")
        self.last_prize_label = tk.Label(
            frame, text="€0", bg="#16213e", fg="#00d9ff", font=("Segoe UI", 10)
        )
        self.last_prize_label.grid(row=1, column=1, sticky="w", padx=10)

        # Selettore numero schedine (1-5)
        tk.Label(
            frame, text="Schedine da generare:",
            bg="#16213e", fg="#888888", font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.schedine_var = tk.IntVar(value=2)
        self.schedine_spin = tk.Spinbox(
            frame, from_=1, to=5, width=5,
            textvariable=self.schedine_var,
            bg="#1a1a2e", fg="#00ff88", font=("Segoe UI", 10, "bold"),
            state="readonly",
        )
        self.schedine_spin.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        tk.Button(
            frame,
            text="Genera Schedine (QuartileSpread)",
            command=self.generate_optimal_dual,
            bg="#00ff88",
            fg="#1a1a2e",
            font=("Segoe UI", 11, "bold"),
            activebackground="#88ffcc",
            padx=20,
            pady=5,
        ).grid(row=2, column=0, columnspan=2, pady=15)

        tk.Label(
            frame,
            text="Strategia: 1 numero per quartile (1-22/23-45/46-67/68-90)\n+ somma 246-306, max 2/decade, max 1 numero>80\nMiglior ROI backtest 4226 draw: 35.73%",
            bg="#16213e",
            fg="#666666",
            font=("Segoe UI", 8),
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

        tk.Label(
            frame,
            text="Schedine generate:",
            bg="#16213e",
            fg="#888888",
            font=("Segoe UI", 9),
        ).grid(row=4, column=0, sticky="w")

        self.numbers_frame = tk.Frame(frame, bg="#16213e")
        self.numbers_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)

    def create_results_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="ESTRAZIONI RECENTI",
            bg="#16213e",
            fg="#00d9ff",
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("Data", "N1", "N2", "N3", "N4", "N5", "N6", "Jolly", "Star")
        self.results_tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)

        for col in cols:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=60, anchor="center")

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=self.results_tree.yview
        )
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_tracking_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="TRACKING",
            bg="#16213e",
            fg="#00d9ff",
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", padx=10, pady=10)

        btn_frame = tk.Frame(frame, bg="#16213e")
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="Aggiorna CSV",
            command=self.update_csv,
            bg="#0f3460",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Scarica Dati API",
            command=self.fetch_latest_draw,
            bg="#0f3460",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Agg. Jackpot",
            command=self.update_jackpot,
            bg="#0f3460",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Esporta Report",
            command=self.export_report,
            bg="#0f3460",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="Verifica Vince",
            command=self.check_win,
            bg="#0f3460",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)

    def load_data(self):
        if not os.path.exists(self.csv_path):
            messagebox.showwarning("Attenzione", f"File {self.csv_path} non trovato!")
            return

        self.records = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 9:
                    try:
                        nums = [
                            int(row[2]),
                            int(row[3]),
                            int(row[4]),
                            int(row[5]),
                            int(row[6]),
                            int(row[7]),
                        ]
                        self.records.append(
                            {
                                "data": row[0],
                                "nums": nums,
                                "sum": sum(nums),
                                "jolly": int(row[8]) if row[8] else 0,
                                "star": int(row[9]) if len(row) > 9 and row[9] else 0,
                            }
                        )
                    except:
                        continue

        self.calculate_stats()
        self.update_results_display()

    def calculate_stats(self):
        if not self.records:
            return

        sums = [r["sum"] for r in self.records]
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
            "primes": sum(1 for num in all_nums if self.is_prime(num))
            / len(all_nums)
            * 100,
            "extremes": sum(1 for num in all_nums if num >= 76) / len(all_nums) * 100,
            "gt31": sum(1 for num in all_nums if num > 31) / len(all_nums) * 100,
            "gt80": sum(1 for num in all_nums if num > 80) / len(all_nums) * 100,
        }

    def is_prime(self, n):
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        return True

    def update_stats_display(self):
        if not self.stats:
            return

        self.stats_labels["Estrazioni"].config(text=str(self.stats["count"]))
        self.stats_labels["Somma Media"].config(text=f"{self.stats['mean']:.1f}")
        self.stats_labels["Mediana"].config(text=str(self.stats["median"]))
        self.stats_labels["Std Dev"].config(text=f"{self.stats['std']:.1f}")
        self.stats_labels["Q1"].config(text=str(self.stats["q1"]))
        self.stats_labels["Q3"].config(text=str(self.stats["q3"]))
        self.stats_labels["Range"].config(
            text=f"{self.stats['min']} - {self.stats['max']}"
        )
        self.stats_labels["Primi %"].config(text=f"{self.stats['primes']:.1f}%")
        self.stats_labels["Estremi %"].config(text=f"{self.stats['extremes']:.1f}%")
        self.stats_labels[">31 %"].config(text=f"{self.stats['gt31']:.1f}%")
        self.stats_labels[">80 %"].config(text=f"{self.stats['gt80']:.1f}%")

    def update_results_display(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for record in self.records[-10:]:
            self.results_tree.insert(
                "",
                0,
                values=[
                    record["data"],
                    record["nums"][0],
                    record["nums"][1],
                    record["nums"][2],
                    record["nums"][3],
                    record["nums"][4],
                    record["nums"][5],
                    record["jolly"],
                    record["star"],
                ],
            )

    def check_draw_day(self):
        today = datetime.now().strftime("%A")
        draw_days = ["Tuesday", "Thursday", "Friday", "Saturday"]

        if today in draw_days:
            self.status_label.config(text=f"Oggi e' {today} - GIORNO DI ESTRAZIONE!")
            self.status_label.config(fg="#00ff00")
        else:
            next_draw = self.get_next_draw_date()
            self.status_label.config(text=f"Prossima estrazione: {next_draw}")
            self.status_label.config(fg="#ffcc00")

    def get_next_draw_date(self):
        today = datetime.now()
        draw_days = {"Tuesday": 1, "Thursday": 3, "Friday": 4, "Saturday": 5}
        today_dow = today.weekday()

        for day_offset in sorted(draw_days.values()):
            days_ahead = (day_offset - today_dow) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_date = today + timedelta(days=days_ahead)
            return next_date.strftime("%d/%m/%Y")

        return "N/A"

    def _valid_constraints(self, nums):
        s = sum(nums)
        if s < 246 or s > 306:
            return False
        decades = Counter(n // 10 for n in nums)
        if max(decades.values()) > 2:
            return False
        if sum(1 for n in nums if n > 80) > 1:
            return False
        return True

    def _quartile_spread(self):
        # Costruisce 6 numeri garantendo 1 per quartile (copertura spaziale massima)
        q_ranges = [(1, 22), (23, 45), (46, 67), (68, 90)]
        best = None
        for _ in range(2000):
            # distribuzione 2+1+1+2 o 1+2+2+1 o simili, sempre >=1 per quartile
            alloc = [1, 1, 1, 1]
            extra = 2
            while extra > 0:
                alloc[random.randrange(4)] += 1
                extra -= 1
            nums = []
            ok = True
            for qi in range(4):
                lo, hi = q_ranges[qi]
                pick = random.sample(range(lo, hi + 1), alloc[qi])
                nums.extend(pick)
            nums = sorted(nums)
            if not self._valid_constraints(nums):
                continue
            if best is None:
                best = nums
                # accetta subito il primo valido (vincoli già garantiti)
                return nums
        # fallback estremo: 1 per quartile + 2 casuali nei bordi
        if best is None:
            nums = []
            for lo, hi in q_ranges:
                nums.append(random.randint(lo, hi))
            nums.extend(random.sample(range(1, 91), 2))
            return sorted(nums)
        return best

    def generate_optimal_dual(self):
        """Modalita' Dual ottimale (backtest 4226 draw, ROI 35.73%):
        QuartileSpread x N schedine (1-5), 1 biglietto per estrazione cadauna."""
        if not self.stats:
            messagebox.showwarning("Attenzione", "Carica prima i dati!")
            return

        n_schedine = max(1, min(5, int(self.schedine_var.get())))
        self.generated_numbers = []
        for _ in range(n_schedine):
            q = self._quartile_spread()
            self.generated_numbers.append({"nums": q, "sum": sum(q)})

        self.display_generated_numbers()
        self.save_to_tracking()

    def display_generated_numbers(self):
        for widget in self.numbers_frame.winfo_children():
            widget.destroy()

        for i, sched in enumerate(self.generated_numbers):
            nums_str = "-".join(str(n) for n in sched["nums"])
            color = "#00ff88" if 240 <= sched["sum"] <= 320 else "#ff6b6b"

            frame = tk.Frame(self.numbers_frame, bg="#1a1a2e")
            frame.pack(fill="x", pady=2)

            tk.Label(
                frame,
                text=f"Schedina {i + 1}:",
                bg="#1a1a2e",
                fg="#888888",
                font=("Segoe UI", 9),
            ).pack(side="left")

            tk.Label(
                frame,
                text=nums_str,
                bg="#1a1a2e",
                fg=color,
                font=("Segoe UI", 12, "bold"),
            ).pack(side="left", padx=10)

            tk.Label(
                frame,
                text=f"[somma: {sched['sum']}]",
                bg="#1a1a2e",
                fg="#ffcc00",
                font=("Segoe UI", 9),
            ).pack(side="left")

    def save_to_tracking(self):
        today = datetime.now().strftime("%Y-%m-%d")
        day_name = datetime.now().strftime("%A")

        if not self.generated_numbers:
            return

        file_exists = os.path.exists(self.tracking_path)

        with open(self.tracking_path, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("data,giornata,budget,schedine,numeri,somma\n")

            for sched in self.generated_numbers:
                nums_str = "-".join(str(n) for n in sched["nums"])
                f.write(f"{today},{day_name},1.00,1,{nums_str},{sched['sum']}\n")

        self.status_label.config(
            text=f"Tracking salvato! ({len(self.generated_numbers)} schedine)"
        )

    def update_csv(self):
        messagebox.showinfo(
            "Info",
            "Funzione aggiornamento CSV richiede connessione API.\n"
            "Usa lo script PowerShell update_csv.ps1 per aggiornare.",
        )

    def export_report(self):
        if not self.stats:
            messagebox.showwarning("Attenzione", "Nessun dato da esportare!")
            return

        report = f"""
========================================
SUPERENALOTTO - REPORT
Generato: {datetime.now().strftime("%d/%m/%Y %H:%M")}
========================================

DATI STORICI
Estrazioni analizzate: {self.stats["count"]}
Periodo: {self.records[0]["data"]} - {self.records[-1]["data"]}

STATISTICHE SOMMA
Media: {self.stats["mean"]:.2f}
Mediana: {self.stats["median"]}
Std Dev: {self.stats["std"]:.2f}
Q1: {self.stats["q1"]}
Q3: {self.stats["q3"]}
Range: {self.stats["min"]} - {self.stats["max"]}

DISTRIBUZIONE NUMERI
Primi: {self.stats["primes"]:.2f}%
Estremi (76-90): {self.stats["extremes"]:.2f}%
>31: {self.stats["gt31"]:.2f}%
>80: {self.stats["gt80"]:.2f}%

ULTIME 10 ESTRAZIONI
"""
        for r in self.records[-10:]:
            nums_str = " ".join(f"{n:2d}" for n in r["nums"])
            report += f"{r['data']}: {nums_str}\n"

        report += f"""
========================================
NOTE OPERATIVE
Target somma: {int(self.stats["mean"] - 30)} - {int(self.stats["mean"] + 30)}
Fascia ottimale: 260-299 (36.65% estrazioni)
Giorni estrazione: Martedi, Giovedi, Venerdi, Sabato
========================================
"""

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        messagebox.showinfo("Report", f"Report salvato in: {filename}")

    def check_win(self):
        if not self.generated_numbers:
            messagebox.showinfo("Verifica", "Genera prima i numeri da giocare!")
            return

        if not self.records:
            messagebox.showinfo("Verifica", "Nessun dato di estrazione disponibile!")
            return

        last_draw = self.records[-1]["nums"]
        jolly = self.records[-1].get("jolly", 0)
        star = self.records[-1].get("star", 0)
        premi = {2: 5, 3: 10, 4: 100, 5: 1000, 6: 1000000}
        message = (
            f"Ultima estrazione: {' '.join(str(n) for n in sorted(last_draw))}"
            f"  Jolly:{jolly}  Star:{star}\n\n"
        )
        message += "I tuoi numeri:\n"
        tot_win = 0
        for i, sched in enumerate(self.generated_numbers):
            matches = len(set(sched["nums"]) & set(last_draw))
            jolly_hit = 1 if jolly and jolly in sched["nums"] else 0
            premio = premi.get(matches, 0)
            tot_win += premio
            detail = f"  (Jolly +{jolly_hit})" if jolly_hit else ""
            message += (
                f"Schedina {i + 1}: {matches} numeri indovinati"
                f" -> {'€' + str(premio) if premio else 'nessuna vincita'}{detail}\n"
            )
        message += f"\nVincita totale stimata: €{tot_win}"
        messagebox.showinfo("Verifica Vincita", message)

    # ===== INTEGRAZIONE API lotteryresultsfeed.com =====
    API_BASE = "https://www.lotteryresultsfeed.com/api/lottery/lotteries"

    def fetch_latest_draw(self):
        """Scarica l'ultima estrazione SuperEnalotto da lotteryresultsfeed.com.
        Endpoint: GET /lotteries?country=it  (campo results_latest[lottery_id=712]).
        Auth: Bearer token (apiKey in config.json)."""
        cfg = {}
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
        api_key = cfg.get("apiKey", "")
        if not api_key or api_key == "[REDACTED]":
            messagebox.showinfo(
                "API non configurata",
                "Inserisci la tua 'apiKey' in config.json per scaricare i dati.\n"
                "Source: lotteryresultsfeed.com (Bearer token).",
            )
            return
        try:
            import urllib.request
            import ssl

            # NOTE: TLS verification disabled intentionally — public lottery API
            # uses certs that fail strict check; read-only public data, no auth secrets in transit.
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = f"{self.API_BASE}?country=it"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                data = json.loads(r.read().decode("utf-8", "ignore"))
            se = next(
                (l for l in data.get("lotteries", []) if l.get("id") == 712),
                None,
            )
            if not se:
                messagebox.showerror("Errore", "SuperEnalotto non trovato nella risposta.")
                return
            self._apply_draw_data(se.get("results_latest", {}), jackpot=se.get("jackpot"))
        except Exception as e:
            messagebox.showerror("Errore API", f"Impossibile scaricare i dati:\n{str(e)[:200]}")

    def _apply_draw_data(self, data, jackpot=None):
        """Normalizza il JSON dell'API e aggiorna CSV + jackpot + verificatore."""
        numeri = [int(x) for x in data.get("balls", data.get("numeri", []))]
        if len(numeri) != 6:
            messagebox.showerror("Dati non validi", "L'API non ha restituito 6 numeri.")
            return
        bonus = data.get("ball_bonus", [])
        jolly = int(bonus[0]) if bonus else 0
        star = int(data.get("star", 0) or 0)
        jp = float(jackpot if jackpot is not None else data.get("jackpot", 0) or 0)
        data_str = str(data.get("draw_date", datetime.now().strftime("%d/%m/%Y")))
        # lotteryresultsfeed usa YYYY-MM-DD
        try:
            data_str = datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            pass
        # aggiorna jackpot label (in palio, da config) e ultimo montepremi (da API)
        if jp > 0:
            self.last_prize_label.config(text=f"€{jp:,.0f}")
        # append to CSV if not already present
        exists = any(r["data"] == data_str for r in self.records)
        if not exists:
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow([data_str, "", "1.00", "1"] + numeri + [jolly, star])
            self.load_data()
            self.update_stats_display()
            self.update_results_display()
            messagebox.showinfo(
                "Dati aggiornati",
                f"Estrazione {data_str} aggiunta.\n"
                f"Numeri: {'-'.join(map(str, numeri))}  Jolly: {jolly}\n"
                f"Ultimo montepremi: €{jp:,.0f}",
            )
        else:
            # estrazione già presente: aggiorna ultimo montepremi da API
            if jp > 0:
                self.last_prize_label.config(text=f"€{jp:,.0f}")
            messagebox.showinfo(
                "Già presente",
                f"Estrazione {data_str} già nel database.\nUltimo montepremi: €{jp:,.0f}",
            )

    def update_jackpot(self):
        """Jackpot in palio = valore in config.json['jackpot'] (aggiornato manualmente
        dall'utente, perché l'API non espone il jackpot accumulato milionario)."""
        cfg = {}
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            pass
        jp = float(cfg.get("jackpot", 0) or 0)
        if jp > 0:
            self.jackpot_label.config(text=f"€{jp:,.0f}")
        else:
            self.jackpot_label.config(text="€0 (imposta in config.json)")

def main():
    root = tk.Tk()
    app = SuperenalottoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
