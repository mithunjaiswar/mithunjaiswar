-- Daily agent allocation for yesterday's New Join / Rejoin / Resurrection, ALL products (level-up / water-filling logic)
-- Agent load = pilots per agent x city x product from mv_collections_calling_masterlist (city sheet snapshot):
--   current hisaab week if >= 80% of the city's current-week rows have an agent, else last week.
-- Eligible agent: >= 10 pilots of that product in the city (NA / NaN / Agent_Missing excluded).
--   No eligible agent for the product -> agents of the city on total load. No agent in city -> 'No agent in city'.
-- Level-up: every new pilot goes to the agent with the lowest count right now (ties: lower start count, then name),
--   i.e. lowest agents are lifted to the next one, then together, ... Cap 165; when every agent is >= 165 the lowest still gets it ('over 165').
with cfg as materialized (select date_trunc('week', current_date)::date cw, date_trunc('week', current_date)::date - 7 lw, current_date - 1 ad),
snap as materialized (
  select distinct on (s.week, s.partner_et_id) s.week, s.partner_et_id, s.city, s.product_type, s.agent_username
  from public.mv_collections_calling_masterlist s, cfg
  where s.week in (cfg.cw, cfg.lw)
  order by s.week, s.partner_et_id, s.date desc, s.loaded_at desc
),
okag as materialized (select * from snap where coalesce(agent_username,'') not in ('','-','NA','NaN','#N/A','Agent_Missing','Agent Missing','Unassigned')),
cov as materialized (select s.city, count(*) filter (where s.week = c.cw) n_cw, (select count(*) from okag o where o.city = s.city and o.week = c.cw) ag_cw from snap s, cfg c group by 1, c.cw),
src as materialized (select v.city, case when v.n_cw > 0 and v.ag_cw >= 0.8 * v.n_cw then c.cw else c.lw end as wk from cov v, cfg c),
mp as materialized (select o.* from okag o join src on src.city = o.city and o.week = src.wk),
cnt as materialized (select city, product_type, agent_username, count(*) d from mp group by 1,2,3),
tot as materialized (select city, agent_username, sum(d) d from cnt group by 1,2),
al as materialized (
  select distinct on (s.employee_id) s.city, s.employee_id, s.category, s.allocation_datetime,
    case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV' else 'SINGLE' end
         when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
         when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as prod
  from analytics.ssot_alloc_dealloc_full s, cfg
  where s.allocation_date = cfg.ad and s.category in ('New Join','Rejoin','Resurrection')
  order by s.employee_id, s.allocation_datetime
),
grp as materialized (select city, prod, count(*) n from al group by 1,2),
pool as materialized (
  select g.city, g.prod, g.n, e.agent_username agent, e.d from grp g join cnt e on e.city = g.city and e.product_type = g.prod and e.d >= 10
  union all
  select g.city, g.prod, g.n, c.agent_username, c.d from grp g join tot c on c.city = g.city and c.d >= 10
  where not exists (select 1 from cnt e2 where e2.city = g.city and e2.product_type = g.prod and e2.d >= 10)
),
slots as materialized (
  select p.*, k, row_number() over (partition by p.city, p.prod order by k, p.d, p.agent) rn
  from pool p cross join lateral generate_series(p.d + 1, greatest(p.d, 165) + p.n) k
),
dr as materialized (select a.*, row_number() over (partition by a.city, a.prod order by a.allocation_datetime, a.employee_id) rn from al a)
select d.city as "city", d.prod as "product", d.category as "category", to_char(d.allocation_datetime, 'HH24:MI') as "alloc_time",
       d.employee_id as "employee_id", coalesce(s.agent, 'No agent in city') as "agent (Hawkeye)", s.k as "agent count after",
       case when s.k > 165 then 'over 165' else '' end as "cap", (select to_char(wk, 'DD-Mon') from src where src.city = d.city) as "agent mapping week"
from dr d left join slots s on s.city = d.city and s.prod = d.prod and s.rn = d.rn
order by d.city, d.prod, d.rn
