{{ config(materialized='table') }}

with all_badges as (
    select badge_id, 'student' as person_type from students
    union all
    select badge_id, 'teacher' as person_type from teachers
),

dates as (
    select
        generate_series::date                          as full_date,
        extract(dow from generate_series)::int         as day_of_week,
        extract(dow from generate_series) in (0, 6)    as is_weekend
    from generate_series('2026-01-01'::date, current_date, '1 day')
),

attendance as (
    select
        b.badge_id,
        b.person_type,
        d.full_date,
        d.day_of_week,
        d.is_weekend,
        case
            when d.day_of_week = 0               then false
            when d.is_weekend and random() < 0.4  then false
            when not d.is_weekend and random() < 0.1 then false
            else true
        end as is_present
    from all_badges b
    cross join dates d
),

events as (
    select
        badge_id,
        person_type,
        full_date,
        full_date + (interval '7 hours'  + (random() * interval '3 hours')) as in_time,
        full_date + (interval '14 hours' + (random() * interval '5 hours')) as out_time
    from attendance
    where is_present
)

select
    md5(badge_id || in_time::text  || 'IN')  as event_id,
    badge_id,
    in_time                                   as event_time,
    'IN'                                      as event_type
from events

union all

select
    md5(badge_id || out_time::text || 'OUT') as event_id,
    badge_id,
    out_time                                  as event_time,
    'OUT'                                     as event_type
from events
