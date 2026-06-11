# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- int_multiday_sessions: cross-day IN/OUT session pairs
-- Captures sessions where IN is on Day 1 and OUT falls on Day 2+.
-- Edge case for overnight or forgotten badge-out scenarios.

DROP TABLE IF EXISTS int_multiday_sessions CASCADE;

CREATE TABLE int_multiday_sessions AS
WITH ordered_events AS (
    SELECT
        badge_id,
        event_time,
        event_type,
        event_time::date AS event_date,
        LEAD(event_time)       OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_time,
        LEAD(event_type)       OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_type,
        LEAD(event_time::date) OVER (PARTITION BY badge_id ORDER BY event_time) AS next_event_date
    FROM stg_badge_events
)

SELECT
    badge_id,
    event_date                                                       AS in_date,
    next_event_date                                                  AS out_date,
    event_time                                                       AS in_time,
    next_event_time                                                  AS out_time,
    EXTRACT(EPOCH FROM (next_event_time - event_time)) / 3600.0     AS session_hours
FROM ordered_events
WHERE
    event_type          = 'IN'
    AND next_event_type = 'OUT'
    AND next_event_date > event_date;

CREATE INDEX idx_multiday_sessions_badge_id ON int_multiday_sessions(badge_id);
CREATE INDEX idx_multiday_sessions_in_date  ON int_multiday_sessions(in_date);
'''
