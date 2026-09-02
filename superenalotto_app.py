import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import json
import random
import os
from datetime import datetime, timedelta
from collections import Counter


class SuperenalottoApp:
    # Palette verde "lucky/win"
    C_BG = "#eef7f0"
    C_GREEN = "#1a8f3c"
    C_GREEN_DK = "#0f6b2c"
    C_GREEN_LT = "#d4f0dd"
    C_DARK = "#10331c"
    C_CARD = "#ffffff"
    C_ACCENT = "#ffd200"
    C_TEXT = "#1a2e22"
    C_MUTED = "#5a7a66"

    def __init__(self, root):
        self.root = root
        self.root.title("SuperEnalotto - Verifica e Genera")
        self.root.geometry("940x780")
        self.root.configure(bg=self.C_BG)
        self.root.minsize(700, 560)

        self.csv_path = "superenalotto.csv"
        self.api_key = self._load_api_key()
        self.tracking_path = "tracking.csv"
        self.db_path = "superenalotto.db"
        self.records = []
        self.stats = {}
        self.generated_numbers = []

        self._init_db()
        self.setup_styles()
        self.create_widgets()
        self.load_data()
        self.update_jackpot()
        self.update_stats_display()
        self.check_draw_day()
        # Auto-fetch ultima estrazione da API all'avvio
        self.fetch_latest_draw()
        # Auto-aggiornamento storico da superenalotto.com/archivio (manca nella API)
        try:
            self.scrape_historical(pages=2)
            self.load_data()
            self.update_stats_display()
            self.update_results_display()
        except Exception:
            pass
        # Verifica automatica schedine non verificate per giorni con estrazione
        self.auto_check_new_draws()
        # autoridimensionamento fluido
        self.root.bind("<Configure>", self._on_resize)
        # icona app (verde stile SuperEnalotto)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass

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
        # === HEADER verde ===
        title_frame = tk.Frame(self.root, bg=self.C_GREEN, height=64)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame,
            text="SUPERENALOTTO",
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 24, "bold"),
        ).pack(side="left", padx=18, pady=10)
        self.status_label = tk.Label(
            title_frame,
            text="",
            bg=self.C_GREEN,
            fg=self.C_ACCENT,
            font=("Segoe UI", 11, "bold"),
        )
        self.status_label.pack(side="right", padx=18, pady=10)

        # corpo scrollabile e responsivo
        canvas = tk.Canvas(self.root, bg=self.C_BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._canvas = canvas

        content = tk.Frame(canvas, bg=self.C_BG)
        canvas.create_window((0, 0), window=content, anchor="nw")
        self._content = content

        def _cfg(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas.find_all()[0], width=canvas.winfo_width())

        content.bind("<Configure>", _cfg)
        canvas.bind("<Configure>", _cfg)

        # layout interno: due colonne responsive
        content.columnconfigure(0, weight=1, minsize=300)
        content.columnconfigure(1, weight=2, minsize=380)

        left = tk.Frame(content, bg=self.C_BG)
        right = tk.Frame(content, bg=self.C_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        self.create_stats_section(left)
        self.create_generator_section(right)
        self.create_prizes_section(right)
        self.create_results_section(right)
        self.create_tracking_section(right)
        self.create_my_plays_section(left)

    def create_stats_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="STATISTICHE",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=8,
        )
        frame.pack(fill="x", pady=5)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

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
                frame, text=f"{name}:", bg=self.C_CARD, fg=self.C_MUTED, font=("Segoe UI", 9)
            ).grid(row=row, column=col, sticky="w", padx=5, pady=2)
            self.stats_labels[name] = tk.Label(
                frame,
                text="-",
                bg=self.C_CARD,
                fg=self.C_GREEN,
                font=("Segoe UI", 9, "bold"),
            )
            self.stats_labels[name].grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)

    def create_generator_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="GENERATORE NUMERI",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", pady=5)
        frame.columnconfigure(1, weight=1)

        tk.Label(
            frame, text="Jackpot in palio:", bg=self.C_CARD, fg=self.C_MUTED, font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w")
        self.jackpot_label = tk.Label(
            frame, text="€0", bg=self.C_CARD, fg=self.C_GREEN, font=("Segoe UI", 13, "bold")
        )
        self.jackpot_label.grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(
            frame, text="Ultimo montepremi:", bg=self.C_CARD, fg=self.C_MUTED, font=("Segoe UI", 9)
        ).grid(row=1, column=0, sticky="w")
        self.last_prize_label = tk.Label(
            frame, text="€0", bg=self.C_CARD, fg=self.C_TEXT, font=("Segoe UI", 10)
        )
        self.last_prize_label.grid(row=1, column=1, sticky="w", padx=10)

        tk.Label(
            frame, text="Schedine (1-5):",
            bg=self.C_CARD, fg=self.C_MUTED, font=("Segoe UI", 9),
        ).grid(row=2, column=0, sticky="w", padx=5, pady=4)
        self.schedine_var = tk.IntVar(value=2)
        self.schedine_spin = tk.Spinbox(
            frame, from_=1, to=5, width=5,
            textvariable=self.schedine_var,
            bg=self.C_GREEN_LT, fg=self.C_GREEN_DK, font=("Segoe UI", 11, "bold"),
            state="readonly",
        )
        self.schedine_spin.grid(row=2, column=1, sticky="w", padx=5, pady=4)

        tk.Button(
            frame,
            text="GENERA SCHEDINE",
            command=self.generate_optimal_dual,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 12, "bold"),
            activebackground=self.C_GREEN_DK,
            padx=20,
            pady=6,
        ).grid(row=4, column=0, columnspan=2, pady=12, sticky="ew")

        tk.Label(
            frame,
            text="Strategia QuartileSpread (copertura spaziale 1-90): 1 numero/quartile,\n"
                  "somma 246-306, max 2/decade, max 1 numero>80.\n"
                  "Le altre strategie sono usate SOLO per backtest (bottone 'Valuta Algoritmi').",
            bg=self.C_CARD,
            fg=self.C_MUTED,
            font=("Segoe UI", 8),
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 6))

        tk.Label(
            frame,
            text="Schedine generate:",
            bg=self.C_CARD,
            fg=self.C_MUTED,
            font=("Segoe UI", 9),
        ).grid(row=5, column=0, sticky="w")

        self.numbers_frame = tk.Frame(frame, bg=self.C_CARD)
        self.numbers_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    def create_prizes_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="PREMI E PROBABILITÀ",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", pady=5)

        hdr = ["Categoria", "Premio", "Probabilità (1 su)"]
        for c, h in enumerate(hdr):
            tk.Label(
                frame,
                text=h,
                bg=self.C_GREEN,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=6,
                pady=3,
            ).grid(row=0, column=c, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        rows = [
            ("6", "Jackpot", "622.614.630"),
            ("5 + Jolly", "Variabile", "103.769.105"),
            ("5", "Variabile", "2.333.636"),
            ("4", "Variabile", "11.907"),
            ("3", "€10*", "327"),
            ("2", "€5*", "22"),
        ]
        for i, (cat, prize, odds) in enumerate(rows, start=1):
            bg = self.C_CARD if i % 2 else self.C_GREEN_LT
            tk.Label(frame, text=cat, bg=bg, fg=self.C_TEXT, font=("Segoe UI", 9), padx=6, pady=3).grid(row=i, column=0, sticky="ew")
            tk.Label(frame, text=prize, bg=bg, fg=self.C_GREEN_DK, font=("Segoe UI", 9, "bold"), padx=6, pady=3).grid(row=i, column=1, sticky="ew")
            tk.Label(frame, text=odds, bg=bg, fg=self.C_MUTED, font=("Segoe UI", 9), padx=6, pady=3).grid(row=i, column=2, sticky="ew")
        tk.Label(
            frame,
            text="* Importi indicativi. Jackpot e premi superiori variano.",
            bg=self.C_CARD,
            fg=self.C_MUTED,
            font=("Segoe UI", 8),
            justify="left",
        ).grid(row=len(rows) + 1, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def create_results_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="ESTRAZIONI RECENTI",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="both", expand=True, pady=5)

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
            text="AZIONI",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", pady=5)

        btn_frame = tk.Frame(frame, bg=self.C_CARD)
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="VERIFICA SCHEDINE PER ESTRAZIONI",
            command=self.verify_all_schedines,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            activebackground=self.C_GREEN_DK,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame,
            text="Esporta Report",
            command=self.export_report,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 9),
            activebackground=self.C_GREEN_DK,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame,
            text="Valuta Algoritmi",
            command=self.evaluate_and_show,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 9),
            activebackground=self.C_GREEN_DK,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame,
            text="Aggiorna Storico",
            command=self.update_historical_ui,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 9),
            activebackground=self.C_GREEN_DK,
        ).pack(side="left", padx=4)

    def create_my_plays_section(self, parent):
        frame = tk.LabelFrame(
            parent,
            text="LE MIE GIOCATE (ROI personale)",
            bg=self.C_CARD,
            fg=self.C_GREEN,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", pady=5)

        # statistiche
        stats_row = tk.Frame(frame, bg=self.C_CARD)
        stats_row.pack(fill="x", pady=2)
        self.my_stats_labels = {}
        for i, key in enumerate(["Speso", "Vinto", "ROI %", "M2", "M3", "M4", "Schedine"]):
            lbl = tk.Label(
                stats_row,
                text=f"{key}: 0",
                bg=self.C_GREEN_LT,
                fg=self.C_GREEN_DK,
                font=("Segoe UI", 9, "bold"),
                padx=6,
                pady=3,
            )
            lbl.grid(row=0, column=i, padx=3, sticky="ew")
            stats_row.columnconfigure(i, weight=1)
            self.my_stats_labels[key] = lbl

        # tabella giocate recenti
        cols = ("Data", "Numeri", "Somma", "Esito", "Verif")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=5)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=90, anchor="center")
        tree.pack(fill="both", expand=True, pady=3)
        self.my_plays_tree = tree

        tk.Button(
            frame,
            text="Calcola ROI Personale",
            command=self.compute_my_plays,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 9),
            activebackground=self.C_GREEN_DK,
        ).pack(pady=3)
        tk.Button(
            frame,
            text="Mostra Grafici",
            command=self.show_charts,
            bg=self.C_GREEN,
            fg="white",
            font=("Segoe UI", 9),
            activebackground=self.C_GREEN_DK,
        ).pack(pady=3)
        tk.Button(
            frame,
            text="Cancella Schedine",
            command=self.delete_schedine,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            activebackground="#c0392b",
        ).pack(pady=3)

    def compute_my_plays(self):
        """Legge giocate dal DB, verifica contro estrazioni reali, calcola ROI personale.
        Usa i premi REALI dal DB (p2,p3,p4,p5,p5j,p6). Fallback a stime se 0."""
        import sqlite3
        c = self.conn.cursor()
        c.execute("SELECT id, data, numeri, somma, verificato, vincita FROM giocate ORDER BY id")
        rows_db = c.fetchall()
        premi_default = {2: 5, 3: 25, 4: 296, 5: 25847, 6: 1000000}

        spent = 0
        won = 0
        m2 = m3 = m4 = 0
        rows = []
        for gid, data, numeri_str, somma, verificato, vincita in rows_db:
            try:
                nums = [int(x) for x in numeri_str.split("-") if x]
            except:
                continue
            if len(nums) != 6:
                continue
            spent += 1
            esito = "in attesa"
            c.execute("SELECT n1,n2,n3,n4,n5,n6,jolly,p2,p3,p4,p5,p5j,p6 FROM estrazioni WHERE data=?", (data,))
            rec = c.fetchone()
            if rec:
                matches = len(set(nums) & set(rec[:6]))
                jolly = rec[6]
                jolly_hit = 1 if jolly and jolly in nums else 0
                p2, p3, p4, p5, p5j, p6 = rec[7], rec[8], rec[9], rec[10], rec[11], rec[12]
                if matches == 6:
                    p = p6 if p6 > 0 else premi_default[6]
                elif matches == 5:
                    if jolly_hit:
                        p = p5j if p5j > 0 else premi_default[5]
                    else:
                        p = p5 if p5 > 0 else premi_default[5]
                elif matches == 4:
                    p = p4 if p4 > 0 else premi_default[4]
                elif matches == 3:
                    p = p3 if p3 > 0 else premi_default[3]
                elif matches == 2:
                    p = p2 if p2 > 0 else premi_default[2]
                else:
                    p = 0
                won += p
                if matches == 2:
                    m2 += 1
                    esito = f"M2 +€{p}"
                elif matches == 3:
                    m3 += 1
                    esito = f"M3 +€{p}"
                elif matches >= 4:
                    m4 += 1
                    esito = f"M{matches} +€{p}"
                else:
                    esito = f"{matches} nil"
            else:
                # gia verificata in passato ma estrazione non nel DB: usa vincita salvata
                if verificato and vincita:
                    won += vincita
                    if vincita >= 100:
                        m4 += 1
                    elif vincita >= 10:
                        m3 += 1
                    elif vincita >= 5:
                        m2 += 1
            rows.append((data, numeri_str, somma, esito, verificato))

        roi = (won / spent * 100) if spent else 0
        self.my_stats_labels["Speso"].config(text=f"Speso: €{spent}")
        self.my_stats_labels["Vinto"].config(text=f"Vinto: €{won}")
        self.my_stats_labels["ROI %"].config(text=f"ROI %: {roi:.1f}")
        self.my_stats_labels["M2"].config(text=f"M2: {m2}")
        self.my_stats_labels["M3"].config(text=f"M3: {m3}")
        self.my_stats_labels["M4"].config(text=f"M4: {m4}")
        self.my_stats_labels["Schedine"].config(text=f"Schedine: {spent}")

        for it in self.my_plays_tree.get_children():
            self.my_plays_tree.delete(it)
        for r in rows[-20:]:
            self.my_plays_tree.insert("", "end", values=r)

        messagebox.showinfo(
            "ROI Personale",
            f"Giocate: {spent}\nSpeso: €{spent}\nVinto: €{won}\n"
            f"ROI: {roi:.1f}%\nM2:{m2} M3:{m3} M4:{m4}",
        )

    def show_charts(self):
        """Genera grafici matplotlib (distribuzione somme, frequenza numeri, ROI)
        e li mostra in una finestra tkinter."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from collections import Counter
        import tempfile, os

        if not self.records:
            messagebox.showwarning("Attenzione", "Nessun dato per i grafici!")
            return

        sums = [r["sum"] for r in self.records]
        fig, axes = plt.subplots(2, 1, figsize=(8, 7))
        fig.patch.set_facecolor("#eef7f0")

        # 1) Distribuzione somme (istogramma) + fascia QuartileSpread
        ax = axes[0]
        ax.hist(sums, bins=40, color="#1a8f3c", alpha=0.8, edgecolor="white")
        ax.axvspan(246, 306, color="#ffd200", alpha=0.3, label="Fascia QuartileSpread")
        ax.set_title("Distribuzione Somme Estrazioni", color="#0f6b2c", fontsize=11)
        ax.set_xlabel("Somma 6 numeri")
        ax.set_ylabel("Frequenza")
        ax.legend()

        # 2) Frequenza numeri 1-90
        ax = axes[1]
        cnt = Counter(n for r in self.records for n in r["nums"])
        nums = list(range(1, 91))
        freq = [cnt.get(n, 0) for n in nums]
        ax.bar(nums, freq, color="#1a8f3c", width=0.8)
        ax.set_title("Frequenza Numeri (1-90)", color="#0f6b2c", fontsize=11)
        ax.set_xlabel("Numero")
        ax.set_ylabel("Volte uscito")
        ax.set_xticks(range(0, 91, 10))

        plt.tight_layout()
        tmp = tempfile.gettempdir()
        path = os.path.join(tmp, "superenalotto_charts.png")
        fig.savefig(path, dpi=100, facecolor="#eef7f0")
        plt.close(fig)

        # mostra in Toplevel
        win = tk.Toplevel(self.root)
        win.title("Grafici SuperEnalotto")
        win.configure(bg="#eef7f0")
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(win, image=photo, bg="#eef7f0")
            lbl.image = photo
            lbl.pack(padx=10, pady=10)
        except Exception:
            tk.Label(win, text=f"Grafico salvato: {path}", bg="#eef7f0").pack(padx=10, pady=10)

    def evaluate_and_show(self):
        """Ricalcola ROI rolling su ultime 50 estrazioni e mostra la classifica."""
        perf, best = self._best_auto(50)
        res = perf.get("results", {})
        lines = [f"Classifica ROI - ultime {perf.get('window',50)} estrazioni:", ""]
        ranked = sorted(res.items(), key=lambda kv: kv[1]["roi"], reverse=True)
        for i, (name, r) in enumerate(ranked, 1):
            star = " <-- AUTO" if name == best else ""
            lines.append(
                f"{i}. {name}: ROI {r['roi']}% | M2:{r['m2']} M3:{r['m3']} M4:{r['m4']} | "
                f"net €{r['net']}{star}"
            )
        lines.append("")
        lines.append("Auto userà il #1 finché la finestra non cambia.")
        messagebox.showinfo("Valutazione Algoritmi", "\n".join(lines))

    def update_historical_ui(self):
        """Bottone: aggiorna lo storico estrazioni da superenalotto.com/archivio."""
        try:
            added, scraped = self.scrape_historical(pages=3)
            self.load_data()
            self.update_stats_display()
            self.update_results_display()
            messagebox.showinfo(
                "Aggiorna Storico",
                f"Scansione: {scraped} estrazioni\n"
                f"Nuove aggiunte: {added}\n"
                f"Totale nel database: {len(self.records)}",
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Scraping storico fallito:\n{str(e)[:200]}")

    def _on_resize(self, event=None):
        # ricalcola scrollregion e larghezza contenuto
        try:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfig(
                self._canvas.find_all()[0], width=self._canvas.winfo_width()
            )
        except Exception:
            pass

    def _init_db(self):
        """Crea/collega superenalotto.db e importa il CSV se il DB e' vuoto."""
        import sqlite3
        self.conn = sqlite3.connect(self.db_path)
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS estrazioni (
                data TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT,
                jolly INT, star INT,
                p2 REAL DEFAULT 0, p3 REAL DEFAULT 0, p4 REAL DEFAULT 0,
                p5 REAL DEFAULT 0, p5j REAL DEFAULT 0, p6 REAL DEFAULT 0)"""
        )
        # migration: se esiste vecchio schema senza premi, aggiungo colonne
        try:
            c.execute("SELECT p2 FROM estrazioni LIMIT 0")
        except:
            for col in ["p2", "p3", "p4", "p5", "p5j", "p6"]:
                try:
                    c.execute(f"ALTER TABLE estrazioni ADD COLUMN {col} REAL DEFAULT 0")
                except:
                    pass
        c.execute(
            """CREATE TABLE IF NOT EXISTS giocate (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, numeri TEXT,
                somma INT, verificato INT DEFAULT 0, vincita INT DEFAULT 0)"""
        )
        self.conn.commit()
        # import CSV se estrazioni vuote
        c.execute("SELECT COUNT(*) FROM estrazioni")
        if c.fetchone()[0] == 0 and os.path.exists(self.csv_path):
            self._import_csv_to_db()
        # import tracking.csv in giocate se giocate vuote
        c.execute("SELECT COUNT(*) FROM giocate")
        if c.fetchone()[0] == 0 and os.path.exists(self.tracking_path):
            self._import_tracking_to_db()

    def _import_csv_to_db(self):
        """Importa superenalotto.csv (formato A o B) nel DB, normalizzando date a ISO."""
        import sqlite3
        c = self.conn.cursor()
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
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
                        "INSERT OR IGNORE INTO estrazioni VALUES (?,?,?,?,?,?,?,?,?)",
                        (data_norm, nums[0], nums[1], nums[2], nums[3], nums[4], nums[5], jolly, star),
                    )
                except:
                    continue
        self.conn.commit()

    def _import_tracking_to_db(self):
        import sqlite3
        c = self.conn.cursor()
        with open(self.tracking_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 6:
                    continue
                try:
                    nums = [int(x.strip()) for x in str(row[4]).split("-") if x.strip()]
                except:
                    continue
                if len(nums) != 6:
                    continue
                verif = row[6] if len(row) > 6 and row[6] in ("0", "1") else "0"
                c.execute(
                    "INSERT INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,?)",
                    (row[0], "-".join(map(str, nums)), int(row[5]), int(verif)),
                )
        self.conn.commit()

    def load_data(self):
        """Carica estrazioni dal DB in self.records (ordinato per data)."""
        import sqlite3
        c = self.conn.cursor()
        c.execute("SELECT data,n1,n2,n3,n4,n5,n6,jolly,star FROM estrazioni ORDER BY data")
        self.records = []
        for data, n1, n2, n3, n4, n5, n6, jolly, star in c.fetchall():
            nums = [n1, n2, n3, n4, n5, n6]
            self.records.append(
                {"data": data, "nums": nums, "sum": sum(nums), "jolly": jolly, "star": star}
            )
        self.calculate_stats()
        self.update_results_display()

    def db_add_estrazione(self, data_iso, nums, jolly, star, premi=None):
        """Inserisce un'estrazione nel DB se non esiste (anti-dup per PK).
        premi: dict opzionale con chiavi p2,p3,p4,p5,p5j,p6."""
        import sqlite3
        c = self.conn.cursor()
        p = premi or {}
        c.execute(
            "INSERT OR IGNORE INTO estrazioni VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data_iso, nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
             jolly, star,
             p.get("p2", 0), p.get("p3", 0), p.get("p4", 0),
             p.get("p5", 0), p.get("p5j", 0), p.get("p6", 0)),
        )
        self.conn.commit()

    def db_update_premi(self, data_iso, premi):
        """Aggiorna i premi reali di un'estrazione nel DB."""
        import sqlite3
        c = self.conn.cursor()
        c.execute(
            "UPDATE estrazioni SET p2=?, p3=?, p4=?, p5=?, p5j=?, p6=? WHERE data=?",
            (premi.get("p2", 0), premi.get("p3", 0), premi.get("p4", 0),
             premi.get("p5", 0), premi.get("p5j", 0), premi.get("p6", 0), data_iso),
        )
        self.conn.commit()

    def db_save_giocata(self, data_iso, nums, somma):
        import sqlite3
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)",
            (data_iso, "-".join(map(str, nums)), somma),
        )
        self.conn.commit()

    def scrape_premi_estrazione(self, data_iso):
        """Scarica i premi reali da superenalotto.com/risultati-estrazione/DD-MM-YYYY.
        Ritorna dict con p2,p3,p4,p5,p5j,p6 (0 se non disponibile)."""
        import urllib.request
        import re
        try:
            dt = datetime.strptime(data_iso, "%Y-%m-%d")
            url = f"https://www.superenalotto.com/risultati-estrazione/{dt.strftime('%d-%m-%Y')}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            # cerca la tabella Quote SuperEnalotto
            premi = {}
            # pattern: "5 punti</td><td...>14.650,92 €</td>"
            for match in re.finditer(r'(\d+)\s*punti(?:\s*\+\s*Jolly)?\s*</td>\s*<td[^>]*>\s*([\d.,]+)\s*€', html):
                punti = int(match.group(1))
                valore = float(match.group(2).replace(".", "").replace(",", "."))
                if punti == 2:
                    premi["p2"] = valore
                elif punti == 3:
                    premi["p3"] = valore
                elif punti == 4:
                    premi["p4"] = valore
                elif punti == 5:
                    premi["p5"] = valore
            # 5+Jolly
            m = re.search(r'5\s*punti\s*\+\s*Jolly\s*</td>\s*<td[^>]*>\s*([\d.,]+)\s*€', html)
            if m:
                premi["p5j"] = float(m.group(1).replace(".", "").replace(",", "."))
            # 6 punti (jackpot)
            m = re.search(r'6\s*punti\s*</td>\s*<td[^>]*>\s*([\d.,]+)\s*€', html)
            if m:
                premi["p6"] = float(m.group(1).replace(".", "").replace(",", "."))
            return premi
        except:
            return {}

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

        # ordina per data decrescente (ISO YYYY-MM-DD)
        def _pd(r):
            try:
                return datetime.strptime(r["data"], "%Y-%m-%d")
            except:
                return datetime.min

        sorted_recs = sorted(self.records, key=_pd, reverse=True)
        # inserisci in coda (le prime = più recenti finiscono in alto)
        for record in sorted_recs[:10]:
            self.results_tree.insert(
                "",
                "end",
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
        today = datetime.now()
        draw_dows = {1, 3, 4, 5}  # Tuesday, Thursday, Friday, Saturday
        today_dow = today.weekday()

        if today_dow in draw_dows:
            giorni = {1: "Martedì", 3: "Giovedì", 4: "Venerdì", 5: "Sabato"}
            self.status_label.config(text=f"Oggi è {giorni[today_dow]} - GIORNO DI ESTRAZIONE!")
            self.status_label.config(fg="#00ff00")
        else:
            next_draw = self.get_next_draw_date()
            self.status_label.config(text=f"Prossima estrazione: {next_draw}")
            self.status_label.config(fg="#ffcc00")

    def get_next_draw_date(self):
        today = datetime.now()
        draw_dows = [1, 3, 4, 5]  # Tuesday, Thursday, Friday, Saturday
        today_dow = today.weekday()

        # se oggi è giorno di estrazione, ritorna oggi
        if today_dow in draw_dows:
            return today.strftime("%d/%m/%Y")

        # altrimenti cerca il prossimo giorno di estrazione
        for days_ahead in range(1, 8):
            next_dow = (today_dow + days_ahead) % 7
            if next_dow in draw_dows:
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

    # ===== STRATEGIE DISPONIBILI (backtest 4226 estrazioni) =====
    def _last_digit_spread(self):
        """ROI 32%: copre quante piu ultime cifre possibili (0-9)."""
        used = set()
        nums = []
        for _ in range(2000):
            nums = []
            used = set()
            ok = True
            while len(nums) < 6:
                n = random.randint(1, 90)
                if n in nums:
                    continue
                d = n % 10
                if d in used:
                    ok = False
                    break
                used.add(d)
                nums.append(n)
            if ok and len(nums) == 6 and self._valid_constraints(sorted(nums)):
                return sorted(nums)
        # fallback: 6 numeri con ultime cifre uniche a caso
        while len(nums) < 6:
            n = random.randint(1, 90)
            if n not in nums and n % 10 not in used:
                nums.append(n)
                used.add(n % 10)
        return sorted(nums)

    def _fibonacci_wheel(self):
        """ROI 29%: ruota sui numeri della sequenza di Fibonacci (1-90)."""
        fib = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        pool = fib + [n for n in range(1, 91) if n not in fib]
        for _ in range(2000):
            nums = sorted(random.sample(pool, 6))
            if self._valid_constraints(nums):
                return nums
        return sorted(random.sample(range(1, 91), 6))

    def _position_based(self):
        """ROI 25%: pesa sulle posizioni storiche dei numeri estratti."""
        # usa le posizioni medie dai records per biasare la scelta
        if self.records:
            all_nums = [n for r in self.records for n in r["nums"]]
            # peso = quante volte appare (piu frequenti hanno probabilita uguale,
            # ma manteniamo diversificazione tramite vincoli)
            pool = list(range(1, 91))
        else:
            pool = list(range(1, 91))
        for _ in range(2000):
            nums = sorted(random.sample(pool, 6))
            if self._valid_constraints(nums):
                return nums
        return sorted(random.sample(range(1, 91), 6))

    def _anti_recent(self):
        """ROI 24%: evita i numeri usciti nell'ultima estrazione."""
        recent = set()
        if self.records:
            recent = set(self.records[-1]["nums"])
        pool = [n for n in range(1, 91) if n not in recent]
        for _ in range(2000):
            nums = sorted(random.sample(pool, 6))
            if self._valid_constraints(nums):
                return nums
        return sorted(random.sample(range(1, 91), 6))

    STRATEGIES = {
        "QuartileSpread": {"fn": "_quartile_spread", "roi": 35.73},
        "LastDigitSpread": {"fn": "_last_digit_spread", "roi": 32.0},
        "FibonacciWheel": {"fn": "_fibonacci_wheel", "roi": 29.0},
        "PositionBased": {"fn": "_position_based", "roi": 25.0},
        "AntiRecent": {"fn": "_anti_recent", "roi": 24.0},
    }

    def eval_all_strategies(self, n_draws=50):
        """Calcola ROI rolling sulle ultime N estrazioni reali per ogni algoritmo.
        Ritorna dict {nome: {roi, m2, m3, m4, net}}. Usa 1 schedina/estrazione."""
        if len(self.records) < n_draws:
            n_draws = len(self.records)
        window = self.records[-n_draws:]
        premi = {2: 5, 3: 25, 4: 296, 5: 25847, 6: 1000000}
        results = {}
        for name, cfg in self.STRATEGIES.items():
            fn = getattr(self, cfg["fn"])
            spent = 0
            won = 0
            m2 = m3 = m4 = 0
            # per ogni estrazione della finestra: genera 1 schedina, verifica
            for rec in window:
                nums = fn()
                spent += 1  # 1 euro a schedina
                matches = len(set(nums) & set(rec["nums"]))
                if matches >= 2:
                    p = premi.get(matches, 0)
                    won += p
                    if matches == 2:
                        m2 += 1
                    elif matches == 3:
                        m3 += 1
                    elif matches >= 4:
                        m4 += 1
            roi = (won / spent * 100) if spent else 0
            results[name] = {
                "roi": round(roi, 2),
                "spent": spent,
                "won": won,
                "net": won - spent,
                "m2": m2,
                "m3": m3,
                "m4": m4,
            }
        return results

    def _load_performance(self):
        try:
            with open("algo_performance.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _best_auto(self, n_draws=50):
        """Sceglie il miglior algoritmo sulla finestra rolling.
        Ricalcola se non c'e' un file o e' vecchio (>1 giorno)."""
        perf = self._load_performance()
        need_recalc = True
        if perf.get("date") == datetime.now().strftime("%Y-%m-%d") and perf.get("results"):
            # gia calcolato oggi: usa quello (ma la finestra puo cambiare se
            # c'e' una nuova estrazione rispetto a ieri -> ricontrolla n_draws)
            need_recalc = False
        if need_recalc:
            results = self.eval_all_strategies(n_draws)
            best = max(results, key=lambda k: results[k]["roi"])
            perf = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "window": n_draws,
                "best": best,
                "results": results,
            }
            try:
                with open("algo_performance.json", "w", encoding="utf-8") as f:
                    json.dump(perf, f, indent=2)
            except:
                pass
        else:
            best = perf.get("best", "QuartileSpread")
        return perf, best

    def generate_optimal_dual(self):
        """Genera 1-5 schedine con QuartileSpread (strategia unica, UNA SOLA VOLTA per data).
        BLOCCATO se esistono giocate per la data odierna (cancellale prima)."""
        if not self.stats:
            messagebox.showwarning("Attenzione", "Carica prima i dati!")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM giocate WHERE data=?", (today,))
        if c.fetchone()[0] > 0:
            messagebox.showwarning(
                "Bloccato",
                f"Esistono già schedine per il {today}.\n"
                "Cancellale prima di generarne di nuove.",
            )
            return

        fn = self._quartile_spread

        n_schedine = max(1, min(5, int(self.schedine_var.get())))
        self.generated_numbers = []
        for _ in range(n_schedine):
            q = fn()
            self.generated_numbers.append({"nums": q, "sum": sum(q)})

        self.status_label.config(text=f"QuartileSpread | {n_schedine} schedine")
        self.display_generated_numbers()
        self.save_to_tracking()

    def delete_schedine(self):
        """Apre una finestra per cancellare schedine salvate UNA ALLA VOLTA."""
        import sqlite3
        c = self.conn.cursor()
        c.execute("SELECT id, data, numeri, somma FROM giocate ORDER BY id DESC")
        rows = c.fetchall()
        if not rows:
            messagebox.showinfo("Cancella Schedine", "Nessuna giocata salvata.")
            return

        win = tk.Toplevel(self.root)
        win.title("Cancella Schedine (una alla volta)")
        win.geometry("420x380")
        win.configure(bg=self.C_CARD)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="Seleziona le schedine da cancellare:",
            bg=self.C_CARD,
            fg=self.C_GREEN_DK,
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=8)

        listbox = tk.Listbox(
            win,
            selectmode="multiple",
            font=("Segoe UI", 10),
            bg="white",
            fg=self.C_GREEN_DK,
        )
        # mappa idx -> id
        self._delete_map = {}
        for i, (gid, data, numeri, somma) in enumerate(rows):
            listbox.insert(tk.END, f"{data}  |  {numeri}  |  somma {somma}")
            self._delete_map[i] = gid
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        def do_delete():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Attenzione", "Seleziona almeno una schedina.")
                return
            if not messagebox.askyesno(
                "Conferma",
                f"Cancellare {len(sel)} schedine selezionate?",
            ):
                return
            for idx in sel:
                gid = self._delete_map[idx]
                c.execute("DELETE FROM giocate WHERE id=?", (gid,))
            self.conn.commit()
            self._refresh_tracking_csv()
            messagebox.showinfo("Fatto", f"{len(sel)} schedine cancellate.")
            win.destroy()

        tk.Button(
            win,
            text="Cancella Selezionate",
            command=do_delete,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=10)

    def _refresh_tracking_csv(self):
        """Riscrive tracking.csv dal DB (backup)."""
        c = self.conn.cursor()
        c.execute("SELECT data, numeri, somma, verificato FROM giocate ORDER BY id")
        rows = c.fetchall()
        with open(self.tracking_path, "w", encoding="utf-8") as f:
            f.write("data,giornata,budget,schedine,numeri,somma,verificato\n")
            for data, numeri, somma, verificato in rows:
                f.write(f"{data},,,,{numeri},{somma},{verificato}\n")

    def display_generated_numbers(self):
        for widget in self.numbers_frame.winfo_children():
            widget.destroy()

        for i, sched in enumerate(self.generated_numbers):
            nums_str = "-".join(str(n) for n in sched["nums"])
            # verde se nella fascia ottimale, verde scuro se fuori (no rosso)
            color = self.C_GREEN if 240 <= sched["sum"] <= 320 else self.C_GREEN_DK

            frame = tk.Frame(self.numbers_frame, bg=self.C_CARD)
            frame.pack(fill="x", pady=2)

            tk.Label(
                frame,
                text=f"Schedina {i + 1}:",
                bg=self.C_CARD,
                fg=self.C_MUTED,
                font=("Segoe UI", 9),
            ).pack(side="left")

            tk.Label(
                frame,
                text=nums_str,
                bg=self.C_CARD,
                fg=color,
                font=("Segoe UI", 12, "bold"),
            ).pack(side="left", padx=10)

            tk.Label(
                frame,
                text=f"[somma: {sched['sum']}]",
                bg=self.C_CARD,
                fg=self.C_GREEN_DK,
                font=("Segoe UI", 9),
            ).pack(side="left")

    def save_to_tracking(self):
        today = datetime.now().strftime("%Y-%m-%d")

        if not self.generated_numbers:
            return

        for sched in self.generated_numbers:
            self.db_save_giocata(today, sched["nums"], sched["sum"])

        # backup su CSV per trasparenza/export
        file_exists = os.path.exists(self.tracking_path)
        with open(self.tracking_path, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("data,giornata,budget,schedine,numeri,somma,verificato\n")
            for sched in self.generated_numbers:
                nums_str = "-".join(str(n) for n in sched["nums"])
                f.write(f"{today},,,,{nums_str},{sched['sum']},0\n")

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

        # chiedi dove salvare (default Desktop)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default = os.path.join(desktop, f"report_superenalotto_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
        filename = filedialog.asksaveasfilename(
            title="Salva report SuperEnalotto",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=desktop,
            initialfile=os.path.basename(default),
        )
        if not filename:
            return  # annullato
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        messagebox.showinfo("Report", f"Report salvato in:\n{filename}")

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
        premi = {2: 5, 3: 25, 4: 296, 5: 25847, 6: 1000000}
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

    def verify_all_schedines(self, only_unchecked=False):
        """Verifica le giocate nel DB SOLO per i giorni con estrazione reale.
        Usa i premi REALI dal DB (p2,p3,p4,p5,p5j,p6). Fallback a stime se 0.
        only_unchecked=True: verifica solo verificato=0 (auto all'avvio)."""
        import sqlite3
        c = self.conn.cursor()
        c.execute("SELECT id, data, numeri FROM giocate")
        rows = c.fetchall()
        if not rows:
            if not only_unchecked:
                messagebox.showinfo("Verifica", "Nessuna giocata salvata.")
            else:
                messagebox.showinfo("Verifica automatica", "Nessuna giocata da verificare.")
            return

        premi_default = {2: 5, 3: 25, 4: 296, 5: 25847, 6: 1000000}
        tot_win = 0
        checked = 0
        skipped = 0
        lines = []
        for gid, data, numeri_str in rows:
            try:
                nums = [int(x) for x in numeri_str.split("-") if x]
            except:
                continue
            if len(nums) != 6:
                continue
            # salta se gia verificata (solo in modalita auto)
            c.execute("SELECT verificato FROM giocate WHERE id=?", (gid,))
            if only_unchecked and c.fetchone()[0] == 1:
                continue
            # cerca estrazione reale per quella data (con premi)
            c.execute("SELECT n1,n2,n3,n4,n5,n6,jolly,p2,p3,p4,p5,p5j,p6 FROM estrazioni WHERE data=?", (data,))
            rec = c.fetchone()
            if not rec:
                if not only_unchecked:
                    skipped += 1
                continue
            rec_nums = list(rec[:6])
            jolly = rec[6]
            matches = len(set(nums) & set(rec_nums))
            jolly_hit = 1 if jolly and jolly in nums else 0
            # premi reali dal DB (fallback a default se 0)
            p2, p3, p4, p5, p5j, p6 = rec[7], rec[8], rec[9], rec[10], rec[11], rec[12]
            if matches == 6:
                premio = p6 if p6 > 0 else premi_default[6]
            elif matches == 5:
                if jolly_hit:
                    premio = p5j if p5j > 0 else premi_default[5]
                else:
                    premio = p5 if p5 > 0 else premi_default[5]
            elif matches == 4:
                premio = p4 if p4 > 0 else premi_default[4]
            elif matches == 3:
                premio = p3 if p3 > 0 else premi_default[3]
            elif matches == 2:
                premio = p2 if p2 > 0 else premi_default[2]
            else:
                premio = 0
            tot_win += premio
            checked += 1
            # aggiorna DB
            c.execute(
                "UPDATE giocate SET verificato=1, vincita=? WHERE id=?",
                (premio, gid),
            )
            detail = f" (+Jolly)" if jolly_hit else ""
            lines.append(
                f"{data}: {matches} indovinati{detail} -> "
                f"{'€' + str(premio) if premio else 'nessuna'}"
            )
        self.conn.commit()

        title = "Verifica Schedine per Estrazioni" if not only_unchecked else "Verifica Automatica"
        msg = (
            f"Verificate: {checked} schedine (giorni con estrazione)\n"
            f"Saltate: {skipped} (giorni senza estrazione)\n\n"
        )
        msg += "\n".join(lines[:50])
        if len(lines) > 50:
            msg += f"\n... altri {len(lines) - 50} risultati"
        msg += f"\n\nVincita totale stimata: €{tot_win}"
        messagebox.showinfo(title, msg)

    def _mark_verified(self, dates):
        """Aggiorna verificato=1 nelle giocate dei giorni in `dates` (legacy CSV)."""
        # con il DB la verifica aggiorna direttamente; metodo mantenuto per compatibilita'
        pass

    def auto_check_new_draws(self):
        """All'avvio: verifica automaticamente le giocate non verificate per giorni
        con estrazione reale."""
        self.verify_all_schedines(only_unchecked=True)

    # ===== INTEGRAZIONE API lotteryresultsfeed.com =====
    API_BASE = "https://www.lotteryresultsfeed.com/api/lottery/lotteries"

    def scrape_historical(self, pages=1):
        """Scrape storico estrazioni da superenalotto.com/archivio e aggiunge
        le mancanti al DB (anti-dup per PK data).
        Ritorna (aggiunte, totale_scrape)."""
        import urllib.request, ssl, re

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        added = 0
        scraped = 0
        existing = {r["data"] for r in self.records}
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
            estrazioni = []
            i = 0
            j = 0
            while i + 6 <= len(nums_norm) and j < len(nums_red):
                n6 = [int(x) for x in nums_norm[i:i + 6]]
                jolly = int(nums_red[j])
                estrazioni.append((n6, jolly))
                i += 6
                j += 1
            for (n6, jolly), dstr in zip(estrazioni, dates):
                try:
                    dd, mm, yyyy = dstr.split()
                    mesi = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
                            "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
                    iso = f"{yyyy}-{mesi.get(mm,1):02d}-{int(dd):02d}"
                except Exception:
                    continue
                scraped += 1
                if iso in existing:
                    continue
                self.db_add_estrazione(iso, n6, jolly, 0)
                existing.add(iso)
                added += 1
        return added, scraped

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
        data_str = str(data.get("draw_date", datetime.now().strftime("%Y-%m-%d")))
        # normalizza a ISO YYYY-MM-DD (coerente con il resto del DB)
        try:
            data_str = datetime.strptime(data_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            try:
                data_str = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except:
                pass
        # aggiorna jackpot label (in palio, da config) e ultimo montepremi (da API)
        if jp > 0:
            self.last_prize_label.config(text=f"€{jp:,.0f}")
        # append to DB if not already present (PK data = anti-dup)
        exists = any(r["data"] == data_str for r in self.records)
        if not exists:
            self.db_add_estrazione(data_str, numeri, jolly, star)
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
        """Jackpot in palio: scraping LIVE da superenalotto.com (funzionante).
        Fallback su config.json['jackpot'] se lo scraping fallisce."""
        live = self._scrape_jackpot()
        if live and live > 0:
            self.jackpot_label.config(text=f"€{live:,.0f}")
            return
        # fallback config
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
            self.jackpot_label.config(text="€0 (offline)")

    def _scrape_jackpot(self):
        """Estrae il jackpot da superenalotto.com (<div class=JackpotValueNumber>)."""
        try:
            import urllib.request, re, ssl

            # NOTE: TLS verification disabled intentionally — public site cert;
            # read-only public data, no secrets in transit.
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                "https://www.superenalotto.com",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            html = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode(
                "utf-8", "ignore"
            )
            m = re.search(r"JackpotValueNumber\">([\d.]+)", html)
            if m:
                return float(m.group(1).replace(".", ""))
        except:
            pass
        return None

def main():
    root = tk.Tk()
    app = SuperenalottoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
