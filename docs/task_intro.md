# Getting Started with LeastAction

## Welcome to LeastAction!

LeastAction is an AI-powered orchestration platform that makes building, managing, and scaling data pipelines simple and intuitive. Whether you're a seasoned data engineer or just getting started, LeastAction provides the tools you need to orchestrate complex workflows without writing extensive code.

This guide will walk you through the fundamentals of LeastAction and help you create your first working task.

---

## What is LeastAction?

LeastAction is a workflow orchestration platform that combines the power of traditional orchestrators with AI-driven development and a visual, folder-based interface. Think of it as a system where:

- **Everything is an item** - Tasks, operators, connections, configs, and payloads are all first-class items stored in a folder structure
- **AI helps you build** - Generate operators and actions in seconds using natural language
- **Configuration is king** - Control execution behavior, dependencies, and defaults through configs
- **Actions extend everything** - Add custom behavior at any point in the task lifecycle

### Core Concepts

**Operator** — The "HOW". Code that defines how tasks execute (e.g., run SQL queries, call an API, process files on EC2)

**Connection** — The "WHERE". Credentials and resource configuration for external systems (AWS, PostgreSQL, GitHub, etc.)

**Payload** — The "WHAT". Specific parameters for a task instance (e.g., which SQL to run, what S3 path to use)

**Config** — The "RULES". Defaults, retry logic, parameters, and lifecycle behavior shared across tasks

**Actions** — The "HOOKS". Reusable Python functions that run at specific lifecycle points (pre, running, post)

**Task** — The "INSTANCE". Combines operator + connection + payload + config to execute work on a schedule or on demand

---

## Quick Start: The Formula

Every task in LeastAction follows one simple formula:

```
Connection + Operator + Payload = Task
```

Config and Actions are optional but powerful additions.

---

## Creating Your First Task

The example below walks through setting up a PostgreSQL task — one of the most common real-world setups in LeastAction.

### Step 1: Create a Connection

A **connection** holds credentials and resource settings for an external system.

1. Navigate to your project folder in the UI
2. Click **Create Connection**
3. Fill in the form:
  - **Name**: A descriptive name (e.g., `postgres-prod`)
  - **Description**: Optional
  - **Content**: JSON with credentials
  - **Max Parallelism**: Max concurrent tasks using this connection (e.g., `10`)

**Example — PostgreSQL connection content:**

```json
{
  "host": "db.example.com",
  "port": 5432,
  "database": "analytics",
  "user": "pipeline_user",
  "password": "${AWS_SECRET_MANAGER:db-password}"
}
```

> **Security**: Never store plain-text passwords. Reference secrets using `${AWS_SECRET_MANAGER:secret-name}` or environment variables.

> **AWS connections** use fields like `region`, `ec2_instance_id`, `aws_access_key_id`. See the [Connections Guide](/path?laui=getting-started-advanced-task_managment-connection&itemtype=doc.file&itemname=Connection) for all connection types.

---

### Step 2: Choose or Create an Operator

An **operator** contains the execution logic. LeastAction ships with operators for PostgreSQL, AWS EC2, Airflow, and more. You can also **generate new operators with AI** in seconds.

**Option A — Use an existing operator**
Browse the operators folder and select one (e.g., `PostgresqlExecuteSQL`).

**Option B — Generate with AI**

1. Navigate to **AI > Operator** in the UI
2. Describe what you need in plain English
3. AI generates the operator code, sample connection, and sample payload
4. Review, test, and save

When saving a new operator, fill in:

- **Name**: e.g., `PostgresqlExecuteSQL`
- **Codeblock**: Python with the 4 required methods (`initialize`, `run`, `checkCompletion`, `finish`)
- **Bashblock**: Shell commands for dependencies (e.g., `pip install psycopg2-binary`)
- **Connection Sample**: Example connection JSON
- **Payload Sample**: Example payload JSON

See [AI Operator & Action Guide](/path?laui=getting-started-AI_tech_intro&itemtype=doc.file&itemname=AI%20Tech%20Intro) for details on AI generation.

---

### Step 3: Create a Payload

The **payload** specifies the task-specific input — what the operator should do this particular run.

**Example — PostgreSQL payload:**

```json
INSERT INTO reports.daily_summary SELECT * FROM staging.events WHERE date = '{{ds}}'
```

`**{{ds}}**` is a built-in variable replaced at runtime with the task's logical date (e.g., `2026-03-30`). Parameters defined in a linked config are also available as `{{parameter_name}}`.

---

### Step 4: Create a Task

Combine everything into a runnable task:

1. Navigate to your workflow folder
2. Click **Create Task**
3. Fill in:
  - **Name**: `process_daily_events`
  - **Operator**: Select your operator (e.g., `PostgresqlExecuteSQL`)
  - **Connection**: Select your connection (e.g., `postgres-prod`)
  - **Frequency**: `ADHOC` for a one-time run, or a cron expression for scheduled (e.g., `0 2 * * `*)
  - **Payload**: Paste your payload JSON
  - **Config**: Optional — attach a config for retry logic, parameters, default actions
  - **Start / End Dates**: Required for scheduled tasks; leave empty for ADHOC
4. Click **Create Task**

---

## Running Tasks

### Adhoc

Set `frequency` to `ADHOC`. The task runs immediately when triggered — no schedule, no instances generated.

### Scheduled

Set `frequency` to a cron expression and provide `start_date` and `end_date`. LeastAction generates one task instance per scheduled interval.

**Example — daily task running at 2 AM:**

```
frequency:  0 2 * * *
start_date: 2026-03-01T00:00:00Z
end_date:   2026-03-31T23:59:59Z
```

This creates 31 task instances, one per day, each with a `logical_date` (the `{{ds}}` value) for that day.

---

## Scheduling Model: logical_date vs next_run_date

Every scheduled task has two independent date fields:

| Field | What it represents |
|---|---|
| `logical_date` | The **data period** the task is computing. Injected as `{{ds}}` or `{{logical_date}}` in payloads. Same concept as Airflow's `logical_date` (called `execution_date` before Airflow 2.2). Floored to the cron's granularity — daily → midnight, monthly → 1st of month at midnight, 5-min → exact cron minute mark. |
| `next_run_date` | The **scheduler trigger date**. The cron compares this against UTC wall clock time. When `next_run_date ≤ UTC now`, the scheduler dispatches the task (runs pre-actions, then the operator). |

Both fields start equal to `start_date` and advance together on each successful run. They are closely tied — for a daily cron at 11:01 AM, `logical_date` would be `2026-05-15 00:00:00` (midnight, the start of that day's data period) while `next_run_date` would be `2026-05-15 11:01:00` (the exact cron tick time).

### Catch-Up Behavior (default)

On each successful run, `next_run_date` advances exactly **one cron interval from the previous `next_run_date`** — not from the physical wall-clock time of the run. This means:

- If the scheduler was down for several days, `next_run_date` remains in the past
- The cron immediately dispatches the next run after each success
- This repeats, one cron slot at a time, until `next_run_date > UTC now`

**Example:** A daily task missed 5 days while the scheduler was unhealthy. When the scheduler recovers, it runs 5 consecutive times (one per cron slot) to catch up — processing each missed `logical_date` in order.

This is equivalent to Airflow's `catchup=True` behavior and is always on by default.

---

## Viewing Task Logs

1. Navigate to the **Logs** section in the UI
2. Browse by task name → date → execution
3. Logs show timestamps, function names, log level, and message
4. For actions that ran on the task, logs are listed separately under the task's execution

Logs are stored in Hive-partitioned format on local disk by default. Use actions (e.g., `LeastActionLogsToS3`) to ship them to cloud storage.

---

## Task Dependencies

LeastAction handles dependencies through **actions**, not hard-coded DAG edges. This makes them flexible and reusable.

The key built-in action is:

`**LeastActionCheckIfParentsAreDone`** — runs as a pre-action before task execution. It checks that all specified parent tasks completed successfully for the same logical date before allowing this task to run.

**Action variables structure:**

```json
{
  "parents": [
    {
      "task_name": "extract_data",
      "project_laui": "{{project_laui}}",
      "account_laui": "{{account_laui}}",
      "partition": "{{partition}}"
    }
  ]
}
```

**How to attach it to a task:**
When creating or editing a task, add `LeastActionCheckIfParentsAreDone` as a **pre-action** and fill in the `parents` variables with the upstream task name and context.

**For pipelines with many tasks**, set `LeastActionCheckIfParentsAreDone` as a default pre-action in your workflow config so every task inherits it automatically. See the [Config Guide](/path?laui=getting-started-advanced-task_managment-config&itemtype=doc.file&itemname=Config).

---

## Visualizing Dependencies

Every task has a **Parent-Child Data** tab in the UI:

- **List view**: Shows parent and child tasks with their current state
- **Graph view**: Toggle to an interactive dependency graph
  - Click any node to focus on that task
  - Use expand buttons to add more levels of parents/children

**Example graph:**

```
[extract_sales]
      ↓
[transform_sales]
      ↓
[load_sales] → [validate_sales]
```

---

## Next Steps

1. **Explore the bootstrap project** — Pre-built operators, connections, payloads, and actions for AWS, PostgreSQL, and more
2. **Generate an operator with AI** — [AI Guide](/path?laui=getting-started-AI_tech_intro&itemtype=doc.file&itemname=AI%20Tech%20Intro)
3. **Set up workflow configs** — Defaults, parameters, retry logic: [Config Guide](/path?laui=getting-started-advanced-task_managment-config&itemtype=doc.file&itemname=Config)
4. **Build a dependency pipeline** — Link tasks with `LeastActionCheckIfParentsAreDone`
5. **Learn about connections** — [Connections Guide](/path?laui=getting-started-advanced-task_managment-connection&itemtype=doc.file&itemname=Connection)
6. **Learn about actions** — [Actions Guide](/path?laui=getting-started-advanced-task_managment-action_aka_hook&itemtype=doc.file&itemname=Action%20Aka%20Hook)

---

> **Getting help**: Use the AI Assistant directly in the UI, browse the bootstrap project for real-world examples, or check the marketplace for community-built operators and actions.

