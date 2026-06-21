# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
description = (
    "An ABC Streaming Data Warehouse built entirely on PostgreSQL. "
    "Loads real IMDB metadata for 15 curated titles, generates synthetic streaming events "
    "for 20 customers across 30 devices over 90 days, transforms through a Kimball star schema "
    "(5 dimensions, 2 facts), builds daily reporting aggregates with DOD and 7-day rolling metrics, "
    "runs 6 data-quality validation checks, builds 5 extended reporting tables "
    "(device engagement, genre mix, country engagement, title completion funnel, subscription tier), "
    "and renders 5 ABC-styled HTML dashboards — "
    "all via a 9-task DAG using PostgresqlLoadTSVFromURL, PostgresqlExecuteSQL, "
    "PostgresqlValidatorSQL, and PostgresqlGenerateHtmlTableReport operators chained with "
    "LeastActionCheckIfParentsAreDone pre-actions."
)

prompt = (
    "Create an eight-task LeastAction pipeline that builds an ABC streaming data warehouse "
    "on PostgreSQL. "
    "Task 00 downloads IMDB title metadata (15 curated tconsts) into the imdb_base schema. "
    "Task 01 creates all five schemas and seeds synthetic landing data: 15 titles, 20 customers, "
    "30 devices, and 2000 streaming events over 90 days. "
    "Task 02 deduplicates events and sessionizes into raw.stream_events_dedup and raw.view_sessions. "
    "Task 03 builds five processed dimensions: dim_customer, dim_device, dim_title (LEFT JOIN IMDB), "
    "dim_genre (unnested), and dim_date (365-day spine). "
    "Task 04 builds two processed facts: fact_view_events (event grain) and fact_view_sessions (session grain). "
    "Task 05 builds reporting.fact_streaming_daily (DOD, 7-day rolling, rank, pct-of-total) and "
    "reporting.streaming_metrics_kv (EAV/long-format with columns date, dim_key, dim_key_grouping, "
    "dim_value, metric_key, metric_value, cube_level). "
    "Task 05b builds 5 extended reporting tables: device_engagement_daily, genre_mix_daily, "
    "country_engagement_daily, title_completion_funnel (10-bucket completion funnel for top 3 titles), "
    "and subscription_tier_daily. "
    "Task 06 runs six YAML-defined SQL validation checks writing results to reporting.validation_reports. "
    "Task 07 generates an ABC-styled HTML dashboard from streaming_metrics_kv. "
    "Tasks 01 through 05 form a strict linear chain. Tasks 05b, 06 and 07 are parallel siblings, "
    "all waiting on Task 05. After all tasks complete, push 4 additional HTML reports to the catalog: "
    "ABC Device Performance, ABC Genre Engagement, ABC Country Engagement, ABC Drop-off Analysis. "
    "Connection name: keto. "
    "Task 00 uses PostgresqlLoadTSVFromURL. Tasks 01-05 and 05b use PostgresqlExecuteSQL. "
    "Task 06 uses PostgresqlValidatorSQL. Task 07 uses PostgresqlGenerateHtmlTableReport."
)

guide_docs = """\
## Prerequisites

### 1. PostgreSQL database

This usecase runs against the `postgres` service already defined in this repo's
`docker-compose.yml` — no separate container needed. If running this usecase elsewhere,
provision a PostgreSQL 13+ instance with the same credentials shown below.

### 2. Connection item — name it `keto`

| Field | Value |
|-------|-------|
| host | postgres |
| port | 5432 |
| database | keto |
| user | keto |
| password | secret |

Set `item_type` to `connection.postgresql` (not the generic `connection` type) —
the MCP `inspect_data` tool requires this exact type to query/verify data.

### 3. Operators required

| Operator | Used by |
|----------|---------|
| PostgresqlLoadTSVFromURL | Task 00 |
| PostgresqlExecuteSQL | Tasks 01–05, 05b |
| PostgresqlValidatorSQL | Task 06 |
| PostgresqlGenerateHtmlTableReport | Task 07 |

### 4. Payload files

| File | Task | Operator |
|------|------|----------|
| 00_imdb_load.json | Task 00 | PostgresqlLoadTSVFromURL |
| 01_landing_synthetic.sql | Task 01 | PostgresqlExecuteSQL |
| 02_raw_dedup.sql | Task 02 | PostgresqlExecuteSQL |
| 03_processed_dims.sql | Task 03 | PostgresqlExecuteSQL |
| 04_processed_facts.sql | Task 04 | PostgresqlExecuteSQL |
| 05_reporting_aggregates.sql | Task 05 | PostgresqlExecuteSQL |
| 05b_reporting_extended.sql | Task 05b | PostgresqlExecuteSQL |
| 06_validation.yaml | Task 06 | PostgresqlValidatorSQL |
| 07_streaming_dashboard.json | Task 07 | PostgresqlGenerateHtmlTableReport |

### 5. Output parent LAUI

Tasks 06 and 07 publish HTML reports to the catalog. Before creating those tasks,
set `output_parent_laui` in their payloads to the LAUI of your project folder.

---

## Pipeline Overview

Five PostgreSQL schemas, one direction of data flow:

```
imdb_base/     ← Task 00 (IMDB real data, monthly)
    ↓
landing/       ← Task 01 (synthetic titles, customers, devices, events)
    ↓
raw/           ← Task 02 (dedup + sessionize)
    ↓
processed/     ← Tasks 03-04 (Kimball star schema)
    ↓
reporting/     ← Task 05 (aggregates + EAV) → Task 06 (validation) + Task 07 (dashboard)
```

## DAG structure

```
Task 00: 00_imdb_load.json            (root)
    └── Task 01: 01_landing_synthetic.sql
            └── Task 02: 02_raw_dedup.sql
                    └── Task 03: 03_processed_dims.sql
                            └── Task 04: 04_processed_facts.sql
                                    └── Task 05: 05_reporting_aggregates.sql
                                            ├── Task 05b: 05b_reporting_extended.sql
                                            ├── Task 06: 06_validation.yaml
                                            └── Task 07: 07_streaming_dashboard.json
```

## Tables created end-to-end

| Table | Zone | Created by |
|-------|------|-----------|
| imdb_base.title_basics | imdb_base | Task 00 |
| imdb_base.title_ratings | imdb_base | Task 00 |
| landing.titles | landing | Task 01 |
| landing.customers | landing | Task 01 |
| landing.devices | landing | Task 01 |
| landing.stream_events | landing | Task 01 |
| raw.stream_events_dedup | raw | Task 02 |
| raw.view_sessions | raw | Task 02 |
| processed.dim_customer | processed | Task 03 |
| processed.dim_device | processed | Task 03 |
| processed.dim_title | processed | Task 03 |
| processed.dim_genre | processed | Task 03 |
| processed.dim_date | processed | Task 03 |
| processed.fact_view_events | processed | Task 04 |
| processed.fact_view_sessions | processed | Task 04 |
| reporting.fact_streaming_daily | reporting | Task 05 |
| reporting.streaming_metrics_kv | reporting | Task 05 |
| reporting.device_engagement_daily | reporting | Task 05b |
| reporting.genre_mix_daily | reporting | Task 05b |
| reporting.country_engagement_daily | reporting | Task 05b |
| reporting.title_completion_funnel | reporting | Task 05b |
| reporting.subscription_tier_daily | reporting | Task 05b |
| reporting.validation_reports | reporting | Task 06 |
| reporting.streaming_reports | reporting | Task 07 |

---

## Step-by-Step Setup

### Step 1 — Create the connection

Create a connection item named `keto` with the fields above.

### Step 2 — Upload all eight payload files

Upload each payload file to your project's payload library before creating tasks.

### Step 3 — Create Task 00 (root, no pre-action)

| Field | Value |
|-------|-------|
| Name | 00_imdb_load.json |
| Operator | PostgresqlLoadTSVFromURL |
| Connection | keto |
| Payload | 00_imdb_load.json |
| Frequency | 0 6 * * * |
| Timeout | 600 |

### Step 4 — Create Tasks 01–05 in sequence

Each task waits for its upstream task via `LeastActionCheckIfParentsAreDone`:

| Task | Name | Parent task name |
|------|------|-----------------|
| 01 | 01_landing_synthetic.sql | 00_imdb_load.json |
| 02 | 02_raw_dedup.sql | 01_landing_synthetic.sql |
| 03 | 03_processed_dims.sql | 02_raw_dedup.sql |
| 04 | 04_processed_facts.sql | 03_processed_dims.sql |
| 05 | 05_reporting_aggregates.sql | 04_processed_facts.sql |

All use operator `PostgresqlExecuteSQL`, connection `keto`, frequency `0 6 * * *`.

### Step 5 — Update output_parent_laui in payloads 06 and 07

Before creating Tasks 06 and 07, update `output_parent_laui` in `06_validation.yaml`
and `07_streaming_dashboard.json` to your project folder LAUI.

### Step 6 — Create Tasks 05b, 06 and 07 (parallel siblings, all wait on Task 05)

| Task | Name | Operator | Parent |
|------|------|----------|--------|
| 05b | 05b_reporting_extended.sql | PostgresqlExecuteSQL | 05_reporting_aggregates.sql |
| 06 | 06_validation.yaml | PostgresqlValidatorSQL | 05_reporting_aggregates.sql |
| 07 | 07_streaming_dashboard.json | PostgresqlGenerateHtmlTableReport | 05_reporting_aggregates.sql |

### Step 7 — Run the pipeline

Start Task 00 and let pre-actions drive the chain automatically,
or run tasks in order: 00 → 01 → 02 → 03 → 04 → 05 → (06 and 07 in parallel).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Task 00 timeout | IMDB file download slow | Increase task timeout to 900s |
| Task 03 dim_title has no IMDB data | Task 00 didn't load the 15 tconsts | Re-run Task 00 and check imdb_base.title_basics row count |
| Pre-action stuck RUNNING | Parent task still running or on ADHOC frequency | Set frequency to 0 6 * * * on both parent and child |
| HTML report shows No data | streaming_metrics_kv empty or date_filter too narrow | Re-run Task 05, widen date_filter in payload 07 |
| HTML report shows No content / empty | `create_catalog_item` used `{"content": "..."}` instead of `{"html": "..."}` in extra_fields | Delete the item with hard_delete=true, recreate with `extra_fields: {"html": "<html>..."}` |
| output_parent_laui not found | LAUI in payload doesn't match any catalog item | Update output_parent_laui in payloads 06 and 07 |
"""

payloads = {
    "00_imdb_load.json": """\
/*
{
  "name": "00_imdb_load.json",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlLoadTSVFromURL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {"timeout": 600},
  "actions": {}
}
*/
{
  "schema_setup": "CREATE SCHEMA IF NOT EXISTS imdb_base",
  "tables": [
    {
      "url": "https://datasets.imdbws.com/title.basics.tsv.gz",
      "target_table": "imdb_base.title_basics",
      "drop_first": true,
      "create_ddl": "CREATE TABLE imdb_base.title_basics (tconst VARCHAR(20) PRIMARY KEY, title_type VARCHAR(50), primary_title TEXT, original_title TEXT, is_adult VARCHAR(5), start_year VARCHAR(10), end_year VARCHAR(10), runtime_minutes VARCHAR(10), genres TEXT)",
      "tsv_columns": ["tconst","titleType","primaryTitle","originalTitle","isAdult","startYear","endYear","runtimeMinutes","genres"],
      "target_columns": ["tconst","title_type","primary_title","original_title","is_adult","start_year","end_year","runtime_minutes","genres"],
      "filter_column": "tconst",
      "filter_values": [
        "tt0120737","tt0816692","tt1375666","tt0468569","tt0137523",
        "tt0109830","tt0133093","tt0245429","tt6751668","tt7286456",
        "tt4154796","tt0050083","tt0076759","tt0167261","tt0167260"
      ],
      "max_rows": null,
      "batch_size": 5000
    },
    {
      "url": "https://datasets.imdbws.com/title.ratings.tsv.gz",
      "target_table": "imdb_base.title_ratings",
      "drop_first": true,
      "create_ddl": "CREATE TABLE imdb_base.title_ratings (tconst VARCHAR(20) PRIMARY KEY, average_rating NUMERIC(4,2), num_votes INTEGER)",
      "tsv_columns": ["tconst","averageRating","numVotes"],
      "target_columns": ["tconst","average_rating","num_votes"],
      "filter_column": "tconst",
      "filter_values": [
        "tt0120737","tt0816692","tt1375666","tt0468569","tt0137523",
        "tt0109830","tt0133093","tt0245429","tt6751668","tt7286456",
        "tt4154796","tt0050083","tt0076759","tt0167261","tt0167260"
      ],
      "max_rows": null,
      "batch_size": 5000
    }
  ]
}
""",

    "01_landing_synthetic.sql": """\
/*
{
  "name": "01_landing_synthetic.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "00_imdb_load.json"
            }
          ]
        }
      }
    ]
  }
}
*/
CREATE SCHEMA IF NOT EXISTS landing;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS processed;
CREATE SCHEMA IF NOT EXISTS reporting;

DROP TABLE IF EXISTS landing.titles;
CREATE TABLE landing.titles (
    title_id VARCHAR(10) PRIMARY KEY,
    tconst VARCHAR(20),
    title_name VARCHAR(200),
    release_year INTEGER,
    genre VARCHAR(100),
    runtime_minutes INTEGER
);

INSERT INTO landing.titles (title_id, tconst, title_name, release_year, genre, runtime_minutes) VALUES
('t001','tt0120737','The Fellowship Journey',2001,'Adventure',178),
('t002','tt0816692','Interstellar Dreams',2014,'Sci-Fi',169),
('t003','tt1375666','Inception Protocol',2010,'Sci-Fi',148),
('t004','tt0468569','Dark Vigilante',2008,'Action',152),
('t005','tt0137523','Project Mayhem',1999,'Drama',139),
('t006','tt0109830','Running Memories',1994,'Drama',142),
('t007','tt0133093','Simulation Theory',1999,'Sci-Fi',136),
('t008','tt0245429','Spirit Journey',2001,'Animation',125),
('t009','tt6751668','Parasite Lives',2019,'Thriller',132),
('t010','tt7286456','Clown Origins',2019,'Drama',122),
('t011','tt4154796','Heroes Assembly',2019,'Action',181),
('t012','tt0050083','Deliberation Room',1957,'Drama',96),
('t013','tt0076759','Space Opera I',1977,'Sci-Fi',121),
('t014','tt0167261','Two Towers Quest',2002,'Adventure',179),
('t015','tt0167260','Return Home',2003,'Adventure',201);

DROP TABLE IF EXISTS landing.customers;
CREATE TABLE landing.customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    subscription_type VARCHAR(20),
    country VARCHAR(10),
    age_group VARCHAR(10)
);

INSERT INTO landing.customers (customer_id, subscription_type, country, age_group) VALUES
('c001','premium','US','25-34'),
('c002','standard','UK','35-44'),
('c003','basic','CA','18-24'),
('c004','premium','AU','45-54'),
('c005','standard','DE','25-34'),
('c006','basic','FR','35-44'),
('c007','premium','JP','55+'),
('c008','standard','US','18-24'),
('c009','basic','UK','25-34'),
('c010','premium','BR','35-44'),
('c011','standard','IN','18-24'),
('c012','basic','MX','45-54'),
('c013','premium','US','25-34'),
('c014','standard','CA','35-44'),
('c015','basic','DE','18-24'),
('c016','premium','JP','25-34'),
('c017','standard','AU','45-54'),
('c018','basic','FR','55+'),
('c019','premium','IN','25-34'),
('c020','standard','US','35-44');

DROP TABLE IF EXISTS landing.devices;
CREATE TABLE landing.devices (
    device_id VARCHAR(10) PRIMARY KEY,
    device_type VARCHAR(50),
    device_version VARCHAR(100),
    os_type VARCHAR(50)
);

INSERT INTO landing.devices (device_id, device_type, device_version, os_type) VALUES
('d001','Mobile','iPhone 15','iOS'),
('d002','Smart TV','Samsung 4K','Tizen'),
('d003','Desktop','Chrome Browser','Windows'),
('d004','Tablet','iPad Pro','iOS'),
('d005','Game Console','PlayStation 5','FreeBSD'),
('d006','Mobile','Pixel 8','Android'),
('d007','Smart TV','LG OLED','WebOS'),
('d008','Desktop','Safari Browser','macOS'),
('d009','Tablet','Galaxy Tab','Android'),
('d010','Game Console','Xbox Series X','Windows'),
('d011','Mobile','iPhone 14','iOS'),
('d012','Smart TV','Sony Bravia','Android TV'),
('d013','Desktop','Firefox Browser','Linux'),
('d014','Tablet','Fire HD','FireOS'),
('d015','Game Console','Nintendo Switch','HorizonOS'),
('d016','Mobile','Galaxy S24','Android'),
('d017','Smart TV','TCL Roku TV','Roku OS'),
('d018','Desktop','Edge Browser','Windows'),
('d019','Tablet','iPad Air','iOS'),
('d020','Game Console','PlayStation 4','FreeBSD'),
('d021','Mobile','OnePlus 12','Android'),
('d022','Smart TV','Hisense U8','VIDAA'),
('d023','Desktop','Chrome Browser','macOS'),
('d024','Tablet','Galaxy Tab S9','Android'),
('d025','Game Console','Steam Deck','SteamOS'),
('d026','Mobile','iPhone 13','iOS'),
('d027','Smart TV','Vizio SmartCast','SmartCast OS'),
('d028','Desktop','Safari Browser','iOS'),
('d029','Tablet','Lenovo Tab','Android'),
('d030','Game Console','Xbox One','Windows');

DROP TABLE IF EXISTS landing.stream_events;
CREATE TABLE landing.stream_events (
    event_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10),
    title_id VARCHAR(10),
    device_id VARCHAR(10),
    event_date DATE,
    minutes_watched INTEGER,
    completion_pct NUMERIC(5,2)
);

INSERT INTO landing.stream_events (event_id, customer_id, title_id, device_id, event_date, minutes_watched, completion_pct)
SELECT
    'e' || LPAD(s.i::TEXT, 6, '0'),
    'c' || LPAD((FLOOR(RANDOM() * 20) + 1)::TEXT, 3, '0'),
    't' || LPAD((FLOOR(RANDOM() * 15) + 1)::TEXT, 3, '0'),
    'd' || LPAD((FLOOR(RANDOM() * 30) + 1)::TEXT, 3, '0'),
    CURRENT_DATE - (FLOOR(RANDOM() * 90))::INTEGER,
    (FLOOR(RANDOM() * 120) + 10)::INTEGER,
    ROUND((RANDOM() * 100)::NUMERIC, 2)
FROM generate_series(1, 2000) AS s(i);
""",

    "02_raw_dedup.sql": """\
/*
{
  "name": "02_raw_dedup.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "01_landing_synthetic.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS raw.stream_events_dedup;
CREATE TABLE raw.stream_events_dedup AS
SELECT event_id, customer_id, title_id, device_id, event_date, minutes_watched, completion_pct
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id, title_id, event_date
               ORDER BY event_id
           ) AS rn
    FROM landing.stream_events
) ranked
WHERE rn = 1;

DROP TABLE IF EXISTS raw.view_sessions;
CREATE TABLE raw.view_sessions AS
SELECT
    customer_id,
    title_id,
    event_date,
    COUNT(*) AS session_count,
    SUM(minutes_watched) AS total_minutes,
    ROUND(AVG(completion_pct)::NUMERIC, 2) AS avg_completion_pct
FROM raw.stream_events_dedup
GROUP BY customer_id, title_id, event_date;
""",

    "03_processed_dims.sql": """\
/*
{
  "name": "03_processed_dims.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "02_raw_dedup.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS processed.dim_customer;
CREATE TABLE processed.dim_customer AS
SELECT
    ROW_NUMBER() OVER (ORDER BY customer_id) AS customer_sk,
    customer_id,
    subscription_type,
    country,
    age_group
FROM landing.customers;

DROP TABLE IF EXISTS processed.dim_device;
CREATE TABLE processed.dim_device AS
SELECT
    ROW_NUMBER() OVER (ORDER BY device_id) AS device_sk,
    device_id,
    device_type,
    device_version,
    os_type
FROM landing.devices;

DROP TABLE IF EXISTS processed.dim_title;
CREATE TABLE processed.dim_title AS
SELECT
    ROW_NUMBER() OVER (ORDER BY t.title_id) AS title_sk,
    t.title_id,
    t.tconst,
    REPLACE(COALESCE(b.primary_title, t.title_name), ':', ' -') AS display_name,
    t.title_name AS synthetic_name,
    COALESCE(b.title_type, 'movie') AS title_type,
    COALESCE(b.start_year, t.release_year::TEXT) AS release_year,
    COALESCE(b.genres, t.genre) AS genres,
    COALESCE(
        CASE WHEN b.runtime_minutes ~ '^[0-9]+$' THEN b.runtime_minutes::INTEGER ELSE NULL END,
        t.runtime_minutes
    ) AS runtime_minutes,
    r.average_rating,
    r.num_votes
FROM landing.titles t
LEFT JOIN imdb_base.title_basics b ON t.tconst = b.tconst
LEFT JOIN imdb_base.title_ratings r ON t.tconst = r.tconst;

DROP TABLE IF EXISTS processed.dim_genre;
CREATE TABLE processed.dim_genre AS
SELECT DISTINCT
    t.title_id,
    TRIM(g.genre) AS genre
FROM landing.titles t
LEFT JOIN imdb_base.title_basics b ON t.tconst = b.tconst
CROSS JOIN LATERAL unnest(
    string_to_array(COALESCE(b.genres, t.genre), ',')
) AS g(genre)
WHERE TRIM(g.genre) IS NOT NULL AND LENGTH(TRIM(g.genre)) > 0;

DROP TABLE IF EXISTS processed.dim_date;
CREATE TABLE processed.dim_date AS
SELECT
    d::DATE AS date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    EXTRACT(DAY FROM d)::INTEGER AS day,
    EXTRACT(DOW FROM d)::INTEGER AS day_of_week,
    TRIM(TO_CHAR(d, 'Day')) AS day_name,
    TRIM(TO_CHAR(d, 'Month')) AS month_name,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter
FROM generate_series(
    CURRENT_DATE - INTERVAL '364 days',
    CURRENT_DATE,
    INTERVAL '1 day'
) AS d;
""",

    "04_processed_facts.sql": """\
/*
{
  "name": "04_processed_facts.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "03_processed_dims.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS processed.fact_view_events;
CREATE TABLE processed.fact_view_events AS
SELECT
    e.event_id,
    c.customer_sk,
    t.title_sk,
    d.device_sk,
    e.event_date,
    e.minutes_watched,
    e.completion_pct,
    CASE WHEN e.completion_pct >= 90 THEN TRUE ELSE FALSE END AS is_completed
FROM landing.stream_events e
JOIN processed.dim_customer c ON e.customer_id = c.customer_id
JOIN processed.dim_title t ON e.title_id = t.title_id
JOIN processed.dim_device d ON e.device_id = d.device_id;

DROP TABLE IF EXISTS processed.fact_view_sessions;
CREATE TABLE processed.fact_view_sessions AS
SELECT
    vs.customer_id,
    vs.title_id,
    vs.event_date,
    c.customer_sk,
    t.title_sk,
    vs.session_count,
    vs.total_minutes,
    vs.avg_completion_pct,
    CASE WHEN vs.avg_completion_pct >= 90 THEN TRUE ELSE FALSE END AS is_completed
FROM raw.view_sessions vs
JOIN processed.dim_customer c ON vs.customer_id = c.customer_id
JOIN processed.dim_title t ON vs.title_id = t.title_id;
""",

    "05_reporting_aggregates.sql": """\
/*
{
  "name": "05_reporting_aggregates.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "04_processed_facts.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS reporting.fact_streaming_daily;
CREATE TABLE reporting.fact_streaming_daily AS
SELECT
    agg.event_date AS date,
    agg.title_id,
    agg.display_name,
    agg.views,
    agg.watch_hours,
    agg.completion_rate,
    agg.views - LAG(agg.views, 1) OVER (
        PARTITION BY agg.title_id ORDER BY agg.event_date
    ) AS dod_views,
    ROUND(
        AVG(agg.views::NUMERIC) OVER (
            PARTITION BY agg.title_id ORDER BY agg.event_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_7d_avg,
    RANK() OVER (
        PARTITION BY agg.event_date ORDER BY agg.views DESC
    ) AS rank,
    ROUND(
        (agg.views * 100.0 / NULLIF(
            SUM(agg.views) OVER (PARTITION BY agg.event_date), 0
        ))::NUMERIC, 4
    ) AS pct_of_total
FROM (
    SELECT
        e.event_date,
        t.title_id,
        t.display_name,
        COUNT(*) AS views,
        ROUND((SUM(e.minutes_watched) / 60.0)::NUMERIC, 2) AS watch_hours,
        ROUND(AVG(e.completion_pct)::NUMERIC, 2) AS completion_rate
    FROM processed.fact_view_events e
    JOIN processed.dim_title t ON e.title_sk = t.title_sk
    GROUP BY e.event_date, t.title_id, t.display_name
) agg;

DROP TABLE IF EXISTS reporting.streaming_metrics_kv;
CREATE TABLE reporting.streaming_metrics_kv (
    id SERIAL,
    date DATE,
    dim_key VARCHAR(50),
    dim_key_grouping VARCHAR(255),
    dim_value VARCHAR(255),
    metric_key VARCHAR(100),
    metric_value NUMERIC(14,4),
    cube_level INTEGER
);

INSERT INTO reporting.streaming_metrics_kv
    (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level)
SELECT date, title_id, display_name, display_name, 'views', views::NUMERIC, 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'watch_hours', watch_hours, 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'completion_rate', completion_rate, 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'dod_views', COALESCE(dod_views, 0)::NUMERIC, 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'rolling_7d_avg', COALESCE(rolling_7d_avg, 0), 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'rank', rank::NUMERIC, 1
FROM reporting.fact_streaming_daily
UNION ALL
SELECT date, title_id, display_name, display_name, 'pct_of_total', pct_of_total, 1
FROM reporting.fact_streaming_daily;
""",

    "05b_reporting_extended.sql": """\
/*
{
  "name": "05b_reporting_extended.sql",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "05_reporting_aggregates.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS reporting.device_engagement_daily;
CREATE TABLE reporting.device_engagement_daily AS
SELECT
    e.event_date AS date,
    d.device_type,
    COUNT(*) AS views,
    ROUND((SUM(e.minutes_watched) / 60.0)::NUMERIC, 2) AS watch_hours,
    ROUND(AVG(e.completion_pct)::NUMERIC, 2) AS avg_completion_pct,
    COUNT(DISTINCT e.customer_sk) AS unique_viewers
FROM processed.fact_view_events e
JOIN processed.dim_device d ON e.device_sk = d.device_sk
GROUP BY e.event_date, d.device_type;

DROP TABLE IF EXISTS reporting.genre_mix_daily;
CREATE TABLE reporting.genre_mix_daily AS
SELECT
    e.event_date AS date,
    g.genre,
    COUNT(*) AS views,
    ROUND((SUM(e.minutes_watched) / 60.0)::NUMERIC, 2) AS watch_hours,
    ROUND(AVG(e.completion_pct)::NUMERIC, 2) AS avg_completion_pct
FROM processed.fact_view_events e
JOIN processed.dim_title t ON e.title_sk = t.title_sk
JOIN processed.dim_genre g ON t.title_id = g.title_id
GROUP BY e.event_date, g.genre;

DROP TABLE IF EXISTS reporting.country_engagement_daily;
CREATE TABLE reporting.country_engagement_daily AS
SELECT
    e.event_date AS date,
    c.country,
    COUNT(*) AS views,
    ROUND((SUM(e.minutes_watched) / 60.0)::NUMERIC, 2) AS watch_hours,
    ROUND(AVG(e.completion_pct)::NUMERIC, 2) AS avg_completion_pct,
    COUNT(DISTINCT e.customer_sk) AS unique_viewers
FROM processed.fact_view_events e
JOIN processed.dim_customer c ON e.customer_sk = c.customer_sk
GROUP BY e.event_date, c.country;

DROP TABLE IF EXISTS reporting.title_completion_funnel;
CREATE TABLE reporting.title_completion_funnel AS
WITH top_titles AS (
    SELECT title_sk, COUNT(*) AS total_views
    FROM processed.fact_view_events
    GROUP BY title_sk
    ORDER BY total_views DESC
    LIMIT 3
),
buckets AS (
    SELECT
        t.display_name AS title_name,
        WIDTH_BUCKET(e.completion_pct, 0, 100, 10) AS bucket,
        COUNT(*) AS sessions_in_bucket
    FROM processed.fact_view_events e
    JOIN processed.dim_title t ON e.title_sk = t.title_sk
    WHERE e.title_sk IN (SELECT title_sk FROM top_titles)
    GROUP BY t.display_name, WIDTH_BUCKET(e.completion_pct, 0, 100, 10)
),
starts AS (
    SELECT t.display_name AS title_name, COUNT(*) AS total_starts
    FROM processed.fact_view_events e
    JOIN processed.dim_title t ON e.title_sk = t.title_sk
    WHERE e.title_sk IN (SELECT title_sk FROM top_titles)
    GROUP BY t.display_name
)
SELECT
    b.title_name,
    b.bucket,
    (b.bucket - 1) * 10 AS bucket_start_pct,
    b.bucket * 10 AS bucket_end_pct,
    b.sessions_in_bucket,
    s.total_starts,
    ROUND((1.0 - b.sessions_in_bucket::NUMERIC / NULLIF(s.total_starts, 0)) * 100, 1) AS drop_off_pct
FROM buckets b
JOIN starts s ON b.title_name = s.title_name
ORDER BY b.title_name, b.bucket;

DROP TABLE IF EXISTS reporting.subscription_tier_daily;
CREATE TABLE reporting.subscription_tier_daily AS
SELECT
    e.event_date AS date,
    c.subscription_type,
    COUNT(*) AS views,
    ROUND((SUM(e.minutes_watched) / 60.0)::NUMERIC, 2) AS watch_hours,
    ROUND(AVG(e.completion_pct)::NUMERIC, 2) AS avg_completion_pct,
    COUNT(DISTINCT e.customer_sk) AS unique_viewers
FROM processed.fact_view_events e
JOIN processed.dim_customer c ON e.customer_sk = c.customer_sk
GROUP BY e.event_date, c.subscription_type;
""",

    "06_validation.yaml": """\
/*
{
  "name": "06_validation.yaml",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlValidatorSQL",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "05_reporting_aggregates.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
report_title: 'ABC Streaming DW — Data Quality Validation'
output_table: 'reporting.validation_reports'
output_parent_laui: '{{output_parent_laui}}'

queries:
  - name: 'Stream events loaded'
    description: 'landing.stream_events must have at least 1000 rows'
    sql: "SELECT COUNT(*) AS row_count FROM landing.stream_events"
    severity: critical
    pass_condition: 'row_count > 1000'
    display: scalar

  - name: 'IMDB titles loaded'
    description: 'imdb_base.title_basics must have at least 1 row (the 15 seed tconsts)'
    sql: "SELECT COUNT(*) AS row_count FROM imdb_base.title_basics"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'IMDB enrichment coverage'
    description: 'At least 10 of 15 titles must have an IMDB rating'
    sql: "SELECT COUNT(*) AS row_count FROM processed.dim_title WHERE average_rating IS NOT NULL"
    severity: warning
    pass_condition: 'row_count >= 10'
    display: scalar

  - name: 'No null customer surrogate keys in fact'
    description: 'fact_view_events must have no NULL customer_sk (all events must join to a customer)'
    sql: "SELECT COUNT(*) AS null_count FROM processed.fact_view_events WHERE customer_sk IS NULL"
    severity: critical
    pass_condition: 'null_count == 0'
    display: scalar

  - name: 'Date coverage greater than 30 days'
    description: 'reporting.fact_streaming_daily must span at least 30 distinct dates'
    sql: "SELECT COUNT(DISTINCT date) AS row_count FROM reporting.fact_streaming_daily"
    severity: warning
    pass_condition: 'row_count > 30'
    display: scalar

  - name: 'Completion rate in valid range'
    description: 'Average completion rate should be between 20% and 80% (sanity check on synthetic data)'
    sql: "SELECT ROUND(AVG(completion_rate)::NUMERIC, 2) AS avg_pct FROM reporting.fact_streaming_daily"
    severity: info
    pass_condition: 'avg_pct > 20 and avg_pct < 80'
    display: scalar
""",

    "07_streaming_dashboard.json": """\
/*
{
  "name": "07_streaming_dashboard.json",
  "frequency": "0 6 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "keto",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
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
              "task_name": "05_reporting_aggregates.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "data": {
    "report_title": "ABC Streaming Dashboard — Content Performance",
    "output_table": "reporting.streaming_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "netflix_dark",
      "header_bg_color": "#E50914",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#1a1a1a",
      "row_bg_color_odd": "#242424",
      "row_hover_color": "#333333",
      "border_color": "#444444",
      "font_family": "Helvetica Neue, Helvetica, Arial, sans-serif"
    },
    "query": {
      "table": "reporting.streaming_metrics_kv",
      "date_filter": "date >= CURRENT_DATE - INTERVAL '30 days'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "Daily Views by Title",
        "dim_key_grouping": "*",
        "metric_key": "views",
        "cell_format": "{value:,.0f}",
        "cell_bg_color": "#1a1a1a",
        "cell_text_color": "#E5E5E5"
      },
      {
        "display_name": "Watch Hours by Title",
        "dim_key_grouping": "*",
        "metric_key": "watch_hours",
        "cell_format": "{value:,.1f}h",
        "cell_bg_color": "#111111",
        "cell_text_color": "#E5E5E5"
      },
      {
        "display_name": "Completion Rate by Title",
        "dim_key_grouping": "*",
        "metric_key": "completion_rate",
        "cell_format": "{value:.1f}%",
        "cell_bg_color": "#1a1a1a",
        "cell_text_color": "#46D369"
      },
      {
        "display_name": "Day-over-Day View Change",
        "dim_key_grouping": "*",
        "metric_key": "dod_views",
        "cell_format": "{value:+.0f}",
        "cell_bg_color": "#111111",
        "cell_text_color": "#46D369"
      },
      {
        "display_name": "Grand Total Views",
        "dim_key_grouping": null,
        "metric_key": "views",
        "cell_format": "{value:,.0f}",
        "cell_bg_color": "#E50914",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "16px"
      },
      {
        "display_name": "Grand Total Watch Hours",
        "dim_key_grouping": null,
        "metric_key": "watch_hours",
        "cell_format": "{value:,.1f}h",
        "cell_bg_color": "#B20710",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "16px"
      }
    ]
  }
}
""",
}

skills = {
    "abc_streaming_dw.md": """\
# ABC Streaming DW — AI Orchestration Skill

## Purpose
Eight-task LeastAction DAG that builds an ABC streaming data warehouse on PostgreSQL.
Loads real IMDB metadata, seeds synthetic streaming events, transforms through a Kimball star schema,
produces daily aggregates with DOD/rolling metrics, runs data quality checks, and renders an
HTML dashboard — zero manual SQL steps.

## Operators used

| Operator | Tasks |
|----------|-------|
| PostgresqlLoadTSVFromURL | 00 |
| PostgresqlExecuteSQL | 01, 02, 03, 04, 05, 05b |
| PostgresqlValidatorSQL | 06 |
| PostgresqlGenerateHtmlTableReport | 07 |

## Constants
- `LeastActionCheckIfParentsAreDone` action LAUI: `6a2ce2e2a6105ed2d89c780b`
  (look this up once via `search_catalog(item_type="action")` if it ever changes —
  do not re-search every run, it's stable across the lifetime of an instance)

## Connection (name: `keto`, item_type: `connection.postgresql`)
```json
{
  "host": "postgres",
  "port": 5432,
  "database": "keto",
  "user": "keto",
  "password": "secret"
}
```
Must be created with `item_type: "connection.postgresql"`, not the generic `"connection"` type —
`inspect_data` (used for post-task verification) only works against `connection.postgresql` items.

## DAG structure

```
Task 00 (PostgresqlLoadTSVFromURL)      — root, no pre-action
    └── Task 01 (PostgresqlExecuteSQL)  — pre: CheckIfParentsAreDone → Task 00
            └── Task 02 (PostgresqlExecuteSQL)  — pre: → Task 01
                    └── Task 03 (PostgresqlExecuteSQL)  — pre: → Task 02
                            └── Task 04 (PostgresqlExecuteSQL)  — pre: → Task 03
                                    └── Task 05 (PostgresqlExecuteSQL)  — pre: → Task 04
                                            ├── Task 05b (PostgresqlExecuteSQL) — pre: → Task 05
                                            ├── Task 06 (PostgresqlValidatorSQL) — pre: → Task 05
                                            └── Task 07 (PostgresqlGenerateHtmlTableReport) — pre: → Task 05
```

Tasks 05b, 06 and 07 are **parallel siblings** — all wait on Task 05, not on each other.
Task 05b builds 5 extended reporting tables for device, genre, country, funnel, and subscription reporting.

## PostgresqlExecuteSQL constraints (Tasks 01–05)
- Allowed statement types: INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, COMMENT
- Blocked: top-level SELECT, BEGIN/COMMIT/ROLLBACK, dollar-quoted blocks (`$...$`)
- SELECT inside a subquery, CTE, or UNION ALL inside INSERT/CREATE TABLE AS SELECT is fine
- `CREATE TABLE ... AS SELECT ...` classifies as CREATE — always allowed

## PostgresqlGenerateHtmlTableReport constraints (Task 07)
- Source table must have exactly: date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level
- `dim_key_grouping = "*"` in template → expands one HTML row per distinct dim_value
- `dim_key_grouping = null` in template → grand total row (sums all metric_values for that metric_key)
- dim_key_grouping values in data must NOT start with `dim_` and must NOT contain `::`
- Our display_name uses `REPLACE(primary_title, ':', ' -')` to remove colons

## PostgresqlValidatorSQL constraints (Task 06)
- YAML payload: report_title, output_table, output_parent_laui, queries[]
- Each query: name, description, sql (SELECT only), severity (critical/warning/info), pass_condition
- pass_condition uses column name from query result or `row_count`
- Examples: `row_count > 1000`, `null_count == 0`, `avg_pct > 20 and avg_pct < 80`

## PostgresqlLoadTSVFromURL constraints (Task 00)
- JSON payload: schema_setup, tables[] with url, target_table, drop_first, create_ddl,
  tsv_columns, target_columns, filter_column, filter_values, max_rows, batch_size
- Set task timeout >= 600 seconds (IMDB files are large)
- Converts IMDB \\N sentinel to SQL NULL automatically

---

## Required behavior — step-by-step orchestration

### Step 0 — Verify prerequisites and resolve output_parent_laui
1. Confirm `keto` connection exists with all five required fields.
2. The eight payload files are embedded in this usecase's `payloads` dict (accessible from the usecase catalog item). Do NOT pre-upload them separately — when calling `create_task` for each task, read the corresponding payload content string directly from the usecase `payloads` dict and pass it inline as the task payload content.
3. Confirm `PostgresqlLoadTSVFromURL` operator is deployed on this instance.
4. **Auto-resolve the report destination (output_parent_laui):**
   a. Call `get_root_items` to list the top-level catalog items for the current account/project.
   b. Look for an existing folder named "Streaming Reports" or "Reports" in the catalog.
      If found, record its LAUI as `output_parent_laui`.
   c. If no suitable folder exists, call `create_catalog_item` with `item_type="folder"`,
      `name="Streaming Reports"`, and `parent_laui` set to the project root LAUI.
      Record the new folder's LAUI as `output_parent_laui`.
   d. Confirm `output_parent_laui` is a non-empty string before proceeding.
5. If any check fails, surface the error and stop.

### Step 1 — Create and run Task 00 (root)
1. Create task with `name` set to the **exact literal string** `00_imdb_load.json`
   (including the `.json` extension — do NOT strip it) with operator `PostgresqlLoadTSVFromURL`,
   connection `keto`, frequency `0 6 * * *`, timeout 600, no pre-actions.
2. After creation, confirm the task's stored `name` field equals `00_imdb_load.json` exactly
   before proceeding — this name is what every downstream pre-action will look for as a parent.
3. Start Task 00. Poll until terminal status (success or failed).
4. On failed: capture logs, surface error, abort. Do not proceed to Task 01.
5. On success: record task_id_00. Proceed.

### Step 2 — Create and run Tasks 01–05 in strict sequence
For each task in order (01 → 02 → 03 → 04 → 05):
1. Create the task with `name` set to the **exact literal payload filename including extension**
   (`01_landing_synthetic.sql`, `02_raw_dedup.sql`, etc. — never strip the extension), operator
   `PostgresqlExecuteSQL`, connection `keto`, frequency `0 6 * * *`, and a
   `LeastActionCheckIfParentsAreDone` pre-action (laui `6a2ce2e2a6105ed2d89c780b`) whose
   `task_name` is the preceding task's exact name (see DAG structure above).
2. Confirm the created task's `name` field matches the literal filename exactly — a mismatched
   extension here is the single most common cause of `LeastActionCheckIfParentsAreDone` never
   resolving and the downstream task hanging forever.
3. Start the task. Poll until terminal status.
4. On failed: capture error logs, surface to user, abort all downstream. Do not create the next task.
5. On success: record the task_id and proceed.

**NEVER create Task 02 before Task 01 reaches terminal status.**
**NEVER create Task 03 before Task 02 reaches terminal status.** (And so on.)

### Step 3 — Create and run Tasks 05b, 06 and 07 (parallel siblings)
1. Take the `output_parent_laui` resolved in Step 0 and substitute it into the payload
   content before creating Tasks 06 and 07. Specifically: take the raw payload content string
   from the usecase `payloads` dict for `06_validation.yaml` and `07_streaming_dashboard.json`,
   perform a **literal string replacement** of `{{output_parent_laui}}` with the actual LAUI
   string, then pass the substituted string as the inline payload to `create_task`.
   NEVER pass the placeholder `{{output_parent_laui}}` literally — it is not a runtime template
   variable; the operator will silently find no folder and skip the catalog upload entirely.
2. Create Task 05b with `name` set to the exact literal string `05b_reporting_extended.sql`,
   operator `PostgresqlExecuteSQL`, connection `keto`, frequency `0 6 * * *`,
   and `LeastActionCheckIfParentsAreDone` (laui `6a2ce2e2a6105ed2d89c780b`) pointing to
   `05_reporting_aggregates.sql`. This task builds 5 extended reporting tables.
3. Create Task 06 with `name` set to the exact literal string `06_validation.yaml`, operator
   `PostgresqlValidatorSQL`, connection `keto`, frequency `0 6 * * *`,
   and `LeastActionCheckIfParentsAreDone` (laui `6a2ce2e2a6105ed2d89c780b`) pointing to
   `05_reporting_aggregates.sql`.
4. Create Task 07 with `name` set to the exact literal string `07_streaming_dashboard.json`,
   operator `PostgresqlGenerateHtmlTableReport`, connection `keto`,
   frequency `0 6 * * *`, `total_retries: 1` and `retry_interval: 1` (this task has a known
   transient first-run flake — one automatic retry one minute later resolves it),
   and `LeastActionCheckIfParentsAreDone` pointing to `05_reporting_aggregates.sql`.
5. Start Tasks 05b, 06 and 07 concurrently (all three wait on Task 05, not on each other).
6. Poll each independently until terminal status.
7. Collect results from all three. Report any failures without aborting the siblings.
8. Check each task's result for `catalog_saved`. **Do not assume `true` means a catalog item
   exists** — if running via MCP/headless (no logged-in user session), `user_access_token` is
   never present in the Celery worker context and the operator-side catalog upload will always
   report `catalog_saved: false`. This is expected, not a failure — proceed to Step 3.5.

### Step 3.5 — Push final reports to the catalog via MCP (required for MCP-driven runs)
Operator-side catalog upload only works when a real logged-in user triggers the task from the
frontend (their session cookie is available). For MCP/headless runs there is no such cookie, so
this step is the actual catalog-publishing path. Publish **all** of the following:

1. **Validation report (Task 06)** — use `inspect_data` to read the latest row from
   `reporting.validation_reports.html_content` and push it via `create_catalog_item`
   (`item_type="html_report"`).
2. **Raw pivot report (Task 07)** — read every row written to `reporting.streaming_reports`
   by the current run and push each as its own `html_report` catalog item, same naming as
   the operator would use ("(Part i of N)" / "(Index)"). This preserves the full
   date×title×metric breakdown for auditing.
3. **Curated dashboard (aggregated, human-readable)** — query
   `reporting.fact_streaming_daily` directly for: total views/hours/titles/days, top 10
   titles by total views, and a 14-day daily views trend. Build a single compact HTML page
   (KPI cards + ranked top-10 table + trend chart, well under the 100,000-char limit) and
   push it via `create_catalog_item` as its own `html_report` item.
4. **ABC Device Performance — Daily** — query `reporting.device_engagement_daily` for total
   views and watch hours by device type. Build an HTML dashboard with a bar chart section
   (one row per device type showing views, hours, avg completion %, unique viewers) and
   push via `create_catalog_item`. Name: `ABC Device Performance — Daily`.
5. **ABC Genre Engagement — Weekly Mix** — query `reporting.genre_mix_daily` for total views
   and watch hours grouped by genre. Build an HTML dashboard showing genre breakdown with
   totals and percentages. Name: `ABC Genre Engagement — Weekly Mix`.
6. **ABC Country Engagement — Watch Time by Market** — query
   `reporting.country_engagement_daily` for total views, watch hours and unique viewers by
   country. Build an HTML table/chart showing top markets. Name:
   `ABC Country Engagement — Watch Time by Market`.
7. **ABC Drop-off Analysis — Completion Funnel** — query `reporting.title_completion_funnel`
   for the top 3 titles with their 10-bucket completion funnel data. Build an HTML page with
   a funnel bar chart per title showing sessions remaining and drop-off percentage at each
   10% completion bucket. Name: `ABC Drop-off Analysis — Completion Funnel`.
8. If any HTML exceeds ~90,000 characters, split into parts and push each part separately.
9. **CRITICAL — html_report field name**: When calling `create_catalog_item` for an `html_report`
   item, the HTML content MUST go into `extra_fields` under the key `"html"`, NOT `"content"`.
   Use exactly: `extra_fields: {"html": "<html>...</html>", "project_laui": "...", "account_laui": "..."}`.
   Passing `{"content": "..."}` silently succeeds (no error) but the frontend will show "No content"
   for the report — the field is simply ignored because `html_report` schema only reads `html`.
   Always verify with `get_item_schema(item_type="html_report")` if in doubt — the field is `html`.
10. Set `project_laui` and `account_laui` in `extra_fields` on every `create_catalog_item`
    call, and `parent_laui` to the resolved `output_parent_laui` from Step 0.
11. This is the step that actually makes reports visible in the LA frontend catalog for
    MCP-driven runs — Step 3's `catalog_saved` field will legitimately be `false` in this mode,
    and that's fine as long as Step 3.5 completes.

### Step 4 — Consolidated result report
Return one final summary covering all eight tasks:
- Task status (success / failed) for each
- Tables created and row counts if available
- For Task 06: checks_total, checks_passed, checks_failed, catalog_saved (operator-side)
- For Task 07: report title, metrics_count, catalog_parts_uploaded, catalog_saved (operator-side)
- Whether Step 3.5 (MCP-driven catalog push) succeeded and the resulting catalog item LAUI(s)
- For any failed task: error message, failing phase, suggested fix from guide_docs troubleshooting table

---

## Invariants
- **Sequential for Tasks 00–05.** Never start a transformation before its parent succeeds.
- **Tasks 05b, 06 and 07 are siblings.** All wait on Task 05, not on each other.
- **Never bypass `LeastActionCheckIfParentsAreDone`.** Do not sleep-poll as a substitute.
- **Task names must exactly match payload filenames, extension included — no exceptions.**
  `00_imdb_load.json`, `01_landing_synthetic.sql`, ..., `05b_reporting_extended.sql`,
  `06_validation.yaml`, `07_streaming_dashboard.json`.
  Verify the created task's `name` field after creation, every time — a dropped extension is
  silent: the task creates fine, but `LeastActionCheckIfParentsAreDone` never finds the parent
  and the downstream task just hangs with no error.
- **output_parent_laui must be resolved via MCP** (get_root_items → find or create "Streaming Reports" folder)
  before creating Tasks 06 and 07. Never pass the literal `{{output_parent_laui}}` placeholder.
- **`catalog_saved: true` in a task result only means the operator's own upload attempt
  succeeded** (requires a real `user_access_token`, i.e. a frontend-triggered run). It does
  NOT mean a catalog item exists when run via MCP/headless — see Step 3.5, which is the
  authoritative path for getting reports into the catalog in that mode.
- **`html_report` items require `extra_fields: {"html": "..."}` — NOT `{"content": "..."}`.**
  Using `content` silently succeeds but the report shows "No content" in the frontend.
  The correct field name is `html`. Verify via `get_item_schema(item_type="html_report")` if unsure.
- **Task 00 timeout must be >= 600 seconds** to allow IMDB file download.
- **Task 07 should have `total_retries: 1`, `retry_interval: 1`** to absorb its known transient
  first-run flake automatically.
- **dim_key_grouping values must not contain `::`** — enforced by `REPLACE(primary_title, ':', ' -')` in dim_title.
""",
}

metadata = {
    "tags": [
        "postgresql", "streaming", "abc", "analytics", "etl", "reporting",
        "html", "dashboard", "imdb", "kimball", "star-schema", "data-warehouse",
        "validation", "dod", "rolling-metrics",
    ],
    "category": "Data Engineering",
}

publisher = "LeastAction"
