# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
_00 = '''\
/*
{
  "name": "00_dbt_seed",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/

-- Seed step: creates students and teachers tables and loads static reference data.
-- Run once (ADHOC) before any incremental model runs.
-- 20 students across 6 departments, 10 teachers across 6 departments.

DROP TABLE IF EXISTS students CASCADE;
CREATE TABLE students (
    badge_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100),
    department  VARCHAR(100),
    year_or_sem INTEGER
);

INSERT INTO students (badge_id, name, department, year_or_sem) VALUES
('BADGE000001', 'Alice Johnson',    'Engineering', 1),
('BADGE000002', 'Bob Smith',        'Science',     2),
('BADGE000003', 'Carol White',      'Business',    3),
('BADGE000004', 'David Brown',      'Arts',        4),
('BADGE000005', 'Emma Davis',       'Medicine',    1),
('BADGE000006', 'Frank Miller',     'Law',         2),
('BADGE000007', 'Grace Wilson',     'Engineering', 3),
('BADGE000008', 'Henry Moore',      'Science',     4),
('BADGE000009', 'Iris Taylor',      'Business',    1),
('BADGE000010', 'Jack Anderson',    'Arts',        2),
('BADGE000011', 'Kate Thomas',      'Medicine',    3),
('BADGE000012', 'Liam Jackson',     'Law',         4),
('BADGE000013', 'Mia Harris',       'Engineering', 1),
('BADGE000014', 'Noah Martin',      'Science',     2),
('BADGE000015', 'Olivia Garcia',    'Business',    3),
('BADGE000016', 'Peter Martinez',   'Arts',        4),
('BADGE000017', 'Quinn Robinson',   'Medicine',    1),
('BADGE000018', 'Rachel Clark',     'Law',         2),
('BADGE000019', 'Sam Rodriguez',    'Engineering', 3),
('BADGE000020', 'Tina Lewis',       'Science',     4);

DROP TABLE IF EXISTS teachers CASCADE;
CREATE TABLE teachers (
    badge_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100),
    department  VARCHAR(100)
);

INSERT INTO teachers (badge_id, name, department) VALUES
('TEACHER00001', 'Dr. Alan Grant',    'Engineering'),
('TEACHER00002', 'Dr. Ellie Sattler', 'Science'),
('TEACHER00003', 'Dr. Ian Malcolm',   'Business'),
('TEACHER00004', 'Dr. John Hammond',  'Arts'),
('TEACHER00005', 'Dr. Sarah Harding', 'Medicine'),
('TEACHER00006', 'Dr. Robert Burke',  'Law'),
('TEACHER00007', 'Dr. Paul Kirby',    'Engineering'),
('TEACHER00008', 'Dr. Amanda Kirby',  'Science'),
('TEACHER00009', 'Dr. Billy Brennan', 'Business'),
('TEACHER00010', 'Dr. Eric Kirby',    'Arts');
'''

_01 = '''\
/*
{
  "name": "01_stg_badge_events",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "00_dbt_seed"
            }
          ]
        }
      }
    ]
  }
}
*/

-- stg_badge_events: synthetic badge swipe events for all students and teachers.
-- Sundays: always absent. Saturdays: 40% absent. Weekdays: 10% absent.
-- IN events: random between 07:00-10:00. OUT events: random between 14:00-19:00.
-- Covers 2026-01-01 to current date.

DROP TABLE IF EXISTS stg_badge_events CASCADE;

CREATE TABLE stg_badge_events AS
WITH all_badges AS (
    SELECT badge_id, 'student' AS person_type FROM students
    UNION ALL
    SELECT badge_id, 'teacher' AS person_type FROM teachers
),

dates AS (
    SELECT
        generate_series::date                            AS full_date,
        EXTRACT(DOW FROM generate_series)::int           AS day_of_week,
        EXTRACT(DOW FROM generate_series) IN (0, 6)     AS is_weekend
    FROM generate_series('2026-01-01'::date, CURRENT_DATE, '1 day')
),

attendance AS (
    SELECT
        b.badge_id,
        b.person_type,
        d.full_date,
        d.day_of_week,
        d.is_weekend,
        CASE
            WHEN d.day_of_week = 0               THEN false
            WHEN d.is_weekend AND random() < 0.4  THEN false
            WHEN NOT d.is_weekend AND random() < 0.1 THEN false
            ELSE true
        END AS is_present
    FROM all_badges b
    CROSS JOIN dates d
),

events AS (
    SELECT
        badge_id,
        person_type,
        full_date,
        full_date + (INTERVAL '7 hours'  + (random() * INTERVAL '3 hours')) AS in_time,
        full_date + (INTERVAL '14 hours' + (random() * INTERVAL '5 hours')) AS out_time
    FROM attendance
    WHERE is_present
)

SELECT
    md5(badge_id || in_time::text  || 'IN')  AS event_id,
    badge_id,
    in_time                                   AS event_time,
    'IN'                                      AS event_type
FROM events

UNION ALL

SELECT
    md5(badge_id || out_time::text || 'OUT') AS event_id,
    badge_id,
    out_time                                  AS event_time,
    'OUT'                                     AS event_type
FROM events;

CREATE INDEX idx_badge_events_badge_id   ON stg_badge_events(badge_id);
CREATE INDEX idx_badge_events_event_time ON stg_badge_events(event_time);
CREATE INDEX idx_badge_events_event_type ON stg_badge_events(event_type);
'''

_02 = '''\
/*
{
  "name": "02_int_badge_sessions",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/

-- int_badge_sessions: same-day IN/OUT session pairs.
-- Uses LEAD() to pair each IN event with the next OUT event on the same date.
-- Only clean same-day sessions included. session_hours computed in fractional hours.

DROP TABLE IF EXISTS int_badge_sessions CASCADE;

CREATE TABLE int_badge_sessions AS
WITH ordered_events AS (
    SELECT
        event_id,
        badge_id,
        event_time,
        event_type,
        event_time::date AS event_date,
        LEAD(event_time) OVER (PARTITION BY badge_id, event_time::date ORDER BY event_time) AS next_event_time,
        LEAD(event_type) OVER (PARTITION BY badge_id, event_time::date ORDER BY event_time) AS next_event_type
    FROM stg_badge_events
)

SELECT
    badge_id,
    event_date,
    event_time                                                    AS in_time,
    next_event_time                                               AS out_time,
    EXTRACT(EPOCH FROM (next_event_time - event_time)) / 3600.0  AS session_hours
FROM ordered_events
WHERE
    event_type          = 'IN'
    AND next_event_type = 'OUT'
    AND next_event_time::date = event_date;

CREATE INDEX idx_badge_sessions_badge_id   ON int_badge_sessions(badge_id);
CREATE INDEX idx_badge_sessions_event_date ON int_badge_sessions(event_date);
'''

_03 = '''\
/*
{
  "name": "03_int_multiday_sessions",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/

-- int_multiday_sessions: cross-day IN/OUT session pairs.
-- Captures sessions where IN is on Day 1 and OUT falls on Day 2+.
-- Edge case: overnight stays or forgotten badge-out. Allocated to the IN date in fct_attendance_daily.

DROP TABLE IF EXISTS int_multiday_sessions CASCADE;

CREATE TABLE int_multiday_sessions AS
WITH ordered_events AS (
    SELECT
        badge_id,
        event_time,
        event_type,
        event_time::date AS event_date,
        LEAD(event_time)        OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_time,
        LEAD(event_type)        OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_type,
        LEAD(event_time::date)  OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_date
    FROM stg_badge_events
)

SELECT
    badge_id,
    event_date                                                    AS in_date,
    next_event_date                                               AS out_date,
    event_time                                                    AS in_time,
    next_event_time                                               AS out_time,
    EXTRACT(EPOCH FROM (next_event_time - event_time)) / 3600.0  AS session_hours
FROM ordered_events
WHERE
    event_type          = 'IN'
    AND next_event_type = 'OUT'
    AND next_event_date > event_date;

CREATE INDEX idx_multiday_sessions_badge_id ON int_multiday_sessions(badge_id);
CREATE INDEX idx_multiday_sessions_in_date  ON int_multiday_sessions(in_date);
'''

_04 = '''\
/*
{
  "name": "04_int_absent_badges",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/

-- int_absent_badges: identifies badges with no events on a given date.
-- Cross joins all badges with all active event dates, then anti-joins against actual events.
-- Includes name, department, person_type for downstream reporting.

DROP TABLE IF EXISTS int_absent_badges CASCADE;

CREATE TABLE int_absent_badges AS
WITH all_badges AS (
    SELECT badge_id, name, department, 'student' AS person_type FROM students
    UNION ALL
    SELECT badge_id, name, department, 'teacher' AS person_type FROM teachers
),

active_dates AS (
    SELECT DISTINCT event_time::date AS event_date
    FROM stg_badge_events
),

badge_dates AS (
    SELECT
        b.badge_id,
        b.name,
        b.department,
        b.person_type,
        d.event_date
    FROM all_badges b
    CROSS JOIN active_dates d
),

present_badges AS (
    SELECT DISTINCT
        badge_id,
        event_time::date AS event_date
    FROM stg_badge_events
)

SELECT
    bd.badge_id,
    bd.name,
    bd.department,
    bd.person_type,
    bd.event_date
FROM badge_dates bd
LEFT JOIN present_badges pb
    ON bd.badge_id = pb.badge_id
    AND bd.event_date = pb.event_date
WHERE pb.badge_id IS NULL;

CREATE INDEX idx_absent_badges_badge_id   ON int_absent_badges(badge_id);
CREATE INDEX idx_absent_badges_event_date ON int_absent_badges(event_date);
'''

_05 = '''\
/*
{
  "name": "05_fct_attendance_daily",
  "frequency": "0 7 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "02_int_badge_sessions"
            },
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "03_int_multiday_sessions"
            }
          ]
        }
      }
    ]
  }
}
*/

-- fct_attendance_daily: one row per badge per day.
-- Combines int_badge_sessions (same-day) and int_multiday_sessions (overnight, allocated to IN date).
-- Outputs: date_id (YYYYMMDD int), full_date, total_hours, total_sessions, first_in_time, last_out_time, avg_session_hours.

DROP TABLE IF EXISTS fct_attendance_daily CASCADE;

CREATE TABLE fct_attendance_daily AS
WITH same_day AS (
    SELECT
        badge_id,
        event_date,
        SUM(session_hours)  AS total_hours,
        COUNT(*)            AS total_sessions,
        MIN(in_time)        AS first_in_time,
        MAX(out_time)       AS last_out_time
    FROM int_badge_sessions
    GROUP BY badge_id, event_date
),

multiday AS (
    SELECT
        badge_id,
        in_date             AS event_date,
        SUM(session_hours)  AS total_hours,
        COUNT(*)            AS total_sessions,
        MIN(in_time)        AS first_in_time,
        MAX(out_time)       AS last_out_time
    FROM int_multiday_sessions
    GROUP BY badge_id, in_date
),

combined AS (
    SELECT * FROM same_day
    UNION ALL
    SELECT * FROM multiday
),

aggregated AS (
    SELECT
        badge_id,
        event_date,
        SUM(total_hours)                                    AS total_hours,
        SUM(total_sessions)                                 AS total_sessions,
        MIN(first_in_time)                                  AS first_in_time,
        MAX(last_out_time)                                  AS last_out_time,
        SUM(total_hours) / NULLIF(SUM(total_sessions), 0)  AS avg_session_hours
    FROM combined
    GROUP BY badge_id, event_date
)

SELECT
    a.badge_id,
    TO_CHAR(a.event_date, 'YYYYMMDD')::int  AS date_id,
    a.event_date                             AS full_date,
    a.total_hours,
    a.total_sessions,
    a.first_in_time,
    a.last_out_time,
    a.avg_session_hours
FROM aggregated a;

CREATE INDEX idx_fct_daily_badge_id  ON fct_attendance_daily(badge_id);
CREATE INDEX idx_fct_daily_full_date ON fct_attendance_daily(full_date);
'''

_06 = '''\
/*
{
  "name": "06_fct_attendance_weekly",
  "frequency": "0 8 * * 0",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "05_fct_attendance_daily"
            }
          ]
        }
      }
    ]
  }
}
*/

-- fct_attendance_weekly: one row per badge per ISO week.
-- Aggregates fct_attendance_daily by week. Runs on Sundays (0 8 * * 0).
-- Equivalent to Airflow fact_attendance_bulk_dag weekly recalculation.

DROP TABLE IF EXISTS fct_attendance_weekly CASCADE;

CREATE TABLE fct_attendance_weekly AS
WITH weekly AS (
    SELECT
        badge_id,
        DATE_TRUNC('week', full_date)::date                       AS week_start_date,
        SUM(total_hours)                                          AS total_hours,
        SUM(total_sessions)                                       AS total_sessions,
        COUNT(DISTINCT full_date)                                 AS days_present,
        MIN(first_in_time)                                        AS earliest_in,
        MAX(last_out_time)                                        AS latest_out,
        SUM(total_hours) / NULLIF(SUM(total_sessions), 0)        AS avg_session_hours
    FROM fct_attendance_daily
    GROUP BY badge_id, DATE_TRUNC('week', full_date)::date
)

SELECT
    w.badge_id,
    w.week_start_date,
    w.week_start_date + 6                               AS week_end_date,
    EXTRACT(YEAR  FROM w.week_start_date)::int          AS year,
    EXTRACT(MONTH FROM w.week_start_date)::int          AS month,
    EXTRACT(WEEK  FROM w.week_start_date)::int          AS week_of_year,
    w.total_hours,
    w.total_sessions,
    w.days_present,
    w.earliest_in,
    w.latest_out,
    w.avg_session_hours
FROM weekly w;

CREATE INDEX idx_fct_weekly_badge_id        ON fct_attendance_weekly(badge_id);
CREATE INDEX idx_fct_weekly_week_start_date ON fct_attendance_weekly(week_start_date);
'''

_07 = '''\
/*
{
  "name": "07_mart_attendance_summary",
  "frequency": "0 7 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "dbt_postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "05_fct_attendance_daily"
            }
          ]
        }
      }
    ]
  }
}
*/

-- mart_attendance_summary: daily attendance report for the latest date.
-- Combines present + absent badges. Flags: still_on_campus, early_exit, absence_streak_days (3+).
-- Final mart consumed by downstream HTML report tasks (08-12).

DROP TABLE IF EXISTS mart_attendance_summary CASCADE;

CREATE TABLE mart_attendance_summary AS
WITH all_people AS (
    SELECT badge_id, name, department, 'student' AS person_type FROM students
    UNION ALL
    SELECT badge_id, name, department, 'teacher' AS person_type FROM teachers
),

latest_date AS (
    SELECT MAX(full_date) AS report_date FROM fct_attendance_daily
),

present_today AS (
    SELECT
        p.badge_id, p.name, p.department, p.person_type,
        f.full_date, f.total_hours, f.total_sessions,
        f.first_in_time, f.last_out_time, f.avg_session_hours,
        'present' AS attendance_status
    FROM fct_attendance_daily f
    INNER JOIN all_people p ON f.badge_id = p.badge_id
    INNER JOIN latest_date ld ON f.full_date = ld.report_date
),

absent_today AS (
    SELECT
        a.badge_id, a.name, a.department, a.person_type,
        a.event_date AS full_date,
        0.0 AS total_hours, 0 AS total_sessions,
        NULL::timestamp AS first_in_time, NULL::timestamp AS last_out_time,
        0.0 AS avg_session_hours,
        'absent' AS attendance_status
    FROM int_absent_badges a
    INNER JOIN latest_date ld ON a.event_date = ld.report_date
),

still_on_campus AS (
    SELECT p.badge_id
    FROM fct_attendance_daily f
    INNER JOIN all_people p ON f.badge_id = p.badge_id
    INNER JOIN latest_date ld ON f.full_date = ld.report_date
    WHERE EXTRACT(HOUR FROM f.last_out_time) < 17 OR f.last_out_time IS NULL
),

early_exits AS (
    SELECT p.badge_id
    FROM fct_attendance_daily f
    INNER JOIN all_people p ON f.badge_id = p.badge_id
    INNER JOIN latest_date ld ON f.full_date = ld.report_date
    WHERE EXTRACT(HOUR FROM f.last_out_time) BETWEEN 10 AND 14
),

absence_streaks AS (
    SELECT badge_id, MAX(consecutive_absent_days) AS consecutive_absent_days
    FROM (
        SELECT
            ab.badge_id,
            COUNT(*) AS consecutive_absent_days,
            ab.event_date - (ROW_NUMBER() OVER (PARTITION BY ab.badge_id ORDER BY ab.event_date) || ' days')::interval AS grp
        FROM int_absent_badges ab
        GROUP BY ab.badge_id,
                 ab.event_date - (ROW_NUMBER() OVER (PARTITION BY ab.badge_id ORDER BY ab.event_date) || ' days')::interval
        HAVING COUNT(*) >= 3
    ) a
    GROUP BY badge_id
)

SELECT
    COALESCE(pt.badge_id, ab.badge_id)                         AS badge_id,
    COALESCE(pt.name, ab.name)                                 AS name,
    COALESCE(pt.department, ab.department)                     AS department,
    COALESCE(pt.person_type, ab.person_type)                   AS person_type,
    COALESCE(pt.full_date, ab.full_date)                       AS report_date,
    COALESCE(pt.attendance_status, ab.attendance_status)       AS attendance_status,
    COALESCE(pt.total_hours, 0.0)                              AS total_hours,
    COALESCE(pt.total_sessions, 0)                             AS total_sessions,
    pt.first_in_time,
    pt.last_out_time,
    COALESCE(pt.avg_session_hours, 0.0)                        AS avg_session_hours,
    CASE WHEN sc.badge_id IS NOT NULL THEN true ELSE false END AS still_on_campus,
    CASE WHEN ee.badge_id IS NOT NULL THEN true ELSE false END AS early_exit,
    COALESCE(ast.consecutive_absent_days, 0)                   AS absence_streak_days
FROM present_today pt
FULL OUTER JOIN absent_today ab
    ON pt.badge_id = ab.badge_id AND pt.full_date = ab.full_date
LEFT JOIN still_on_campus sc ON COALESCE(pt.badge_id, ab.badge_id) = sc.badge_id
LEFT JOIN early_exits ee      ON COALESCE(pt.badge_id, ab.badge_id) = ee.badge_id
LEFT JOIN absence_streaks ast ON COALESCE(pt.badge_id, ab.badge_id) = ast.badge_id;

CREATE INDEX idx_mart_summary_badge_id    ON mart_attendance_summary(badge_id);
CREATE INDEX idx_mart_summary_report_date ON mart_attendance_summary(report_date);
CREATE INDEX idx_mart_summary_status      ON mart_attendance_summary(attendance_status);
'''

payloads = {
    "00_dbt_seed":              _00,
    "01_stg_badge_events":      _01,
    "02_int_badge_sessions":    _02,
    "03_int_multiday_sessions": _03,
    "04_int_absent_badges":     _04,
    "05_fct_attendance_daily":  _05,
    "06_fct_attendance_weekly": _06,
    "07_mart_attendance_summary": _07,
}

skills = {
    "00_dbt_seed.md": """\
# Step 0 — Seed: Students & Teachers

Creates the two static reference tables (`students`, `teachers`) and loads all seed data.
Run once with ADHOC frequency before any incremental model runs.

## Schema — students
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) PK | Unique badge identifier (BADGE000001–BADGE000020) |
| `name` | VARCHAR(100) | Full name |
| `department` | VARCHAR(100) | Engineering, Science, Business, Arts, Medicine, Law |
| `year_or_sem` | INTEGER | Academic year or semester (1–4) |

## Schema — teachers
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) PK | Unique badge identifier (TEACHER00001–TEACHER00010) |
| `name` | VARCHAR(100) | Full name with Dr. prefix |
| `department` | VARCHAR(100) | Engineering, Science, Business, Arts, Medicine, Law |

## Adapting this step
- **Add people**: Insert additional rows into the INSERT statements.
- **Add departments**: Add new department values — all downstream models use them as-is.
- **Real data**: Replace the INSERT blocks with `INSERT INTO students SELECT ... FROM your_source`.
- **No DROP**: Remove the `DROP TABLE IF EXISTS` lines to preserve existing data across runs.

## No dependencies
This step has no pre_actions — it always runs first.
""",

    "01_stg_badge_events.md": """\
# Step 1 — stg_badge_events: Synthetic Badge Swipe Events

Generates IN and OUT swipe events for all 30 badges (20 students + 10 teachers)
from 2026-01-01 to current date. Uses `random()` + cross join with a date series
to simulate realistic attendance patterns.

## Attendance simulation rules
| Day type | Absence probability |
|---|---|
| Sunday (DOW=0) | Always absent |
| Saturday (DOW=6) | 40% absent |
| Weekday | 10% absent |

- IN events: random time between 07:00 and 10:00
- OUT events: random time between 14:00 and 19:00

## Schema — stg_badge_events
| Column | Type | Description |
|---|---|---|
| `event_id` | TEXT | MD5 hash of badge_id + event_time + event_type |
| `badge_id` | VARCHAR(20) | FK to students or teachers |
| `event_time` | TIMESTAMP | Swipe timestamp |
| `event_type` | TEXT | 'IN' or 'OUT' |

## Adapting this step
- **Change date range**: Replace `'2026-01-01'` with your start date.
- **Change absence rates**: Modify the `random() < 0.4` / `0.1` thresholds.
- **Real data**: Replace this entire step with `INSERT INTO stg_badge_events SELECT ... FROM your_access_control_system`.

## Dependency
Waits for `00_dbt_seed` (`LeastActionCheckIfParentsAreDone`).
""",

    "02_int_badge_sessions.md": """\
# Step 2 — int_badge_sessions: Same-Day Session Pairs

Pairs each IN event with the next OUT event on the same calendar date using `LEAD()`.
Only clean same-day sessions are kept — cross-day sessions go to `int_multiday_sessions`.

## Schema — int_badge_sessions
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `event_date` | DATE | Date of the session |
| `in_time` | TIMESTAMP | Badge-in timestamp |
| `out_time` | TIMESTAMP | Badge-out timestamp |
| `session_hours` | FLOAT | Duration in fractional hours |

## Dependency
Waits for `01_stg_badge_events` (`LeastActionCheckIfParentsAreDone`).
""",

    "03_int_multiday_sessions.md": """\
# Step 3 — int_multiday_sessions: Cross-Day Session Pairs

Captures sessions where badge-IN is on Day 1 and badge-OUT falls on Day 2 or later.
These are allocated to the IN date in `fct_attendance_daily`.

## Schema — int_multiday_sessions
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `in_date` | DATE | Date of badge-in event |
| `out_date` | DATE | Date of badge-out event |
| `in_time` | TIMESTAMP | Badge-in timestamp |
| `out_time` | TIMESTAMP | Badge-out timestamp |
| `session_hours` | FLOAT | Duration in fractional hours |

## Dependency
Waits for `01_stg_badge_events` (`LeastActionCheckIfParentsAreDone`).
Runs in parallel with `02_int_badge_sessions`.
""",

    "04_int_absent_badges.md": """\
# Step 4 — int_absent_badges: Absent Badge Identification

Cross joins all badges with all active event dates, then anti-joins against actual
swipe events to identify which badges had no activity on each date.
Used in `mart_attendance_summary` for absence tracking and streak detection.

## Schema — int_absent_badges
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `name` | VARCHAR(100) | Person name |
| `department` | VARCHAR(100) | Department |
| `person_type` | TEXT | 'student' or 'teacher' |
| `event_date` | DATE | Date with no badge events |

## Dependency
Waits for `01_stg_badge_events` (`LeastActionCheckIfParentsAreDone`).
Runs in parallel with `02_int_badge_sessions` and `03_int_multiday_sessions`.
""",

    "05_fct_attendance_daily.md": """\
# Step 5 — fct_attendance_daily: Daily Attendance Grain

One row per badge per day. Combines same-day sessions (`int_badge_sessions`) and
overnight sessions (`int_multiday_sessions`, allocated to their IN date).

## Schema — fct_attendance_daily
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `date_id` | INTEGER | Date as YYYYMMDD integer |
| `full_date` | DATE | Calendar date |
| `total_hours` | FLOAT | Total hours on campus |
| `total_sessions` | INTEGER | Number of distinct IN/OUT pairs |
| `first_in_time` | TIMESTAMP | Earliest badge-in of the day |
| `last_out_time` | TIMESTAMP | Latest badge-out of the day |
| `avg_session_hours` | FLOAT | Average session duration |

## Dependency
Waits for both `02_int_badge_sessions` AND `03_int_multiday_sessions`
(`LeastActionCheckIfParentsAreDone` with two parents).
""",

    "06_fct_attendance_weekly.md": """\
# Step 6 — fct_attendance_weekly: Weekly Rollup

Aggregates `fct_attendance_daily` by ISO week. One row per badge per week.
Runs on Sundays (`0 8 * * 0`) to cover the completed week.
Equivalent to Airflow's `fact_attendance_bulk_dag`.

## Schema — fct_attendance_weekly
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `week_start_date` | DATE | Monday of the ISO week |
| `week_end_date` | DATE | Sunday of the ISO week |
| `year` | INTEGER | Calendar year |
| `month` | INTEGER | Calendar month of week start |
| `week_of_year` | INTEGER | ISO week number |
| `total_hours` | FLOAT | Total hours that week |
| `total_sessions` | INTEGER | Total sessions that week |
| `days_present` | INTEGER | Distinct days with attendance |
| `earliest_in` | TIMESTAMP | Earliest badge-in of the week |
| `latest_out` | TIMESTAMP | Latest badge-out of the week |
| `avg_session_hours` | FLOAT | Average session duration |

## Dependency
Waits for `05_fct_attendance_daily` (`LeastActionCheckIfParentsAreDone`).
""",

    "07_mart_attendance_summary.md": """\
# Step 7 — mart_attendance_summary: Final Daily Summary Mart

The terminal model. Combines present and absent badges for the latest date,
enriches with person details, and adds derived flags.
Consumed by all 5 downstream HTML report tasks (08–12).

## Schema — mart_attendance_summary
| Column | Type | Description |
|---|---|---|
| `badge_id` | VARCHAR(20) | Badge identifier |
| `name` | VARCHAR(100) | Person name |
| `department` | VARCHAR(100) | Department |
| `person_type` | TEXT | 'student' or 'teacher' |
| `report_date` | DATE | Latest date in fct_attendance_daily |
| `attendance_status` | TEXT | 'present' or 'absent' |
| `total_hours` | FLOAT | Hours on campus (0 if absent) |
| `total_sessions` | INTEGER | Sessions (0 if absent) |
| `first_in_time` | TIMESTAMP | First badge-in (null if absent) |
| `last_out_time` | TIMESTAMP | Last badge-out (null if absent) |
| `avg_session_hours` | FLOAT | Average session duration |
| `still_on_campus` | BOOLEAN | True if last_out_time before 17:00 |
| `early_exit` | BOOLEAN | True if last_out_time between 10:00–14:59 |
| `absence_streak_days` | INTEGER | Length of current consecutive absence streak (0 if no streak) |

## Dependency
Waits for `05_fct_attendance_daily` (`LeastActionCheckIfParentsAreDone`).
Runs in parallel with `06_fct_attendance_weekly`.
""",
}

prompt = (
    "Eight-step badge attendance pipeline: "
    "(0) seed students and teachers reference tables; "
    "(1) generate synthetic badge swipe events from 2026-01-01 to today; "
    "(2) pair same-day IN/OUT events into sessions; "
    "(3) capture cross-day overnight sessions; "
    "(4) identify absent badges by anti-joining all badges against events; "
    "(5) build daily attendance grain combining same-day and multiday sessions; "
    "(6) roll up to weekly attendance grain; "
    "(7) build final mart combining present/absent with flags for still-on-campus, "
    "early exits, and 3+ consecutive absence streaks. "
    "Steps 02-04 run in parallel after step 01. "
    "Steps 06-07 run in parallel after step 05. "
    "All steps use PostgresqlExecuteSQL on a dbt_postgresql connection, "
    "chained via LeastActionCheckIfParentsAreDone."
)

description = (
    "Badge attendance data pipeline built as a LeastAction usecase. "
    "Seeds 20 students and 10 teachers, generates synthetic daily swipe events "
    "with realistic absence patterns, transforms into session pairs, "
    "identifies absences, and builds daily and weekly attendance facts. "
    "Terminal mart combines present/absent status with department context "
    "and flags for still-on-campus, early exits, and consecutive absence streaks. "
    "Feeds 5 downstream HTML report tasks. "
    "Runs as an 8-task DAG using PostgresqlExecuteSQL, "
    "chained via LeastActionCheckIfParentsAreDone pre-actions."
)

guide_docs = """\
# dbtBadgeAttendancePipeline — Setup Guide

## What it does
Builds a complete badge attendance data mart in PostgreSQL across 8 sequential/parallel steps.

| Step | Task name | Output table | What it does |
|------|-----------|---|---|
| 0 | `00_dbt_seed` | `students`, `teachers` | Loads static reference data (run once) |
| 1 | `01_stg_badge_events` | `stg_badge_events` | Generates synthetic swipe events for all badges |
| 2 | `02_int_badge_sessions` | `int_badge_sessions` | Same-day IN/OUT pairs |
| 3 | `03_int_multiday_sessions` | `int_multiday_sessions` | Cross-day overnight sessions |
| 4 | `04_int_absent_badges` | `int_absent_badges` | Badges with no events per date |
| 5 | `05_fct_attendance_daily` | `fct_attendance_daily` | Daily grain: hours, sessions, in/out times |
| 6 | `06_fct_attendance_weekly` | `fct_attendance_weekly` | Weekly rollup |
| 7 | `07_mart_attendance_summary` | `mart_attendance_summary` | Final mart with presence flags |

## DAG structure
```
00_dbt_seed
 └── 01_stg_badge_events
      ├── 02_int_badge_sessions    ──┐
      ├── 03_int_multiday_sessions ──┤──► 05_fct_attendance_daily
      └── 04_int_absent_badges         ├── 06_fct_attendance_weekly
                                       └── 07_mart_attendance_summary
                                                └── (reports: 08-12 in dbtBadgeAttendanceReports)
```

## Prerequisites
- PostgreSQL instance accessible from LeastAction (use `host.docker.internal` if running in Docker)
- Connection named `dbt_postgresql` with fields: `host`, `port`, `database`, `user`, `password`
- Operator `PostgresqlExecuteSQL` installed
- Action `LeastActionCheckIfParentsAreDone` available

## Frequencies
| Task | Frequency | Notes |
|---|---|---|
| `00_dbt_seed` | ADHOC | Run once to load reference data |
| `01_stg_badge_events` | `0 6 * * *` | Daily at 06:00 |
| `02_int_badge_sessions` | `0 6 * * *` | Daily at 06:00 (parallel with 03, 04) |
| `03_int_multiday_sessions` | `0 6 * * *` | Daily at 06:00 |
| `04_int_absent_badges` | `0 6 * * *` | Daily at 06:00 |
| `05_fct_attendance_daily` | `0 7 * * *` | Daily at 07:00 (after 02+03 done) |
| `06_fct_attendance_weekly` | `0 8 * * 0` | Sundays at 08:00 |
| `07_mart_attendance_summary` | `0 7 * * *` | Daily at 07:00 (parallel with 06) |

## Deploying
Use the **Usecase Deploy Skill** in the LeastAction AI assistant:
> "deploy usecase dbtBadgeAttendancePipeline"

After this pipeline succeeds through step 07, deploy the reports usecase:
> "deploy usecase dbtBadgeAttendanceReports"
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Data Engineering",
    "tags": [
        "dbt", "badge", "attendance", "postgresql", "pipeline",
        "incremental", "sessions", "mart", "usecase",
    ],
    "airflow_equivalent": "BashOperator",
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
