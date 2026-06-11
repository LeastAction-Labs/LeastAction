# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- int_badge_sessions: same-day IN/OUT session pairs
-- Pairs each IN event with the next OUT event on the same date using LEAD().
-- Only clean same-day sessions are included.

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
    event_time                                                       AS in_time,
    next_event_time                                                  AS out_time,
    EXTRACT(EPOCH FROM (next_event_time - event_time)) / 3600.0     AS session_hours
FROM ordered_events
WHERE
    event_type      = 'IN'
    AND next_event_type = 'OUT'
    AND next_event_time::date = event_date;

CREATE INDEX idx_badge_sessions_badge_id   ON int_badge_sessions(badge_id);
CREATE INDEX idx_badge_sessions_event_date ON int_badge_sessions(event_date);
'''
