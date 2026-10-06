"""Database acceptance tests for the Niken Ecoprint Supabase schema.

Runs against a plain local Postgres prepared with supabase/tests/local_stub.sql,
the migrations and seed.sql. Each test plays a real caller: an anonymous visitor
(role anon), a signed-in admin (role authenticated + JWT sub) or the payment
provider (service_role).

    DSN="host=/tmp port=54322 user=postgres dbname=niken" python3 supabase/tests/db_test.py
"""
import json, os, sys, threading, time, uuid
import psycopg

DSN = os.environ.get('DSN', 'host=/tmp port=54322 user=postgres dbname=niken')
R = []
USERS = {}


def conn():
    return psycopg.connect(DSN, autocommit=True)


def as_role(c, role, uid=None):
    claims = {'role': role}
    if uid:
        claims['sub'] = str(uid)
    c.execute("select set_config('request.jwt.claims', %s, false)", (json.dumps(claims),))
    c.execute(f'set role {role}')


def rpc(c, fn, *args):
    ph = ','.join(['%s'] * len(args))
    conv = [json.dumps(a) if isinstance(a, (dict, list)) else a for a in args]
    row = c.execute(f'select public.{fn}({ph})', conv).fetchone()
    return row[0] if row else None


def denied(c, sql, args=()):
    try:
        c.execute(sql, args)
        return False
    except psycopg.errors.InsufficientPrivilege:
        return True
    except psycopg.Error as e:
        return '403' in str(e) or '401' in str(e) or 'permission denied' in str(e)


def test(name):
    def deco(fn):
        try:
            note = fn()
            R.append((True, name, note or ''))
        except Exception as e:  # noqa
            R.append((False, name, f'{type(e).__name__}: {e}'[:300]))
        print(('PASS ' if R[-1][0] else 'FAIL ') + name + ' — ' + R[-1][2], flush=True)
        return fn
    return deco


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


CUST = {'name': 'Sari Pembeli', 'email': 'sari@example.com', 'phone': '+62 812 1111 2222', 'address': 'Jl. Sudirman No. 10, Balikpapan'}


def order(c, lines, zone='kal', **kw):
    p = {'lines': lines, 'customer': CUST, 'country': 'ID', 'zone': zone, 'pay': 'QRIS (simulasi)'}
    p.update(kw)
    return rpc(c, 'create_order', p)


def setup():
    c = conn()
    for role in ['owner', 'content', 'sales', 'fulfillment', 'none']:
        uid = uuid.uuid4()
        c.execute('insert into auth.users(id,email) values (%s,%s)', (uid, f'{role}@niken.test'))
        if role != 'none':
            c.execute('insert into public.admin_users(user_id,role,name) values (%s,%s,%s)', (uid, role, role.title()))
        USERS[role] = uid
    c.close()


def admin(role):
    c = conn()
    as_role(c, 'authenticated', USERS[role])
    return c


def anon():
    c = conn()
    as_role(c, 'anon')
    return c


def run():
    setup()

    @test('T01 Pengunjung anonim tidak bisa membaca tabel apa pun secara langsung')
    def _():
        c = anon()
        blocked = [t for t in ['products', 'product_fob', 'orders', 'order_items', 'inquiries', 'admin_users', 'site_settings', 'audit_logs']
                   if denied(c, f'select * from public.{t} limit 1')]
        check(len(blocked) == 8, f'hanya {blocked} yang tertutup')
        check(denied(c, "update public.products set price=1"), 'anon bisa update')
        return '8 tabel tertutup untuk select & update'

    @test('T02 Pengunjung anonim tidak bisa memanggil fungsi admin atau helper')
    def _():
        c = anon()
        fns = ["select public.admin_snapshot()", "select public.admin_set_product_status('p1','archived')",
               "select public._release('x')", "select public._finalize('x')", "select public._expire_reservations()"]
        check(all(denied(c, f) for f in fns), 'ada fungsi yang bisa dipanggil')
        return f'{len(fns)} fungsi ditolak'

    @test('T03 Katalog publik: tanpa draft, FOB resmi tampil, tanpa revisi draft')
    def _():
        c = anon()
        s = rpc(c, 'get_public_site')
        skus = [p['sku'] for p in s['products']]
        check('NE-ACC-SCF-001' not in skus and 'NE-FSH-BLZ-001' not in skus, 'draft bocor')
        check(all(p['rev'] is None for p in s['products']), 'revisi draft bocor')
        check(any(p['fob'] for p in s['products']) and all(p['price'] is None for p in s['products'] if p['fob'] and p['sale'] == 'quote'), 'FOB resmi tidak tampil / terbaca sebagai harga')
        check(s['contact']['phones'] == [] and s['contact']['address'] is None, 'kontak belum dikonfirmasi bocor')
        check('notifyOk' not in s['settings'], 'pengaturan internal bocor')
        return f'{len(skus)} produk publik; FOB resmi tampil; draft, kontak & pengaturan internal tersembunyi'

    @test('T04 Validasi checkout di server')
    def _():
        c = anon()
        r = rpc(c, 'create_order', {'lines': [], 'customer': {}, 'country': 'JP', 'zone': 'pap', 'pay': ''})
        check(not r['ok'] and set(r['errs']) >= {'name', 'email', 'phone', 'address', 'country', 'zone', 'pay'}, r)
        r = order(c, [{'pid': 'p14', 'ref': 'p14-onesize', 'qty': 1}], zone='pap')
        check(not r['ok'] and 'zone' in r['errs'], 'Papua diterima')
        return '7 field ditolak; wilayah tanpa layanan ditolak'

    @test('T05 Total dihitung server; harga dari browser diabaikan')
    def _():
        c = anon()
        r = order(c, [{'pid': 'p14', 'ref': 'p14-onesize', 'qty': 2, 'price': 1}], clientTotal=1000)
        o = r['order']
        check(r['ok'] and o['total'] == 485000 * 2 + 25000 and o['priceTampered'], o)
        rpc(c, 'payment_callback', o['no'], 'expired', 'evt-t05')
        return f"{o['no']}: total Rp{o['total']:,} (browser kirim Rp1.000)"

    @test('T06 Exact piece: dua checkout paralel, hanya satu yang berhasil')
    def _():
        res = []
        a = conn(); as_role(a, 'anon')
        a.autocommit = False
        r1 = order(a, [{'pid': 'p12', 'ref': 'pc-1201', 'qty': 1}])   # holds the row lock, not committed yet

        def second():
            b = anon()
            res.append(order(b, [{'pid': 'p12', 'ref': 'pc-1201', 'qty': 1}]))
        t = threading.Thread(target=second); t.start()
        time.sleep(1.0)
        check(not res, 'checkout kedua tidak menunggu kunci baris')
        a.commit(); t.join(5)
        check(r1['ok'] and res and not res[0]['ok'], f'{r1.get("ok")} / {res}')
        TEST['t06'] = r1['order']['no']
        return 'Checkout kedua menunggu kunci baris lalu ditolak'

    @test('T07 Unit terakhir varian: dua checkout paralel, hanya satu yang berhasil')
    def _():
        c = conn()
        c.execute("update public.variants set stock=1, reserved=0 where id='p8-s'")
        out = []

        def buy():
            b = anon(); out.append(order(b, [{'pid': 'p8', 'ref': 'p8-s', 'qty': 1}]))
        ts = [threading.Thread(target=buy) for _ in range(4)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        oks = [o for o in out if o['ok']]
        v = c.execute("select stock, reserved from public.variants where id='p8-s'").fetchone()
        check(len(oks) == 1 and v == (1, 1), f'{len(oks)} berhasil, stok {v}')
        TEST['t07'] = oks[0]['order']['no']
        return '4 pembeli serentak, 1 berhasil; stok 1 / reservasi 1'

    @test('T08 Pembayaran sukses, callback duplikat diabaikan')
    def _():
        c = anon(); no = TEST['t06']
        r1 = rpc(c, 'payment_callback', no, 'paid', 'evt-a')
        r2 = rpc(c, 'payment_callback', no, 'paid', 'evt-a')
        r3 = rpc(c, 'payment_callback', no, 'paid', 'evt-b')
        st = conn().execute("select status from public.pieces where id='pc-1201'").fetchone()[0]
        check(r1['order']['pay'] == 'paid' and r2.get('dup') and r3.get('dup') and st == 'sold', (r1, r2, r3, st))
        return 'paid → piece sold; event sama & event baru untuk order paid diabaikan'

    @test('T09 Pembayaran gagal & reservasi kedaluwarsa melepas stok')
    def _():
        c = anon(); db = conn()
        rpc(c, 'payment_callback', TEST['t07'], 'failed', 'evt-c')
        v1 = db.execute("select reserved from public.variants where id='p8-s'").fetchone()[0]
        r = order(c, [{'pid': 'p7', 'ref': 'p7-m', 'qty': 1}])
        before = db.execute("select reserved from public.variants where id='p7-m'").fetchone()[0]
        db.execute("update public.orders set expires_at = now() - interval '1 minute' where no=%s", (r['order']['no'],))
        st = rpc(c, 'get_order', r['order']['no'], 'SARI@example.com')
        after = db.execute("select reserved from public.variants where id='p7-m'").fetchone()[0]
        check(v1 == 0 and before == 1 and after == 0 and st['pay'] == 'expired', (v1, before, after, st['pay']))
        TEST['t09'] = r['order']['no']
        return 'failed → reservasi 0; expired otomatis saat dicek → reservasi 1 → 0'

    @test('T10 Pembayaran terlambat untuk barang yang sudah terjual masuk rekonsiliasi')
    def _():
        c = anon()
        r1 = order(c, [{'pid': 'p16', 'ref': 'pc-1601', 'qty': 1}])
        rpc(c, 'payment_callback', r1['order']['no'], 'expired', 'evt-d')
        r2 = order(c, [{'pid': 'p16', 'ref': 'pc-1601', 'qty': 1}])
        rpc(c, 'payment_callback', r2['order']['no'], 'paid', 'evt-e')
        late = rpc(c, 'payment_callback', r1['order']['no'], 'paid', 'evt-f')
        check(late['order']['recon'] and late['order']['pay'] == 'paid', late)
        TEST['recon'] = r1['order']['no']
        return f"{r1['order']['no']} ditandai rekonsiliasi; piece tidak dijual dua kali"

    @test('T11 Simulator mati: callback hanya diterima dari penyedia (service_role)')
    def _():
        db = conn(); db.execute("update public.site_settings set value = value || '{\"paySimulator\":false}' where key='private'")
        c = anon(); r = order(c, [{'pid': 'p14', 'ref': 'p14-onesize', 'qty': 1}])
        blocked = denied(c, "select public.payment_callback(%s,'paid','evt-g')", (r['order']['no'],))
        s = conn(); as_role(s, 'service_role')
        ok = rpc(s, 'payment_callback', r['order']['no'], 'paid', 'evt-h')
        db.execute("update public.site_settings set value = value || '{\"paySimulator\":true}' where key='private'")
        check(blocked and ok['order']['pay'] == 'paid', (blocked, ok))
        return 'anon ditolak; webhook penyedia (service_role) diterima'

    @test('T12 Status pesanan hanya dengan nomor + email yang benar')
    def _():
        c = anon()
        ok = rpc(c, 'get_order', TEST['t06'].lower(), 'Sari@Example.com')
        bad = rpc(c, 'get_order', TEST['t06'], 'orang@lain.com')
        check(ok and ok['no'] == TEST['t06'] and bad is None and ok['notes'] == '', (ok, bad))
        return 'email lain → null; catatan internal tidak ikut'

    @test('T13 Admin: izin role ditegakkan di server')
    def _():
        p1 = conn().execute("select row_to_json(p) from public.products p where id='p1'").fetchone()[0]
        rev = {k: p1[k] for k in ['sku', 'cat', 'name', 'story', 'material', 'size', 'mode', 'sale', 'price', 'lead', 'images']}
        c = admin('content')
        check(denied(c, 'select public.admin_save_product(%s,%s,%s)', ('p1', json.dumps({**rev, 'price': 1}), '[]')), 'content ubah harga')
        rpc(c, 'admin_save_product', 'p1', {**rev, 'story': {'en': 'Edited story', 'id': 'Cerita'}}, [])
        f = admin('fulfillment'); s = admin('sales'); n = admin('none')
        checks = [denied(f, 'select public.admin_save_product(%s,%s,%s)', ('p1', json.dumps(rev), '[]')),
                  denied(s, "select public.admin_save_settings('{}')"),
                  denied(n, 'select public.admin_snapshot()'),
                  denied(c, "select public.admin_save_contact(0,true,'{}')"),
                  denied(s, "select public.admin_order_refund('x')")]
        check(all(checks), checks)
        return 'content ubah harga, fulfillment edit produk, sales ubah pengaturan/refund, user non-admin: semua 403/401'

    @test('T14 Snapshot admin berisi data sesuai role')
    def _():
        snap = {r: rpc(admin(r), 'admin_snapshot') for r in ['owner', 'content', 'sales', 'fulfillment']}
        fob = lambda s: any(p['fob'] for p in s['products'])
        check(snap['owner']['orders'] and fob(snap['owner']) and snap['owner']['audit'], 'owner kurang data')
        check(not snap['content']['orders'] and not snap['content']['inquiries'], 'content melihat PII')
        check(snap['sales']['orders'] and fob(snap['sales']) and not snap['sales']['audit'], 'sales salah')
        check(snap['fulfillment']['orders'] and not snap['fulfillment']['inquiries'], 'fulfillment salah')
        return 'Owner semua; Content tanpa data pembeli; Sales tanpa audit; Fulfillment hanya pesanan'

    @test('T15 Draft → publish: toko tetap sampai dipublikasikan')
    def _():
        pub = rpc(anon(), 'get_public_site')
        p = next(x for x in pub['products'] if x['id'] == 'p1')
        check(p['story']['en'] != 'Edited story', 'draft sudah tampil di publik')
        rpc(admin('owner'), 'admin_publish_product', 'p1')
        p = next(x for x in rpc(anon(), 'get_public_site')['products'] if x['id'] == 'p1')
        check(p['story']['en'] == 'Edited story', 'publish tidak diterapkan')
        return 'revisi tersimpan sebagai draft, tampil setelah publish'

    @test('T16 Snapshot pesanan tidak berubah saat produk diedit; hapus produk bertransaksi ditolak')
    def _():
        db = conn(); o = admin('owner')
        db.execute("update public.products set name = '{\"en\":\"Renamed\",\"id\":\"Renamed\"}', price=1 where id='p12'")
        it = db.execute("select name, unit from public.order_items where product_id='p12' limit 1").fetchone()
        rpc(o, 'admin_set_product_status', 'p12', 'draft')
        check(it[0] != 'Renamed' and it[1] == 1250000, it)
        try:
            rpc(o, 'admin_delete_product', 'p12'); raise AssertionError('produk bertransaksi terhapus')
        except psycopg.Error as e:
            check('Hanya draft tanpa transaksi' in str(e), str(e))
        return f'snapshot tetap "{it[0]}" Rp{it[1]:,}; hapus ditolak'

    @test('T17 Stok tidak boleh di bawah reservasi; mutasi tercatat')
    def _():
        c = anon(); r = order(c, [{'pid': 'p6', 'ref': 'p6-m', 'qty': 2}])
        p6 = conn().execute("select row_to_json(p) from public.products p where id='p6'").fetchone()[0]
        rev = {k: p6[k] for k in ['sku', 'cat', 'name', 'story', 'material', 'size', 'mode', 'sale', 'price', 'lead', 'images']}
        o = admin('owner')
        try:
            rpc(o, 'admin_save_product', 'p6', rev, [{'id': 'p6-m', 'stock': 1}]); raise AssertionError('diterima')
        except psycopg.Error as e:
            check('di bawah' in str(e), str(e))
        rpc(o, 'admin_save_product', 'p6', rev, [{'id': 'p6-m', 'stock': 9}])
        mv = conn().execute("select count(*) from public.inventory_movements where reason='adjust' and sku='NE-FSH-MSH-001'").fetchone()[0]
        rpc(o, 'admin_order_cancel', r['order']['no'])
        res = conn().execute("select reserved from public.variants where id='p6-m'").fetchone()[0]
        check(mv == 1 and res == 0, (mv, res))
        return 'stok < reservasi ditolak; penyesuaian tercatat; pembatalan melepas reservasi'

    @test('T18 Alur pemenuhan pesanan ditegakkan server')
    def _():
        f = admin('fulfillment'); no = TEST['t06']
        rpc(f, 'admin_order_fulfill', no, 'processing', '')
        try:
            rpc(f, 'admin_order_fulfill', no, 'shipped', ''); raise AssertionError('kirim tanpa resi')
        except psycopg.Error as e:
            check('resi' in str(e), str(e))
        try:
            rpc(f, 'admin_order_fulfill', TEST['t09'], 'processing', ''); raise AssertionError('proses order belum bayar')
        except psycopg.Error as e:
            check('dibayar' in str(e), str(e))
        rpc(f, 'admin_order_fulfill', no, 'shipped', 'JNE-BPN-1'); rpc(f, 'admin_order_fulfill', no, 'delivered', '')
        rpc(f, 'admin_order_fulfill', no, 'returned', ''); rpc(f, 'admin_order_restock', no)
        st = conn().execute("select status from public.pieces where id='pc-1201'").fetchone()[0]
        check(st == 'available', st)
        return 'tanpa resi & belum bayar ditolak; retur → restok mengembalikan piece'

    @test('T19 Inquiry tersimpan dengan nomor; notifikasi gagal tetap tersimpan; batas spam')
    def _():
        c = anon(); db = conn()
        bad = rpc(c, 'submit_inquiry', {'type': 'export', 'name': '', 'email': 'x'})
        db.execute("update public.site_settings set value = value || '{\"notifyOk\":false}' where key='private'")
        r = rpc(c, 'submit_inquiry', {'type': 'export', 'name': 'Kenji', 'email': 'kenji@mori.jp', 'country': 'Japan', 'privacy': True, 'sku': 'NE-FSH-VST-001'})
        n = db.execute('select notify from public.inquiries where no=%s', (r['inq']['no'],)).fetchone()[0]
        db.execute("update public.site_settings set value = value || '{\"notifyOk\":true}' where key='private'")
        rpc(admin('sales'), 'admin_inquiry_retry', r['inq']['no'])
        n2 = db.execute('select notify from public.inquiries where no=%s', (r['inq']['no'],)).fetchone()[0]
        for i in range(6):
            last = rpc(c, 'submit_inquiry', {'type': 'catalogue', 'name': 'Spam', 'email': 'spam@x.com'})
        check(not bad['ok'] and set(bad['errs']) == {'name', 'email', 'country', 'privacy'}, bad)
        check(n == 'failed' and n2 == 'sent' and not last['ok'], (n, n2, last))
        TEST['inq'] = r['inq']['no']
        return f"{r['inq']['no']}: notifikasi failed → kirim ulang sent; permintaan ke-6 dalam 10 menit ditolak"

    @test('T20 Quotation berversi; harga retail tidak berubah')
    def _():
        s = admin('sales'); inq = TEST['inq']
        rpc(s, 'admin_inquiry_update', inq, 'New', 'Sales 1')
        q = {'qty': '60 pcs', 'cur': 'USD', 'price': 38, 'basis': 'FOB', 'port': 'Balikpapan', 'valid': '2026-10-31', 'lead': '30 hari kerja', 'terms': '50/50'}
        a = rpc(s, 'admin_quote_create', inq, q); b = rpc(s, 'admin_quote_create', inq, {**q, 'price': 36})
        rpc(s, 'admin_quote_set_status', b['no'], 2, 'Sent'); rpc(s, 'admin_quote_set_status', b['no'], 2, 'Approved')
        st = conn().execute('select status from public.inquiries where no=%s', (inq,)).fetchone()[0]
        price = conn().execute("select price from public.products where id='p1'").fetchone()[0]
        check(a['no'] == b['no'] and b['ver'] == 2 and st == 'Approved' and price == 685000, (a, b, st, price))
        return f"{a['no']} v1 → v2 → Sent → Approved; harga retail tetap"

    @test('T21 Audit log mencatat siapa, kapan, aksi')
    def _():
        n = conn().execute("select count(*), count(distinct role) from public.audit_logs").fetchone()
        check(n[0] >= 10 and n[1] >= 3, n)
        return f'{n[0]} entri dari {n[1]} role'

    ok = sum(1 for r in R if r[0])
    print(f'\n== {ok}/{len(R)} PASS ==')
    json.dump([{'ok': r[0], 'name': r[1], 'note': r[2]} for r in R], open(os.path.join(os.path.dirname(__file__), 'db_results.json'), 'w'), indent=1, ensure_ascii=False)
    return ok == len(R)


TEST = {}
if __name__ == '__main__':
    sys.exit(0 if run() else 1)
