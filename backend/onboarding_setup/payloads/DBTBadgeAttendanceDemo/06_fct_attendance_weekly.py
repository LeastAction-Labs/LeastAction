# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- fct_attendance_weekly: weekly rollup — one row per badge per week
-- Aggregates fct_attendance_daily by ISO week.
-- Equivalent to Airflow fact_attendance_bulk_dag (weekly recalculation).

DROP TABLE IF EXISTS fct_attendance_weekly CASCADE;

CREATE TABLE fct_attendance_weekly AS
WITH weekly AS (
    SELECT
        badge_id,
        DATE_TRUNC('week', full_date)::date                         AS week_start_date,
        SUM(total_hours)                                            AS total_hours,
        SUM(total_sessions)                                         AS total_sessions,
        COUNT(DISTINCT full_date)                                   AS days_present,
        MIN(first_in_time)                                          AS earliest_in,
        MAX(last_out_time)                                          AS latest_out,
        SUM(total_hours) / NULLIF(SUM(total_sessions), 0)          AS avg_session_hours
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
