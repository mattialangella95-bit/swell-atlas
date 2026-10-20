-- Swell Atlas: admin che leggono e gestiscono le segnalazioni dall'app (pannello profilo).
-- Chi è admin sta in swell_admins: si aggiunge solo via SQL o con scripts/admin.py (secret key),
-- mai dall'app. Gli altri utenti e i visitatori continuano a non vedere le segnalazioni.

create table if not exists public.swell_admins (
  user_id     uuid primary key references auth.users (id) on delete cascade,
  note        text check (char_length(note) <= 200),
  created_at  timestamptz not null default now()
);

alter table public.swell_admins enable row level security;

-- ognuno può solo sapere se lui stesso è admin
create policy "swell_admins: vedo se sono admin"
  on public.swell_admins for select to authenticated
  using ((select auth.uid()) = user_id);

revoke all on public.swell_admins from anon, authenticated;
grant select on public.swell_admins to authenticated;

create or replace function public.swell_is_admin() returns boolean
  language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.swell_admins where user_id = (select auth.uid()));
$$;

revoke all on function public.swell_is_admin() from public, anon;
grant execute on function public.swell_is_admin() to authenticated;

-- segnalazioni: gli admin le leggono e ne cambiano solo lo stato (nuova, letta, risolta)
create policy "swell_feedback: gli admin leggono"
  on public.swell_feedback for select to authenticated
  using ((select public.swell_is_admin()));

create policy "swell_feedback: gli admin cambiano lo stato"
  on public.swell_feedback for update to authenticated
  using ((select public.swell_is_admin())) with check ((select public.swell_is_admin()));

grant select on public.swell_feedback to authenticated;
grant update (status) on public.swell_feedback to authenticated;
