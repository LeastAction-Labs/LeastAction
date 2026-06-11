# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- int_absent_badges: badges with no events on a given date
-- Cross joins all badges with all active dates, then anti-joins against actual events.
-- Used for absence tracking in mart_attendance_summary.

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
