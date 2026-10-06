-- =====================================================================
-- Official catalogue & price list (Niken Ecoprint catalogue, Aug 2026)
--   * The owner confirmed the FOB export prices as official, so FOB
--     references are now public (shown on product pages and in the
--     printed catalogue). FOB is never used as a retail/checkout price.
--   * Data aligned with the official catalogue: FOB for the RTW vests
--     (NE-RTW-TN-001 group) and the men's tee (NE-RTW-MS-001 group),
--     women's leather shoes size 37–40, catalogue version 1.2 (EN/ID).
-- =====================================================================

create or replace function public._product_json(p public.products, internal boolean) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'id', p.id, 'slug', p.slug, 'sku', p.sku, 'legacySku', coalesce(p.legacy_sku, ''), 'cat', p.cat,
    'status', p.status, 'featured', p.featured, 'name', p.name, 'story', p.story, 'material', p.material,
    'size', p.size, 'mode', p.mode, 'sale', p.sale, 'price', p.price, 'lead', p.lead, 'care', p.care,
    'images', p.images, 'pkg', p.pkg, 'catalogue', p.catalogue,
    'hasOrders', case when internal then p.has_orders else false end,
    'rev', case when internal then p.rev else null end,
    'fob', (select jsonb_build_object('usd', f.usd, 'unit', f.unit, 'label', f.label) from product_fob f where f.product_id = p.id),
    'variants', coalesce((select jsonb_agg(jsonb_build_object(
                  'id', v.id, 'label', v.label,
                  'stock', case when internal then v.stock else greatest(0, v.stock - v.reserved) end,
                  'reserved', case when internal then v.reserved else 0 end) order by v.sort, v.label)
                from variants v where v.product_id = p.id), '[]'::jsonb),
    'pieces', coalesce((select jsonb_agg(jsonb_build_object(
                  'id', x.id, 'code', x.code, 'label', x.label, 'img', x.img, 'status', x.status,
                  'heldBy', case when internal then x.held_by else null end) order by x.sort, x.code)
                from pieces x where x.product_id = p.id), '[]'::jsonb)
  ) $$;

insert into public.product_fob(product_id, usd, unit, label)
select v.id, v.usd, v.unit, v.label
  from (values ('p1', 75::numeric, 'pc', 'Blouse/Tunik'),
               ('p2', 75::numeric, 'pc', 'Blouse/Tunik'),
               ('p7', 80::numeric, 'pc', 'Shirt')) as v(id, usd, unit, label)
 where exists (select 1 from public.products p where p.id = v.id)
on conflict (product_id) do update set usd = excluded.usd, unit = excluded.unit, label = excluded.label;

update public.products set legacy_sku = 'NE-RTW-TN-001' where id = 'p1' and legacy_sku is null;

update public.products set size = '{"en":"EU 37–40","id":"EU 37–40"}'::jsonb
 where id in ('p17', 'p22') and size->>'en' = 'EU 37–41';

update public.site_settings
   set value = value || '{"version":"1.2","date":"2026-10-06","lang":"EN/ID"}'::jsonb
 where key = 'catalogue_meta';
