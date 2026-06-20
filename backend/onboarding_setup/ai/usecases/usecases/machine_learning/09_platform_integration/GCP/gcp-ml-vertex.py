# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE GCP Vertex AI for an ML pipeline: BigQuery/GCS features -> Vertex training -> registry ->
# batch/online prediction. Standard ML reference pattern, authored originally. Operators generated from GCP skills.
payloads = {}

skills = {
    "00_gcp_ml_vertex.md": """\
# How to build a GCP Vertex AI ML pipeline

A train-and-score flow on **Vertex AI**: build features in **BigQuery** (or **GCS**), train a model, register
a versioned model, then batch-predict back to BigQuery/GCS (or deploy an online endpoint) — each a
LeastAction task chained with `LeastActionCheckIfParentsAreDone`.

> No GCP operators ship in core. The agent **generates** them from the GCP skills — **`GCP_ml_ai.md`**
> (Vertex AI), **`GCP_analytics.md`** (BigQuery), **`GCP_storage.md`** (GCS) — via Operator Dev, then wires
> the flow. Knowledge lives in the skills; the flow lives here.

## Prerequisites
- A GCP `connection` (project + service account with Vertex AI + BigQuery/GCS access).
- Generated operators (from GCP skills): a BigQuery query op, a Vertex training/pipeline launch op, a model
  registry op, a batch-prediction op (or endpoint deploy op). `LeastActionCheckIfParentsAreDone`.

## The flow
| Step | Service / generated operator | Does |
|---|---|---|
| 0 `features` | BigQuery SQL (CTAS) | Build the training/feature table for `{{logical_date}}` |
| 1 `train` | Vertex training / pipeline launch | Train (or run a Vertex Pipeline); artifacts to GCS/Model Registry |
| 2 `register` | Vertex Model Registry op | Register the new model version |
| 3 `batch_predict` | Vertex batch prediction | Score new data -> BigQuery/GCS predictions for the window |
| 3b `deploy` (alt) | Vertex endpoint deploy | For online serving instead of batch |

Steps chain via `LeastActionCheckIfParentsAreDone`; carry `{{logical_date}}` so each run is a dated,
reproducible cycle (backfillable — see `leastaction-pipelines-orchestration`).

## Variants
- **BQML:** for simple models, train/predict entirely in BigQuery SQL (`CREATE MODEL` / `ML.PREDICT`) — no Vertex.
- **AutoML:** use a Vertex AutoML training op instead of custom training.
- **Existing pipeline:** trigger a defined Vertex Pipeline instead of step 1.

## Verify
BigQuery `SELECT COUNT(*)` on the predictions table for `{{logical_date}}`; confirm the new model version in
the registry.

## Deploy
> "use the gcp-ml-vertex usecase to train and batch-score my model from BigQuery features"
"""
,
}

prompt = (
    "How to use GCP Vertex AI as a LeastAction ML pipeline: build features in BigQuery (or GCS), train (or run "
    "a Vertex Pipeline / AutoML), register a versioned model in the Vertex Model Registry, and batch-predict "
    "to BigQuery/GCS (or deploy an online endpoint). Variants: BQML (CREATE MODEL/ML.PREDICT in BigQuery), "
    "AutoML, triggering an existing Vertex Pipeline. Steps chain via LeastActionCheckIfParentsAreDone, dated by "
    "{{logical_date}}. No GCP operators ship in core, so the agent generates them from the GCP_ml_ai, "
    "GCP_analytics, and GCP_storage skills."
)

description = (
    "Platform Integration (how-to-use): a GCP Vertex AI ML pipeline — BigQuery/GCS features -> training -> "
    "model registry -> batch/online prediction (or BQML for simple models). Dated, reproducible cycles in "
    "LeastAction. Operators generated from the GCP skills."
)

guide_docs = """\
# GCP Vertex AI ML Pipeline (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow,
generates the GCP operators from the GCP skills, and implements it.

## The flow
BigQuery/GCS features -> Vertex training -> Model Registry -> batch/online prediction, chained via
`LeastActionCheckIfParentsAreDone` and dated by `{{logical_date}}`. Variants: BQML (all-in-BigQuery),
AutoML, or triggering an existing Vertex Pipeline.

## Prerequisites
- GCP `connection` (Vertex + BigQuery/GCS); reference skills `GCP_ml_ai.md`, `GCP_analytics.md`,
  `GCP_storage.md` (operators generated from these — none ship in core).

## Using
> "use the gcp-ml-vertex usecase to train and batch-score my churn model from BigQuery"
"""

publisher = "LeastAction"

metadata = {
    "service": "GCP Vertex AI",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "gcp", "vertex-ai", "bigquery", "ml", "training", "inference"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
