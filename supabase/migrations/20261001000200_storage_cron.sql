-- =====================================================================
-- Product photos in Supabase Storage + scheduled reservation expiry
-- =====================================================================

-- Public bucket for product media (anyone can view, only staff with product rights can change)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('media', 'media', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set public = true, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "media: staff upload"  on storage.objects;
drop policy if exists "media: staff update"  on storage.objects;
drop policy if exists "media: staff delete"  on storage.objects;
create policy "media: staff upload" on storage.objects for insert to authenticated
  with check (bucket_id = 'media' and public._can('product.edit'));
create policy "media: staff update" on storage.objects for update to authenticated
  using (bucket_id = 'media' and public._can('product.edit'));
create policy "media: staff delete" on storage.objects for delete to authenticated
  using (bucket_id = 'media' and public._can('product.edit'));

-- Release expired stock reservations every minute (pg_cron ships with Supabase)
do $$
begin
  create extension if not exists pg_cron;
  perform cron.unschedule(jobid) from cron.job where jobname = 'niken-expire-reservations';
  perform cron.schedule('niken-expire-reservations', '* * * * *', 'select public._expire_reservations()');
exception when others then
  raise notice 'pg_cron not available (%). Reservations are still released whenever the site or admin loads.', sqlerrm;
end $$;
