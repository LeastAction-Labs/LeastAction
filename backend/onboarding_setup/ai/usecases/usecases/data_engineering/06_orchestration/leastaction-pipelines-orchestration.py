# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 06_orchestration  |  Flavor: KB (skills-only knowledge bundle — no payloads)
# Teaches backfilling thousands of runs and managing pipelines at scale, because in LeastAction the
# date is a DIMENSION of a task (logical_date), not baked into the run. Covers backfill methods,
# dependency checking, cross-project deps, partitions, and catch-up.
payloads = {}

skills = {
    "00_overview.md": """\
# Backfill & scale — overview & prerequisites

## Lifecycle stage
Orchestration. **Knowledge bundle** (no payloads): an AI agent reads these skills and applies the
patterns to existing tasks/workflows.

## The core idea
Elsewhere (Airflow/Prefect/Dagster) the execution date is coupled to the run, so backfill means
replaying historical runs. In LeastAction the date is a **dimension** of the task — `logical_date` is
*assigned* at import or schedule time, not embedded in code. The same operator/SQL/Python runs for any
date you give it. That single decision makes backfill, reschedule, and parallel partitions simple.

## Prerequisites in core
- Action `LeastActionCheckIfParentsAreDone` (core) for dependency ordering.
- Action `LeastActionGitToTask` (core) if backfilling by import (Option 1 in skill 01).
- The target workflow/tasks to backfill or reschedule.

## Verify success
After a backfill, the table/graph view shows one task instance per date with `state=success`, and each
date's child ran only after that date's parent succeeded (not after today's parent).
""",

    "01_backfill_methods.md": """\
# Backfilling — two methods + catch-up

## Why it's one action here
The date is not baked into the task; it is set per instance. So backfilling N dates = creating N
instances, each with its own `logical_date`. No code change.

## Option 1 — set the date at import (LeastActionGitToTask)
When importing tasks from git, set `logical_date` in the import payload. Backfill a range by looping the
import over dates (or invoking once per date):
```json
{ "repo_url": "https://github.com/your-org/your-pipeline", "branch": "main",
  "sub_path": "daily_finance_pipeline", "workflow_name": "finance_daily", "logical_date": "2024-01-15" }
```
Each date creates its own instances; dependencies hold for every date automatically.

## Option 2 — bulk reschedule (UI action)
If tasks already exist, select them in the table view and trigger a reschedule action to set a new
`logical_date` on any number of tasks at once. Dependencies re-evaluate against the new schedule.

## Catch-up (built in)
On each successful run the scheduler advances `next_run_date` by one cron interval from the *previous*
`next_run_date` (not wall-clock). If the scheduler was down or a backfill anchor is in the past, it
dispatches the next slot immediately after each success until it catches up — one logical_date at a time,
in order.

## Test before you use
Reschedule / skip-subtree / rerun-subtree can have broad effects. Test on 2–3 tasks first, verify, then
scale. Keep action code in git so any change is reversible.
""",

    "02_dependencies_and_partitions.md": """\
# Dependencies & partitions

## LeastActionCheckIfParentsAreDone (pre-action)
Before a task runs, this action: (1) looks up each declared parent by primary key
`name + account + project + partition`; (2) checks the parent's `state` is `success`; (3) checks the
parent's `last_run_date` is at/after the expected scheduled time. If any parent fails, the child waits.
This is why backfill respects ordering: each date's child runs only after that date's parent succeeds.

## Declaring a dependency
```json
{ "parents": [ { "task_name": "fact_sales_transform",
  "project_laui": "{{project_laui}}", "account_laui": "{{account_laui}}", "partition": "{{partition}}" } ] }
```
The `{{...}}` placeholders resolve at runtime, so the same definition works across environments/partitions.

## Cross-project dependencies
Because lookup is by primary key, a task in one project can depend on a task in a different project — no
shared DAG. The finance pipeline can wait on the platform team's ingestion task without sharing code.

## Partitions
A partition is part of the task primary key. Same name + same project + different partition = an
independent instance with its own state, run date, and dependency chain. Use it for sharding (one
partition per region), multi-tenant pipelines (one partition per client), or parallel report variants.
A child depending on `partition: NORTH_AMERICA` waits only for that partition.

## Custom dependency/control actions
`LeastActionCheckIfParentsAreDone` is one example — write your own: run-child-on-parent-complete,
rerun-subtree, skip-subtree, or conditional dependency (check the parent's *output* — row count, S3 file,
quality score — not just its state). All regular Python actions in git.
""",
}

prompt = (
    "Knowledge bundle teaching pipeline management at scale in LeastAction: backfilling thousands of runs "
    "because logical_date is a dimension of a task (set at import/schedule time, not baked into code). "
    "Covers backfill via LeastActionGitToTask (set logical_date at import) and bulk reschedule UI actions, "
    "catch-up, LeastActionCheckIfParentsAreDone dependency checking, cross-project dependencies, and "
    "partitions for sharding/multi-tenant/parallel variants. Skills-only (Pattern 3)."
)

description = (
    "Orchestration (KB): backfill thousands of runs with one action and manage dependencies at scale — "
    "because logical_date is a task dimension, not baked into the run. Teaches backfill methods, catch-up, "
    "LeastActionCheckIfParentsAreDone, cross-project deps, and partitions."
)

guide_docs = """\
# Backfill & Manage Pipelines at Scale

**Lifecycle stage:** Orchestration. **Flavor:** skills-only knowledge bundle — the AI reads the skills
and applies the patterns to your tasks; there are no tasks to deploy.

## The key idea
The date is not a connected component of the run. A task has a `logical_date` that is **assigned** — so
the same operator/SQL/Python runs for any date. Backfill = create one instance per date; reschedule =
change the date on selected tasks. No pipeline code changes.

## Backfill methods
- **At import** with `LeastActionGitToTask`: set `logical_date` in the import payload; loop over a date
  range to backfill it.
- **Bulk reschedule**: select tasks in the table view, trigger a reschedule action, confirm the new date.
- **Catch-up** is built in: after each success the scheduler dispatches the next missed slot immediately
  until current, one logical_date at a time, in order.

## Dependencies & partitions
`LeastActionCheckIfParentsAreDone` (pre-action) gates a child on its parents by primary key
(`name + account + project + partition`), so ordering holds per date and per partition. Dependencies can
cross projects. Partitions give independent parallel instances (sharding, multi-tenant, report variants).

## Prerequisites
- `LeastActionCheckIfParentsAreDone` (core), and `LeastActionGitToTask` (core) for import-time backfill.

## Test before you use
Bulk actions (reschedule/skip-subtree/rerun-subtree) have broad effects — test on a few tasks first;
keep action code in git so changes are reversible.

## Using
> "use the leastaction-pipelines-orchestration usecase to backfill finance_daily from 2024-01-01 to today"

The agent reads these skills and drives the backfill via the import/reschedule actions.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Orchestration",
    "tags": ["flavor:KB", "lifecycle:orchestration", "backfill", "dependencies", "partitions", "logical_date", "scale"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
