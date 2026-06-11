# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

_00 = '''\
/*
{
  "name": "00_fact_sales_daily",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "PostgresqlSalesReportingDB",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/

DROP TABLE IF EXISTS fact_sales_daily CASCADE;

CREATE TABLE fact_sales_daily (
    sale_id BIGSERIAL,
    sale_date DATE NOT NULL,
    sale_timestamp TIMESTAMP NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    product_sku VARCHAR(50),
    category_id VARCHAR(50) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    sub_category_id VARCHAR(50),
    sub_category_name VARCHAR(100),
    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_type VARCHAR(50),
    customer_segment VARCHAR(50),
    region_id VARCHAR(50) NOT NULL,
    region_name VARCHAR(100) NOT NULL,
    sub_region_id VARCHAR(50),
    sub_region_name VARCHAR(100),
    country_id VARCHAR(50),
    country_name VARCHAR(100),
    state_id VARCHAR(50),
    state_name VARCHAR(100),
    city_id VARCHAR(50),
    city_name VARCHAR(100),
    store_id VARCHAR(50) NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    store_type VARCHAR(50),
    sales_channel VARCHAR(50),
    revenue DECIMAL(15,2) NOT NULL,
    units_sold INTEGER NOT NULL,
    cost DECIMAL(15,2) NOT NULL,
    discount_amount DECIMAL(15,2) DEFAULT 0,
    shipping_cost DECIMAL(15,2) DEFAULT 0,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    gross_profit DECIMAL(15,2) GENERATED ALWAYS AS (revenue - cost) STORED,
    net_revenue DECIMAL(15,2) GENERATED ALWAYS AS (revenue - discount_amount) STORED,
    profit_margin DECIMAL(6,2) GENERATED ALWAYS AS (
        CASE WHEN revenue > 0 THEN LEAST(((revenue - cost) / revenue * 100), 100.00) ELSE 0 END
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sale_id)
);

CREATE INDEX idx_fact_sales_date      ON fact_sales_daily(sale_date);
CREATE INDEX idx_fact_sales_product   ON fact_sales_daily(product_id);
CREATE INDEX idx_fact_sales_category  ON fact_sales_daily(category_id);
CREATE INDEX idx_fact_sales_customer  ON fact_sales_daily(customer_id);
CREATE INDEX idx_fact_sales_region    ON fact_sales_daily(region_id);
CREATE INDEX idx_fact_sales_store     ON fact_sales_daily(store_id);
CREATE INDEX idx_fact_sales_channel   ON fact_sales_daily(sales_channel);
CREATE INDEX idx_fact_sales_composite ON fact_sales_daily(sale_date, product_id, store_id);

INSERT INTO fact_sales_daily (
    sale_date, sale_timestamp, product_id, product_name, product_sku,
    category_id, category_name, customer_id, customer_name, customer_type,
    customer_segment, region_id, region_name, sub_region_id, sub_region_name,
    store_id, store_name, store_type, sales_channel,
    revenue, units_sold, cost, discount_amount, shipping_cost, tax_amount
)
SELECT
    (DATE '2023-01-01' + (i % 730) * INTERVAL '1 day')::DATE,
    TIMESTAMP '2023-01-01' + (i % 730) * INTERVAL '1 day' + (i % 86400) * INTERVAL '1 second',
    'P' || LPAD((i % 10 + 1)::TEXT, 3, '0'),
    (ARRAY['Laptop Pro','Wireless Mouse','Mechanical Keyboard','4K Monitor','USB-C Hub',
           'Webcam HD','Gaming Headset','Desk Lamp','Chair Ergonomic','Standing Desk'])[i % 10 + 1],
    'SKU-' || LPAD((i % 9999)::TEXT, 4, '0'),
    'CAT-' || LPAD((i % 5 + 1)::TEXT, 2, '0'),
    (ARRAY['Electronics','Peripherals','Audio','Lighting','Furniture'])[i % 5 + 1],
    'C' || LPAD((i % 100000)::TEXT, 6, '0'),
    'Customer ' || (i % 100000 + 1)::TEXT,
    CASE WHEN i % 3 = 0 THEN 'Business' ELSE 'Consumer' END,
    (ARRAY['Premium','Standard','Budget'])[i % 3 + 1],
    'R' || LPAD((i % 5 + 1)::TEXT, 2, '0'),
    (ARRAY['North America','Europe','Asia Pacific','Latin America','Middle East'])[i % 5 + 1],
    'SR' || LPAD((i % 14 + 1)::TEXT, 2, '0'),
    (ARRAY['Northeast','Southeast','Midwest','West Coast','Southwest',
           'Western Europe','Eastern Europe','East Asia','Southeast Asia',
           'South Asia','Northern SA','Southern SA','GCC','Levant'])[i % 14 + 1],
    'S' || LPAD((i % 50 + 1)::TEXT, 3, '0'),
    'Store ' || (i % 50 + 1)::TEXT,
    CASE WHEN i % 2 = 0 THEN 'physical' ELSE 'online' END,
    (ARRAY['online','retail','wholesale','direct'])[i % 4 + 1],
    (50.00 + (i % 2451))::DECIMAL(15,2),
    (1 + i % 50)::INTEGER,
    ((50.00 + (i % 2451)) * (0.40 + (i % 31) * 0.01))::DECIMAL(15,2),
    CASE WHEN i % 5 = 0 THEN (2.00 + (i % 99))::DECIMAL(15,2) ELSE 0.00 END,
    (i % 31)::DECIMAL(15,2),
    ((50.00 + (i % 2451)) * 0.08)::DECIMAL(15,2)
FROM generate_series(0, 499999) AS g(i);
'''

_01 = '''\
/*
{
  "name": "01_dbt_stage1",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "DbtServer",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
{"model": "fact_product_agg_daily_stage1"}
'''

_02 = '''\
/*
{
  "name": "02_dbt_stage2",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "DbtServer",
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
              "task_name": "01_dbt_stage1"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "fact_product_agg_daily_stage2"}
'''

_03 = '''\
/*
{
  "name": "03_dbt_final",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "DbtServer",
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
              "task_name": "02_dbt_stage2"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "fact_product_agg_daily"}
'''

_04 = '''\
/*
{
  "name": "04_sales_performance_reporting",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "PostgresqlSalesReportingDB",
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
              "task_name": "03_dbt_final"
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
      "host": "postgres",
      "port": 5432,
      "database": "postgres",
      "user": "keto",
      "password": "secret"
    },
    "query": {
      "table": "fact_product_agg_daily",
      "date_filter": "date >= (SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL \'30 days\'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "Laptop Pro - Revenue by Region",
        "dim_key_grouping": "Laptop Pro::dim_category::*::dim_subregion",
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#E8F5E9",
        "cell_text_color": "#2E7D32"
      },
      {
        "display_name": "Laptop Pro - Revenue DOD by Region",
        "dim_key_grouping": "Laptop Pro::dim_category::*::dim_subregion",
        "metric_key": "revenue_dod",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#FFF3E0",
        "cell_text_color": "#E65100"
      },
      {
        "display_name": "Electronics Category - Revenue by Region",
        "dim_key_grouping": "dim_product::Electronics::*::dim_subregion",
        "metric_key": "revenue",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#F3E5F5",
        "cell_text_color": "#6A1B9A",
        "text_bold": true
      },
      {
        "display_name": "North America - All Products Revenue",
        "dim_key_grouping": "dim_product::dim_category::North America::dim_subregion",
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
'''

_05 = '''\
/*
{
  "name": "05_category_performance_reporting",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "PostgresqlSalesReportingDB",
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
              "task_name": "03_dbt_final"
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
      "host": "postgres",
      "port": 5432,
      "database": "postgres",
      "user": "keto",
      "password": "secret"
    },
    "query": {
      "table": "fact_product_agg_daily",
      "date_filter": "date >= (SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL \'7 days\'",
      "limit": null
    },
    "metric_template": [
      {
        "display_name": "Peripherals Category - Revenue by Region",
        "dim_key_grouping": "dim_product::Peripherals::*::dim_subregion",
        "metric_key": "revenue",
        "cell_format": "${value:,.0f}",
        "cell_bg_color": "#E3F2FD",
        "cell_text_color": "#1565C0"
      },
      {
        "display_name": "Audio Category - Units Sold by Region",
        "dim_key_grouping": "dim_product::Audio::*::dim_subregion",
        "metric_key": "units_sold",
        "cell_format": "{value:,} units",
        "cell_bg_color": "#FFF9C4",
        "cell_text_color": "#F57F17"
      },
      {
        "display_name": "Furniture - Revenue Volatility (10D STD)",
        "dim_key_grouping": "dim_product::Furniture::*::dim_subregion",
        "metric_key": "revenue_std_10d",
        "cell_format": "${value:,.2f}",
        "cell_bg_color": "#F3E5F5",
        "cell_text_color": "#6A1B9A"
      },
      {
        "display_name": "Lighting - WOW Revenue Change by Region",
        "dim_key_grouping": "dim_product::Lighting::*::dim_subregion",
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
'''

payloads = {
    "00_fact_sales_daily":             _00,
    "01_dbt_stage1":                   _01,
    "02_dbt_stage2":                   _02,
    "03_dbt_final":                    _03,
    "04_sales_performance_reporting":  _04,
    "05_category_performance_reporting": _05,
}

skills = {
    "DBT_postgresql_sales_reporting.md": """\
# PostgreSQL + dbt Sales Reporting Pipeline — AI Orchestration Context

## Purpose
Six-task LeastAction DAG: creates a PostgreSQL fact table with 500k synthetic rows,
runs three dbt models to build a 45-metric analytics cube in `fact_product_agg_daily`,
then generates two styled HTML dashboard reports published to the catalog.
Tasks are chained via `LeastActionCheckIfParentsAreDone` pre-actions.

## Operators used

| Operator | Catalog type | Task(s) |
|----------|-------------|---------|
| `PostgresqlExecuteSQL` | `operator.postgresql` | Task 00 |
| `DBTRunModel` | `operator.python` | Tasks 01, 02, 03 |
| `PostgresqlGenerateHtmlTableReport` | `operator.postgresql` | Tasks 04, 05 |

## Connections used

| Connection | Catalog type | Points to |
|------------|-------------|-----------|
| `PostgresqlSalesReportingDB` | `connection.postgresql` | `postgres:5432/postgres` |
| `DbtServer` | `connection.dbt` | `http://dbt-server:8001` |

## Full DAG

```
Task 00  PostgresqlExecuteSQL  + PostgresqlSalesReportingDB   (ADHOC — run once manually)

Daily chain (all 0 2 * * *, same partition):
Task 01  DBTRunModel   + DbtServer  + {"model":"fact_product_agg_daily_stage1"}   (no pre-action — root)
    └── Task 02  DBTRunModel   + DbtServer  + {"model":"fact_product_agg_daily_stage2"}
            └── Task 03  DBTRunModel   + DbtServer  + {"model":"fact_product_agg_daily"}
                    ├── Task 04  PostgresqlGenerateHtmlTableReport  + PostgresqlSalesReportingDB
                    └── Task 05  PostgresqlGenerateHtmlTableReport  + PostgresqlSalesReportingDB
```

Task 00 is standalone ADHOC — it does not chain into the daily schedule.
Task 01 is the root of the daily chain (no pre-action).
Tasks 02–05 each wait on their parent via `LeastActionCheckIfParentsAreDone`.
Tasks 04 and 05 both wait on Task 03 and run in parallel.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `dbt-server unreachable` | Container not started | `docker compose up -d dbt-server` |
| `model file missing` | Volume not mounted | Check `dbt-server` volumes in `docker-compose.yml` |
| `DBTRunModel not in catalog` | setup-helper not run | `docker compose build backend && docker compose run --rm setup-helper` |
| `DbtServer connection missing` | setup-helper not run | `docker compose run --rm setup-helper` |
| `connection refused` on postgres | Wrong host | Connection must use `postgres` (service name) inside Docker |
| Task stuck in `scheduled` | Pre-action parent not yet succeeded | Wait for parent task to reach `success` |
| `No rows found` in HTML report | Date filter too narrow | Widen `date_filter` in the reporting payload |
| `output_parent_laui not found` | LAUI does not match catalog | Update `output_parent_laui` to your project folder LAUI |
""",
}

description = (
    "A complete PostgreSQL + dbt sales analytics pipeline. "
    "Task 00 creates the fact_sales_daily table and inserts 500,000 synthetic rows "
    "via a single INSERT ... SELECT FROM generate_series(0, 499999) using the "
    "PostgresqlExecuteSQL operator. "
    "Tasks 01–03 run three dbt models in sequence via the DBTRunModel operator: "
    "stage1 applies a CUBE aggregation across product × category × region × sub-region "
    "producing 5 base metrics; stage2 adds DOD, WOW, rolling 10-day avg/std/min/max, "
    "MTD and YTD; the final model adds YOY, DODLY, rank, pct-of-total, LY, LW, "
    "MTD-YOY and YTD-YOY — resulting in 45+ metric types per dimension combination. "
    "Task 04 generates a Sales Performance HTML dashboard and Task 05 generates a "
    "Category & Channel Performance HTML dashboard — both reading from "
    "fact_product_agg_daily via the PostgresqlGenerateHtmlTableReport operator. "
    "Tasks are chained via LeastActionCheckIfParentsAreDone pre-actions."
)

prompt = (
    "Create a six-task LeastAction pipeline that connects to PostgreSQL and dbt-server "
    "to run a full sales analytics workflow. "
    "Task 00 uses the PostgresqlExecuteSQL operator with connection PostgresqlSalesReportingDB "
    "to create the fact_sales_daily table and populate it with 500,000 synthetic rows using "
    "a single INSERT ... SELECT FROM generate_series(0, 499999) — do NOT use stored "
    "procedures or CALL statements as these are rejected by the SQL validator. "
    "Task 01 uses the DBTRunModel operator with connection DbtServer and payload "
    "{\"model\": \"fact_product_agg_daily_stage1\"} to run the CUBE aggregation stage. "
    "Task 02 uses DBTRunModel with payload {\"model\": \"fact_product_agg_daily_stage2\"} "
    "to compute DOD, WOW, and rolling metrics. "
    "Task 03 uses DBTRunModel with payload {\"model\": \"fact_product_agg_daily\"} "
    "to compute YOY, rank, and penetration metrics. "
    "Task 04 uses the PostgresqlGenerateHtmlTableReport operator with connection "
    "PostgresqlSalesReportingDB to generate a Sales Performance HTML dashboard "
    "(product × region metrics, 30-day rolling window). "
    "Task 05 uses PostgresqlGenerateHtmlTableReport with connection PostgresqlSalesReportingDB "
    "to generate a Category & Channel Performance HTML dashboard (7-day rolling window). "
    "Tasks 01–05 must each wait for their upstream task via LeastActionCheckIfParentsAreDone. "
    "Tasks 04 and 05 both wait on Task 03 and run in parallel."
)

guide_docs = """\
## PostgreSQL + dbt Sales Reporting Pipeline — Step-by-Step Guide

### Overview

Six tasks chained via `LeastActionCheckIfParentsAreDone` pre-actions:

```
Task 00  PostgresqlExecuteSQL      — create fact_sales_daily + insert 500k rows  (ADHOC)
    └── Task 01  DBTRunModel       — fact_product_agg_daily_stage1  (CUBE aggregation)
            └── Task 02  DBTRunModel   — fact_product_agg_daily_stage2  (DOD/WOW/rolling)
                    └── Task 03  DBTRunModel   — fact_product_agg_daily  (YOY/rank/pct)
                            ├── Task 04  PostgresqlGenerateHtmlTableReport  — Sales Performance
                            └── Task 05  PostgresqlGenerateHtmlTableReport  — Category & Channel
```

Task 00 is a one-time ADHOC bootstrap — run it manually once before starting the scheduler.
Tasks 01–05 all run on `0 2 * * *` so they share the same daily partition.
Tasks 01–05 each declare a `LeastActionCheckIfParentsAreDone` pre-action pointing to
their upstream task. Tasks 04 and 05 both wait on Task 03 and run in parallel.

---

### Tables produced

| Table | Created by | Purpose |
|-------|-----------|---------|
| `fact_sales_daily` | Task 00 | Raw transaction rows (500k synthetic rows) |
| `fact_product_agg_daily_stage1` | Task 01 | CUBE aggregation — 5 base metrics per dim combo |
| `fact_product_agg_daily_stage2` | Task 02 | Adds DOD, WOW, rolling 10-day, MTD, YTD |
| `fact_product_agg_daily` | Task 03 | Final table — 45+ metric types |
| `fact_product_agg_reports` | Tasks 04–05 | HTML report rows published to catalog |

---

### Metric types in fact_product_agg_daily (45+ total)

| Group | Metric keys |
|-------|------------|
| Base | `revenue`, `profit`, `units_sold`, `cost`, `discount` |
| DOD | `*_dod`, `*_dod_pct` |
| WOW | `*_wow` |
| Rolling 10D | `*_avg_10d`, `*_std_10d`, `*_min_10d`, `*_max_10d`, `*_sum_10d` |
| MTD / YTD | `*_mtd`, `*_ytd` |
| YOY | `*_yoy`, `*_yoy_pct` |
| DODLY | `*_dodly`, `*_dodly_pct` |
| Rolling YOY | `*_std_10d_yoy`, `*_avg_10d_yoy` |
| Period YOY | `*_mtd_yoy`, `*_ytd_yoy` |
| Lookups | `*_ly`, `*_lw` |
| Ranking | `*_rank`, `*_pct_of_total` |

---

### Prerequisites

#### 1. PostgreSQL connection — `PostgresqlSalesReportingDB`
| Field | Value |
|-------|-------|
| `host` | `postgres` |
| `port` | `5432` |
| `database` | `postgres` |
| `user` | `keto` |
| `password` | `secret` |

#### 2. dbt-server connection — `DbtServer`
| Field | Value |
|-------|-------|
| `url` | `http://dbt-server:8001` |

#### 3. dbt model files
Three SQL files must exist at `/dbt/project/models/` inside the dbt-server container:
- `fact_product_agg_daily_stage1.sql`
- `fact_product_agg_daily_stage2.sql`
- `fact_product_agg_daily.sql`

#### 4. Operators
- `PostgresqlExecuteSQL` — Task 00
- `DBTRunModel` — Tasks 01–03
- `PostgresqlGenerateHtmlTableReport` — Tasks 04–05

---

### Step 1 — Start all services

```bash
docker compose up -d mongodb redis postgres backend dbt-server
```

### Step 2 — Build and register catalog items

```bash
docker compose build backend
docker compose run --rm setup-helper
```

This registers operators, connections, and the usecase.

### Step 3 — Run Task 00 (ADHOC seed)

Run `00_fact_sales_daily` once to create and populate `fact_sales_daily`.
Tasks 01–05 will chain automatically via their pre-actions once their
parent task reaches `success` on the matching partition.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `dbt-server unreachable` | Container not started | `docker compose up -d dbt-server` |
| `model file missing` | Volume not mounted | Check `dbt-server` volumes in `docker-compose.yml` |
| `DBTRunModel not in catalog` | setup-helper not run | `docker compose build backend && docker compose run --rm setup-helper` |
| `connection refused` on postgres | Wrong host | Use `postgres` (service name), not `localhost` |
| Task stuck in `scheduled` | Pre-action parent not yet succeeded | Wait for parent task to reach `success` |
| `CALL` statement fails SQL validation | `CALL` classified as UNKNOWN by sqlparse | Use plain `INSERT ... SELECT FROM generate_series()` instead |
| `No rows found` in HTML report | Date filter too narrow or table empty | Widen `date_filter` in the reporting payload |
| `output_parent_laui not found` | LAUI does not match any catalog item | Update `output_parent_laui` in the JSON payload to your project folder LAUI |
"""

metadata = {
    "tags": ["postgresql", "dbt", "analytics", "etl", "sales", "metrics", "cube", "yoy", "dod", "reporting", "html", "dashboard"],
    "category": "Data Engineering",
}

publisher = "LeastAction"
