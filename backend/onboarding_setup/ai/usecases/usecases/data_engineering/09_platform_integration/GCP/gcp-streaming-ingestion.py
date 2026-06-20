# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE GCP streaming: Pub/Sub -> Dataflow -> BigQuery. Standard streaming-ingestion reference pattern,
# authored originally. No GCP operators ship — the agent generates them from the GCP skills.
payloads = {}

skills = {
    "00_gcp_streaming_ingestion.md": """\
# How to build a GCP streaming ingestion pipeline

A near-real-time flow: ingest events via **Pub/Sub**, process with a streaming **Dataflow** job, and sink
to **BigQuery** — with LeastAction managing the streaming job lifecycle and scheduled curation/quality on
the landed windows.

> No GCP operators ship in core. The agent **generates** them from the GCP skills —
> **`GCP_messaging_integration.md`** (Pub/Sub), **`GCP_analytics.md`** (Dataflow/BigQuery) — via Operator
> Dev, then wires this flow. Knowledge lives in the skills; the flow lives here.

## Prerequisites
- A GCP `connection` (project + service account).
- Generated operators (from GCP skills): a Pub/Sub topic/subscription op, a Dataflow launch op, a BigQuery
  query op. `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Service / generated operator | Does |
|---|---|---|
| 0 `ensure_topic` | Pub/Sub admin op | Create/verify the topic + subscription (idempotent) |
| 1 `start_stream_job` | Dataflow launch (streaming) | Launch the streaming Dataflow job: Pub/Sub -> BigQuery raw table |
| 2 `curate_bq` | BigQuery SQL (MERGE/CTAS) | On the batch cadence, dedupe/curate the `{{logical_date}}` window into a curated table |
| 3 `quality` (optional) | BigQuery SQL assertions | Gate the curated window on data-quality checks before consumers read it |

Steps 0-1 manage the always-on stream (run once / on change). Steps 2-3 run on the batch cadence over the
`{{logical_date}}` window and chain via `LeastActionCheckIfParentsAreDone`. Make step 2 idempotent
(`MERGE` on the key, or delete-the-partition then insert) so re-runs/backfills are safe.

## Variants
- **Batch lakehouse:** GCS -> Dataflow -> BigQuery — see `gcp-analytics-lakehouse`.
- **Dataflow templates:** launch a Google-provided or custom Flex template instead of a custom job.

## Verify
BigQuery `SELECT COUNT(*) ... WHERE dt = '{{logical_date}}'` on the curated table; confirm the Dataflow job
is RUNNING.

## Deploy
> "use the gcp-streaming-ingestion usecase to stream Pub/Sub events into BigQuery and curate hourly"
"""
,
}

prompt = (
    "How to use GCP streaming services as a LeastAction pipeline: ingest via Pub/Sub, process with a "
    "streaming Dataflow job into a BigQuery raw table, then on a batch cadence curate/dedupe the "
    "{{logical_date}} window with idempotent BigQuery MERGE/CTAS and optional DQ assertions. Stream-management "
    "steps run once/on-change; curation steps chain via LeastActionCheckIfParentsAreDone. No GCP operators "
    "ship in core, so the agent generates them from the GCP_messaging_integration and GCP_analytics skills."
)

description = (
    "Platform Integration (how-to-use): GCP near-real-time ingestion — Pub/Sub -> Dataflow -> BigQuery — "
    "with LeastAction managing the streaming job and curating landed windows idempotently. No GCP operators "
    "ship, so the agent generates them from the GCP skills."
)

guide_docs = """\
# GCP Streaming Ingestion (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow,
generates the GCP operators from the GCP skills, and implements it.

## The flow
Pub/Sub (ingest) -> Dataflow (stream) -> BigQuery (raw) -> BigQuery curate per `{{logical_date}}`,
with an optional DQ gate. Stream-management tasks run once/on-change; curation tasks chain via
`LeastActionCheckIfParentsAreDone` and are idempotent.

## Prerequisites
- GCP `connection`; reference skills `GCP_messaging_integration.md`, `GCP_analytics.md` (operators generated
  from these — none ship in core).

## Using
> "use the gcp-streaming-ingestion usecase to land Pub/Sub events in BigQuery and curate hourly"

For the batch path see `gcp-analytics-lakehouse`.
"""

publisher = "LeastAction"

metadata = {
    "service": "GCP Streaming",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "gcp", "pubsub", "dataflow", "bigquery", "streaming"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
