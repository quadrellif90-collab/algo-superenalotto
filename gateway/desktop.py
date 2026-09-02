"""
SuperEnalotto Desktop App - Tray icon + Webview window (stesso pattern AI Gateway Manager).
"""

import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer
from pathlib import Path
from datetime import datetime

import webview
import pystray
from PIL import Image, ImageDraw

from gateway.engine import SuperenalottoEngine
from gateway.server import SuperenalottoHandler, PORT, open_browser

# Stato globale
_server = None
_window = None
_tray = None
_engine = None


# ═══════════════════════════════════════════════════
# Icon Generation
# ═══════════════════════════════════════════════════

def get_icon_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico = os.path.join(base, "icon.ico")
    return ico if os.path.exists(ico) else None


def create_tray_icon():
    """Genera un'icona tray per SuperEnalotto."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Sfondo verde (colore SuperEnalotto)
    for i in range(32, 0, -1):
        r = int(34 + (22 - 34) * (32 - i) / 32)
        g = int(197 + (163 - 197) * (32 - i) / 32)
        b = int(94 + (74 - 94) * (32 - i) / 32)
        draw.ellipse([32 - i, 32 - i, 32 + i, 32 + i], fill=(r, g, b, 255))
    # Cerchio interno
    draw.ellipse([20, 20, 44, 44], fill=(34, 197, 94, 255), outline=(255, 255, 255, 255), width=2)
    # "SE" (SuperEnalotto)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arialbd.ttf", 18)
    except:
        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
        except:
            font = None
    if font:
        draw.text((14, 20), "SE", fill="white", font=font)
    return img


# ═══════════════════════════════════════════════════
# Server
# ═══════════════════════════════════════════════════

class ServerThread(threading.Thread):
    """Run HTTP server in background thread."""
    def __init__(self):
        super().__init__(daemon=True)
        self._server = None

    def run(self):
        global _engine
        _engine = SuperenalottoEngine()
        SuperenalottoHandler.engine = _engine

        self._server = HTTPServer(("127.0.0.1", PORT), SuperenalottoHandler)
        print(f"SuperEnalotto Server running on http://localhost:{PORT}")
        try:
            self._server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()


def wait_for_server(url=None, timeout=10):
    if url is None:
        url = f"http://127.0.0.1:{PORT}"
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"{url}/api/prossima", timeout=1)
            return True
        except:
            time.sleep(0.3)
    return False


# ═══════════════════════════════════════════════════
# Windows Startup
# ═══════════════════════════════════════════════════

def add_to_startup():
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "SuperEnalotto", 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to add startup: {e}")
        return False


def remove_from_startup():
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "SuperEnalotto")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def is_in_startup():
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "SuperEnalotto")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════
# Tray
# ═══════════════════════════════════════════════════

def setup_tray(on_open, on_quit):
    """Crea system tray icon con menu."""
    global _tray
    icon = create_tray_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Apri SuperEnalotto", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Avvio automatico Windows",
            pystray.Menu(
                pystray.MenuItem(
                    "Abilita",
                    lambda: add_to_startup(),
                    checked=lambda item: is_in_startup(),
                ),
                pystray.MenuItem(
                    "Disabilita",
                    lambda: remove_from_startup(),
                    checked=lambda item: not is_in_startup(),
                ),
            )
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Esci", on_quit),
    )
    _tray = pystray.Icon("SuperEnalotto", icon, "SuperEnalotto", menu)
    return _tray


# ═══════════════════════════════════════════════════
# Main Desktop App
# ═══════════════════════════════════════════════════

class DesktopApp:
    def __init__(self):
        self.url = f"http://127.0.0.1:{PORT}"
        self.window = None
        self.server_thread = None
        self.tray = None
        self._quit_flag = False

    def start(self):
        # 1) Avvia server in thread
        self.server_thread = ServerThread()
        self.server_thread.start()

        # 2) Aspetta server
        if not wait_for_server(self.url):
            print("Server non avviato")
            return

        # 3) Crea finestra webview
        self._create_window()

        # 4) Avvia webview (blocking, su thread principale)
        webview.start(self._on_webview_ready, gui=None, debug=False)

    def _create_window(self):
        icon = get_icon_path()
        self.window = webview.create_window(
            "SuperEnalotto",
            self.url,
            width=1280,
            height=800,
            min_size=(900, 600),
            text_select=True,
            confirm_close=False,
        )
        self.window.events.closing += self._on_window_closing

    def _on_webview_ready(self):
        # Thread tray
        def run_tray():
            self.tray = setup_tray(
                on_open=self.show_window,
                on_quit=self.quit_app,
            )
            self.tray.run()

        threading.Thread(target=run_tray, daemon=True).start()

    def _on_window_closing(self):
        """Hide to tray instead of closing."""
        if self.window:
            self.window.hide()
        return False  # Prevent close

    def show_window(self, *args):
        if self.window:
            try:
                self.window.show()
                self.window.restore()
                return
            except Exception as e:
                print(f"[WARN] show_window: {e}")
        # Crea nuova finestra se quella esistente non e visibile
        self._create_window()
        webview.start(self._on_webview_ready, gui=None, debug=False)

    def quit_app(self, *args):
        self._quit_flag = True
        if self.tray:
            try:
                self.tray.stop()
            except Exception as e:
                print(f"[WARN] quit_app tray: {e}")
        if self.server_thread:
            try:
                self.server_thread.stop()
            except Exception as e:
                print(f"[WARN] quit_app server: {e}")
        if self.window:
            try:
                self.window.destroy()
            except Exception as e:
                print(f"[WARN] quit_app window: {e}")
        os._exit(0)


if __name__ == "__main__":
    app = DesktopApp()
    app.start()
