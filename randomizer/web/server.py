"""Local HTTP server (stdlib only) + JSON API."""
import json
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .. import config, locations
from ..fill import TOKENSANITY, Settings
from ..generate import GenerationError, generate
from ..items import KEY_ITEM_HOME, KEY_ITEMS, LABELS, NON_EXCLUDABLE
from ..nup import SUPPORTED_DISPLAY_VERSION, SUPPORTED_UPDATE_VERSION, TITLE_ID, NupArchive, NupError

STATIC_DIR = Path(__file__).resolve().parent / 'static'
MAX_BODY = 1024 * 1024
MODES = ('vanilla', 'any_chest')
_CONFIG_LOCK = threading.Lock()
_GENERATE_LOCK = threading.Lock()


def _movable_flags() -> dict[str, bool]:
    entries = list(locations.load_map().values())
    return {actor: not any(e.needs_event_patch for e in entries if e.location == home)
            for actor, home in KEY_ITEM_HOME.items()}


class _BadRequest(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def make_server(port: int, config_path: Path) -> ThreadingHTTPServer:
    config_path = Path(config_path)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'RandoLocal'

        def log_message(self, fmt, *args):
            pass

        # ---- responses ----
        def _send(self, status, body: bytes, ctype):
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, status=200):
            self._send(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                       'application/json; charset=utf-8')

        def _err(self, message, status=400, **extra):
            self._json({'ok': False, 'error': message, **extra}, status)

        def _read_json(self) -> dict:
            try:
                n = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                raise _BadRequest('Invalid Content-Length.')
            if n < 0:
                raise _BadRequest('Invalid Content-Length.')
            if n > MAX_BODY:
                raise _BadRequest('The request is too large.', 413)
            raw = self.rfile.read(n) if n else b''
            if not raw:
                return {}
            try:
                d = json.loads(raw.decode('utf-8'))
            except ValueError:
                raise _BadRequest('Invalid JSON body.')
            if not isinstance(d, dict):
                raise _BadRequest('Invalid JSON body.')
            return d

        def _dispatch(self, fn):
            try:
                fn()
            except _BadRequest as e:
                self._err(str(e), e.status)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc(file=sys.stderr)
                self._err(f'Internal error: {type(e).__name__}', 500)

        def _check_origin(self, post):
            port = self.server.server_address[1]
            allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if self.headers.get('Host') not in allowed:
                raise _BadRequest('Host not allowed.', 403)
            if post:
                origin = self.headers.get('Origin')
                if origin and origin not in {f'http://{h}' for h in allowed}:
                    raise _BadRequest('Origin not allowed.', 403)
                ctype = (self.headers.get('Content-Type') or '').lower()
                if not ctype.startswith('application/json'):
                    raise _BadRequest('Content-Type must be application/json.', 415)

        def do_GET(self):
            def run():
                self._check_origin(False)
                self._get()
            self._dispatch(run)

        def do_POST(self):
            def run():
                self._check_origin(True)
                self._post()
            self._dispatch(run)

        # ---- GET ----
        def _get(self):
            url = urlparse(self.path)
            p = url.path
            if p == '/':
                return self._static('index.html')
            if p.startswith('/static/'):
                return self._static(unquote(p[len('/static/'):]))
            if p == '/api/config':
                return self._json(config.load(config_path))
            if p == '/api/items':
                movable = _movable_flags()
                return self._json([{'actor': a, 'label': LABELS.get(a, a),
                                    'movable': movable.get(a, True),
                                    'excludable': movable.get(a, True)
                                    and a not in NON_EXCLUDABLE} for a in KEY_ITEMS])
            if p == '/api/spoiler':
                return self._spoiler(parse_qs(url.query).get('path', [''])[0])
            self._err('Not found.', 404)

        def _static(self, rel):
            types = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
                     '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml',
                     '.json': 'application/json; charset=utf-8'}
            try:
                f = (STATIC_DIR / rel).resolve()
                if STATIC_DIR.resolve() not in f.parents or not f.is_file():
                    return self._err('Not found.', 404)
                data = f.read_bytes()
            except (OSError, ValueError):
                return self._err('Not found.', 404)
            self._send(200, data, types.get(f.suffix.lower(), 'application/octet-stream'))

        def _spoiler(self, raw):
            out_dir = config.load(config_path).get('out_dir')
            try:
                f = Path(raw).resolve()
                root = Path(out_dir).resolve() if out_dir else None
                ok = bool(raw and root is not None and f.name == 'spoiler.txt'
                          and root in f.parents)
            except (OSError, ValueError, TypeError):
                ok = False
            if not ok:
                return self._err('Access denied.', 403)
            try:
                data = f.read_bytes()
            except OSError:
                return self._err('Not found.', 404)
            self._send(200, data, 'text/plain; charset=utf-8')

        # ---- POST ----
        def _post(self):
            p = urlparse(self.path).path
            body = self._read_json()
            if p == '/api/validate':
                return self._validate(body)
            if p == '/api/generate':
                return self._generate(body)
            self._err('Not found.', 404)

        def _validate(self, body):
            path = str(body.get('nup_path') or '')
            try:
                exists = bool(path) and Path(path).is_file()
            except (OSError, ValueError):
                exists = False
            if not exists:
                return self._json({'ok': False, 'error': f'The file does not exist: {path}'})
            try:
                nup = NupArchive(path)
            except NupError as e:
                return self._json({'ok': False, 'error': str(e)})
            try:
                if nup.title_id != TITLE_ID:
                    return self._json({'ok': False, 'error':
                                       'The file is not Zelda: Ocarina of Time '
                                       f'(title id 0x{nup.title_id:016X}).'})
                v = nup.update_version
                if v != SUPPORTED_UPDATE_VERSION:
                    shown = f'update {v}' if v is not None else 'no update'
                    return self._json({'ok': False, 'error':
                                       f'Unsupported game version: {shown}. '
                                       f'Version {SUPPORTED_DISPLAY_VERSION} is required.'})
                return self._json({'ok': True, 'version': SUPPORTED_DISPLAY_VERSION})
            finally:
                nup.close()

        def _generate(self, body):
            nup_path = str(body.get('nup_path') or '')
            out_dir = str(body.get('out_dir') or '')
            seed = str(body.get('seed') or '').strip()
            mode = body.get('key_items_mode', 'any_chest')
            excluded = body.get('excluded_items') or []
            if mode not in MODES:
                return self._err('Invalid key item mode.')
            if (not isinstance(excluded, list)
                    or any(not isinstance(x, str) or x not in KEY_ITEMS for x in excluded)):
                return self._err('Invalid excluded items list.')
            spoiler = body.get('spoiler', True)
            if not isinstance(spoiler, bool):
                return self._err('The spoiler setting must be true or false.')
            skip = body.get('skip_cutscenes', False)
            if not isinstance(skip, bool):
                return self._err('skip_cutscenes must be true or false')
            tokensanity = body.get('tokensanity', 'off')
            if not isinstance(tokensanity, str) or tokensanity not in TOKENSANITY:
                return self._err('Invalid Tokensanity value.')
            bad = [x for x in excluded if x in NON_EXCLUDABLE]
            if bad:
                return self._err(
                    f'Cannot exclude {LABELS.get(bad[0], bad[0])}: the logic '
                    'needs to move it for the game to be beatable.')
            if not nup_path or not out_dir:
                return self._err('The .nup path or the output folder is missing.')
            movable = _movable_flags()
            # Non-movable items never move: they must not alter the RNG key.
            effective = frozenset(x for x in excluded if movable.get(x, True))
            settings = Settings(seed=seed, key_items_mode=mode,
                                excluded_items=effective, spoiler=spoiler,
                                skip_cutscenes=skip, tokensanity=tokensanity)
            if not _GENERATE_LOCK.acquire(blocking=False):
                return self._err('A generation is already in progress.', 409)
            try:
                res = generate(nup_path, out_dir, settings,
                               overwrite=bool(body.get('overwrite', False)))
            except GenerationError as e:
                extra = {'exists': True, 'mod_dir': e.mod_dir} if e.exists else {}
                return self._json({'ok': False, 'error': str(e), **extra})
            finally:
                _GENERATE_LOCK.release()
            with _CONFIG_LOCK:
                cfg = config.load(config_path)
                cfg.update({'nup_path': nup_path, 'out_dir': out_dir,
                            'last_settings': {'seed': seed, 'key_items_mode': mode,
                                              'excluded_items': sorted(excluded),
                                              'spoiler': settings.spoiler,
                                              'skip_cutscenes': skip,
                                              'tokensanity': tokensanity}})
                config.save(config_path, cfg)
            self._json({'ok': True, 'seed': res.seed, 'mod_dir': res.mod_dir,
                        'spoiler_txt': res.spoiler_txt,
                        'changed_files': res.changed_files})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
