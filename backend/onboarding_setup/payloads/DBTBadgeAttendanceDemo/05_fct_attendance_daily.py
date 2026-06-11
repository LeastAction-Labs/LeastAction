# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- fct_attendance_daily: daily attendance grain — one row per badge per day
-- Combines same-day sessions (int_badge_sessions) and
-- allocates multiday sessions to their IN date.

DROP TABLE IF EXISTS fct_attendance_daily CASCADE;

CREATE TABLE fct_attendance_daily AS
WITH same_day AS (
    SELECT
        badge_id,
        event_date,
        SUM(session_hours)   AS total_hours,
        COUNT(*)             AS total_sessions,
        MIN(in_time)         AS first_in_time,
        MAX(out_time)        AS last_out_time
    FROM int_badge_sessions
    GROUP BY badge_id, event_date
),

multiday AS (
    SELECT
        badge_id,
        in_date              AS event_date,
        SUM(session_hours)   AS total_hours,
        COUNT(*)             AS total_sessions,
        MIN(in_time)         AS first_in_time,
        MAX(out_time)        AS last_out_time
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
        SUM(total_hours)                                        AS total_hours,
        SUM(total_sessions)                                     AS total_sessions,
        MIN(first_in_time)                                      AS first_in_time,
        MAX(last_out_time)                                      AS last_out_time,
        SUM(total_hours) / NULLIF(SUM(total_sessions), 0)      AS avg_session_hours
    FROM combined
    GROUP BY badge_id, event_date
)

SELECT
    a.badge_id,
    TO_CHAR(a.event_date, 'YYYYMMDD')::int     AS date_id,
    a.event_date                                AS full_date,
    a.total_hours,
    a.total_sessions,
    a.first_in_time,
    a.last_out_time,
    a.avg_session_hours
FROM aggregated a;

CREATE INDEX idx_fct_daily_badge_id  ON fct_attendance_daily(badge_id);
CREATE INDEX idx_fct_daily_full_date ON fct_attendance_daily(full_date);
'''
