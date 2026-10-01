"""End-to-end test of the website in Supabase mode (Playwright + local Supabase stand-in).

Needs: Postgres prepared by reset_db, PostgREST on :3001 and fake_supabase.py on :8780.
    python3 supabase/tests/e2e_remote.py
"""
import asyncio, json, os, re, sys, time
import psycopg
from playwright.async_api import async_playwright

BASE = os.environ.get('BASE', 'http://127.0.0.1:8780/index.html')
DSN = os.environ.get('DSN', 'host=/tmp port=54322 user=postgres dbname=niken')
OUT = os.path.join(os.path.dirname(__file__), 'out'); os.makedirs(OUT, exist_ok=True)
R, ERRS, CTX = [], [], {}


def db(sql, *a):
    with psycopg.connect(DSN, autocommit=True) as c:
        cur = c.execute(sql, a)
        return cur.fetchall() if cur.description else None


class Fail(Exception):
    pass


def check(c, m):
    if not c:
        raise Fail(m)


async def step(pg, tid, name, fn):
    try:
        note = await fn()
        R.append({'id': tid, 'name': name, 'ok': True, 'note': note or ''})
    except Exception as e:
        try:
            await pg.screenshot(path=f'{OUT}/{tid}.png')
        except Exception:
            pass
        R.append({'id': tid, 'name': name, 'ok': False, 'note': f'{type(e).__name__}: {e}'[:400]})
    print(('PASS ' if R[-1]['ok'] else 'FAIL ') + tid + ' ' + name + ' — ' + R[-1]['note'][:180], flush=True)


async def go(pg, r, wait=500):
    await pg.evaluate(f'location.hash={json.dumps(r)}')
    await pg.wait_for_timeout(wait)


async def settle(pg, ms=700):
    await pg.wait_for_function('!document.body.classList.contains("is-busy")', timeout=15000)
    await pg.wait_for_timeout(ms)


async def toast(pg):
    return (await pg.inner_text('#toast')).strip()


async def login(pg, email, pw):
    await go(pg, 'admin')
    if await pg.locator('[data-act=logout]').count():
        await pg.click('.aside [data-act=logout]'); await settle(pg)
    await pg.fill('#l-email', email); await pg.fill('#l-pass', pw)
    await pg.click('#loginform button[type=submit]'); await settle(pg, 900)


async def fill_co(pg):
    await pg.fill('#c-name', 'Sari Pembeli'); await pg.fill('#c-email', 'sari@example.com'); await pg.fill('#c-phone', '+62 812 1111 2222')
    await pg.fill('#c-address', 'Jl. Jenderal Sudirman No. 10, Balikpapan'); await pg.fill('#c-city', 'Balikpapan 76114')
    await pg.check('input[name=pay] >> nth=0')


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1366, 'height': 900})
        pg = await ctx.new_page()

        def onerr(m):
            if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_TUNNEL' not in m.text and 'status of 4' not in m.text:
                ERRS.append(m.text)
        pg.on('console', onerr); pg.on('pageerror', lambda e: ERRS.append('pageerror: ' + str(e)))
        await pg.goto(BASE + '#home'); await pg.wait_for_timeout(2500)

        async def r01():
            check(await pg.evaluate('REMOTE.on'), 'website tidak dalam mode Supabase')
            rib = await pg.inner_text('#ribbon'); check('STAGING' in rib, rib)
            await go(pg, 'shop'); n = await pg.locator('.pcard').count()
            check(n == 21, f'{n} produk')
            t = await pg.inner_text('#view'); check('Scarf' not in t and 'Blazer' not in t, 'draft tampil')
            return f'{n} produk dari database; draft tidak tampil; ribbon STAGING'
        await step(pg, 'R01', 'Katalog dimuat dari database', r01)

        async def r02():
            await go(pg, 'checkout')
            await go(pg, 'p-leather-clutch-bag'); await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            await go(pg, 'p-cotton-ecoprint-tote'); await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            await go(pg, 'checkout'); await pg.click('#coform button[type=submit]'); await settle(pg)
            errs = await pg.locator('#coform .err').count()
            check(errs >= 4, f'{errs} pesan error'); check(db('select count(*) from orders')[0][0] == 0, 'order tercipta')
            return f'{errs} pesan error dari server; tidak ada order'
        await step(pg, 'R02', 'Validasi checkout oleh server', r02)

        async def r03():
            await fill_co(pg)
            await pg.evaluate("document.getElementById('c-total').value='1000'")
            await pg.click('#coform button[type=submit]'); await settle(pg, 1200)
            check('#pay-' in pg.url, pg.url)
            no = pg.url.split('#pay-')[1]; CTX['no'] = no
            o = db('select pay, total, price_tampered from orders where no=%s', no)[0]
            pc = db("select status, held_by from pieces where id='pc-1201'")[0]
            check(o[0] == 'pending' and o[1] == 1250000 + 485000 + 25000 and o[2], o)
            check(pc == ('reserved', no), pc)
            t = await pg.inner_text('#view'); check(re.search(r'1[45]:\d\d', t), 'timer tidak tampil')
            return f'{no}: pending, total Rp{o[1]:,} dari server (browser kirim Rp1.000), piece reserved'
        await step(pg, 'R03', 'Checkout membuat pesanan & reservasi di database', r03)

        async def r04():
            pg2 = await ctx.new_page(); await pg2.goto(BASE + '#p-leather-clutch-bag'); await pg2.wait_for_timeout(2200)
            t = await pg2.inner_text('.buy'); dis = await pg2.locator('.buy [data-act=add]').is_disabled(); await pg2.close()
            check(dis and ('Reserved' in t or 'Sold' in t), t[:200])
            return 'Pengunjung lain melihat piece sebagai Reserved dan tidak bisa membelinya'
        await step(pg, 'R04', 'Barang yang direservasi terkunci untuk pembeli lain', r04)

        async def r05():
            await pg.click('[data-act=pay][data-v=paid]'); await settle(pg)
            o = db('select pay from orders where no=%s', CTX['no'])[0][0]
            pc = db("select status from pieces where id='pc-1201'")[0][0]
            await pg.click('[data-act=pay][data-dup="1"]'); await settle(pg, 300)
            tt = await toast(pg); n = db("select count(*) from payment_events where order_no=%s", CTX['no'])[0][0]
            cart = await pg.evaluate('DB.cart.length')
            check(o == 'paid' and pc == 'sold' and 'Duplicate' in tt and n == 1 and cart == 0, (o, pc, tt, n, cart))
            return 'paid, piece sold, keranjang kosong; callback ulang diabaikan (1 event tersimpan)'
        await step(pg, 'R05', 'Pembayaran & callback duplikat', r05)

        async def r06():
            await go(pg, 'order'); await pg.fill('#os-no', CTX['no'].lower()); await pg.fill('#os-email', 'SARI@example.com')
            await pg.click('#osform button'); await settle(pg); t = await pg.inner_text('#view')
            await pg.fill('#os-email', 'lain@x.com'); await pg.click('#osform button'); await settle(pg); t2 = await pg.inner_text('#view')
            check('paid' in t and 'No order matches' in t2, (t[:120], t2[:120]))
            return 'nomor + email benar → status; email lain → ditolak'
        await step(pg, 'R06', 'Cek status pesanan', r06)

        async def r07():
            await go(pg, 'wholesale')
            await pg.fill('#i-name', 'Kenji Tanaka'); await pg.fill('#i-company', 'Mori Select'); await pg.fill('#i-email', 'kenji@mori.jp')
            await pg.select_option('#i-country', 'Japan'); await pg.select_option('#i-type', 'export'); await pg.fill('#i-sku', 'NE-FSH-VST-001')
            await pg.fill('#i-qty', '60 pcs'); await pg.check('#i-privacy'); await pg.click('#inqform button[type=submit]'); await settle(pg)
            t = await pg.inner_text('#view'); m = re.search(r'INQ-\d{4}-\d{4}', t)
            check(m and db('select count(*) from inquiries where no=%s', m.group(0))[0][0] == 1, t[:200])
            CTX['inq'] = m.group(0)
            await go(pg, 'catalogue'); await pg.fill('#k-name', 'Amy'); await pg.fill('#k-email', 'amy@shop.sg'); await pg.click('#catform button'); await settle(pg)
            check(pg.url.endswith('#inq-done'), 'katalog tidak terkirim')
            return f"{m.group(0)} tersimpan di database; permintaan katalog terkirim"
        await step(pg, 'R07', 'Inquiry & permintaan katalog tersimpan', r07)

        async def r08():
            await login(pg, 'owner@niken.test', 'salah')
            t1 = await pg.inner_text('#loginform')
            await login(pg, 'guest@niken.test', 'Guest#2026')
            t2 = await pg.inner_text('#loginform')
            check('salah' in t1 and 'belum terdaftar' in t2, (t1, t2))
            return 'kata sandi salah ditolak; akun tanpa role admin ditolak'
        await step(pg, 'R08', 'Login admin menolak yang tidak berhak', r08)

        async def r09():
            await login(pg, 'owner@niken.test', 'Owner#2026')
            t = await pg.inner_text('.amain'); a = await pg.inner_text('.aside')
            check('Ringkasan' in t and 'owner@niken.test' in a and CTX['no'] in t, t[:200])
            await pg.reload(); await pg.wait_for_timeout(2500); await go(pg, 'admin')
            check(await pg.locator('.aside').count() == 1, 'sesi hilang setelah reload')
            return 'Owner masuk; dashboard menampilkan pesanan dari database; sesi bertahan setelah reload'
        await step(pg, 'R09', 'Owner login & dashboard', r09)

        async def r10():
            await pg.click('.aside [data-act=tab][data-v=products]'); await pg.wait_for_timeout(300)
            await pg.click('tr[data-v=p7]'); await pg.wait_for_timeout(200)
            await pg.fill('#e-sen', 'Everyday crew-neck tee — staging edit.'); await pg.fill('#e-price', '405000')
            await pg.click('#pform button[type=submit]'); await settle(pg)
            rev = db("select rev->>'price', price from products where id='p7'")[0]
            p3 = await ctx.new_page(); await p3.goto(BASE + '#p-botanical-tee'); await p3.wait_for_timeout(2200)
            before = await p3.inner_text('.buy')
            await pg.click('[data-act=p-publish]'); await settle(pg)
            await p3.reload(); await p3.wait_for_timeout(2200); after = await p3.inner_text('.buy'); await p3.close()
            check(rev == ('405000', 395000) and '395.000' in before and '405.000' in after and 'staging edit' in after, (rev, before[:80], after[:80]))
            return 'perubahan jadi draft (toko tetap Rp395.000) → publish → toko Rp405.000'
        await step(pg, 'R10', 'Edit produk: draft → publish', r10)

        async def r11():
            img = os.path.join(os.path.dirname(__file__), '..', '..', 'img', 'tee.jpg')
            await pg.click('tr[data-v=p7]'); await pg.wait_for_timeout(200)
            await pg.set_input_files('#e-upload', img); await settle(pg, 1200)
            imgs = db("select coalesce(rev->'images', images) from products where id='p7'")[0][0]
            up = [x for x in imgs if x.startswith('http')]
            check(up and '/storage/v1/object/public/media/products/p7/' in up[0], imgs)
            ok = await pg.evaluate(f"fetch({json.dumps(up[0])}).then(r=>r.status)")
            check(ok == 200, f'foto tidak bisa diakses ({ok})')
            return 'foto terunggah ke bucket media & masuk draft produk'
        await step(pg, 'R11', 'Upload foto produk ke Storage', r11)

        async def r12():
            await login(pg, 'content@niken.test', 'Content#2026')
            tabs = await pg.locator('.aside [data-act=tab]').count()
            await pg.click('.aside [data-act=tab][data-v=products]'); await pg.click('tr[data-v=p1]'); await pg.wait_for_timeout(200)
            dis = await pg.locator('#e-price').is_disabled()
            await pg.evaluate("document.getElementById('e-price').disabled=false;document.getElementById('e-price').value='1'")
            await pg.click('#pform button[type=submit]'); await settle(pg, 300)
            tt = await toast(pg); price = db("select coalesce((rev->>'price')::int, price) from products where id='p1'")[0][0]
            check(tabs == 4 and dis and '403' in tt and price == 685000, (tabs, dis, tt, price))
            return 'Content Admin: 4 menu, harga terkunci; memaksa lewat browser ditolak server (403)'
        await step(pg, 'R12', 'Izin role ditegakkan server (Content Admin)', r12)

        async def r13():
            await login(pg, 'fulfil@niken.test', 'Fulfil#2026')
            await pg.click('.aside [data-act=tab][data-v=orders]'); await pg.click(f'tr[data-v="{CTX["no"]}"]'); await pg.wait_for_timeout(200)
            await pg.click('[data-act=o-ful][data-v=processing]'); await settle(pg)
            await pg.click('[data-act=o-ful][data-v=shipped]'); await settle(pg, 300); tt = await toast(pg)
            await pg.fill('#o-track', 'JNE-BPN-77001'); await pg.click('[data-act=o-ful][data-v=shipped]'); await settle(pg)
            o = db('select ful, tracking from orders where no=%s', CTX['no'])[0]
            check('resi' in tt and o == ('shipped', 'JNE-BPN-77001'), (tt, o))
            return 'processing → shipped (resi wajib) tersimpan di database'
        await step(pg, 'R13', 'Fulfillment memproses pesanan', r13)

        async def r14():
            await login(pg, 'sales@niken.test', 'Sales#2026')
            await pg.click('.aside [data-act=tab][data-v=inquiries]'); await pg.click(f'tr[data-v="{CTX["inq"]}"]'); await pg.wait_for_timeout(200)
            await pg.select_option('#i-pic', 'Sales 1'); await pg.click('[data-act=i-save]'); await settle(pg)
            await pg.fill('#q-price', '38'); await pg.fill('#q-valid', '2026-10-31'); await pg.fill('#q-lead', '30 working days'); await pg.fill('#q-terms', '50/50')
            await pg.click('#qform button[type=submit]'); await settle(pg)
            st = db('select status, pic from inquiries where no=%s', CTX['inq'])[0]; q = db('select no, ver, cur, price from quotations where inquiry_no=%s', CTX['inq'])
            check(st == ('In Discussion', 'Sales 1') and len(q) == 1 and float(q[0][3]) == 38, (st, q))
            return f'PIC Sales 1 → quotation {q[0][0]} v1 USD 38'
        await step(pg, 'R14', 'Sales menindaklanjuti inquiry', r14)

        async def r15():
            await login(pg, 'owner@niken.test', 'Owner#2026')
            await pg.click('.aside [data-act=tab][data-v=settings]'); await pg.select_option('#s-paysim', '0'); await pg.click('#sform button[type=submit]'); await settle(pg)
            p4 = await ctx.new_page(); await p4.goto(BASE + '#p-botanical-tee'); await p4.wait_for_timeout(2200)
            await p4.click('.opt button:has-text("M")'); await p4.click('.buy [data-act=add]'); await go(p4, 'checkout'); await fill_co(p4)
            await p4.click('#coform button[type=submit]'); await settle(p4, 1200)
            sim = await p4.locator('[data-act=pay]').count(); rib = await p4.locator('#ribbon').is_visible()
            no = p4.url.split('#pay-')[1]; CTX['no2'] = no
            forced = await p4.evaluate(f"rpc('payment_callback',{{p_no:{json.dumps(no)},p_type:'paid',p_event:'x1'}}).then(()=>'ok',e=>e.message)")
            await p4.close()
            await pg.select_option('#s-paysim', '1'); await pg.click('#sform button[type=submit]'); await settle(pg)
            check(sim == 0 and not rib and 'payment provider' in forced, (sim, rib, forced))
            return 'Simulator dimatikan: tombol hilang, ribbon hilang, panggilan paksa dari browser ditolak'
        await step(pg, 'R15', 'Owner mematikan simulator pembayaran', r15)

        async def r16():
            p5 = await ctx.new_page(); await p5.goto(BASE + '#order'); await p5.wait_for_timeout(2200)
            await p5.fill('#os-no', CTX['no2']); await p5.fill('#os-email', 'sari@example.com'); await p5.click('#osform button'); await settle(p5)
            await go(p5, 'pay-' + CTX['no2'], 800)
            db("update orders set expires_at = now() - interval '1 second' where no=%s", CTX['no2'])
            await p5.wait_for_timeout(7000); t = await p5.inner_text('#view'); await p5.close()
            st = db('select pay from orders where no=%s', CTX['no2'])[0][0]
            rv = db("select reserved from variants where id='p7-m'")[0][0]
            check(st == 'expired' and rv == 0 and 'released' in t.lower(), (st, rv, t[:200]))
            return 'reservasi habis → halaman bayar memperbarui sendiri; stok dilepas'
        await step(pg, 'R16', 'Reservasi kedaluwarsa terdeteksi otomatis', r16)

        async def r17():
            await go(pg, 'admin'); await pg.click('.aside [data-act=logout]'); await settle(pg)
            login_form = await pg.locator('#loginform').count()
            left = await pg.evaluate('DB.inquiries.length+DB.audit.length')
            check(login_form == 1 and left == 0, (login_form, left))
            return 'keluar → form login; data admin dibersihkan dari browser'
        await step(pg, 'R17', 'Logout admin', r17)

        async def r18():
            m = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            mp = await m.new_page(); over = []
            for r in ['home', 'shop', 'p-ecoprint-utility-vest', 'checkout', 'wholesale', 'admin']:
                await mp.goto(BASE + '#' + r); await mp.wait_for_timeout(1500)
                w = await mp.evaluate('document.documentElement.scrollWidth')
                if w > 391: over.append(f'{r}:{w}')
            await m.close(); check(not over, over)
            return '6 layar tanpa scroll horizontal di 390 px'
        await step(pg, 'R18', 'Mobile', r18)

        async def r19():
            check(not ERRS, ERRS[:5]); return 'tanpa error JavaScript'
        await step(pg, 'R19', 'Tanpa error JavaScript', r19)
        await b.close()
    json.dump(R, open(os.path.join(os.path.dirname(__file__), 'e2e_results.json'), 'w'), indent=1, ensure_ascii=False)
    print(f"\n== {sum(r['ok'] for r in R)}/{len(R)} PASS ==")

asyncio.run(main())
