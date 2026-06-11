/*
{
  "name": "03_compute_metrics.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql_s",
  "partition": "{{partition}}",
  "config_name": [],
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
              "task_name": "01_ingest_customer_profiles.sql"
            },
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "02_ingest_fact_engagement.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
WITH window_facts AS (
    SELECT f.engagement_date, f.customer_id, f.sessions_count,
           c.plan_tier, c.country
    FROM fact_daily_engagement f
    LEFT JOIN dim_customer_profiles c ON f.customer_id = c.customer_id
    WHERE f.engagement_date BETWEEN DATE '{{logical_date}}' - INTERVAL '29 days'
                                AND DATE '{{logical_date}}'
)
INSERT INTO metrics_daily (as_of_date, wau, mau, l7_sessions, l30_sessions,
                           wau_by_plan, wau_by_country, computed_at)
SELECT
    DATE '{{logical_date}}',
    COUNT(DISTINCT CASE WHEN engagement_date >= DATE '{{logical_date}}' - INTERVAL '6 days'
                        THEN customer_id END),
    COUNT(DISTINCT customer_id),
    SUM(CASE WHEN engagement_date >= DATE '{{logical_date}}' - INTERVAL '6 days'
             THEN sessions_count END),
    SUM(sessions_count),
    (SELECT jsonb_object_agg(COALESCE(plan_tier, 'unknown'), n)
     FROM (SELECT plan_tier, COUNT(DISTINCT customer_id) n
           FROM window_facts
           WHERE engagement_date >= DATE '{{logical_date}}' - INTERVAL '6 days'
           GROUP BY plan_tier) p),
    (SELECT jsonb_object_agg(COALESCE(country, 'unknown'), n)
     FROM (SELECT country, COUNT(DISTINCT customer_id) n
           FROM window_facts
           WHERE engagement_date >= DATE '{{logical_date}}' - INTERVAL '6 days'
           GROUP BY country
           ORDER BY n DESC
           LIMIT 10) p),
    now()
FROM window_facts
ON CONFLICT (as_of_date) DO UPDATE SET
    wau = EXCLUDED.wau,
    mau = EXCLUDED.mau,
    l7_sessions = EXCLUDED.l7_sessions,
    l30_sessions = EXCLUDED.l30_sessions,
    wau_by_plan = EXCLUDED.wau_by_plan,
    wau_by_country = EXCLUDED.wau_by_country,
    computed_at = now();
