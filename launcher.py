#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SuperEnalotto Launcher
- Singola istanza via lock file
- Avvia backend Bottle in-thread
- Apre browser predefinito su http://localhost:8766
"""

import os
import sys
import threading
import time
import urllib.request
import urllib.error
import webbrowser
import ctypes

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

PORT = 8766
URL = f"http://localhost:{PORT}"
LOCK_PATH = os.path.join(APP_DIR, '.superenalotto.lock')

# Aggiungi gateway al path
GATEWAY_DIR = os.path.join(APP_DIR, 'gateway')
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)


def acquire_lock():
    try:
        import msvcrt
        fp = open(LOCK_PATH, 'w')
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        return fp
    except Exception:
        return None


def release_lock(fp):
    try:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        fp.close()
    except Exception:
        pass
    try:
        os.remove(LOCK_PATH)
    except OSError:
        pass


def bring_existing_to_front():
    try:
        import win32gui
        import win32con

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if 'SuperEnalotto' in title:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return False
            return True

        win32gui.EnumWindows(_enum, None)
    except Exception:
        pass


def start_backend():
    try:
        from gateway.server import start_server
        start_server(open_browser_flag=False)
    except Exception as e:
        print(f"[ERROR] Backend failed: {e}")


def wait_server(max_attempts=30, delay=1):
    """Attende che il server risponda all'API."""
    api_url = URL + "/api/stats"
    for _ in range(max_attempts):
        try:
            urllib.request.urlopen(api_url, timeout=1)
            return True
        except urllib.error.HTTPError as e:
            # 200 = OK, qualsiasi response HTTP significa che il server è up
            if e.code in (200, 404, 500):
                return True
        except Exception:
            time.sleep(delay)
    return False


if __name__ == '__main__':
    lock_fp = acquire_lock()
    if lock_fp is None:
        print("SuperEnalotto già aperto. Porto in primo piano...")
        bring_existing_to_front()
        sys.exit(0)

    print("Avvio SuperEnalotto...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    try:
        if not wait_server():
            print("ERRORE: Backend non risponde")
            release_lock(lock_fp)
            sys.exit(1)

        webbrowser.open(URL)
        print(f"SuperEnalotto aperto su {URL}")

        while True:
            time.sleep(5)
            if not backend_thread.is_alive():
                print("Backend finito, riavvio...")
                backend_thread = threading.Thread(target=start_backend, daemon=True)
                backend_thread.start()
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nChiusura in corso...")
    finally:
        try:
            release_lock(lock_fp)
        except Exception as e:
            print(f"[WARN] release_lock: {e}")
        print("SuperEnalotto chiuso.")
