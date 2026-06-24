{{ config(materialized='table') }}

with ordered_events as (
    select
        badge_id,
        event_time,
        event_type,
        event_time::date as event_date,
        lead(event_time)        over (partition by badge_id order by event_time) as next_event_time,
        lead(event_type)        over (partition by badge_id order by event_time) as next_event_type,
        lead(event_time::date)  over (partition by badge_id order by event_time) as next_event_date
    from {{ ref('stg_badge_events') }}
)

select
    badge_id,
    event_date                                                    as in_date,
    next_event_date                                               as out_date,
    event_time                                                    as in_time,
    next_event_time                                               as out_time,
    extract(epoch from (next_event_time - event_time)) / 3600.0  as session_hours
from ordered_events
where
    event_type          = 'IN'
    and next_event_type = 'OUT'
    and next_event_date > event_date
