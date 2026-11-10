-- Odometrics tables. All prefixed odm_ so they never clash with the other
-- apps in this Supabase project. Run once in Supabase → SQL Editor.
-- Safe to re-run: uses "if not exists".

create table if not exists public.odm_rtos (
  rto_code   text primary key,          -- e.g. KL41
  rto_name   text not null,             -- e.g. Aluva SRTO
  state      text not null default 'KL'
);

-- Maker x Month registrations per RTO, segment and fuel group
create table if not exists public.odm_registrations (
  id          bigint generated always as identity primary key,
  state       text    not null,         -- KL
  rto_code    text    not null,         -- KL41
  segment     text    not null check (segment in ('2W', '4W')),
  fuel_group  text    not null,         -- PET, DSL, CNG, EV, HYB, PHEV, OTH
  maker       text    not null,         -- name exactly as on Vahan
  brand       text    not null,         -- cleaned brand, e.g. Yamaha
  year        int     not null,
  month       int     not null check (month between 1 and 12),
  count       int     not null,
  as_of       date    not null,         -- date the data was downloaded
  unique (state, rto_code, segment, fuel_group, maker, year, month)
);
create index if not exists odm_reg_lookup
  on public.odm_registrations (segment, year, month, rto_code);
create index if not exists odm_reg_brand
  on public.odm_registrations (segment, brand, year, month);

-- Exact Vahan fuel type x Month per RTO (used to cross-check the groups)
create table if not exists public.odm_fuel_mix (
  id        bigint generated always as identity primary key,
  state     text not null,
  rto_code  text not null,
  segment   text not null check (segment in ('2W', '4W')),
  fuel      text not null,              -- e.g. PETROL(E20), PURE EV
  year      int  not null,
  month     int  not null check (month between 1 and 12),
  count     int  not null,
  as_of     date not null,
  unique (state, rto_code, segment, fuel, year, month)
);

-- Row level security ON with no policies: only the service-role key
-- (server side) can read or write. The public anon key sees nothing.
alter table public.odm_rtos          enable row level security;
alter table public.odm_registrations enable row level security;
alter table public.odm_fuel_mix      enable row level security;
