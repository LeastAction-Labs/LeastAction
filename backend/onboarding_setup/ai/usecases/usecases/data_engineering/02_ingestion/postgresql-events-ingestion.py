# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 02_ingestion  |  Flavor: S+P (skills + runnable payloads)
# Teaches the incremental / watermark ingestion pattern: load only the rows in the task's logical_date
# window, idempotently (delete-the-slice then insert), so re-runs and backfills are safe. Self-contained
# demo (seeds a source) but the pattern is the real takeaway.
payloads = {
    "00_setup.sql": """\
/*
{
  "name": "00_setup.sql",
  "frequency": "0 1 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
-- Target table (idempotent). In real use the SOURCE already exists upstream; the demo source block
-- below is only so this usecase runs end-to-end out of the box — delete it for a real ingestion.
CREATE TABLE IF NOT EXISTS fact_events_daily (
    event_id   BIGINT,
    user_id    BIGINT,
    event_type VARCHAR(100),
    amount     NUMERIC(12,2),
    event_date DATE,
    loaded_at  TIMESTAMP DEFAULT NOW()
);

-- DEMO SOURCE (remove for real ingestion): three rows stamped within the logical_date window.
CREATE TABLE IF NOT EXISTS source_events (
    event_id   BIGINT PRIMARY KEY,
    user_id    BIGINT,
    event_type VARCHAR(100),
    amount     NUMERIC(12,2),
    updated_at TIMESTAMP
);
INSERT INTO source_events (event_id, user_id, event_type, amount, updated_at) VALUES
    (1, 101, 'purchase', 49.99, '{{logical_date}}'::date + TIME '09:15'),
    (2, 102, 'refund',   -9.99, '{{logical_date}}'::date + TIME '10:30'),
    (3, 103, 'purchase', 19.50, '{{logical_date}}'::date + TIME '13:45')
ON CONFLICT (event_id) DO UPDATE
    SET updated_at = EXCLUDED.updated_at, amount = EXCLUDED.amount;
""",

    "01_incremental_load.sql": """\
/*
{
  "name": "01_incremental_load.sql",
  "frequency": "0 1 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
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
              "task_name": "00_setup.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
-- Incremental load, idempotent and backfill-safe:
--   1. clear this date's slice so a re-run/backfill does not duplicate rows
--   2. load ONLY the source rows whose watermark (updated_at) falls in the logical_date day window
DELETE FROM fact_events_daily WHERE event_date = '{{logical_date}}'::date;

INSERT INTO fact_events_daily (event_id, user_id, event_type, amount, event_date)
SELECT event_id, user_id, event_type, amount, '{{logical_date}}'::date
FROM source_events
WHERE updated_at >= '{{logical_date}}'::date
  AND updated_at <  '{{logical_date}}'::date + INTERVAL '1 day';
""",
}

skills = {
    "00_setup.md": """\
# Step 0 — Setup (target + demo source)

## Lifecycle & prerequisites
**Stage:** Ingestion (generation → ingestion). This usecase teaches **incremental** loading driven by
the task's `logical_date`, the safe default for batch ingestion.

**Prerequisites in core:** operator `PostgresqlExecuteSQL`, action `LeastActionCheckIfParentsAreDone`,
and a PostgreSQL `connection` (defaults to `postgresql`).

**Verify success:** after both steps for a date,
`SELECT event_date, COUNT(*) FROM fact_events_daily GROUP BY event_date` shows one row-group per loaded
date, and re-running the same date does NOT change the count (idempotent).

## What this step does
Creates the target `fact_events_daily` (idempotent `IF NOT EXISTS`). It also seeds a small demo
`source_events` table so the usecase runs out of the box. **In a real ingestion the source already
exists upstream — delete the demo-source block** and point step 1 at your real source.

## Adapting
- Replace the target schema with your real columns; keep an `event_date` (or partition) column so step 1
  can clear a single slice.
- For cross-database ingestion (source and target on different systems), see the
  `leastaction-crossdb-ingestion` usecase — the windowing pattern in step 1 is the same.
""",

    "01_incremental_load.md": """\
# Step 1 — Incremental load (watermark + idempotent)

## The pattern
Load only what changed in this run's window, and make the load **idempotent** so re-runs and backfills
never duplicate:
1. `DELETE FROM target WHERE event_date = '{{logical_date}}'` — clear this date's slice.
2. `INSERT ... SELECT ... WHERE updated_at >= '{{logical_date}}'::date AND updated_at < '{{logical_date}}'::date + INTERVAL '1 day'`
   — load only rows whose watermark falls in the logical_date day window.

Because the window is derived from `{{logical_date}}` (a task dimension), the SAME SQL backfills any
historical date correctly — run it for 2024-01-15 and it loads exactly that day. This is why the
`leastaction-pipelines-orchestration` usecase can replay thousands of dates with no code change.

## Why delete-then-insert
It is the simplest idempotent load: re-running a date replaces that date's slice exactly. Alternatives:
- **Upsert** (`INSERT ... ON CONFLICT (key) DO UPDATE`) when the target has a stable primary key and you
  want last-write-wins without a delete.
- **Append-only** when the source is immutable and you trust the watermark not to re-emit rows.

## Dependency
Waits for `00_setup.sql` via `LeastActionCheckIfParentsAreDone`.

## Adapting
- Change the watermark column (`updated_at`) and grain (day → hour) to match your source.
- For late-arriving data, widen the window (e.g. reprocess the last N days) and keep delete-then-insert.
- For CDC sources (log/timestamp/snapshot-diff), see the `postgresql-events-cdc` usecase — same idempotency goal,
  different change-capture mechanics.
"""
,
}

prompt = (
    "Incremental / watermark ingestion pipeline on PostgresqlExecuteSQL: step 0 creates the target table "
    "(and a demo source so it runs out of the box); step 1 loads only the source rows whose updated_at "
    "falls in the task's logical_date day window, using an idempotent delete-the-slice-then-insert so "
    "re-runs and backfills never duplicate. Step 1 depends on step 0 via LeastActionCheckIfParentsAreDone. "
    "Teaches the safe default for batch ingestion and pairs with the leastaction-pipelines-orchestration usecase."
)

description = (
    "Ingestion (S+P): the incremental/watermark pattern — load only the rows in the task's logical_date "
    "window, idempotently (delete-the-slice then insert), so re-runs and backfills are safe. Self-contained "
    "demo, but the windowed-idempotent pattern is the takeaway."
)

guide_docs = """\
# Incremental Ingestion

**Lifecycle stage:** Ingestion. **Flavor:** skills + runnable payloads. Teaches the safe default for
batch ingestion: load only what changed in the run's window, idempotently.

## Steps
| Step | File | Operator | What it does |
|---|---|---|---|
| 0 | `00_setup.sql` | `PostgresqlExecuteSQL` | Creates target `fact_events_daily` (+ a demo `source_events` so it runs out of the box) |
| 1 | `01_incremental_load.sql` | `PostgresqlExecuteSQL` | Clears this date's slice, then loads source rows whose `updated_at` is in the `{{logical_date}}` day window |

## The pattern
`DELETE FROM target WHERE event_date = '{{logical_date}}'` then
`INSERT ... SELECT ... WHERE updated_at >= '{{logical_date}}'::date AND updated_at < '{{logical_date}}'::date + INTERVAL '1 day'`.
Idempotent and backfill-safe: the window is derived from the task's `logical_date`, so the same SQL loads
any historical date exactly once. Pairs directly with the `leastaction-pipelines-orchestration` usecase.

## Prerequisites
- Operator `PostgresqlExecuteSQL` (core), action `LeastActionCheckIfParentsAreDone` (core),
  a PostgreSQL `connection` (default `postgresql`).

## Adapting to real sources
Delete the demo-source block in step 0 and point step 1 at your real source table. Swap the watermark
column/grain to match. Choose delete-then-insert (shown), upsert (`ON CONFLICT`), or append-only as fits
your source. For cross-system source→target, see `leastaction-crossdb-ingestion`; for change-data-capture,
see `postgresql-events-cdc`.

## Template variables
| Variable | Description |
|---|---|
| `{{logical_date}}` | The run's date — defines the load window and the target slice |
| `{{partition}}` | Task partition key |
| `{{account_laui}}` / `{{project_laui}}` | Resolved at runtime (used in the step-1 dependency) |

## Deploying
> "deploy usecase postgresql-events-ingestion"

Then run step 0, then step 1 for a date, and verify with `inspect_data`:
`SELECT event_date, COUNT(*) FROM fact_events_daily GROUP BY event_date`.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Ingestion",
    "tags": ["flavor:S+P", "lifecycle:ingestion", "incremental", "watermark", "idempotent", "backfill", "postgresql"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
