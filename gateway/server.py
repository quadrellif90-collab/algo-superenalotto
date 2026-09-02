"""
SuperEnalotto Server - HTTP API + Static File Server.
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from gateway.engine import SuperenalottoEngine

# Porta del server (evita conflitto con AI Gateway Manager su 8765)
PORT = 8766


def get_base_dir():
    """Restituisce la directory base (compatibile con PyInstaller)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SuperenalottoHandler(SimpleHTTPRequestHandler):
    engine = None

    def __init__(self, *args, **kwargs):
        base_dir = get_base_dir()
        web_dir = os.path.join(base_dir, "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API endpoints
        if path == "/api/stats":
            self._json_response(self.engine.stats)
        elif path == "/api/estrazioni":
            n = int(parse_qs(parsed.query).get("n", [20])[0])
            self._json_response(self.engine.get_estrazioni_recenti(n))
        elif path == "/api/giocate":
            self._json_response(self.engine.get_giocate())
        elif path == "/api/prossima":
            self._json_response({
                "data": self.engine.prossima_estrazione(),
                "oggi": self.engine.oggi_estrazione(),
            })
        elif path == "/api/genera":
            n = int(parse_qs(parsed.query).get("n", [1])[0])
            n = max(1, min(5, n))
            schedine = self.engine.genera_schedine(n)
            self._json_response([{"nums": s, "sum": sum(s)} for s in schedine])
        elif path == "/api/jackpot":
            self._json_response({"jackpot": "€218.700.000"})
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/salva":
            data = self._read_json()
            today = data.get("data") or __import__("datetime").datetime.now().strftime("%Y-%m-%d")
            for sched in data.get("schedine", []):
                nums = sched.get("nums", [])
                self.engine.salva_giocata(today, nums, sum(nums))
            self._json_response({"ok": True})
        elif path == "/api/verifica":
            body = self._read_json()
            only_unchecked = body.get("only_unchecked", False)
            result = self.engine.verifica_tutte(only_unchecked=only_unchecked)
            self._json_response(result)
        elif path == "/api/cancella":
            body = self._read_json()
            gid = body.get("id")
            if gid:
                self.engine.cancella_giocata(gid)
            self._json_response({"ok": True})
        else:
            self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8")) if body else {}

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # silenzia log


def open_browser():
    webbrowser.open(f"http://localhost:{PORT}")


def start_server(open_browser_flag=True):
    engine = SuperenalottoEngine()
    SuperenalottoHandler.engine = engine

    server = HTTPServer(("127.0.0.1", PORT), SuperenalottoHandler)
    print(f"SuperEnalotto Server running on http://localhost:{PORT}")

    if open_browser_flag:
        threading.Timer(1.0, open_browser).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        engine.close()
        server.server_close()


if __name__ == "__main__":
    start_server()
