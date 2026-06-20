{{ config(materialized='table') }}

with all_badges as (
    select badge_id, name, department, 'student' as person_type from students
    union all
    select badge_id, name, department, 'teacher' as person_type from teachers
),

active_dates as (
    select distinct event_time::date as event_date
    from {{ ref('stg_badge_events') }}
),

badge_dates as (
    select
        b.badge_id,
        b.name,
        b.department,
        b.person_type,
        d.event_date
    from all_badges b
    cross join active_dates d
),

present_badges as (
    select distinct
        badge_id,
        event_time::date as event_date
    from {{ ref('stg_badge_events') }}
)

select
    bd.badge_id,
    bd.name,
    bd.department,
    bd.person_type,
    bd.event_date
from badge_dates bd
left join present_badges pb
    on bd.badge_id = pb.badge_id
    and bd.event_date = pb.event_date
where pb.badge_id is null
