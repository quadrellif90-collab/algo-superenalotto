# PIANO STRATEGICO — SuperEnalotto (v8.6+)

**Data:** 08/09/2026
**Stato del progetto:** unificato e pulito (commit `37f0932` + `ad6859b`)
**Documento base:** analisi completa del codice sorgente (`launcher.py`, `gateway/engine.py`, `gateway/server.py`, `web/*`, `.spec`, `requirements.txt`) e dell'audit rigoroso (`AUDIT_RIGOROSO_SUPERENALOTTO.md`).

---

## ⚠️ Premessa etica e tecnica (vincolante per tutto il piano)

L'audit rigoroso out-of-sample (4238 estrazioni, walk-forward senza data snooping) ha stabilito **senza ambiguità**:

- Le estrazioni sono **compatibili con un processo casuale uniforme** (chi² = 93.02, df = 89, p = 0.364): nessun numero è intrinsecamente "caldo" o "freddo".
- **Tutte le 16 strategie** di generazione hanno pFDR 0.96–1.0 → **nessuna è statisticamente migliore del caso**.
- **ROI negativo garantito** (peggiore Optimized −74%, migliore HotCold −50%): house edge ~67%. Ogni €1 restituisce ~€0.33 in media.
- Combinaioni totali: C(90,6) = 622.614.630; probabilità "6" = 1 su 622 milioni.

**Conseguenza strategica:** qualsiasi piano che prometta "previsione della vincita" o "algoritmi che batteranno il gioco" è **tecnicamente falso ed eticamente irresponsabile**. Il valore reale dell'app va quindi ri-centrato su **esperienza d'uso, trasparenza, privacy, educazione (gioco responsabile), analisi descrittiva e automazione**. Le "previsioni" vanno presentate come **simulazione statistica di scenario**, mai come certezza.

Questa premessa è il fondamento su cui sono costruite tutte le sezioni seguenti.

---

## 1. ANALISI PRELIMINARE E DEFINIZIONE DELLE PRIORITÀ

### 1.1 Audit dello stato attuale

| Area | Stato attuale | Criticità | Opportunità |
|---|---|---|---|
| **UI/UX** | Sidebar 8 tab, tema verde (CSS vars), 3 colonne nel tab "Gioca" | Responsive debole (solo breakpoint 1200px); il tab "Gioca" usa `display:grid` a 3 colonne fisse → estremamente fragile su finestre piccole; nessun tema scuro; `alert()`/`confirm()` nativi per feedback | Rifattorizzazione responsive completa, tema scuro, componenti accessibili, notifiche toast non bloccanti |
| **Prestazioni** | Engine carica 4238 estrazioni in RAM; stats ricalcolate a ogni `_load_records`; API `ThreadingHTTPServer`; frontend vanilla sincrono | Tempo dipende da O(n) per strategie; `resolve_auto_strategy()` → `get_dynamic_ranking()` esegue 16 backtest × n estrazioni **stringendo un lock** (blocca le richieste concorrenti); frontend fa 8+ fetch sequenziali all'avvio | Caching Redis-lite in memoria, caricamento lazyload dei tab, prefetch, conteggi incrementali, separazione lock read/write |
| **Calcolatori** | `genera_schedine()`, `valuta_strategie()` (STUB: simula ROI su QuartileSpread), `run_backtest()`, `get_dynamic_ranking()` | `valuta_strategie()` è chiaramente un placeholder (ROI "spento/vinto" naive); nessun report esportabile; nessuna elaborazione batch avanzata | Riscrivere `valuta_strategie` come simulazione Monte Carlo seria con confidenze; report CSV/PDF esportabili; pannello "Ricerca di sistema" |
| **Algoritmi** | 16 strategie euristiche deterministiche + RNG `secrets.SystemRandom` | Tutte **non significative** (audit) ma presentate come "previsioni" nella UI; niente suite di test automatici per l'engine | Trasformare in **simulatore trasparente** con metrica di "coerenza col caso" mostrata onestamente; suite pytest completa |
| **Architettura** | Backend Python monolitico + frontend vanilla separato via HTTP locale; binary PyInstaller | Accoppiamento frontend/backend via URL hardcoded `8766`; nessuna separazione di servizi; nessuna unit-test coverage | Moduli API versionati (`/api/v1`), plugin strategy registry, test di contratto con OpenAPI |

### 1.2 Matrice priorità (impatto × fattibilità)

| # | Intervento | Impatto utente | Fattibilità | Priorità |
|---|---|---|---|---|
| P0 | Fix `valuta_strategie` stub + onestà scientifica nella UI | Alto | Alta | **Critica** |
| P0 | Responsive + tema scuro + accessibilità (A11y) | Alto | Alta | **Critica** |
| P1 | Performance startup (prefetch/cache/concorrenza) | Alto | Media | Alta |
| P1 | Suite di test automatici (unità + integrazione) | Medio (affid.) | Alta | Alta |
| P1 | Export report (CSV/PDF) + pannello Monte Carlo | Medio | Media | Alta |
| P2 | Intrattenimento responsabile (limiti, timeout, info) | Alto (etica) | Alta | Media |
| P2 | Notifiche real-time (WebSocket) | Medio | Media | Media |
| P3 | Personalizzazione (tema, preferenze salvate) | Medio | Alta | Media |
| P3 | Collaborazione / cloud (prototipo) | Basso | Bassa | Bassa |

### 1.3 Metriche di successo

| Intervento | Metrica obiettivo |
|---|---|
| Startup app (finestra visibile) | < 2 s (oggi ~3–5 s con 8 fetch sequenziali) |
| Switch tab | < 100 ms di latenza percepita |
| `resolve_auto_strategy` (16 backtest) | < 800 ms (oggi secondi sotto lock) |
| Caricamento pagina "Gioca" | < 1.5 s / < 2 MB trasferiti |
| Test coverage engine | ≥ 85% da ~0% |
| Soddisfazione utente | NPS rilevato via sondaggio in-app ≥ 30 |
| Accessibilità | WCAG 2.1 AA su tutti gli 8 tab esistenti |
| Precisione calcoli | 100% su suite di regressione (nessun delta) |

---

## 2. MIGLIORAMENTI DELLA UI/UX

### 2.1 Ridisegno dell'interfaccia
- **Design token unificati**: estendere le CSS custom properties con palette (tema chiaro + **tema scuro**), spaziatura, tipografia e stati (hover/focus/error). Premessa già ben avviata in `:root`.
- **Layout responsive a griglia fluida**: sostituire la grid a 3 colonne fisse del tab "Gioca" con `grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))` + breakpoint progressivi (≤ 900 px, ≤ 600 px). Oggi vi è un solo breakpoint a 1200 px (insufficiente).
- **Header "informativo" e unificato**: spostare JACKPOT e prossima estrazione in una barra sticky compatta, non confonderli con azioni.
- **Componenti ricorrenti**: `data-table`, `stat-card`, `toast`, `modal`, `tooltip` riusabili (oggi tutto inline/duplicato).

### 2.2 Flussi semplificati
- **Flusso "Gioca" in 3 passi visibili** (1. scegli quantità → 2. genera → 3. salva) con una **wizard leggera** invece di una sola pagina densa.
- **Eliminare i `confirm()` nativi** per azioni distruttive (cancella giocata, clear tutti, restore backup) a favore di finestre di dialogo accessibili e keyboard-friendly.
- **Auto-verifica con notifica in toast**, non apre modal senza richiesta esplicita.
- **Accesso rapido**: tasto "Verifica + Salva" combinato dove sensato.

### 2.3 Personalizzazione
- **Preferenze persistenti** (localStorage `/web/` o `config.json`): tema chiaro/scuro, dimensione font, tab di avvio, quantità schedine predefinita.
- **Dashboard personalizzabile**: ordine/visibilità dei tab; riordino tramite drag & drop (prototipo).

### 2.4 Test di usabilità
- Sessione di test **guidata con 5 utenti reali** seguendo le euristiche Nielsen (10 punti); registrare task: "genera·salva·verifica·importa", "trova la strategia X", "ripristina un backup".
- Metriche: tasso di completamento task, errori per task, tempo per task, SUS (System Usability Scale) ≥ 70.
- Raccolta feedback in-app (modal semplice a 5 stelle + campo libero, una volta al mese).

---

## 3. SVILUPPO DI CALCOLATORI AVANZATI

> Integrando la premessa: i "calcolatori" divengono **strumenti di analisi e simulazione trasparenti**, non strumenti di previsione.

### 3.1 Pannello "Simulatore Monte Carlo" (nuovo)
- Sostituisce/estende lo stub `valuta_strategie()` con una vera simulazione:
  - N simulazioni (default 10.000) su dataset reale, restituendo **intervalli di confidenza** della vincita attesa.
  - Distribuzione dei "migliori" risultati: percentili 5/50/95.
  - Controllo massimo (spesso 6) → costi SaaS contenuti (vedi 3.5).
- Espone la **metrica "coerenza col caso"** (p-value del confronto con una strategia random): valore educativo, onesto.

### 3.2 "Ricerca di sistema" (calcolatore combinatorio)
- Presi N numeri selezionati dall'utente (es. 8–12), calcola il **sistema integrale** (tutte le combinazioni da 6) con:
  - Numero totale di colonne e costo.
  - **Sistema ridotto** ottimizzato (riduzione con garanzia di vincita) per ridurre il costo.
  - Report dettagliato: probabilità di "almeno N indovinati" per ogni livello, calcolato esattamente con combinatoria (già in parte disponibile in `PREMI_DEFAULT`/odds).
- Interfaccia a tabella interattiva + export.

### 3.3 Ripetizione di numeri / analisi descrittiva
- **Verifica incrociata di più giocate** simultanee rispetto a date multiple (pannello batch, oggi assente).
- Statistiche descrittive per tab: frequenze, ritardi ("late numbers"), co-occorrenze, heatmap (API `get_heatmap_data`/`get_trend_data` già esistono ma non sono esposte nella UI → collegarle).

### 3.4 Precisione e validazione
- **Validazione input centralizzata** già presente (`validate_numbers`, `validate_date`) → estenderla con messaggi chiari e feedback visivo inline (non solo errori in `toolStatus`).
- **Controlli incrociati**: verifica della somma dei numeri, controllo duplicati, sanity check ROI.
- **Suite di regressione** dei calcoli con fixture congelate (vedi §4.2).

### 3.5 Costo complessità
- La suite Monte Carlo e la ricerca di sistema ridotta sono implementabili **in sola stdlib** (`math.comb`, `itertools.combinations`, `random`), mantenendo intatto il requisito "solo dipendenze stdlib + pywebview". Nessuna nuova dipendenza pesante.

---

## 4. MIGLIORAMENTO DEGLI ALGORITMI E TEST PIÙ PROFONDI

### 4.1 Riprogettazione (onesta)
- Conservare le 16 strategie come **strumenti educativi/di varietà**, ma:
  - Rinominazione/esposizione nella UI con etichetta chiara: es. `HotCold — varietà (nessun vantaggio statistico dimostrato)`.
  - **Registry plugin** delle strategie (`STRATEGY_NAMES` diventa loader dinamico `strategies/registry.py`) → aggiungere/rimuovere strategie senza modificare `engine.py`.
  - **Motor generator estratto a modulo dedicato** `gateway/strategies.py` per isolare e testare.
- **Nuovo motore di "coerenza col caso"**: funzione che, per ogni strategia, restituisce p-value vs random (riusa i test statistici già scritti in `rigorous_backtest_audit.py`). Questo è il contributo matematico più solido e differenziante che possiamo produrre onestamente.

### 4.2 Suite di test automatici (pytest)
Sostituire i 4 test esistenti (`test_imports`, `test_game_logic`, `test_launcher`, `test_server`) con suite strutturata:
- **Unit test**: `test_engine.py` (statistiche, constraints, validazione numeri/date), `test_strategies.py` (ogni strategia ritorna 6 numeri unici 1–90 e rispetta i vincoli), `test_server.py` (gestione errori HTTP, payload >100 KB, JSON malformato).
- **Integration test**: flusso completo genera→salva→verifica→report su DB SQLite temporaneo (`:memory:` o tmp) — oggi i test girano su DB reale (fragile).
- **Load/stress test**: N=200 richieste concorrenti a `/api/genera` per misurare il tempo sotto lock e validare il fix di concorrenza (§5).
- **Proprietà (property-based)**: fuzzing delle strategie (1000 iterazioni) per garantire che non producano mai duplicati/invalidi.
- **Regressione calcoli**: fixture congelate (valori attesi) per `_calc_stats`, `verifica_giocata`, premi.

### 4.3 Precisione su grandi dataset
- Script `benchmark_precision.py`: confronto dei nuovi risultati con i valori attesi congelati dell'audit (4238 estrazioni): somma, media, chi² devono combaciare esattamente.
- Confronto strategia-vs-random su tutti i 4238 campioni (già prodotto dall'audit) riusato come **baseline di regressione**.

### 4.4 Auto-miglioramento (etico e limitato)
- **Learning dai dati reali con metriche trasparenti**: registrare (anonimizzato) il tasso di "match" storico delle giocate dell'utente per mostrare il ROI reale accumulato — e **non** per "affinare la previsione".
- **Feedback utente** per priorità di funzionalità (non per tuning di algoritmi, che è privo di fondamento).
- Ogni "auto-miglioramento" dell'engine è **escluso** (non esiste segnale da sfruttare); eventuali modifiche a strategie vanno sempre validate contro il benchmark random e la suite.

---

## 5. INCREMENTO DI VELOCITÀ E USABILITÀ GENERALE

### 5.1 Startup e risposta
- **Lazy-load dei tab**: all'avvio carica solo il tab attivo; gli altri tab montano i dati quando vengono aperti (oggi `init()` fa 8 fetch sequenziali). Risparmio stimato: da ~8 fetch a 1–2 → startup < 2 s.
- **Prefetch + debounce**: cache lato frontend dei dati già scaricati per 60 s.
- **Concorrenza backend**: il ranking (`get_dynamic_ranking`) blocca `self._lock` per tutta la valutazione (16 strategie × n). Introdurre:
  - **Read/write lock** o lock separati; il ranking in background con snapshot dei record.
  - **Cache multi-chiave** (già parzialmente presente: `_ranking_cache`) → estenderla con TTL e invalidazione su modifica dati invece che tempo fisso di 5 min.
- **Compressione**: servire HTML/CSS/JS come gzip (aggiungere `Content-Encoding`); minificare `style.css`/`app.js` nella build PyInstaller.
- **Indici SQLite**: indice su `estrazioni.data` (usato nelle query `WHERE data=`) e su `giocate.verificato`.

### 5.2 Cache, compressione, lazy
- Cache HTTP con `Cache-Control` per asset statici immutabili.
- Asset bundle: un solo file JS + un solo CSS (oggi già 1+1, ridurne dimensione minificando).
- Charging lazy delle immagini/grafici (heatmap) solo quando il tab è visibile.

### 5.3 Accessibilità (A11y)
- **WCAG 2.1 AA**: contrasto (tema chiaro+scuro), focus visibile, navigazione da tastiera (TAB/Enter/Escape) su tutti i controlli interattivi.
- **ARIA**: `role="tablist"/"tab"` per la sidebar, `aria-live` per status/notifiche, etichette per tutti gli input.
- **Screen reader**: ordine DOM logico; testo alternativo per emoji-icone (aggiungere `aria-label`).
- **Ridotta mobilità**: target touch ≥ 44 px, scorrevolezza delle tabelle con header sticky (già presente).

### 5.4 Documentazione e tutorial interattivi
- **Tour guidato in-app** (primo avvio): overlay con frecce sui tab principali ("Genera", "Salva", "Verifica", "Backup") — integrato nel primo avvio già gestito da `_show_notification`.
- **Tooltip contestuali** su sezioni complesse (Strategie, Classifica) con spiegazione onesta del significato.
- **Guida utente** aggiornata: `manuale_operativo.md` esteso con le nuove funzionalità + sezione FAQ.
- **Changelog visibile in-app** (verso `SUPER_ENALOTTO_RELEASE_NOTES.md`).

---

## 6. IDEE E PROGETTI RIVOLUZIONARI

> Tutti i progetti rivoluzionari **rispettano la premessa etica**: nessuno promette di battere il caso. L'innovazione sta in *privacità, analisi onesta, automazione e comunità*, non nella pretesa di previsione.

### 6.1 AI Assistant "personal trainer del budget" (feasible, alto valore)
- **Cosa**: un assistente conversazionale (locale, modello piccolo) che:
  - Analizza le giocate dell'utente e calcola **ROI reale e budget residuo**.
  - Aiuta a **definire limiti di spesa** e ne avvisa al superamento (gioco responsabile).
  - Spiega con parole semplici **perché il gioco è a perdita attesa** e mostra le probabilità reali per categoria.
- **Fattibilità**: dipende da LLM → richiede deployment locale (es. Ollama/llama.cpp, ~1–3 GB) o cloud (costo/privacità). **Prototipo**: prima versione **rule-based/finita** in stdlib (niente LLM) per provare il flusso, poi valutare LLM.
- **Costo**: basso (locale stdlib) → medio (LLM). Time-box al prototipo di flusso.

### 6.2 Analitiche predittive avventive (≠ previsione)
- **Cosa**: dashboard di **analisi descrittiva** avanzata: serie temporali di frequenze, heatmap, ritardi, "co-occorrenze", riusando le API già presenti ma oggi non esposte (`get_heatmap_data`, `get_trend_data`, `/api/trend`, `/api/heatmap`).
- **Etichetta trasparente**: ogni grafico reca "Dati descrittivi storici — nessuna capacità predittiva dimostrata".
- **Fattibilità**: alta, sola stdlib. È l'idea più differenziante e fattibile a breve.

### 6.3 Collaborazione in tempo reale / comunità
- **Cosa**: condivisione (opzionale e anonima) di statistiche aggregate tra utenti; "sfide" settimanali di analisi; classifica community.
- **Fattibilità**: media-bassa (richiede backend cloud + account). **Fase**: analisi di fattibilità + prototipo statico non persistente.
- **Rischi**: costi server, privacy (PII), moderazione. Da rimandare a post-P1.

### 6.4 Multi-piattaforma (estensione della distribuzione)
- **Cosa**: trasformare il frontend vanilla in PWA/componente web riutilizzabile per aprire la strada a versioni per browser/mobile senza riscrivere il backend (che resta locale API).
- **Fattibilità**: media (refactor frontend attuale già autonomo). Prototipo: servire la stessa `web/` in un browser con API venditrice.

### 6.5 Roadmap integrata

**Fase 0 — Stabilizzazione (breve termine)**
- Fix `valuta_strategie` stub → Monte Carlo onesto (§3.1).
- Etichettatura trasparente delle strategie (§4.1).
- Suite pytest completa + script benchmark (§4.2–4.3).
- Lazy-load dei tab + startup < 2 s (§5.1).

**Fase 1 — Esperienza (medio termine)**
- Ridisegno responsive + tema scuro + A11y (§2, §5.3).
- Export report CSV/PDF + ricerca di sistema (§3.2).
- Tour guidato + FAQ (§5.4).

**Fase 2 — Differenziazione (medio-lungo termine)**
- Dashboard analitica descrittiva (§6.2).
- Assistente budget rule-based → LLM (§6.1).
- Preferenze/personalizzazione (§2.3).

**Fase 3 — Community / multi-piattaforma (lungo termine, condizionata)**
- PWA/mobile (§6.4), collaborazione (§6.3) — solo dopo validazione di domanda e costi.

---

## 7. RISORSE NECESSARIE

| Risorsa | Fase 0 | Fase 1 | Fase 2 | Fase 3 |
|---|---|---|---|---|
| Python 3.14 + stdlib | ✔ (esistente) | ✔ | ✔ | ✔ |
| pytest | ✔ dev-dep | — | — | — |
| pywebview (già in req) | ✔ | ✔ | ✔ | ✔ |
| Frontend vanilla (esistente) | ✔ | ✔ | ✔ | PWA upgrade |
| Postgre/cloud | — | — | — | da valutare |
| LLM (opzionale) | — | — | prototipo locale | — |
| Test utenti reali | — | 5 sessioni | sondaggio in-app | beta group |

- **Nessuna nuova dipendenza runtime** nelle Fasi 0–2 (solo stdlib + pywebview già presenti).
- **Impegno**: stimato per priorità P0-P1 condivisibile, senza impegno su tempo calandario non richiesto.

---

## 8. RISULTATI ATTESI

| KPI | Valore oggi | Target Fase 0 | Target Fase 1 |
|---|---|---|---|
| Startup app | 3–5 s | ≤ 2 s | ≤ 1.5 s |
| Fetch all'avvio | 8 sequenziali | 1–2 | 1 |
| `resolve_auto_strategy` | secondi (sotto lock) | < 800 ms | < 400 ms |
| Test coverage engine | ~0% | ≥ 85% | ≥ 85% |
| Tema scuro/accessibilità | no | no | WCAG 2.1 AA |
| Calcolatore valuta | stub | Monte Carlo ±CI | + ricerca di sistema |
| Export report | no | CSV | + PDF |
| Onestà scientifica UI | parziale | completa | completa |

---

## 9. SINTESI ESECUTIVA

1. **Fondamento**: l'audit dimostra che nessuna strategia batte il caso. Il piano **non promette previsioni**, ma trasforma l'app in uno strumento **onesto, veloce, accessibile e utile** per chi sceglie consapevolmente di giocare per intrattenimento.
2. **Priorità immediate (P0)**: correggere lo stub del calcolatore, rendere la UI onesta/responsive/accessibile.
3. **Priorità P1**: performance di startup, suite di test completa, export report.
4. **Differenziazione (P2)**: analisi descrittiva avanzata (già supportata dalle API backend inutilizzate), assistente al budget responsabile.
5. **Rivoluzionario (P3)**: multi-piattaforma e comunità, solo dopo validazione di domanda e costi, **senza mai affermare capacità predittiva**.
6. **Vincolo trasversale**: nessuna nuova dipendenza runtime nelle fasi principali; gioco sempre presentato come intrattenimento a perdita attesa.
