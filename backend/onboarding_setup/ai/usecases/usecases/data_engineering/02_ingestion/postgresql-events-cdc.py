# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 02_ingestion  |  Flavor: KB (skills-only knowledge bundle)
# Change-data-capture ingestion patterns (timestamp, log/LSN, snapshot-diff) with idempotent merge.
# The change-capture counterpart to postgresql-events-ingestion (windowed incremental load).
payloads = {}

skills = {
    "00_cdc_ingestion.md": """\
# CDC ingestion patterns

## Lifecycle & prerequisites
**Stage:** Ingestion. Knowledge bundle — the agent reads this and builds the right CDC pattern for the
source. Prerequisites: a `connection` to the source/target, `PostgresqlExecuteSQL` (or the relevant
engine operator), `LeastActionCheckIfParentsAreDone` for ordering. Builds on
`postgresql-events-ingestion` (the windowed incremental pattern) — read that first.

## When CDC vs plain incremental
Plain incremental (window on `{{logical_date}}`) is enough when rows are append-only or carry a reliable
`updated_at`. Use CDC when you must capture **updates and deletes** and the source changes between runs.

## Three capture mechanisms
| Mechanism | How changes are detected | Notes |
|---|---|---|
| **Timestamp / high-watermark** | `WHERE updated_at > {last_watermark}` | Simplest; misses hard deletes; needs a trustworthy `updated_at` |
| **Log-based (WAL/LSN/binlog)** | Read the DB change log (e.g. Postgres logical replication / Debezium) into a staging table, then merge | Captures inserts/updates/deletes + order; needs log access/tooling |
| **Snapshot-diff** | Compare today's snapshot to yesterday's (`EXCEPT` / hash compare) | Works on any source; expensive on large tables; catches deletes |

## Idempotent merge (target stays correct on re-run / backfill)
Whatever the capture, apply changes idempotently keyed on the primary key:
```sql
-- upsert (insert/update)
INSERT INTO target (id, col_a, col_b, updated_at)
SELECT id, col_a, col_b, updated_at FROM staged_changes
ON CONFLICT (id) DO UPDATE
  SET col_a = EXCLUDED.col_a, col_b = EXCLUDED.col_b, updated_at = EXCLUDED.updated_at
  WHERE EXCLUDED.updated_at >= target.updated_at;   -- last-write-wins

-- deletes (when the source emits them)
DELETE FROM target t USING staged_deletes d WHERE t.id = d.id;
```
Because the change set is derived from a watermark/log position tied to the run, re-running a date
re-applies the same changes safely. Track the watermark in a small state table or use the task's
`{{logical_date}}` window.

## Soft deletes & SCD
- Prefer **soft delete** (`is_deleted`/`deleted_at` flag) over physical delete when consumers need history.
- For slowly-changing dimensions (history of changes), close the prior version (`valid_to = now`) and
  insert the new version (`valid_from = now`) — SCD Type 2 — instead of an in-place update.

## Adapting
- Choose the mechanism by source capability: trustworthy `updated_at` -> timestamp; need deletes + order
  -> log-based; no metadata -> snapshot-diff.
- For cross-system CDC (source and target on different engines), stage the change set first — see
  `leastaction-crossdb-ingestion`.
- Order multi-step CDC (capture -> merge -> dedupe) with `LeastActionCheckIfParentsAreDone`.
""",
}

prompt = (
    "Knowledge bundle for change-data-capture ingestion in LeastAction. Covers when CDC beats plain "
    "windowed incremental (must capture updates+deletes), the three capture mechanisms (timestamp/high-"
    "watermark, log-based WAL/LSN/binlog into staging, snapshot-diff via EXCEPT/hash), idempotent merge "
    "(INSERT ... ON CONFLICT DO UPDATE with last-write-wins + delete handling) keyed on the primary key so "
    "re-runs/backfills stay correct, soft-deletes, and SCD Type 2. Builds on postgresql-events-ingestion."
)

description = (
    "Ingestion (KB): change-data-capture patterns — timestamp/high-watermark, log-based (WAL/LSN/binlog), "
    "and snapshot-diff — applied with an idempotent upsert/delete merge keyed on the PK so re-runs and "
    "backfills stay correct. Captures updates and deletes, not just appends. The CDC counterpart to incremental."
)

guide_docs = """\
# CDC Ingestion

**Lifecycle stage:** Ingestion. **Flavor:** skills-only knowledge bundle — the agent reads the skill and
builds the CDC pattern that fits the source; no tasks to deploy.

## What it teaches
Use CDC when you must capture updates and deletes (plain windowed incremental only handles appends well).
Three capture mechanisms — timestamp/high-watermark, log-based (WAL/LSN/binlog), snapshot-diff — all
applied with an **idempotent merge** (`ON CONFLICT DO UPDATE` last-write-wins + delete handling) keyed on
the primary key, so re-running a date is safe. Covers soft-deletes and SCD Type 2.

## Prerequisites
- A source/target `connection`, `PostgresqlExecuteSQL` (or engine operator), `LeastActionCheckIfParentsAreDone`.
- Read `postgresql-events-ingestion` first (the windowed incremental base pattern).

## Using
> "use the postgresql-events-cdc usecase to capture updates and deletes from orders into the warehouse"

The agent picks a capture mechanism by source capability and builds the staged-change + idempotent-merge
tasks. For cross-engine CDC see `leastaction-crossdb-ingestion`.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Ingestion",
    "tags": ["flavor:KB", "lifecycle:ingestion", "cdc", "change-data-capture", "merge", "upsert", "scd", "idempotent"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
