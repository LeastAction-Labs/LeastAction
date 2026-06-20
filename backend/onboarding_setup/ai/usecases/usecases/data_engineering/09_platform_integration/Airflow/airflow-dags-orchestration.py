# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE Airflow from LeastAction: import DAGs from Git, trigger DAG runs via REST (AirflowDAGOperator),
# backfill by logical_date, and monitor. Authored originally. Per-operator detail = Airflow skill.
payloads = {}

skills = {
    "00_airflow_dags_orchestration.md": """\
# How to orchestrate Airflow DAGs from LeastAction

LeastAction can manage existing **Airflow** DAGs as first-class tasks: import a DAG inventory from Git,
trigger DAG runs over Airflow's REST API, backfill by logical date, and monitor — without changing the
Airflow project. The DAG code stays in Airflow; LeastAction drives and observes it.

> Per-operator detail (Airflow REST auth, JWT, endpoints) comes from the **`manage_airflow_dags.md`** skill —
> the agent attaches it. This usecase is the assembly only.

## Prerequisites
- An Airflow `connection` (base URL + auth; Airflow 3.x uses JWT — see the skill).
- Operator `AirflowDAGOperator` (core) — triggers a DAG run and polls to completion via REST.
- The `AirflowImportDAGFromGit` action (from the skill) if you want to auto-create one LeastAction task per
  DAG. `LeastActionCheckIfParentsAreDone` for cross-DAG ordering.

## The flow
| Step | Operator / action | Does |
|---|---|---|
| 0 `import_dags` (optional) | `AirflowImportDAGFromGit` action | Read the DAG inventory from a Git repo and create one LeastAction task per DAG, wired to `AirflowDAGOperator` |
| 1 `trigger_dag` | `AirflowDAGOperator` | Trigger a DAG run with `logical_date` = `{{logical_date}}`, poll until it succeeds/fails |
| 2 `dependent_dag` | `AirflowDAGOperator` | A downstream DAG that waits on step 1 via `LeastActionCheckIfParentsAreDone` |

`AirflowDAGOperator` payload carries the `dag_id` (and any conf). Passing `{{logical_date}}` as the run's
logical date makes LeastAction backfills map to Airflow DAG runs for the same date — backfill from
LeastAction (`leastaction-pipelines-orchestration`) replays Airflow runs per date.

## Why drive Airflow from LeastAction
- **Cross-DAG / cross-system dependencies** by primary key (a LeastAction task on DAG B waits on DAG A) —
  no Airflow cross-DAG sensors.
- **Unified backfill** across Airflow + non-Airflow tasks, by logical_date.
- **One control plane**: trigger, monitor, retry (`leastaction-pipelines-retry`), notify
  (`leastaction-pipelines-notify`) Airflow runs alongside everything else.

## Verify
Check the triggered DAG run state in Airflow (the operator polls it); confirm the LeastAction task reached
`success` for the `{{logical_date}}`.

## Deploy
> "use the airflow-dags-orchestration usecase to trigger my daily_sales Airflow DAG and gate a downstream DAG on it"
"""
,
}

prompt = (
    "How to orchestrate Airflow DAGs from LeastAction: optionally import a DAG inventory from Git with the "
    "AirflowImportDAGFromGit action (one LeastAction task per DAG), trigger DAG runs over Airflow's REST API "
    "with AirflowDAGOperator (passing logical_date = {{logical_date}}, polling to completion), gate downstream "
    "DAGs via LeastActionCheckIfParentsAreDone, and backfill by logical date so LeastAction backfills map to "
    "Airflow runs per date. Drive, monitor, retry, and notify Airflow runs alongside non-Airflow tasks from one "
    "control plane. Per-operator REST/JWT detail comes from the manage_airflow_dags skill."
)

description = (
    "Platform Integration (how-to-use): orchestrate existing Airflow DAGs from LeastAction — import from Git, "
    "trigger via AirflowDAGOperator (REST), cross-DAG dependencies, unified backfill by logical_date, and one "
    "control plane for retry/notify. DAG code stays in Airflow; LeastAction drives it."
)

guide_docs = """\
# Airflow DAG Orchestration (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow and
implements it (attaching `manage_airflow_dags.md`); content referenced, not copied.

## The flow
(Optional) `AirflowImportDAGFromGit` to create a task per DAG -> `AirflowDAGOperator` triggers a DAG run with
`logical_date` and polls it -> downstream DAGs gate via `LeastActionCheckIfParentsAreDone`. Backfill from
LeastAction maps to Airflow runs per date.

## Prerequisites
- An Airflow `connection` (base URL + JWT auth); operator `AirflowDAGOperator` (core); the
  `AirflowImportDAGFromGit` action for auto-import; reference skill `manage_airflow_dags.md`.

## Using
> "use the airflow-dags-orchestration usecase to trigger my Airflow DAG daily and gate a downstream DAG"

Compose with `leastaction-pipelines-retry` / `-notify` for resilience and alerts.
"""

publisher = "LeastAction"

metadata = {
    "service": "Apache Airflow",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "airflow", "dag", "rest", "git", "orchestration"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
