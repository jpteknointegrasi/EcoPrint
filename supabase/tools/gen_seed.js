// Generates supabase/seed.sql from the seed() data inside index.html,
// so the database starts with exactly the catalogue the prototype was tested with.
// Usage: node supabase/tools/gen_seed.js > supabase/seed.sql
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
const a = html.indexOf('const CARE='), b = html.indexOf('/* ---------------- STORAGE');
if (a < 0 || b < 0) throw new Error('seed block not found in index.html');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(html.slice(a, b) + '\nthis.__seed = seed();', ctx);
const D = ctx.__seed;
const q = v => v === null || v === undefined ? 'null' : "'" + String(v).replace(/'/g, "''") + "'";
const j = v => v === null || v === undefined ? 'null' : q(JSON.stringify(v)) + '::jsonb';
const out = [];
out.push('-- Seed data generated from index.html by supabase/tools/gen_seed.js — safe to re-run (upserts).');
out.push('begin;');
D.categories.forEach((c, i) => out.push(`insert into public.categories(id,name,cover,sort,visible,soon) values (${q(c.id)},${j(c.name)},${q(c.cover)},${i},${!!c.visible},${!!c.soon}) on conflict (id) do update set name=excluded.name, cover=excluded.cover, sort=excluded.sort, visible=excluded.visible, soon=excluded.soon;`));
D.products.forEach((p, i) => {
  out.push(`insert into public.products(id,slug,sku,legacy_sku,cat,status,featured,name,story,material,size,mode,sale,price,lead,care,images,pkg,catalogue,sort) values (${q(p.id)},${q(p.slug)},${q(p.sku)},${q(p.legacySku || null)},${q(p.cat)},${q(p.status)},${!!p.featured},${j(p.name)},${j(p.story)},${j(p.material)},${j(p.size)},${q(p.mode)},${q(p.sale)},${p.price || 'null'},${j(p.lead)},${q(p.care)},${j(p.images)},${j(p.pkg)},${p.catalogue !== false},${i}) on conflict (id) do nothing;`);
  if (p.fob) out.push(`insert into public.product_fob(product_id,usd,unit,label) values (${q(p.id)},${p.fob.usd},${q(p.fob.unit)},${q(p.fob.label)}) on conflict (product_id) do update set usd=excluded.usd, unit=excluded.unit, label=excluded.label;`);
  p.variants.forEach((v, k) => out.push(`insert into public.variants(id,product_id,label,stock,sort) values (${q(p.id + '-' + v.id.replace(/^v-/, ''))},${q(p.id)},${q(v.label)},${v.stock},${k}) on conflict (id) do nothing;`));
  p.pieces.forEach((x, k) => out.push(`insert into public.pieces(id,product_id,code,label,img,status,sort) values (${q(x.id)},${q(p.id)},${q(x.code)},${q(x.label)},${q(x.img)},'available',${k}) on conflict (id) do nothing;`));
});
const S = D.settings;
const kv = (k, v) => out.push(`insert into public.site_settings(key,value) values (${q(k)},${j(v)}) on conflict (key) do nothing;`);
kv('content', D.content);
kv('contact', D.contact);
kv('settings', { reserveMin: S.reserveMin, zones: S.zones, pay: S.pay, intlCheckout: false });
kv('private', { notifyOk: true, paySimulator: true });
kv('catalogue_meta', D.catalogueMeta);
out.push('commit;');
process.stdout.write(out.join('\n') + '\n');
