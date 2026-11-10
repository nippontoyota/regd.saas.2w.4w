-- One call that returns every registration row in a compact column layout,
-- so the website loads all data in one request instead of 1,000-row pages.
-- Only the service role (the website's server) may call it.

create or replace function public.odm_registrations_snapshot()
returns json
language sql
stable
security invoker
as $$
  select json_build_object(
    'rto_code',   coalesce(array_agg(rto_code   order by id), '{}'),
    'segment',    coalesce(array_agg(segment    order by id), '{}'),
    'fuel_group', coalesce(array_agg(fuel_group order by id), '{}'),
    'maker',      coalesce(array_agg(maker      order by id), '{}'),
    'brand',      coalesce(array_agg(brand      order by id), '{}'),
    'year',       coalesce(array_agg(year       order by id), '{}'),
    'month',      coalesce(array_agg(month      order by id), '{}'),
    'count',      coalesce(array_agg(count      order by id), '{}'),
    'as_of',      coalesce(array_agg(as_of      order by id), '{}')
  )
  from public.odm_registrations;
$$;

revoke execute on function public.odm_registrations_snapshot() from public, anon, authenticated;
grant execute on function public.odm_registrations_snapshot() to service_role;

notify pgrst, 'reload schema';
