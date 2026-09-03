# -*- coding: utf-8 -*-
"""
SuperEnalotto Launcher v8.3
- Singola istanza via lock file in Documents/SuperEnalotto
- Avvia backend HTTP in-thread (porta 8766)
- Apre finestra nativa PyWebView su http://localhost:8766
- Dati persistenti in Documents/SuperEnalotto/
"""

import os
import sys
import threading
import time
import urllib.request
import urllib.error
import ctypes
import traceback
import webview

# Log su file per debug (console=False nel build exe)
LOG_FILE = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperEnalotto', 'launcher.log')

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

log(f"=== LAUNCHER START v8.2 ===")
log(f"Executable: {sys.executable}")
log(f"Frozen: {getattr(sys, 'frozen', False)}")
log(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

PORT = 8766
URL = f"http://localhost:{PORT}"

# Lock file in Documents/SuperEnalotto (portable, non accanto all'EXE)
def get_data_dir():
    data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperEnalotto')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

LOCK_PATH = os.path.join(get_data_dir(), '.superenalotto.lock')

# In frozen, i moduli gateway sono in _MEIPASS (hiddenimports), non serve sys.path
if not getattr(sys, 'frozen', False):
    GATEWAY_DIR = os.path.join(APP_DIR, 'gateway')
    if GATEWAY_DIR not in sys.path:
        sys.path.insert(0, GATEWAY_DIR)

log("Imports: stdlib ok")

def acquire_lock():
    import time as _time
    # Se lock esiste ma è >15 minuti fa (processo crashato), rimuovi
    if os.path.exists(LOCK_PATH):
        age = _time.time() - os.path.getmtime(LOCK_PATH)
        if age > 900:  # 15 minuti
            log("Lock stale (>15min), rimuovo")
            try:
                os.remove(LOCK_PATH)
            except OSError:
                pass
    try:
        import msvcrt
        fp = open(LOCK_PATH, 'w')
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        log("Lock acquisito")
        return fp
    except Exception as e:
        log(f"acquire_lock FAIL: {e}")
        return None


def release_lock(fp):
    try:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        fp.close()
    except Exception as e:
        log(f"release_lock msvcrt error: {e}")
    try:
        os.remove(LOCK_PATH)
        log("Lock file rimosso")
    except OSError:
        pass


def bring_existing_to_front():
    try:
        import win32gui
        import win32con
    except ImportError as e:
        log(f"win32gui/win32con not available: {e}")
        return

    try:
        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if 'SuperEnalotto' in title:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return False
            return True

        win32gui.EnumWindows(_enum, None)
        log("bring_existing_to_front ok")
    except Exception as e:
        log(f"bring_existing_to_front error: {e}")


def start_backend():
    try:
        log("Thread backend: import gateway.server...")
        from gateway.server import start_server
        log("Thread backend: start_server()...")
        start_server(open_browser_flag=False)
    except Exception as e:
        log(f"Thread backend ERRORE: {e}\n{traceback.format_exc()}")
        print(f"[ERROR] Backend server failed: {e}")
        raise


def show_first_run_notification(data_dir):
    """Mostra un MessageBox Windows al primo avvio indicando dove sono salvati i dati."""
    sentinel = os.path.join(data_dir, '.first_run_done')
    if os.path.exists(sentinel):
        return
    try:
        # Crea subito il sentinel per evitare blocchi ripetuti
        with open(sentinel, 'w', encoding='utf-8') as f:
            f.write('done')
        ctypes.windll.user32.MessageBoxW(
            0,
            "SuperEnalotto - Primo avvio\n\n"
            "I dati (database, giocate, configurazione) vengono salvati in:\n"
            f"{data_dir}\n\n"
            "Puoi spostare SuperEnalotto.exe in qualsiasi cartella: "
            "i dati resteranno in Documents.",
            "SuperEnalotto",
            0x40,  # MB_ICONINFORMATION
        )
        log("Notifica primo avvio mostrata")
    except Exception as e:
        log(f"notification error: {e}")
        # Assicura comunque che il sentinel esista
        try:
            with open(sentinel, 'w', encoding='utf-8') as f:
                f.write('done')
        except Exception:
            pass


def wait_server(max_attempts=30, delay=1):
    """Attende che il server risponda all'API /api/stats."""
    api_url = URL + "/api/stats"
    log(f"wait_server: polling {api_url}")
    for i in range(max_attempts):
        try:
            urllib.request.urlopen(api_url, timeout=1)
            log(f"wait_server: server risponde dopo {i+1} tentativi")
            return True
        except urllib.error.HTTPError as e:
            if e.code in (200, 404, 500):
                log(f"wait_server: server risponde (HTTP {e.code})")
                return True
        except Exception as e:
            if i % 10 == 0:
                log(f"wait_server: attempt {i+1}/{max_attempts} - {e}")
            time.sleep(delay)
    log(f"wait_server: TIMEOUT dopo {max_attempts} tentativi")
    return False


if __name__ == '__main__':
    try:
        # Migra DB/tracking/config
        log("Import gateway.engine...")
        from gateway.engine import get_user_data_dir, migrate_db_if_needed
        log("gateway.engine imported ok")
        
        data_dir = get_user_data_dir()
        log(f"Data dir: {data_dir}")
        
        migrate_db_if_needed()
        log("Migrazione completata")

        # Mostra notifica primo avvio in un THREAD separato con timeout,
        # dopo che il server e' pronto. Se non c'e' sessione desktop, non blocca.
        first_run = not os.path.exists(os.path.join(data_dir, '.first_run_done'))
        if first_run:
            # Crea sentinel SUBITO (evita notifiche ripetute se MessageBox blocca)
            open(os.path.join(data_dir, '.first_run_done'), 'w').write('done')

    except Exception as e:
        log(f"ERRORE setup dati: {e}\n{traceback.format_exc()}")

    lock_fp = acquire_lock()
    if lock_fp is None:
        log("Lock non acquisito, gia aperto")
        bring_existing_to_front()
        sys.exit(0)

    log("Lock acquisito, avvio backend...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    try:
        if not wait_server():
            log("ERRORE: Backend non risponde")
            release_lock(lock_fp)
            sys.exit(1)

        log("Server pronto, apro GUI con PyWebView...")
        # PyWebView: finestra nativa che carica l'UI HTML dal server locale
        win = webview.create_window("SuperEnalotto v8.3", URL, width=1280, height=800, resizable=True)

        # Mostra notifica primo avvio (in thread separato)
        if first_run:
            def _show_notification():
                try:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        "SuperEnalotto - Primo avvio\n\n"
                        "I dati (database, giocate, configurazione) vengono salvati in:\n"
                        f"{data_dir}\n\n"
                        "Puoi spostare SuperEnalotto.exe in qualsiasi cartella: "
                        "i dati resteranno in Documents.",
                        "SuperEnalotto",
                        0x40,
                    )
                except Exception as e:
                    log(f"notification error: {e}")
            threading.Thread(target=_show_notification, daemon=True).start()

        # webview.start() DEVE girare nel thread principale (STA per WinForms).
        # Il server HTTP (ThreadingHTTPServer) gira nel backend_thread (daemon)
        # e gestisce richieste in thread separati grazie a ThreadingHTTPServer.
        log("Avvio webview.start()...")
        webview.start()
        log("webview.start() terminato")
        # Se webview.start() ritorna, manteniamo il backend vivo
        # (la finestra potrebbe chiudersi ma il server debe continuare o termina)
        while backend_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log("KeyboardInterrupt")
        print("\nChiusura in corso...")
    except Exception as e:
        log(f"ERRORE MAIN LOOP: {e}\n{traceback.format_exc()}")
    finally:
        try:
            release_lock(lock_fp)
        except Exception as e:
            log(f"release_lock error: {e}")
        log("SuperEnalotto chiuso.")