import os
import sys
import threading
import time
import urllib.request
import urllib.error
import ctypes
import traceback
import webview

LOG_FILE = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperEnalotto', 'launcher.log')

import logging
import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"=== LAUNCHER START v8.3 ===")
logger.info(f"Executable: {sys.executable}")
logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
logger.info(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

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

logger.info("Imports: stdlib ok")

def acquire_lock():
    import time as _time
    # Se lock esiste ma è >15 minuti fa (processo crashato), rimuovi
    if os.path.exists(LOCK_PATH):
        age = _time.time() - os.path.getmtime(LOCK_PATH)
        if age > 900:  # 15 minuti
            logger.info("Lock stale (>15min), rimuovo")
            try:
                os.remove(LOCK_PATH)
            except OSError:
                pass
    try:
        import msvcrt
        fp = open(LOCK_PATH, 'w')
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        logger.info("Lock acquisito")
        return fp
    except Exception as e:
        logger.error(f"acquire_lock FAIL: {e}")
        return None


def release_lock(fp):
    try:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        fp.close()
    except Exception as e:
        logger.error(f"release_lock msvcrt error: {e}")
    try:
        os.remove(LOCK_PATH)
        logger.info("Lock file rimosso")
    except OSError:
        pass


def bring_existing_to_front():
    try:
        import win32gui
        import win32con
    except ImportError as e:
        logger.error(f"win32gui/win32con not available: {e}")
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

        # Invoca esplicitamente EnumWindows per trovare e portare in primo piano la finestra
        win32gui.EnumWindows(_enum, None)
        logger.info("bring_existing_to_front ok")
    except Exception as e:
        logger.error(f"bring_existing_to_front error: {e}")


def start_backend():
    try:
        logger.info("Thread backend: import gateway.server...")
        from gateway.server import start_server
        logger.info("Thread backend: start_server()...")
        start_server(open_browser_flag=False)
    except Exception as e:
        logger.error(f"Thread backend ERRORE: {e}", exc_info=True)
        logger.error(f"Backend server failed: {e}")
        raise


def wait_server(max_attempts=30, delay=1):
    """Attende che il server risponda all'API /api/stats."""
    api_url = URL + "/api/stats"
    logger.info(f"wait_server: polling {api_url}")
    for i in range(max_attempts):
        try:
            urllib.request.urlopen(api_url, timeout=1)
            logger.info(f"wait_server: server risponde dopo {i+1} tentativi")
            return True
        except urllib.error.HTTPError as e:
            if e.code in (200, 404, 500):
                logger.info(f"wait_server: server risponde (HTTP {e.code})")
                return True
        except Exception as e:
            if i % 10 == 0:
                logger.info(f"wait_server: attempt {i+1}/{max_attempts} - {e}")
            time.sleep(delay)
    logger.error(f"wait_server: TIMEOUT dopo {max_attempts} tentativi")
    return False


if __name__ == '__main__':
    try:
        # Migra DB/tracking/config
        logger.info("Import gateway.engine...")
        from gateway.engine import get_user_data_dir, migrate_db_if_needed
        logger.info("gateway.engine imported ok")
        
        data_dir = get_user_data_dir()
        logger.info(f"Data dir: {data_dir}")
        
        migrate_db_if_needed()
        logger.info("Migrazione completata")

        # Mostra notifica primo avvio in un THREAD separato con timeout,
        # dopo che il server e' pronto. Se non c'e' sessione desktop, non blocca.
        first_run = not os.path.exists(os.path.join(data_dir, '.first_run_done'))
        if first_run:
            # Crea sentinel SUBITO (evita notifiche ripetute se MessageBox blocca)
            open(os.path.join(data_dir, '.first_run_done'), 'w').write('done')

    except Exception as e:
        logger.error(f"ERRORE setup dati: {e}", exc_info=True)

    lock_fp = acquire_lock()
    if lock_fp is None:
        logger.info("Lock non acquisito, gia aperto")
        bring_existing_to_front()
        sys.exit(0)

    logger.info("Lock acquisito, avvio backend...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    try:
        if not wait_server():
            logger.error("ERRORE: Backend non risponde")
            release_lock(lock_fp)
            sys.exit(1)

        logger.info("Server pronto, apro GUI con PyWebView...")
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
                    logger.error(f"notification error: {e}")
            threading.Thread(target=_show_notification, daemon=True).start()

        # webview.start() DEVE girare nel thread principale (STA per WinForms).
        # Il server HTTP (ThreadingHTTPServer) gira nel backend_thread (daemon)
        # e gestisce richieste in thread separati grazie a ThreadingHTTPServer.
        logger.info("Avvio webview.start()...")
        webview.start()
        logger.info("webview.start() terminato")
        # Se webview.start() ritorna, manteniamo il backend vivo
        # (la finestra potrebbe chiudersi ma il server deve continuare o termina)
        while backend_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
        logger.info("Chiusura in corso...")
    except Exception as e:
        logger.error(f"ERRORE MAIN LOOP: {e}", exc_info=True)
    finally:
        try:
            release_lock(lock_fp)
        except Exception as e:
            logger.error(f"release_lock error: {e}")
        logger.info("SuperEnalotto chiuso.")