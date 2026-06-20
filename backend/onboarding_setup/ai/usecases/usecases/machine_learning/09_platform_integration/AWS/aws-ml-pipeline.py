# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE AWS SageMaker for an ML pipeline: S3 features -> process -> train -> register -> batch infer.
# Standard ML-pipeline reference pattern, authored originally. Per-operator detail = AWS ML/AI skill.
payloads = {}

skills = {
    "00_aws_ml_pipeline.md": """\
# How to build an AWS SageMaker ML pipeline

A train-and-score flow on **SageMaker**: prepare features from **S3**, run a processing job, train a
model, register a versioned model, then batch-score new data back to S3 (or stand up a real-time
endpoint) — each a LeastAction task chained with `LeastActionCheckIfParentsAreDone`.

> Per-operator authoring detail comes from the **`AWS_ml_ai.md`** and **`AWS_storage.md`** skills (the
> agent attaches them). This usecase is the assembly only.

## Prerequisites
- An AWS `connection` (region + IAM role with SageMaker + S3 access).
- Operators (core): `AWSSageMakerStartProcessingJob`, `AWSSageMakerStartTrainingJob`,
  `AWSSageMakerCreateModel`, `AWSSageMakerRegisterModelVersion`, `AWSSageMakerStartBatchTransform`
  (or `AWSSageMakerCreateEndpointConfig` + `AWSSageMakerCreateEndpoint` for real-time). S3 operators for
  data movement. `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Operator | Does |
|---|---|---|
| 0 `feature_prep` | `AWSSageMakerStartProcessingJob` | Transform raw `s3://.../raw/` into train/validation feature sets in S3 |
| 1 `train` | `AWSSageMakerStartTrainingJob` | Train on the prepared features; artifacts to `s3://.../model/{{logical_date}}/` |
| 2 `register` | `AWSSageMakerCreateModel` + `AWSSageMakerRegisterModelVersion` | Create the model + register a versioned entry in the Model Registry |
| 3 `batch_score` | `AWSSageMakerStartBatchTransform` | Batch-infer new data; predictions to `s3://.../predictions/{{logical_date}}/` |
| 3b `deploy` (alt) | `AWSSageMakerCreateEndpointConfig` + `AWSSageMakerCreateEndpoint` | For online serving instead of batch |

Steps chain via `LeastActionCheckIfParentsAreDone`; carry `{{logical_date}}` so each run is a dated,
reproducible training/scoring cycle (and backfillable — see `leastaction-pipelines-orchestration`).

## Variants
- **AutoML:** swap steps 0-1 for `AWSSageMakerStartAutoMLJob`.
- **Tuning:** insert `AWSSageMakerStartHyperparameterTuning` between prep and train.
- **Pipelines:** if you already have a SageMaker Pipeline, trigger it with `AWSSageMakerStartPipelineExecution`.

## Verify
`inspect_data` on `s3://.../predictions/{{logical_date}}/` (DuckDB `read_parquet`) to confirm scores
landed; check the Model Registry for the new version.

## Deploy
> "use the aws-ml-pipeline usecase to train and batch-score my churn model from S3 features"
"""
,
}

prompt = (
    "How to use AWS SageMaker as a LeastAction ML pipeline: AWSSageMakerStartProcessingJob prepares "
    "features from S3, AWSSageMakerStartTrainingJob trains a model, AWSSageMakerCreateModel + "
    "AWSSageMakerRegisterModelVersion register a versioned model, and AWSSageMakerStartBatchTransform "
    "batch-scores new data back to S3 (or CreateEndpointConfig+CreateEndpoint for online serving). Variants: "
    "StartAutoMLJob, StartHyperparameterTuning, StartPipelineExecution. Steps chain via "
    "LeastActionCheckIfParentsAreDone and carry {{logical_date}} for reproducible, backfillable cycles. "
    "Per-operator detail comes from the AWS_ml_ai and AWS_storage skills."
)

description = (
    "Platform Integration (how-to-use): an AWS SageMaker ML pipeline — S3 features -> processing -> "
    "training -> model registry -> batch inference (or online endpoint). Dated, reproducible cycles chained "
    "in LeastAction. Teaches the assembly; per-service detail comes from the AWS ML/AI skill."
)

guide_docs = """\
# AWS SageMaker ML Pipeline (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow and
implements it (attaching `AWS_ml_ai.md` / `AWS_storage.md`); content referenced, not copied.

## The flow
S3 features -> `StartProcessingJob` -> `StartTrainingJob` -> `CreateModel`/`RegisterModelVersion` ->
`StartBatchTransform` (or `CreateEndpoint`), chained via `LeastActionCheckIfParentsAreDone` and dated by
`{{logical_date}}`. Variants: AutoML, hyperparameter tuning, triggering an existing SageMaker Pipeline.

## Prerequisites
- AWS `connection` (SageMaker + S3 IAM); SageMaker + S3 operators (core); reference skill `AWS_ml_ai.md`.

## Using
> "use the aws-ml-pipeline usecase to train and batch-score my churn model"

The agent generates the SageMaker operators (attaching the AWS ML skill), wires the train->register->score
chain, and dates each cycle by logical_date.
"""

publisher = "LeastAction"

metadata = {
    "service": "AWS SageMaker",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "aws", "sagemaker", "ml", "training", "inference", "s3"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
