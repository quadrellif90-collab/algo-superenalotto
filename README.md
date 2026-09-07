# SuperEnalotto - Protocollo Sniper

**Strumento avanzato di analisi statistica e generazione numeri per SuperEnalotto**, basato su 4238 estrazioni storiche (1997-2026). Include strategie ottimizzate (Hot-Cold, Position-Based, Anti-Recent) e backtest completo.

## 🗂️ Struttura Files

```
Superenalotto/
├── superenalotto.csv          # Archivio 4238 estrazioni storiche (1997-2026)
├── superenalotto.db           # SQLite DB (estrazioni + giocate)
├── gateway/                   # Backend Python
│   ├── engine.py              # Core logic: strategie, verifica, scraping, backup
│   ├── server.py              # HTTP API server (porta 8766)
│   ├── desktop.py             # Desktop app (tray icon)
│   ├── __main__.py            # PyInstaller entry point
│   └── __init__.py
├── web/                       # Frontend HTML/JS
│   ├── index.html             # Frontend HTML (7 tab)
│   ├── app.js                 # Frontend JavaScript (fetch API)
│   └── style.css              # Tema verde
├── launcher.py                # Entry point v8.3 (PyWebView)
├── SuperEnalotto.spec         # PyInstaller build config
├── config.json                # Configurazione API (lotteryresultsfeed.com)
├── tracking.csv               # Schedine giocate + verificate
├── daily_limit.csv            # Contatore schedine giornaliere
├── analisi_completa.ps1       # Analisi statistica completa (PowerShell)
├── analisi_completa_v3.json   # Output JSON analisi (Python)
├── advanced_backtest.py       # Backtest 15 strategie (Python)
├── advanced_backtest_results.json  # Risultati backtest
├── common_denominator_analysis.py   # Analisi pattern ricorrenti
├── common_denominator_analysis.json # Risultati analisi
├── backtest_full_4226.ps1     # Backtest completo (PowerShell)
├── hot_cold_strategy.ps1      # Strategia Hot-Cold
├── hot_cold_config.json       # Configurazione strategia Hot-Cold
├── sniper.ps1                 # Protocollo Sniper (generazione schedine)
├── sniper_full.ps1            # Workflow completo
├── update_csv.ps1             # Aggiornamento CSV da API
├── setup_scheduler.ps1        # Configura attività pianificata Windows
├── backtest_window_analysis.py # Analisi finestra rolling
├── manuale_operativo.md       # Manuale completo
├── SUPER_ENALOTTO_RELEASE_NOTES.md  # Note di rilascio
└── requirements.txt           # Dipendenze (stdlib-only)
```

## 🚀 Quick Start

### GUI Desktop (PyWebView)
```bash
python launcher.py
```

### Analisi completa
```powershell
powershell -ExecutionPolicy Bypass -File "analisi_completa.ps1"
```

### Backtest (tutte le strategie)
```powershell
powershell -ExecutionPolicy Bypass -File "backtest_full_4226.ps1"
```

### Generazione schedine Hot-Cold
```powershell
powershell -ExecutionPolicy Bypass -File "hot_cold_strategy.ps1"
```

## 📊 Statistiche Chiave (4238 estrazioni)

| Metrica | Valore |
|---------|--------|
| Media Somma | 276.64 |
| Mediana | 277 |
| Std Dev | 61.95 |
| Q1 / Q3 | 234 / 319 |
| Min / Max | 81 / 467 |
| Primi | 26.27% |
| >31 | 66.51% |
| >80 | 11.81% |
| Pari | 49.52% |

### Pattern Comune Denominatore
| Pattern | Frequenza |
|---------|-----------|
| **2L-2M-2H** (low 1-30, mid 31-60, high 61-90) | **525 (12.6%)** |
| 3 even / 3 odd | 1329 (31.8%) |
| 1-2 numeri primi | 2735 (65.4%) |

## 🎯 Strategie

1. **QuartileSpread** (default) - 1 per quartile, somma Q1-Q3, max 2/decade, max 1 >80
2. **Optimized** - Comune denominatore: somma 274-278, pattern 2L/2M/2H, 1-2 primi, 3 even/3 odd
3. **SumLocked** - Somma bloccata su media (274-278)
4. **PrimeFocus** - Almeno 3 numeri primi
5. **MiddleFrequency** - Numeri di frequenza media
6. **GapSpread** - Minimo gap=5 tra numeri adiacenti
7. **ComplementMirror** - 3 numeri + 3 complementari (91-n)
8. **HotCold** - Mix caldi (ultime 10) e freddi
9. **AntiRecent** - Evita ultime 5 estrazioni
10. **MixHotColdPrime** - HotCold + PrimeFocus (best M3+ rate)
11. **MixQuartileHotCold** - QuartileSpread + HotCold
12. **MixAllThree** - Quartile + HotCold + AntiRecent mescolati

## ⚡ Risultati Backtest (4238 estrazioni, 2 biglietti/draw)

```
SumLocked:             M3+/1000=8.50  Net=-€3,786  ROI: -89.38%
HotCold:               M3+/1000=8.26  Net=-€3,515  ROI: -82.98%
AntiRecent:            M3+/1000=8.26  Net=-€3,515  ROI: -82.98%
PrimeFocus:            M3+/1000=6.14  Net=-€3,344  ROI: -78.94%  ← Best ROI
FibonacciWheel:         M3+/1000=7.08  Net=-€3,861  ROI: -91.15%
Random (baseline):     M3+/1000=5.19  Net=-€3,961  ROI: -93.51%

MixHotColdPrime:       M3+/1000=7.79  Net=-€7,080  ROI: -83.57%  ← Best Mix
```

> Nota: Tutte le strategie perdono matemmaticamente (house edge ~65%). L'obiettivo è massimizzare Match 3+ rispetto al caso puro (Random: 5.19 M3+/1000).

## 🛠️ Sviluppo

### Aggiungere una nuova strategia
1. In `gateway/engine.py` → aggiungi metodo `def nuova_strategia(self)`
2. Registra in `genera_schedine()` → `'nuova': self.nuova_strategia`
3. In `web/index.html` → aggiungi `<option>` nel select strategie
4. Testa con: `py -3.14 test_new_strategies.py`
5. Aggiungi al backtest in `advanced_backtest.py` → `STRATEGIES` dict
6. Aggiorna `manuale_operativo.md` con risultati

### Aggiornare dati storici
1. Esegui `update_csv.ps1` (richiede API key valida)
2. Oppure usa scraping: `py -3.14 -c "from gateway.engine import SuperenalottoEngine; e=SuperenalottoEngine(); e.scrape_historical(pages=3); e._load_records()"`
3. Aggiungi manualmente a `superenalotto.csv` (formato: data,concorso,n1..n6,jolly,star)

### Eseguire backtest avanzato
```bash
py -3.14 advanced_backtest.py           # 15 strategie complete
py -3.14 common_denominator_analysis.py # Analisi pattern ricorrenti
```

## 🔒 Sicurezza
- API key in `config.json` (non committare mai valori reali)
- `.gitignore` consigliato per `config.json`

# SUPERENALOTTO - PROTOLLO SNIPER

## 🖥️ REQUISITI
- Python 3.x (tkinter incluso in stdlib)
- Windows PowerShell 5.1+
- 4238 estrazioni storiche in `superenalotto.csv`

## ⚡ AVVIO RAPIDO

1. Assicurati che `superenalotto.csv` sia nella stessa cartella
2. Avvia l'app: `python superenalotto_app.py`
3. Clicca "Genera Numeri" per schedine ottimizzate
4. Verifica con "Verifica Vince"

## 📊 STATISTICHE AUTOMATICHE
- Carica automaticamente le statistiche CSV all'avvio
- Aggiorna in tempo reale le schede recenti
- Mostra media somma, mediana, std dev

## 🎲 STRATEGIA DI GENERAZIONE
- Somma target: media ±30 (es. 245-305)
- Max 2 numeri per decade
- Max 1 numero >80
- Distribuzione uniforme primi/estremi

## 🔍 TRACKING & LIMITI
- `tracking.csv`: salva ogni schedina con data, somma, numeri
- `daily_limit.csv`: limite 2 schedine al giorno
- `sniper.ps1`: protocollo di generazione avanzata
