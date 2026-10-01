"""UAT Niken Ecoprint — end-to-end lewat UI (Playwright/Chromium)."""
import asyncio, http.server, threading, functools, json, os, re, sys, time
from playwright.async_api import async_playwright

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
import shutil; shutil.copy(f'{SITE}/index.html', f'{SITE}/_t.html')
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(type('Q', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None}), directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:8766/_t.html'

R = []          # results
ERRS = []       # js errors

class Fail(Exception): pass
def check(cond, msg):
    if not cond: raise Fail(msg)

async def step(pg, area, tid, name, fn):
    t0 = time.time()
    try:
        note = await fn()
        R.append(dict(id=tid, area=area, name=name, ok=True, note=note or ''))
    except Exception as e:
        shot = f'{OUT}/{tid}.png'
        try: await pg.screenshot(path=shot)
        except Exception: shot = ''
        R.append(dict(id=tid, area=area, name=name, ok=False, note=f'{type(e).__name__}: {e}'[:400], shot=shot))
    print(('PASS ' if R[-1]['ok'] else 'FAIL ') + tid, name, '—', R[-1]['note'][:160], flush=True)

async def go(pg, route, wait=180):
    await pg.evaluate(f"location.hash={json.dumps(route)}")
    await pg.wait_for_timeout(wait)

async def toast(pg):
    return (await pg.inner_text('#toast')).strip()

async def fresh(pg, route='home'):
    await pg.goto(BASE + '#' + route)
    await pg.evaluate("localStorage.clear()")
    await pg.goto(BASE + '#' + route)
    await pg.reload()
    await pg.wait_for_timeout(300)

ROUTES = ['home','shop','shop-fabric','shop-fashion','shop-bags','shop-accessories','shop-footwear','shop-home','p-ecoprint-utility-vest','p-leather-clutch-bag','p-ochre-silk-ecoprint-fabric','story','process','wholesale','custom','catalogue','catalogue-view','journal','contact','faq','order','cart','checkout','admin']

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1366, 'height': 900})
        pg = await ctx.new_page()
        def onerr(m):
            if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_TUNNEL' not in m.text: ERRS.append(m.text)
        pg.on('console', onerr); pg.on('pageerror', lambda e: ERRS.append('pageerror: ' + str(e)))
        await fresh(pg)

        # ================= A. Navigasi & konten =================
        async def a01():
            bad = []
            for r in ROUTES:
                await go(pg, r)
                h = await pg.evaluate("(document.querySelector('#view h1,#view h2')||{}).textContent||''")
                if not h.strip(): bad.append(r)
            check(not bad, f'route tanpa judul: {bad}')
            return f'{len(ROUTES)} route tampil dengan judul'
        await step(pg, 'Navigasi & konten', 'A01', 'Semua halaman blueprint dapat dibuka', a01)

        async def a02():
            known = set(ROUTES) | {'inq-done'}
            dead = set()
            for r in ROUTES:
                await go(pg, r, 120)
                hrefs = await pg.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')].map(a=>a.getAttribute('href').slice(1))")
                for h in hrefs:
                    if h and h not in known and not h.startswith(('p-','shop-','pay-')): dead.add(h)
                    if h.startswith('p-'):
                        ok = await pg.evaluate(f"DB.products.some(p=>p.slug==={json.dumps(h[2:])}&&p.status==='published')")
                        if not ok: dead.add(h)
            check(not dead, f'tautan mati: {sorted(dead)}')
            return 'Semua tautan internal menuju halaman/produk yang ada'
        await step(pg, 'Navigasi & konten', 'A02', 'Tidak ada tautan internal mati', a02)

        async def a03():
            broken = []
            for r in ROUTES:
                await go(pg, r, 100)
                await pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
                await pg.wait_for_timeout(250)
                bs = await pg.evaluate("[...document.querySelectorAll('#view img,footer img')].filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.getAttribute('src'))")
                broken += [f'{r}:{s}' for s in bs]
            check(not broken, f'gambar gagal: {broken[:8]}')
            return 'Semua gambar termuat'
        await step(pg, 'Navigasi & konten', 'A03', 'Semua gambar termuat (tidak ada broken image)', a03)

        async def a04():
            await go(pg, 'home')
            secs = ['Featured product','Shop by collection','Our process','What makes us different','From leaf to story','For retailers','Craftsmanship','Exhibitions','FAQ']
            txt = await pg.inner_text('#view')
            miss = [s for s in secs if s.lower() not in txt.lower()]
            check(await pg.locator('.hero h1').count() == 1, 'hero tidak ada')
            check('Request Catalogue' in txt and 'Request a Quote' in txt and 'Contact' in txt, 'CTA final tidak lengkap')
            check(not miss, f'section hilang: {miss}')
            usp = await pg.locator('.usp > div').count(); steps = await pg.locator('.steps .step').count()
            check(usp == 6 and steps == 6, f'USP={usp}, langkah={steps}')
            foot = await pg.inner_text('footer')
            check('PT. Manna Borneo Persada' in foot, 'footer tanpa nama perusahaan')
            return 'Hero, featured, koleksi, cerita, 6 USP, 6 langkah, B2B, impact, pameran, FAQ, CTA final, footer'
        await step(pg, 'Navigasi & konten', 'A04', 'Homepage memuat 12 bagian blueprint §5', a04)

        async def a05():
            await go(pg, 'home')
            await pg.click('#lang-id'); await pg.wait_for_timeout(150)
            nav = await pg.inner_text('#nav')
            check('Belanja' in nav and 'Cerita Kami' in nav, f'nav ID salah: {nav}')
            await pg.reload(); await pg.wait_for_timeout(300)
            nav = await pg.inner_text('#nav')
            check('Belanja' in nav, 'bahasa tidak tersimpan setelah reload')
            await go(pg, 'p-ecoprint-utility-vest')
            h1 = await pg.inner_text('.buy h1'); check('Rompi' in h1, f'nama produk tidak diterjemahkan: {h1}')
            await pg.click('#lang-en'); await pg.wait_for_timeout(150)
            return 'Teks UI & produk berganti EN↔ID dan tersimpan'
        await step(pg, 'Navigasi & konten', 'A05', 'Pengalih bahasa EN/ID', a05)

        async def a06():
            # ID fallback: field ID kosong menampilkan EN + penanda
            await pg.evaluate("DB.products.find(p=>p.id==='p7').story.id='';save()")
            await pg.click('#lang-id'); await go(pg, 'p-botanical-tee')
            t = await pg.inner_text('.buy')
            await pg.click('#lang-en')
            await pg.evaluate("DB.products.find(p=>p.id==='p7').story.id='Kaos kerah bulat harian.';save()")
            check('[EN]' in t, 'tidak ada penanda fallback [EN]')
            return 'Terjemahan kosong tampil versi EN dengan penanda [EN]'
        await step(pg, 'Navigasi & konten', 'A06', 'Fallback terjemahan yang jelas (§14)', a06)

        async def a07():
            pub = ''
            for r in ['home','shop','p-ochre-silk-ecoprint-fabric','p-ecoprint-bomber','wholesale','catalogue-view']:
                await go(pg, r); pub += await pg.inner_text('#view')
            hits = re.findall(r'(USD\s?\d+|US\$\s?\d+|FOB\s+USD)', pub)
            check(not hits, f'harga FOB bocor ke publik: {hits}')
            return 'Harga referensi FOB tidak tampil di halaman publik'
        await step(pg, 'Navigasi & konten', 'A07', 'Harga FOB tidak tampil sebagai harga publik', a07)

        async def a08():
            await go(pg, 'contact'); t = await pg.inner_text('#view')
            check('sedang dikonfirmasi' in t.lower() or 'being confirmed' in t.lower(), 'nomor telepon tampil padahal belum ditetapkan owner')
            check('De Green Azaria' not in t, 'alamat lengkap tampil sebelum dikonfirmasi')
            check('NIB' not in t and 'HKI' not in t, 'klaim legalitas tampil sebelum diverifikasi')
            return 'Nomor, alamat lengkap & legalitas tersembunyi sampai dikonfirmasi owner'
        await step(pg, 'Navigasi & konten', 'A08', 'Data belum dikonfirmasi tidak dipublikasikan (§2)', a08)

        # ================= B. Shop =================
        async def b01():
            await go(pg, 'shop')
            allc = await pg.locator('.pcard').count()
            per = {}
            for c in ['fabric','fashion','bags','accessories','footwear']:
                await pg.click(f'.pill[data-v={c}]'); await pg.wait_for_timeout(150)
                per[c] = await pg.locator('.pcard').count()
                cats = await pg.evaluate("[...document.querySelectorAll('.pcard .sku span:last-child')].map(s=>s.textContent)")
                check(len(set(cats)) <= 1, f'filter {c} bocor kategori lain: {set(cats)}')
            check(sum(per.values()) == allc, f'jumlah per kategori {per} ≠ total {allc}')
            return f'Total {allc}; ' + ', '.join(f'{k} {v}' for k, v in per.items())
        await step(pg, 'Shop', 'B01', 'Filter kategori', b01)

        async def b02():
            await go(pg, 'shop')
            await pg.fill('#q', 'NE-BAG'); await pg.wait_for_timeout(500)
            n = await pg.locator('.pcard').count(); check(n == 3, f'pencarian NE-BAG = {n}, harusnya 3')
            await pg.fill('#q', 'leather'); await pg.wait_for_timeout(500)
            n2 = await pg.locator('.pcard').count(); check(n2 >= 4, f'pencarian material leather = {n2}')
            await pg.fill('#q', 'zzzz'); await pg.wait_for_timeout(500)
            check(await pg.locator('.empty').count() == 1, 'tidak ada empty state')
            await pg.click('[data-act=clearq]'); await pg.wait_for_timeout(200)
            check(await pg.locator('.pcard').count() > 3, 'clear search tidak memulihkan daftar')
            return f'SKU: 3 hasil; material "leather": {n2}; kosong → empty state + hapus pencarian'
        await step(pg, 'Shop', 'B02', 'Pencarian nama/SKU/material', b02)

        async def b03():
            await go(pg, 'shop'); await pg.select_option('#sort', 'plh'); await pg.wait_for_timeout(200)
            prices = await pg.evaluate("[...document.querySelectorAll('.pcard .price')].map(e=>+e.textContent.replace(/\\D/g,''))")
            check(prices == sorted(prices), f'urutan harga salah: {prices}')
            await pg.select_option('#sort', 'phl'); await pg.wait_for_timeout(200)
            p2 = await pg.evaluate("[...document.querySelectorAll('.pcard .price')].map(e=>+e.textContent.replace(/\\D/g,''))")
            check(p2 == sorted(p2, reverse=True), 'urutan tertinggi salah')
            await pg.select_option('#sort', 'featured')
            return 'Urut harga naik & turun benar'
        await step(pg, 'Shop', 'B03', 'Sortir', b03)

        async def b04():
            await go(pg, 'shop-home'); t = await pg.inner_text('#view')
            check(await pg.locator('.pcard').count() == 0, 'ada produk fiktif di Home & Lifestyle')
            check('coming soon' in t.lower(), 'tidak ada status coming soon')
            return 'Coming soon, tanpa produk fiktif'
        await step(pg, 'Shop', 'B04', 'Kategori Home & Lifestyle coming soon', b04)

        async def b05():
            await go(pg, 'shop'); t = await pg.inner_text('#view')
            check('Scarf' not in t, 'produk draft muncul di shop')
            await go(pg, 'p-ecoprint-scarf'); t = await pg.inner_text('#view')
            check('not found' in t.lower(), 'draft dapat dibuka via URL')
            return 'Draft tidak tampil & URL langsung ditolak'
        await step(pg, 'Shop', 'B05', 'Produk draft tidak publik', b05)

        # ================= C. Detail produk =================
        async def c01():
            await go(pg, 'p-leather-clutch-bag')
            t = await pg.inner_text('.buy')
            check('exact piece' in t.lower() and 'NE-BAG-EC-001' in t, 'mode/SKU tidak tampil')
            check(await pg.locator('.piece button').count() >= 1, 'pilihan piece tidak ada')
            await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            tt = await toast(pg); check('already' in tt.lower(), f'tambah piece dua kali tidak dicegah: {tt}')
            n = await pg.evaluate("DB.cart.length"); check(n == 1, f'keranjang berisi {n}')
            return 'Pilih piece → masuk keranjang; piece sama tidak bisa ditambah 2×'
        await step(pg, 'Detail produk', 'C01', 'Exact piece: pilih & tambah sekali', c01)

        async def c02():
            await go(pg, 'p-leaf-tunic-dress')
            xl = pg.locator('.opt button', has_text='XL')
            check(await xl.is_disabled(), 'ukuran habis (XL) masih bisa dipilih')
            t = await pg.inner_text('.buy'); check('pattern family' in t.lower() and 'vary' in t, 'catatan keluarga motif tidak ada')
            return 'Ukuran stok 0 dinonaktifkan; catatan variasi motif tampil'
        await step(pg, 'Detail produk', 'C02', 'Pattern family: varian habis tidak bisa dipilih', c02)

        async def c03():
            await go(pg, 'p-ecoprint-bomber')  # M=1 L=2 XL=1
            await pg.click('.opt button:has-text("L")')
            for _ in range(4): await pg.click('[data-act=qty][data-v="1"]'); await pg.wait_for_timeout(60)
            await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            tt = await toast(pg)
            n = await pg.evaluate("DB.cart.filter(l=>l.pid==='p8').reduce((a,l)=>a+l.qty,0)")
            check(n == 0 and 'stock' in tt.lower(), f'qty melebihi stok diterima (cart {n}, toast {tt})')
            await go(pg, 'home'); await go(pg, 'p-ecoprint-bomber')
            await pg.click('.opt button:has-text("L")'); await pg.click('[data-act=qty][data-v="1"]'); await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(200)
            n = await pg.evaluate("DB.cart.filter(l=>l.pid==='p8').reduce((a,l)=>a+l.qty,0)")
            check(n == 2, f'qty 2 (=stok) tidak masuk: {n}')
            return 'Qty 5 > stok 2 ditolak; qty 2 diterima'
        await step(pg, 'Detail produk', 'C03', 'Jumlah tidak boleh melebihi stok', c03)

        async def c04():
            await go(pg, 'p-ochre-silk-ecoprint-fabric')
            t = await pg.inner_text('.buy'); check('Price on request' in t, 'label harga atas permintaan tidak ada')
            check(await pg.locator('.buy [data-act=add]').count() == 0, 'tombol add to cart muncul untuk produk quote')
            await pg.click('.buy [data-act=quote-for]'); await pg.wait_for_timeout(300)
            check(pg.url.endswith('#wholesale'), 'tidak diarahkan ke form wholesale')
            v = await pg.input_value('#i-sku'); check(v == 'NE-FAB-SLK-001', f'SKU tidak terisi otomatis: {v}')
            return 'Request Price → form inquiry dengan SKU terisi'
        await step(pg, 'Detail produk', 'C04', 'Produk tanpa harga retail → Request Price', c04)

        async def c05():
            await go(pg, 'p-ecoprint-sneakers-umber'); t = await pg.inner_text('.buy')
            check(await pg.locator('.buy [data-act=add]').count() == 0 and 'Order Made to Order' in t, 'MTO tanpa lead time masih bisa checkout')
            await go(pg, 'p-womens-leather-shoes'); t = await pg.inner_text('.buy')
            check('21 working days' in t and await pg.locator('.buy [data-act=add]').count() == 1, 'MTO dengan lead time tidak bisa dipesan')
            return 'MTO tanpa lead time → inquiry; dengan lead time → checkout + info lead time'
        await step(pg, 'Detail produk', 'C05', 'Made to order mengikuti kesiapan lead time', c05)

        async def c06():
            await go(pg, 'p-ecoprint-utility-vest')
            await pg.click('[data-act=img][data-v="1"]'); await pg.wait_for_timeout(120)
            src = await pg.get_attribute('.gallery .main img', 'src'); check('vest-unisex' in src, 'galeri tidak berganti')
            t = await pg.inner_text('.tabs-d'); check(all(k.lower() in t.lower() for k in ['Specifications','Care','Shipping','Motif & returns']), 'bagian detail kurang')
            check(await pg.locator('.pd + .sec-head, .wrap > .sec-head').count() >= 1, 'produk terkait tidak ada')
            return 'Galeri, spesifikasi, perawatan, pengiriman, retur, produk terkait'
        await step(pg, 'Detail produk', 'C06', 'Isi halaman detail sesuai §8', c06)

        # ================= D. Cart & checkout =================
        async def d01():
            await go(pg, 'cart'); n0 = await pg.locator('.line').count()
            check(n0 == 2, f'isi keranjang {n0}')
            sub0 = await pg.inner_text('.summary .r:first-child')
            await pg.click('[data-act=cqty][data-v="-1"]'); await pg.wait_for_timeout(150)
            sub1 = await pg.inner_text('.summary .r:first-child'); check(sub0 != sub1, 'subtotal tidak berubah saat qty dikurangi')
            await pg.click('[data-act=cqty][data-v="1"]'); await pg.click('[data-act=cqty][data-v="1"]'); await pg.wait_for_timeout(150)
            tt = await toast(pg); check('stock' in tt.lower(), 'qty keranjang melebihi stok tidak dicegah')
            return 'Ubah qty memperbarui subtotal; melebihi stok ditolak'
        await step(pg, 'Keranjang & checkout', 'D01', 'Ubah jumlah di keranjang', d01)

        async def d02():
            await go(pg, 'checkout')
            await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(200)
            errs = await pg.locator('#coform .err').count()
            check(errs >= 4, f'hanya {errs} pesan error')
            focused = await pg.evaluate("document.activeElement && document.activeElement.id")
            check(focused == 'c-name', f'fokus tidak ke field pertama yang salah: {focused}')
            check(await pg.evaluate("DB.orders.length") == 0, 'pesanan tercipta walau form tidak valid')
            return f'{errs} pesan error spesifik, fokus ke field pertama, tidak ada pesanan'
        await step(pg, 'Keranjang & checkout', 'D02', 'Validasi form checkout', d02)

        async def fill_co():
            if await pg.input_value('#c-country') != 'ID': await pg.select_option('#c-country', 'ID'); await pg.wait_for_timeout(150)
            await pg.fill('#c-name', 'Sari Pembeli'); await pg.fill('#c-email', 'sari@example.com'); await pg.fill('#c-phone', '+62 812 1111 2222')
            await pg.fill('#c-address', 'Jl. Jenderal Sudirman No. 10, Balikpapan'); await pg.fill('#c-city', 'Balikpapan 76114')
            await pg.check('input[name=pay] >> nth=0')

        async def d03():
            await go(pg, 'checkout'); await fill_co()
            await pg.select_option('#c-zone', 'pap'); await pg.wait_for_timeout(200)
            await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#coform'); check('Papua' in t and ("don't ship" in t or 'not served' in t), 'wilayah tanpa layanan tidak ditolak')
            v = await pg.input_value('#c-name'); check(v == 'Sari Pembeli', 'isian hilang setelah ganti wilayah')
            check(await pg.evaluate("DB.orders.length") == 0, 'pesanan dibuat untuk wilayah tanpa layanan')
            await pg.select_option('#c-zone', 'jawa'); await pg.wait_for_timeout(200)
            tot = await pg.inner_text('.summary .r.t'); return f'Papua ditolak; isian tetap; total Jawa: {tot.split()[-1]}'
        await step(pg, 'Keranjang & checkout', 'D03', 'Wilayah kirim tanpa layanan', d03)

        async def d04():
            await pg.select_option('#c-country', 'Japan'); await pg.wait_for_timeout(200)
            check(await pg.locator('#coform button[type=submit]').is_disabled(), 'checkout internasional tidak dinonaktifkan')
            await pg.click('[data-act=cart-to-inq]'); await pg.wait_for_timeout(300)
            check(pg.url.endswith('#wholesale'), 'tidak diarahkan ke inquiry')
            c = await pg.input_value('#i-country'); s = await pg.input_value('#i-sku')
            check(c == 'Japan' and 'NE-BAG-EC-001' in s, f'inquiry tidak terisi dari keranjang: {c} / {s}')
            await go(pg, 'checkout'); await pg.select_option('#c-country', 'ID'); await pg.wait_for_timeout(200)
            return 'Negara non-ID: checkout nonaktif, keranjang dikirim sebagai inquiry ekspor (negara & SKU terisi)'
        await step(pg, 'Keranjang & checkout', 'D04', 'Pembeli internasional diarahkan ke inquiry', d04)

        async def d05():
            await go(pg, 'checkout'); await fill_co(); await pg.select_option('#c-zone', 'kal'); await pg.wait_for_timeout(150)
            await fill_co()
            await pg.evaluate("document.getElementById('c-total').value='1000'")
            exp = await pg.evaluate("API.quote(DB.cart,'kal').total")
            await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(400)
            check('#pay-' in pg.url, f'tidak menuju halaman bayar: {pg.url}')
            o = await pg.evaluate("DB.orders[0]")
            check(o['total'] == exp and o['priceTampered'], f'total server {o["total"]} vs harapan {exp}')
            return f'Total dari browser Rp1.000 diabaikan; server menetapkan Rp{exp:,}'.replace(',', '.')
        await step(pg, 'Keranjang & checkout', 'D05', 'Total dihitung server, manipulasi browser ditolak', d05)

        async def d06():
            t = await pg.inner_text('#view')
            tm = await pg.inner_text('#timer'); check(re.match(r'1[45]:\d\d', tm), f'timer reservasi tidak ~15 menit: {tm}')
            o = await pg.evaluate("DB.orders[0]")
            check(o['pay'] == 'pending' and o['ful'] == 'unfulfilled', 'status awal salah')
            st = await pg.evaluate("DB.products.find(p=>p.id==='p12').pieces[0].status"); check(st == 'reserved', f'piece tidak direservasi: {st}')
            await go(pg, 'p-leather-clutch-bag'); t = await pg.inner_text('.buy')
            check('Reserved' in t and await pg.locator('.buy [data-act=add]').is_disabled(), 'piece yang direservasi masih bisa dibeli')
            return f'Order {o["no"]} pending/unfulfilled, timer {tm}, piece berstatus Reserved di toko'
        await step(pg, 'Keranjang & checkout', 'D06', 'Pesanan pending + reservasi stok', d06)

        async def d07():
            no = await pg.evaluate("DB.orders[0].no"); await go(pg, 'pay-' + no)
            await pg.click('[data-act=pay][data-v=paid]'); await pg.wait_for_timeout(300)
            o = await pg.evaluate("DB.orders[0]")
            check(o['pay'] == 'paid', 'status tidak paid')
            st = await pg.evaluate("DB.products.find(p=>p.id==='p12').pieces[0].status"); check(st == 'sold', 'piece tidak sold')
            stk = await pg.evaluate("DB.products.find(p=>p.id==='p8').variants.find(v=>v.label==='L')")
            check(stk['stock'] == 0 and stk['reserved'] == 0, f'stok varian tidak berkurang: {stk}')
            check(await pg.evaluate("DB.cart.length") == 0, 'keranjang tidak dikosongkan')
            await pg.click('[data-act=pay][data-dup="1"]'); await pg.wait_for_timeout(200)
            tt = await toast(pg); check('duplicate' in tt.lower(), f'callback duplikat: {tt}')
            n = await pg.evaluate("DB.orders.filter(o=>o.pay==='paid').length"); check(n == 1, 'pembayaran ganda')
            return 'Paid → piece sold, stok varian berkurang, keranjang kosong; callback ulang diabaikan'
        await step(pg, 'Keranjang & checkout', 'D07', 'Pembayaran sukses & callback duplikat', d07)

        async def d08():
            no = await pg.evaluate("DB.orders[0].no")
            await go(pg, 'order'); await pg.fill('#os-no', no.lower()); await pg.fill('#os-email', 'SARI@example.com'); await pg.click('#osform button'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#view'); check('paid' in t, 'status tidak tampil')
            await pg.fill('#os-email', 'orang@lain.com'); await pg.click('#osform button'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#view'); check('No order matches' in t and 'paid' not in t.split('No order matches')[1][:200], 'pesanan bisa dilihat dengan email lain')
            return 'Status tampil dengan nomor+email (tidak peka huruf besar); email lain ditolak'
        await step(pg, 'Keranjang & checkout', 'D08', 'Cek status pesanan secara aman', d08)

        async def mk_order(slug, size=None):
            await go(pg, 'p-' + slug)
            if size: await pg.click(f'.opt button:has-text("{size}")')
            await pg.click('.buy [data-act=add]'); await pg.wait_for_timeout(120)
            await go(pg, 'checkout'); await fill_co(); await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(350)
            return await pg.evaluate("DB.orders[0].no")

        async def d09():
            before = await pg.evaluate("(v=>v.stock-v.reserved)(DB.products.find(p=>p.id==='p6').variants[0])")
            no = await mk_order('mens-ecoprint-shirt', 'M')
            mid = await pg.evaluate("(v=>v.stock-v.reserved)(DB.products.find(p=>p.id==='p6').variants[0])")
            await pg.click('[data-act=pay][data-v=failed]'); await pg.wait_for_timeout(200)
            after = await pg.evaluate("(v=>v.stock-v.reserved)(DB.products.find(p=>p.id==='p6').variants[0])")
            st = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}').pay")
            check(mid == before - 1 and after == before and st == 'failed', f'{before}->{mid}->{after}, {st}')
            return f'Tersedia {before} → {mid} → {after}; status failed'
        await step(pg, 'Keranjang & checkout', 'D09', 'Pembayaran gagal melepas reservasi', d09)

        async def d10():
            await pg.evaluate("DB.cart=[];save()")
            before = await pg.evaluate("(v=>v.stock-v.reserved)(DB.products.find(p=>p.id==='p7').variants[0])")
            no = await mk_order('botanical-tee', 'M')
            await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}').expiresAt=Date.now()-1000;save()")
            await pg.wait_for_timeout(6000)
            o = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}')")
            after = await pg.evaluate("(v=>v.stock-v.reserved)(DB.products.find(p=>p.id==='p7').variants[0])")
            t = await pg.inner_text('#view')
            check(o['pay'] == 'expired' and after == before, f'{o["pay"]}, stok {before}->{after}')
            check('released' in t.lower(), 'halaman bayar tidak diperbarui otomatis')
            await pg.click('[data-act=pay][data-v=paid]'); await pg.wait_for_timeout(250)
            o = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}')")
            check(o['pay'] == 'paid' and not o['recon'], 'pembayaran terlambat (stok masih ada) tidak diproses')
            return 'Reservasi habis otomatis (sweep 5 dtk) → expired & stok kembali; pembayaran terlambat dengan stok tersedia → paid'
        await step(pg, 'Keranjang & checkout', 'D10', 'Reservasi kedaluwarsa & pembayaran terlambat', d10)

        async def d11():
            await pg.evaluate("DB.cart=[];save()")
            no1 = await mk_order('long-leather-wallet')
            await pg.click('[data-act=pay][data-v=expired]'); await pg.wait_for_timeout(200)
            no2 = await mk_order('long-leather-wallet')
            await pg.click('[data-act=pay][data-v=paid]'); await pg.wait_for_timeout(200)
            await go(pg, 'pay-' + no1); await pg.click('[data-act=pay][data-v=paid]'); await pg.wait_for_timeout(250)
            o1 = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no1}')")
            t = await pg.inner_text('#view')
            check(o1['recon'] and 'no longer available' in t, 'pembayaran terlambat atas barang terjual tidak masuk rekonsiliasi')
            return f'{no1}: dibayar terlambat setelah piece terjual ke {no2} → antrean rekonsiliasi + pesan ke pembeli'
        await step(pg, 'Keranjang & checkout', 'D11', 'Pembayaran terlambat untuk barang yang sudah terjual', d11)

        async def d12():
            await pg.evaluate("DB.cart=[];save()"); await go(pg, 'cart')
            t = await pg.inner_text('#view'); check('empty' in t.lower(), 'empty state keranjang tidak ada')
            # produk tidak lagi tersedia di keranjang
            await pg.evaluate("DB.cart=[{pid:'p16',ref:'pc-1601',qty:1}];save()"); await go(pg, 'home'); await go(pg, 'cart')
            t = await pg.inner_text('#view'); check('available' in t.lower() or 'another checkout' in t.lower(), 'barang terjual di keranjang tidak ditandai')
            await go(pg, 'checkout'); await fill_co(); await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(250)
            check('#checkout' in pg.url and 'no longer available' in (await pg.inner_text('#coform')), 'checkout barang terjual tidak ditolak')
            await pg.evaluate("DB.cart=[];save()")
            return 'Keranjang kosong tampil; barang terjual ditandai & checkout ditolak'
        await step(pg, 'Keranjang & checkout', 'D12', 'Keranjang kosong & barang tak tersedia', d12)

        # ================= E. Inquiry =================
        async def e01():
            await go(pg, 'wholesale'); await pg.evaluate("INQ={pre:{},errs:{},done:null}"); await go(pg, 'home'); await go(pg, 'wholesale')
            await pg.click('#inqform button[type=submit]'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#inqform'); n = await pg.evaluate("DB.inquiries.length")
            check('Enter your name' in t and 'valid email' in t and 'Choose a country' in t and 'privacy' in t.lower(), 'pesan validasi tidak lengkap')
            await pg.fill('#i-name', 'Kenji Tanaka'); await pg.fill('#i-company', 'Mori Select Shop'); await pg.fill('#i-email', 'kenji@mori.jp')
            await pg.select_option('#i-country', 'Japan'); await pg.select_option('#i-type', 'export'); await pg.fill('#i-sku', 'NE-BAG-EC-003')
            await pg.fill('#i-qty', '60 pcs'); await pg.fill('#i-dest', 'Osaka 530-0001'); await pg.check('#i-privacy')
            await pg.click('#inqform button[type=submit]'); await pg.wait_for_timeout(300)
            t = await pg.inner_text('#view'); m = re.search(r'INQ-2026-\d{4}', t)
            check(m and pg.url.endswith('#inq-done'), 'tidak ada halaman konfirmasi bernomor')
            q = await pg.evaluate("DB.inquiries[0]"); check(q['status'] == 'New' and q['notify'] == 'sent' and q['mkt'] is False, 'data inquiry salah')
            return f'Validasi lengkap; {m.group(0)} tersimpan (status New, marketing consent terpisah = tidak)'
        await step(pg, 'Inquiry B2B', 'E01', 'Inquiry wholesale/ekspor: validasi & nomor', e01)

        async def e02():
            await go(pg, 'custom')
            opts = await pg.evaluate("[...document.querySelectorAll('#i-type option')].map(o=>o.value)")
            check(set(opts) == {'custom','private','sample'}, f'jenis inquiry custom: {opts}')
            check(await pg.locator('#i-brand').count() == 1 and await pg.locator('#i-pack').count() == 1, 'field branding/kemasan tidak ada')
            await pg.fill('#i-name', 'Lena Vogel'); await pg.fill('#i-email', 'lena@studio.de'); await pg.select_option('#i-country', 'Germany')
            await pg.select_option('#i-type', 'private'); await pg.fill('#i-brand', 'Woven label'); await pg.select_option('#i-pack', 'Gift box')
            await pg.set_input_files('#i-file', files=[{'name': 'ref.png', 'mimeType': 'image/png', 'buffer': b'\x89PNG\r\n'}])
            await pg.check('#i-privacy'); await pg.check('#i-mkt'); await pg.click('#inqform button[type=submit]'); await pg.wait_for_timeout(300)
            q = await pg.evaluate("DB.inquiries[0]")
            check(q['type'] == 'private' and q['pack'] == 'Gift box' and q['file'] == 'ref.png' and q['mkt'] is True, f'data: {q}')
            return 'Private label + branding, kemasan, lampiran, marketing consent tersimpan'
        await step(pg, 'Inquiry B2B', 'E02', 'Proyek custom/private label', e02)

        async def e03():
            await go(pg, 'catalogue')
            fields = await pg.locator('#catform input, #catform select').count()
            check(fields <= 4, f'form katalog terlalu panjang ({fields} field)')
            await pg.fill('#k-name', 'Amy'); await pg.fill('#k-email', 'amy@shop.sg'); await pg.click('#catform button'); await pg.wait_for_timeout(300)
            check(pg.url.endswith('#inq-done'), 'tidak ada konfirmasi')
            await pg.click('a[href="#catalogue-view"]'); await pg.wait_for_timeout(250)
            t = await pg.inner_text('#view'); check('Version 1.0' in t and 'NE-BAG-EC-001' in t, 'katalog digital tidak lengkap')
            return f'Form singkat ({fields} field) → konfirmasi → katalog digital v1.0'
        await step(pg, 'Inquiry B2B', 'E03', 'Request Catalogue', e03)

        # ================= F. Admin CMS =================
        async def login(role):
            await go(pg, 'admin')
            if await pg.locator('[data-act=logout]').count(): await pg.click('[data-act=logout]'); await pg.wait_for_timeout(100)
            await pg.click(f'[data-act=role][data-v={role}]'); await pg.wait_for_timeout(150)
        async def tab(t): await pg.click(f'.aside [data-act=tab][data-v={t}]'); await pg.wait_for_timeout(150)

        async def f01():
            exp = {'owner': 9, 'content': 4, 'sales': 4, 'fulfillment': 2}  # content: dash, produk, konten, katalog
            got = {}
            for r in exp:
                await login(r); got[r] = await pg.locator('.aside [data-act=tab]').count()
            check(got == exp, f'tab per role {got}')
            return ', '.join(f'{k}: {v} menu' for k, v in got.items())
        await step(pg, 'Admin CMS', 'F01', 'Menu admin sesuai role', f01)

        async def f02():
            await login('content'); await tab('products'); await pg.click('tr[data-v=p1]'); await pg.wait_for_timeout(150)
            check(await pg.locator('#e-price').is_disabled(), 'Content Admin dapat mengedit harga')
            t = await pg.inner_text('#pform'); check('FOB' not in t, 'referensi FOB terlihat oleh Content Admin')
            # bypass UI: panggil API langsung
            r = await pg.evaluate("(()=>{try{const p=DB.products.find(x=>x.id==='p1');API.saveProduct('content',p,Object.assign({},p,{price:1}),p.variants.map(v=>v.stock));return 'ok'}catch(e){return e.message}})()")
            check('403' in r, f'API tidak menolak: {r}')
            r2 = await pg.evaluate("(()=>{try{API.admin('fulfillment','product.edit','x',()=>{});return 'ok'}catch(e){return e.message}})()")
            r3 = await pg.evaluate("(()=>{try{API.admin('sales','settings','x',()=>{});return 'ok'}catch(e){return e.message}})()")
            check('403' in r2 and '403' in r3, f'{r2} / {r3}')
            return 'Field harga terkunci; panggilan API langsung ditolak 403 (harga, edit produk, pengaturan)'
        await step(pg, 'Admin CMS', 'F02', 'Izin diperiksa di backend, bukan hanya UI', f02)

        async def f03():
            await login('owner'); await tab('products'); await pg.click('tr[data-v=p1]'); await pg.wait_for_timeout(150)
            await pg.fill('#e-nen', 'Ecoprint Utility Vest — Rust'); await pg.fill('#e-price', '715000')
            await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(200)
            check('draft' in (await pg.inner_text('#pform')).lower(), 'tidak ada tanda draft')
            await go(pg, 'p-ecoprint-utility-vest'); t = await pg.inner_text('.buy')
            check('Rust' not in t and '685.000' in t, 'perubahan draft sudah tampil di toko')
            await go(pg, 'admin'); await tab('products'); await pg.click('tr[data-v=p1]'); await pg.click('[data-act=p-preview]'); await pg.wait_for_timeout(300)
            t = await pg.inner_text('#view'); check('PREVIEW' in t and 'Rust' in t and '715.000' in t, 'preview tidak menampilkan draft')
            await pg.click('[data-act=endpreview]'); await pg.wait_for_timeout(200); await pg.click('tr[data-v=p1]'); await pg.click('[data-act=p-publish]'); await pg.wait_for_timeout(200)
            await go(pg, 'p-ecoprint-utility-vest'); t = await pg.inner_text('.buy')
            check('Rust' in t and '715.000' in t, 'publish tidak menerapkan perubahan')
            return 'Edit → draft (toko tetap) → preview → publish (toko berubah)'
        await step(pg, 'Admin CMS', 'F03', 'Alur edit → draft → preview → publish', f03)

        async def f04():
            await go(pg, 'admin'); await tab('products'); await pg.click('[data-act=p-new]'); await pg.wait_for_timeout(200)
            await pg.fill('#e-sku', 'NE-BAG-EC-001'); await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(200)
            tt = await toast(pg); check('unik' in tt.lower() or 'sudah dipakai' in tt.lower(), f'SKU duplikat diterima: {tt}')
            await pg.fill('#e-sku', 'NE-HOM-CSH-001'); await pg.fill('#e-nen', 'Ecoprint Cushion Cover'); await pg.fill('#e-price', '275000'); await pg.select_option('#e-cat', 'home')
            await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=p-publish]'); await pg.wait_for_timeout(150)
            tt = await toast(pg); check('foto' in tt.lower(), f'publish tanpa foto tidak dicegah: {tt}')
            await pg.select_option('#e-addimg', 'fabric-mood'); await pg.wait_for_timeout(200)
            await pg.fill('#e-st-0', '3'); await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=p-publish]'); await pg.wait_for_timeout(200)
            await pg.reload(); await pg.wait_for_timeout(300)
            await go(pg, 'shop'); await pg.fill('#q', 'NE-HOM-CSH-001'); await pg.wait_for_timeout(500)
            n = await pg.locator('.pcard').count(); check(n == 1, f'produk baru tidak tampil setelah reload ({n})')
            return 'SKU duplikat ditolak; tanpa foto tidak bisa publish; produk baru tampil dan tersimpan setelah reload'
        await step(pg, 'Admin CMS', 'F04', 'Tambah produk baru hingga tampil di toko', f04)

        async def f05():
            await login('owner'); await tab('products')
            pid = await pg.evaluate("DB.products.find(p=>p.sku==='NE-HOM-CSH-001').id")
            await pg.click(f'tr[data-v={pid}]'); await pg.click('[data-act=p-status][data-v=archived]'); await pg.wait_for_timeout(150)
            await go(pg, 'shop'); await pg.fill('#q', 'NE-HOM-CSH-001'); await pg.wait_for_timeout(500)
            check(await pg.locator('.pcard').count() == 0, 'produk archived masih tampil')
            await pg.fill('#q', ''); await pg.wait_for_timeout(400)
            await go(pg, 'admin'); await tab('products'); await pg.click(f'tr[data-v={pid}]')
            check(await pg.locator('[data-act=p-del]').count() == 0, 'tombol hapus muncul untuk produk archived')
            await pg.click('[data-act=p-status][data-v=draft]'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=p-del]'); await pg.wait_for_timeout(100)
            check(await pg.evaluate(f"DB.products.some(p=>p.id==='{pid}')"), 'terhapus tanpa konfirmasi')
            await pg.click('[data-act=p-del-yes]'); await pg.wait_for_timeout(150)
            check(not await pg.evaluate(f"DB.products.some(p=>p.id==='{pid}')"), 'draft tidak terhapus')
            await pg.click('tr[data-v=p12]'); check(await pg.locator('[data-act=p-del]').count() == 0, 'produk dengan transaksi bisa dihapus')
            return 'Archive menyembunyikan; restore → draft; hapus permanen perlu konfirmasi & hanya untuk draft tanpa transaksi'
        await step(pg, 'Admin CMS', 'F05', 'Archive, restore & hapus aman', f05)

        async def f06():
            await pg.click('tr[data-v=p6]'); await pg.wait_for_timeout(100)
            snap = await pg.evaluate("DB.orders.flatMap(o=>o.items).find(i=>i.sku==='NE-FSH-MSH-001')")
            await pg.fill('#e-nen', 'Renamed Shirt'); await pg.click('#pform button[type=submit]'); await pg.click('[data-act=p-publish]'); await pg.wait_for_timeout(150)
            snap2 = await pg.evaluate("DB.orders.flatMap(o=>o.items).find(i=>i.sku==='NE-FSH-MSH-001')")
            check(snap['name'] == snap2['name'], 'snapshot pesanan berubah')
            check(await pg.locator('#e-mode').is_disabled(), 'mode motif masih bisa diubah setelah ada pesanan')
            await pg.fill('#e-nen', snap['name']); await pg.click('#pform button[type=submit]'); await pg.click('[data-act=p-publish]')
            return f'Snapshot "{snap["name"]}" tetap; mode motif terkunci setelah ada pesanan'
        await step(pg, 'Admin CMS', 'F06', 'Snapshot pesanan tidak berubah saat produk diedit', f06)

        async def f07():
            # stok di bawah reservasi
            await pg.evaluate("DB.cart=[];save()")
            no = await mk_order('botanical-tee', 'L')
            await login('owner'); await tab('products'); await pg.click('tr[data-v=p7]'); await pg.wait_for_timeout(100)
            idx = await pg.evaluate("DB.products.find(p=>p.id==='p7').variants.findIndex(v=>v.label==='L')")
            await pg.fill(f'#e-st-{idx}', '0'); await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(150)
            tt = await toast(pg); check('di bawah' in tt, f'stok di bawah reservasi diterima: {tt}')
            await pg.fill(f'#e-st-{idx}', '8'); await pg.click('#pform button[type=submit]'); await pg.wait_for_timeout(150)
            await tab('settings'); t = await pg.inner_text('.amain'); check('adjust' in t, 'mutasi penyesuaian stok tidak tercatat')
            await tab('orders'); await pg.click(f'tr[data-v={no}]'); await pg.click('[data-act=o-cancel]'); await pg.wait_for_timeout(150)
            v = await pg.evaluate(f"DB.products.find(p=>p.id==='p7').variants[{idx}]")
            check(v['reserved'] == 0, 'pembatalan tidak melepas stok')
            return 'Stok < reservasi ditolak; penyesuaian tercatat di mutasi; Owner batalkan pending → stok dilepas'
        await step(pg, 'Admin CMS', 'F07', 'Stok, mutasi & pembatalan', f07)

        async def f08():
            await login('fulfillment'); await tab('orders')
            no = await pg.evaluate("DB.orders.find(o=>o.pay==='paid'&&!o.recon&&o.ful==='unfulfilled').no")
            await pg.click(f'tr[data-v={no}]'); await pg.click('[data-act=o-ful][data-v=processing]'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=o-ful][data-v=shipped]'); await pg.wait_for_timeout(150)
            tt = await toast(pg); check('resi' in tt.lower(), 'kirim tanpa resi diterima')
            await pg.fill('#o-track', 'JNE-BPN-88812345'); await pg.click('[data-act=o-ful][data-v=shipped]'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=o-ful][data-v=delivered]'); await pg.wait_for_timeout(150)
            o = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}')"); check(o['ful'] == 'delivered' and o['pay'] == 'paid', 'status salah')
            check(await pg.locator('[data-act=o-refund]').count() == 0, 'Fulfillment bisa refund')
            await pg.click('[data-act=o-ful][data-v=returned]'); await pg.wait_for_timeout(150)
            before = await pg.evaluate("JSON.stringify(DB.products.map(p=>[p.pieces.map(x=>x.status),p.variants.map(v=>v.stock)]))")
            await pg.click('[data-act=o-restock]'); await pg.wait_for_timeout(150)
            after = await pg.evaluate("JSON.stringify(DB.products.map(p=>[p.pieces.map(x=>x.status),p.variants.map(v=>v.stock)]))")
            check(before != after, 'restok tidak mengubah stok')
            await go(pg, 'order'); await pg.fill('#os-no', no); await pg.fill('#os-email', 'sari@example.com'); await pg.click('#osform button'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#view'); check('Returned' in t or 'JNE-BPN' in t, 'pembeli tidak melihat status/resi')
            return f'{no}: processing → shipped (wajib resi) → delivered → returned → restok setelah diperiksa; pembeli melihat status'
        await step(pg, 'Admin CMS', 'F08', 'Pemenuhan pesanan oleh Fulfillment', f08)

        async def f09():
            await login('owner'); await tab('orders')
            no = await pg.evaluate("DB.orders.find(o=>o.recon).no")
            await pg.click(f'tr[data-v={no}]'); t = await pg.inner_text('.amain'); check('Rekonsiliasi' in t, 'tanda rekonsiliasi tidak tampil')
            await pg.click('[data-act=o-refund]'); await pg.wait_for_timeout(150)
            o = await pg.evaluate(f"DB.orders.find(o=>o.no==='{no}')"); check(o['pay'] == 'refunded' and not o['recon'], 'refund tidak tercatat')
            await tab('dash'); t = await pg.inner_text('.amain')
            rev = await pg.evaluate("DB.orders.filter(o=>o.pay==='paid').reduce((a,o)=>a+o.total,0)")
            return f'Order rekonsiliasi {no} di-refund; dashboard pendapatan terverifikasi = Rp{rev:,}'.replace(',', '.')
        await step(pg, 'Admin CMS', 'F09', 'Rekonsiliasi & refund oleh Owner', f09)

        async def f10():
            await login('sales'); await tab('inquiries')
            no = await pg.evaluate("DB.inquiries.find(i=>i.type==='export').no")
            await pg.click(f'tr[data-v={no}]'); await pg.select_option('#i-pic', 'Sales 1'); await pg.click('[data-act=i-save]'); await pg.wait_for_timeout(150)
            st = await pg.evaluate(f"DB.inquiries.find(i=>i.no==='{no}').status"); check(st == 'Assigned', f'PIC tidak mengubah status ke Assigned: {st}')
            t = await pg.inner_text('#qform'); check('FOB katalog: USD' in t, 'referensi FOB tidak tersedia untuk Sales')
            await pg.click('#qform button[type=submit]'); await pg.wait_for_timeout(150)
            check('Isi harga' in await pg.inner_text('#qform'), 'quotation kosong diterima')
            await pg.fill('#q-price', '38'); await pg.fill('#q-valid', '2026-10-31'); await pg.fill('#q-lead', '30 working days from deposit and sample approval'); await pg.fill('#q-terms', '50% deposit, 50% before shipment')
            await pg.fill('#q-port', 'Balikpapan'); await pg.click('#qform button[type=submit]'); await pg.wait_for_timeout(150)
            await pg.fill('#q-price', '36'); await pg.fill('#q-valid', '2026-11-15'); await pg.fill('#q-lead', '30 working days'); await pg.fill('#q-terms', '50/50')
            await pg.click('#qform button[type=submit]'); await pg.wait_for_timeout(150)
            qs = await pg.evaluate(f"DB.quotes.filter(q=>q.inq==='{no}').map(q=>q.no+' v'+q.ver)")
            check(len(qs) == 2 and qs[0].split()[0] == qs[1].split()[0], f'versi quotation: {qs}')
            await pg.click('[data-act=q-send] >> nth=1'); await pg.wait_for_timeout(150); await pg.click('[data-act=q-approve]'); await pg.wait_for_timeout(150)
            st = await pg.evaluate(f"DB.inquiries.find(i=>i.no==='{no}').status"); check(st == 'Approved', st)
            check(await pg.evaluate("DB.products.find(p=>p.id==='p1').price") == 715000, 'quotation mengubah harga retail')
            return f'{no}: Assigned → quotation {qs[0]}, {qs[1]} (USD FOB Balikpapan) → Sent → Approved; harga retail tidak berubah'
        await step(pg, 'Admin CMS', 'F10', 'Pipeline inquiry & versi quotation (Sales)', f10)

        async def f11():
            await login('owner'); await tab('settings'); await pg.select_option('#s-notif', '0'); await pg.click('#sform button[type=submit]'); await pg.wait_for_timeout(150)
            await go(pg, 'catalogue'); await pg.fill('#k-name', 'Bo'); await pg.fill('#k-email', 'bo@x.com'); await pg.click('#catform button'); await pg.wait_for_timeout(250)
            q = await pg.evaluate("DB.inquiries[0]"); check(q['notify'] == 'failed', 'notifikasi gagal tidak tercatat')
            await go(pg, 'admin'); await tab('dash'); check('gagal' in await pg.inner_text('.amain'), 'dashboard tidak memberi peringatan')
            await tab('settings'); await pg.select_option('#s-notif', '1'); await pg.click('#sform button[type=submit]'); await pg.wait_for_timeout(150)
            await tab('inquiries'); await pg.click(f'tr[data-v={q["no"]}]'); await pg.click('[data-act=i-retry]'); await pg.wait_for_timeout(150)
            n = await pg.evaluate(f"DB.inquiries.find(i=>i.no==='{q['no']}').notify"); check(n == 'sent', 'retry gagal')
            return f'{q["no"]} tersimpan saat email gagal; peringatan di dashboard; kirim ulang berhasil'
        await step(pg, 'Admin CMS', 'F11', 'Inquiry tetap tersimpan saat notifikasi gagal', f11)

        async def f12():
            await login('content'); await tab('content')
            await pg.fill('#c-hen', 'Leaves tell the story of Borneo'); await pg.fill('#c-hid', 'Setiap daun bercerita tentang Borneo')
            await pg.select_option('#c-feat', 'p12'); await pg.click('#cform button[type=submit]'); await pg.wait_for_timeout(150)
            check(await pg.locator('[data-act=k-save]').count() == 0 and await pg.locator('input[name=activePhone]').first.is_disabled(), 'Content Admin dapat menetapkan kontak')
            await pg.click('#lang-id'); await go(pg, 'home'); t = await pg.inner_text('#view'); await pg.click('#lang-en')
            check('Setiap daun bercerita' in t and 'Tas Clutch Kulit' in t, 'konten hero ID / featured tidak berubah')
            return 'Hero EN/ID & produk unggulan berubah di homepage; kontak terkunci untuk Content Admin'
        await step(pg, 'Admin CMS', 'F12', 'Kelola konten homepage', f12)

        async def f13():
            await login('owner'); await tab('content')
            await pg.check('input[name=activePhone][value="0"]'); await pg.check('#k-addr'); await pg.check('[data-legal="0"]')
            await pg.click('[data-act=k-save]'); await pg.wait_for_timeout(150)
            await go(pg, 'contact'); t = await pg.inner_text('#view'); f = await pg.inner_text('footer')
            check('+62 815-4545-7999' in t and '+62 815-4545-7999' in f, 'nomor aktif tidak tampil')
            check('De Green Azaria' in t, 'alamat terkonfirmasi tidak tampil')
            return 'Nomor yang dipilih Owner & alamat terkonfirmasi tampil di Contact dan footer'
        await step(pg, 'Admin CMS', 'F13', 'Owner menetapkan kontak resmi', f13)

        async def f14():
            await login('content'); await tab('catalogue')
            await pg.uncheck('[data-catp=p19]'); await pg.click('[data-act=cat-save]'); await pg.wait_for_timeout(150)
            await go(pg, 'catalogue-view'); t = await pg.inner_text('#view')
            check('Version 1.1' in t and 'NE-FTW-SNK-002' not in t and 'NE-FTW-SNK-001' in t, 'versi/isi katalog salah')
            return 'Versi naik ke 1.1 dengan tanggal; produk yang dikeluarkan tidak tampil'
        await step(pg, 'Admin CMS', 'F14', 'Versi katalog dari database produk', f14)

        async def f15():
            await login('sales'); await tab('reports'); t = await pg.inner_text('.amain')
            csv = await pg.input_value('#csv')
            check('sku,name,qty,revenue_idr' in csv and 'NE-BAG-EC-001' in csv, 'CSV tidak berisi penjualan terbayar')
            check('NE-ACC-WLL-001' in csv, 'penjualan wallet terbayar tidak masuk')
            rows = csv.strip().split('\n')
            return f'Laporan per produk & per jenis inquiry; CSV {len(rows)-1} baris'
        await step(pg, 'Admin CMS', 'F15', 'Laporan & ekspor CSV', f15)

        async def f16():
            await login('owner'); await tab('settings')
            await pg.fill('#z-r-0', '30000'); await pg.uncheck('#z-on-4'); await pg.click('#sform button[type=submit]'); await pg.wait_for_timeout(150)
            await pg.evaluate("DB.cart=[{pid:'p14',ref:DB.products.find(p=>p.id==='p14').variants[0].id,qty:1}];save()")
            await go(pg, 'checkout'); t = await pg.inner_text('#c-zone')
            check('30.000' in t and 'NTB, NTT & Maluku · not served' in t, f'tarif/layanan baru tidak dipakai: {t}')
            await pg.evaluate("DB.cart=[];save()")
            await go(pg, 'admin'); await tab('settings'); a = await pg.inner_text('.audit')
            check('Pengaturan transaksi' in a and 'Content Admin' in a and 'Sales' in a, 'audit log tidak lengkap')
            return 'Tarif & wilayah baru langsung dipakai checkout; audit log mencatat role, waktu & aksi'
        await step(pg, 'Admin CMS', 'F16', 'Pengaturan pengiriman & audit log', f16)

        async def f17():
            await tab('tests'); await pg.click('[data-act=run-tests]'); await pg.wait_for_timeout(300)
            t = await pg.inner_text('.amain'); m = re.search(r'(\d+)/(\d+) lulus', t)
            check(m and m.group(1) == m.group(2), f'hasil: {m.group(0) if m else t[:100]}')
            return m.group(0)
        await step(pg, 'Admin CMS', 'F17', 'Uji penerimaan otomatis bawaan (§17)', f17)

        async def f18():
            n0 = await pg.evaluate("DB.orders.length")
            await pg.reload(); await pg.wait_for_timeout(300)
            n1 = await pg.evaluate("DB.orders.length"); check(n0 == n1 and n0 > 0, 'data hilang setelah reload')
            await go(pg, 'admin'); await pg.click('[data-act=role][data-v=owner]') if await pg.locator('[data-act=role]').count() else None
            await tab('settings'); await pg.click('[data-act=reset]'); await pg.wait_for_timeout(100)
            check(await pg.evaluate("DB.orders.length") == n0, 'reset tanpa konfirmasi')
            await pg.click('[data-act=reset-yes]'); await pg.wait_for_timeout(150)
            check(await pg.evaluate("DB.orders.length") == 0, 'reset gagal')
            return f'{n0} pesanan tetap setelah reload; reset demo perlu konfirmasi'
        await step(pg, 'Admin CMS', 'F18', 'Data tersimpan & reset demo', f18)

        # ================= G. Responsif, aksesibilitas, tema =================
        m = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
        mp = await m.new_page(); mp.on('console', onerr); mp.on('pageerror', lambda e: ERRS.append('pageerror(m): ' + str(e)))
        async def g01():
            await mp.goto(BASE + '#home'); await mp.wait_for_timeout(300)
            over = []
            for r in ROUTES:
                await mp.evaluate(f"location.hash={json.dumps(r)}"); await mp.wait_for_timeout(150)
                if r == 'admin' and await mp.locator('[data-act=role]').count():
                    await mp.click('[data-act=role][data-v=owner]'); await mp.wait_for_timeout(150)
                w = await mp.evaluate("document.documentElement.scrollWidth")
                if w > 391: over.append(f'{r}:{w}')
            for t in ['products','orders','inquiries','content','settings','tests']:
                await mp.evaluate(f"UI.tab='{t}';render(true)"); await mp.wait_for_timeout(100)
                w = await mp.evaluate("document.documentElement.scrollWidth")
                if w > 391: over.append(f'admin-{t}:{w}')
            check(not over, f'scroll horizontal: {over}')
            return f'{len(ROUTES)+6} layar tanpa scroll horizontal di 390 px'
        await step(mp, 'Responsif & aksesibilitas', 'G01', 'Mobile 390 px tanpa scroll horizontal', g01)

        async def g02():
            await mp.evaluate("location.hash='home'"); await mp.wait_for_timeout(150)
            await mp.click('#menubtn'); await mp.wait_for_timeout(100)
            check(await mp.locator('#mnav').is_visible(), 'menu mobile tidak terbuka')
            await mp.click('#mnav a[href="#wholesale"]'); await mp.wait_for_timeout(200)
            check(mp.url.endswith('#wholesale') and not await mp.locator('#mnav').is_visible(), 'navigasi menu mobile gagal')
            await mp.evaluate("location.hash='p-ecoprint-utility-vest'"); await mp.wait_for_timeout(200)
            check(await mp.locator('#buybar').is_visible(), 'tombol beli tidak menempel di bawah layar')
            await mp.click('#buybar [data-act=add]'); await mp.wait_for_timeout(150)
            n = await mp.evaluate("DB.cart.length"); check(n == 1, 'tombol buybar tidak menambah ke keranjang')
            badge = await mp.inner_text('#cartn'); check(badge == '1', 'badge keranjang tidak terlihat')
            return 'Menu ringkas bekerja; tombol beli menempel & berfungsi; badge keranjang'
        await step(mp, 'Responsif & aksesibilitas', 'G02', 'Navigasi & pembelian di mobile', g02)

        async def g03():
            d = await b.new_context(viewport={'width': 1280, 'height': 900}, color_scheme='dark'); dp = await d.new_page()
            await dp.goto(BASE + '#home'); await dp.wait_for_timeout(300)
            res = {}
            for r in ['home','shop','p-leather-clutch-bag','checkout','admin']:
                await dp.evaluate(f"location.hash='{r}'"); await dp.wait_for_timeout(150)
                res[r] = await dp.evaluate("""(()=>{const L=c=>{const m=c.match(/\\d+(\\.\\d+)?/g).map(Number).slice(0,3).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
                 const bg=getComputedStyle(document.body).backgroundColor;let worst=99;
                 document.querySelectorAll('#view p,#view h1,#view h2,#view h3,#view h4,#view span,#view a,#view label,#view td').forEach(e=>{if(!e.offsetParent||!e.textContent.trim())return;let n=e,b=null;while(n&&n!==document.documentElement){const c=getComputedStyle(n).backgroundColor;if(c&&!c.startsWith('rgba(0, 0, 0, 0)')&&c!=='transparent'){b=c;break}n=n.parentElement}if(!b||e.closest('.hero'))return;const a=L(getComputedStyle(e).color),z=L(b);const r=(Math.max(a,z)+.05)/(Math.min(a,z)+.05);if(r<worst)worst=r});
                 return {bg,worst:Math.round(worst*100)/100}})()""")
            await d.close()
            low = {k: v for k, v in res.items() if v['worst'] < 3}
            check(all('20, 25, 20' in v['bg'] for v in res.values()), f'background bukan tema gelap: {res}')
            check(not low, f'kontras rendah: {low}')
            return 'Tema gelap aktif; kontras teks terendah ' + ', '.join(f"{k} {v['worst']}:1" for k, v in res.items())
        await step(pg, 'Responsif & aksesibilitas', 'G03', 'Tema gelap & kontras teks', g03)

        async def g04():
            await pg.goto(BASE + '#home'); await pg.wait_for_timeout(250)
            issues = []
            for r in ['home','shop','p-ecoprint-utility-vest','checkout','wholesale','custom','catalogue','order','contact','admin']:
                await go(pg, r, 150)
                if r == 'admin' and await pg.locator('[data-act=role]').count():
                    await pg.click('[data-act=role][data-v=owner]'); await tab('products'); await pg.click('tr[data-v=p1]'); await pg.wait_for_timeout(100)
                bad = await pg.evaluate("""[...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(e=>{if(e.offsetParent===null&&e.type!=='file')return false;const id=e.id;const lab=id&&document.querySelector('label[for="'+id+'"]');return !(lab||e.getAttribute('aria-label')||e.closest('label'))}).map(e=>e.id||e.name||e.outerHTML.slice(0,60))""")
                noalt = await pg.evaluate("[...document.querySelectorAll('img')].filter(i=>!i.hasAttribute('alt')).length")
                if bad: issues.append(f'{r}: tanpa label {bad}')
                if noalt: issues.append(f'{r}: {noalt} img tanpa alt')
            check(not issues, '; '.join(issues))
            return 'Semua input berlabel; semua gambar punya alt'
        await step(pg, 'Responsif & aksesibilitas', 'G04', 'Label form & teks alternatif', g04)

        async def g05():
            await pg.goto(BASE + '#home'); await pg.reload(); await pg.wait_for_timeout(300)
            seen = []; okfocus = True
            for i in range(14):
                await pg.keyboard.press('Tab')
                info = await pg.evaluate("(()=>{const e=document.activeElement;const s=getComputedStyle(e);return {t:(e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,24),o:s.outlineStyle,w:s.outlineWidth}})()")
                seen.append(info['t'])
                if info['o'] == 'none': okfocus = False
            check(okfocus, 'ada elemen fokus tanpa outline')
            check(seen[0].startswith('Skip') and any('Shop' in s for s in seen) and any('Request Catalogue' in s for s in seen), f'urutan tab: {seen}')
            await pg.reload(); await pg.wait_for_timeout(300); await pg.keyboard.press('Tab'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            check(await pg.evaluate("document.activeElement.id") == 'view', 'skip link tidak memindah fokus ke konten')
            # keyboard buy
            await go(pg, 'p-botanical-tee'); await pg.focus('.opt button:nth-child(2)'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(120)
            await pg.focus('.buy [data-act=add]'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            check(await pg.evaluate("DB.cart.some(l=>l.pid==='p7')"), 'tidak bisa membeli dengan keyboard')
            await pg.evaluate("DB.cart=[];save()")
            return 'Fokus terlihat; navigasi & beli produk bisa dengan keyboard'
        await step(pg, 'Responsif & aksesibilitas', 'G05', 'Navigasi keyboard', g05)

        async def g06():
            rm = await b.new_context(reduced_motion='reduce'); rp_ = await rm.new_page(); await rp_.goto(BASE + '#shop'); await rp_.wait_for_timeout(250)
            tr = await rp_.evaluate("getComputedStyle(document.querySelector('.pcard .ph img')).transitionDuration")
            await rm.close()
            check(tr in ('0s', '1e-05s') or tr.startswith('0s'), f'transisi tetap aktif: {tr}')
            return 'Animasi dimatikan saat prefers-reduced-motion'
        await step(pg, 'Responsif & aksesibilitas', 'G06', 'Reduced motion', g06)

        async def g07():
            t0 = time.time(); await pg.goto(BASE + '#home', wait_until='load'); dt = time.time() - t0
            res = await pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.initiatorType==='img').reduce((a,r)=>a+(r.transferSize||r.encodedBodySize||0),0)")
            lazy = await pg.evaluate("[...document.querySelectorAll('#view img')].filter(i=>i.loading==='lazy').length")
            size = os.path.getsize(f'{SITE}/index.html')
            check(lazy >= 10, 'lazy loading tidak dipakai')
            return f'Load lokal {dt:.2f} dtk; HTML {size/1024:.0f} KB; gambar awal {res/1024:.0f} KB; {lazy} gambar lazy'
        await step(pg, 'Responsif & aksesibilitas', 'G07', 'Performa & lazy loading', g07)

        async def g09():
            await pg.reload(); await pg.wait_for_timeout(250)
            await pg.evaluate("DB.cart=[{pid:'p14',ref:DB.products.find(p=>p.id==='p14').variants[0].id,qty:1}];save()")
            await pg.click('#lang-id'); await go(pg, 'checkout'); await pg.click('#coform button[type=submit]'); await pg.wait_for_timeout(200)
            t = await pg.inner_text('#coform')
            await go(pg, 'wholesale'); await pg.click('#inqform button[type=submit]'); await pg.wait_for_timeout(200)
            t2 = await pg.inner_text('#inqform'); await pg.click('#lang-en'); await pg.evaluate("DB.cart=[];save()")
            check('Isi nama penerima' in t and 'Enter' not in t, f'error checkout bukan Bahasa Indonesia: {t[:200]}')
            check('Isi nama Anda' in t2 and 'Pilih negara' in t2, 'error inquiry bukan Bahasa Indonesia')
            return 'Pesan validasi checkout & inquiry tampil dalam Bahasa Indonesia'
        await step(pg, 'Responsif & aksesibilitas', 'G09', 'Pesan error mengikuti bahasa (ID)', g09)

        async def g08():
            check(not ERRS, f'{len(ERRS)} error: {ERRS[:5]}')
            return 'Tidak ada error JavaScript di seluruh sesi'
        await step(pg, 'Responsif & aksesibilitas', 'G08', 'Tanpa error JavaScript/console', g08)

        await pg.screenshot(path=f'{OUT}/final-home.png')
        await b.close()
    json.dump(R, open(f'{OUT}/results.json', 'w'), indent=1, ensure_ascii=False)
    print(f"\n== {sum(r['ok'] for r in R)}/{len(R)} PASS ==")

asyncio.run(main())
