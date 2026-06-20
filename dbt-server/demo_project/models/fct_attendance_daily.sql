{{ config(materialized='table') }}

with same_day as (
    select
        badge_id,
        event_date,
        sum(session_hours)  as total_hours,
        count(*)            as total_sessions,
        min(in_time)        as first_in_time,
        max(out_time)       as last_out_time
    from {{ ref('int_badge_sessions') }}
    group by badge_id, event_date
),

multiday as (
    select
        badge_id,
        in_date             as event_date,
        sum(session_hours)  as total_hours,
        count(*)            as total_sessions,
        min(in_time)        as first_in_time,
        max(out_time)       as last_out_time
    from {{ ref('int_multiday_sessions') }}
    group by badge_id, in_date
),

combined as (
    select * from same_day
    union all
    select * from multiday
),

aggregated as (
    select
        badge_id,
        event_date,
        sum(total_hours)                                    as total_hours,
        sum(total_sessions)                                 as total_sessions,
        min(first_in_time)                                  as first_in_time,
        max(last_out_time)                                  as last_out_time,
        sum(total_hours) / nullif(sum(total_sessions), 0)  as avg_session_hours
    from combined
    group by badge_id, event_date
)

select
    a.badge_id,
    to_char(a.event_date, 'YYYYMMDD')::int  as date_id,
    a.event_date                             as full_date,
    a.total_hours,
    a.total_sessions,
    a.first_in_time,
    a.last_out_time,
    a.avg_session_hours
from aggregated a
