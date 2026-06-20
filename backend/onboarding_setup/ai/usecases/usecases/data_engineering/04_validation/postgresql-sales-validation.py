# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 04_validation  |  Flavor: S+P (skills + one runnable payload)
# Teaches config-driven data-quality validation: one operator (PostgresqlValidatorSQL) runs N named
# SQL checks from a YAML config, renders a pass/fail HTML report (with the actual failing rows),
# writes it to a DB table, and publishes it as a catalog asset. Validation as evidence, not a boolean.
payloads = {
    "00_validate.yaml": """\
/*
{
  "name": "00_validate.yaml",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlValidatorSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
# Validation config (YAML). The PostgresqlValidatorSQL operator runs every query, evaluates each
# pass_condition, renders one HTML report, writes it to `output_table`, and publishes an
# html_report asset under `output_parent_laui`.
#
# REPLACE `output_parent_laui` below with the laui of the catalog folder where the report should
# be published (e.g. your "validation-reports" asset folder). Inside `sql`, use single-brace
# {logical_date} / {partition} — the operator templates those from the task's runtime context.
report_title: 'Daily Pipeline Validation'
output_table: 'validation_reports'
output_parent_laui: 'REPLACE_WITH_VALIDATION_REPORTS_FOLDER_LAUI'

queries:
  - name: 'Partition row count'
    description: 'Confirms the expected partition exists and is non-empty'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily WHERE date = '{logical_date}'"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Null check — sale_amount'
    description: 'Finds rows where sale_amount is null for this date'
    sql: "SELECT COUNT(*) AS null_count FROM fact_sales_daily WHERE sale_amount IS NULL AND date = '{logical_date}'"
    severity: critical
    pass_condition: 'null_count == 0'
    display: scalar

  - name: 'Negative amount check'
    description: 'Surfaces the actual rows with negative sale amounts (data quality issue)'
    sql: |
      SELECT order_id, sale_amount, date
      FROM fact_sales_daily
      WHERE sale_amount < 0 AND date = '{logical_date}'
    severity: warning
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Column audit'
    description: 'Verifies expected columns exist on the fact table'
    sql: "SELECT column_name FROM information_schema.columns WHERE table_name = 'fact_sales_daily' ORDER BY column_name"
    severity: info
    pass_condition: 'row_count > 0'
    display: count
""",
}

skills = {
    "00_validate.md": """\
# Step 0 — Config-driven SQL validation report

## Lifecycle & prerequisites
**Stage:** Validation (data-quality undercurrent). This usecase teaches how to express a suite of
data-quality checks as config and produce one shareable HTML report per run.

**Prerequisites in core before deploying:**
- Operator `PostgresqlValidatorSQL` (core)
- A PostgreSQL `connection` pointing at the database to validate (this usecase defaults to `postgresql`)
- A catalog folder to publish reports into — paste its laui into `output_parent_laui`

**Verify success:** after a run, open the published `html_report` asset, or
`SELECT report_date, checks_passed, checks_failed FROM validation_reports ORDER BY report_date DESC`
via `inspect_data`.

## How the operator works
The payload is a YAML (or JSON) config: a list of named SQL checks. The operator runs **every**
query (so you see the full picture, not just the first failure), evaluates each `pass_condition`
against the result, renders one HTML report, writes it to `output_table`, and publishes an
`html_report` catalog asset under `output_parent_laui`.

## Config reference
Top level: `report_title`, `output_table` (auto-created), `output_parent_laui`, `queries`, optional `email`.

Per-query fields:
| Field | Meaning |
|---|---|
| `name` | Section heading in the report |
| `description` | What this check validates |
| `sql` | The query. Use single-brace `{logical_date}`, `{partition}`, `{account}`, `{project}` — the operator templates these from the task's runtime context (works for any backfill/partition/date) |
| `severity` | `critical` (red) / `warning` (orange) / `info` (blue) — affects the badge; failing `info` does NOT fail the report |
| `pass_condition` | Python expression. For `display: scalar` the result column name is the variable (e.g. `null_count == 0`); for `display: table` use `row_count` |
| `display` | `scalar` (single value) / `table` (renders all returned rows — the failing rows) / `count` (row count only) |

## Why a report, not a boolean
A failing dbt/GE test tells you a check failed. This renders **the rows that failed** — the actual
`order_id`s that broke reconciliation — inline in the catalog. Validation as evidence.

## Adapting this step
- Replace the `queries` with your own checks; a check is just SQL — join across schemas, compare to a
  30-day rolling average, look up a threshold in a config table, etc.
- Point `connection_name` at the database you want to validate.
- Add an optional `email:` block (`recipients`, `subject`, `smtp_connection`, `send_on: always|failure_only`)
  to deliver the report; `failure_only` keeps inboxes quiet on healthy days.
- **Connect to pipeline control:** add a postAction that reads `checks_failed` for this `logical_date`
  and, on critical failures, runs `LeastActionSkipSubtree` + `LeastActionSlackNotify` so bad data does
  not flow downstream. The validator produces the evidence; the postAction acts on it.
""",
}

prompt = (
    "Config-driven SQL data-quality validation: a single task using the PostgresqlValidatorSQL operator "
    "that reads a YAML config of named SQL checks (each with severity, pass_condition, and display mode), "
    "runs all of them against a PostgreSQL connection, renders a pass/fail HTML report including the actual "
    "failing rows, writes it to a validation_reports table, and publishes it as an html_report catalog asset. "
    "SQL uses single-brace {logical_date}/{partition} templating resolved by the operator at runtime."
)

description = (
    "Validation: one operator runs a YAML suite of SQL data-quality checks, renders a pass/fail HTML "
    "report (with the failing rows shown), saves it to a table, and publishes it as a catalog asset — "
    "optionally emailing it. Validation as evidence, inside one LeastAction task with no extra infrastructure."
)

guide_docs = """\
# SQL Validation Reports

**Lifecycle stage:** Validation (data-quality). One operator, one config, one HTML report — run your
whole suite of checks every run and see exactly what passed, what failed, and the rows that failed.

## What it does
`PostgresqlValidatorSQL` reads a list of named SQL checks from the task payload (YAML/JSON), runs them
all against the configured connection, evaluates each `pass_condition`, and renders a single HTML report:

```
For each query: template {logical_date}/{partition} -> execute -> evaluate pass_condition
Render HTML (summary badge + per-check section + failing rows) ->
  write to output_table  +  publish html_report asset (output_parent_laui)  +  optional email
```

## Step
| Step | File | Operator | What it does |
|---|---|---|---|
| 0 | `00_validate.yaml` | `PostgresqlValidatorSQL` | Runs the YAML check suite and publishes the report |

## Prerequisites
- Operator `PostgresqlValidatorSQL` in core
- A PostgreSQL `connection` (default `postgresql`) for the database under test
- A catalog folder for the reports — paste its laui into `output_parent_laui` in the payload

## Required edit (deploy time)
Replace `output_parent_laui: 'REPLACE_WITH_VALIDATION_REPORTS_FOLDER_LAUI'` with the laui of your
validation-reports folder. Point `connection_name` at the database you want to validate, and replace
the example `queries` with your own checks.

## Template variables
| Variable | Where | Resolved by |
|---|---|---|
| `{{partition}}` | payload header | LeastAction runtime |
| `{{account_laui}}` / `{{project_laui}}` | (in pre_actions, if you add dependencies) | LeastAction runtime |
| `{logical_date}` / `{partition}` (single brace) | inside check `sql` | the PostgresqlValidatorSQL operator |

## Where the report goes
- **DB:** `output_table` (auto-created) with `report_date, partition, checks_total, checks_passed, checks_failed, html_content`.
- **Catalog:** an `html_report` asset under `output_parent_laui`, renders inline.
- **Email (optional):** add an `email:` block with `send_on: always|failure_only`.

## Test before you use
Validation reads data (it doesn't write), so it's lower-risk than control actions — but a misconfigured
`pass_condition` can give false confidence, and a check without a date filter can be slow. Test on one
date/partition first; keep the config in git.

## Deploying
> "deploy usecase postgresql-sales-validation"

The Usecase Deploy Skill verifies `PostgresqlValidatorSQL` exists, asks for the connection and the
`output_parent_laui`, and creates the task.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Validation",
    "tags": ["flavor:S+P", "lifecycle:validation", "data-quality", "postgresql", "reporting", "html_report"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
