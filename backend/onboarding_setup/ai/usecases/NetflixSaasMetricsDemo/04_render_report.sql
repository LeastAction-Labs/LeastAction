/*
{
  "name": "04_render_report.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "postgresql_s",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {"report_title": "Netflix SaaS Metrics - {{logical_date}}"},
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
              "task_name": "03_compute_metrics.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
SELECT
    as_of_date,
    wau,
    mau,
    l7_sessions,
    l30_sessions,
    wau_by_plan,
    wau_by_country,
    computed_at
FROM metrics_daily
WHERE as_of_date BETWEEN DATE '{{logical_date}}' - INTERVAL '29 days'
                    AND DATE '{{logical_date}}'
ORDER BY as_of_date DESC;
