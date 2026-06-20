# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = {
    "description": "Invoke dbt from LeastAction: DBTRunModel / DBTRunSelectModel against a DbtServer connection, per-model vs full-package, DBTImportModel auto-import. dbt code stays in the dbt project.",
    "content": """You are a LeastAction AI engineer. Help the user build operators, actions, and tasks that **invoke dbt** from LeastAction.

## The core rule
**dbt code lives in the dbt project, not in LeastAction.** LeastAction only *invokes* dbt. A dbt pipeline
in LeastAction therefore carries **model names + the invocation graph + a `DbtServer` connection** — never
raw model SQL in the task payload.

## Operators
| Operator | Payload | What it does |
|---|---|---|
| `DBTRunModel` | `{"model": "<model_name>"}` | Runs ONE dbt model by name (calls the dbt-server `/run-model`). |
| `DBTRunSelectModel` | `{"model": "<selector>"}` | Runs a dbt `--select` graph (e.g. `model+` = a model and its downstream). |

Both read the dbt-server URL from the connection and return dbt's `returncode`/`stdout`/`stderr`.

## Connection — `DbtServer`
Holds `dbt_server_url` (e.g. `http://host.docker.internal:8001` or `http://dbt-server:8001`). The operator
health-checks `/health` on initialize.

## Two ways to invoke
- **Per-file (each model):** one task per model with `DBTRunModel` + `{"model": "<name>"}`. Order tasks with
  `LeastActionCheckIfParentsAreDone` (parent = the upstream model's task). Gives LeastAction-level
  visibility/retry per model.
- **Full package:** a single task that runs the whole project (`dbt run`/`build`). The shipped operators are
  per-model — for a true full run use `DBTRunSelectModel` with a project-wide selector, or add a small
  "run all" operator. (Confirm what the dbt-server exposes.)
- **Auto-import a project:** the `DBTImportModel` action reads a dbt project, topologically sorts the model
  files, and creates one LeastAction task per model with dependencies already wired — the fastest way to turn
  an existing dbt project into a managed task graph.

## Make models testable (required)
Every model a `DBTRunModel` step references MUST have its SQL available — as a **skill** per model
(`NN_<model>.md`) — so a user can inspect and run it. Never ship a bare `{"model": "x"}` with no way to
see `x`. Ship each as a **proper dbt model**: a `SELECT` plus `{{ config(materialized='table') }}`, with
upstream referenced via `{{ ref('...') }}` / `{{ source(...) }}`. Do NOT include `DROP`/`CREATE`/`INSERT`
DDL — dbt handles materialization. Test with `dbt run --select <model>` (a `{{ ref }}` model can't run in
raw psql). If a model needs seeds, sources, or SQL UDFs, list them in the skill (UDFs via an
`on-run-start` hook).

## Header-correctness
A dbt step's header uses `operator_name: "DBTRunModel"` (or `DBTRunSelectModel`),
`connection_name: "DbtServer"`, and a `{"model": ...}` body. A step that hand-writes SQL via
`PostgresqlExecuteSQL` is NOT dbt — label it SQL-native instead.

## Concrete example
The `dbt-sales-reporting` usecase (03_transformation): seeds a fact table with `PostgresqlExecuteSQL`, runs
`fact_product_agg_daily_stage1/stage2/final` via `DBTRunModel`, reports with
`PostgresqlGenerateHtmlTableReport`, and includes each model's SQL as a skill.
""",
}

prompt = "AI skill for generating LeastAction operators, actions, and tasks that invoke dbt (DBTRunModel / DBTRunSelectModel / DBTImportModel)."

install_docs = "Attach as a skill to a LeastAction AI chat or task. Requires a running dbt-server and a DbtServer connection (dbt_server_url)."

guide_docs = "Guides the AI to invoke dbt from LeastAction: per-model runs (DBTRunModel), graph runs (DBTRunSelectModel), full-package, and auto-import (DBTImportModel) against a DbtServer connection. dbt code stays in the dbt project; ship each referenced model's SQL as a copyable skill for testing."

description = "AI skill — invoke dbt from LeastAction via DBTRunModel / DBTRunSelectModel / DBTImportModel against a DbtServer connection, with per-model vs full-package patterns and the model-SQL-in-skill rule."

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "AI Skill",
    "tags": ["dbt", "dbt-invocation", "DBTRunModel", "DBTImportModel", "transformation", "skill", "ai"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
