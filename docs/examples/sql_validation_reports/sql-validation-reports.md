# SQL Validation Reports: Config-Driven Data Quality at Scale

Running SQL queries to check data quality is not a new idea. What is new is having a single operator(coming soon #todo) that takes a list of named checks in a YAML or JSON config, runs all of them, renders the results into a styled HTML report, saves that report to the database, publishes it as a catalog asset, and optionally emails it — all inside one LeastAction task with no extra infrastructure.

This is the validation counterpart to [PostgreSQL Sales Reporting](/path?laui=getting-started-examples-postgres_sales_reporting-postgres-sales-reporting&itemtype=doc.file&itemname=Postgres%20Sales%20Reporting). Same pipeline lifecycle. Same catalog publishing pattern. Instead of pivoting a fact table into a summary report, it runs your entire suite of validation checks and shows you exactly what passed, what failed, and the actual bad rows for any failing check.

---

## The Problem This Solves

Data quality checks tend to sprawl. Some live in dbt tests. Some in Great Expectations. Some are ad-hoc queries an engineer runs manually before a business review. The results live in different places, require different tools to inspect, and have no consistent view that leadership or a data lead can glance at to understand the health of a pipeline on any given date.

This operator gives you one place: a config file that defines your checks, one task that runs them all, and one HTML report that shows the full picture — automatically, every run.

---

## How It Works

The operator reads a validation config from the task payload. The config is a list of named SQL checks, each with a severity level, a pass condition, and a display mode. The operator runs every query, evaluates the pass condition against the result, and renders all results into a single HTML report.

```
Task starts
    │
    ▼
Operator reads config (JSON or YAML from task payload)
    │
    ▼
For each query in config:
    ├── Template {logical_date}, {partition}, {account}, {project} into SQL
    ├── Execute against the configured connection
    └── Evaluate pass_condition against result
    │
    ▼
Render HTML report:
    ├── Header: title + pass/fail summary (X of N checks passed)
    ├── Per-check section: name, severity badge, pass/fail badge, result table or scalar
    └── Footer: generation time, catalog link
    │
    ├── Write report to DB (checks_passed, checks_failed, html_content)
    ├── Publish html_report item to catalog (output_parent_laui)
    └── Optionally email to recipients list
```

All queries always run. The report shows every check result so the engineer sees the full picture in one place — not just the first failure.

---

## The Config

Validation checks are defined in JSON or YAML in the task payload. A minimal example:

```yaml
report_title: "Daily Order Pipeline Validation"
output_table: "validation_reports"
output_parent_laui: "<laui of your validation-reports folder in the catalog>"

queries:
  - name: "Null check — order_id"
    description: "Finds rows where order_id is null"
    sql: "SELECT COUNT(*) AS null_count FROM orders WHERE order_id IS NULL AND date = '{logical_date}'"
    severity: critical
    pass_condition: "null_count == 0"
    display: scalar

  - name: "Orphaned order items"
    description: "Order items with no matching order"
    sql: |
      SELECT oi.item_id, oi.order_id
      FROM order_items oi
      LEFT JOIN orders o ON oi.order_id = o.order_id
      WHERE o.order_id IS NULL AND oi.date = '{logical_date}'
    severity: warning
    pass_condition: "row_count == 0"
    display: table

  - name: "Revenue reconciliation"
    description: "Orders where line item sum does not match order total"
    sql: |
      SELECT order_id, order_total, item_sum,
             ABS(order_total - item_sum) AS delta
      FROM (
        SELECT o.order_id, o.total AS order_total,
               SUM(oi.price * oi.quantity) AS item_sum
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.date = '{logical_date}'
        GROUP BY o.order_id, o.total
      ) t
      WHERE ABS(order_total - item_sum) > 0.01
    severity: critical
    pass_condition: "row_count == 0"
    display: table

  - name: "Partition row count"
    description: "Confirms expected partition exists and is non-empty"
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales WHERE partition = '{partition}' AND date = '{logical_date}'"
    severity: info
    pass_condition: "row_count > 0"
    display: scalar
```

### Config reference

| Field | Description |
|-------|-------------|
| `report_title` | Shown in the report header and as the catalog item name |
| `output_table` | DB table to write results to (created automatically if it doesn't exist) |
| `output_parent_laui` | Catalog folder where the `html_report` item is published |
| `queries` | List of validation checks — runs in order, all always execute |

Per-query fields:

| Field | Description |
|-------|-------------|
| `name` | Section heading in the report |
| `description` | Shown under the heading — what this check validates |
| `sql` | The query to run. Use `{logical_date}`, `{partition}`, `{account}`, `{project}` for templating |
| `severity` | `critical` (red), `warning` (orange), `info` (blue) — affects badge color |
| `pass_condition` | Python expression evaluated against result. For `display: scalar` the column name is available as a variable. For `display: table` use `row_count` |
| `display` | `table` renders all returned rows, `scalar` renders a single value, `count` renders a row count only |

### SQL templating

Before execution, the operator replaces `{logical_date}`, `{partition}`, `{account}`, and `{project}` from the task's runtime context — the same date and partition the task itself is running for. Write your checks once. They work correctly for any backfill, any partition, any date.

### Pass condition evaluation

For `display: scalar`, the single column value from the result is available by column name. `null_count == 0` checks whether the scalar column named `null_count` is zero.

For `display: table`, `row_count` is the number of rows returned. A check that expects to find no bad rows uses `row_count == 0`. A check that expects at least some rows uses `row_count > 0`.

`info` severity checks are shown for context. A failing `info` check does not mark the report as failed overall — only `critical` and `warning` failures count toward the summary badge.

---

## The Report

The HTML report is self-contained and renders without any external dependencies.

**Header**: report title, run date, summary badge — "3 of 4 checks passed" in green if all critical checks passed, red if any critical check failed.

**Per-check section**: severity badge (color coded), pass/fail badge, description, result. For a passing `row_count == 0` check this is just a green badge and a "0 rows" note. For a failing table check, the actual rows are rendered as a table — the engineer sees exactly which `order_id` values failed reconciliation, not just that some did.

**Footer**: generation timestamp, link to the catalog item.

This is the key difference from a boolean test framework. A failing check in dbt tells you the check failed. This report shows you the data that failed.

---

## Where the Report Goes

### Database

The operator writes to `output_table` (created automatically if it doesn't exist):

| Column | Description |
|--------|-------------|
| `id` | Auto-increment |
| `report_date` | The task's `logical_date` |
| `partition` | The task's partition |
| `checks_total` | Total number of checks |
| `checks_passed` | Number that passed |
| `checks_failed` | Number that failed (critical + warning only) |
| `html_content` | Full HTML of the report |
| `created_at` | Timestamp |

Query validation history directly: `SELECT report_date, checks_passed, checks_failed FROM validation_reports ORDER BY report_date DESC`.

### Catalog

An `html_report` item is created under `output_parent_laui`. The HTML renders inline when you open the item in the catalog. The item name includes the report title and date.

Open the catalog folder, see all validation runs by date, click any one to read the full report inline. No separate tool, no separate login.

### Email (optional)

Add an `email` block to the config:

```yaml
email:
  recipients:
    - "data-team@company.com"
    - "pipeline-lead@company.com"
  subject: "Daily Order Validation — {logical_date}"
  smtp_connection: "<name of your SMTP connection in the catalog>"
  send_on: always  # or: failure_only
```

`send_on: failure_only` sends the report only when one or more critical or warning checks fail — useful for keeping inboxes quiet on healthy days and only alerting when something needs attention.

---

## Connecting to Pipeline Control

The validation report is most powerful when connected to downstream pipeline control. After the validation task runs, a postAction can check the result and act:

```
Validation task completes
    │
    ▼
postAction reads checks_failed from DB for this logical_date
    ├── 0 failures → return true, downstream pipeline runs
    └── critical failures found → LeastActionSkipSubtree + LeastActionSlackNotify
```

This connects directly to the pattern in [Beyond Notifications: Actions That Control Your Pipeline](/path?laui=getting-started-examples-notify_and_manage-running-actions-pipeline-control&itemtype=doc.file&itemname=Running%20Actions%20Pipeline%20Control) — specifically the data quality enforce use case. The validation operator generates the evidence. The postAction acts on it.

---

## Compared to dbt Tests and Great Expectations

| | dbt tests | Great Expectations | This operator |
|--|-----------|-------------------|---------------|
| Where checks live | `schema.yml` in dbt project | Expectation suites | YAML/JSON in task payload |
| Result storage | dbt artifacts / separate store | Validation store | DB table + catalog asset |
| Report format | CLI output or dbt docs | HTML or JSON | Inline HTML in catalog |
| Email on failure | Separate alerting setup | Separate alerting setup | Built into config |
| Pipeline integration | Separate CI step | Separate orchestration | Same task, same lifecycle |
| Backfill behavior | Separate run per date | Separate run per date | Same task, {logical_date} templated |

This is not a replacement for test frameworks if you're already heavily invested in them. It is the right choice when you want validation, reporting, asset publishing, and optional email to happen inside one LeastAction task without separate tooling or infrastructure.

---

## Test Before You Use

Validation checks read data — they don't write — so they are lower risk than control actions. But a misconfigured `pass_condition` will mark checks as passing when they shouldn't, which can give false confidence. And a check that runs a full table scan without a date filter will be slow and expensive.

**Test on a single date and partition first.** Confirm the SQL returns what you expect. Confirm the pass condition evaluates correctly. Confirm the report renders cleanly. Then attach to a production schedule.

Keep the config in git. The check SQL, the pass conditions, the email list — all of it should be version controlled. When a check is added or a threshold is changed, the change is traceable.

---

## This Is Just the Starting Point

The operator runs SQL queries and renders results. What that means is entirely up to your checks. A check can join across any table in any schema, call a stored procedure, compute a ratio, look up a threshold in a config table, or compare today's counts to a 30-day rolling average. The config is just SQL. The operator handles everything else.

For the report approval and email workflow that this integrates with, see [Report Approval and Email Workflow](/path?laui=getting-started-examples-reporting_asset_management-report-approval-workflow&itemtype=doc.file&itemname=Report%20Approval%20Workflow).

For connecting validation results to pipeline control actions, see [Beyond Notifications: Actions That Control Your Pipeline](/path?laui=getting-started-examples-notify_and_manage-running-actions-pipeline-control&itemtype=doc.file&itemname=Running%20Actions%20Pipeline%20Control).
