# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE GCP analytics services: GCS -> Dataflow/Dataproc -> BigQuery -> Looker. Standard lakehouse
# reference pattern, authored originally. No GCP operators ship — the agent generates them from GCP skills.
payloads = {}

skills = {
    "00_gcp_analytics_lakehouse.md": """\
# How to build a GCP analytics lakehouse pipeline

A worked, multi-service flow: land raw data in **GCS**, transform with **Dataflow** (or **Dataproc**),
load curated tables into **BigQuery**, and surface them in **Looker** — each a LeastAction task chained
with `LeastActionCheckIfParentsAreDone`.

> No GCP operators ship in core. The agent **generates** the needed operators from the GCP skills —
> **`GCP_storage.md`** (GCS), **`GCP_analytics.md`** (Dataflow/Dataproc/BigQuery/Looker) — using the
> Operator Dev flow, then wires them into this flow. Knowledge lives in the skills; the flow lives here.

## Prerequisites
- A GCP `connection` (project + service-account credentials).
- Generated operators (from the GCP skills): a GCS load/transfer op, a Dataflow/Dataproc launch op, a
  BigQuery load/query op (and a Looker refresh action if used). `LeastActionCheckIfParentsAreDone`.

## The flow
| Step | Service / generated operator | Does |
|---|---|---|
| 0 `land_raw` | GCS object/transfer | Land raw data in `gs://.../raw/{{logical_date}}/` |
| 1 `transform` | Dataflow job (or Dataproc Spark) | Clean/normalize raw -> curated `gs://.../curated/{{logical_date}}/` |
| 2 `load_bq` | BigQuery load / `bq load` (or external table) | Load the curated partition into a BigQuery table |
| 3 `model_bq` | BigQuery SQL (CTAS/MERGE) | Build marts/aggregates in BigQuery for the window |
| 4 `refresh_looker` | Looker API action | Refresh the Looker dashboard/PDT (or rely on live query) |

Step 0 has no pre-action; steps 1-4 each wait on the previous via `LeastActionCheckIfParentsAreDone`.
Carry `{{logical_date}}` so the whole pipeline is windowed and backfill-safe (see
`postgresql-events-ingestion`; `leastaction-pipelines-orchestration` for backfill).

## Variants (same building blocks)
- **Streaming:** Pub/Sub -> Dataflow -> BigQuery — see `gcp-streaming-ingestion`.
- **ELT-in-BigQuery:** skip Dataflow; load raw to BigQuery and do all transforms in BigQuery SQL (step 3).
- **Spark:** use Dataproc instead of Dataflow for step 1.

## Verify
`inspect_data` against the GCP connection: DuckDB `read_parquet('gs://.../curated/{{logical_date}}/')` for
the curated slice, and a BigQuery `SELECT COUNT(*)` for the load.

## Deploy
> "use the gcp-analytics-lakehouse usecase to build GCS -> Dataflow -> BigQuery -> Looker for <dataset>"

The agent generates each operator (attaching the GCP skills), wires the chain, and points tasks at your
GCP connection.
"""
,
}

prompt = (
    "How to use GCP analytics services as one LeastAction pipeline: land raw data in GCS, transform with "
    "Dataflow (or Dataproc Spark), load curated partitions into BigQuery, build marts with BigQuery SQL, and "
    "refresh Looker. No GCP operators ship in core, so the agent generates them from the GCP_storage and "
    "GCP_analytics skills via Operator Dev, then chains the tasks with LeastActionCheckIfParentsAreDone, "
    "windowed on {{logical_date}}. Variants: Pub/Sub->Dataflow->BigQuery streaming, ELT-in-BigQuery, Dataproc Spark."
)

description = (
    "Platform Integration (how-to-use): a GCP analytics lakehouse — GCS -> Dataflow/Dataproc -> BigQuery -> "
    "Looker — as chained LeastAction tasks. No GCP operators ship, so the agent generates them from the GCP "
    "skills. Teaches the assembly; per-service detail comes from the GCP skills."
)

guide_docs = """\
# GCP Analytics Lakehouse (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow,
generates the GCP operators from the GCP skills (none ship in core), and implements it. Content referenced,
not copied.

## The flow
GCS (land) -> Dataflow/Dataproc (transform) -> BigQuery (load + model) -> Looker (BI), each a task chained
via `LeastActionCheckIfParentsAreDone`, windowed on `{{logical_date}}`.

## Prerequisites
- A GCP `connection` (project + service account); reference skills `GCP_storage.md`, `GCP_analytics.md`
  (the agent generates the operators from these — no GCP operators ship in core).

## Using
> "use the gcp-analytics-lakehouse usecase to build GCS -> Dataflow -> BigQuery -> Looker for events"

Variants: streaming (`gcp-streaming-ingestion`), ELT-in-BigQuery, or Dataproc Spark.
"""

publisher = "LeastAction"

metadata = {
    "service": "GCP Analytics",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "gcp", "gcs", "dataflow", "bigquery", "looker", "lakehouse"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
