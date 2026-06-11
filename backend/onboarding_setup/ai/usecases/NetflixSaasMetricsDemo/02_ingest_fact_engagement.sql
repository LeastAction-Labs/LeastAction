/*
{
  "name": "02_ingest_fact_engagement.sql",
  "frequency": "0 6 * * *",
  "operator_name": "AWSAthenaResultToPostgres",
  "connection_name": "aws_athena_pg_s",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {
    "target_table": "fact_daily_engagement",
    "target_columns": ["engagement_date", "customer_id", "title_id", "sessions_count", "events_count", "max_position_ms", "geo_country"],
    "load_mode": "upsert_by",
    "upsert_keys": ["engagement_date", "customer_id", "title_id"]
  },
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
              "task_name": "00_create_tables.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
SELECT DATE '{{logical_date}}' AS engagement_date,
       customer_id,
       title_id,
       CAST(COUNT(DISTINCT session_id) AS INTEGER) AS sessions_count,
       CAST(COUNT(*) AS INTEGER) AS events_count,
       CAST(MAX(position_ms) AS BIGINT) AS max_position_ms,
       arbitrary(geo_country) AS geo_country
FROM netflix_streaming_raw.playback_events
WHERE yyyy = SUBSTR('{{logical_date}}', 1, 4)
  AND mm = SUBSTR('{{logical_date}}', 6, 2)
  AND dd = SUBSTR('{{logical_date}}', 9, 2)
  AND customer_id IS NOT NULL
  AND title_id IS NOT NULL
GROUP BY customer_id, title_id
