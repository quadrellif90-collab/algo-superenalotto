#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SuperEnalotto v8.1 - Desktop App nativa (single instance, no duplicate processes)
Stesso pattern dell'AI Gateway Manager:
  - avvia il server backend in-thread (Bottle)
  - apre finestra nativa PyWebView su http://localhost:8766
  - lock file su Windows per evitare istanze multiple
"""

import os
import sys
import threading
import time
import urllib.request
import webview

# Path progetto
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

LOCK_PATH = os.path.join(APP_DIR, '.superenalotto.lock')
PORT = 8766
URL = f"http://localhost:{PORT}"

# Aggiungi gateway al path per import in dev e in EXE
GATEWAY_DIR = os.path.join(APP_DIR, 'gateway')
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)


def acquire_single_instance_lock():
    """Lock file Windows: impedisce istanze multiple."""
    try:
        import msvcrt
        fp = open(LOCK_PATH, 'w')
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        return fp
    except Exception:
        return None


def release_single_instance_lock(fp):
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
    """Porta in primo piano una finestra SuperEnalotto già aperta."""
    try:
        import win32gui
        import win32con

        found = []

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if 'SuperEnalotto' in title:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    found.append(hwnd)
            return True

        win32gui.EnumWindows(_enum, None)
        return bool(found)
    except Exception as e:
        print(f"[WARN] bring_existing_to_front: {e}")
        return False


def start_backend():
    """Avvia il server Bottle nel thread corrente."""
    try:
        from gateway.server import start_server
        start_server(open_browser_flag=False)
    except Exception as e:
        print(f"[ERROR] Backend server failed: {e}")
        raise


def wait_server(max_attempts=40, delay=1):
    for _ in range(max_attempts):
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(delay)
    return False


if __name__ == '__main__':
    print("Avvio SuperEnalotto Desktop App...")

    lock_fp = acquire_single_instance_lock()
    if lock_fp is None:
        print("SuperEnalotto è già aperto. Porto la finestra in primo piano...")
        bring_existing_to_front()
        sys.exit(0)

    # Avvia backend in-thread invece che come subprocess
    print("Avvio server backend...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    print("Attendo server...")
    if not wait_server():
        print("ERRORE: Server non risponde dopo 40 tentativi")
        release_single_instance_lock(lock_fp)
        sys.exit(1)

    print("Server pronto! Apertura finestra app...")

    window = webview.create_window(
        title='SuperEnalotto',
        url=URL,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False,
        background_color='#1a1a2e',
    )
    
    try:
        webview.start(
            func=lambda: None,
            gui='edgechromium',
        )
    except Exception as e:
        print(f"[ERROR] Window error: {e}")
    finally:
        try:
            release_single_instance_lock(lock_fp)
        except Exception:
            pass
        print("SuperEnalotto chiuso.")
