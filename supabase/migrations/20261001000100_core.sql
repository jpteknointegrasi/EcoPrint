-- =====================================================================
-- Niken Ecoprint — core schema (Blueprint v1 §9–§13)
-- Every table is closed to the browser. The website talks to the
-- database only through the functions at the bottom of this file, which
-- recalculate prices, lock stock rows and check the admin's role.
-- =====================================================================
create extension if not exists pgcrypto;

-- ---------- staff & audit ----------
create table if not exists public.admin_users (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  role       text not null check (role in ('owner','content','sales','fulfillment')),
  name       text,
  created_at timestamptz not null default now()
);
create table if not exists public.audit_logs (
  id      bigserial primary key,
  at      timestamptz not null default now(),
  user_id uuid,
  role    text,
  perm    text,
  descr   text
);

-- ---------- catalogue ----------
create table if not exists public.categories (
  id      text primary key,
  name    jsonb not null,
  cover   text,
  sort    int not null default 0,
  visible boolean not null default true,
  soon    boolean not null default false
);
create table if not exists public.products (
  id          text primary key,
  slug        text not null unique,
  sku         text not null unique,
  legacy_sku  text,
  cat         text not null references public.categories(id),
  status      text not null default 'draft' check (status in ('draft','published','archived')),
  featured    boolean not null default false,
  name        jsonb not null,
  story       jsonb not null default '{}'::jsonb,
  material    jsonb not null default '{}'::jsonb,
  size        jsonb not null default '{}'::jsonb,
  mode        text not null check (mode in ('exact','pattern')),
  sale        text not null check (sale in ('retail','mto','quote')),
  price       integer check (price is null or price > 0),
  lead        jsonb,
  care        text not null default 'textile' check (care in ('textile','leather')),
  images      jsonb not null default '[]'::jsonb,
  pkg         jsonb not null default '{"w":400,"dim":"30×25×4 cm"}'::jsonb,
  catalogue   boolean not null default true,
  has_orders  boolean not null default false,
  rev         jsonb,                       -- unpublished draft of a published product
  sort        int not null default 0,
  updated_at  timestamptz not null default now()
);
-- internal FOB reference prices: never exposed to the public catalogue
create table if not exists public.product_fob (
  product_id text primary key references public.products(id) on delete cascade,
  usd        numeric(10,2),
  unit       text,
  label      text
);
create table if not exists public.variants (
  id         text primary key,
  product_id text not null references public.products(id) on delete cascade,
  label      text not null,
  stock      int not null default 0 check (stock >= 0),
  reserved   int not null default 0 check (reserved >= 0),
  sort       int not null default 0,
  check (reserved <= stock),
  unique (product_id, label)
);
create table if not exists public.pieces (
  id         text primary key,
  product_id text not null references public.products(id) on delete cascade,
  code       text not null unique,
  label      text,
  img        text,
  status     text not null default 'available' check (status in ('available','reserved','sold')),
  held_by    text,
  sort       int not null default 0
);
create table if not exists public.inventory_movements (
  id     bigserial primary key,
  at     timestamptz not null default now(),
  sku    text,
  ref    text,
  delta  int,
  reason text,
  ref_no text
);

-- ---------- orders ----------
create sequence if not exists public.order_seq;
create sequence if not exists public.inquiry_seq;
create sequence if not exists public.quote_seq;
create table if not exists public.orders (
  no             text primary key,
  created_at     timestamptz not null default now(),
  customer       jsonb not null,
  email          text not null,
  zone           text not null,
  pay            text not null default 'pending' check (pay in ('pending','paid','failed','expired','partially refunded','refunded')),
  ful            text not null default 'unfulfilled' check (ful in ('unfulfilled','processing','shipped','delivered','cancelled','returned')),
  method         text,
  sub            int not null,
  ship           int not null,
  total          int not null,
  client_total   int,
  price_tampered boolean not null default false,
  expires_at     timestamptz not null,
  held           boolean not null default true,
  tracking       text not null default '',
  notes          text not null default '',
  recon          boolean not null default false,
  restocked      boolean not null default false,
  log            jsonb not null default '[]'::jsonb
);
create index if not exists orders_email_idx on public.orders (email);
create index if not exists orders_pending_idx on public.orders (expires_at) where pay = 'pending' and held;
-- order items are a snapshot: editing a product later never changes them
create table if not exists public.order_items (
  id         bigserial primary key,
  order_no   text not null references public.orders(no) on delete cascade,
  product_id text references public.products(id),
  ref        text not null,
  qty        int not null check (qty > 0),
  sku        text not null,
  name       text not null,
  variant    text,
  unit       int not null,
  img        text,
  mode       text,
  sale       text,
  lead       text
);
create table if not exists public.payment_events (
  event_id    text primary key,              -- provider event id: a repeat is ignored
  order_no    text,
  type        text,
  received_at timestamptz not null default now()
);

-- ---------- B2B ----------
create table if not exists public.inquiries (
  no      text primary key,
  at      timestamptz not null default now(),
  type    text not null check (type in ('catalogue','wholesale','export','sample','custom','private')),
  name    text not null,
  company text, email text not null, wa text, country text, btype text, sku text, qty text, spec text,
  when_   text, dest text, brand text, pack text, notes text, file text,
  privacy boolean not null default false,
  mkt     boolean not null default false,
  status  text not null default 'New' check (status in ('New','Assigned','In Discussion','Quotation Sent','Approved','In Production','Completed','Lost','Cancelled')),
  pic     text not null default '',
  notify  text not null default 'pending'
);
create table if not exists public.quotations (
  no         text not null,
  ver        int not null,
  inquiry_no text not null references public.inquiries(no) on delete cascade,
  qty text, cur text not null, price numeric(12,2) not null check (price > 0),
  basis text, port text, valid date not null, lead text not null, terms text not null, sample text, excl text,
  status     text not null default 'Draft' check (status in ('Draft','Sent','Approved')),
  at         timestamptz not null default now(),
  primary key (no, ver)
);

-- ---------- site content & settings (key/value) ----------
-- keys: content, contact, settings (public part), private (internal), catalogue_meta
create table if not exists public.site_settings (
  key   text primary key,
  value jsonb not null
);

-- =====================================================================
-- Helpers (not callable from the browser)
-- =====================================================================
create or replace function public._ms(t timestamptz) returns bigint
language sql immutable as $$ select (extract(epoch from t) * 1000)::bigint $$;

create or replace function public._t(en text, id text) returns jsonb
language sql immutable as $$ select jsonb_build_object('en', en, 'id', id) $$;

create or replace function public._setting(k text) returns jsonb
language sql stable security definer set search_path = public as $$
  select value from site_settings where key = k $$;

create or replace function public._role() returns text
language sql stable security definer set search_path = public as $$
  select role from admin_users where user_id = auth.uid() $$;

create or replace function public._can(perm text) returns boolean
language plpgsql stable security definer set search_path = public as $$
declare r text := _role(); p text[];
begin
  if r is null then return false; end if;
  p := case r
    when 'owner'       then array['*']
    when 'content'     then array['product','content','catalogue']
    when 'sales'       then array['inquiry','quote','order.view','report']
    when 'fulfillment' then array['order.view','order.fulfill']
  end;
  return '*' = any(p) or perm = any(p) or exists (select 1 from unnest(p) x where perm like x || '.%');
end $$;

-- raise 403 unless the signed-in admin holds `perm`; write an audit line
create or replace function public._need(perm text, descr text) returns text
language plpgsql security definer set search_path = public as $$
declare r text := _role();
begin
  if r is null then
    raise exception '401 · Silakan masuk sebagai admin.' using errcode = '42501';
  end if;
  if not _can(perm) then
    raise exception '403 · Role "%" tidak memiliki izin "%"', r, perm using errcode = '42501';
  end if;
  insert into audit_logs(user_id, role, perm, descr) values (auth.uid(), r, perm, descr);
  return r;
end $$;

-- check the role before touching any row, so a caller without rights learns nothing about the data
create or replace function public._guard(perm text) returns void
language plpgsql stable security definer set search_path = public as $$
declare r text := _role();
begin
  if r is null then raise exception '401 · Silakan masuk sebagai admin.' using errcode = '42501'; end if;
  if not _can(perm) then raise exception '403 · Role "%" tidak memiliki izin "%"', r, perm using errcode = '42501'; end if;
end $$;

create or replace function public._log(p_no text, msg text) returns void
language sql security definer set search_path = public as $$
  update orders set log = log || jsonb_build_array(jsonb_build_object('at', _ms(now()), 'm', msg)) where no = p_no $$;

create or replace function public._move(p_sku text, p_ref text, p_delta int, p_reason text, p_no text) returns void
language sql security definer set search_path = public as $$
  insert into inventory_movements(sku, ref, delta, reason, ref_no) values (p_sku, p_ref, p_delta, p_reason, p_no) $$;

create or replace function public._product_json(p public.products, internal boolean) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'id', p.id, 'slug', p.slug, 'sku', p.sku, 'legacySku', coalesce(p.legacy_sku, ''), 'cat', p.cat,
    'status', p.status, 'featured', p.featured, 'name', p.name, 'story', p.story, 'material', p.material,
    'size', p.size, 'mode', p.mode, 'sale', p.sale, 'price', p.price, 'lead', p.lead, 'care', p.care,
    'images', p.images, 'pkg', p.pkg, 'catalogue', p.catalogue,
    'hasOrders', case when internal then p.has_orders else false end,
    'rev', case when internal then p.rev else null end,
    'fob', case when internal and _can('quote') then
             (select jsonb_build_object('usd', f.usd, 'unit', f.unit, 'label', f.label) from product_fob f where f.product_id = p.id)
           else null end,
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

create or replace function public._order_json(p_no text, internal boolean) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'no', o.no, 'at', _ms(o.created_at), 'customer', o.customer, 'zone', o.zone, 'pay', o.pay, 'ful', o.ful,
    'method', o.method, 'sub', o.sub, 'ship', o.ship, 'total', o.total, 'priceTampered', o.price_tampered,
    'expiresAt', _ms(o.expires_at), 'held', o.held, 'tracking', o.tracking,
    'notes', case when internal then o.notes else '' end,
    'recon', o.recon, 'restocked', o.restocked, 'log', o.log,
    'items', coalesce((select jsonb_agg(jsonb_build_object('sku', i.sku, 'name', i.name, 'variant', i.variant, 'unit', i.unit,
               'qty', i.qty, 'img', i.img, 'mode', i.mode, 'sale', i.sale, 'lead', i.lead) order by i.id)
               from order_items i where i.order_no = o.no), '[]'::jsonb),
    'res', coalesce((select jsonb_agg(jsonb_build_object('pid', i.product_id, 'ref', i.ref, 'qty', i.qty) order by i.id)
               from order_items i where i.order_no = o.no), '[]'::jsonb))
  from orders o where o.no = p_no $$;

-- ---------- stock moves for one order ----------
create or replace function public._release(p_no text) returns void
language plpgsql security definer set search_path = public as $$
declare it record;
begin
  if not coalesce((select held from orders where no = p_no for update), false) then return; end if;
  for it in select * from order_items where order_no = p_no order by product_id, ref loop
    if it.mode = 'exact' then
      update pieces set status = 'available', held_by = null where id = it.ref and status = 'reserved' and held_by = p_no;
      if found then perform _move(it.sku, it.ref, 1, 'release', p_no); end if;
    else
      update variants set reserved = greatest(0, reserved - it.qty) where id = it.ref;
      perform _move(it.sku, it.ref, it.qty, 'release', p_no);
    end if;
  end loop;
  update orders set held = false where no = p_no;
end $$;

create or replace function public._finalize(p_no text) returns void
language plpgsql security definer set search_path = public as $$
declare it record;
begin
  for it in select * from order_items where order_no = p_no order by product_id, ref loop
    update products set has_orders = true where id = it.product_id;
    if it.mode = 'exact' then
      update pieces set status = 'sold', held_by = p_no where id = it.ref;
    else
      update variants set reserved = greatest(0, reserved - it.qty), stock = greatest(0, stock - it.qty) where id = it.ref;
    end if;
    perform _move(it.sku, it.ref, 0, 'sold', p_no);
  end loop;
  update orders set held = false where no = p_no;
end $$;

-- lock every row the order needs; reserve all of it or nothing
create or replace function public._try_reserve(p_no text) returns boolean
language plpgsql security definer set search_path = public as $$
declare it record; ok boolean := true;
begin
  for it in select * from order_items where order_no = p_no order by product_id, ref loop
    if it.mode = 'exact' then
      perform 1 from pieces where id = it.ref and status = 'available' for update;
    else
      perform 1 from variants where id = it.ref and stock - reserved >= it.qty for update;
    end if;
    if not found then ok := false; end if;
  end loop;
  if not ok then return false; end if;
  for it in select * from order_items where order_no = p_no order by product_id, ref loop
    if it.mode = 'exact' then
      update pieces set status = 'reserved', held_by = p_no where id = it.ref;
    else
      update variants set reserved = reserved + it.qty where id = it.ref;
    end if;
    perform _move(it.sku, it.ref, -it.qty, 'reserve', p_no);
  end loop;
  update orders set held = true where no = p_no;
  return true;
end $$;

-- release reservations whose time is up (also scheduled every minute by pg_cron)
create or replace function public._expire_reservations() returns int
language plpgsql security definer set search_path = public as $$
declare o record; n int := 0;
begin
  for o in select no from orders where pay = 'pending' and held and expires_at < now() for update skip locked loop
    update orders set pay = 'expired' where no = o.no;
    perform _release(o.no);
    perform _log(o.no, 'Reservation expired; stock released');
    n := n + 1;
  end loop;
  return n;
end $$;

-- =====================================================================
-- PUBLIC API (anon + signed-in)
-- =====================================================================
create or replace function public.get_public_site() returns jsonb
language plpgsql security definer set search_path = public as $$
declare c jsonb := coalesce(_setting('contact'), '{}'::jsonb); s jsonb := coalesce(_setting('settings'), '{}'::jsonb);
        ap int := nullif(c->>'activePhone', '')::int;
begin
  perform _expire_reservations();
  return jsonb_build_object(
    'categories', coalesce((select jsonb_agg(jsonb_build_object('id', id, 'name', name, 'cover', cover, 'visible', visible, 'soon', soon) order by sort)
                  from categories where visible), '[]'::jsonb),
    'products',   coalesce((select jsonb_agg(_product_json(p, false) order by p.sort, p.id) from products p where p.status = 'published'), '[]'::jsonb),
    'content',    coalesce(_setting('content'), '{}'::jsonb),
    'contact',    jsonb_build_object(
                    'email', c->'email', 'instagram', c->'instagram',
                    'phones', case when ap is null then '[]'::jsonb else jsonb_build_array(c->'phones'->ap) end,
                    'activePhone', case when ap is null then null else 0 end,
                    'addressConfirmed', coalesce((c->>'addressConfirmed')::boolean, false),
                    'address', case when coalesce((c->>'addressConfirmed')::boolean, false) then c->'address' else null end,
                    'legal', coalesce((select jsonb_agg(l) from jsonb_array_elements(c->'legal') l where (l->>'verified')::boolean), '[]'::jsonb)),
    'settings',   jsonb_build_object('reserveMin', s->'reserveMin', 'zones', s->'zones', 'pay', s->'pay', 'intlCheckout', false,
                                     'paySimulator', coalesce((_setting('private')->>'paySimulator')::boolean, false)),
    'catalogueMeta', coalesce(_setting('catalogue_meta'), '{}'::jsonb));
end $$;

create or replace function public.create_order(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  c jsonb := coalesce(p->'customer', '{}'::jsonb);
  lang text := case when p->>'lang' = 'id' then 'id' else 'en' end;
  s jsonb := coalesce(_setting('settings'), '{}'::jsonb);
  errs jsonb := '{}'::jsonb; z jsonb; ln record; pr products; v variants; pc pieces;
  items jsonb := '[]'::jsonb; bad jsonb := '[]'::jsonb; sub int := 0; q int; lbl text;
  v_no text; v_total int; it jsonb; ct int;
begin
  perform _expire_reservations();
  if length(trim(coalesce(c->>'name', ''))) < 2 then errs := errs || jsonb_build_object('name', _t('Enter the recipient name.', 'Isi nama penerima.')); end if;
  if coalesce(c->>'email', '') !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then errs := errs || jsonb_build_object('email', _t('Enter a valid email address.', 'Isi alamat email yang valid.')); end if;
  if coalesce(c->>'phone', '') !~ '^[+0-9 ()-]{8,}$' then errs := errs || jsonb_build_object('phone', _t('Enter a phone number with at least 8 digits.', 'Isi nomor telepon minimal 8 digit.')); end if;
  if length(trim(coalesce(c->>'address', ''))) < 8 then errs := errs || jsonb_build_object('address', _t('Enter the full street address.', 'Isi alamat lengkap.')); end if;
  if coalesce(p->>'country', '') <> 'ID' then errs := errs || jsonb_build_object('country', _t('International checkout is not active yet. Send an export inquiry instead.', 'Checkout internasional belum aktif. Kirim inquiry ekspor.')); end if;
  select e into z from jsonb_array_elements(s->'zones') e where e->>'id' = p->>'zone';
  if z is null then errs := errs || jsonb_build_object('zone', _t('Choose a shipping region.', 'Pilih wilayah pengiriman.'));
  elsif not (z->>'on')::boolean then errs := errs || jsonb_build_object('zone', _t(format('We don''t ship to %s yet. Contact us for alternatives.', z->>'name'), format('Kami belum mengirim ke %s. Hubungi kami untuk alternatif.', z->>'name')));
  end if;
  if not exists (select 1 from jsonb_array_elements_text(coalesce(s->'pay', '[]'::jsonb)) m where m = p->>'pay') then
    errs := errs || jsonb_build_object('pay', _t('Choose a payment method.', 'Pilih metode pembayaran.'));
  end if;
  if errs <> '{}'::jsonb then return jsonb_build_object('ok', false, 'errs', errs); end if;

  if jsonb_typeof(p->'lines') <> 'array' or jsonb_array_length(p->'lines') = 0 then
    return jsonb_build_object('ok', false, 'errs', jsonb_build_object('cart', _t('Your cart is empty.', 'Keranjang Anda kosong.')));
  end if;
  if jsonb_array_length(p->'lines') > 30 then
    return jsonb_build_object('ok', false, 'errs', jsonb_build_object('cart', _t('Too many items in one order. Split it or send an inquiry.', 'Terlalu banyak barang dalam satu pesanan. Pisahkan atau kirim inquiry.')));
  end if;

  -- prices, availability and locks are decided here, never by the browser
  for ln in
    select l->>'pid' as pid, l->>'ref' as ref,
           sum(greatest(1, least(50, coalesce(nullif(l->>'qty', '')::int, 1))))::int as qty
    from jsonb_array_elements(p->'lines') l group by 1, 2 order by 1, 2
  loop
    select * into pr from products where id = ln.pid;
    if not found or pr.status <> 'published' or pr.price is null
       or not (pr.sale = 'retail' or (pr.sale = 'mto' and pr.lead is not null)) then
      bad := bad || jsonb_build_object('pid', ln.pid, 'ref', ln.ref, 'why', 'unavailable'); continue;
    end if;
    if pr.mode = 'exact' then
      select * into pc from pieces where id = ln.ref and product_id = pr.id for update;
      if not found or pc.status <> 'available' then
        bad := bad || jsonb_build_object('pid', ln.pid, 'ref', ln.ref, 'why', coalesce(pc.status, 'unavailable')); continue;
      end if;
      q := 1; lbl := pc.code;
    else
      select * into v from variants where id = ln.ref and product_id = pr.id for update;
      if not found or v.stock - v.reserved < ln.qty then
        bad := bad || jsonb_build_object('pid', ln.pid, 'ref', ln.ref, 'why', 'stock'); continue;
      end if;
      q := ln.qty; lbl := v.label;
    end if;
    sub := sub + pr.price * q;
    items := items || jsonb_build_object('pid', pr.id, 'ref', ln.ref, 'qty', q, 'sku', pr.sku,
              'name', coalesce(pr.name->>lang, pr.name->>'en'), 'variant', lbl, 'unit', pr.price,
              'img', pr.images->>0, 'mode', pr.mode, 'sale', pr.sale,
              'lead', coalesce(pr.lead->>lang, pr.lead->>'en', ''));
  end loop;
  if jsonb_array_length(bad) > 0 then
    return jsonb_build_object('ok', false, 'bad', bad,
      'errs', jsonb_build_object('cart', _t('Some items are no longer available. Review your cart.', 'Beberapa barang sudah tidak tersedia. Periksa keranjang Anda.')));
  end if;

  v_total := sub + (z->>'rate')::int;
  ct := nullif(p->>'clientTotal', '')::int;
  v_no := 'NE-' || to_char(now() at time zone 'Asia/Jakarta', 'YYMM') || '-' || lpad(nextval('order_seq')::text, 4, '0');
  insert into orders(no, customer, email, zone, method, sub, ship, total, client_total, price_tampered, expires_at, log)
  values (v_no,
          jsonb_build_object('name', trim(c->>'name'), 'email', lower(trim(c->>'email')), 'phone', trim(c->>'phone'),
                             'address', left(trim(c->>'address'), 500), 'city', left(trim(coalesce(c->>'city', '')), 120)),
          lower(trim(c->>'email')), z->>'name', p->>'pay', sub, (z->>'rate')::int, v_total, ct,
          ct is not null and ct <> v_total,
          now() + make_interval(mins => greatest(1, coalesce((s->>'reserveMin')::int, 15))),
          jsonb_build_array(jsonb_build_object('at', _ms(now()), 'm', 'Order created, stock reserved')));
  for it in select * from jsonb_array_elements(items) loop
    insert into order_items(order_no, product_id, ref, qty, sku, name, variant, unit, img, mode, sale, lead)
    values (v_no, it->>'pid', it->>'ref', (it->>'qty')::int, it->>'sku', it->>'name', it->>'variant',
            (it->>'unit')::int, it->>'img', it->>'mode', it->>'sale', it->>'lead');
    if it->>'mode' = 'exact' then
      update pieces set status = 'reserved', held_by = v_no where id = it->>'ref';
    else
      update variants set reserved = reserved + (it->>'qty')::int where id = it->>'ref';
    end if;
    update products set has_orders = true where id = it->>'pid';
    perform _move(it->>'sku', it->>'ref', -(it->>'qty')::int, 'reserve', v_no);
  end loop;
  return jsonb_build_object('ok', true, 'order', _order_json(v_no, false));
end $$;

-- order status for the buyer: needs the order number AND the email used at checkout
create or replace function public.get_order(p_no text, p_email text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  perform _expire_reservations();
  if not exists (select 1 from orders where no = upper(trim(p_no)) and email = lower(trim(p_email))) then return null; end if;
  return _order_json(upper(trim(p_no)), false);
end $$;

-- Payment provider callback. In production only the provider's webhook (an Edge Function
-- holding the service_role key and verifying the signature) may call this. While the
-- 'paySimulator' flag is on (staging) the website's test buttons may call it too.
create or replace function public.payment_callback(p_no text, p_type text, p_event text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare o orders;
begin
  if coalesce(auth.role(), '') <> 'service_role'
     and not coalesce((_setting('private')->>'paySimulator')::boolean, false) then
    raise exception 'Payment confirmations are only accepted from the payment provider.' using errcode = '42501';
  end if;
  if p_type not in ('paid', 'failed', 'expired') or coalesce(p_event, '') = '' then
    raise exception 'Invalid payment event.' using errcode = '22023';
  end if;
  begin
    insert into payment_events(event_id, order_no, type) values (p_event, p_no, p_type);
  exception when unique_violation then
    return jsonb_build_object('dup', true, 'msg', 'Duplicate callback ignored');
  end;
  select * into o from orders where no = p_no for update;
  if not found then return jsonb_build_object('err', 'Order not found'); end if;
  if p_type = 'paid' then
    if o.pay = 'paid' then return jsonb_build_object('dup', true, 'msg', 'Order already paid'); end if;
    if o.pay = 'pending' then
      perform _finalize(p_no);
      update orders set pay = 'paid' where no = p_no;
      perform _log(p_no, 'Payment confirmed by provider');
    elsif o.pay in ('expired', 'failed') then
      if _try_reserve(p_no) then
        perform _finalize(p_no);
        update orders set pay = 'paid' where no = p_no;
        perform _log(p_no, 'Late payment received; stock still available, sale completed');
      else
        update orders set pay = 'paid', recon = true where no = p_no;
        perform _log(p_no, 'Late payment received but item no longer available: reconciliation queue');
      end if;
    end if;
  elsif p_type = 'failed' and o.pay = 'pending' then
    update orders set pay = 'failed' where no = p_no;
    perform _release(p_no);
    perform _log(p_no, 'Payment failed; reservation released');
  elsif p_type = 'expired' and o.pay = 'pending' then
    update orders set pay = 'expired' where no = p_no;
    perform _release(p_no);
    perform _log(p_no, 'Reservation expired; stock released');
  end if;
  return jsonb_build_object('ok', true, 'order', _order_json(p_no, false));
end $$;

create or replace function public.submit_inquiry(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare errs jsonb := '{}'::jsonb; t text := coalesce(p->>'type', 'wholesale'); v_no text; em text := lower(trim(coalesce(p->>'email', '')));
        f text; clean jsonb := '{}'::jsonb;
begin
  if t not in ('catalogue','wholesale','export','sample','custom','private') then t := 'wholesale'; end if;
  if length(trim(coalesce(p->>'name', ''))) < 2 then errs := errs || jsonb_build_object('name', _t('Enter your name.', 'Isi nama Anda.')); end if;
  if em !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then errs := errs || jsonb_build_object('email', _t('Enter a valid email address.', 'Isi alamat email yang valid.')); end if;
  if t <> 'catalogue' then
    if coalesce(p->>'country', '') = '' then errs := errs || jsonb_build_object('country', _t('Choose a country.', 'Pilih negara.')); end if;
    if not coalesce((p->>'privacy')::boolean, false) then errs := errs || jsonb_build_object('privacy', _t('Please agree to the privacy notice so we can reply.', 'Setujui pemberitahuan privasi agar kami dapat membalas.')); end if;
  end if;
  if errs <> '{}'::jsonb then return jsonb_build_object('ok', false, 'errs', errs); end if;
  -- simple spam brake: at most 5 inquiries per email per 10 minutes
  if (select count(*) from inquiries where email = em and at > now() - interval '10 minutes') >= 5 then
    return jsonb_build_object('ok', false, 'errs', jsonb_build_object('email', _t('Too many requests from this email. Please wait a few minutes.', 'Terlalu banyak permintaan dari email ini. Coba lagi beberapa menit lagi.')));
  end if;
  foreach f in array array['company','wa','country','btype','sku','qty','spec','when','dest','brand','pack','notes','file'] loop
    clean := clean || jsonb_build_object(f, left(coalesce(p->>f, ''), 2000));
  end loop;
  v_no := 'INQ-' || to_char(now() at time zone 'Asia/Jakarta', 'YYYY') || '-' || lpad(nextval('inquiry_seq')::text, 4, '0');
  insert into inquiries(no, type, name, company, email, wa, country, btype, sku, qty, spec, when_, dest, brand, pack, notes, file, privacy, mkt, notify)
  values (v_no, t, left(trim(p->>'name'), 200), clean->>'company', em, clean->>'wa', clean->>'country', clean->>'btype', clean->>'sku',
          clean->>'qty', clean->>'spec', clean->>'when', clean->>'dest', clean->>'brand', clean->>'pack', clean->>'notes', clean->>'file',
          coalesce((p->>'privacy')::boolean, t = 'catalogue'), coalesce((p->>'mkt')::boolean, false), 'pending');
  -- stored first; the notification may fail on its own and is retried from the CMS
  update inquiries set notify = case when coalesce((_setting('private')->>'notifyOk')::boolean, true) then 'sent' else 'failed' end where no = v_no;
  return jsonb_build_object('ok', true, 'inq', jsonb_build_object('no', v_no, 'email', em, 'type', t));
end $$;

-- =====================================================================
-- ADMIN API (signed-in staff; every call checks the role on the server)
-- =====================================================================
create or replace function public.admin_me() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when a.user_id is null then null else jsonb_build_object('role', a.role, 'name', a.name,
         'email', (select email from auth.users u where u.id = a.user_id)) end
  from (select auth.uid() as uid) x left join admin_users a on a.user_id = x.uid $$;

create or replace function public.admin_snapshot() returns jsonb
language plpgsql security definer set search_path = public as $$
declare r text := _role();
begin
  if r is null then raise exception '401 · Silakan masuk sebagai admin.' using errcode = '42501'; end if;
  perform _expire_reservations();
  return jsonb_build_object(
    'role', r,
    'categories', (select coalesce(jsonb_agg(jsonb_build_object('id', id, 'name', name, 'cover', cover, 'visible', visible, 'soon', soon) order by sort), '[]'::jsonb) from categories),
    'products',   (select coalesce(jsonb_agg(_product_json(p, true) order by p.sort, p.id), '[]'::jsonb) from products p),
    'content',    coalesce(_setting('content'), '{}'::jsonb),
    'contact',    coalesce(_setting('contact'), '{}'::jsonb),
    'settings',   coalesce(_setting('settings'), '{}'::jsonb) || jsonb_build_object(
                    'notifyOk', coalesce((_setting('private')->>'notifyOk')::boolean, true),
                    'paySimulator', coalesce((_setting('private')->>'paySimulator')::boolean, false)),
    'catalogueMeta', coalesce(_setting('catalogue_meta'), '{}'::jsonb),
    'orders',     case when _can('order.view') then (select coalesce(jsonb_agg(_order_json(o.no, true) order by o.created_at desc), '[]'::jsonb) from orders o) else '[]'::jsonb end,
    'inquiries',  case when _can('inquiry') then (select coalesce(jsonb_agg(jsonb_build_object(
                    'no', no, 'at', _ms(at), 'type', type, 'name', name, 'company', company, 'email', email, 'wa', wa, 'country', country,
                    'btype', btype, 'sku', sku, 'qty', qty, 'spec', spec, 'when', when_, 'dest', dest, 'brand', brand, 'pack', pack,
                    'notes', notes, 'file', file, 'privacy', privacy, 'mkt', mkt, 'status', status, 'pic', pic, 'notify', notify) order by at desc), '[]'::jsonb) from inquiries) else '[]'::jsonb end,
    'quotes',     case when _can('quote') then (select coalesce(jsonb_agg(jsonb_build_object(
                    'no', no, 'ver', ver, 'inq', inquiry_no, 'qty', qty, 'cur', cur, 'price', price, 'basis', basis, 'port', port,
                    'valid', valid, 'lead', lead, 'terms', terms, 'sample', sample, 'excl', excl, 'status', status, 'at', _ms(at)) order by no, ver), '[]'::jsonb) from quotations) else '[]'::jsonb end,
    'audit',      case when _can('settings') then (select coalesce(jsonb_agg(jsonb_build_object('at', _ms(at), 'role', role, 'perm', perm, 'desc', descr) order by at desc), '[]'::jsonb)
                    from (select * from audit_logs order by at desc limit 300) a) else '[]'::jsonb end,
    'movements',  case when _can('settings') then (select coalesce(jsonb_agg(jsonb_build_object('at', _ms(at), 'sku', sku, 'ref', ref, 'delta', delta, 'reason', reason, 'refNo', ref_no) order by at desc, id desc), '[]'::jsonb)
                    from (select * from inventory_movements order by at desc, id desc limit 400) m) else '[]'::jsonb end);
end $$;

-- ---------- products ----------
create or replace function public._valid_images(imgs jsonb) returns boolean
language sql immutable as $$
  select jsonb_typeof(imgs) = 'array' and jsonb_array_length(imgs) <= 12
     and not exists (select 1 from jsonb_array_elements_text(imgs) x
                     where length(x) > 500 or not (x ~ '^[a-z0-9-]{1,80}$' or x ~ '^https://[A-Za-z0-9._~:/?#@!$&''()*+,;=%-]+$' or x ~ '^http://(localhost|127\.0\.0\.1)(:[0-9]+)?/[A-Za-z0-9._~:/?#@!$&''()*+,;=%-]*$')) $$;

create or replace function public.admin_save_product(p_id text, p_rev jsonb, p_stocks jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pr products; cur jsonb; newp int; st jsonb; v variants; n int;
begin
  perform _guard('product.edit');
  select * into pr from products where id = p_id for update;
  if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.edit', 'Simpan draft ' || coalesce(p_rev->>'sku', pr.sku));
  if coalesce(trim(p_rev->>'sku'), '') = '' then raise exception 'SKU wajib diisi.'; end if;
  if exists (select 1 from products x where x.id <> p_id and (x.sku = p_rev->>'sku' or x.rev->>'sku' = p_rev->>'sku')) then
    raise exception 'SKU % sudah dipakai produk lain. SKU harus unik.', p_rev->>'sku';
  end if;
  if (p_rev->>'cat') is null or not exists (select 1 from categories where id = p_rev->>'cat') then raise exception 'Kategori tidak valid.'; end if;
  if p_rev->>'mode' not in ('exact','pattern') or p_rev->>'sale' not in ('retail','mto','quote') then raise exception 'Mode tidak valid.'; end if;
  if pr.has_orders and p_rev->>'mode' <> pr.mode then raise exception 'Mode motif terkunci karena produk sudah pernah dipesan.'; end if;
  if not _valid_images(coalesce(p_rev->'images', '[]'::jsonb)) then raise exception 'Daftar foto tidak valid.'; end if;
  cur := coalesce(pr.rev, to_jsonb(pr));
  newp := nullif(p_rev->>'price', '')::int;
  if newp is distinct from nullif(cur->>'price', '')::int and not _can('price') then
    raise exception '403 · Hanya Owner yang dapat mengubah harga.' using errcode = '42501';
  end if;
  if newp is not null and newp <= 0 then raise exception 'Harga harus lebih dari 0.'; end if;
  p_rev := jsonb_build_object('sku', trim(p_rev->>'sku'), 'cat', p_rev->>'cat', 'name', p_rev->'name', 'story', p_rev->'story',
             'material', p_rev->'material', 'size', p_rev->'size', 'mode', p_rev->>'mode', 'sale', p_rev->>'sale',
             'price', newp, 'lead', p_rev->'lead', 'images', coalesce(p_rev->'images', '[]'::jsonb));
  if pr.status = 'published' then
    update products set rev = p_rev, updated_at = now() where id = p_id;
  else
    update products set sku = p_rev->>'sku', cat = p_rev->>'cat', name = p_rev->'name', story = coalesce(p_rev->'story', '{}'),
           material = coalesce(p_rev->'material', '{}'), size = coalesce(p_rev->'size', '{}'), mode = p_rev->>'mode',
           sale = p_rev->>'sale', price = newp, lead = nullif(p_rev->'lead', 'null'::jsonb), images = p_rev->'images',
           rev = null, updated_at = now() where id = p_id;
  end if;
  for st in select * from jsonb_array_elements(coalesce(p_stocks, '[]'::jsonb)) loop
    select * into v from variants where id = st->>'id' and product_id = p_id for update;
    if not found then continue; end if;
    n := greatest(0, coalesce(nullif(st->>'stock', '')::int, v.stock));
    if n <> v.stock then
      if n < v.reserved then raise exception 'Stok % tidak boleh di bawah jumlah yang sedang dipesan (%).', v.label, v.reserved; end if;
      update variants set stock = n where id = v.id;
      perform _move(coalesce(p_rev->>'sku', pr.sku), v.label, n - v.stock, 'adjust', 'admin');
    end if;
  end loop;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_create_product() returns text
language plpgsql security definer set search_path = public as $$
declare n int := (select count(*) from products) + 1; v_id text := 'p' || substr(md5(gen_random_uuid()::text), 1, 8); v_sku text;
begin
  perform _guard('product.create');
  perform _need('product.create', 'Produk baru');
  v_sku := 'NE-NEW-' || lpad(n::text, 3, '0');
  while exists (select 1 from products where sku = v_sku) loop n := n + 1; v_sku := 'NE-NEW-' || lpad(n::text, 3, '0'); end loop;
  insert into products(id, slug, sku, cat, status, name, mode, sale, sort)
  values (v_id, 'new-product-' || v_id, v_sku, (select id from categories order by sort limit 1), 'draft',
          jsonb_build_object('en', 'New product', 'id', ''), 'pattern', 'retail', -1);
  insert into variants(id, product_id, label, stock) values (v_id || '-one', v_id, 'One size', 0);
  return v_id;
end $$;

create or replace function public.admin_duplicate_product(p_id text) returns text
language plpgsql security definer set search_path = public as $$
declare s products; v_id text := 'p' || substr(md5(gen_random_uuid()::text), 1, 8);
begin
  perform _guard('product.create');
  select * into s from products where id = p_id; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.create', 'Duplikat ' || s.sku);
  insert into products(id, slug, sku, legacy_sku, cat, status, featured, name, story, material, size, mode, sale, price, lead, care, images, pkg, catalogue, sort)
  values (v_id, s.slug || '-copy-' || substr(v_id, 2, 4), s.sku || '-COPY-' || upper(substr(v_id, 2, 4)), s.legacy_sku, s.cat, 'draft', false, s.name, s.story,
          s.material, s.size, s.mode, s.sale, s.price, s.lead, s.care, s.images, s.pkg, s.catalogue, s.sort);
  insert into variants(id, product_id, label, stock, sort) select v_id || '-' || substr(md5(v.id), 1, 6), v_id, v.label, 0, v.sort from variants v where v.product_id = p_id;
  return v_id;
end $$;

create or replace function public.admin_publish_product(p_id text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pr products; r jsonb;
begin
  perform _guard('product.publish');
  select * into pr from products where id = p_id for update; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.publish', 'Publish ' || pr.sku);
  r := coalesce(pr.rev, to_jsonb(pr));
  if jsonb_array_length(coalesce(r->'images', '[]'::jsonb)) = 0 then raise exception 'Tambahkan minimal satu foto sebelum publish.'; end if;
  if coalesce(r->'name'->>'en', '') = '' then raise exception 'Nama EN wajib diisi.'; end if;
  if pr.rev is not null then
    update products set sku = r->>'sku', cat = r->>'cat', name = r->'name', story = coalesce(r->'story', '{}'), material = coalesce(r->'material', '{}'),
           size = coalesce(r->'size', '{}'), mode = r->>'mode', sale = r->>'sale', price = nullif(r->>'price', '')::int,
           lead = nullif(r->'lead', 'null'::jsonb), images = r->'images', rev = null where id = p_id;
  end if;
  update products set status = 'published', updated_at = now() where id = p_id;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_set_product_status(p_id text, p_status text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare s text;
begin
  perform _guard('product.status');
  if p_status not in ('draft','archived','published') then raise exception 'Status tidak valid.'; end if;
  select sku into s from products where id = p_id; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  if p_status = 'published' then return admin_publish_product(p_id); end if;
  perform _need('product.status', s || ' → ' || p_status);
  update products set status = p_status, updated_at = now() where id = p_id;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_delete_product(p_id text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pr products;
begin
  perform _guard('product.delete');
  select * into pr from products where id = p_id for update; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.delete', 'Hapus ' || pr.sku);
  if pr.has_orders or pr.status <> 'draft' or exists (select 1 from order_items where product_id = p_id) then
    raise exception 'Hanya draft tanpa transaksi yang bisa dihapus. Gunakan Archive.';
  end if;
  delete from products where id = p_id;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_add_piece(p_id text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pr products; n int;
begin
  perform _guard('product.edit');
  select * into pr from products where id = p_id for update; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.edit', 'Tambah piece ' || pr.sku);
  if pr.mode <> 'exact' then raise exception 'Piece hanya untuk produk mode exact piece.'; end if;
  n := (select count(*) from pieces where product_id = p_id) + 1;
  while exists (select 1 from pieces where code = pr.sku || '-P' || lpad(n::text, 2, '0')) loop n := n + 1; end loop;
  insert into pieces(id, product_id, code, label, img, status, sort)
  values ('pc-' || substr(md5(gen_random_uuid()::text), 1, 8), p_id, pr.sku || '-P' || lpad(n::text, 2, '0'),
          (select label from pieces where product_id = p_id order by sort limit 1), pr.images->>0, 'available', n);
  perform _move(pr.sku, 'P' || n, 1, 'new piece', 'admin');
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_add_variant(p_id text, p_label text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare s text;
begin
  perform _guard('product.edit');
  select sku into s from products where id = p_id; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  perform _need('product.edit', 'Tambah varian ' || p_label);
  if coalesce(trim(p_label), '') = '' then raise exception 'Isi nama varian.'; end if;
  if exists (select 1 from variants where product_id = p_id and label = trim(p_label)) then raise exception 'Varian sudah ada.'; end if;
  insert into variants(id, product_id, label, stock, sort)
  values (p_id || '-' || substr(md5(gen_random_uuid()::text), 1, 6), p_id, trim(p_label), 0, (select coalesce(max(sort), 0) + 1 from variants where product_id = p_id));
  return jsonb_build_object('ok', true);
end $$;

-- ---------- orders ----------
create or replace function public.admin_order_fulfill(p_no text, p_ful text, p_tracking text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare o orders; tr text := trim(coalesce(p_tracking, ''));
begin
  perform _guard('order.fulfill');
  select * into o from orders where no = p_no for update; if not found then raise exception 'Pesanan tidak ditemukan.'; end if;
  perform _need('order.fulfill', p_no || ' → ' || p_ful);
  if p_ful = 'processing' and not (o.pay = 'paid' and o.ful = 'unfulfilled') then raise exception 'Hanya pesanan yang sudah dibayar dan belum diproses yang bisa diproses.';
  elsif p_ful = 'shipped' and o.ful <> 'processing' then raise exception 'Pesanan harus diproses dulu sebelum dikirim.';
  elsif p_ful = 'shipped' and tr = '' then raise exception 'Isi nomor resi sebelum menandai dikirim.';
  elsif p_ful = 'delivered' and o.ful <> 'shipped' then raise exception 'Pesanan belum dikirim.';
  elsif p_ful = 'returned' and o.ful not in ('shipped','delivered') then raise exception 'Retur hanya untuk pesanan yang sudah dikirim.';
  elsif p_ful not in ('processing','shipped','delivered','returned') then raise exception 'Status pemenuhan tidak valid.';
  end if;
  update orders set ful = p_ful, tracking = case when tr <> '' then tr else tracking end where no = p_no;
  perform _log(p_no, 'Fulfillment: ' || p_ful || case when p_ful = 'shipped' then ' · ' || tr else '' end);
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_order_notes(p_no text, p_tracking text, p_notes text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  perform _guard('order.fulfill');
  if not exists (select 1 from orders where no = p_no) then raise exception 'Pesanan tidak ditemukan.'; end if;
  perform _need('order.fulfill', 'Catatan ' || p_no);
  update orders set tracking = left(trim(coalesce(p_tracking, '')), 100), notes = left(coalesce(p_notes, ''), 4000) where no = p_no;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_order_cancel(p_no text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare o orders;
begin
  perform _guard('order.cancel');
  select * into o from orders where no = p_no for update; if not found then raise exception 'Pesanan tidak ditemukan.'; end if;
  perform _need('order.cancel', 'Batalkan ' || p_no);
  if o.pay <> 'pending' then raise exception 'Hanya pesanan yang belum dibayar yang bisa dibatalkan.'; end if;
  perform _release(p_no);
  update orders set pay = 'expired', ful = 'cancelled' where no = p_no;
  perform _log(p_no, 'Cancelled by admin; stock released');
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_order_refund(p_no text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare o orders;
begin
  perform _guard('order.refund');
  select * into o from orders where no = p_no for update; if not found then raise exception 'Pesanan tidak ditemukan.'; end if;
  perform _need('order.refund', 'Refund ' || p_no);
  if o.pay <> 'paid' then raise exception 'Hanya pesanan berstatus paid yang bisa di-refund.'; end if;
  update orders set pay = 'refunded', recon = false where no = p_no;
  perform _log(p_no, 'Full refund recorded');
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_order_restock(p_no text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare o orders; it record;
begin
  perform _guard('order.fulfill');
  select * into o from orders where no = p_no for update; if not found then raise exception 'Pesanan tidak ditemukan.'; end if;
  perform _need('order.fulfill', 'Restok retur ' || p_no);
  if o.ful <> 'returned' or o.restocked then raise exception 'Restok hanya untuk retur yang belum direstok.'; end if;
  for it in select * from order_items where order_no = p_no loop
    if it.mode = 'exact' then update pieces set status = 'available', held_by = null where id = it.ref;
    else update variants set stock = stock + it.qty where id = it.ref; end if;
    perform _move(it.sku, it.ref, it.qty, 'return restock', p_no);
  end loop;
  update orders set restocked = true where no = p_no;
  perform _log(p_no, 'Returned items inspected and restocked');
  return jsonb_build_object('ok', true);
end $$;

-- ---------- inquiries & quotations ----------
create or replace function public.admin_inquiry_update(p_no text, p_status text, p_pic text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare v_st text := p_status; v_pic text := case when coalesce(p_pic, '') in ('', '—') then '' else p_pic end;
begin
  perform _guard('inquiry.edit');
  if not exists (select 1 from inquiries where no = p_no) then raise exception 'Inquiry tidak ditemukan.'; end if;
  perform _need('inquiry.edit', p_no || ' → ' || p_status);
  if v_st = 'New' and v_pic <> '' then v_st := 'Assigned'; end if;
  update inquiries set status = v_st, pic = left(v_pic, 80) where no = p_no;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_inquiry_retry(p_no text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare ok boolean := coalesce((_setting('private')->>'notifyOk')::boolean, true);
begin
  perform _guard('inquiry.notify');
  perform _need('inquiry.notify', 'Kirim ulang notifikasi ' || p_no);
  update inquiries set notify = case when ok then 'sent' else 'failed' end where no = p_no;
  return jsonb_build_object('ok', true, 'notify', case when ok then 'sent' else 'failed' end);
end $$;

create or replace function public.admin_quote_create(p_inq text, p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare v_no text; v_ver int; pr numeric;
begin
  perform _guard('quote.create');
  if not exists (select 1 from inquiries where no = p_inq) then raise exception 'Inquiry tidak ditemukan.'; end if;
  perform _need('quote.create', 'Quotation untuk ' || p_inq);
  pr := nullif(p->>'price', '')::numeric;
  if pr is null or pr <= 0 or coalesce(p->>'valid', '') = '' or coalesce(trim(p->>'lead'), '') = '' or coalesce(trim(p->>'terms'), '') = '' then
    raise exception 'Isi harga per unit, masa berlaku, lead time dan termin pembayaran.';
  end if;
  select no, max(ver) into v_no, v_ver from quotations where inquiry_no = p_inq group by no limit 1;
  if v_no is null then v_no := 'QUO-' || to_char(now() at time zone 'Asia/Jakarta', 'YYYY') || '-' || lpad(nextval('quote_seq')::text, 4, '0'); v_ver := 0; end if;
  insert into quotations(no, ver, inquiry_no, qty, cur, price, basis, port, valid, lead, terms, sample, excl)
  values (v_no, v_ver + 1, p_inq, p->>'qty', coalesce(nullif(p->>'cur', ''), 'USD'), pr, p->>'basis', p->>'port', (p->>'valid')::date,
          p->>'lead', p->>'terms', p->>'sample', p->>'excl');
  update inquiries set status = 'In Discussion' where no = p_inq and status in ('New', 'Assigned');
  return jsonb_build_object('ok', true, 'no', v_no, 'ver', v_ver + 1);
end $$;

create or replace function public.admin_quote_set_status(p_no text, p_ver int, p_status text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare q quotations;
begin
  perform _guard('quote.edit');
  select * into q from quotations where no = p_no and ver = p_ver for update; if not found then raise exception 'Quotation tidak ditemukan.'; end if;
  perform _need('quote.edit', format('%s v%s %s', p_no, p_ver, p_status));
  if not ((q.status = 'Draft' and p_status = 'Sent') or (q.status = 'Sent' and p_status = 'Approved')) then
    raise exception 'Perubahan status quotation tidak valid.';
  end if;
  update quotations set status = p_status where no = p_no and ver = p_ver;
  update inquiries set status = case when p_status = 'Sent' then 'Quotation Sent' else 'Approved' end where no = q.inquiry_no;
  return jsonb_build_object('ok', true);
end $$;

-- ---------- content, contact, catalogue, settings ----------
create or replace function public.admin_save_content(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  perform _guard('content.edit');
  perform _need('content.edit', 'Konten homepage');
  if p->>'featured' is not null and not exists (select 1 from products where id = p->>'featured' and status = 'published') then
    raise exception 'Produk unggulan harus produk yang sudah dipublikasikan.';
  end if;
  if p->>'heroImg' is not null and not _valid_images(jsonb_build_array(p->>'heroImg')) then raise exception 'Foto hero tidak valid.'; end if;
  insert into site_settings(key, value) values ('content', '{}') on conflict do nothing;
  update site_settings set value = value || jsonb_strip_nulls(jsonb_build_object(
    'heroTitle', p->'heroTitle', 'heroSub', p->'heroSub', 'featured', p->'featured', 'heroImg', p->'heroImg')) where key = 'content';
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_save_contact(p_active int, p_address_confirmed boolean, p_legal boolean[]) returns jsonb
language plpgsql security definer set search_path = public as $$
declare c jsonb; i int; leg jsonb;
begin
  perform _guard('contact.edit');
  perform _need('contact.edit', 'Kontak & legalitas');
  c := coalesce(_setting('contact'), '{}'::jsonb);
  if p_active is not null and (p_active < 0 or p_active >= jsonb_array_length(coalesce(c->'phones', '[]'::jsonb))) then raise exception 'Nomor tidak valid.'; end if;
  leg := coalesce(c->'legal', '[]'::jsonb);
  for i in 0 .. coalesce(jsonb_array_length(leg), 0) - 1 loop
    if p_legal is not null and array_length(p_legal, 1) > i then
      leg := jsonb_set(leg, array[i::text, 'verified'], to_jsonb(coalesce(p_legal[i + 1], false)));
    end if;
  end loop;
  update site_settings set value = c || jsonb_build_object('activePhone', p_active, 'addressConfirmed', coalesce(p_address_confirmed, false), 'legal', leg)
  where key = 'contact';
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_save_catalogue(p_ids text[]) returns jsonb
language plpgsql security definer set search_path = public as $$
declare m jsonb; maj int; mn int;
begin
  perform _guard('catalogue.edit');
  perform _need('catalogue.edit', 'Katalog versi baru');
  update products set catalogue = (id = any(coalesce(p_ids, '{}'))) where status = 'published';
  m := coalesce(_setting('catalogue_meta'), '{"version":"1.0","lang":"EN"}'::jsonb);
  maj := coalesce(split_part(m->>'version', '.', 1), '1')::int; mn := coalesce(nullif(split_part(m->>'version', '.', 2), ''), '0')::int;
  insert into site_settings(key, value) values ('catalogue_meta', m || jsonb_build_object('version', maj || '.' || (mn + 1), 'date', to_char(now() at time zone 'Asia/Jakarta', 'YYYY-MM-DD')))
  on conflict (key) do update set value = excluded.value;
  return jsonb_build_object('ok', true, 'version', maj || '.' || (mn + 1));
end $$;

create or replace function public.admin_save_settings(p jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare s jsonb := coalesce(_setting('settings'), '{}'::jsonb); z jsonb; nz jsonb := '[]'::jsonb; upd jsonb;
begin
  perform _guard('settings');
  perform _need('settings', 'Pengaturan transaksi');
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

-- =====================================================================
-- Lock down: no direct table access; only the API functions above
-- =====================================================================
do $$ declare t text; begin
  for t in select tablename from pg_tables where schemaname = 'public' and tablename in
    ('admin_users','audit_logs','categories','products','product_fob','variants','pieces','inventory_movements','orders',
     'order_items','payment_events','inquiries','quotations','site_settings') loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on all functions in schema public from public, anon, authenticated;

grant execute on function public.get_public_site()                         to anon, authenticated;
grant execute on function public.create_order(jsonb)                       to anon, authenticated;
grant execute on function public.get_order(text, text)                     to anon, authenticated;
grant execute on function public.submit_inquiry(jsonb)                     to anon, authenticated;
grant execute on function public.payment_callback(text, text, text)        to anon, authenticated, service_role;
grant execute on function public.admin_me()                                to authenticated;
grant execute on function public.admin_snapshot()                          to authenticated;
grant execute on function public.admin_save_product(text, jsonb, jsonb)    to authenticated;
grant execute on function public.admin_create_product()                    to authenticated;
grant execute on function public.admin_duplicate_product(text)             to authenticated;
grant execute on function public.admin_publish_product(text)               to authenticated;
grant execute on function public.admin_set_product_status(text, text)      to authenticated;
grant execute on function public.admin_delete_product(text)                to authenticated;
grant execute on function public.admin_add_piece(text)                     to authenticated;
grant execute on function public.admin_add_variant(text, text)             to authenticated;
grant execute on function public.admin_order_fulfill(text, text, text)     to authenticated;
grant execute on function public.admin_order_notes(text, text, text)       to authenticated;
grant execute on function public.admin_order_cancel(text)                  to authenticated;
grant execute on function public.admin_order_refund(text)                  to authenticated;
grant execute on function public.admin_order_restock(text)                 to authenticated;
grant execute on function public.admin_inquiry_update(text, text, text)    to authenticated;
grant execute on function public.admin_inquiry_retry(text)                 to authenticated;
grant execute on function public.admin_quote_create(text, jsonb)           to authenticated;
grant execute on function public.admin_quote_set_status(text, int, text)   to authenticated;
grant execute on function public.admin_save_content(jsonb)                 to authenticated;
grant execute on function public.admin_save_contact(int, boolean, boolean[]) to authenticated;
grant execute on function public.admin_save_catalogue(text[])              to authenticated;
grant execute on function public.admin_save_settings(jsonb)                to authenticated;
-- storage policies call this one
grant execute on function public._can(text)                                to authenticated;
