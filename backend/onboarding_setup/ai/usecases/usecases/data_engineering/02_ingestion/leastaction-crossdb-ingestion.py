# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 02_ingestion  |  Flavor: KB (skills-only knowledge bundle)
# Move data ACROSS systems (e.g. Postgres -> S3 -> Redshift/BigQuery). A task uses one connection, so
# cross-system ingestion is a chain of single-connection tasks via a neutral staging hop.
payloads = {}

skills = {
    "00_crossdb_ingestion.md": """\
# Cross-system (multi-connection) ingestion

## Lifecycle & prerequisites
**Stage:** Ingestion. Knowledge bundle — the agent reads this and wires a cross-system move. Key fact: a
LeastAction **task uses exactly one `connection`**. So moving data between two systems is a *chain* of
single-connection tasks, ordered by `LeastActionCheckIfParentsAreDone`. Prerequisites: a `connection` per
system involved, and the operators for each (e.g. `PostgresqlExecuteSQL`, AWS S3/Redshift operators).

## The pattern: extract -> stage -> load
```
[extract]  src connection   -> write the {{logical_date}} slice to a neutral staging location (S3/GCS/file/staging table)
   |  (LeastActionCheckIfParentsAreDone)
   v
[load]     tgt connection   -> read the staged slice and merge into the target (idempotent)
```
The staging hop (object storage or a staging table) decouples the two engines — each task talks to one
system. Carry `{{logical_date}}` through so the move is windowed and backfill-safe (see
`postgresql-events-ingestion`), and make the load idempotent (delete-slice-then-insert or upsert).

## Choosing the staging hop
| Target/source pair | Typical neutral hop |
|---|---|
| Postgres -> Redshift/Snowflake | unload to S3 (Parquet/CSV) -> `COPY` into target |
| Postgres -> BigQuery | export to GCS -> `bq load` / external table |
| Any -> any (small data) | a staging table the load task reads via the target connection |
| Files/lake -> warehouse | `inspect_data`/operators that `read_parquet('s3://...')` then insert |

## Verifying / inspecting across systems
`inspect_data` is read-only and works against any catalog connection, including S3/GCS/Azure via DuckDB
(`read_parquet('s3://...')`). Use it to confirm the staged slice and the loaded target rows match.

## Why not one task with two connections
A task is scoped to one connection (the admin control boundary for what an operator may touch). Splitting
extract and load gives independent state, retries, and permissions per system, and a re-runnable staging
artifact. If you truly need a single operator that bridges two endpoints, put both endpoints in one
connection's `content` and have the operator read both — but the two-task chain is the recommended default.

## Adapting
- One extract + one load per source->target; chain with `LeastActionCheckIfParentsAreDone`.
- Reuse `postgresql-events-ingestion` (windowing/idempotency) and `postgresql-events-cdc` (updates/deletes)
  on each side; reuse the relevant `09_platform_integration` bundle for the cloud target's operators.
""",
}

prompt = (
    "Knowledge bundle for cross-system (multi-connection) ingestion in LeastAction. Because a task uses one "
    "connection, moving data between systems is a chain: an extract task (source connection) writes the "
    "{{logical_date}} slice to a neutral staging hop (S3/GCS/file/staging table), then a load task (target "
    "connection) reads it and merges idempotently, ordered by LeastActionCheckIfParentsAreDone. Covers "
    "choosing the staging hop per engine pair (unload-to-S3+COPY, export-to-GCS+bq load, staging table), "
    "verifying across systems with inspect_data (DuckDB read_parquet), and when to use one connection with "
    "two endpoints instead."
)

description = (
    "Ingestion (KB): move data across systems (Postgres -> S3 -> Redshift/BigQuery) as a chain of "
    "single-connection tasks through a neutral staging hop, windowed on logical_date and idempotent on load. "
    "Because a task uses one connection, cross-DB = extract -> stage -> load, ordered by parent checks."
)

guide_docs = """\
# Cross-System Ingestion

**Lifecycle stage:** Ingestion. **Flavor:** skills-only knowledge bundle — the agent reads the skill and
wires the extract->stage->load chain; no tasks to deploy.

## What it teaches
A LeastAction task uses one connection, so moving data between systems is a chain: extract (source conn)
writes the `{{logical_date}}` slice to a neutral hop (S3/GCS/file/staging table); load (target conn) reads
it and merges idempotently; ordered by `LeastActionCheckIfParentsAreDone`. The hop decouples the engines;
`inspect_data` (read-only, DuckDB for cloud files) verifies both sides match.

## Prerequisites
- A `connection` per system + their operators (e.g. `PostgresqlExecuteSQL`, AWS S3/Redshift operators).
- Reuse `postgresql-events-ingestion` (windowing/idempotency) on each side.

## Using
> "use the leastaction-crossdb-ingestion usecase to move daily orders from Postgres to Redshift"

The agent builds an unload-to-S3 extract task + a COPY load task, chained and windowed on logical_date.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Ingestion",
    "tags": ["flavor:KB", "lifecycle:ingestion", "cross-system", "multi-connection", "staging", "s3", "redshift", "bigquery"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
