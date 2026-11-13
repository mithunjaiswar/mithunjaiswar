with c as (
  select date as d, partner_et_id as etm, lower(trim(coalesce(last_subdisposition, ''))) as s,
         row_number() over (partition by date, partner_et_id
                            order by coalesce(last_attempt_time, '1900-01-01') desc, id desc) as rn
  from public.collections_calling_data_raw
  where date >= current_date - 21 and date <= current_date and coalesce(attempt_count, 0) > 0
)
select d as "Date", etm as "Employee ID",
  case when s = '' then 'No disposition'
       when s like '%car recovery%' then 'Car recovery'
       when s like '%os recovery%' then 'OS Recovery / Promise'
       when s = 'unclear' then 'Unclear'
       when s like '%busy%' or s like '%hang%' or s like '%no response%' or s like '%no_response%'
         or s like '%ringing%' or s like '%not_reachable%' or s like '%invalid%' or s like '%response missing%' then 'Busy / Hang up / No response'
       when s like '%app%' or s like '%payment%' or s like '%hisaab%' or s like '%recovery amount%'
         or s like '%deposit%' or s like '%not received%' or s like '%razorpay%' then 'App / Payment / Hisaab issue'
       else 'Other' end as "Disposition Bucket"
from c
where rn = 1
order by 1, 2
