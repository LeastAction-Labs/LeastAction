# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- mart_attendance_summary: daily attendance report — one row per badge for the latest date
-- Combines present + absent badges, enriches with department and person_type.
-- Flags: still_on_campus, early_exit, absence_streak_days.
-- Covers: present today, absent today, still on campus, early exits, 3+ day absence streaks.

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
        p.badge_id,
        p.name,
        p.department,
        p.person_type,
        f.full_date,
        f.total_hours,
        f.total_sessions,
        f.first_in_time,
        f.last_out_time,
        f.avg_session_hours,
        'present' AS attendance_status
    FROM fct_attendance_daily f
    INNER JOIN all_people p ON f.badge_id = p.badge_id
    INNER JOIN latest_date ld ON f.full_date = ld.report_date
),

absent_today AS (
    SELECT
        a.badge_id,
        a.name,
        a.department,
        a.person_type,
        a.event_date             AS full_date,
        0.0                      AS total_hours,
        0                        AS total_sessions,
        NULL::timestamp          AS first_in_time,
        NULL::timestamp          AS last_out_time,
        0.0                      AS avg_session_hours,
        'absent'                 AS attendance_status
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
    SELECT
        a.badge_id,
        MAX(a.consecutive_absent_days) AS consecutive_absent_days
    FROM (
        SELECT
            ab.badge_id,
            ab.name,
            ab.department,
            ab.person_type,
            COUNT(*) AS consecutive_absent_days,
            ab.event_date - (ROW_NUMBER() OVER (PARTITION BY ab.badge_id ORDER BY ab.event_date) || ' days')::interval AS grp
        FROM int_absent_badges ab
        GROUP BY ab.badge_id, ab.name, ab.department, ab.person_type,
                 ab.event_date - (ROW_NUMBER() OVER (PARTITION BY ab.badge_id ORDER BY ab.event_date) || ' days')::interval
        HAVING COUNT(*) >= 3
    ) a
    GROUP BY a.badge_id
)

SELECT
    COALESCE(pt.badge_id, ab.badge_id)                          AS badge_id,
    COALESCE(pt.name, ab.name)                                  AS name,
    COALESCE(pt.department, ab.department)                      AS department,
    COALESCE(pt.person_type, ab.person_type)                    AS person_type,
    COALESCE(pt.full_date, ab.full_date)                        AS report_date,
    COALESCE(pt.attendance_status, ab.attendance_status)        AS attendance_status,
    COALESCE(pt.total_hours, 0.0)                               AS total_hours,
    COALESCE(pt.total_sessions, 0)                              AS total_sessions,
    pt.first_in_time,
    pt.last_out_time,
    COALESCE(pt.avg_session_hours, 0.0)                         AS avg_session_hours,
    CASE WHEN sc.badge_id IS NOT NULL THEN true ELSE false END  AS still_on_campus,
    CASE WHEN ee.badge_id IS NOT NULL THEN true ELSE false END  AS early_exit,
    COALESCE(ast.consecutive_absent_days, 0)                    AS absence_streak_days
FROM present_today pt
FULL OUTER JOIN absent_today ab
    ON pt.badge_id = ab.badge_id AND pt.full_date = ab.full_date
LEFT JOIN still_on_campus sc  ON COALESCE(pt.badge_id, ab.badge_id) = sc.badge_id
LEFT JOIN early_exits ee       ON COALESCE(pt.badge_id, ab.badge_id) = ee.badge_id
LEFT JOIN absence_streaks ast  ON COALESCE(pt.badge_id, ab.badge_id) = ast.badge_id;

CREATE INDEX idx_mart_summary_badge_id    ON mart_attendance_summary(badge_id);
CREATE INDEX idx_mart_summary_report_date ON mart_attendance_summary(report_date);
CREATE INDEX idx_mart_summary_status      ON mart_attendance_summary(attendance_status);
'''
