# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- stg_badge_events: incremental synthetic badge swipe events
-- Generates IN/OUT events for all students and teachers.
-- Sundays: everyone absent. Saturdays: 40% absent. Weekdays: 10% absent.
-- IN time: 07:00-10:00 random. OUT time: 14:00-19:00 random.

DROP TABLE IF EXISTS stg_badge_events CASCADE;

CREATE TABLE stg_badge_events AS
WITH all_badges AS (
    SELECT badge_id, 'student' AS person_type FROM students
    UNION ALL
    SELECT badge_id, 'teacher' AS person_type FROM teachers
),

dates AS (
    SELECT
        generate_series::date                          AS full_date,
        EXTRACT(DOW FROM generate_series)::int         AS day_of_week,
        EXTRACT(DOW FROM generate_series) IN (0, 6)   AS is_weekend
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
            WHEN d.day_of_week = 0              THEN false
            WHEN d.is_weekend AND random() < 0.4 THEN false
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
