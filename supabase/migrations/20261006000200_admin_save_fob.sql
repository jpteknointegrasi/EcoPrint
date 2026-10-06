-- =====================================================================
-- Owner edits the official FOB export price per product from Admin CMS.
-- Applies immediately (no draft/publish), since FOB is a price list, not
-- product content. p_usd null or <= 0 removes the FOB price.
-- =====================================================================
create or replace function public.admin_save_fob(p_id text, p_usd numeric, p_unit text, p_label text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pr products;
begin
  perform _guard('price');
  select * into pr from products where id = p_id; if not found then raise exception 'Produk tidak ditemukan.'; end if;
  if p_usd is null or p_usd <= 0 then
    perform _need('price', 'Hapus FOB ' || pr.sku);
    delete from product_fob where product_id = p_id;
  else
    if p_usd > 100000 then raise exception 'Harga FOB tidak wajar.'; end if;
    if coalesce(p_unit, '') not in ('pc', 'pair', 'meter') then raise exception 'Satuan FOB tidak valid.'; end if;
    if coalesce(trim(p_label), '') = '' or length(p_label) > 60 then raise exception 'Kelompok FOB tidak valid.'; end if;
    perform _need('price', 'FOB ' || pr.sku || ' → USD ' || round(p_usd, 2) || '/' || p_unit);
    insert into product_fob(product_id, usd, unit, label) values (p_id, round(p_usd, 2), p_unit, trim(p_label))
    on conflict (product_id) do update set usd = excluded.usd, unit = excluded.unit, label = excluded.label;
  end if;
  return jsonb_build_object('ok', true);
end $$;

revoke execute on function public.admin_save_fob(text, numeric, text, text) from public, anon;
grant execute on function public.admin_save_fob(text, numeric, text, text) to authenticated;
