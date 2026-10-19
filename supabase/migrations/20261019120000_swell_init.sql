-- Swell Atlas: profili, preferiti e segnalazioni.
-- Tutto con prefisso swell_, così può stare in un progetto Supabase già usato da altro.
-- Row Level Security attiva su tutte le tabelle:
--   - profilo e preferiti: ognuno vede e modifica solo i propri;
--   - segnalazioni: chiunque le può inserire (anche senza login), nessuno le può leggere dall'app.
--     Si leggono solo con la chiave di servizio (scripts/feedback.py), che ignora la RLS.

-- ---------- profili

create table if not exists public.swell_profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  display_name  text check (char_length(display_name) <= 60),
  home_airport  text check (home_airport ~ '^[A-Z]{3}$'),
  surf_level    text check (surf_level in ('principiante', 'intermedio', 'esperto')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

alter table public.swell_profiles enable row level security;

create policy "swell_profiles: leggo il mio"
  on public.swell_profiles for select to authenticated
  using ((select auth.uid()) = id);
create policy "swell_profiles: creo il mio"
  on public.swell_profiles for insert to authenticated
  with check ((select auth.uid()) = id);
create policy "swell_profiles: modifico il mio"
  on public.swell_profiles for update to authenticated
  using ((select auth.uid()) = id) with check ((select auth.uid()) = id);
create policy "swell_profiles: cancello il mio"
  on public.swell_profiles for delete to authenticated
  using ((select auth.uid()) = id);

-- ---------- preferiti

create table if not exists public.swell_favorites (
  user_id     uuid not null references auth.users (id) on delete cascade,
  zone_id     text not null check (zone_id ~ '^[a-z0-9-]{1,60}$'),   -- id stabili di data/zone-ids.json
  note        text check (char_length(note) <= 500),
  created_at  timestamptz not null default now(),
  primary key (user_id, zone_id)
);

alter table public.swell_favorites enable row level security;

create policy "swell_favorites: leggo i miei"
  on public.swell_favorites for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "swell_favorites: aggiungo i miei"
  on public.swell_favorites for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "swell_favorites: modifico i miei"
  on public.swell_favorites for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "swell_favorites: tolgo i miei"
  on public.swell_favorites for delete to authenticated
  using ((select auth.uid()) = user_id);

-- ---------- segnalazioni

create table if not exists public.swell_feedback (
  id          bigint generated always as identity primary key,
  user_id     uuid references auth.users (id) on delete set null,   -- facoltativo
  kind        text not null check (kind in ('bug', 'miglioria', 'dato_zona')),
  zone_id     text check (zone_id ~ '^[a-z0-9-]{1,60}$'),
  message     text not null check (char_length(message) between 1 and 4000),
  page        text check (char_length(page) <= 500),
  app_state   jsonb check (pg_column_size(app_state) <= 4000),        -- settimana, zona, partenza
  user_agent  text check (char_length(user_agent) <= 500),
  status      text not null default 'nuova' check (status in ('nuova', 'letta', 'risolta')),
  created_at  timestamptz not null default now()
);

alter table public.swell_feedback enable row level security;

-- inserimento per tutti: anonimo senza user_id, oppure con il proprio; sempre come "nuova"
create policy "swell_feedback: chiunque segnala"
  on public.swell_feedback for insert to anon, authenticated
  with check (status = 'nuova' and (user_id is null or user_id = (select auth.uid())));
-- nessuna policy di select/update/delete: dall'app non si leggono né si modificano

-- ---------- permessi espliciti (in Supabase anon e authenticated li hanno già di default su public;
-- qui si restringono al minimo necessario)

revoke all on public.swell_profiles, public.swell_favorites, public.swell_feedback from anon, authenticated;
grant select, insert, update, delete on public.swell_profiles, public.swell_favorites to authenticated;
grant insert on public.swell_feedback to anon, authenticated;

-- updated_at del profilo
create or replace function public.swell_touch_updated_at() returns trigger
  language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

create trigger swell_profiles_updated_at before update on public.swell_profiles
  for each row execute function public.swell_touch_updated_at();

create index if not exists swell_feedback_status_idx on public.swell_feedback (status, created_at desc);
