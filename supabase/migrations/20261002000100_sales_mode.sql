-- =====================================================================
-- Sales mode: "Mode Katalog" (default) vs "Mode Jualan"
--   settings.salesLive = false → public site shows every product as
--     "Harga atas permintaan", no retail prices leave the database and
--     create_order refuses. Buyers go through WhatsApp / inquiry forms.
--   settings.salesLive = true  → products follow their own sale type
--     (retail / mto / quote) and checkout is open.
-- Only the Owner can switch the mode. Product data is never changed.
-- =====================================================================

update public.site_settings
   set value = value || '{"salesLive": false}'::jsonb
 where key = 'settings' and not (value ? 'salesLive');

-- Public snapshot: hide prices and checkout while in catalogue mode
create or replace function public.get_public_site() returns jsonb
language plpgsql security definer set search_path = public as $$
declare c jsonb := coalesce(_setting('contact'), '{}'::jsonb); s jsonb := coalesce(_setting('settings'), '{}'::jsonb);
        ap int := nullif(c->>'activePhone', '')::int;
        live boolean := coalesce((s->>'salesLive')::boolean, false);
begin
  perform _expire_reservations();
  return jsonb_build_object(
    'categories', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'name', name, 'cover', cover, 'visible', visible, 'soon', soon) order by sort)
                  from categories where visible), '[]'::jsonb),
    'products',   coalesce((select jsonb_agg(case when live then _product_json(p, false)
                                                  else _product_json(p, false) || jsonb_build_object('sale', 'quote', 'price', null, 'lead', null) end
                                             order by p.sort, p.id)
                            from products p where p.status = 'published'), '[]'::jsonb),
    'content',    coalesce(_setting('content'), '{}'::jsonb),
    'contact',    jsonb_build_object(
                    'email', c->'email', 'instagram', c->'instagram',
                    'phones', case when ap is null then '[]'::jsonb else jsonb_build_array(c->'phones'->ap) end,
                    'activePhone', case when ap is null then null else 0 end,
                    'addressConfirmed', coalesce((c->>'addressConfirmed')::boolean, false),
                    'address', case when coalesce((c->>'addressConfirmed')::boolean, false) then c->'address' else null end,
                    'legal', coalesce((select jsonb_agg(l) from jsonb_array_elements(c->'legal') l where (l->>'verified')::boolean), '[]'::jsonb)),
    'settings',   jsonb_build_object('reserveMin', s->'reserveMin', 'zones', s->'zones', 'pay', s->'pay', 'intlCheckout', false,
                                     'salesLive', live,
                                     'paySimulator', coalesce((_setting('private')->>'paySimulator')::boolean, false)),
    'catalogueMeta', coalesce(_setting('catalogue_meta'), '{}'::jsonb));
end $$;

-- Checkout: keep the existing logic, refuse while in catalogue mode
alter function public.create_order(jsonb) rename to _create_order_core;
revoke execute on function public._create_order_core(jsonb) from public, anon, authenticated;

create or replace function public.create_order(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if not coalesce((_setting('settings')->>'salesLive')::boolean, false) then
    return jsonb_build_object('ok', false, 'errs', jsonb_build_object('cart',
      _t('Online checkout is not open yet. Please contact us on WhatsApp to order.',
         'Pembelian online belum dibuka. Silakan hubungi kami via WhatsApp untuk memesan.')));
  end if;
  return _create_order_core(p);
end $$;
revoke execute on function public.create_order(jsonb) from public;
grant execute on function public.create_order(jsonb) to anon, authenticated;

-- Admin settings: accept salesLive (Owner only)
create or replace function public.admin_save_settings(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare s jsonb := coalesce(_setting('settings'), '{}'::jsonb); z jsonb; nz jsonb := '[]'::jsonb; upd jsonb;
begin
  perform _guard('settings');
  perform _need('settings', 'Pengaturan transaksi');
  if p ? 'salesLive' and jsonb_typeof(p->'salesLive') = 'boolean'
     and (p->>'salesLive')::boolean is distinct from coalesce((s->>'salesLive')::boolean, false) then
    if _role() <> 'owner' then
      raise exception '403 · Hanya Owner yang dapat mengubah mode penjualan.' using errcode = '42501';
    end if;
    s := s || jsonb_build_object('salesLive', (p->>'salesLive')::boolean);
  end if;
  for z in select * from jsonb_array_elements(coalesce(s->'zones', '[]'::jsonb)) loop
    select e into upd from jsonb_array_elements(coalesce(p->'zones', '[]'::jsonb)) e where e->>'id' = z->>'id';
    if upd is not null then
      z := z || jsonb_build_object('rate', greatest(0, coalesce(nullif(upd->>'rate', '')::int, (z->>'rate')::int)),
                                   'on', coalesce((upd->>'on')::boolean, (z->>'on')::boolean));
    end if;
    nz := nz || z;
  end loop;
  update site_settings set value = s || jsonb_build_object('zones', nz,
           'reserveMin', least(240, greatest(1, coalesce(nullif(p->>'reserveMin', '')::int, (s->>'reserveMin')::int, 15))))
  where key = 'settings';
  if p ? 'notifyOk' or p ? 'paySimulator' then
    insert into site_settings(key, value) values ('private', '{}') on conflict do nothing;
    update site_settings set value = value || jsonb_strip_nulls(jsonb_build_object('notifyOk', p->'notifyOk', 'paySimulator', p->'paySimulator')) where key = 'private';
  end if;
  return jsonb_build_object('ok', true);
end $$;
