# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payloads = {
    "00_create_table.sql": """\
/*
{
  "name": "00_create_table.sql",
  "frequency": "*/3 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": ["PostgresqlDemoWorkflow"],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    logical_date DATE
);
""",

    "01_insert_rows.sql": """\
/*
{
  "name": "01_insert_rows.sql",
  "frequency": "*/3 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": ["PostgresqlDemoWorkflow"],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "00_create_table.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
INSERT INTO people (name, age, logical_date)
VALUES
    ('Alice',   28, '{{logical_date}}'),
    ('Bob',     34, '{{logical_date}}'),
    ('Charlie', 22, '{{logical_date}}');
""",

    "02_update_rows.sql": """\
/*
{
  "name": "02_update_rows.sql",
  "frequency": "*/3 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": ["PostgresqlDemoWorkflow"],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "01_insert_rows.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
UPDATE people
SET
    age = CASE name
        WHEN 'Alice'   THEN 29
        WHEN 'Bob'     THEN 35
        WHEN 'Charlie' THEN 23
    END,
    logical_date = '{{logical_date}}'
WHERE name IN ('Alice', 'Bob', 'Charlie');
""",
}

skills = {
    "00_create_table.md": """\
# Step 0 — Create Table

Creates the `people` table if it does not already exist. Safe to re-run (idempotent via `IF NOT EXISTS`).

## Schema
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PRIMARY KEY | Auto-increment surrogate key |
| `name` | VARCHAR(100) | Person's name |
| `age` | INT | Person's age |
| `logical_date` | DATE | Partition date — set by the workflow at runtime |

## Adapting this step
- To add columns: extend the `CREATE TABLE` statement and update the INSERT/UPDATE steps to match.
- To use a different table name: rename `people` here and in steps 1 and 2.
- This step has no dependencies — it always runs first.
""",

    "01_insert_rows.md": """\
# Step 1 — Insert Rows

Inserts three sample rows (Alice, Bob, Charlie) into the `people` table, stamped with `{{logical_date}}`.

## Template variables
| Variable | Value source |
|---|---|
| `{{logical_date}}` | Resolved at runtime by the LeastAction scheduler — represents the task's execution date |

## Dependency
Waits for `00_create_table.sql` to succeed before running (`LeastActionCheckIfParentsAreDone`).

## Adapting this step
- To insert different rows: replace the VALUES list. Keep `{{logical_date}}` as the date column value.
- To insert from a SELECT: replace the VALUES clause with `INSERT INTO people (...) SELECT ...`.
- `over_ride: true` means this task re-runs on the same partition if triggered again — remove it to make inserts partition-safe (run-once per date).
""",

    "02_update_rows.md": """\
# Step 2 — Update Rows

Updates the `age` and `logical_date` for the three demo rows using a CASE expression.

## What it changes
| Name | Old age | New age |
|---|---|---|
| Alice | 28 | 29 |
| Bob | 34 | 35 |
| Charlie | 22 | 23 |

## Dependency
Waits for `01_insert_rows.sql` to succeed before running (`LeastActionCheckIfParentsAreDone`).

## Adapting this step
- To update different fields: add more `SET` assignments inside the CASE or as additional columns.
- To update based on a query result: replace the literal CASE values with a subquery or JOIN pattern.
- To make this a soft-delete or archive step: swap the UPDATE for an `INSERT INTO archive_table SELECT ... FROM people`.
""",
}

prompt = (
    "Three-step PostgreSQL demo pipeline: create the 'people' table, insert three sample rows "
    "with a logical_date partition, then update their ages. Each step depends on the previous "
    "via LeastActionCheckIfParentsAreDone. Designed to run every 3 minutes on the PostgresqlExecuteSQL "
    "operator with the bundled 'postgresql' connection (points at the internal postgres-demo "
    "demo database) and the 'PostgresqlDemoWorkflow' config (auto-reschedule on error/fail)."
)

description = (
    "Minimal end-to-end PostgreSQL demo: create table → insert rows → update rows. "
    "Three sequential tasks linked by dependency checks. Self-contained — bundles its own "
    "connection and config, ready to run out of the box."
)

guide_docs = """\
# PostgresqlDemo Usecase

## What it does
Runs a simple 3-step pipeline against a PostgreSQL database to demonstrate LeastAction task chaining.

| Step | File | What it does |
|------|------|--------------|
| 0 | `00_create_table.sql` | Creates `people(id, name, age, logical_date)` if it doesn't exist |
| 1 | `01_insert_rows.sql` | Inserts Alice, Bob, Charlie with the partition logical_date |
| 2 | `02_update_rows.sql` | Updates ages (Alice→29, Bob→35, Charlie→23) and refreshes logical_date |

## Bundled items
This usecase is self-contained — deploying it sets up everything needed to run:

| Item | Name | Purpose |
|---|---|---|
| Connection | `Postgresql` (connection_name `postgresql`) | Points to the internal `postgres-demo` demo database (docker service `postgres-demo`, db `postgres_demo_db`, user/pass `postgres`/`postgres`). Edit the connection to point at your own PostgreSQL instance if desired. |
| Config | `PostgresqlDemoWorkflow` | Attached to all 3 tasks via `config_name`. Adds `LeastActionReschedule` on error/fail states. |
| Operator | `PostgresqlExecuteSQL` | Executes each step's SQL payload (core operator). |
| Action | `LeastActionCheckIfParentsAreDone` | Used by steps 1 and 2 to wait for the previous step (core action). |

## Prerequisites
- Operator `PostgresqlExecuteSQL` must exist in core
- Action `LeastActionCheckIfParentsAreDone` must exist in core
- Connection `Postgresql` (connection_name `postgresql`) and config `PostgresqlDemoWorkflow`
  are deployed as part of this usecase — no manual setup required when running the bundled
  docker-compose stack with the `postgres-demo` service.

## Template variables
| Variable | Description |
|---|---|
| `{{partition}}` | Task partition key (e.g. `ALL` or a date string) |
| `{{logical_date}}` | The date value inserted/updated in the `people` table |
| `{{account_laui}}` | LAUI of the account folder (resolved at runtime) |
| `{{project_laui}}` | LAUI of the project folder (resolved at runtime) |

## Deploying
Use the **Usecase Deploy Skill** in the LeastAction AI assistant:
> "deploy usecase PostgresqlDemo"

The assistant will create the `Postgresql` connection and `PostgresqlDemoWorkflow` config (if
they don't already exist), then create all three tasks in order, each referencing them.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "demo", "usecase", "pipeline", "create", "insert", "update"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
