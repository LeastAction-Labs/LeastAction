# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE AWS analytics services together as one pipeline: S3 -> Glue -> Athena/Redshift -> QuickSight.
# Per-service operator authoring detail lives in the AWS skills (referenced, not copied).
payloads = {}

skills = {
    "00_aws_analytics_lakehouse.md": """\
# How to build an AWS analytics lakehouse pipeline

A worked, multi-service flow: land raw data in **S3**, catalog it with **Glue**, transform with
**Athena** (or a Glue job), load curated marts into **Redshift**, and surface them in **QuickSight** —
each step a LeastAction task chained with `LeastActionCheckIfParentsAreDone`.

> This usecase teaches the *assembly*. For how to author each operator (fields, payloads, SDK calls),
> the agent attaches the per-service skills: **`AWS_storage.md`** (S3) and **`AWS_analytics.md`**
> (Glue/Athena/Redshift/QuickSight). Knowledge lives in the skills; the flow lives here.

## Prerequisites
- An AWS `connection` (region + IAM role or access keys) — all steps use it.
- Operators (core, under `operators/AWS/`): `AWSS3CreateObjectOperator`/`AWSS3CopyObjectOperator`,
  `AWSGlueCrawlerStart`, `AWSGlueStartJob`, `AWSGlueDataQualityRun`, `AWSAthenaExecuteSQL`,
  `AWSRedshiftDataExecuteSQL`. (No QuickSight operator ships — see step 5.)
- `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Operator | Payload (shape) | Does |
|---|---|---|---|
| 0 `land_raw` | `AWSS3CreateObjectOperator` | `{"bucket","key","body"}` (or upstream drops the file) | Land raw data in `s3://.../raw/{{logical_date}}/` |
| 1 `crawl` | `AWSGlueCrawlerStart` | `{"crawler_name"}` | Glue crawler catalogs the raw prefix into the Data Catalog |
| 2 `transform` | `AWSAthenaExecuteSQL` | `CREATE TABLE curated.x WITH (...) AS SELECT ... WHERE dt='{{logical_date}}'` | Athena CTAS writes a curated/partitioned table to S3 |
| 3 `quality` (optional) | `AWSGlueDataQualityRun` | `{"ruleset"/"table"}` | Gate on data-quality rules before loading |
| 4 `load_redshift` | `AWSRedshiftDataExecuteSQL` | `COPY curated.x FROM 's3://.../curated/{{logical_date}}/' IAM_ROLE '...' FORMAT AS PARQUET` | Load the curated mart into Redshift |
| 5 `dashboard` | (no operator) | — | Refresh QuickSight: a small custom action calling `boto3.client('quicksight').create_ingestion(...)` to reload the SPICE dataset; OR generate an HTML report from the Athena/Redshift result. See `AWS_analytics.md`. |

## Dependency chain
Step 0 has no pre-action; steps 1-5 each wait on the previous via `LeastActionCheckIfParentsAreDone`
(parents reference the previous step's task name, with `{{account_laui}}`/`{{project_laui}}`/`{{partition}}`).
Carry `{{logical_date}}` through every step so the whole pipeline is windowed and backfill-safe (see
`postgresql-events-ingestion` for the windowing/idempotency pattern; `leastaction-pipelines-orchestration`
for backfill).

## Variants (same building blocks)
- **Streaming:** Kinesis -> Firehose -> S3 -> (this flow from step 1). See `AWS_messaging_integration.md`.
- **Spark ETL:** swap step 2 for `AWSGlueStartJob` (a Glue Spark job) instead of Athena CTAS.
- **Lake-only:** stop at step 2 (curated S3 + Glue Catalog) and query via Athena — skip Redshift.

## Verify
Use `inspect_data` against the AWS connection (DuckDB `read_parquet('s3://.../curated/{{logical_date}}/')`)
to confirm the curated slice, and a Redshift `SELECT COUNT(*)` to confirm the load.

## How to deploy
Ask the agent: *"use the aws-analytics-lakehouse usecase to build an S3->Glue->Athena->Redshift pipeline
for <dataset>"*. It generates each operator (attaching `AWS_storage`/`AWS_analytics` skills), wires the
dependency chain, and points every task at your AWS connection.
""",
}

prompt = (
    "How to use AWS analytics services together as one LeastAction pipeline: land raw data in S3 "
    "(AWSS3CreateObjectOperator), catalog with Glue (AWSGlueCrawlerStart), transform with Athena CTAS "
    "(AWSAthenaExecuteSQL) or a Glue Spark job (AWSGlueStartJob), optionally gate on Glue Data Quality, "
    "load curated marts into Redshift (AWSRedshiftDataExecuteSQL COPY from S3), and refresh a QuickSight "
    "SPICE dataset via a boto3 custom action (no QuickSight operator ships). Steps chained with "
    "LeastActionCheckIfParentsAreDone and windowed on {{logical_date}}. Per-operator authoring detail comes "
    "from the AWS_storage and AWS_analytics skills, which the agent attaches during generation."
)

description = (
    "Platform Integration (how-to-use): build an AWS analytics lakehouse pipeline end to end — "
    "S3 -> Glue -> Athena/Redshift -> QuickSight — as chained LeastAction tasks. Teaches the assembly; "
    "per-service operator detail comes from the AWS skills (referenced, not copied)."
)

guide_docs = """\
# AWS Analytics Lakehouse (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads this flow and
implements it (Pattern 3), attaching the per-service AWS skills for operator detail. No content is copied
from the skills; this usecase is the *assembly* (which services, in what order, wired how).

## The flow
S3 (land) -> Glue (catalog/ETL) -> Athena or Redshift (transform/load) -> QuickSight (dashboard), each a
task chained via `LeastActionCheckIfParentsAreDone` and windowed on `{{logical_date}}`.

## Prerequisites
- An AWS `connection` (region + IAM role/keys).
- AWS operators under `operators/AWS/` (S3, Glue, Athena, Redshift) + `LeastActionCheckIfParentsAreDone`.
- Reference skills `AWS_storage.md`, `AWS_analytics.md` for per-operator authoring.

## Using
> "use the aws-analytics-lakehouse usecase to build S3 -> Glue -> Athena -> Redshift for clickstream"

The agent generates each operator (attaching the AWS skills), wires the chain, and points tasks at your
AWS connection. Variants: streaming (Kinesis->S3), Spark ETL (Glue job), or lake-only (stop at Athena).
"""

publisher = "LeastAction"

metadata = {
    "service": "AWS Analytics",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "aws", "s3", "glue", "athena", "redshift", "quicksight", "lakehouse"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
