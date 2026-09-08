# STATO DEL PROGETTO (MEMORY STATE)

## AMBIENTE OPERATIVO
- OS Target: Windows (PowerShell / CMD)
- Gestore Pacchetti: winget / npm / pip
- Python: 3.14
- Stato Build: v8.6+ funzionante, PyInstaller EXE generato
- Repository: `Pro superenalotto/` (unico progetto, unificato 2026-09-08)

## ARCHITETTURA (POST-UNIFICAZIONE 2026-09-08)
- **Backend**: gateway/engine.py (1555 righe, logica dominio), gateway/server.py (API HTTP porta 8766, stop_server() per shutdown ordinato)
- **Frontend**: web/index.html (8 tab), web/app.js (SPA vanilla), web/style.css (tema verde)
- **Entry point UNICO**: launcher.py (PyWebView + lock single-instance + backend thread + stop_backend())
- **Distribuzione**: PyInstaller single-file (SuperEnalotto.spec)
- **Persistenza**: SQLite (WAL) + CSV tracking, dati in Documents/SuperEnalotto/
- **File totali**: ~30 (ridotti da ~110 dopo pulizia)

## FUNZIONALITÀ
- 16 strategie generazione numeri (quartile, hotcold, antirecent, mix, sumlocked, primefocus, middlefreq, gapspread, complement, mixhotcoldprime, mixquartilehotcold, optimized, fibonacci, adaptive, ensemble, mlpattern)
- Classifica dinamica deterministica con cache fingerprint (no leakage)
- Verifica automatica giocate, backup/restore, scraping storico
- Notifiche real-time (jackpot, estrazione, giocate da verificare)

## UNIFICAZIONE + FIX CHIUSURA (2026-09-08) — MERGED
- Commit: 37f0932 su master (81 file modificati, -11.715 righe)
- **Unificazione**: i due progetti duplicati (`Pro superenalotto/` e `Superenalotto Max/algo-superenalotto/`) erano identici al 100%. Unificati in unico progetto in `Pro superenalotto/`
- **Fix critico chiusura**: l'app restava attiva in background dopo chiusura finestra perche' `while backend_thread.is_alive()` non fermava il server HTTP. Soluzione: aggiunta `stop_server()` in server.py (shutdown ordinato cross-thread) e `stop_backend()` in launcher.py
- **Entry point ridondanti eliminati**: gateway/desktop.py, gateway/__main__.py (path "hide-to-tray" non usato dal binario)
- **Pulizia file**: eliminati ~80 file inutili (script analisi, JSON risultati, log TXT, PS1 usa-e-getta, test rotti, .spec obsoleto, immagini)
- File eliminati: SuperEnalottoDebug.spec, gateway/desktop.py, gateway/__main__.py, ~25 .py analisi/test, ~25 .json risultati, ~13 .txt log, ~29 .ps1 script, immagini .png
- Collaudo: compilazione py_compile OK, test unitari OK (test_imports, test_game_logic, test_launcher, test_server), verify.ps1 exit 0

## AUDIT RIGOROSO SUPERENALOTTO (2026-09-08) — COMPLETATO E MERGED
- File: rigorous_backtest_audit.py (1274 righe, solo stdlib), AUDIT_RIGOROSO_SUPERENALOTTO.md, rigorous_audit_results.json
- Metodologia: walk-forward out-of-sample (train=300, block=200) su 4238 estrazioni, 21 strategie
- Risultati: tutte le strategie NON statisticamente significative (pFDR 0.96-1.0), ROI negativo (house edge ~67%)
- Nessuna strategia e' economicamente sostenibile — gioco solo come intrattenimento con budget limitato

## NOTE OPERATIVE
- dist/SuperEnalotto.exe: binario compilato, NON committato (in .gitignore)
- Cartella duplicata `Superenalotto Max/algo-superenalotto/` ancora presente su desktop (da eliminare)
