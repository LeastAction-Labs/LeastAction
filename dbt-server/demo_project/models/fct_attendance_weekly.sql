{{ config(materialized='table') }}

with weekly as (
    select
        badge_id,
        date_trunc('week', full_date)::date                       as week_start_date,
        sum(total_hours)                                          as total_hours,
        sum(total_sessions)                                       as total_sessions,
        count(distinct full_date)                                 as days_present,
        min(first_in_time)                                        as earliest_in,
        max(last_out_time)                                        as latest_out,
        sum(total_hours) / nullif(sum(total_sessions), 0)        as avg_session_hours
    from {{ ref('fct_attendance_daily') }}
    group by badge_id, date_trunc('week', full_date)::date
)

select
    w.badge_id,
    w.week_start_date,
    w.week_start_date + 6                               as week_end_date,
    extract(year  from w.week_start_date)::int          as year,
    extract(month from w.week_start_date)::int          as month,
    extract(week  from w.week_start_date)::int          as week_of_year,
    w.total_hours,
    w.total_sessions,
    w.days_present,
    w.earliest_in,
    w.latest_out,
    w.avg_session_hours
from weekly w
