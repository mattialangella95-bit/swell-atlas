-- Swell Atlas, fase 5: prezzi voli indicativi per mese (cache Aviasales via Travelpayouts).
-- Storico: ogni giro settimanale AGGIUNGE righe, non sovrascrive, così nel tempo si vede la stagionalità vera.
-- Lettura per tutti (publishable key), scrittura solo con la secret key (scripts/fetch_prices.py),
-- che non passa dalla Row Level Security.

create table if not exists public.swell_prices (
  id            bigint generated always as identity primary key,
  origin        text not null check (origin ~ '^[A-Z]{3}$'),
  destination   text not null check (destination ~ '^[A-Z]{3}$'),
  month         date not null check (extract(day from month) = 1),    -- primo giorno del mese di partenza
  price_min     integer not null check (price_min > 0),               -- euro, andata e ritorno, il più basso trovato
  price_median  integer check (price_median > 0),                     -- euro, mediana delle offerte trovate
  offers        integer not null default 1 check (offers > 0),        -- quante offerte c'erano in cache
  currency      text not null default 'EUR' check (currency ~ '^[A-Z]{3}$'),
  source        text not null default 'travelpayouts',
  observed_at   timestamptz not null default now()                    -- data della rilevazione (inizio del giro)
);

alter table public.swell_prices enable row level security;

create policy "swell_prices: chiunque legge"
  on public.swell_prices for select to anon, authenticated
  using (true);
-- nessuna policy di scrittura: inserisce solo la secret key

revoke all on public.swell_prices from anon, authenticated;
grant select on public.swell_prices to anon, authenticated;

create index if not exists swell_prices_route_idx on public.swell_prices (origin, destination, month, observed_at desc);
create index if not exists swell_prices_origin_idx on public.swell_prices (origin, observed_at desc);

-- ultima rilevazione per tratta e mese, quella che legge l'app (rispetta i permessi di chi interroga)
create or replace view public.swell_prices_latest
  with (security_invoker = true) as
  select distinct on (origin, destination, month)
         origin, destination, month, price_min, price_median, offers, currency, source, observed_at
  from public.swell_prices
  order by origin, destination, month, observed_at desc;

revoke all on public.swell_prices_latest from anon, authenticated;
grant select on public.swell_prices_latest to anon, authenticated;
