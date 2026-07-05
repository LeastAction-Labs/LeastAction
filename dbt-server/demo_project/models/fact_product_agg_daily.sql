{{ config(materialized='table') }}

select date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level
from {{ ref('fact_product_agg_daily_stage2') }}

union all
(
with metric_with_lag as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value,
        lag(metric_value, 365) over (partition by dim_key_grouping, dim_value, metric_key order by date) as prev_year_value
    from {{ ref('fact_product_agg_daily_stage2') }}
    where metric_key in ('revenue', 'units_sold', 'profit', 'cost')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_yoy' as metric_key,
    coalesce(metric_value - prev_year_value, 0) as metric_value,
    null::int as cube_level
from metric_with_lag where prev_year_value is not null
)

union all
(
with ranked as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key,
        rank() over (partition by date, dim_key_grouping, metric_key order by metric_value desc) as rank_value
    from {{ ref('fact_product_agg_daily_stage2') }}
    where metric_key in ('revenue', 'units_sold', 'profit')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_rank' as metric_key,
    rank_value as metric_value,
    null::int as cube_level
from ranked
)

union all
(
with totals as (
    select date, dim_key_grouping, metric_key, sum(metric_value) as total_value
    from {{ ref('fact_product_agg_daily_stage2') }}
    where metric_key in ('revenue', 'units_sold', 'profit')
    group by date, dim_key_grouping, metric_key
),
with_totals as (
    select f.date, f.dim_key, f.dim_key_grouping, f.dim_value, f.metric_key, f.metric_value, t.total_value
    from {{ ref('fact_product_agg_daily_stage2') }} f
    inner join totals t on f.date = t.date and f.dim_key_grouping = t.dim_key_grouping and f.metric_key = t.metric_key
    where f.metric_key in ('revenue', 'units_sold', 'profit')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_pct_of_total' as metric_key,
    case when total_value = 0 then 0 else (metric_value / nullif(total_value, 0)) * 100 end as metric_value,
    null::int as cube_level
from with_totals
)
