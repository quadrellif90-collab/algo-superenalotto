# STATO DEL PROGETTO (MEMORY STATE)

## AMBIENTE OPERATIVO
- OS Target: Windows (PowerShell / CMD)
- Gestore Pacchetti: winget / npm / pip
- Python: 3.14
- Stato Build: v8.3 funzionante, PyInstaller EXE generato

## ARCHITETTURA
- **Progetto 1 - Gateway (Backend Python)**: gateway/ — engine.py (1555 righe, logica dominio), server.py (API HTTP porta 8766), desktop.py (tray icon + webview)
- **Progetto 2 - Web (Frontend)**: web/ — index.html (8 tab), app.js (SPA vanilla), style.css (tema verde)
- **Entry point**: launcher.py (PyWebView + lock single-instance + backend thread)
- **Distribuzione**: PyInstaller single-file (SuperEnalotto.spec)
- **Persistenza**: SQLite (WAL) + CSV tracking, dati in Documents/SuperEnalotto/

## FUNZIONALITÀ
- 16 strategie generazione numeri (quartile, hotcold, antirecent, mix, sumlocked, primefocus, middlefreq, gapspread, complement, mixhotcoldprime, mixquartilehotcold, optimized, fibonacci, adaptive, ensemble, mlpattern)
- Classifica dinamica deterministica con cache fingerprint (no leakage)
- Verifica automatica giocate, backup/restore, scraping storico
- Notifiche real-time (jackpot, estrazione, giocate da verificare)

## REVISIONE COMPLETATA (2026-09-07) — AGGIORNAMENTO 2
- Punteggio globale: 6.8/10 (aggiornato da 6.5)
- Criticità: 3 Critiche / 5 Alto / 10 Medio / 5 Basso (totale 23)
- Critiche principali: test_desktop.py rotto (import errato), bring_existing_to_front() senza EnumWindows, run_server.py import rotto in frozen
- Alto: os._exit(0) non ordinato, logging duplicato, resolve_auto_strategy() costoso, checkShowClear() duplicato, funzione morta show_first_run_notification()
- Note: funzione show_first_run_notification() (L128-155) NON viene chiamata — logica notifica è inline a L194-238
- Azioni prioritarie: fix import rotti, EnumWindows, cleanup ordinato, centralizzare logging, cache Auto strategy, rimuovere checkShowClear() duplicato
- **Status: FIX IMPLEMENTATI E MERGED SU MASTER (2026-09-07)**
