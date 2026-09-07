from gateway.engine import SuperenalottoEngine, get_user_data_dir, migrate_db_if_needed

import json, os, sys, threading, time, webbrowser
import logging
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler, HTTPStatus, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

PORT = 8766

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path():
    if getattr(sys, 'frozen', False):
        data_dir = get_user_data_dir()
        docs_cfg = os.path.join(data_dir, 'config.json')
        if os.path.exists(docs_cfg):
            return docs_cfg
        exe_cfg = os.path.join(os.path.dirname(sys.executable), 'config.json')
        if os.path.exists(exe_cfg):
            return exe_cfg
        try:
            mei_cfg = os.path.join(sys._MEIPASS, 'config.json')
            if os.path.exists(mei_cfg):
                return mei_cfg
        except Exception:
            pass
        return docs_cfg
    return os.path.join(get_base_dir(), 'config.json')

def validate_timestamp(ts):
    try:
        datetime.strptime(ts, '%Y%m%d_%H%M%S')
        return True
    except (ValueError, TypeError):
        return False

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

def validate_numbers(nums):
    """6 numeri unici 1-90."""
    if not isinstance(nums, list) or len(nums) != 6:
        return False
    try:
        ints = [int(x) for x in nums]
    except Exception:
        return False
    if len(set(ints)) != 6:
        return False
    return all(1 <= n <= 90 for n in ints)

def sanitize_input(data, max_length=1000):
    if isinstance(data, str) and len(data) > max_length:
        return data[:max_length]
    return data

class SuperenalottoHandler(SimpleHTTPRequestHandler):
    engine = None

    def __init__(self, *args, **kwargs):
        base_dir = get_base_dir()
        web_dir = os.path.join(base_dir, 'web')
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/stats':
            self._json_response(self.engine.stats)
        elif path == '/api/estrazioni':
            try:
                n = int(parse_qs(parsed.query).get('n', [20])[0])
                if n < 1 or n > 1000:
                    self._json_response({'error': 'n must be between 1 and 1000'})
                    return
                self._json_response(self.engine.get_estrazioni_recenti(n))
            except (ValueError, IndexError) as e:
                self._json_response({'error': str(e)})
        elif path == '/api/giocate':
            self._json_response(self.engine.get_giocate())
        elif path == '/api/prossima':
            self._json_response({
                'data': self.engine.prossima_estrazione(),
                'oggi': self.engine.oggi_estrazione(),
            })
        elif path == '/api/jackpot':
            try:
                jp_val = self.engine.fetch_jackpot_sisal()
                jackpot_val = f'EUR {jp_val:,.0f}'.replace(',', '.')
            except Exception as e:
                logger.warning(f"fetch_jackpot_sisal: {e}")
                jackpot_val = 'EUR 210.000.000'
            self._json_response({'jackpot': jackpot_val})
        elif path == '/api/premi':
            self._json_response(self.engine.get_premi())
        elif path == '/api/valuta':
            try:
                n = int(parse_qs(parsed.query).get('n', [50])[0])
                self._json_response(self.engine.valuta_strategie(n))
            except (ValueError, IndexError) as e:
                self._json_response({'error': str(e)})
        elif path == '/api/grafici':
            self._json_response(self.engine.get_grafici())
        elif path == '/api/genera':
            try:
                n = int(parse_qs(parsed.query).get('n', [1])[0])
                n = max(1, min(5, n))
                strategy = parse_qs(parsed.query).get('strategy', ['quartile'])[0]
                q = parse_qs(parsed.query)
                resolved = strategy
                if strategy == 'auto':
                    resolved = self.engine.resolve_auto_strategy()
                elif strategy == 'quartile' and q.get('auto', ['0'])[0] in ('1','true'):
                    # compat: Gioca senza esplicito -> usa auto
                    resolved = self.engine.resolve_auto_strategy()
                schedine = self.engine.genera_schedine(n, strategy=resolved)
                self._json_response([{
                    'nums': s, 'sum': sum(s), 'strategy': resolved, 'requested': strategy
                } for s in schedine])
            except (ValueError, IndexError) as e:
                self._json_response({'error': str(e)})
        elif path == '/api/backups':
            try:
                result = self.engine.list_backups()
                self._json_response({'backups': result})
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/backup_info':
            try:
                backup_dir = os.path.join(get_user_data_dir(), 'backups')
                exists = os.path.exists(backup_dir)
                count = len(os.listdir(backup_dir)) if exists else 0
                self._json_response({'exists': exists, 'count': count})
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/backtest':
            try:
                strategy = parse_qs(parsed.query).get('strategy', ['quartile'])[0]
                n = int(parse_qs(parsed.query).get('n', [50])[0])
                result = self.engine.run_backtest(strategy=strategy, n=n)
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/heatmap':
            try:
                result = self.engine.get_heatmap_data()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/trend':
            try:
                result = self.engine.get_trend_data()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/ranking':
            try:
                result = self.engine.get_strategy_comparison()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/notifications':
            try:
                result = self.engine.get_notifications()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/alerts':
            try:
                result = self.engine.get_active_alerts()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/salva':
            try:
                data = self._read_json()
                if not data:
                    self._json_response({'ok': False, 'error': 'Invalid JSON'})
                    return
                today = data.get('data') or datetime.now().strftime('%Y-%m-%d')
                if not validate_date(today):
                    self._json_response({'ok': False, 'error': 'Invalid date format, use YYYY-MM-DD'})
                    return
                schedine = data.get('schedine', [])
                if len(schedine) > 100:
                    self._json_response({'ok': False, 'error': 'Batch too large, max 100 schedine'})
                    return
                c = self.engine.conn.cursor()
                c.execute('SELECT COUNT(*) FROM giocate WHERE data=? AND verificato=0', (today,))
                already_exists = c.fetchone()[0] > 0
                if already_exists:
                    self._json_response({'ok': False, 'blocked': True, 'msg': 'Schedine gi salvate per questa data. Verifica o cancella prima.'})
                    return
                saved = 0
                for sched in schedine:
                    nums = sched.get('nums', [])
                    if not validate_numbers(nums):
                        continue
                    try:
                        c.execute(
                            'INSERT OR IGNORE INTO giocate (data, numeri, somma, verificato) VALUES (?,?,?,0)',
                            (today, '-'.join(map(str, nums)), sum(nums)),
                        )
                        if c.rowcount > 0:
                            saved += 1
                    except sqlite3.IntegrityError as e:
                        logger.warning(f'salva gioccata skip: {e}')
                        continue
                self.engine.conn.commit()
                if saved > 0:
                    self.engine.save_tracking()
                self._json_response({'ok': True, 'saved': saved, 'blocked': False})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})
        elif path == '/api/verifica':
            try:
                body = self._read_json()
                only_unchecked = body.get('only_unchecked', False)
                result = self.engine.verifica_tutte(only_unchecked=only_unchecked)
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/cancella':
            try:
                body = self._read_json()
                gid = body.get('id')
                if gid:
                    self.engine.cancella_giocata(gid)
                    self.engine.save_tracking()
                self._json_response({'ok': True, 'notification': 'Schedina cancellata'})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})
        elif path == '/api/clear_giocate':
            try:
                c = self.engine.conn.cursor()
                c.execute('DELETE FROM giocate')
                self.engine.conn.commit()
                self._json_response({'ok': True, 'deleted': True, 'notification': 'Tutte le schedine cancellate'})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})
        elif path == '/api/aggiorna_storico':
            try:
                result = self.engine.aggiorna_storico()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/chiudi':
            self._json_response({'ok': True})
        elif path == '/api/importa_giocata':
            try:
                data = self._read_json()
                if not data:
                    self._json_response({'ok': False, 'error': 'Invalid JSON'})
                    return
                data_str = data.get('data', '')
                nums = data.get('numeri', [])
                if not validate_date(data_str):
                    self._json_response({'ok': False, 'error': 'Invalid date format, use YYYY-MM-DD'})
                    return
                if not validate_numbers(nums):
                    self._json_response({'ok': False, 'error': 'Must provide 6 unique numbers between 1-90'})
                    return
                somma = sum(nums)
                ok = self.engine.salva_giocata(data_str, nums, somma)
                if ok:
                    self.engine.save_tracking()
                self._json_response({'ok': ok, 'data': data_str, 'numeri': nums})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})
        elif path == '/api/save_tracking':
            try:
                result = self.engine.save_tracking()
                self._json_response(result)
            except Exception as e:
                self._json_response({'error': str(e)})
        elif path == '/api/backup':
            try:
                result = self.engine.backup_dati()
                self._json_response({'ok': True, **result})
            except Exception as e:
                self._json_response({'error': str(e)})
        # rimosso duplicato POST /api/backups (conflict con GET) — usa GET /api/backups o POST /api/backup
        elif path == '/api/restore_backup':
            try:
                data = self._read_json()
                if not data:
                    self._json_response({'ok': False, 'error': 'Invalid JSON'})
                    return
                ts = data.get('timestamp', '')
                if not ts:
                    self._json_response({'ok': False, 'error': 'timestamp richiesto'})
                    return
                if not validate_timestamp(ts):
                    self._json_response({'ok': False, 'error': 'Invalid timestamp format, use YYYYMMDD_HHMMSS'})
                    return
                result = self.engine.restore_backup(ts)
                self._json_response({'ok': True, **result})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})
        else:
            self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 100000:
            self.send_error(413, 'Payload too large')
            return {}
        body = self.rfile.read(length)
        try:
            return json.loads(body.decode('utf-8')) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        # CORS ristretto a localhost
        origin = self.headers.get('Origin', '')
        if origin in ('http://localhost:8766', 'http://127.0.0.1:8766'):
            self.send_header('Access-Control-Allow-Origin', origin)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        pass

def open_browser():
    webbrowser.open(f'http://localhost:{PORT}')

def start_server(open_browser_flag=True):
    engine = SuperenalottoEngine()
    SuperenalottoHandler.engine = engine

    def _auto_tasks():
        import traceback
        try:
            time.sleep(5)
            try:
                engine._import_tracking()
            except Exception:
                pass
            added, scraped = engine.scrape_historical(pages=1)
            logger.info(f"[AUTO] scrape_historical: added={added}, scraped={scraped}")
            if added > 0:
                engine._load_records()
            result = engine.verifica_tutte(only_unchecked=True)
            logger.info(f"[AUTO] auto_check_new_draws: checked={result['checked']} skipped={result['skipped']}")
            engine.save_tracking()
            logger.info("[AUTO] tracking salvato")
            backup_result = engine.backup_giornaliero()
            logger.info(f"[AUTO] backup: {backup_result}")
        except Exception as e:
            logger.error(f'auto_tasks: {e}', exc_info=True)

    threading.Thread(target=_auto_tasks, daemon=True).start()

    server = ThreadingHTTPServer(('127.0.0.1', PORT), SuperenalottoHandler)
    server.timeout = 0.5
    logger.info(f"SuperEnalotto Server running on http://localhost:{PORT}")

    if open_browser_flag:
        threading.Timer(1.0, open_browser).start()

    try:
        server.serve_forever(poll_interval=0.05)
    except KeyboardInterrupt:
        logger.info('Shutting down...')
    finally:
        engine.close()
        server.server_close()
