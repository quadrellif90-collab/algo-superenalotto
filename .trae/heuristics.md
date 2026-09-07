# EURISTICHE E MEMORIA DI AUTO-APPRENDIMENTO (WINDOWS)

## PATTERN DI ERRORE APPRESI E SOLUZIONI
- [SISTEMA]: Ambiente Windows (PowerShell/CMD). Usare separatori di percorso `\` e sintassi PowerShell valida.
- [REGOLA 1]: Usare la codifica UTF-8 per la scrittura dei file per evitare errori di caratteri speciali in PowerShell.
- [REGOLA 2]: Gestire difensivamente il lock dei file su Windows durante le modifiche e riscritture.

## PATTERN APPRESI DALLA REVISIONE 2026-09-07
- [REVISIONE 1]: test_desktop.py importa `desktop_app` che non esiste — il modulo corretto è `launcher` (entry point) o `gateway.desktop` (DesktopApp). Attenzione ai nomi dei moduli dopo i refactoring.
- [REVISIONE 2]: Non duplicare `logging.basicConfig()` in moduli diversi dello stesso processo Python — solo la prima chiamata ha effetto, le successive vengono ignorate. Centralizzare la configurazione logging nel punto di ingresso.
- [REVISIONE 3]: `os._exit(0)` su Windows salta i `finally` block e non esegue cleanup — usare `threading.Event` + loop di attesa, o assicurarsi che il cleanup sia in `finally` del main thread.
- [REVISIONE 4]: Su Windows con `msvcrt.locking`, il lock stale detection (>15min) è corretto ma il lock file va chiuso esplicitamente prima di `os.remove()` per evitare PermissionError.
- [REVISIONE 5]: Le variabili in list comprehension in Python possono shadoware variabili esterne (es. `n` in `all_nums = [n for r in records for n in r["nums"]]`) — causare confusione. Usare nomi diversi (es. `num` o `val`).
- [REVISIONE 6]: Su Windows, `ThreadingHTTPServer` può avere problemi con thread pooling sotto carico elevato. Per applicazioni desktop single-user è sufficiente.
- [REVISIONE 7]: PyInstaller `sys._MEIPASS` è temporaneo e viene eliminato dopo l'uscita — mai scrivere dati persistenti lì. Usare Documents/SuperEnalotto/ per dati utente.
- [REVISIONE 8]: win32gui.EnumWindows() va esplicitamente invocata — definire la callback _enum() senza chiamare EnumWindows non ha effetto. Verificare sempre che le funzioni Windows API siano effettivamente chiamate, non solo definite.
- [REVISIONE 9]: In Python, funzioni definite ma mai chiamate nel codice effettivo (dead code) possono persistere dopo refactoring. Fare audit periodico delle funzioni per identificare quelle non invocate da nessun punto del programma.
- [REVISIONE 10]: Frontend JS che chiama API diverse per lo stesso dato (es. /api/giocate due volte) introduce latenza e overhead inutile. Derivare i dati ausiliari dalla risposta già disponibile.
- [REVISIONE 11]: In applicazioni desktop con ranking/calcoli costosi, cachare i risultati con TTL anche lato server (non solo per il ranking) per evitare ricalcoli ad ogni richiesta. Il pattern fingerprint+TTL funziona bene per questo caso.
- [REVISIONE 12]: run_server.py con `from server import start_server` funziona solo quando gateway/ è nella sys.path direttamente (dev mode). In frozen PyInstaller, i moduli sono in _MEIPASS e richiedono `from gateway.server import start_server`. Usare sempre il prefisso del pacchetto.
