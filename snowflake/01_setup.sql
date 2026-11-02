use role accountadmin;

create or replace resource monitor trial_monitor
  with credit_quota = 40
  frequency = monthly
  start_timestamp = immediately
  triggers on 75 percent do notify
           on 100 percent do suspend;

create warehouse if not exists loading_wh      warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true;
create warehouse if not exists transforming_wh warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true;
create warehouse if not exists reporting_wh    warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true;
alter warehouse loading_wh      set resource_monitor = trial_monitor;
alter warehouse transforming_wh set resource_monitor = trial_monitor;
alter warehouse reporting_wh    set resource_monitor = trial_monitor;

create database if not exists raw;
create database if not exists analytics;

create role if not exists loader;
create role if not exists transformer;
create role if not exists reporter;
grant role loader      to role sysadmin;
grant role transformer to role sysadmin;
grant role reporter    to role sysadmin;

grant usage on warehouse loading_wh      to role loader;
grant usage on warehouse transforming_wh to role transformer;
grant usage on warehouse reporting_wh    to role reporter;

grant all on database raw to role loader;
grant usage on database raw to role transformer;
grant usage on future schemas in database raw to role transformer;
grant select on future tables in database raw to role transformer;

grant all on database analytics to role transformer;
grant usage on database analytics to role reporter;
grant usage on future schemas in database analytics to role reporter;
grant select on future tables in database analytics to role reporter;
grant select on future views  in database analytics to role reporter;

create user if not exists alto_svc
  type = service
  default_role = transformer
  default_warehouse = transforming_wh
  rsa_public_key = '<COLLER_ICI_LA_CLE_PUBLIQUE_ALTO_SVC>';
grant role loader      to user alto_svc;
grant role transformer to user alto_svc;

create user if not exists metabase_svc
  type = service
  default_role = reporter
  default_warehouse = reporting_wh
  rsa_public_key = '<COLLER_ICI_LA_CLE_PUBLIQUE_METABASE_SVC>';
grant role reporter to user metabase_svc;

show grants to role transformer;
