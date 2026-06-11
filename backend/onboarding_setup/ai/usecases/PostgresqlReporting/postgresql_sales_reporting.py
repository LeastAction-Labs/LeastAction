# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
description = (
    "A complete PostgreSQL sales analytics pipeline. "
    "Ingests raw daily sales transactions, runs a three-stage SQL transformation "
    "that builds a multi-dimensional aggregation cube with 45 metric types "
    "(revenue, profit, units sold, DOD, WOW, MTD, YTD, YOY, rolling 10-day avg/std/min/max, "
    "rank, penetration, and more), then generates two styled HTML dashboard reports — "
    "a Sales Performance report and a Category & Channel Performance report — "
    "and publishes them to the LeastAction catalog. "
    "Runs as a six-task DAG using the PostgresqlExecuteSQL and "
    "PostgresqlGenerateHtmlTableReport operators, chained via "
    "LeastActionCheckIfParentsAreDone pre-actions."
)

prompt = (
    "Create a six-task LeastAction pipeline that connects to a PostgreSQL database and "
    "runs a full sales analytics workflow. "
    "Task 00 ingests raw daily sales data into fact_sales_daily. "
    "Task 01 runs a cube dynamic transform into fact_product_agg_daily_stage1. "
    "Task 02 computes day-over-day and rolling metrics into fact_product_agg_daily_stage2. "
    "Task 03 computes final YOY and lookup metrics into fact_product_agg_daily (45 metric types). "
    "Task 04 generates a Sales Performance HTML dashboard report from fact_product_agg_daily. "
    "Task 05 generates a Category & Channel Performance HTML dashboard report from fact_product_agg_daily. "
    "Tasks 01-05 must each wait for their upstream task to succeed using the "
    "LeastActionCheckIfParentsAreDone pre-action. "
    "Use a PostgreSQL connection with host, port, database, user, and password fields. "
    "Tasks 00-03 use the PostgresqlExecuteSQL operator with .sql file payloads. "
    "Tasks 04-05 use the PostgresqlGenerateHtmlTableReport operator with .json payloads "
    "that define report style, query config, and per-metric display templates."
)

guide_docs = """\
## Prerequisites

### 1. PostgreSQL database
You need a running PostgreSQL instance (local, Docker, or cloud-managed).
The pipeline creates and populates all tables automatically on first run.

Recommended database: `analytics_db`

**Docker quick-start:**
```bash
docker run -d \\
  --name la-analytics-postgres \\
  -e POSTGRES_USER=postgres \\
  -e POSTGRES_PASSWORD=postgres \\
  -e POSTGRES_DB=analytics_db \\
  -p 5432:5432 \\
  postgres:15
```

> **Important:** If LeastAction runs inside Docker, use `host.docker.internal`
> as the host in your connection — not `localhost`.

### 2. Connection item
Create a **connection** item in your project with the following fields:

| Field      | Example value           |
|------------|-------------------------|
| `host`     | `host.docker.internal`  |
| `port`     | `5432`                  |
| `database` | `analytics_db`          |
| `user`     | `postgres`              |
| `password` | `postgres`              |

### 3. Operator dependencies
- **PostgresqlExecuteSQL** — requires `psycopg2-binary`
- **PostgresqlGenerateHtmlTableReport** — requires `psycopg2-binary`, `jinja2`

Both are installed automatically via the operator's `bashblock`.

### 4. Payload files
The pipeline ships six payload files (four `.sql`, two `.json`).
Place them in your project's payload library before creating tasks:

| File | Task | Operator |
|------|------|----------|
| `00_fact_sales_daily.sql` | Task 00 | PostgresqlExecuteSQL |
| `01_cube_dynamic_transform.sql` | Task 01 | PostgresqlExecuteSQL |
| `02_stage2_metrics_dod_rolling.sql` | Task 02 | PostgresqlExecuteSQL |
| `03_stage3_final_metrics_yoy_lookup.sql` | Task 03 | PostgresqlExecuteSQL |
| `sales_performance_reporting.json` | Task 04 | PostgresqlGenerateHtmlTableReport |
| `category_performance_reporting.json` | Task 05 | PostgresqlGenerateHtmlTableReport |

### 5. Output parent LAUI (for HTML report tasks)
The reporting payloads contain an `output_parent_laui` field — this is the LAUI
of the folder or project item where the generated HTML report items will be
published in the catalog. Update this to match your project's LAUI before running.

---

## PostgreSQL Sales Reporting Pipeline — Step-by-Step Guide

### Overview

This pipeline runs **six LeastAction tasks in sequence**, each chained to the previous
via `LeastActionCheckIfParentsAreDone`. The full DAG:

```
Task 00: ingest raw sales
    └── Task 01: cube stage 1 (dim_key aggregation)
            └── Task 02: stage 2 (DOD, rolling 10D metrics)
                    └── Task 03: final metrics (YOY, YTD, MTD, rank, penetration)
                            ├── Task 04: Sales Performance HTML report
                            └── Task 05: Category & Channel HTML report
```

---

### Database tables created by the pipeline

| Table | Created by | Purpose |
|-------|-----------|---------|
| `fact_sales_daily` | Task 00 | Raw transaction-level sales data |
| `fact_product_agg_daily_stage1` | Task 01 | Aggregated by dim_key (product × category × region × subregion × store) |
| `fact_product_agg_daily_stage2` | Task 02 | Adds DOD, rolling 10-day avg/std/min/max |
| `fact_product_agg_daily` | Task 03 | Final 45-metric cube: YOY, YTD, MTD, WOW, rank, penetration |
| `fact_product_agg_reports` | Tasks 04–05 | Generated HTML report rows published to catalog |

---

### Metric types in fact_product_agg_daily (45 total)

For each of `revenue`, `profit`, `units_sold`, and `cost`:

| Suffix | Meaning |
|--------|---------|
| *(none)* | Daily value |
| `_dod` | Day-over-day absolute change |
| `_dod_pct` | Day-over-day % change |
| `_wow` | Week-over-week change |
| `_lw` | Last week's value |
| `_mtd` | Month-to-date cumulative |
| `_ytd` | Year-to-date cumulative |
| `_avg_10d` | 10-day rolling average |
| `_std_10d` | 10-day rolling standard deviation |
| `_min_10d` | 10-day rolling minimum |
| `_max_10d` | 10-day rolling maximum |
| `_sum_10d` | 10-day rolling sum |
| `_rank` | Rank within date partition |
| `_pct_of_total` | Share of grand total |

---

### Setting up the pipeline

#### Step 1 — Create the PostgreSQL connection

In your project, create a connection item named `postgresql` with:
```json
{
  "host": "host.docker.internal",
  "port": 5432,
  "database": "analytics_db",
  "user": "postgres",
  "password": "postgres"
}
```

#### Step 2 — Upload payload files

Upload all six payload files to your project's payload library.

#### Step 3 — Create Task 00 (no pre-action needed)

| Field | Value |
|-------|-------|
| Task name | `00_fact_sales_daily.sql` |
| Operator | `PostgresqlExecuteSQL` |
| Connection | `postgresql` |
| Payload | `00_fact_sales_daily.sql` |
| Frequency | `0 * * * *` (hourly) |

No pre-actions. This is the root of the DAG.

#### Step 4 — Create Tasks 01, 02, 03 (each waits for its parent)

For each task, add a `LeastActionCheckIfParentsAreDone` pre-action pointing
to the previous task name:

| Task | Name | Parent task name |
|------|------|-----------------|
| 01 | `01_cube_dynamic_transform.sql` | `00_fact_sales_daily.sql` |
| 02 | `02_stage2_metrics_dod_rolling.sql` | `01_cube_dynamic_transform.sql` |
| 03 | `03_stage3_final_metrics_yoy_lookup.sql` | `02_stage2_metrics_dod_rolling.sql` |

All use operator `PostgresqlExecuteSQL`, connection `postgresql`, frequency `0 * * * *`.

#### Step 5 — Create Tasks 04 and 05 (both wait for Task 03)

| Task | Name | Payload | Parent task name |
|------|------|---------|-----------------|
| 04 | `sales_performance_reporting` | `sales_performance_reporting.json` | `03_stage3_final_metrics_yoy_lookup.sql` |
| 05 | `category_performance_reporting` | `category_performance_reporting.json` | `03_stage3_final_metrics_yoy_lookup.sql` |

Both use operator `PostgresqlGenerateHtmlTableReport`, connection `postgresql`.

> **Note:** Before attaching the JSON payloads, update `output_parent_laui`
> in each file to match your project's catalog folder LAUI.

#### Step 6 — Run the pipeline

Run tasks in order (or let the scheduler trigger them):
1. Run Task 00 → wait for success
2. Run Task 01 → wait for success
3. Run Task 02 → wait for success
4. Run Task 03 → wait for success
5. Run Task 04 and Task 05 (can run in parallel after Task 03 succeeds)

---

### HTML report configuration (Tasks 04 and 05)

The reporting JSON payload has three main sections:

**`report_style`** — Controls table appearance (theme colors, fonts, hover color).

**`query`** — Specifies which table to read and the date filter:
```json
{
  "table": "fact_product_agg_daily",
  "date_filter": "date >= CURRENT_DATE - INTERVAL '30 days'",
  "limit": null
}
```

**`metric_template`** — Array of row definitions. Each entry produces one or more
rows in the HTML table:
```json
{
  "display_name": "Laptop Pro 15 - Revenue by Region",
  "dim_key_grouping": "Laptop Pro 15::dim_category::*::dim_subregion::dim_store",
  "metric_key": "revenue",
  "cell_format": "${value:,.2f}",
  "cell_bg_color": "#E8F5E9",
  "cell_text_color": "#2E7D32"
}
```

`dim_key_grouping` uses `*` as a wildcard — `*` expands to one row per distinct
value found in that dimension position (e.g. one row per region).
`null` in `dim_key_grouping` means aggregate across all dimensions (grand total row).

---

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `500 Failed to run operator` on Tasks 00–03 | Dollar-quoted SQL (`$...$`) hits sqlparse UNKNOWN type | Rewrite functions/procedures as plain DDL or split into separate payloads |
| `connection refused` | Wrong host in connection | Use `host.docker.internal` instead of `localhost` when LeastAction runs in Docker |
| Pre-action stuck in RUNNING | Task or parent frequency is ADHOC | Set frequency to a cron expression (e.g. `0 * * * *`) on both parent and child tasks |
| `table does not exist` on Task 01+ | Previous task did not create the table | Run tasks in order and confirm each reaches `success` before running the next |
| `No rows found` in HTML report | Date filter too narrow or table empty | Widen `date_filter` in the reporting payload |
| `output_parent_laui not found` | LAUI in payload does not match any catalog item | Update `output_parent_laui` in the JSON payload to your project's folder LAUI |
"""

payloads = {
    "00_fact_sales_daily.sql": """\
/*
{
  "name": "00_fact_sales_daily.sql",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
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
DROP TABLE IF EXISTS fact_sales_daily;

CREATE TABLE fact_sales_daily (
    id SERIAL,
    date DATE NOT NULL,
    dim_product VARCHAR(100) NOT NULL,
    dim_category VARCHAR(100) NOT NULL,
    dim_region VARCHAR(100) NOT NULL,
    dim_subregion VARCHAR(100) NOT NULL,
    dim_store VARCHAR(100) NOT NULL,
    revenue NUMERIC(14,2),
    profit NUMERIC(14,2),
    units_sold INTEGER,
    cost NUMERIC(14,2),
    discount NUMERIC(14,2)
);

INSERT INTO fact_sales_daily (date, dim_product, dim_category, dim_region, dim_subregion, dim_store, revenue, profit, units_sold, cost, discount)
SELECT
    g.d::DATE AS date,
    p.dim_product,
    p.dim_category,
    r.dim_region,
    r.dim_subregion,
    s.dim_store,
    ROUND((RANDOM() * 4500 + 500)::NUMERIC, 2)  AS revenue,
    ROUND((RANDOM() * 900  + 100)::NUMERIC, 2)  AS profit,
    (RANDOM() * 90 + 10)::INTEGER                AS units_sold,
    ROUND((RANDOM() * 3600 + 400)::NUMERIC, 2)  AS cost,
    ROUND((RANDOM() * 100)::NUMERIC, 2)          AS discount
FROM generate_series(CURRENT_DATE - INTERVAL '400 days', CURRENT_DATE, INTERVAL '1 day') AS g(d)
CROSS JOIN (VALUES
    ('Laptop Pro 15',  'Electronics'),
    ('Desktop Elite',  'Computers'),
    ('Wireless Mouse', 'Accessories'),
    ('USB-C Hub',      'Accessories'),
    ('Office Chair',   'Furniture'),
    ('Standing Desk',  'Furniture'),
    ('Notebook Pack',  'Office Supplies'),
    ('Pen Set',        'Office Supplies')
) AS p(dim_product, dim_category)
CROSS JOIN (VALUES
    ('North America', 'East US'),
    ('North America', 'West US'),
    ('North America', 'Canada'),
    ('Europe',        'Western Europe'),
    ('Europe',        'Eastern Europe'),
    ('Europe',        'UK'),
    ('Asia Pacific',  'East Asia'),
    ('Asia Pacific',  'Southeast Asia'),
    ('Asia Pacific',  'Australia')
) AS r(dim_region, dim_subregion)
CROSS JOIN (VALUES
    ('Online Store'),
    ('Retail Store'),
    ('Wholesale')
) AS s(dim_store);
""",

    "01_cube_dynamic_transform.sql": """\
/*
{
  "name": "01_cube_dynamic_transform.sql",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
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
              "task_name": "00_fact_sales_daily.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS fact_product_agg_daily_stage1;

CREATE TABLE fact_product_agg_daily_stage1 (
    date DATE NOT NULL,
    dim_key VARCHAR(500) NOT NULL,
    dim_product VARCHAR(100),
    dim_category VARCHAR(100),
    dim_region VARCHAR(100),
    dim_subregion VARCHAR(100),
    dim_store VARCHAR(100),
    revenue NUMERIC(14,2),
    profit NUMERIC(14,2),
    units_sold BIGINT,
    cost NUMERIC(14,2),
    discount NUMERIC(14,2)
);

INSERT INTO fact_product_agg_daily_stage1
SELECT
    date,
    dim_product || '::' || dim_category || '::' || dim_region || '::' || dim_subregion || '::' || dim_store AS dim_key,
    dim_product,
    dim_category,
    dim_region,
    dim_subregion,
    dim_store,
    SUM(revenue)    AS revenue,
    SUM(profit)     AS profit,
    SUM(units_sold) AS units_sold,
    SUM(cost)       AS cost,
    SUM(discount)   AS discount
FROM fact_sales_daily
GROUP BY date, dim_product, dim_category, dim_region, dim_subregion, dim_store;
""",

    "02_stage2_metrics_dod_rolling.sql": """\
/*
{
  "name": "02_stage2_metrics_dod_rolling.sql",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
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
              "task_name": "01_cube_dynamic_transform.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS fact_product_agg_daily_stage2;

CREATE TABLE fact_product_agg_daily_stage2 (
    date DATE NOT NULL,
    dim_key VARCHAR(500) NOT NULL,
    dim_product VARCHAR(100),
    dim_category VARCHAR(100),
    dim_region VARCHAR(100),
    dim_subregion VARCHAR(100),
    dim_store VARCHAR(100),
    revenue NUMERIC(14,2),
    profit NUMERIC(14,2),
    units_sold BIGINT,
    cost NUMERIC(14,2),
    discount NUMERIC(14,2),
    revenue_dod NUMERIC(14,2),
    revenue_dod_pct NUMERIC(10,4),
    revenue_avg_10d NUMERIC(14,2),
    revenue_std_10d NUMERIC(14,2),
    revenue_min_10d NUMERIC(14,2),
    revenue_max_10d NUMERIC(14,2),
    revenue_sum_10d NUMERIC(14,2),
    profit_dod NUMERIC(14,2),
    profit_dod_pct NUMERIC(10,4),
    profit_avg_10d NUMERIC(14,2),
    profit_std_10d NUMERIC(14,2),
    profit_min_10d NUMERIC(14,2),
    profit_max_10d NUMERIC(14,2),
    profit_sum_10d NUMERIC(14,2),
    units_sold_dod NUMERIC(14,2),
    units_sold_dod_pct NUMERIC(10,4),
    units_sold_avg_10d NUMERIC(14,2),
    units_sold_std_10d NUMERIC(14,2),
    units_sold_min_10d NUMERIC(14,2),
    units_sold_max_10d NUMERIC(14,2),
    units_sold_sum_10d NUMERIC(14,2),
    cost_dod NUMERIC(14,2),
    cost_dod_pct NUMERIC(10,4),
    cost_avg_10d NUMERIC(14,2),
    cost_std_10d NUMERIC(14,2),
    cost_min_10d NUMERIC(14,2),
    cost_max_10d NUMERIC(14,2),
    cost_sum_10d NUMERIC(14,2)
);

INSERT INTO fact_product_agg_daily_stage2
SELECT
    date, dim_key, dim_product, dim_category, dim_region, dim_subregion, dim_store,
    revenue, profit, units_sold, cost, discount,
    revenue - LAG(revenue, 1) OVER (PARTITION BY dim_key ORDER BY date) AS revenue_dod,
    ROUND(((revenue - LAG(revenue, 1) OVER (PARTITION BY dim_key ORDER BY date))
           / NULLIF(LAG(revenue, 1) OVER (PARTITION BY dim_key ORDER BY date), 0) * 100)::NUMERIC, 4) AS revenue_dod_pct,
    ROUND(AVG(revenue)    OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS revenue_avg_10d,
    ROUND(STDDEV(revenue) OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS revenue_std_10d,
    MIN(revenue)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS revenue_min_10d,
    MAX(revenue)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS revenue_max_10d,
    SUM(revenue)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS revenue_sum_10d,
    profit - LAG(profit, 1) OVER (PARTITION BY dim_key ORDER BY date) AS profit_dod,
    ROUND(((profit - LAG(profit, 1) OVER (PARTITION BY dim_key ORDER BY date))
           / NULLIF(LAG(profit, 1) OVER (PARTITION BY dim_key ORDER BY date), 0) * 100)::NUMERIC, 4) AS profit_dod_pct,
    ROUND(AVG(profit)    OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS profit_avg_10d,
    ROUND(STDDEV(profit) OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS profit_std_10d,
    MIN(profit)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS profit_min_10d,
    MAX(profit)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS profit_max_10d,
    SUM(profit)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS profit_sum_10d,
    (units_sold - LAG(units_sold, 1) OVER (PARTITION BY dim_key ORDER BY date))::NUMERIC AS units_sold_dod,
    ROUND(((units_sold - LAG(units_sold, 1) OVER (PARTITION BY dim_key ORDER BY date))::NUMERIC
           / NULLIF(LAG(units_sold, 1) OVER (PARTITION BY dim_key ORDER BY date), 0) * 100)::NUMERIC, 4) AS units_sold_dod_pct,
    ROUND(AVG(units_sold)    OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS units_sold_avg_10d,
    ROUND(STDDEV(units_sold) OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS units_sold_std_10d,
    MIN(units_sold)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS units_sold_min_10d,
    MAX(units_sold)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS units_sold_max_10d,
    SUM(units_sold)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS units_sold_sum_10d,
    cost - LAG(cost, 1) OVER (PARTITION BY dim_key ORDER BY date) AS cost_dod,
    ROUND(((cost - LAG(cost, 1) OVER (PARTITION BY dim_key ORDER BY date))
           / NULLIF(LAG(cost, 1) OVER (PARTITION BY dim_key ORDER BY date), 0) * 100)::NUMERIC, 4) AS cost_dod_pct,
    ROUND(AVG(cost)    OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS cost_avg_10d,
    ROUND(STDDEV(cost) OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)::NUMERIC, 2) AS cost_std_10d,
    MIN(cost)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS cost_min_10d,
    MAX(cost)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS cost_max_10d,
    SUM(cost)          OVER (PARTITION BY dim_key ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS cost_sum_10d
FROM fact_product_agg_daily_stage1;
""",

    "03_stage3_final_metrics_yoy_lookup.sql": """\
/*
{
  "name": "03_stage3_final_metrics_yoy_lookup.sql",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
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
              "task_name": "02_stage2_metrics_dod_rolling.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
DROP TABLE IF EXISTS fact_product_agg_daily;

CREATE TABLE fact_product_agg_daily (
    date DATE NOT NULL,
    dim_key VARCHAR(500) NOT NULL,
    dim_product VARCHAR(100),
    dim_category VARCHAR(100),
    dim_region VARCHAR(100),
    dim_subregion VARCHAR(100),
    dim_store VARCHAR(100),
    revenue NUMERIC(14,2),
    profit NUMERIC(14,2),
    units_sold BIGINT,
    cost NUMERIC(14,2),
    discount NUMERIC(14,2),
    revenue_dod NUMERIC(14,2),
    revenue_dod_pct NUMERIC(10,4),
    revenue_wow NUMERIC(14,2),
    revenue_lw NUMERIC(14,2),
    revenue_mtd NUMERIC(14,2),
    revenue_ytd NUMERIC(14,2),
    revenue_avg_10d NUMERIC(14,2),
    revenue_std_10d NUMERIC(14,2),
    revenue_min_10d NUMERIC(14,2),
    revenue_max_10d NUMERIC(14,2),
    revenue_sum_10d NUMERIC(14,2),
    revenue_rank INTEGER,
    revenue_pct_of_total NUMERIC(10,6),
    profit_dod NUMERIC(14,2),
    profit_dod_pct NUMERIC(10,4),
    profit_wow NUMERIC(14,2),
    profit_lw NUMERIC(14,2),
    profit_mtd NUMERIC(14,2),
    profit_ytd NUMERIC(14,2),
    profit_avg_10d NUMERIC(14,2),
    profit_std_10d NUMERIC(14,2),
    profit_min_10d NUMERIC(14,2),
    profit_max_10d NUMERIC(14,2),
    profit_sum_10d NUMERIC(14,2),
    profit_rank INTEGER,
    profit_pct_of_total NUMERIC(10,6),
    units_sold_dod NUMERIC(14,2),
    units_sold_dod_pct NUMERIC(10,4),
    units_sold_wow NUMERIC(14,2),
    units_sold_lw NUMERIC(14,2),
    units_sold_mtd NUMERIC(14,2),
    units_sold_ytd NUMERIC(14,2),
    units_sold_avg_10d NUMERIC(14,2),
    units_sold_std_10d NUMERIC(14,2),
    units_sold_min_10d NUMERIC(14,2),
    units_sold_max_10d NUMERIC(14,2),
    units_sold_sum_10d NUMERIC(14,2),
    units_sold_rank INTEGER,
    units_sold_pct_of_total NUMERIC(10,6),
    cost_dod NUMERIC(14,2),
    cost_dod_pct NUMERIC(10,4),
    cost_wow NUMERIC(14,2),
    cost_lw NUMERIC(14,2),
    cost_mtd NUMERIC(14,2),
    cost_ytd NUMERIC(14,2),
    cost_avg_10d NUMERIC(14,2),
    cost_std_10d NUMERIC(14,2),
    cost_min_10d NUMERIC(14,2),
    cost_max_10d NUMERIC(14,2),
    cost_sum_10d NUMERIC(14,2),
    cost_rank INTEGER,
    cost_pct_of_total NUMERIC(10,6)
);

INSERT INTO fact_product_agg_daily
SELECT
    date, dim_key, dim_product, dim_category, dim_region, dim_subregion, dim_store,
    revenue, profit, units_sold, cost, discount,
    revenue_dod,
    revenue_dod_pct,
    revenue - LAG(revenue, 7) OVER (PARTITION BY dim_key ORDER BY date) AS revenue_wow,
    LAG(revenue, 7) OVER (PARTITION BY dim_key ORDER BY date) AS revenue_lw,
    SUM(revenue) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
                       ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS revenue_mtd,
    SUM(revenue) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date)
                       ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS revenue_ytd,
    revenue_avg_10d, revenue_std_10d, revenue_min_10d, revenue_max_10d, revenue_sum_10d,
    RANK() OVER (PARTITION BY date ORDER BY revenue DESC) AS revenue_rank,
    ROUND((revenue / NULLIF(SUM(revenue) OVER (PARTITION BY date), 0) * 100)::NUMERIC, 6) AS revenue_pct_of_total,
    profit_dod,
    profit_dod_pct,
    profit - LAG(profit, 7) OVER (PARTITION BY dim_key ORDER BY date) AS profit_wow,
    LAG(profit, 7) OVER (PARTITION BY dim_key ORDER BY date) AS profit_lw,
    SUM(profit) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
                      ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS profit_mtd,
    SUM(profit) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date)
                      ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS profit_ytd,
    profit_avg_10d, profit_std_10d, profit_min_10d, profit_max_10d, profit_sum_10d,
    RANK() OVER (PARTITION BY date ORDER BY profit DESC) AS profit_rank,
    ROUND((profit / NULLIF(SUM(profit) OVER (PARTITION BY date), 0) * 100)::NUMERIC, 6) AS profit_pct_of_total,
    units_sold_dod,
    units_sold_dod_pct,
    (units_sold - LAG(units_sold, 7) OVER (PARTITION BY dim_key ORDER BY date))::NUMERIC AS units_sold_wow,
    LAG(units_sold, 7) OVER (PARTITION BY dim_key ORDER BY date) AS units_sold_lw,
    SUM(units_sold) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
                          ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS units_sold_mtd,
    SUM(units_sold) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date)
                          ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS units_sold_ytd,
    units_sold_avg_10d, units_sold_std_10d, units_sold_min_10d, units_sold_max_10d, units_sold_sum_10d,
    RANK() OVER (PARTITION BY date ORDER BY units_sold DESC) AS units_sold_rank,
    ROUND((units_sold::NUMERIC / NULLIF(SUM(units_sold) OVER (PARTITION BY date), 0) * 100)::NUMERIC, 6) AS units_sold_pct_of_total,
    cost_dod,
    cost_dod_pct,
    cost - LAG(cost, 7) OVER (PARTITION BY dim_key ORDER BY date) AS cost_wow,
    LAG(cost, 7) OVER (PARTITION BY dim_key ORDER BY date) AS cost_lw,
    SUM(cost) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
                    ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cost_mtd,
    SUM(cost) OVER (PARTITION BY dim_key, EXTRACT(YEAR FROM date)
                    ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cost_ytd,
    cost_avg_10d, cost_std_10d, cost_min_10d, cost_max_10d, cost_sum_10d,
    RANK() OVER (PARTITION BY date ORDER BY cost DESC) AS cost_rank,
    ROUND((cost / NULLIF(SUM(cost) OVER (PARTITION BY date), 0) * 100)::NUMERIC, 6) AS cost_pct_of_total
FROM fact_product_agg_daily_stage2;
""",

    "sales_performance_reporting.json": """\
/*
{
  "name": "sales_performance_reporting.json",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "postgresql",
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
              "task_name": "03_stage3_final_metrics_yoy_lookup.sql"
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
    "report_title": "Sales Performance Dashboard - Product & Region Analysis",
    "output_table": "fact_product_agg_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "corporate_blue",
      "header_bg_color": "#1565C0",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#f9f9f9",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#E3F2FD",
      "border_color": "#BBDEFB",
      "font_family": "Segoe UI, Arial, sans-serif"
    },
    "database": {
      "host": "host.docker.internal",
      "port": 5432,
      "database": "analytics_db",
      "user": "postgres",
      "password": "postgres"
    },
    "query": {
      "table": "fact_product_agg_daily",
      "date_filter": "date >= CURRENT_DATE - INTERVAL '30 days'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "Laptop Pro 15 - Revenue by Region",
        "dim_key_grouping": "Laptop Pro 15::dim_category::*::dim_subregion::dim_store",
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#E8F5E9",
        "cell_text_color": "#2E7D32"
      },
      {
        "display_name": "Laptop Pro 15 - Revenue DOD",
        "dim_key_grouping": "Laptop Pro 15::dim_category::*::dim_subregion::dim_store",
        "metric_key": "revenue_dod",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#FFF3E0",
        "cell_text_color": "#E65100"
      },
      {
        "display_name": "Electronics Category - Revenue by Region",
        "dim_key_grouping": "dim_product::Electronics::*::dim_subregion::dim_store",
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#F3E5F5",
        "cell_text_color": "#6A1B9A",
        "text_bold": true
      },
      {
        "display_name": "North America Region - All Products Revenue",
        "dim_key_grouping": "dim_product::dim_category::North America::dim_subregion::dim_store",
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#E0F2F1",
        "cell_text_color": "#00796B",
        "text_bold": true
      },
      {
        "display_name": "Grand Total Revenue",
        "dim_key_grouping": null,
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#1565C0",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "16px"
      },
      {
        "display_name": "Grand Total Units Sold",
        "dim_key_grouping": null,
        "metric_key": "units_sold",
        "cell_format": "{value:,} units",
        "cell_bg_color": "#558B2F",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "16px"
      }
    ]
  }
}
""",

    "category_performance_reporting.json": """\
/*
{
  "name": "category_performance_reporting.json",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "postgresql",
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
              "task_name": "03_stage3_final_metrics_yoy_lookup.sql"
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
    "report_title": "Category & Channel Performance - Multi-Metric Dashboard",
    "output_table": "fact_product_agg_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "modern_green",
      "header_bg_color": "#2E7D32",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#fafafa",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#E8F5E9",
      "border_color": "#C8E6C9",
      "font_family": "Arial, sans-serif"
    },
    "database": {
      "host": "host.docker.internal",
      "port": 5432,
      "database": "analytics_db",
      "user": "postgres",
      "password": "postgres"
    },
    "query": {
      "table": "fact_product_agg_daily",
      "date_filter": "date >= CURRENT_DATE - INTERVAL '7 days'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "Computers Category - Revenue by Region",
        "dim_key_grouping": "dim_product::Computers::*::dim_subregion::dim_store",
        "metric_key": "revenue",
        "cell_format": "${value:,.0f}",
        "cell_bg_color": "#E3F2FD",
        "cell_text_color": "#1565C0"
      },
      {
        "display_name": "Accessories - Units Sold by Region",
        "dim_key_grouping": "dim_product::Accessories::*::dim_subregion::dim_store",
        "metric_key": "units_sold",
        "cell_format": "{value:,} units",
        "cell_bg_color": "#FFF9C4",
        "cell_text_color": "#F57F17"
      },
      {
        "display_name": "Furniture - Revenue Volatility by Region (10D STD)",
        "dim_key_grouping": "dim_product::Furniture::*::dim_subregion::dim_store",
        "metric_key": "revenue_std_10d",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#F3E5F5",
        "cell_text_color": "#6A1B9A"
      },
      {
        "display_name": "Office Supplies - WOW Change by Region",
        "dim_key_grouping": "dim_product::Office Supplies::*::dim_subregion::dim_store",
        "metric_key": "revenue_wow",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#E1F5FE",
        "cell_text_color": "#0277BD"
      },
      {
        "display_name": "All Categories - Total Revenue",
        "dim_key_grouping": null,
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#2E7D32",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "18px"
      },
      {
        "display_name": "All Categories - YTD Revenue",
        "dim_key_grouping": null,
        "metric_key": "revenue_ytd",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#558B2F",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "18px"
      },
      {
        "display_name": "Total Profit",
        "dim_key_grouping": null,
        "metric_key": "profit",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#1B5E20",
        "cell_text_color": "#FFFFFF",
        "text_bold": true,
        "text_size": "18px"
      }
    ]
  }
}
""",
}

skills = {
    "postgresql_sales_reporting.md": """\
# PostgreSQL Sales Reporting Pipeline — AI Context

## Purpose
This usecase orchestrates a six-task LeastAction DAG that ingests raw PostgreSQL
sales data, transforms it through three aggregation stages producing 45 metric types,
and generates two styled HTML dashboard reports published to the catalog.

## Operators used
- **PostgresqlExecuteSQL** — runs SQL payloads against a PostgreSQL connection;
  used for Tasks 00–03 (ingestion and transformation)
- **PostgresqlGenerateHtmlTableReport** — reads from `fact_product_agg_daily`,
  generates a styled HTML table based on `metric_template` config, and writes
  output rows to `fact_product_agg_reports`; used for Tasks 04–05

## Connection fields (required for both operators)
```json
{
  "host": "host.docker.internal",
  "port": 5432,
  "database": "analytics_db",
  "user": "postgres",
  "password": "postgres"
}
```
> Use `host.docker.internal` when LeastAction runs inside Docker. Use `localhost`
> only when LeastAction runs directly on the host machine.

## Task DAG structure

```
Task 00 (PostgresqlExecuteSQL)      — no pre-action (root)
    └── Task 01 (PostgresqlExecuteSQL)  — pre: CheckIfParentsAreDone → Task 00
            └── Task 02 (PostgresqlExecuteSQL)  — pre: CheckIfParentsAreDone → Task 01
                    └── Task 03 (PostgresqlExecuteSQL)  — pre: CheckIfParentsAreDone → Task 02
                            ├── Task 04 (PostgresqlGenerateHtmlTableReport) — pre: → Task 03
                            └── Task 05 (PostgresqlGenerateHtmlTableReport) — pre: → Task 03
```

## PostgresqlExecuteSQL — key constraints

The operator uses `sqlparse` to validate SQL before execution.
Allowed statement types: `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`,
`DROP`, `TRUNCATE`, `GRANT`, `REVOKE`, `COMMENT`.

**Blocked statement types:**
- `SELECT` — use a reporting operator instead
- `BEGIN` / `COMMIT` / `ROLLBACK` — implicit transaction management only
- `UNKNOWN` — sqlparse cannot parse PostgreSQL dollar-quoted blocks (`$...$`);
  avoid stored procedures or functions using dollar-quoting in the payload SQL

## PostgresqlGenerateHtmlTableReport — payload schema

```json
{
  "data": {
    "report_title": "string",
    "output_table": "fact_product_agg_reports",
    "output_parent_laui": "string — LAUI of catalog folder to publish report to",
    "report_style": {
      "theme": "string",
      "header_bg_color": "#hex",
      "header_text_color": "#hex",
      "row_bg_color_even": "#hex",
      "row_bg_color_odd": "#hex",
      "row_hover_color": "#hex",
      "border_color": "#hex",
      "font_family": "string"
    },
    "database": { "host": "...", "port": 5432, "database": "...", "user": "...", "password": "..." },
    "query": {
      "table": "fact_product_agg_daily",
      "date_filter": "date >= CURRENT_DATE - INTERVAL '30 days'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "string — row label in the HTML table",
        "dim_key_grouping": "product::category::region::subregion::store OR null for grand total",
        "metric_key": "string — one of 45 metric types (revenue, profit_dod, units_sold_ytd, ...)",
        "cell_format": "string — Python format spec e.g. '${value:,.2f}' or '{value:,} units'",
        "cell_bg_color": "#hex",
        "cell_text_color": "#hex",
        "text_bold": "boolean (optional)",
        "text_size": "string e.g. '16px' (optional)"
      }
    ]
  }
}
```

### dim_key_grouping rules
- Format: `product::category::region::subregion::store`
- Use a literal value to filter by that dimension: `"Laptop Pro 15::dim_category::*::dim_subregion::dim_store"`
- Use `*` as a wildcard — expands to one HTML row per distinct value in that dimension position
- Use `null` to aggregate across all dimensions (grand total row)
- Prefix `dim_` on a segment means "use whatever value is in that column" (no filter)

## Available metric keys (45 total)

For each base metric (`revenue`, `profit`, `units_sold`, `cost`):
`<base>`, `<base>_dod`, `<base>_dod_pct`, `<base>_wow`, `<base>_lw`,
`<base>_mtd`, `<base>_ytd`, `<base>_avg_10d`, `<base>_std_10d`,
`<base>_min_10d`, `<base>_max_10d`, `<base>_sum_10d`, `<base>_rank`,
`<base>_pct_of_total`

Plus: `discount`

## Skill orchestration model

```
API / AI (agent)
    └── MCP (tool surface)
            └── MCP skill (single tool call → single capability)
                    └── Usecase skill (THIS layer — drives the full 6-task DAG)
```

### Required behavior of the PostgreSQL Sales Reporting usecase skill

#### Step 1 — Validate prerequisites
1. Confirm the PostgreSQL connection item exists and has all five required fields.
2. Confirm all six payload files are available in the project payload library.
3. If either check fails, surface a clear error and stop — do not proceed.

#### Step 2 — Create and run Task 00 (root — no pre-action)
1. Create Task 00 (`00_fact_sales_daily.sql`) with `PostgresqlExecuteSQL`, no pre-actions.
2. Start the task and wait for terminal status.
3. On `failed`: capture the error phase and log, surface to user, abort.
4. On `success`: record `task_id_00` and proceed.

#### Step 3 — Create and run Tasks 01, 02, 03 in sequence
For each task in order (01 → 02 → 03):
1. Create the task with `PostgresqlExecuteSQL` and a `LeastActionCheckIfParentsAreDone`
   pre-action pointing to the preceding task name.
2. Start the task and wait for terminal status.
3. On `failed`: abort — do not create downstream tasks.
4. On `success`: record the `task_id` and proceed to the next.

**Do NOT create Task 02 before Task 01 reaches terminal status.**
**Do NOT create Task 03 before Task 02 reaches terminal status.**

#### Step 4 — Create and run Tasks 04 and 05 (parallel reporting, both wait on Task 03)
1. Create Task 04 (`sales_performance_reporting`) and Task 05 (`category_performance_reporting`),
   both with `PostgresqlGenerateHtmlTableReport` and `LeastActionCheckIfParentsAreDone`
   pre-actions pointing to Task 03's name.
2. Start both tasks. They may run concurrently — no ordering constraint between them.
3. Wait for both to reach terminal status.
4. On either `failed`: capture the error and include in the final report without aborting
   the sibling task's result.

#### Step 5 — Report results
Return one consolidated report covering all six tasks:
- Task status (success / failed)
- For Tasks 04–05 on success: report title, rows generated, `output_parent_laui` published to
- For any failed task: error message, failing phase, actionable fix from troubleshooting table

### Invariants
- **Sequential for Tasks 00–03.** Never start a transformation task before its parent succeeds.
- **Tasks 04 and 05 are siblings.** Both wait on Task 03, not on each other.
- **Never bypass `LeastActionCheckIfParentsAreDone`.** Do not sleep-poll as a substitute.
- **One `output_parent_laui` per report.** Confirm it resolves to a real catalog item before running Tasks 04–05.
- **Distinct task names.** Each task name must exactly match its payload filename (including `.sql` or `.json` extension as applicable).
""",
}

metadata = {
    "tags": ["postgresql", "sql", "analytics", "etl", "reporting", "html", "dashboard", "sales", "metrics"],
    "category": "Data Engineering",
}

publisher = "LeastAction"
