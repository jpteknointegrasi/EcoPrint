# Blueprint Website Niken Ecoprint
## PT. Manna Borneo Persada

Versi 1 — 1 Oktober 2026. Dokumen perencanaan untuk desain, pembangunan, dan pengujian; bukan website yang sudah beroperasi.

## 1. Konsep dan tujuan

Website menggabungkan brand editorial premium, toko online retail, dan kanal penjualan B2B internasional. Pengunjung dapat mengenal brand, melihat produk, membeli produk yang siap dijual, atau meminta penawaran untuk wholesale, ekspor, custom, dan private label.

Tagline utama: **LEAVES TELL THE STORY OF BORNEO**.

Supporting line: **Nature-inspired. Handcrafted in Indonesia. Made for the world.**

USP: cerita botanical Borneo, motif alami yang unik, kerajinan Indonesia, kemampuan mengubah tekstil menjadi produk, serta pengembangan custom/private label. Dokumen perusahaan juga menekankan pemberdayaan perajin perempuan; tampilkan melalui cerita dan foto asli yang disetujui perusahaan.

CSS mengatur warna, huruf, jarak, dan tampilan. CMS mengatur konten serta data produk. Database menyimpan produk, stok, pesanan, dan inquiry. Backend menjalankan transaksi serta pemeriksaan hak akses. Website membutuhkan seluruh bagian ini agar perubahan admin benar-benar tersimpan dan transaksi berjalan.

## 2. Dasar penyusunan dan data yang perlu dikonfirmasi

Sumber: brief pengguna; screenshot website; profil perusahaan PDF 14 halaman; katalog produk PDF 12 halaman. Informasi dari katalog adalah bahan awal, bukan otomatis ketentuan penjualan terbaru.

| Informasi | Dasar dari dokumen | Perlakuan pada website |
|---|---|---|
| Perusahaan dan brand | PT. Manna Borneo Persada; Niken Ecoprint | Identitas utama |
| Lokasi | Kalimantan Timur; profil menyebut Balikpapan | Alamat lengkap dikonfirmasi sebelum publikasi |
| Email | mannaborneopersada@gmail.com | Kandidat kontak utama |
| Instagram | nikenecoprint | Gunakan tautan akun yang diverifikasi |
| Telepon | Katalog: +6281545457999; profil menampilkan nomor berbeda | Jangan memilih satu secara diam-diam; owner menetapkan nomor aktif |
| Kapasitas | Profil 200–300 pcs/bulan; katalog fabric 300, fashion 100, bags 200 pcs tanpa periode yang jelas | Konfirmasi per kategori, periode, dan apakah kapasitas gabungan; jangan dijumlahkan |
| MOQ | Beberapa produk 1 pcs/pair; fabric dan fashion tertentu flexible | Atur per produk dan jalur retail/B2B |
| SKU | SKU men's dan women's wear sama pada katalog | Beri SKU unik setelah persetujuan; simpan kode lama sebagai referensi |
| Klaim bahan/dye | Katalog menyebut 100% natural plant-based dyes; bahan campuran termasuk kulit | Konfirmasi per produk, komponen, dan proses; jangan menerapkan klaim global tanpa dasar |
| Legalitas | Profil mencantumkan NIB, HKI dan business certificates | Tampilkan status/nomor hanya setelah bukti diperiksa; bukan klaim sertifikasi internasional |
| Pasar global | Profil menyebut target Singapore, Japan, Australia, Europe, USA | Sebut target market, bukan riwayat ekspor yang sudah terjadi |
| Home & Lifestyle | Ada pada brief, belum ada spesifikasi produk lengkap pada katalog | Kategori dapat disiapkan sebagai coming soon tanpa produk fiktif |

## 3. Model penjualan

| Jalur | Produk/permintaan | Tombol utama | Hasil |
|---|---|---|---|
| Retail ready stock | Barang tersedia dengan foto, harga, ukuran dan stok jelas | Add to Cart / Buy Now | Checkout dan pembayaran |
| Made to order | Produk dengan spesifikasi serta lead time yang sudah pasti | Order Made to Order | Checkout jika kapasitas dan ketentuan siap; selain itu inquiry |
| Wholesale/export | Jumlah besar, negara tujuan, sampel, permintaan bisnis | Request Wholesale Quote | Inquiry → penawaran → persetujuan → invoice → pembayaran |
| Custom/private label | Desain, bahan, branding, kemasan khusus | Start a Custom Project | Brief → evaluasi → sampel bila perlu → penawaran → produksi |

Retail domestik menjadi jalur checkout awal. Pembeli internasional tetap dapat memilih produk dan mengirim inquiry dengan negara tujuan. Checkout internasional diaktifkan setelah pembayaran, negara layanan, biaya kirim, dan ketentuan impor disiapkan. Permintaan ekspor tetap dapat diterima sejak peluncuran.

Harga USD pada katalog berjudul FOB tidak menjadi harga retail otomatis. Basis penawaran, mata uang, pelabuhan, dan komponen biaya harus ditetapkan pada quotation; ketentuan aktual ditinjau saat implementasi.

## 4. Struktur halaman

| Halaman | Isi dan fungsi |
|---|---|
| Home | Hero, koleksi unggulan, USP, cerita, proses, B2B, craftsmanship dan CTA |
| Shop / Collections | Semua produk, pencarian, filter, kategori, sortir |
| Product Detail | Foto, cerita, spesifikasi, varian, stok, harga, perawatan dan pembelian/inquiry |
| Our Story | Perusahaan, brand DNA, Borneo, perajin perempuan, visi/misi |
| Our Process | Select → Arrange → Transfer → Reveal → Finish → Create; foto proses asli |
| Wholesale & Export | Tipe mitra, MOQ per produk, sampel, alur pemesanan, packaging/shipping, inquiry |
| Custom & Private Label | Kemampuan layanan, batasan, proses pengembangan, formulir project |
| Catalogue | Katalog digital dari database; PDF versi terbaru dan tanggal pembaruan |
| Journal / Gallery | Botanical, produk, kegiatan dan pameran dengan judul, tanggal serta keterangan |
| Contact | Kontak terverifikasi, lokasi dan formulir |
| Cart / Checkout | Barang, alamat, pengiriman, pembayaran dan ringkasan biaya |
| Order Status | Status pesanan melalui login atau tautan aman |
| Policies / FAQ | Perawatan, variasi motif, pengiriman, retur, privasi dan syarat pembelian |
| Admin | Dashboard CMS, produk, stok, pesanan, inquiry, konten dan pengaturan |

Navigasi desktop: logo; Shop; Our Story; Process; Wholesale & Export; Custom; Contact. Tombol Request Catalogue dan ikon Cart. Mobile: menu ringkas, akses cart jelas, dan tombol pembelian pada detail produk tetap mudah dijangkau.

## 5. Rancangan homepage

1. **Hero:** foto asli produk yang dikenakan atau dipakai; tagline utama; satu paragraf pendek; Explore Collection dan Wholesale & Export. Hindari teks bertumpuk pada bagian foto yang ramai.
2. **Featured Product:** Ecoprint Vest sebagai kandidat dari profil, dengan foto asli, cerita singkat dan View Product. Admin dapat mengganti produk unggulan.
3. **Shop by Collection:** Fabric; Fashion & Vest; Bags; Wallets & Accessories; Footwear; Home & Lifestyle jika tersedia.
4. **Where Nature Becomes Art:** cerita singkat disandingkan foto craftsmanship.
5. **What Makes Us Different:** enam USP brief, disajikan ringkas dalam grid responsif.
6. **From Leaf to Story:** enam langkah ringkas; halaman proses memuat penjelasan lebih lengkap dan foto tahapan produksi dari profil.
7. **Crafted for Your Brand:** wholesale, export, custom, private label dan sample inquiry.
8. **Craftsmanship & Social Impact:** bukti visual perajin dan proses; klaim terukur hanya setelah ada data.
9. **Gallery / Exhibitions:** dokumentasi asli dengan metadata dan izin publikasi.
10. **FAQ:** variasi motif, MOQ, waktu produksi, custom, perawatan dan shipping.
11. **Final CTA:** Request Catalogue, Request a Quote, Contact Us.
12. **Footer:** perusahaan, brand, Indonesia, navigasi, kebijakan dan kanal kontak.

Seluruh 13 bagian brief tetap tercakup melalui homepage dan halaman pendukung. Visi/misi lengkap ditempatkan di Our Story agar homepage tidak terlalu panjang. Narasi sustainability memakai pendekatan hati-hati sesuai brief, tanpa badge atau sertifikasi rekaan.

## 6. Sistem desain dan CSS

Palet usulan: ivory #F7F4EC, deep forest #203024, muted olive #68734A, natural brown #805E43, charcoal #282B25. Ini arah desain, bukan warna logo resmi. Logo asli dipakai dengan proporsi utuh.

Judul menggunakan serif elegan; isi menggunakan sans-serif bersih. Pasangan font final dipilih dengan lisensi penggunaan website yang sesuai. Body 16–18 px, kontras teks terbaca, ukuran heading responsif. Layout lebar maksimum sekitar 1.200–1.280 px; whitespace luas; card dengan sudut lembut; bayangan minimal.

Foto produk menjadi fokus. Foto detail motif dan bahan melengkapi foto penggunaan. Thumbnail produk konsisten; detail produk dapat menampilkan rasio foto asli. Hindari foto AI sebagai representasi barang yang akan diterima pembeli.

Komponen CSS: Header, Button, ProductCard, CategoryCard, Price, StockBadge, Gallery, VariantSelector, InquiryForm, CartItem, FAQ, Footer. Gunakan token terpusat untuk warna, font, spacing, radius, dan ukuran agar semua halaman konsisten.

CMS menyediakan pengaturan tema terbatas: logo, palet yang disetujui, banner, dan urutan section. Admin tidak perlu mengedit CSS atau kode. Animasi ringan, mendukung reduced motion, tanpa mengganggu checkout. Navigasi keyboard, label form, teks alternatif gambar, dan pesan error harus tersedia.

## 7. Kategori dan data produk awal

| Kategori | Data awal dari dokumen | Hal yang belum lengkap |
|---|---|---|
| Ecoprint Fabric | NE-FAB-EC-001; silk/cotton; MOQ flexible | Lebar kain, unit stok meter/piece, harga per bahan |
| Fashion | Tunik, blouse, men's shirt, bomber, vest; M/L/XL atau allsize | SKU unik, size chart cm, komposisi bahan per model |
| Bags | NE-BAG-EC-001: clutch kulit sapi 22×8×13 cm; NE-BAG-EC-002 kulit dan NE-BAG-EC-003 cotton, panjang 29 cm | Dimensi lengkap dua model, stok aktual, harga retail |
| Wallets & Accessories | NE-ACC-WL-001; contoh dompet 19×10 cm dan 11,5×9,5×1,5 cm; scarf/pashmina | Pisahkan model menjadi SKU unik, material serta ukuran scarf |
| Footwear | Sneakers ukuran 37–43; women's leather shoes NE-FTW-FS-001 ukuran 37–40; MOQ 1 pair | Size chart, material tiap komponen, SKU sneakers |
| Home & Lifestyle | Arah pengembangan dari brief | Produk, foto, spesifikasi dan harga belum tersedia |

Harga referensi FOB dari halaman terakhir katalog: blouse/tunik USD75; shirt USD80; bomber USD125; tote USD65; wallet USD28; scarf/pashmina USD35; canvas shoes USD70; women's shoes USD75; fabric USD40/meter. Simpan sebagai referensi internal bertanggal sampai owner memastikan validitas, basis harga, dan pemetaan SKU. Jangan ditampilkan sebagai harga checkout final.

## 8. Halaman detail produk

Urutan: breadcrumb; galeri; nama dan cerita; harga retail atau Request Price; pilihan ukuran/bahan/motif; status stock; jumlah; Add to Cart atau Request Quote; spesifikasi; perawatan; pengiriman; ketentuan motif dan retur; produk terkait.

Data wajib: product ID, SKU unik, nama EN/ID, slug, kategori, deskripsi, story/USP, bahan, dimensi/size chart, berat dan dimensi paket, gambar utama serta galeri, jenis motif, varian, unit penjualan, stok, status, harga dan mata uang, mode penjualan, MOQ B2B, custom options, lead time, care instructions, SEO title dan description.

Data tambahan: lining, closure, kompartemen, asal produksi yang terverifikasi, fitur bahan, catalogue visibility, harga bertingkat untuk B2B jika sudah disetujui.

Setiap produk menggunakan satu dari dua mode motif:

- **Exact piece:** foto adalah barang yang dijual, ID piece unik, stok umumnya satu; barang yang sudah terjual tidak dapat dibeli lagi.
- **Pattern family / made to order:** foto merupakan contoh; pembeli menyetujui bahwa botanical pattern dan warna dapat bervariasi. Pemilihan foto barang aktual sebelum kirim dapat menjadi langkah tambahan jika ditawarkan.

Kategori saja tidak cukup untuk mengatur one-of-a-kind stock. Sistem harus dapat membedakan SKU model, variant ukuran/bahan, dan piece fisik.

## 9. CMS admin

| Modul | Kemampuan admin |
|---|---|
| Dashboard | Pesanan baru, inquiry, stok rendah, pendapatan pembayaran terkonfirmasi |
| Products | Tambah, edit, duplikasi, preview, publish, unpublish, archive, restore |
| Variants & Pieces | SKU, ukuran, bahan, motif, foto exact piece, stok dan reservasi |
| Categories | Tambah/ubah kategori, cover, urutan, visibilitas |
| Media | Upload foto/video, alt text, urutan, kompresi dan pengecekan file |
| Pricing | Harga retail, mata uang, harga B2B internal, tier dan periode berlaku |
| Orders | Status pembayaran, pemenuhan, catatan, packing, tracking dan retur |
| Inquiries | Catalogue, wholesale, sample, export dan custom; PIC serta status tindak lanjut |
| Quotations | Nomor/version, item, jumlah, harga, currency, validity, shipping basis dan persetujuan |
| Content | Hero, cerita, process, USP, gallery, FAQ, footer, kontak dan SEO |
| Catalogue | Pilih produk, susun urutan, preview dan ekspor PDF dari data produk |
| Reports | Penjualan per produk, inquiry per tipe, ekspor CSV dengan akses terbatas |
| Users & Settings | Role, bahasa, area kirim, metode bayar, kebijakan dan audit log |

Alur perubahan: edit → save draft → preview → publish. Perubahan menjadi data permanen di server. Produk yang pernah dipesan diarsipkan agar riwayat transaksi utuh. Hapus permanen hanya untuk draft yang tidak memiliki transaksi. Detail nama, harga, bahan dan varian dalam pesanan disimpan sebagai snapshot agar edit produk tidak mengubah pesanan lama.

Role: Owner memiliki akses penuh; Content Admin mengelola konten dan produk; Sales mengelola inquiry dan quotation; Fulfillment mengelola packing/tracking. Izin dicek di backend, bukan hanya menyembunyikan tombol. Audit log mencatat siapa, kapan, dan perubahan penting.

## 10. Alur checkout dan stok

1. Pembeli memilih piece/variant tersedia dan jumlah.
2. Cart menghitung harga dari server; checkout memeriksa stok, alamat, wilayah layanan, ongkir dan total.
3. Sistem membuat order pending dan reservasi stok dengan waktu kedaluwarsa yang dikonfigurasi.
4. Pembeli membayar melalui metode yang sudah diintegrasikan.
5. Backend memverifikasi konfirmasi pembayaran dari penyedia; callback berulang tidak boleh membuat pembayaran/order ganda.
6. Pembayaran valid memfinalisasi penjualan; dashboard menerima order Paid.
7. Admin memproses, mengirim dan memasukkan tracking.
8. Pembeli menerima konfirmasi dan dapat melihat status aman.

Expired/failed/cancelled melepaskan reservasi. Jika pembayaran datang terlambat setelah reservasi habis, sistem melakukan pemeriksaan stok dan antrean rekonsiliasi; tidak boleh otomatis menjanjikan barang yang telah terjual. Dua pembeli bersamaan tidak dapat membeli exact piece yang sama. Refund dan retur memiliki catatan tersendiri; barang direstok hanya setelah diperiksa.

Status pembayaran: pending, paid, failed, expired, partially refunded, refunded. Status fulfillment: unfulfilled, processing, shipped, delivered, cancelled, returned. Pisahkan kedua status ini.

Guest checkout tersedia. Data harga, diskon, ongkir dan jumlah akhir divalidasi server. WhatsApp membawa referensi produk/order tetapi pencatatan transaksi tetap pada sistem.

## 11. Inquiry wholesale, export dan custom

Form: nama, perusahaan, email, WhatsApp opsional, negara, tipe bisnis, jenis inquiry, produk/SKU, jumlah dan unit, ukuran/bahan, target waktu, branding, packaging, tujuan pengiriman, catatan dan lampiran referensi. Persetujuan privasi tersedia; marketing consent terpisah dan opsional.

Inquiry tersimpan walaupun notifikasi email gagal. Beri nomor inquiry dan halaman konfirmasi. Status: New → Assigned → In Discussion → Quotation Sent → Approved → In Production → Completed; alternatif Lost/Cancelled.

Quotation memuat spesifikasi, varian motif, MOQ, jumlah, biaya sampel/custom, lead time beserta titik mulainya, termin pembayaran, masa berlaku, pengiriman, kemasan dan pengecualian biaya. Harga tidak otomatis sama dengan retail. Lead time tidak diisi angka rekaan; per produk/order berdasarkan kesiapan produksi.

## 12. Katalog internasional

Database produk menjadi sumber bersama website dan katalog agar nama, SKU, bahan serta spesifikasi konsisten. Katalog memiliki tanggal, versi dan bahasa. Ekspor PDF dapat dilakukan dari pilihan produk yang disetujui; proses pembuatan PDF harus menjadi fitur implementasi yang diuji.

Urutan: cover & brand story; fabrics; bags/accessories; fashion; footwear; home/lifestyle jika sudah ada; custom/private label; wholesale; MOQ/lead time; packaging/shipping; how to order; buyer inquiry.

Per produk: Product Name; Story/USP; SKU; Material; Size; Available Colors/Patterns; MOQ; Customization; Care; Wholesale Inquiry. Cantumkan exact piece atau representative pattern. Harga publik, harga retail dan penawaran B2B dapat memiliki aturan visibilitas berbeda.

Request Catalogue cukup memakai nama/email, perusahaan dan negara opsional; jangan memakai form custom yang panjang untuk unduhan katalog biasa.

## 13. Arsitektur sistem dan database

Lapisan: storefront responsif → backend/API → database; CMS mengakses backend yang sama dengan izin admin. Media tersimpan pada penyimpanan file; layanan eksternal untuk pembayaran, pengiriman dan notifikasi dihubungkan melalui backend. Pilihan platform final ditetapkan setelah anggaran, hosting dan integrasi disepakati; blueprint tidak mengunci framework.

| Entitas | Fungsi |
|---|---|
| products, categories, product_categories | Master model produk dan kategori |
| variants, pieces, product_media | Ukuran/bahan, barang unik dan foto |
| prices, inventory_movements, reservations | Harga, mutasi stock dan penahanan sementara |
| orders, order_items, payments | Pesanan, snapshot item dan pembayaran |
| shipments, refunds | Pengiriman dan pengembalian pembayaran |
| inquiries, inquiry_items, quotations, quotation_items | Pipeline B2B dan versi penawaran |
| customers, addresses | Data pembeli sesuai kebutuhan |
| pages, sections, translations, media | Konten CMS dan bahasa |
| catalogue_versions | Versi dan daftar produk katalog |
| admin_users, roles, audit_logs | Akses admin dan jejak perubahan |

Relasi: produk mempunyai banyak variant; variant dapat mempunyai banyak exact piece; order mempunyai banyak order item; order item menyimpan variant/piece dan snapshot; inquiry dapat mempunyai beberapa quotation version. SKU unik, relasi transaksi dan constraint stok ditegakkan di database.

## 14. Bahasa, mata uang dan pengiriman

English menjadi bahasa utama untuk buyer internasional; Bahasa Indonesia tersedia untuk retail lokal. CMS menyediakan field terpisah EN/ID, bukan mencampurkan dua bahasa dalam satu deskripsi. Terjemahan yang belum siap memakai fallback yang jelas.

IDR menjadi kandidat currency checkout domestik. USD untuk quotation B2B atau tampilan referensi yang diberi label. Menampilkan USD tidak berarti pembayaran USD tersedia. Harga katalog dapat berupa harga tetap tersendiri; jangan memakai konversi kurs yang tidak dijelaskan.

Shipping domestik membutuhkan lokasi asal, berat/dimensi paket dan wilayah layanan. Export inquiry meminta negara/kode pos dan quantity untuk menghitung quotation. Packaging retail, gift dan bulk diatur berbeda. Negara layanan, pajak, bea masuk dan ketentuan pengiriman ditetapkan sebelum checkout lintas negara diaktifkan.

## 15. Keamanan, kualitas dan operasional

HTTPS; login admin aman; MFA bila platform mendukung; pembatasan percobaan login; otorisasi server; validasi input; pembatasan file upload; rahasia integrasi tidak masuk browser; signed payment webhook; backup database/media dan uji restore; audit perubahan; form spam protection. Data pembeli dan inquiry tidak menjadi konten publik.

Foto dioptimasi dengan ukuran responsif; lazy loading selain hero; page title/description; sitemap; canonical; metadata produk sesuai data aktual. Product schema hanya untuk barang/harga yang benar-benar tersedia; tidak membuat rating palsu. Error checkout dan webhook dicatat untuk pemantauan.

Dashboard analytics: kunjungan produk, add-to-cart, checkout, paid order, catalogue request, qualified inquiry dan quotation conversion. Klik WhatsApp dihitung sebagai klik, bukan penjualan selesai. Revenue berasal dari pembayaran terverifikasi dengan refund diperhitungkan.

## 16. Tahapan pembangunan

| Tahap | Deliverable | Syarat selesai |
|---|---|---|
| 1. Data & keputusan | Produk/SKU, harga retail, foto, kontak, stock mode, kebijakan | Owner menyetujui data publik dan aturan transaksi |
| 2. Desain | Homepage, shop, detail, checkout, inquiry, admin pada desktop/mobile | Tampilan dan alur dapat ditinjau |
| 3. Fondasi CMS | Database, login/role, produk, media, konten, stock | CRUD tersimpan permanen dan izin diuji |
| 4. Retail & B2B | Cart, payment, shipping, order, inquiry/quotation | Uji end-to-end berhasil di lingkungan uji |
| 5. Konten & katalog | EN/ID, katalog versi awal, SEO, kebijakan | Tidak ada placeholder atau informasi belum disetujui |
| 6. Peluncuran | Domain, integrasi live, backup, monitoring, pelatihan | Checklist penerimaan lulus dan konfigurasi live benar |
| 7. Pengembangan | Checkout internasional, tier B2B, katalog PDF otomatis lanjutan | Integrasi dan operasi siap |

Prioritas peluncuran: CMS produk/konten, toko retail domestik, pembayaran, stok, pengiriman, inquiry internasional/custom, katalog PDF awal, dan halaman kebijakan. B2B tetap beroperasi melalui quotation; kalkulasi ekspor otomatis dan portal buyer dapat menyusul.

## 17. Uji penerimaan wajib

- Admin menambah produk beserta foto, SKU, harga dan stock; publish muncul di shop; draft tetap tidak publik.
- Edit produk tersimpan setelah logout/login dan tidak mengubah snapshot order terdahulu.
- Archive menghilangkan produk dari pembelian tanpa menghapus histori; draft tanpa transaksi dapat dihapus.
- Admin terbatas tidak dapat mengubah role/harga atau membaca data di luar izinnya melalui API.
- Exact piece stok satu tidak oversold saat dua checkout bersamaan; reservasi expired kembali tersedia.
- Pembayaran sukses/gagal/expired dan callback duplikat menghasilkan status serta stok yang benar.
- Total pembayaran sesuai order server; perubahan harga dari browser tidak diterima.
- Varian habis dan wilayah kirim tanpa layanan tidak dapat checkout.
- Inquiry tersimpan dengan nomor, item dan PIC; notifikasi dapat dicoba ulang.
- Quote memakai mata uang/basis harga sendiri; harga FOB tidak terbaca sebagai harga retail otomatis.
- Semua CTA bekerja; EN/ID, mobile, keyboard, form error dan tracking dapat digunakan.
- PDF katalog sesuai produk terpilih dan versi; backup dapat dipulihkan.

## 18. Data yang harus disiapkan owner

Logo asli dan hak penggunaan foto; nomor WhatsApp/alamat resmi; daftar SKU final; foto exact piece bila berlaku; bahan/dimensi/size chart; harga retail dan B2B terpisah; stock awal; MOQ; kapasitas serta lead time; care instructions; rekening/provider pembayaran; alamat asal kirim dan packaging; kebijakan retur untuk ready stock/custom; bukti legalitas/klaim yang akan dipublikasikan.

Keputusan yang belum ditetapkan tidak perlu menghambat desain, tetapi harus selesai sebelum fitur terkait digunakan untuk transaksi live. Blueprint ini menyediakan spesifikasi untuk membangun website yang menarik dan dapat dikelola admin; pelaksanaan integrasi dan peluncuran merupakan pekerjaan berikutnya.
