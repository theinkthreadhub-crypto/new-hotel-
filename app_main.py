# -*- coding: utf-8 -*-
"""
Setu - Restaurant & Hotel POS - Standalone Desktop Launcher + LAN Server
Powered by Aghanya Devanya Enterprises

The PC running this file is the "main counter". It:
  * serves hotel_erp.html to this PC and to phones/tablets on the same WiFi
  * keeps the single shared database on disk (setu-db.json) with daily backups
  * opens the desktop window (unless started with --server)

Usage:
  python app_main.py            -> desktop window + LAN server
  python app_main.py --server   -> LAN server only (no window)
  python app_main.py --server --port 8000 --data <folder>
"""
import os
import sys
import json
import time
import shutil
import socket
import secrets
import threading
import http.server
import urllib.request
import urllib.error
import base64
import copy

APP_PORT = 8000
MAX_BODY = 200 * 1024 * 1024   # 200 MB upper bound for one database upload
KEEP_BACKUPS = 60              # daily backup files kept
print_lock = threading.Lock()  # one print job at a time keeps receipts from interleaving


def get_base_dir():
    # If running as PyInstaller bundled executable
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        # The page built into the EXE always wins: an old hotel_erp.html lying next to a new
        # EXE used to bring the old version back. Testers can opt in with use-local-html.txt.
        if os.path.exists(os.path.join(exe_dir, 'use-local-html.txt')) and os.path.exists(os.path.join(exe_dir, 'hotel_erp.html')):
            return exe_dir
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


def default_data_dir():
    # User data directory on Windows (%LOCALAPPDATA%\AghanyaDevanyaERP\Data)
    local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    return os.path.join(local_app_data, 'AghanyaDevanyaERP', 'Data')


def lan_ips():
    ips = set()
    try:
        # UDP "connect" sends nothing; it only picks the outgoing interface
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            ips.add(s.getsockname()[0])
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except Exception:
        pass
    return sorted(ip for ip in ips if not ip.startswith('127.'))


# ---------------- Direct (silent) printing to Windows printers ----------------
# Receipts arrive as ready ESC/POS bytes and go to the printer as a RAW job,
# so no print dialog appears. Works with thermal printers that have a Windows driver.
def _winspool():
    import ctypes
    from ctypes import wintypes
    ws = ctypes.WinDLL('winspool.drv')
    ws.EnumPrintersW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
    ws.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
    ws.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
    ws.StartPagePrinter.argtypes = [wintypes.HANDLE]
    ws.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    ws.EndPagePrinter.argtypes = [wintypes.HANDLE]
    ws.EndDocPrinter.argtypes = [wintypes.HANDLE]
    ws.ClosePrinter.argtypes = [wintypes.HANDLE]
    ws.GetDefaultPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    return ctypes, wintypes, ws


def list_printers():
    if os.name != 'nt':
        return [], ''
    ctypes, wintypes, ws = _winspool()

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [('pPrinterName', wintypes.LPWSTR), ('pServerName', wintypes.LPWSTR), ('Attributes', wintypes.DWORD)]

    flags = 2 | 4   # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
    needed, count = wintypes.DWORD(), wintypes.DWORD()
    ws.EnumPrintersW(flags, None, 4, None, 0, ctypes.byref(needed), ctypes.byref(count))
    names = []
    if needed.value:
        buf = ctypes.create_string_buffer(needed.value)
        if ws.EnumPrintersW(flags, None, 4, buf, needed, ctypes.byref(needed), ctypes.byref(count)):
            arr = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_4))
            names = [arr[i].pPrinterName for i in range(count.value)]
    size = wintypes.DWORD(0)
    ws.GetDefaultPrinterW(None, ctypes.byref(size))
    default = ''
    if size.value:
        dbuf = ctypes.create_unicode_buffer(size.value)
        if ws.GetDefaultPrinterW(dbuf, ctypes.byref(size)):
            default = dbuf.value
    return names, default


def print_raw(printer, data):
    if os.name != 'nt':
        raise OSError('Direct printing is supported on Windows only')
    ctypes, wintypes, ws = _winspool()

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [('pDocName', wintypes.LPWSTR), ('pOutputFile', wintypes.LPWSTR), ('pDatatype', wintypes.LPWSTR)]

    h = wintypes.HANDLE()
    if not ws.OpenPrinterW(printer, ctypes.byref(h), None):
        raise OSError(f'Printer "{printer}" not found')
    try:
        doc = DOC_INFO_1('Setu Receipt', None, 'RAW')
        if not ws.StartDocPrinterW(h, 1, ctypes.byref(doc)):
            raise OSError('The printer did not accept the job')
        try:
            ws.StartPagePrinter(h)
            buf = ctypes.create_string_buffer(data, len(data))
            written = wintypes.DWORD(0)
            ok = ws.WritePrinter(h, buf, len(data), ctypes.byref(written))
            ws.EndPagePrinter(h)
            if not ok or written.value != len(data):
                raise OSError('Could not send data to the printer')
        finally:
            ws.EndDocPrinter(h)
    finally:
        ws.ClosePrinter(h)


class SetuStore:
    """Single shared database file with optimistic versioning."""

    def __init__(self, data_dir):
        self.dir = data_dir
        self.path = os.path.join(data_dir, 'setu-db.json')
        self.backup_dir = os.path.join(data_dir, 'Backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.on_write = None        # set by CloudSync to push changes quickly
        self.version = 0
        self.saved_at = 0
        self.raw = 'null'           # JSON text of the data object
        self.tokens_path = os.path.join(data_dir, 'setu-devices.json')
        self.tokens = {}            # token -> role, for LAN devices (kept across restarts)
        try:
            with open(self.tokens_path, 'r', encoding='utf-8') as f:
                self.tokens = json.load(f)
        except Exception:
            pass
        self._load()

    def add_token(self, role):
        token = secrets.token_hex(16)
        self.tokens[token] = role
        try:
            with open(self.tokens_path, 'w', encoding='utf-8') as f:
                json.dump(self.tokens, f)
        except Exception:
            pass
        return token

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            self.version = int(doc.get('version', 0))
            self.saved_at = doc.get('savedAt', 0)
            self.raw = json.dumps(doc.get('data'), ensure_ascii=False)
        except Exception:
            # Never overwrite a file we could not read: keep it aside and start empty
            bad = self.path + '.corrupt-' + time.strftime('%Y%m%d-%H%M%S')
            try:
                shutil.copy2(self.path, bad)
            except Exception:
                pass
            self.version, self.raw = 0, 'null'

    def data(self):
        return json.loads(self.raw)

    def log(self, msg):
        try:
            with open(os.path.join(self.dir, 'setu-server.log'), 'a', encoding='utf-8') as f:
                f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
        except Exception:
            pass

    def write(self, data_obj):
        # Nothing changes in memory until the file is safely on disk, so a failed
        # write can never leave the server "ahead" of what survives a restart.
        version = self.version + 1
        saved_at = int(time.time() * 1000)
        raw = json.dumps(data_obj, ensure_ascii=False)
        doc = '{"version": %d, "savedAt": %d, "data": %s}' % (version, saved_at, raw)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(doc)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(10):
            try:
                os.replace(tmp, self.path)   # atomic swap: a power cut leaves old or new, never half
                break
            except PermissionError:
                # Antivirus / indexer may hold the file for a moment on Windows
                if attempt == 9:
                    raise
                time.sleep(0.2)
        self.version, self.saved_at, self.raw = version, saved_at, raw
        if self.on_write:
            self.on_write()
        # One rolling backup per day (last write of the day wins)
        try:
            shutil.copy2(self.path, os.path.join(self.backup_dir, 'setu-' + time.strftime('%Y-%m-%d') + '.json'))
            files = sorted(x for x in os.listdir(self.backup_dir) if x.startswith('setu-') and x.endswith('.json'))
            for old in files[:-KEEP_BACKUPS]:
                os.remove(os.path.join(self.backup_dir, old))
        except Exception:
            pass

    def check_pin(self, pin):
        try:
            d = self.data() or {}
        except Exception:
            return None
        st = d.get('settings') or {}
        auth = d.get('auth') or {}
        pin = str(pin or '')
        if not pin:
            return None
        if pin in (str(st.get('adminPin') or ''), str(auth.get('password') or '')):
            return 'admin', auth.get('ownerName') or 'Manager'
        for s in d.get('staff') or []:
            if not s.get('left') and s.get('access') and str(s.get('pin') or '') == pin:
                return {'manager': 'admin'}.get(s['access'], s['access']), s.get('name') or 'Staff'
        if pin == str(st.get('cashierPin') or ''):
            return 'cashier', 'Cashier'
        return None


# ---------------- Cloud Sync (Setu Cloud on Cloudflare) ----------------
# This PC stays the master. A background thread mirrors the database to the hotel's
# Setu Cloud Worker (cloud/ folder) so the owner / captains can use Setu over the internet.
# Changes on both sides are joined with the same 3-way merge the app uses (merge3 in
# hotel_erp.html), ported below. Keep the two in step.
MISSING = object()


def _js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def jeq(a, b):
    if a is MISSING or b is MISSING:
        return a is b
    return a is b or _js(a) == _js(b)


def _scalar_key(x):
    return (type(x).__name__, x)


def merge_node(b, m, t, depth):
    if jeq(m, b):
        return t           # only the other side changed it
    if jeq(t, b):
        return m           # only this side changed it
    if jeq(m, t):
        return m
    if isinstance(m, list) and isinstance(t, list):
        both = m + t
        if all(isinstance(x, dict) and x.get('id') for x in both):
            return merge_by_id(b if isinstance(b, list) else [], m, t, depth)
        if all(x is not None and not isinstance(x, (dict, list)) for x in both):
            return list({_scalar_key(x): x for x in both}.values())   # e.g. usedKeys
        return m
    if isinstance(m, dict) and isinstance(t, dict) and depth < 6:
        bo = b if isinstance(b, dict) else {}
        out = {}
        for k in dict.fromkeys(list(m) + list(t) + list(bo)):
            in_m, in_t, in_b = k in m, k in t, k in bo
            if not in_m and not in_t:
                continue
            if not in_m:
                if in_b and jeq(t[k], bo[k]):
                    continue    # I deleted it
                out[k] = t[k]
                continue
            if not in_t:
                if in_b and jeq(m[k], bo[k]):
                    continue    # they deleted it
                out[k] = m[k]
                continue
            out[k] = merge_node(bo[k] if in_b else MISSING, m[k], t[k], depth + 1)
        return out
    return m               # both changed one value: "mine" wins


def merge_by_id(b, m, t, depth):
    def by_id(lst):
        return {x.get('id') if isinstance(x, dict) else None: x for x in lst}
    bm, mm, tm = by_id(b), by_id(m), by_id(t)
    out, seen = [], set()
    for x in t + m:
        if x['id'] in seen:
            continue
        seen.add(x['id'])
        bx, mx, tx = bm.get(x['id']), mm.get(x['id']), tm.get(x['id'])
        if mx is not None and tx is not None:
            v = merge_node(bx if bx is not None else MISSING, mx, tx, depth + 1)
        elif mx is not None:
            v = None if bx is not None and jeq(mx, bx) else mx   # they deleted it
        else:
            v = None if bx is not None and jeq(tx, bx) else tx   # I deleted it
        if v is not None:
            out.append(v)
    return out


def _num(x):
    # JavaScript "+x || 0"
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x if x == x else 0
    try:
        s = str(x).strip()
        v = float(s) if s else 0
        return int(v) if float(v).is_integer() else v
    except Exception:
        return 0


def merge3(base, mine, theirs):
    out = copy.deepcopy(merge_node(base if base is not None else {}, mine, theirs, 0))
    ms, ts = mine.get('seq') or {}, theirs.get('seq') or {}
    seq = {**ts, **ms}
    # Running numbers must never go backwards
    for k in ('bill', 'kot'):
        seq[k] = max(_num(ms.get(k)), _num(ts.get(k)))
    # Tokens restart daily, so the newer day wins before comparing numbers
    md, td = str(ms.get('tokenDate') or ''), str(ts.get('tokenDate') or '')
    seq['tokenDate'] = md if md > td else td
    if md == td:
        seq['token'] = max(_num(ms.get('token')), _num(ts.get('token')))
    else:
        seq['token'] = _num(ms.get('token')) if md > td else _num(ts.get('token'))
    out['seq'] = seq
    # Both sides may have used the same bill / KOT number: new ones from "mine" get fresh numbers
    for lst, key in (('bills', 'bill'), ('kots', 'kot')):
        theirs_l = [x for x in theirs.get(lst) or [] if isinstance(x, dict)]
        base_l = [x for x in (base or {}).get(lst) or [] if isinstance(x, dict)]
        their_ids = {x.get('id') for x in theirs_l}
        base_ids = {x.get('id') for x in base_l}
        taken = {x.get('no') for x in theirs_l}
        for x in out.get(lst) or []:
            if not isinstance(x, dict):
                continue
            if x.get('id') not in their_ids and x.get('id') not in base_ids and x.get('no') in taken:
                seq[key] += 1
                x['no'] = seq[key]
            taken.add(x.get('no'))
    return out


def _write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


class CloudBusy(Exception):
    pass


class CloudSync:
    """Two-way sync between this PC's setu-db.json and the hotel's Setu Cloud Worker."""

    def __init__(self, store):
        self.store = store
        self.cfg_path = os.path.join(store.dir, 'setu-cloud.json')
        self.state_path = os.path.join(store.dir, 'setu-cloud-state.json')
        self.base_path = os.path.join(store.dir, 'setu-cloud-base.json')
        self.cfg = _read_json(self.cfg_path, {})
        self.state = _read_json(self.state_path, {})
        self.status = {'ok': None, 'at': 0, 'error': '', 'cloudVersion': self.state.get('cv', -1)}
        self.wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def configured(self):
        return bool(self.cfg.get('url') and self.cfg.get('hotel') and self.cfg.get('key') and self.cfg.get('enabled', True))

    def public(self):
        # The sync key never leaves this PC
        return {'configured': self.configured(), 'url': self.cfg.get('url', ''), 'hotel': self.cfg.get('hotel', ''),
                'enabled': self.cfg.get('enabled', True), 'hasKey': bool(self.cfg.get('key')), **self.status}

    def set_config(self, url, hotel, key, enabled=True):
        url = (url or '').strip().rstrip('/')
        hotel = ''.join(c for c in (hotel or '').upper() if c.isalnum())
        if url.endswith('/hotel_erp.html'):
            url = url[:-len('/hotel_erp.html')]
        key = (key or '').strip() or self.cfg.get('key', '')
        if enabled:
            if not (url.startswith('https://') or url.startswith(('http://127.0.0.1:', 'http://localhost:'))):
                raise ValueError('The cloud URL must start with https://')
            if not hotel:
                raise ValueError('Please enter the Hotel Code')
            if not key:
                raise ValueError('Please enter the Cloud Sync Key')
            try:
                code, _ = self._request('GET', '/api/version', url=url, key=key, hotel=hotel)
            except Exception as e:
                raise ValueError('Could not connect to the cloud: ' + str(e))
            if code == 401:
                raise ValueError('Invalid Cloud Sync Key')
            if code == 404:
                raise ValueError('Hotel Code not found on the cloud')
            if code != 200:
                raise ValueError(f'Unexpected response from the cloud (HTTP {code})')
        if url != self.cfg.get('url') or hotel != self.cfg.get('hotel'):
            # A different cloud starts from scratch: nothing is "already synced" there
            self.state = {}
            try:
                os.remove(self.base_path)
            except OSError:
                pass
            _write_json(self.state_path, self.state)
        self.cfg = {'url': url, 'hotel': hotel, 'key': key, 'enabled': bool(enabled)}
        _write_json(self.cfg_path, self.cfg)
        self.status = {'ok': None, 'at': 0, 'error': '', 'cloudVersion': self.state.get('cv', -1)}
        self.wake.set()

    def _request(self, method, path, body=None, url=None, key=None, hotel=None):
        req = urllib.request.Request(
            (url or self.cfg['url']) + path,
            data=body.encode('utf-8') if body is not None else None,
            method=method,
            headers={'X-Setu-Sync': key or self.cfg['key'], 'X-Setu-Hotel': hotel or self.cfg['hotel'],
                     'Content-Type': 'application/json',
                     'User-Agent': 'Setu-Main-Counter/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def _loop(self):
        while True:
            self.wake.wait(5 if self.status.get('ok') is not False else 20)
            self.wake.clear()
            if not self.configured():
                continue
            try:
                self._tick()
                self.status.update(ok=True, at=int(time.time() * 1000), error='')
            except CloudBusy:
                self.wake.set()     # someone wrote in between: try again right away
            except Exception as e:
                msg = str(e) or e.__class__.__name__
                if self.status.get('error') != msg:
                    self.store.log('CLOUD SYNC: ' + msg)
                self.status.update(ok=False, at=int(time.time() * 1000), error=msg)

    def _tick(self):
        code, text = self._request('GET', '/api/version')
        if code != 200:
            raise OSError('Invalid Cloud Sync Key' if code == 401 else f'Cloud HTTP {code}')
        cv = json.loads(text)['version']
        st_cv, st_lv = self.state.get('cv', -1), self.state.get('lv', -1)
        if cv == st_cv and self.store.version == st_lv:
            return
        base = _read_json(self.base_path, None) if st_cv >= 0 else None
        if cv != st_cv or base is None:
            code, text = self._request('GET', '/api/db')
            if code != 200:
                raise OSError(f'Cloud HTTP {code}')
            doc = json.loads(text)
            cv, theirs = doc['version'], (doc['data'] if doc['version'] else None)
        else:
            theirs = copy.deepcopy(base)     # cloud unchanged since the last sync
        with self.store.lock:
            lv = self.store.version
            local = self.store.data() if lv else None
        if local is None and theirs is None:
            return
        if theirs is None:
            merged = local
        elif local is None:
            merged = theirs
        else:
            # Cloud as "mine" so bills already printed at this counter keep their numbers
            merged = merge3(base, theirs, local)
        if not isinstance(merged, dict) or 'settings' not in merged:
            raise OSError('Merge ke baad data galat laga, sync roka gaya')
        if theirs is None or not jeq(merged, theirs):
            body = '{"baseVersion": %d, "force": false, "data": %s}' % (cv, json.dumps(merged, ensure_ascii=False))
            code, text = self._request('POST', '/api/db', body)
            if code == 409:
                raise CloudBusy()
            if code == 402:
                raise OSError('Setu Cloud subscription expired. Please renew online (billing continues on this PC).')
            if code != 200:
                raise OSError(f'Cloud save failed (HTTP {code})')
            cv = json.loads(text)['version']
        with self.store.lock:
            if self.store.version == lv:
                final = merged
                if local is None or not jeq(merged, local):
                    self.store.write(final)
            else:
                # The counter saved while we talked to the cloud: put its new edits on top
                final = merge3(local, merged, self.store.data())
                self.store.write(final)
            new_lv = self.store.version
        _write_json(self.base_path, merged)
        # lv = -1 tells the next round that this PC still has edits the cloud lacks
        self.state = {'cv': cv, 'lv': new_lv if jeq(final, merged) else -1}
        _write_json(self.state_path, self.state)
        self.status['cloudVersion'] = cv


def make_handler(base_dir, store, port, cloud=None):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=base_dir, **kwargs)

        def log_message(self, format, *args):
            pass  # suppress log output

        # ---------- helpers ----------
        def is_local(self):
            return self.client_address[0] in ('127.0.0.1', '::1', '::ffff:127.0.0.1')

        def role(self):
            if self.is_local():
                return 'local'
            return store.tokens.get(self.headers.get('X-Setu-Token', ''))

        def send_json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_db(self):
            # Data is already JSON text; avoid a parse/serialize round-trip on big databases
            body = ('{"version": %d, "savedAt": %d, "data": %s}' % (store.version, store.saved_at, store.raw)).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def read_json(self):
            n = int(self.headers.get('Content-Length') or 0)
            if n <= 0 or n > MAX_BODY:
                raise ValueError('bad length')
            return json.loads(self.rfile.read(n).decode('utf-8'))

        def end_headers(self):
            # The app page must never come from a stale cache on LAN devices
            if self.path.split('?')[0].endswith('.html'):
                self.send_header('Cache-Control', 'no-cache')
            super().end_headers()

        # ---------- routes ----------
        def do_GET(self):
            path = self.path.split('?')[0]
            if not path.startswith('/api/'):
                return super().do_GET()
            if path == '/api/ping':
                return self.send_json(200, {'setu': True, 'version': store.version, 'local': self.is_local()})
            if path == '/api/cloud':
                if not self.is_local():
                    return self.send_json(403, {'error': 'main counter only'})
                return self.send_json(200, cloud.public() if cloud else {'configured': False})
            if path == '/api/info':
                return self.send_json(200, {'setu': True, 'port': port, 'ips': lan_ips(), 'local': self.is_local()})
            if not self.role():
                return self.send_json(401, {'error': 'pin required'})
            if path == '/api/version':
                return self.send_json(200, {'version': store.version})
            if path == '/api/db':
                with store.lock:
                    return self.send_db()
            if path == '/api/printers':
                try:
                    names, default = list_printers()
                    return self.send_json(200, {'printers': names, 'default': default})
                except Exception as e:
                    return self.send_json(500, {'error': str(e)})
            return self.send_json(404, {'error': 'not found'})

        def do_POST(self):
            path = self.path.split('?')[0]
            if path == '/api/login':
                try:
                    pin = self.read_json().get('pin')
                except Exception:
                    return self.send_json(400, {'error': 'bad request'})
                found = store.check_pin(pin)
                if not found:
                    time.sleep(1)   # slow down PIN guessing
                    return self.send_json(403, {'error': 'wrong pin'})
                role, name = found
                token = store.add_token(role)
                return self.send_json(200, {'token': token, 'role': role, 'name': name})
            if path == '/api/cloud':
                # Cloud URL + sync key are set only from the main counter PC itself
                if not self.is_local() or not cloud:
                    return self.send_json(403, {'error': 'main counter only'})
                try:
                    body = self.read_json()
                    cloud.set_config(body.get('url'), body.get('hotel'), body.get('key'), bool(body.get('enabled', True)))
                except ValueError as e:
                    return self.send_json(400, {'error': str(e)})
                except Exception:
                    return self.send_json(400, {'error': 'bad request'})
                return self.send_json(200, cloud.public())
            if path == '/api/print':
                if not self.role():
                    return self.send_json(401, {'error': 'pin required'})
                try:
                    body = self.read_json()
                    data = base64.b64decode(body.get('data') or '')
                    printer = str(body.get('printer') or '')
                    if not printer or not data or len(data) > 2 * 1024 * 1024:
                        return self.send_json(400, {'error': 'bad request'})
                    with print_lock:
                        print_raw(printer, data)
                    return self.send_json(200, {'ok': True})
                except Exception as e:
                    return self.send_json(500, {'error': str(e)})
            if path == '/api/db':
                role = self.role()
                if not role:
                    return self.send_json(401, {'error': 'pin required'})
                try:
                    body = self.read_json()
                except Exception:
                    return self.send_json(400, {'error': 'bad request'})
                data = body.get('data')
                if not isinstance(data, dict) or 'settings' not in data:
                    return self.send_json(400, {'error': 'invalid data'})
                force = bool(body.get('force'))
                with store.lock:
                    # First upload (migration from the browser) and forced restore are main-counter only
                    if (store.version == 0 or force) and role not in ('local', 'admin'):
                        return self.send_json(403, {'error': 'main counter only'})
                    if not force and int(body.get('baseVersion', -1)) != store.version:
                        return self.send_db_conflict()
                    try:
                        store.write(data)
                    except Exception as e:
                        store.log(f'SAVE FAILED v{store.version + 1}: {e!r}')
                        return self.send_json(500, {'error': 'save failed: ' + str(e)})
                    return self.send_json(200, {'version': store.version, 'savedAt': store.saved_at})
            return self.send_json(404, {'error': 'not found'})

        def send_db_conflict(self):
            body = ('{"conflict": true, "version": %d, "savedAt": %d, "data": %s}' % (store.version, store.saved_at, store.raw)).encode('utf-8')
            self.send_response(409)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def setu_running(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/ping', timeout=1.5) as r:
            return json.loads(r.read().decode('utf-8')).get('setu') is True
    except Exception:
        return False


def port_busy(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def start_server(base_dir, data_dir, port):
    store = SetuStore(data_dir)
    cloud = CloudSync(store)
    store.on_write = cloud.wake.set
    store.log(f'Server start: port {port}, database version {store.version}')
    # Windows lets a second process bind a port with SO_REUSEADDR; two servers would split the data
    http.server.ThreadingHTTPServer.allow_reuse_address = os.name != 'nt'
    httpd = http.server.ThreadingHTTPServer(('0.0.0.0', port), make_handler(base_dir, store, port, cloud))
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    base_dir = get_base_dir()
    port = int(arg('--port', APP_PORT))
    data_dir = arg('--data', default_data_dir())
    os.makedirs(data_dir, exist_ok=True)
    server_only = '--server' in sys.argv

    # The port is fixed on purpose: the browser keeps login/session per address,
    # and a random port used to make all data look "lost".
    already = setu_running(port)
    if not already:
        if port_busy(port):
            msg = (f'Another program is using port {port}, so Setu could not start.\n'
                   f'Close that program and start Setu again.')
            print(msg)
            if not server_only:
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, msg, 'Setu', 0x10)
                except Exception:
                    pass
            sys.exit(1)
        start_server(base_dir, data_dir, port)

    url = f"http://127.0.0.1:{port}/hotel_erp.html"

    if server_only:
        if already:
            print(f'Setu is already running: {url}')
            return
        print('Setu LAN server is running.')
        print(f'  This PC:        {url}')
        for ip in lan_ips():
            print(f'  Phone/Tablet:   http://{ip}:{port}/hotel_erp.html')
        print('Press Ctrl+C to stop.')
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    try:
        open_window(base_dir, data_dir, url)
    except Exception as e:
        # No WebView2 runtime (old Windows 10 / 7) or a broken pywebview: the server is already
        # up, so run Setu in the normal browser instead of closing without a word.
        log_line(data_dir, f'Desktop window failed, opening browser: {e!r}')
        import webbrowser
        webbrowser.open(url)
        msg = ('Setu ki window nahi khul payi, isliye Setu browser mein khula hai.\n\n'
               'Window ke liye Microsoft Edge WebView2 Runtime install karein '
               '(go.microsoft.com/fwlink/p/?LinkId=2124703).\n\n'
               'Billing chalu rakhne ke liye ye message band karein, Setu chalta rahega.')
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, 'Setu', 0x40)
        except Exception:
            print(msg)
        if already:
            return
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return


def log_line(data_dir, msg):
    try:
        with open(os.path.join(data_dir, 'setu-server.log'), 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
    except Exception:
        pass


def open_window(base_dir, data_dir, url):
    import webview  # only needed for the desktop window

    icon_path = os.path.join(base_dir, 'favicon.ico')
    if not os.path.exists(icon_path):
        icon_path = None

    # Create native desktop window
    webview.create_window(
        title='Setu - Restaurant & Hotel POS',
        url=url,
        width=1340,
        height=860,
        min_size=(1020, 680),
        resizable=True,
        text_select=True,
        zoomable=True
    )

    # Drop the window's cached pages so an updated EXE never shows the previous version.
    # Logins and settings (Local Storage) and the database (setu-db.json) are not touched.
    for sub in ('Service Worker', 'Cache', 'Code Cache'):
        shutil.rmtree(os.path.join(data_dir, 'EBWebView', 'Default', sub), ignore_errors=True)

    # Ask for Edge WebView2 by name: without it pywebview drops to old IE (MSHTML), where the
    # page does not work. Asking by name makes it fail here, so main() opens the browser.
    webview.start(
        gui='edgechromium' if os.name == 'nt' else None,
        private_mode=False,
        storage_path=data_dir,
        icon=icon_path
    )

if __name__ == '__main__':
    main()
