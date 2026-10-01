"""Local stand-in for Supabase, for end-to-end testing only.

Serves the website and the three Supabase endpoints the site uses:
  /rest/v1/*     → PostgREST (real, talking to the local Postgres)
  /auth/v1/*     → minimal password login issuing HS256 JWTs (role authenticated)
  /storage/v1/*  → file upload/download for the 'media' bucket (staff only)
Run:  python3 supabase/tests/fake_supabase.py  (expects PostgREST on :3001)
"""
import base64, hashlib, hmac, http.server, json, os, sys, threading, time, urllib.request, urllib.error, uuid
import psycopg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PORT = int(os.environ.get('PORT', '8780'))
PGRST = os.environ.get('PGRST', 'http://127.0.0.1:3001')
DSN = os.environ.get('DSN', 'host=/tmp port=54322 user=postgres dbname=niken')
SECRET = os.environ.get('JWT_SECRET', 'local-test-secret-local-test-secret-0123456789')
MEDIA = os.path.join(os.path.dirname(__file__), 'out', 'media')
os.makedirs(MEDIA, exist_ok=True)


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def jwt(claims):
    h = b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    p = b64(json.dumps(claims).encode())
    sig = b64(hmac.new(SECRET.encode(), f'{h}.{p}'.encode(), hashlib.sha256).digest())
    return f'{h}.{p}.{sig}'


def unjwt(tok):
    try:
        h, p, s = tok.split('.')
        if not hmac.compare_digest(s, b64(hmac.new(SECRET.encode(), f'{h}.{p}'.encode(), hashlib.sha256).digest())):
            return None
        c = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))
        return c if c.get('exp', 1e12) > time.time() else None
    except Exception:
        return None


ANON_KEY = jwt({'role': 'anon', 'iss': 'local', 'exp': int(time.time()) + 10 * 365 * 86400})


def session_for(uid, email):
    now = int(time.time())
    tok = jwt({'sub': str(uid), 'role': 'authenticated', 'aud': 'authenticated', 'email': email, 'exp': now + 3600})
    user = {'id': str(uid), 'aud': 'authenticated', 'role': 'authenticated', 'email': email, 'app_metadata': {'provider': 'email'},
            'user_metadata': {}, 'created_at': '2026-10-01T00:00:00Z', 'updated_at': '2026-10-01T00:00:00Z'}
    return {'access_token': tok, 'token_type': 'bearer', 'expires_in': 3600, 'expires_at': now + 3600,
            'refresh_token': f'r.{uid}.{uuid.uuid4().hex}', 'user': user}


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n) if n else b''

    def claims(self):
        a = self.headers.get('Authorization', '')
        return unjwt(a[7:]) if a.startswith('Bearer ') else None

    # ---------- routing ----------
    def do_GET(self):
        if self.path.startswith('/config.js'):
            body = f'window.NIKEN_CONFIG={{supabaseUrl:"http://127.0.0.1:{PORT}",supabaseAnonKey:"{ANON_KEY}"}};'.encode()
            self.send_response(200); self.send_header('Content-Type', 'application/javascript'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith('/rest/v1/'):
            return self.proxy('GET')
        if self.path.startswith('/auth/v1/user'):
            c = self.claims()
            return self.send_json(200, session_for(c['sub'], c.get('email'))['user']) if c and c.get('sub') else self.send_json(401, {'msg': 'invalid token'})
        if self.path.startswith('/storage/v1/object/public/media/'):
            f = os.path.join(MEDIA, self.path.split('/storage/v1/object/public/media/', 1)[1].split('?')[0])
            if not os.path.isfile(f):
                return self.send_json(404, {'error': 'not found'})
            data = open(f, 'rb').read()
            self.send_response(200); self.send_header('Content-Type', 'image/jpeg'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data); return
        return super().do_GET()

    def do_HEAD(self):
        return super().do_HEAD()

    def do_POST(self):
        if self.path.startswith('/rest/v1/'):
            return self.proxy('POST')
        if self.path.startswith('/auth/v1/token'):
            b = json.loads(self.body() or b'{}')
            if 'grant_type=password' in self.path:
                with psycopg.connect(DSN, autocommit=True) as c:
                    row = c.execute("select id, email from auth.users where email=lower(%s) and encrypted_password = crypt(%s, encrypted_password)",
                                    (b.get('email', ''), b.get('password', ''))).fetchone()
                if not row:
                    return self.send_json(400, {'error': 'invalid_grant', 'error_description': 'Invalid login credentials', 'msg': 'Invalid login credentials'})
                return self.send_json(200, session_for(row[0], row[1]))
            if 'grant_type=refresh_token' in self.path:
                parts = (b.get('refresh_token') or '').split('.')
                if len(parts) == 3:
                    with psycopg.connect(DSN, autocommit=True) as c:
                        row = c.execute('select id, email from auth.users where id=%s', (parts[1],)).fetchone()
                    if row:
                        return self.send_json(200, session_for(row[0], row[1]))
                return self.send_json(400, {'error': 'invalid_grant'})
        if self.path.startswith('/auth/v1/logout'):
            self.send_response(204); self.end_headers(); return
        if self.path.startswith('/storage/v1/object/media/'):
            c = self.claims()
            data = self.body()
            if not c or c.get('role') != 'authenticated':
                return self.send_json(403, {'statusCode': '403', 'error': 'Unauthorized', 'message': 'new row violates row-level security policy'})
            with psycopg.connect(DSN, autocommit=True) as db:
                ok = db.execute("select role in ('owner','content') from public.admin_users where user_id=%s", (c['sub'],)).fetchone()
            if not ok or not ok[0]:
                return self.send_json(403, {'statusCode': '403', 'error': 'Unauthorized', 'message': 'new row violates row-level security policy'})
            rel = self.path.split('/storage/v1/object/media/', 1)[1].split('?')[0]
            f = os.path.join(MEDIA, rel)
            os.makedirs(os.path.dirname(f), exist_ok=True)
            open(f, 'wb').write(data)
            return self.send_json(200, {'Key': 'media/' + rel, 'Id': str(uuid.uuid4())})
        return self.send_json(404, {'error': 'not found'})

    def do_PATCH(self):
        return self.proxy('PATCH') if self.path.startswith('/rest/v1/') else self.send_json(404, {})

    def proxy(self, method):
        url = PGRST + self.path[len('/rest/v1'):]
        data = self.body() if method != 'GET' else None
        hdr = {k: v for k, v in self.headers.items() if k.lower() in ('authorization', 'content-type', 'prefer', 'accept', 'content-profile', 'accept-profile')}
        req = urllib.request.Request(url, data=data, method=method, headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code, body, ctype = r.status, r.read(), r.headers.get('Content-Type', 'application/json')
        except urllib.error.HTTPError as e:
            code, body, ctype = e.code, e.read(), e.headers.get('Content-Type', 'application/json')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    print('ANON_KEY', ANON_KEY, flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
