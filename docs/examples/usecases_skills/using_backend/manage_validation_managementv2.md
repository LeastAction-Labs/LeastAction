<operator/action/doc pending>

You are an AI data engineer, lets write a SQL validation report operator — a config-driven approach to running N SQL validation queries, collecting all results into a styled HTML report, saving that report to the database, publishing it as an asset in the LeastAction catalog, and optionally emailing it.

This is the validation counterpart to the AggReporting pattern in backend/bootstrap/ideas/done/AggReporting/AggReportingOperator/PostgresqlGenerateHtmlTableReport.py — same pipeline lifecycle (initialize, run, check_completion, finish), same catalog API integration, but instead of pivoting a single fact table, it runs a list of named validation queries defined in JSON or YAML config, collects every result set, and renders them all into one HTML report.

Context:
 - Reference operator: LeastAction/backend/bootstrap/ideas/done/AggReporting/AggReportingOperator/PostgresqlGenerateHtmlTableReport.py
   - Same operator lifecycle: initialize() → run() → check_completion() → finish()
   - Same catalog API integration: POST /api/v1/catalog/create with item_type=html_report
   - Same DB write pattern: create table if not exists, insert html_content + metadata
   - Key difference: this operator takes a list of queries (not one), runs them all, assembles all results into one report
 - Config format is JSON or YAML in the task payload — same as how query_config and metric_template work in the reporting operator
 - Catalog API for saving the asset: LeastAction/frontend/src/services/catalog.service.ts
 - Using Catalog API in AI context: LeastAction/frontend/src/services/ai.service.ts
 - Action setup docs: LeastAction/frontend/docs/advanced/action.md
 - output_parent_laui controls where the report asset is saved in the catalog (same as reporting operator)
 - optional: email the report after saving, same SMTP pattern used in ApproveAndSendReport

Validation query config structure (the core of the skill):
 - Top-level: report_title, output_table, output_parent_laui, connection info, optional email config
 - queries: a list of named checks, each with:
   - name: human-readable check name (shown as section heading in the report)
   - description: what this check validates
   - sql: the query to run (can include {partition}, {logical_date} templating)
   - severity: info | warning | critical — affects styling in the report
   - pass_condition: optional — expression to evaluate on result (e.g. row_count == 0 for a "find bad rows" check, or value >= threshold)
   - display: table | scalar | count — how to render the result in the report

Example config:
```yaml
report_title: "Daily Data Quality Validation"
output_table: "validation_reports"
output_parent_laui: "<laui of validation-reports folder>"
queries:
  - name: "Null check — order_id"
    description: "Finds rows where order_id is null in the orders table"
    sql: "SELECT COUNT(*) AS null_count FROM orders WHERE order_id IS NULL AND date = '{logical_date}'"
    severity: critical
    pass_condition: "null_count == 0"
    display: scalar

  - name: "Row count — orders vs order_items"
    description: "Validates that every order has at least one line item"
    sql: |
      SELECT o.order_id
      FROM orders o
      LEFT JOIN order_items oi ON o.order_id = oi.order_id
      WHERE oi.order_id IS NULL AND o.date = '{logical_date}'
    severity: warning
    pass_condition: "row_count == 0"
    display: table

  - name: "Revenue reconciliation"
    description: "Compares sum of line items against order total"
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

  - name: "Partition completeness"
    description: "Check expected partition exists"
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales WHERE partition = '{partition}' AND date = '{logical_date}'"
    severity: info
    pass_condition: "row_count > 0"
    display: scalar
```

Report HTML structure (what the operator generates):
 - Header: report title, generation time, pass/fail summary badge (X checks passed, Y failed)
 - Per-query section:
   - Section heading: check name + severity badge (color coded: green/yellow/red)
   - Description line
   - Pass/Fail badge based on pass_condition evaluation
   - Result rendered as table (for display: table) or single value (for display: scalar/count)
   - If pass_condition fails and display is table: show the actual rows (the bad data) so the engineer can act immediately
 - Footer: link back to catalog, generation timestamp

Styling follows the same inline-style pattern as PostgresqlGenerateHtmlTableReport.py:
 - severity critical → red header + red fail badge
 - severity warning → orange header + orange fail badge
 - severity info → blue header — shown for context, does not fail the report
 - pass → green badge regardless of severity
 - report_style config block for fonts, colors, border — same keys as the reporting operator

Output options (choose one or both):
 - code: location LeastAction/backend/bootstrap/ideas/done/[folder name], files: name.py, name.connection, name.action_variables, copy this skill to the folder, add skill name as comment header
 - doc: location LeastAction/frontend/docs/examples/, add a folder with appropriate name, format md, blog-style title, target audience AI data engineer building for leadership

Additional context:
 - SQL templating: replace {logical_date}, {partition}, {account}, {project} from least_action_task_object before executing each query — same as how date_filter works in the reporting operator
 - pass_condition evaluation: evaluate as a Python expression against the result — if display is scalar, map the single column name to its value; if display is table, pass row_count as the count of returned rows
 - All queries always run — do not short-circuit on first failure. The report shows every check result so the engineer sees the full picture in one place
 - DB write: same CREATE TABLE IF NOT EXISTS + INSERT pattern as PostgresqlGenerateHtmlTableReport.py, but add a checks_passed, checks_failed, checks_total column for quick querying
 - Catalog asset: same /api/v1/catalog/create call, item_type html_report, html is the full rendered HTML
 - Optional email: if email config is present in payload (recipients, subject, smtp connection), send the HTML report after saving to catalog — same SMTP pattern as ApproveAndSendReport
 - Note: test on a single partition/date first before attaching to production workflows. Keep operator code in git so behavior is traceable and reversible.
 - Note: compare to building this in dbt tests or Great Expectations — both require separate tooling, separate orchestration, and separate result storage. Here the config, execution, result storage, asset publishing, and optional email all happen inside one LeastAction task with no extra infrastructure.

Examples:
 - LeastAction/backend/bootstrap/ideas/done/AggReporting/AggReportingOperator/PostgresqlGenerateHtmlTableReport.py — operator lifecycle and catalog API pattern to follow
 - LeastAction/frontend/docs/examples/reporting_asset_management/report-approval-workflow.md — how reports flow to catalog and email
 - LeastAction/frontend/docs/examples/notify_and_manage/running-actions-pipeline-control.md — use case 6 (data quality enforce) for how validation gates fit into postActions
 - LeastAction/backend/bootstrap/ideas/usecases_skills_doc/manage_with_running_actions.md — running action pattern reference
