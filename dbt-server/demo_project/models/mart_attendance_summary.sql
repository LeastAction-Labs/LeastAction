{{ config(materialized='table') }}

with all_people as (
    select badge_id, name, department, 'student' as person_type from students
    union all
    select badge_id, name, department, 'teacher' as person_type from teachers
),

latest_date as (
    select max(full_date) as report_date from {{ ref('fct_attendance_daily') }}
),

present_today as (
    select
        p.badge_id, p.name, p.department, p.person_type,
        f.full_date, f.total_hours, f.total_sessions,
        f.first_in_time, f.last_out_time, f.avg_session_hours,
        'present' as attendance_status
    from {{ ref('fct_attendance_daily') }} f
    inner join all_people p on f.badge_id = p.badge_id
    inner join latest_date ld on f.full_date = ld.report_date
),

absent_today as (
    select
        a.badge_id, a.name, a.department, a.person_type,
        a.event_date as full_date,
        0.0 as total_hours, 0 as total_sessions,
        null::timestamp as first_in_time, null::timestamp as last_out_time,
        0.0 as avg_session_hours,
        'absent' as attendance_status
    from {{ ref('int_absent_badges') }} a
    inner join latest_date ld on a.event_date = ld.report_date
),

still_on_campus as (
    select p.badge_id
    from {{ ref('fct_attendance_daily') }} f
    inner join all_people p on f.badge_id = p.badge_id
    inner join latest_date ld on f.full_date = ld.report_date
    where extract(hour from f.last_out_time) < 17 or f.last_out_time is null
),

early_exits as (
    select p.badge_id
    from {{ ref('fct_attendance_daily') }} f
    inner join all_people p on f.badge_id = p.badge_id
    inner join latest_date ld on f.full_date = ld.report_date
    where extract(hour from f.last_out_time) between 10 and 14
),

absence_numbered as (
    select
        ab.badge_id,
        ab.event_date,
        ab.event_date - (row_number() over (partition by ab.badge_id order by ab.event_date) * interval '1 day') as grp
    from {{ ref('int_absent_badges') }} ab
),

absence_streaks as (
    select badge_id, max(streak_len) as consecutive_absent_days
    from (
        select badge_id, grp, count(*) as streak_len
        from absence_numbered
        group by badge_id, grp
        having count(*) >= 3
    ) a
    group by badge_id
)

select
    coalesce(pt.badge_id, ab.badge_id)                         as badge_id,
    coalesce(pt.name, ab.name)                                 as name,
    coalesce(pt.department, ab.department)                     as department,
    coalesce(pt.person_type, ab.person_type)                   as person_type,
    coalesce(pt.full_date, ab.full_date)                       as report_date,
    coalesce(pt.attendance_status, ab.attendance_status)       as attendance_status,
    coalesce(pt.total_hours, 0.0)                              as total_hours,
    coalesce(pt.total_sessions, 0)                             as total_sessions,
    pt.first_in_time,
    pt.last_out_time,
    coalesce(pt.avg_session_hours, 0.0)                        as avg_session_hours,
    case when sc.badge_id is not null then true else false end as still_on_campus,
    case when ee.badge_id is not null then true else false end as early_exit,
    coalesce(ast.consecutive_absent_days, 0)                   as absence_streak_days
from present_today pt
full outer join absent_today ab
    on pt.badge_id = ab.badge_id and pt.full_date = ab.full_date
left join still_on_campus sc on coalesce(pt.badge_id, ab.badge_id) = sc.badge_id
left join early_exits ee      on coalesce(pt.badge_id, ab.badge_id) = ee.badge_id
left join absence_streaks ast on coalesce(pt.badge_id, ab.badge_id) = ast.badge_id
