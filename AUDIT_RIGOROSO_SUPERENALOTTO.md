# AUDIT COMPLETO DEGLI ALGORITMI E DEI MODELLI DEL SUPERENALOTTO

**Data generazione:** 08/09/2026 08:26  
**Estrazioni analizzate:** 4238  
**Intervallo dati:** 1997-12-03 → 2026-09-04  
**Metodologia:** backtest walk-forward out-of-sample (niente data snooping)  
**Dipendenze:** solo libreria standard Python

---

## ⚠️ Avviso preventivo (obbligatorio)

> Le estrazioni del SuperEnalotto sono **casuali, indipendenti e a distribuzione uniforme**. Nessun algoritmo, calcolatore probabilistico o modello statistico può prevedere l'esito di una estrazione né migliorare la probabilità di vincita di un singolo biglietto. Questo documento **non promuove il gioco** e ne documenta la reale natura matematica (house edge ~60–67%). Giocare comporta una perdita attesa certa nel lungo periodo.

## 1. Struttura del gioco e probabilità esatte

- Spazio campionario: 6 numeri estratti senza reinserimento da 1–90.
- Combinazioni totali: C(90,6) = **622.614.630**
- Probabilità per categoria di vincita (calcolo esatto):

| Combinazione | Probabilità | 1 su |
|---|---|---|
| 6 | 0.000000% | 622.614.630 |
| 5+J | 0.000001% | 103.769.105 |
| 5 | 0.000081% | 1.235.346 |
| 4 | 0.008398% | 11.907 |
| 3 | 0.306077% | 327 |
| 2 | 4.648544% | 22 |
| ≥3 (cum) | 0.3146% | 318 |

## 2. Valore atteso (EV) e house edge

Formula (premi medi ADM, costo €1):

```
EV = P(2)*5 + P(3)*25 + P(4)*296 + P(5)*25847 + P(5+J)*100000 + P(6)*1000000

EV ≈ €0.33
House edge ≈ 1 - 0.33 = ~67%
```

**Implicazione:** per ogni €1 giocato, in media si ricevono ~€0.33–0.40. Il ritorno è garantito negativo a meno di vincite straordinarie il cui costo atteso non viene recuperato.

## 3. Verifica di uniformità delle estrazioni

- Min frequenza per numero: **241**
- Max frequenza per numero: **325**
- Frequenza media attesa: **282.53**
- Chi-quadrato: **93.02** (df=89), p = 0.36449
- Esito: **nessuna deviazione statisticamente significativa dall'uniforme (p>=0.05)**

Se il test non è significativo, le estrazioni sono compatibili con un processo di Bernoulli uniforme: nessun numero è intrinsecamente 'caldo' o 'freddo'.

## 4. Backtest out-of-sample — risultati quantitativi

Il backtest valuta ogni strategia su estrazioni **mai viste durante l'addestramento** (walk-forward con rolling train), quindi i risultati NON sono gonfiati da data snooping.

| Strategia | Speso € | Vinto € | Netto € | ROI % | M3+/1000 | vs Random (M3+) | p-val (FDR) | 
|---|---|---|---|---|---|---|---|
| HotCold | 3938 | 1977.00 | -1961.00 | -49.8% | 4.317 | +0.51 | 0.964179 — |
| QuartileSpread | 3938 | 1646.00 | -2292.00 | -58.2% | 3.809 | +0.00 | 1.0 — |
| GapSpread | 3938 | 1596.00 | -2342.00 | -59.47% | 3.809 | +0.00 | 1.0 — |
| MixQuartileHotCold | 3938 | 1571.00 | -2367.00 | -60.11% | 3.301 | -0.51 | 0.964179 — |
| PoissonModel | 3938 | 1546.00 | -2392.00 | -60.74% | 3.047 | -0.76 | 0.964179 — |
| Random | 3938 | 1531.00 | -2407.00 | -61.12% | 3.809 | +0.00 | 1.0 — |
| Ensemble | 3938 | 1516.00 | -2422.00 | -61.5% | 3.555 | -0.25 | 1.0 — |
| MiddleFrequency | 3938 | 1386.00 | -2552.00 | -64.8% | 2.285 | -1.52 | 0.964179 — |
| MarkovChain | 3938 | 1335.00 | -2603.00 | -66.1% | 3.809 | +0.00 | 1.0 — |
| ComplementMirror | 3938 | 1330.00 | -2608.00 | -66.23% | 4.571 | +0.76 | 0.964179 — |
| AntiPopular | 3938 | 1310.00 | -2628.00 | -66.73% | 3.047 | -0.76 | 0.964179 — |
| FibonacciWheel | 3938 | 1305.00 | -2633.00 | -66.86% | 3.555 | -0.25 | 1.0 — |
| MixHotColdPrime | 3938 | 1295.00 | -2643.00 | -67.12% | 2.793 | -1.02 | 0.964179 — |
| SumLocked | 3938 | 1280.00 | -2658.00 | -67.5% | 2.539 | -1.27 | 0.964179 — |
| AntiRecent | 3938 | 1255.00 | -2683.00 | -68.13% | 3.301 | -0.51 | 0.964179 — |
| PrimeFocus | 3938 | 1190.00 | -2748.00 | -69.78% | 2.793 | -1.02 | 0.964179 — |
| WheelCoverage | 3938 | 1165.00 | -2773.00 | -70.42% | 2.285 | -1.52 | 0.964179 — |
| Mix | 3938 | 1125.00 | -2813.00 | -71.43% | 2.793 | -1.02 | 0.964179 — |
| Adaptive | 3938 | 1115.00 | -2823.00 | -71.69% | 3.301 | -0.51 | 0.964179 — |
| MLPattern | 3938 | 1110.00 | -2828.00 | -71.81% | 2.793 | -1.02 | 0.964179 — |
| Optimized | 3938 | 1015.00 | -2923.00 | -74.23% | 2.285 | -1.52 | 0.964179 — |

> **Lettura:** il ROI è negativo per TUTTE le strategie (atteso). Le differenze nel tasso M3+/1000 sono generalmente NON statisticamente significative dopo la correzione per confronti multipli. Qualsiasi apparente miglioramento è rumore statistico.

## 5. Cause strutturali delle perdite nelle strategie

- **House edge (~67%)** — Il montepremi distribuisce solo ~60% delle giocate; il resto è margine del concessionario e copertura costi.
- **Indipendenza delle estrazioni** — Ogni estrazione è indipendente: i numeri passati non influenzano i futuri.
- **Fallacia del giocatore** — Strategie 'caldi/freddi', 'ritardatari', 'pattern' incorporano errori logici (gambler's fallacy).
- **Data snooping / overfitting** — Strategie ottimizzate sul passato perdono efficacia sul futuro (walk-forward lo dimostra).
- **Dimensione campione insufficiente** — Servirebbero miliardi di estrazioni per osservare convergenza/divergenze.

## 6. Criteri di successo dei backtest

Un backtest si considera 'riuscito' solo se soddisfa TUTTI i seguenti criteri:

1. **Walk-forward fuori campione** — i parametri non devono mai vedere i dati di test.
2. **Significatività statistica** — p < 0.05 dopo correzione per confronti multipli (FDR/Bonferroni).
3. **ROI positivo** — è il criterio economico decisivo; finora nessuna strategia lo supera.
4. **Stabilità** — le prestazioni non devono scomparire cambiando finestra di test.
5. **Consistenza teorica** — deve esistere un meccanismo plausibile, non un pattern casuale.

> In nessun backtest effettuato questi criteri sono soddisfatti simultaneamente.

## 7. Limiti intrinseci del gioco

- **Randomness certificato** — RNG certificati da ADM per estrazioni uniformi.
- **Indipendenza** — Nessuna memoria o persistenza di pattern.
- **Evento rarissimo** — Jackpot: 1 su 622.614.630; in una vita di ~10.000 estrazioni la probabilità di vincere il 6 è ~1 su 62.000.

## 8. Misure di gioco responsabile (obbligatorie)

- **Impostare un budget di spesa fisso e mai superarlo.**
- **Inserire limiti giornalieri/settimanali/mensili (es. €2/estrazione, €20/settimana).**
- **Mostrare sempre l'avviso del house edge (67%) e la probabilità di vincita.**
- **Imporre un 'reality check' temporale e un periodo di raffreddamento dopo perdite.**
- **Vietare il recupero delle perdite ('inseguire' le perdite).**
- **Non giocare mai denaro destinato a spese essenziali o prestiti.**
- **Rivolgersi a supporto specializzato (Giocatori Anonimi, gambling therapy) ai primi segnali.**
- **Non utilizzare mai l'autoesclusione in modo aggirato (ROCCA).**

Risorse ufficiali di supporto:

- **ADM (Agenzia delle Dogane e dei Monopoli)** — regolatore nazionale del gioco.
- **Gambling Therapy / Giocatori Anonimi** — assistenza per disturbo da gioco.
- **Auto-esclusione (ROCCA)** — registro nazionale per l'auto-proibizione dal gioco.

## 9. Sostenibilità economica delle strategie

| Strategia | Sostenibilità economica | Verdetto |
|---|---|---|
| HotCold | ROI -49.8% | NON sostenibile (ROI negativo) |
| QuartileSpread | ROI -58.2% | NON sostenibile (ROI negativo) |
| GapSpread | ROI -59.47% | NON sostenibile (ROI negativo) |
| MixQuartileHotCold | ROI -60.11% | NON sostenibile (ROI negativo) |
| PoissonModel | ROI -60.74% | NON sostenibile (ROI negativo) |
| Random | ROI -61.12% | NON sostenibile (ROI negativo) |
| Ensemble | ROI -61.5% | NON sostenibile (ROI negativo) |
| MiddleFrequency | ROI -64.8% | NON sostenibile (ROI negativo) |
| MarkovChain | ROI -66.1% | NON sostenibile (ROI negativo) |
| ComplementMirror | ROI -66.23% | NON sostenibile (ROI negativo) |
| AntiPopular | ROI -66.73% | NON sostenibile (ROI negativo) |
| FibonacciWheel | ROI -66.86% | NON sostenibile (ROI negativo) |
| MixHotColdPrime | ROI -67.12% | NON sostenibile (ROI negativo) |
| SumLocked | ROI -67.5% | NON sostenibile (ROI negativo) |
| AntiRecent | ROI -68.13% | NON sostenibile (ROI negativo) |
| PrimeFocus | ROI -69.78% | NON sostenibile (ROI negativo) |
| WheelCoverage | ROI -70.42% | NON sostenibile (ROI negativo) |
| Mix | ROI -71.43% | NON sostenibile (ROI negativo) |
| Adaptive | ROI -71.69% | NON sostenibile (ROI negativo) |
| MLPattern | ROI -71.81% | NON sostenibile (ROI negativo) |
| Optimized | ROI -74.23% | NON sostenibile (ROI negativo) |

**Conclusione economica:** nessuna strategia è economicamente sostenibile. Giocare deve essere considerato esclusivamente un costo di intrattenimento con budget predefinito, mai un investimento.

## 10. Roadmap operativa

### Fase 1 — Consolidamento (ora)

- [ ] Esporre il house edge (67%) in evidenza nell'interfaccia.
- [ ] Mostrare la probabilità reale di vincita per ogni categoria.
- [ ] Aggiungere limite giornaliero di spesa (default €2/estrazione).
- [ ] Mostrare warning 'reality check' durante la sessione di gioco.
- [ ] Collegare a risorse di supporto (Giocatori Anonimi, ADM).

### Fase 2 — Strumenti di protezione (3–6 mesi)

- [ ] Implementare limiti di spesa opzionali personalizzabili.
- [ ] Aggiungere limiti di tempo di sessione e cooldown dopo perdite.
- [ ] Sistema di monitoraggio comportamentale (rileva pattern a rischio).
- [ ] Integrazione con il registro nazionale di auto-esclusione ROCCA.

### Fase 3 — Ricerca e trasparenza (6–12 mesi)

- [ ] Pubblicare i risultati dei backtest come documento di trasparenza.
- [ ] Documentare l'insussistenza di vantaggi predittivi.
- [ ] Collaborazione con enti di ricerca sul gioco responsabile.

---
## Metadati tecnici

- Strategie testate: **21**
- Modello di valutazione: walk-forward out-of-sample, train=300, block test=200
- Test statistici: binomiale esatto, z-test proporzioni, chi-quadrato, correzioni Bonferroni e Benjamini-Hochberg
- Scopo del documento: trasparenza e prevenzione; esclude ogni finalità promozionale.
