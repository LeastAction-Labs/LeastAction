{{ config(materialized='table') }}

select date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level
from {{ ref('fact_product_agg_daily_stage1') }}

union all
(
with metric_with_lag as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value,
        lag(metric_value, 1) over (partition by dim_key_grouping, dim_value, metric_key order by date) as prev_day_value
    from {{ ref('fact_product_agg_daily_stage1') }}
    where metric_key in ('revenue', 'units_sold', 'profit', 'cost')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_dod' as metric_key,
    coalesce(metric_value - prev_day_value, 0) as metric_value,
    null::int as cube_level
from metric_with_lag where prev_day_value is not null
)

union all
(
with metric_with_lag as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value,
        lag(metric_value, 7) over (partition by dim_key_grouping, dim_value, metric_key order by date) as prev_week_value
    from {{ ref('fact_product_agg_daily_stage1') }}
    where metric_key in ('revenue', 'units_sold', 'profit')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_wow' as metric_key,
    coalesce(metric_value - prev_week_value, 0) as metric_value,
    null::int as cube_level
from metric_with_lag where prev_week_value is not null
)

union all
(
with rolling_window as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key,
        avg(metric_value) over (partition by dim_key_grouping, dim_value, metric_key order by date rows between 9 preceding and current row) as avg_10d,
        stddev(metric_value) over (partition by dim_key_grouping, dim_value, metric_key order by date rows between 9 preceding and current row) as std_10d
    from {{ ref('fact_product_agg_daily_stage1') }}
    where metric_key in ('revenue', 'units_sold', 'profit')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_avg_10d' as metric_key, coalesce(avg_10d, 0) as metric_value, null::int as cube_level
from rolling_window
union all
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_std_10d', coalesce(std_10d, 0), null::int
from rolling_window
)

union all
(
with ytd_calc as (
    select date, dim_key, dim_key_grouping, dim_value, metric_key,
        sum(metric_value) over (partition by dim_key_grouping, dim_value, metric_key, date_trunc('year', date) order by date rows between unbounded preceding and current row) as ytd_sum
    from {{ ref('fact_product_agg_daily_stage1') }}
    where metric_key in ('revenue', 'units_sold', 'profit')
)
select date, dim_key, dim_key_grouping, dim_value,
    metric_key || '_ytd' as metric_key, coalesce(ytd_sum, 0) as metric_value, null::int as cube_level
from ytd_calc
)
