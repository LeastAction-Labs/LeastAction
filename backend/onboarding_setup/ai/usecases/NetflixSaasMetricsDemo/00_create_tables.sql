/*
{
  "name": "00_create_tables.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql_s",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
CREATE TABLE IF NOT EXISTS dim_customer_profiles (
    customer_id      TEXT PRIMARY KEY,
    country          TEXT,
    plan_tier        TEXT,
    age_band         TEXT,
    household_size   INT,
    signup_date      DATE,
    snapshot_date    DATE NOT NULL,
    updated_at_ts    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_daily_engagement (
    engagement_date  DATE NOT NULL,
    customer_id      TEXT NOT NULL,
    title_id         TEXT NOT NULL,
    sessions_count   INT,
    events_count     INT,
    max_position_ms  BIGINT,
    geo_country      TEXT,
    PRIMARY KEY (engagement_date, customer_id, title_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_engagement_date
    ON fact_daily_engagement (engagement_date);
CREATE INDEX IF NOT EXISTS idx_fact_engagement_customer
    ON fact_daily_engagement (customer_id);

CREATE TABLE IF NOT EXISTS metrics_daily (
    as_of_date       DATE PRIMARY KEY,
    wau              INT,
    mau              INT,
    l7_sessions      BIGINT,
    l30_sessions     BIGINT,
    wau_by_plan      JSONB,
    wau_by_country   JSONB,
    computed_at      TIMESTAMP DEFAULT now()
);
