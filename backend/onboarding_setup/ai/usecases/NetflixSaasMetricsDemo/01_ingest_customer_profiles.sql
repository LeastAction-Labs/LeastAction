/*
{
  "name": "01_ingest_customer_profiles.sql",
  "frequency": "0 6 * * *",
  "operator_name": "AWSAthenaResultToPostgres",
  "connection_name": "aws_athena_pg_s",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {
    "target_table": "dim_customer_profiles",
    "target_columns": ["customer_id", "country", "plan_tier", "age_band", "household_size", "signup_date", "snapshot_date", "updated_at_ts"],
    "load_mode": "upsert_by",
    "upsert_keys": ["customer_id"]
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
WITH ranked AS (
    SELECT customer_id, country, plan_tier, age_band, household_size, signup_date, updated_at,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) AS rn
    FROM netflix_streaming_raw.customer_profiles
    WHERE yyyy = SUBSTR('{{logical_date}}', 1, 4)
      AND mm = SUBSTR('{{logical_date}}', 6, 2)
      AND dd = SUBSTR('{{logical_date}}', 9, 2)
      AND customer_id IS NOT NULL
)
SELECT customer_id,
       country,
       plan_tier,
       age_band,
       CAST(household_size AS INTEGER),
       CAST(signup_date AS DATE),
       DATE '{{logical_date}}' AS snapshot_date,
       CAST(updated_at AS TIMESTAMP)
FROM ranked
WHERE rn = 1
