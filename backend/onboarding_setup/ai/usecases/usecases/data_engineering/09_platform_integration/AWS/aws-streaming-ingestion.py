# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE AWS streaming services: Kinesis -> S3 (lake) -> Glue -> Athena. Standard streaming-ingestion
# (lambda-architecture style) reference pattern, authored originally. Per-operator detail = AWS skills.
payloads = {}

skills = {
    "00_aws_streaming_ingestion.md": """\
# How to build an AWS streaming ingestion pipeline

A near-real-time ingestion flow: capture events with **Kinesis**, land them in **S3** as the durable
lake, then catalog (**Glue**) and query (**Athena**) the landed data on a schedule — the batch side of a
lambda-style architecture. LeastAction orchestrates the management/curation steps; the stream itself runs
continuously in Kinesis.

> Per-operator authoring detail comes from the **`AWS_messaging_integration.md`** (Kinesis) and
> **`AWS_storage.md`** / **`AWS_analytics.md`** (S3/Glue/Athena) skills — the agent attaches them.
> This usecase is the assembly only.

## Prerequisites
- An AWS `connection` (region + IAM role/keys).
- Operators (core): `AWSKinesisAnalyticsV2CreateApplication`/`AWSKinesisAnalyticsV2StartApplication`,
  `AWSS3CreateObjectOperator`, `AWSGlueCrawlerStart`, `AWSAthenaExecuteSQL`,
  `AWSGlueDataQualityRun` (optional). `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Operator | Does |
|---|---|---|
| 0 `ensure_stream_app` | `AWSKinesisAnalyticsV2CreateApplication` | Create the Kinesis Analytics app (idempotent) that reads the stream and writes records to S3 |
| 1 `start_stream_app` | `AWSKinesisAnalyticsV2StartApplication` | Start the streaming app so events land continuously in `s3://.../raw/` |
| 2 `crawl_landed` | `AWSGlueCrawlerStart` | Catalog the new `s3://.../raw/dt={{logical_date}}/` partition |
| 3 `curate` | `AWSAthenaExecuteSQL` | Athena CTAS/INSERT to build a curated/deduped partition for the window |
| 4 `quality` (optional) | `AWSGlueDataQualityRun` | Gate the curated partition on DQ rules before it is consumed |

Steps 0-1 manage the always-on stream (run once / on change). Steps 2-4 run on the batch cadence
(e.g. hourly) over the `{{logical_date}}` window and chain via `LeastActionCheckIfParentsAreDone`.

## Notes
- There is no dedicated Firehose operator — either configure the Kinesis Analytics app to sink to S3, or
  add a small custom action calling `boto3.client('firehose')` if you use Firehose. (See
  `AWS_messaging_integration.md`.)
- Exactly-once / dedup: make step 3 idempotent (delete-the-partition then insert) so re-runs are safe —
  same pattern as `postgresql-events-ingestion`.

## Verify
`inspect_data` with DuckDB `read_parquet('s3://.../curated/dt={{logical_date}}/')` to confirm the curated
window; check Glue Catalog partitions exist.

## Deploy
> "use the aws-streaming-ingestion usecase to land my Kinesis clickstream in S3 and curate hourly"
"""
,
}

prompt = (
    "How to use AWS streaming services as a LeastAction pipeline: a Kinesis Analytics app "
    "(AWSKinesisAnalyticsV2CreateApplication/StartApplication) reads the stream and lands events in S3; "
    "then on a batch cadence Glue crawls the new partition (AWSGlueCrawlerStart), Athena curates/dedupes it "
    "(AWSAthenaExecuteSQL CTAS, idempotent per {{logical_date}}), and an optional AWSGlueDataQualityRun "
    "gates it. Stream-management steps run once/on-change; curation steps chain via "
    "LeastActionCheckIfParentsAreDone. No Firehose operator ships — sink via the Kinesis app or a boto3 "
    "custom action. Per-operator detail comes from the AWS messaging/storage/analytics skills."
)

description = (
    "Platform Integration (how-to-use): AWS near-real-time ingestion — Kinesis -> S3 lake -> Glue -> Athena "
    "(batch side of a lambda architecture). Stream runs continuously; LeastAction curates the landed windows "
    "idempotently. Teaches the assembly; per-service detail comes from the AWS skills."
)

guide_docs = """\
# AWS Streaming Ingestion (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow and
implements it (attaching the AWS messaging/storage/analytics skills); content is referenced, not copied.

## The flow
Kinesis (capture) -> S3 (durable lake) -> Glue (catalog) -> Athena (curate per `{{logical_date}}`),
with an optional Glue Data Quality gate. Stream-management tasks run once/on-change; curation tasks run
on the batch cadence and chain via `LeastActionCheckIfParentsAreDone`.

## Prerequisites
- AWS `connection`; Kinesis/S3/Glue/Athena operators (core); reference skills
  `AWS_messaging_integration.md`, `AWS_storage.md`, `AWS_analytics.md`.

## Using
> "use the aws-streaming-ingestion usecase to ingest my Kinesis stream into an S3 lake and curate it hourly"

The agent generates the operators (attaching the AWS skills), wires stream-management + curation tasks,
and makes the curation idempotent per window. For the batch-only analytics path see `aws-analytics-lakehouse`.
"""

publisher = "LeastAction"

metadata = {
    "service": "AWS Streaming",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "aws", "kinesis", "s3", "glue", "athena", "streaming"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
