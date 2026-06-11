# One Click to Backfill Thousands of Jobs: Managing Pipelines at Scale

You launch a new pipeline. It needs to run daily going back two years. In most orchestration tools, that is a planning problem: how do you backfill 730 runs without breaking dependencies, without overwhelming your database, without hard-coding a date range into your code?

In LeastAction, it is a single action — because the date is not baked into the task. It is a dimension of it.

---

## Why Backfill Is Hard Elsewhere

In Airflow, Prefect, and Dagster, the execution date is tightly coupled to the DAG or flow run. Backfilling means replaying historical execution dates, often one at a time, with careful management of concurrency and dependency ordering. If you add a new task mid-backfill, you re-plan. If a task was skipped for the wrong date, you track it manually.

The root cause: **the date is connected to the run**, not a parameter the task can receive independently.

LeastAction separates them. A task has a `logical_date` — but that date is set at import or schedule time, not embedded in the code. The same operator, the same SQL, the same Python — any date you assign it is the date it uses. This makes backfill trivial.

---

## Backfill with One Click

### Option 1: Set the date at import time with GitToTask

When you import tasks from Git using `LeastActionGitToTask`, you set `logical_date` as part of the import payload. To backfill two years of daily runs, you run the import action 730 times — or loop through dates in a single import action invocation — each time creating task instances for that date.

```json
{
  "repo_url": "https://github.com/your-org/your-pipeline",
  "branch": "main",
  "sub_path": "daily_finance_pipeline",
  "workflow_name": "finance_daily",
  "logical_date": "2024-01-15"
}
```

Each date creates its own set of task instances. Dependencies are wired from the task metadata — they hold for every date automatically. The data pipeline code does not change.

### Option 2: Reschedule in bulk with a UI action

If tasks already exist in a workflow and you need to change their scheduled date — backfilling a new partition, replaying a date range after a data issue — a reschedule action can update `logical_date` on any number of selected tasks in one trigger.

Select the tasks in the table view, trigger the reschedule action, confirm the new date. Every selected task gets the new date. Dependencies re-evaluate against the new schedule. No pipeline code changes.

---

## How Dependencies Work

### LeastActionCheckIfParentsAreDone

The built-in dependency action — `LeastActionCheckIfParentsAreDone` — ships with LeastAction and runs as a preAction on any task that has upstream dependencies. Before a task executes, the action:

1. Looks up each declared parent task by its primary key (`name + account + project + partition`)
2. Checks that the parent's `state` is `success`
3. Validates that the parent's `last_run_date` is at or after the expected scheduled time (derived from the parent's cron frequency and the child's run time)

If any parent fails either check, the child task does not run. It waits. When you retry, the check runs again.

This means backfill respects ordering automatically. If you replay 30 days, tasks at each date only run after their parents at that same date have succeeded — not after the parents at today's date.

### Declaring a dependency

Dependencies are declared in the task metadata as a `parents` list:

```json
{
  "parents": [
    {
      "task_name": "fact_sales_transform",
      "project_laui": "{{project_laui}}",
      "account_laui": "{{account_laui}}",
      "partition": "{{partition}}"
    }
  ]
}
```

The `{{project_laui}}`, `{{account_laui}}`, and `{{partition}}` placeholders resolve at runtime — so the same task definition works across environments and partitions without edits.

### Cross-project dependencies

Because dependency lookup is by primary key (`name + account + project + partition`), a task in one project can depend on a task in a completely different project — no shared DAG, no shared workflow, no complex wiring. As long as the parent task exists in the catalog and has the right name and project, the dependency resolves.

This is how you build cross-team pipelines: the finance pipeline can wait for the data platform team's raw ingestion task to complete, without the two teams sharing a codebase or an orchestrator instance.

---

## Partitions: Parallel Runs and Sharding

A partition is a dimension on the task primary key. The same task name + same project + different partition = a completely independent task instance that runs, succeeds, and is depended upon independently.

### What this enables

**Sharding**: Run the same transformation for 10 regions in parallel by assigning each a different partition value. Each regional instance has its own state, its own run date, its own dependency chain.

**Multi-tenant pipelines**: The same pipeline code serves multiple clients. Each client is a partition. One client's failure does not affect another's.

**Parallel report variants**: Generate a `standard` and a `premium` version of a report in parallel from the same operator — two partitions, same workflow, independent task states.

A task that depends on `fact_sales_transform` with `partition: NORTH_AMERICA` only waits for the North America partition — not Europe, not Asia Pacific. Dependencies respect partition boundaries.

---

## Viewing Pipeline State at Scale

### Table view

The table view shows every task in a workflow as a row — name, partition, logical date, current state, and the status of any actions that ran (preActions, postActions, UI actions). When you have 100 tasks across 10 partitions and 10 dates, the table gives you the full picture at a glance. Filter by state to see everything that failed or is waiting.

From the table, you can select tasks and trigger actions on them directly — reschedule, skip, rerun, or any custom action you have configured.

### Graph view

The graph view renders the dependency tree. Each task is a node; edges connect children to their parents. The graph respects `LeastActionCheckIfParentsAreDone` — tasks that are waiting on a parent show the dependency relationship visually. This is where you trace why something is blocked: follow the red nodes upstream to find the root failure.

---

## Custom Dependency and Control Actions

`LeastActionCheckIfParentsAreDone` is one example of what a dependency action can do. You can write your own. Common patterns:

**Run a child task when parent completes**
A postAction on the parent that directly triggers the child via the task API — no polling, no scheduler lag.

**Rerun all child tasks in a subtree**
Select a parent in the table, trigger a "rerun subtree" action that recursively lists children (filtered by `item_type: task`) and re-enqueues each one. Use the `item_type` filter when listing children — a task folder can contain many things and scanning all of them is expensive.

**Skip all downstream tasks**
When a partition's data is known bad, select the root task and trigger a "skip subtree" action. Every dependent task is marked `skipped` without running. The rest of the workflow continues unaffected.

**Conditional dependency**
A dependency action that checks not just state, but the output of the parent — row count, file existence in S3, a quality score in a metrics table. If the parent succeeded but produced bad data, the child does not run.

These are all regular actions — Python files, in Git, deployed through the standard action config. You can build any dependency logic your pipeline requires.

---

## Comparison to Other Tools

| | LeastAction | Airflow | Prefect | Dagster |
|---|---|---|---|---|
| Backfill a new pipeline | Set date at import, run | Replay DAG runs by date range | Re-run flow runs with historical dates | Asset backfill wizard per partition |
| Date coupling | Date is a parameter, not baked in | Execution date is part of the DAG run | Flow run has a scheduled time | Partition key includes time window |
| Cross-project dependency | By name + project + partition | Not native — requires cross-DAG sensors | Not native — requires events/triggers | Not native — requires source asset declaration |
| Custom dependency logic | Write any Python action | Write a sensor operator | Write a custom state handler | Write a sensor or hook |
| Parallel partitions | First-class partition key | Separate DAG runs or dynamic task mapping | Subflows or dynamic mapping | Asset partitions |
| Bulk reschedule | Select tasks in table, trigger action | Manually update DAG run dates | Not straightforward | Not straightforward |

The key difference: in LeastAction the date is not a connected component of the task. It is assigned. That one decision makes backfill, rescheduling, and parallel partitioning far simpler to manage without changes to pipeline code.

---

## Test Before You Use

Actions that operate on many tasks at once — reschedule, skip subtree, rerun subtree — can have broad effects. **Test on a small set first.** Select two or three tasks, verify the result, then scale.

Keep all action code in Git. If an action produces an unexpected result, you can restore the previous state, redeploy the corrected action, and rerun. The catalog API gives you full control — what the action writes, it can also undo.

This is not a warning to avoid these patterns. It is a reminder that powerful tools reward careful use.
