# Core Concepts

LeastAction has one organizing idea: **everything is an item in a catalog**, and a **task** is assembled from a few of those items.

## The formula

```
Connection + Operator + Payload + Config = Task
```

Config and Actions are optional but powerful additions.

| Item | Role | One-liner |
|---|---|---|
| **Operator** | The **HOW** | Python that defines how a task runs — run SQL, invoke Lambda, process a file, call an API. Has a 4-method contract (`initialize`, `run`, `check_completion`, `finish`). |
| **Connection** | The **WHERE** | Credentials + resource config + concurrency controls for an external system (AWS, PostgreSQL, GitHub, dbt-server, …). Takes whatever fields the operator needs. |
| **Payload** | The **WHAT** | The specific input for one task — which SQL, which S3 path, which model. Any format the operator expects (SQL, JSON, Python, string). |
| **Config** | The **RULES** | Defaults, schedule, retries, SLA, dependencies, parameters — shared across tasks via an N-level hierarchy with locked/overridable values. |
| **Action** | The **HOOKS** | Reusable Python that runs at a lifecycle point (pre / running / post / UI). Dependency checks, SLA alerts, Slack/email, Git sync, report generation. |
| **Task** | The **INSTANCE** | Combines operator + connection + payload (+ config + actions) to do work on a schedule or on demand. |

Read each in depth under [Concepts](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection): connection, operator, payload, config, action, workflow, task states, scheduling.

## The catalog

Every item — including tasks, reports, and registered tables — lives in a **folder hierarchy** (account → project → workflow/connection/operator/…). The catalog is:

- the **shared context** the AI reads and writes through,
- the **interface** engineers use to schedule, monitor, and reuse pipelines,
- and a lightweight **CMS** for published reports and assets.

See [Items & Catalog](/path?laui=getting-started-04-concepts-01-items-and-catalog&itemtype=doc.file&itemname=Items%20And%20Catalog) for the hierarchy and item types.

## Scheduling in one breath

A scheduled task carries a **`logical_date`** (the data period it computes, injected as `{{ds}}`) separate from its scheduler trigger time. Because the date is a *dimension* of the task — not baked into the run — backfilling thousands of dates is one action, and catch-up is automatic. See [Scheduling](/path?laui=getting-started-04-concepts-09-scheduling&itemtype=doc.file&itemname=Scheduling).

## Dependencies without a hard-coded DAG

Tasks depend on each other by **name + project + partition** via the `LeastActionCheckIfParentsAreDone` pre-action — resolved at runtime, even across projects. No DAG edges to wire. See [Task Dependencies](/path?laui=getting-started-05-building-pipelines-03-task-dependencies&itemtype=doc.file&itemname=Task%20Dependencies).

## Next

- [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart) — install and run a task now.
- [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection) — build your first pipeline step by step.
