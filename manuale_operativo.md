# SUPERENALOTTO - MANUALE OPERATIVO (Aggiornato)

## 📊 ANALISI COMUNE DENOMINATORE (4236 ESTRAZIONI 1997-2026)

**Totale estrazioni:** 4236 (CSV) / 4234 (DB)  
**Periodo:** 03/12/1997 - 04/09/2026  
**Media somma:** 276.64  
**Mediana:** 277  
**Deviazione standard:** 61.95  
**Min / Max:** 81 / 467  
**Q1 / Q3:** 234 / 319  

### 🔢 TOP 10 NUMERI PIÙ FREQUENTI
| # | Numero | Count | % |
|---|--------|-------|---|
| 1 | 85 | 321 | 1.28% |
| 2 | 6 | 316 | 1.25% |
| 3 | 79 | 309 | 1.22% |
| 4 | 81 | 308 | 1.21% |
| 5 | 49 | 308 | 1.21% |
| 6 | 83 | 307 | 1.21% |
| 7 | 55 | 307 | 1.21% |
| 8 | 86 | 306 | 1.20% |
| 9 | 80 | 305 | 1.20% |
| 10 | 77 | 305 | 1.19% |

### 🎯 COMUNE DENOMINATORE — PATTERN RICORRENTI

#### Distribuzione per fascia (low/mid/high)
| Pattern | Occorrenze | % |
|---------|-----------|---|
| **2L-2M-2H** | **525** | **12.6%** |
| 3L-1M-2H | 384 | 9.2% |
| 2L-1M-3H | 383 | 9.2% |
| 1L-3M-2H | 374 | 9.0% |
| 1L-2M-3H | 350 | 8.4% |

**Pattern più comune: 2 numeri bassi (1-30) + 2 medi (31-60) + 2 alti (61-90)**

#### Distribuzione parità (even/odd)
| Pattern | Occorrenze | % |
|---------|-----------|---|
| **3 even - 3 odd** | **1329** | **31.8%** |
| 2 even - 4 odd | 1013 | 24.3% |
| 4 even - 2 odd | 977 | 23.4% |
| 1 even - 5 odd | 389 | 9.3% |

**Pattern più comune: 3 pari / 3 dispari**

#### Distribuzione numeri primi per estrazione
| Primi | Occorrenze | % |
|-------|-----------|---|
| 0 primi | 671 | 16.1% |
| **1 primo** | **1406** | **33.6%** |
| **2 primi** | **1329** | **31.8%** |
| 3 primi | 617 | 14.8% |
| 4 primi | 156 | 3.7% |
| 5+ primi | 14 | 0.3% |

**Pattern più comune: 1-2 numeri primi (65.4% delle estrazioni)**

#### Distribuzione per decade
| Decade | Count | % |
|--------|-------|---|
| 81-90 | 299 | 11.5% |
| 41-50 | 299 | 11.5% |
| 61-70 | 299 | 11.4% |
| 51-60 | 298 | 11.4% |
| 31-40 | 299 | 11.4% |
| 71-80 | 285 | 10.9% |
| 21-30 | 272 | 10.4% |
| 11-20 | 275 | 10.5% |
| 1-9 | 248 | 9.5% |

#### Coppie più frequenti (co-occorrenza)
| Coppia | Count |
|--------|-------|
| 48-87 | 32 |
| 18-47 | 32 |
| 6-83 | 31 |
| 6-80 | 31 |
| 1-83 | 30 |

### 🔢 TOP 10 SOMME PIÙ FREQUENTI
| Somma | Count |
|-------|-------|
| 278 | 36 |
| 295 | 35 |
| 260 | 35 |
| 269 | 35 |
| 271 | 35 |
| 279 | 34 |
| 258 | 34 |
| 268 | 34 |
| 280 | 33 |
| 276 | 33 |

### 🎯 JOLLY
| Numero | Count | % |
|--------|-------|---|
| 1 | 61 | 10.7% |
| 26 | 60 | 10.5% |
| 4 | 58 | 10.1% |
| 61 | 57 | 10.0% |
| 62 | 56 | 9.8% |

### 🌟 SUPERSTAR (totale: 43)
| Numero | Count |
|--------|-------|
| 13 | 5 |
| 14 | 5 |
| 15 | 5 |
| 1 | 4 |
| 6 | 4 |
| 23 | 4 |
| 40 | 4 |
| 41 | 4 |
| 49 | 4 |
| 55 | 4 |

## 📈 STATISTICHE PERCENTUALI

| Metrica | Valore |
|---------|--------|
| Primi | 26.27% |
| Estremi (>75) | 17.58% |
| >31 | 66.51% |
| >80 | 11.81% |
| Pari | 49.52% |

## 🎯 STRATEGIE IMPLEMENTATE (aggiornate)

1. **QuartileSpread** (default) — 1 per quartile, somma Q1-Q3, max 2/decade, max 1 >80
2. **Optimized** (comune denominatore) — Somma 274-278, pattern 2L/2M/2H, 1-2 primi, 3 even/3 odd
3. **SumLocked** — Somma bloccata su media (274-278)
4. **PrimeFocus** — Almeno 3 numeri primi
5. **MiddleFrequency** — Numeri di frequenza media
6. **GapSpread** — Minimo gap=5 tra numeri adiacenti
7. **ComplementMirror** — 3 numeri + 3 complementari (91-n)
8. **HotCold** — Mix caldi (ultime 10) e freddi
9. **AntiRecent** — Evita ultime 5 estrazioni
10. **MixHotColdPrime** — HotCold + PrimeFocus (top M3+ rate)
11. **MixQuartileHotCold** — QuartileSpread + HotCold
12. **MixAllThree** — Quartile + HotCold + AntiRecent mescolati

## 🏆 RISULTATI BACKTEST (4236 estrazioni, 2 biglietti/estrazione)

| Strategy | M3+/1000 | Net (€) | ROI | M3 | M4 |
|----------|----------|---------|-----|-----|-----|
| **SumLocked** | **8.50** | -3786 | -89.38% | 18 | 0 |
| HotCold | 8.26 | -3515 | -82.98% | 17 | 1 |
| AntiRecent | 8.26 | -3515 | -82.98% | 17 | 1 |
| FibonacciWheel | 7.08 | -3861 | -91.15% | 15 | 0 |
| HotColdConstrained | 6.85 | -3590 | -84.75% | 14 | 1 |
| AntiRecentConstrained | 6.37 | -3615 | -85.34% | 13 | 1 |
| PrimeFocus | 6.14 | -3344 | -78.94% | 12 | 2 |
| GapSpread | 6.14 | -3911 | -92.33% | 13 | 0 |

### MIX STRATEGIES (2 biglietti/estrazione)

| Strategy | M3+/1000 | Net (€) | ROI | M3 | M4 |
|----------|----------|---------|-----|-----|-----|
| **MixHotColdPrime** | **7.79** | -7080 | -83.57% | 32 | 2 |
| ComplementMirror | 6.73 | -6909 | -81.55% | 27 | 3 |
| AntiRecentConstrained | 6.02 | -7551 | -89.13% | 25 | 1 |
| MixAntiRecentQuartile | 6.14 | -7822 | -92.33% | 26 | 0 |

**Best overall strategy:** MixHotColdPrime (7.79 M3+ per 1000, ROI -83.57%)

> Nota: Tutte le strategie perdono matematicamente (house edge ~65%). L'obiettivo è massimizzare la frequenza di Match 3+ rispetto al caso puro (Random: 5.19 M3+/1000).

## 📂 STRUTTURA FILES

```
Superenalotto/
├── superenalotto.csv          # Archivio 4236 estrazioni (1997-2026)
├── superenalotto.db           # SQLite DB (estrazioni + giocate)
├── gateway/
│   ├── engine.py              # Core: strategie, verifica, scraping, backup
│   ├── server.py              # HTTP API server (porta 8766)
│   ├── desktop.py             # Desktop app (tray icon)
│   ├── __main__.py            # PyInstaller entry point
│   └── __init__.py
├── web/
│   ├── index.html             # Frontend HTML (7 tab)
│   ├── app.js                 # Frontend JavaScript
│   └── style.css              # Tema verde
├── launcher.py                # Entry point v8.3 (PyWebView)
├── SuperEnalotto.spec         # PyInstaller build config
├── config.json                # API key (lotteryresultsfeed.com)
├── tracking.csv               # Giocate salvate + verificate
├── daily_limit.csv            # Contatore schedine giornaliere
├── analisi_completa.ps1       # Analisi statistica (PowerShell)
├── analisi_completa_v3.json   # Output JSON analisi (Python)
├── advanced_backtest.py       # Backtest 15 strategie (Python)
├── common_denominator_analysis.py  # Analisi pattern ricorrenti
├── backtest_full_4226.ps1     # Backtest PowerShell (5 strategie)
├── hot_cold_strategy.ps1      # Strategia Hot-Cold
├── sniper.ps1                 # Protocollo Sniper giornaliero
├── update_csv.ps1             # Aggiornamento CSV da API
├── setup_scheduler.ps1        # Configura attività pianificata
├── backtest_window_analysis.py # Analisi finestra rolling
├── requirements.txt           # Dipendenze (stdlib-only)
├── README.md                  # Documentazione principale
└── manuale_operativo.md       # Questo file
```

## 🚀 AVVIO RAPIDO

### GUI Desktop (PyWebView)
```bash
python launcher.py
```

### Analisi completa
```powershell
powershell -ExecutionPolicy Bypass -File "analisi_completa.ps1"
```

### Backtest avanzato (15 strategie)
```bash
py -3.14 advanced_backtest.py
py -3.14 common_denominator_analysis.py
```

### Backtest PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File "backtest_full_4226.ps1"
```

## 🔧 AGGIUNGERE UNA NUOVA STRATEGIA

1. In `gateway/engine.py` → aggiungi metodo `def nuova_strategia(self)`
2. Registra in `genera_schedine()` → `'nuova': self.nuova_strategia`
3. In `web/index.html` → aggiungi `<option value="nuova">` nel select
4. Testa con `py -3.14 test_new_strategies.py`

## 🔒 SICUREZZA
- API key in `config.json` (non in codice)
- `.gitignore` esclude `config.json`, `*.pyc`, `__pycache__/`, `superenalotto.db`
- Backup giornaliero automatico in `Documents/SuperEnalotto/backups/`
