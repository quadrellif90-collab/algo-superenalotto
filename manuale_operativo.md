# MANUALE OPERATIVO QUANTITATIVO — SUPERENALOTTO
## Architettura di Ingegneria della Varianza Combinatoria

---

## DATI DI RIFERIMENTO

| Parametro | Valore |
|-----------|--------|
| Estrazioni analizzate | 4.193 (03/12/1997 — 28/08/2026) |
| Campo numerico | 1–90 |
| Numeri per estrazione | 6 |
| Combinazioni totali | 622.614.630 |
| Prezzo base (6 numeri) | €1,00 |
| Jackpot medio storico | €46.5M+ |
| API Key | 170961\|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d |
| Lottery ID | 712 |

---

## FASE 1 — EFFICIENZA COMBINATORIA

### 1.1 Architettura Sistemi Ridotti

I sistemi ridotti coprono un sottoinsieme strategico delle combinazioni totali, ottimizzando il rapporto copertura/costo.

| Sistema | Numeri giocati | Combinazioni | Costo | Copertura teorica |
|---------|---------------|--------------|-------|------------------|
| Ridotto R0 | 8 | 28 | €28 | 9,8% (2 if >=5 match) |
| Ridotto R1 | 9 | 84 | €84 | 29,4% (2 if >=5 match) |
| Ridotto R2 | 10 | 210 | €210 | 73,5% (2 if >=5 match) |
| Ridotto R3 | 11 | 462 | €462 | 100% (3 if >=4 match) |
| Ridotto R4 | 12 | 924 | €924 | 100% (4 if >=4 match) |

### 1.2 Matrice di Decisione Costo/Beneficio

```
Budget diario massimo: €2,00 (limite fermo su app)

SE budget == €1:
    → 1 schedina da 6 numeri
    → Focus: somma 240-320, max 2 per decade

SE budget == €2:
    → 2 schedine da 6 numeri
    → Ogni schedina con seed diverso
    → Max 2 per giorno (limite applicato)
```

### 1.3 Criteri di Selezione Fase 1

```
PER OGNI ESTRAZIONE:
    1. Calcola somma dei 6 numeri
    2. ACCETTA solo se: 240 <= somma <= 320
    3. VERIFICA distribuzione decadi: max 2 per decade
    4. EVITA: 3+ numeri dalla stessa decade
    5. PREFERISCI: almeno 2 numeri > 31, max 1 numero > 80
    6. VERIFICA cifra finale: max 2 con stessa cifra
```

---

## FASE 2 — ANALISI ANTI-UMANA DELL'ARCHIVIO

### 2.1 Profilo Statistico Storico

| Metrica | Valore |
|---------|--------|
| **Somma media** | 276,64 |
| **Somma mediana** | 277 |
| **Deviazione std** | 61,95 |
| **Somma minima storica** | 81 |
| **Somma massima storica** | 467 |
| **Q1 (25° percentile)** | 234 |
| **Q3 (75° percentile)** | 319 |
| **Range** | 386 |
| **IQR** | 85 |

### 2.2 Distribuzione Gaussian Approximation

| Intervallo σ | Copertura attesa | Copertura osservata |
|--------------|-----------------|---------------------|
| μ ± 1σ (214,77–338,67) | 68,27% | 67,87% |
| μ ± 2σ (152,82–400,62) | 95,45% | 95,46% |

**Conclusione:** La distribuzione delle somme è normalmente distribuita con alta precisione.

### 2.3 Top 10 Fasce di Somma (bucket 20)

| Fascia | Estrazioni | Frequenza |
|--------|-----------|-----------|
| 260–279 | 548 | 13,10% |
| 280–299 | 494 | 11,81% |
| 300–319 | 491 | 11,74% |
| 240–259 | 459 | 10,97% |
| 220–239 | 397 | 9,49% |
| 320–339 | 379 | 9,06% |
| 200–219 | 314 | 7,51% |
| 340–359 | 285 | 6,81% |
| 180–199 | 189 | 4,52% |
| 360–379 | 152 | 3,63% |

### 2.4 Distribuzione Decadi

| Decina | Range | Frequenza |
|--------|-------|-----------|
| 0 | 1–9 | 9,85% |
| 1 | 10–19 | 10,79% |
| 2 | 20–29 | 10,68% |
| 3 | 30–39 | 10,94% |
| 4 | 40–49 | 11,38% |
| 5 | 50–59 | 11,02% |
| 6 | 60–69 | 11,15% |
| 7 | 70–79 | 11,19% |
| 8 | 80–89 | 11,85% |

**Media decina:** 4,16 → Distribuzione uniforme.

### 2.5 Distribuzione Cifre Finali

| Cifra | Frequenza |
|-------|-----------|
| 0 | 9,75% |
| 1 | 10,21% |
| 2 | 10,10% |
| 3 | 9,92% |
| 4 | 9,63% |
| 5 | 10,36% |
| 6 | 10,06% |
| 7 | 9,93% |
| 8 | 9,98% |
| 9 | 10,07% |

**Entropia Shannon:** 3,3216 bit (max teorico: 3,3219 bit)
**Conclusione:** Distribuzione perfettamente uniforme.

### 2.6 Classificazione Numeri

| Categoria | Definizione | Frequenza |
|-----------|-------------|-----------|
| **Primi** | Numeri primi ≤90 | 26,28% |
| **Estremi** | 76–90 | 17,61% |
| **>31** | Numeri > 31 | 66,56% |
| **>80** | Numeri 81–90 | 11,81% |
| **Dispari** | Numeri dispari | 51,38% |
| **Pari** | Numeri pari | 48,62% |

---

## FASE 3 — ARCHITETTURA DI ACCUMULO

### 3.1 Piano di Accumulo Strategico

```
OBIETTIVO: Max €2/estrazione | Giorni: Mar/Gio/Ven/Sab
Budget settimanale max: €8
Budget mensile max: €32

CICLO DI ACCUMULO:
    Settimana 1-4:   €8/settimana → €32
    Settimana 5-8:   €8/settimana → €64 (totale €96)
    Settimana 9-12:  €8/settimana → €96 (totale €192)

TRIGGER AUMENTO GIOCATA:
    SE jackpot >= €100M AND budget >= €50:
        → AUMENTA a €5/estrazione per 4 estrazioni
        → TORNA a €2 dopo o se jackpot scende

TRIGGER STOP:
    SE 12 perdite consecutive:
        → PAUSA 1 settimana
        → RIPARTI con stesso budget
```

### 3.2 Matrice di Allocazione per Jackpot

| Jackpot | Budget | Strategia |
|---------|--------|-----------|
| < €10M | €1-2 | 1 schedina singola |
| €10M–€50M | €2 | 2 schedine |
| €50M–€100M | €5-10 | Sistema ridotto 8 |
| > €100M | €10-20 | Sistema ridotto 9 |

---

## FASE 4 — CAMPO BASE

### 4.1 Regelazione Anti-Mercato

```
REGOLE DI ESCLUSIONE:
    1. EVITA numeri consecutivi (1-2-3-4-5-6)
    2. EVITA >2 numeri per decade
    3. EVITA somma fuori range 240-320
    4. EVITA >1 numero >80
    5. EVITA pattern simmetrici (somma opposti ≠ 91)
    6. EVITA >2 numeri con stessa cifra finale
```

### 4.2 Algoritmo di Generazione (High-Entropy Model)

```
INPUT: seed = data_corrente (YYYYMMDD)
OUTPUT: 2 schedine da 6 numeri (budget €2)

FASE A: Genera 6 numeri unici 1-90
FASE B: Filtra → somme 240-320, max 2/decade, max 1 >80
FASE C: Se invalido, rigenera (max 1000 tentativi)
FASE D: Salva in tracking.csv con data e somma
```

### 4.3 Esempio Campo Base (29/08/2026)

```
SCHEDINA A: {11, 19, 28, 37, 48, 62} → somma = 205
SCHEDINA B: {15, 24, 33, 41, 52, 65} → somma = 230
```

---

## FASE 5 — PROTOCOLLO SNIPER GIORNALIERO

### 5.1 Flusso Decisionale Pre-Estrazione

```
FUNCTION SnipeDaily():
    data = Get-Date -Format "yyyy-MM-dd"
    giorno = (Get-Date).DayOfWeek
    
    SE giorno NOT IN [Tuesday,Thursday,Friday,Saturday]:
        RETURN "Nessuna estrazione oggi"
    
    SE -not FileExists(tracking.csv):
        Initialize-Tracking()
    
    SE GetTodayPlayed() >= 2:
        RETURN "Limite giornaliero raggiunto"
    
    schedine = Generate-Schedine(2, data)
    Save-Tracking(schedine)
    
    RETURN schedine
```

### 5.2 Limite Giornaliero

```
daily_limit.csv:
    data,schedine_giocate
    2026-08-29,2
    2026-08-27,2

Logica:
    Ciascun giorno = max 2 schedine
    Se oggi ha già 2 → blocco generazione
    Il file viene aggiornato automaticamente
```

### 5.3 Post-Estrazione

```
FUNCTION CheckResult(data):
    ultima = ReadLastDraw()
    match = CountMatch(schedine, ultima)
    
    SE match >= 3:
        NOTIFY("VINCITA: $match numeri")
    
    SE match == 6:
        NOTIFY("JACKPOT!")
```

---

## FASE 6 — ESPORTAZIONE RECORD

### 6.1 Struttura Export

```
Esporta i dati in formato CSV:

tracking.csv:
    data,giornata,budget,schedine,numeri,somma,jackpot
    2026-08-29,Saturday,1.00,1,11-19-28-37-48-62,205,89400000
    2026-08-27,Thursday,1.00,1,15-24-33-41-52-65,230,87600000
```

### 6.2 Report di Riepilogo

```
Report settimanale (generato sabato):

SUPERENALOTTO — REPORT
Settimana: [data range]
Estrazioni giocate: X/4
Speso: €Y
Vincite: €Z
ROI: W%
Jackpot: €JJJ
Prossima estrazione: [data]
```

---

## FASE 7 — AGGIORNAMENTO QUOTIDIANO

### 7.1 Flusso Aggiornamento Automatico

```
1. APRIRE app → carica automaticamente CSV e stats
2. Se è giorno di estrazione → mostra alert
3. Generare le schedine (max 2) → verifica VINCITA
4. Alla fine della settimana → replay tracking
```

### 7.2 Stat Summary Menu

```
Statistiche principali nell'app:
    - Media/Mediana/StdDev somme
    - Q1/Q3 Range
    - % Primi, Estremi (76-90)
    - Cifre finali distribuite
    - Decadi distribuite
    - Top 10 fasce somme
    - Estrazioni per anno
```

---

## SCHEMA RIASSUNTIVO

```
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1: EFFICIENZA COMBINATORIA                                │
│  → Max 2 schedine da 6 numeri (€2/estrazione)                 │
│  → Usa sistemi ridotti solo per jackpot >€50M                  │
├─────────────────────────────────────────────────────────────────┤
│  FASE 2: ANALISI ANTI-UMANA                                    │
│  → Somma target: 240-320 (μ ± 0,6σ)                           │
│  → Distribuzione uniforme: max 2/decade                        │
│  → Evita pattern umani: consecutivi, stesse cifre finali       │
├─────────────────────────────────────────────────────────────────┤
│  FASE 3: ACCUMULO                                              │
│  → €2/estrazione × 4 estrazioni/settimana = €8/settimana      │
│  → Trigger jackpot >€100M: aumenta a €5/estrazione            │
│  → Stop trigger: 12 perdite consecutive → pausa 1 settimana    │
├─────────────────────────────────────────────────────────────────┤
│  FASE 4: CAMPO BASE                                            │
│  → Modello High-Entropy: 2 schedine seed-based                 │
│  → Per €2: 2 schedine da 6 numeri singoli                    │
│  → Per €10+: sistema ridotto 9 numeri (12 combinazioni)        │
├─────────────────────────────────────────────────────────────────┤
│  FASE 5: PROTOCOLLO SNIPER                                     │
│  → Mar/Gio/Ven/Sab: Generate-Schedine(2)                      │
│  → Controllo daily_limit.csv: max 2 al giorno                  │
│  → Post-estrazione: CheckResult(), aggiorna tracking           │
│  → Sabato: report settimanale                                  │
├─────────────────────────────────────────────────────────────────┤
│  FASE 6: ESPORTAZIONE                                          │
│  → tracking.csv con tutti i numeri giocati                     │
│  → Report settimanale in formato testo                         │
│  → Esportazione facile da analizzare                            │
├─────────────────────────────────────────────────────────────────┤
│  FASE 7: AGGIORNAMENTO                                         │
│  → App si aggiorna stessa con CSV e stats                      │
│  → Ricalcola automaticamente al caffeina                       │
│  → Stats UI aggiornata con avg/mediana/stddev                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## DISCLAIMER MATEMATICO

Questo documento fornisce strumenti per l'ingegneria della varianza combinatoria e l'ottimizzazione dell'EV.

- **Nessuna predizione** è effettuata o garantita
- Ogni numero ha probabilità uguale (1/622M per 6 uguali)
- Il banco ha sempre un vantaggio strutturale
- Gioca solo ciò che puoi permetterti di perdere
- Verifica le regole ufficiali Sisal prima di giocare

---

*Documento generato: 29/08/2026*
*Dataset: 4.193 estrazioni SuperEnalotto (1997-2026)*
*App: superenalotto_gui.ps1 — Algoritmo: High-Entropy Sniper*
*Repository: https://github.com/quadrellif90-collab/algo-superenalotto*
