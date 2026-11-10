-- Run in Supabase → SQL Editor, in project pxjdyqttajqmfjvebzil.

-- 1. Grant the server (service_role) access to the odm_ tables.
--    anon/authenticated get nothing; RLS stays on.
grant usage on schema public to service_role;
grant all on table public.odm_rtos, public.odm_registrations, public.odm_fuel_mix to service_role;

-- 2. Refresh the API's table cache.
notify pgrst, 'reload schema';

-- 3. Show what exists. Expect 3 rows: odm_fuel_mix, odm_registrations, odm_rtos.
select current_database() as db, table_schema, table_name
from information_schema.tables
where table_name like 'odm_%'
order by table_name;
