# SuperEnalotto - Protocollo Sniper

**Strumento avanzato di analisi statistica e generazione numeri per SuperEnalotto**, basato su 4226 estrazioni storiche (1997-2026). Include strategie ottimizzate (Hot-Cold, Position-Based, Anti-Recent) e backtest completo.

## 🗂️ Struttura Files

```
Superenalotto/
├── superenalotto.csv          # Archivio 4226 estrazioni storiche
├── superenalotto_app.py       # App GUI principale (Python tkinter)
├── superenalotto_gui.ps1      # GUI PowerShell alternativa
├── config.json                # Configurazione API (lotteryresultsfeed.com)
├── tracking.csv               # Schedine giocate + risultti
├── daily_limit.csv            # Contatore schedine giornaliere
├── analisi_completa.ps1       # Analisi statistica completa (4226 record)
├── analisi_completa.json      # Output JSON analisi
├── backtest.ps1               # Logica backtest strategie
├── backtest_results.txt       # Report backtest (3 strategie, 800 draws)
├── backtest_result.json       # Output JSON backtest
├── backtest_full_4226.ps1     # Backtest completo (4226 draws, 5 strategie)
├── hot_cold_strategy.ps1      # Strategia ottimizzata Hot-Cold
├── hot_cold_config.json       # Configurazione strategia Hot-Cold
├── sniper.ps1                 # Protocollo Sniper (generazione schedine)
├── update_csv.ps1             # Aggiornamento CSV da API
├── manuale_operativo.md       # Manuale completo
└── requirements.txt           # Dipendenze (stdlib-only)
```

## 🚀 Quick Start

### GUI Python
```bash
python superenalotto_app.py
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

## 📊 Statistiche Chiave (4226 estrazioni)

| Metrica | Valore |
|---------|--------|
| Media Somma | 276.37 |
| Mediana | 277 |
| Std Dev | 61.94 |
| Min / Max | 81 / 467 |
| Primi | 26.23% |
| >31 | 66.36% |
| >80 | 11.78% |
| Pari | 49.55% |

## 🎯 Strategie

1. **Random** - Baseline casuale puro
2. **OriginalConstraints** - Somma ±30, max 2 per decade, max 1 >80
3. **HotColdOptimized** - Mix di numeri frequenti (hot) e rari (cold)
4. **AntiRecent** - Evita numeri estratti recentemente (ultime 5)
5. **PositionBased** - Favorisce numeri per posizione

## ⚡ Risultati Backtest (800 draws, 2 biglietti/draw = 1600 biglietti)

```
Random:                 -€1,600 (ROI: 6.25%)
OriginalConstraints:     -€1,540 (ROI: 6.25%)
HotColdOptimized:        -€1,450 (ROI: 6.50%)  ← Migliore
```

> Nota: Tutte le strategie perdono matematicamente (house edge ~65%). I risultati sono usati solo per ottimizzare la frequenza di Match 3+ rispetto al caso puro.

## 🛠️ Sviluppo

### Aggiungere una nuova strategia
1. Modifica `backtest_full_4226.ps1` → Aggiungi funzione `Test-NuovaStrategia`
2. Aggiungi all'array `$strategies`
3. Testa con: `powershell -ExecutionPolicy Bypass -File "backtest_full_4226.ps1"`
4. Aggiorna `manuale_operativo.md` con risultati

### Aggiornare dati storici
1. Esegui `update_csv.ps1` (richiede API key valida)
2. Oppure aggiungi manualmente a `superenalotto.csv` (formato: data,concorso,n1..n6,jolly,star)

## 🔒 Sicurezza
- API key in `config.json` (non committare mai valori reali)
- `.gitignore` consigliato per `config.json`

# SUPERENALOTTO - PROTOLLO SNIPER

## 🖥️ REQUISITI
- Python 3.x (tkinter incluso in stdlib)
- Windows PowerShell 5.1+
- 4226 estrazioni storiche in `superenalotto.csv`

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
