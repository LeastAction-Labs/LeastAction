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
  "connection_name": "dbt_postgresql",
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
  "name": "01_cube_aggregation",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
  "name": "02_rolling_metrics",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "01_cube_aggregation"
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
  "name": "03_final_metrics",
  "frequency": "0 2 * * *",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "02_rolling_metrics"
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
  "name": "04_sales_performance_report",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "dbt_postgresql",
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
              "task_name": "03_final_metrics"
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
  "name": "05_category_performance_report",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlGenerateHtmlTableReport",
  "connection_name": "dbt_postgresql",
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
              "task_name": "03_final_metrics"
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
    "01_cube_aggregation":                   _01,
    "02_rolling_metrics":                   _02,
    "03_final_metrics":                    _03,
    "04_sales_performance_report":  _04,
    "05_category_performance_report": _05,
}

skills = {
    'DBT_postgresql_sales_reporting.md': '''\
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
| `dbt_postgresql` | `connection.postgresql` | `postgres:5432/postgres` |
| `dbt_server` | `connection.dbt` | `http://dbt-server:8001` |

## Full DAG

```
Task 00  PostgresqlExecuteSQL  + dbt_postgresql   (ADHOC — run once manually)

Daily chain (all 0 2 * * *, same partition):
Task 01  DBTRunModel   + dbt_server  + {"model":"fact_product_agg_daily_stage1"}   (no pre-action — root)
    └── Task 02  DBTRunModel   + dbt_server  + {"model":"fact_product_agg_daily_stage2"}
            └── Task 03  DBTRunModel   + dbt_server  + {"model":"fact_product_agg_daily"}
                    ├── Task 04  PostgresqlGenerateHtmlTableReport  + dbt_postgresql
                    └── Task 05  PostgresqlGenerateHtmlTableReport  + dbt_postgresql
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
| `dbt_server connection missing` | setup-helper not run | `docker compose run --rm setup-helper` |
| `connection refused` on postgres | Wrong host | Connection must use `postgres` (service name) inside Docker |
| Task stuck in `scheduled` | Pre-action parent not yet succeeded | Wait for parent task to reach `success` |
| `No rows found` in HTML report | Date filter too narrow | Widen `date_filter` in the reporting payload |
| `output_parent_laui not found` | LAUI does not match catalog | Update `output_parent_laui` to your project folder LAUI |
''',
    '01_fact_product_agg_daily_stage1.md': '''\
# dbt model: `fact_product_agg_daily_stage1`

Copy into `models/fact_product_agg_daily_stage1.sql` in your dbt project. This is a **real dbt model** — a `SELECT` plus `{{ config(...) }}`; dbt creates/materializes the table for you (no `DROP`/`CREATE`/`INSERT`). Test with `dbt run --select fact_product_agg_daily_stage1`.

```sql
{{ config(materialized='table') }}

WITH 
-- Get active dimensions configuration
active_dims AS (
    SELECT 
        dimension_name,
        dimension_column,
        dimension_order,
        include_in_cube,
        is_required,
        filter_values,
        exclude_values
    FROM {{ ref('dim_cube_config') }}
    WHERE active = TRUE
    ORDER BY dimension_order
),
-- Apply dimension filters to base data
filtered_base AS (
    SELECT 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name,
        SUM(revenue) AS total_revenue,
        SUM(units_sold) AS total_units,
        SUM(cost) AS total_cost,
        SUM(discount_amount) AS total_discount
    FROM {{ source('sales', 'fact_sales_daily') }}
    -- Apply filter_values and exclude_values from config
    -- (Simplified - in production, use dynamic SQL or more complex logic)
    GROUP BY 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name
),
-- Generate CUBE of all dimension combinations
cubed_data AS (
    SELECT 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name,
        SUM(total_revenue) AS total_revenue,
        SUM(total_units) AS total_units,
        SUM(total_cost) AS total_cost,
        SUM(total_discount) AS total_discount,
        -- Count how many dimensions are NULL (aggregation level)
        (CASE WHEN product_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN category_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN region_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN sub_region_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN store_name IS NULL THEN 1 ELSE 0 END) AS cube_level
    FROM filtered_base
    GROUP BY CUBE(
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name
    )
    HAVING 
        -- Apply filter rules
        passes_cube_filters(
            product_name,
            category_name,
            region_name,
            sub_region_name,
            store_name
        ) = TRUE
        -- Exclude combinations based on config
        AND (
            -- If store not included in cube, exclude store-level combinations
            (SELECT include_in_cube FROM {{ ref('dim_cube_config') }} WHERE dimension_name = 'store') = TRUE
            OR store_name IS NULL
        )
        -- Exclude full aggregation (all NULLs) - usually not needed
        AND NOT (
            product_name IS NULL AND 
            category_name IS NULL AND 
            region_name IS NULL AND 
            sub_region_name IS NULL AND 
            store_name IS NULL
        )
),
-- Transform to key-value structure
transformed AS (
    -- Revenue metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'revenue' AS metric_key,
        total_revenue AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Units sold metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'units_sold' AS metric_key,
        total_units AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Cost metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'cost' AS metric_key,
        total_cost AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Profit metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'profit' AS metric_key,
        total_revenue - total_cost AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Discount metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'discount' AS metric_key,
        total_discount AS metric_value,
        cube_level
    FROM cubed_data
)
SELECT * FROM transformed where date is not null
```

## Supporting objects this model needs
- **Sources:** declare `fact_sales_daily` in `models/sources.yml` (used as `{{ source('sales','fact_sales_daily') }}`).
- **Seeds:** `dim_cube_config` and `dim_cube_filter_rules` (the dimension config + filter rules) become dbt seeds (`seeds/*.csv`), referenced via `{{ ref('dim_cube_config') }}` / `{{ ref('dim_cube_filter_rules') }}`. Their full seed data is included in THIS usecase — see skills `04_seed_dim_cube_config.md` and `05_seed_dim_cube_filter_rules.md`.
- **SQL UDFs:** the model calls `generate_dim_key_grouping`, `generate_dim_value`, `passes_cube_filters`. Create them once via a dbt `on-run-start` hook in `dbt_project.yml` (or a macro), e.g. `on-run-start: ["{{ create_cube_functions() }}"]`. The function bodies:

```sql
CREATE OR REPLACE FUNCTION generate_dim_key_grouping(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
BEGIN
    -- Build hierarchical key with ::dim placeholder for NULLs
    result := COALESCE(p_product, 'dim_product');
    result := result || '::' || COALESCE(p_category, 'dim_category');
    result := result || '::' || COALESCE(p_region, 'dim_region');
    result := result || '::' || COALESCE(p_sub_region, 'dim_subregion');
    result := result || '::' || COALESCE(p_store, 'dim_store');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- HELPER FUNCTION: Generate dim_value from actual values
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_dim_value(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
    parts TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Only include non-NULL values
    IF p_product IS NOT NULL THEN parts := array_append(parts, p_product); END IF;
    IF p_category IS NOT NULL THEN parts := array_append(parts, p_category); END IF;
    IF p_region IS NOT NULL THEN parts := array_append(parts, p_region); END IF;
    IF p_sub_region IS NOT NULL THEN parts := array_append(parts, p_sub_region); END IF;
    IF p_store IS NOT NULL THEN parts := array_append(parts, p_store); END IF;
    
    result := array_to_string(parts, '::', '');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- HELPER FUNCTION: Check if CUBE combination passes filter rules
-- ============================================================================

CREATE OR REPLACE FUNCTION passes_cube_filters(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_passes BOOLEAN := TRUE;
    v_rule RECORD;
BEGIN
    -- Check each active filter rule in order
    FOR v_rule IN 
        SELECT rule_type, dimension_pattern 
        FROM dim_cube_filter_rules 
        WHERE active = TRUE 
        ORDER BY rule_order
    LOOP
        -- For EXCLUDE rules: if pattern matches, reject
        IF v_rule.rule_type = 'EXCLUDE' THEN
            IF (
                -- Check each dimension in pattern
                (v_rule.dimension_pattern->>'product' = 'NULL' AND p_product IS NULL OR
                 v_rule.dimension_pattern->>'product' = 'NOT NULL' AND p_product IS NOT NULL OR
                 v_rule.dimension_pattern->>'product' IS NULL) AND
                (v_rule.dimension_pattern->>'category' = 'NULL' AND p_category IS NULL OR
                 v_rule.dimension_pattern->>'category' = 'NOT NULL' AND p_category IS NOT NULL OR
                 v_rule.dimension_pattern->>'category' IS NULL) AND
                (v_rule.dimension_pattern->>'region' = 'NULL' AND p_region IS NULL OR
                 v_rule.dimension_pattern->>'region' = 'NOT NULL' AND p_region IS NOT NULL OR
                 v_rule.dimension_pattern->>'region' IS NULL) AND
                (v_rule.dimension_pattern->>'sub_region' = 'NULL' AND p_sub_region IS NULL OR
                 v_rule.dimension_pattern->>'sub_region' = 'NOT NULL' AND p_sub_region IS NOT NULL OR
                 v_rule.dimension_pattern->>'sub_region' IS NULL) AND
                (v_rule.dimension_pattern->>'store' = 'NULL' AND p_store IS NULL OR
                 v_rule.dimension_pattern->>'store' = 'NOT NULL' AND p_store IS NOT NULL OR
                 v_rule.dimension_pattern->>'store' IS NULL)
            ) THEN
                RETURN FALSE;  -- Exclude this combination
            END IF;
        END IF;
        
        -- For KEEP rules: if pattern matches, keep (set flag)
        -- For KEEP rules: if NO patterns match by end, reject
        -- (Implementation can be extended)
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- STAGE 1: TRANSFORM TO KEY-VALUE STRUCTURE USING CUBE
-- ============================================================================
```
''',
    '02_fact_product_agg_daily_stage2.md': '''\
# dbt model: `fact_product_agg_daily_stage2`

Copy into `models/fact_product_agg_daily_stage2.sql` in your dbt project. This is a **real dbt model** — a `SELECT` plus `{{ config(...) }}`; dbt creates/materializes the table for you (no `DROP`/`CREATE`/`INSERT`). Test with `dbt run --select fact_product_agg_daily_stage2`.

Reads `{{ ref('fact_product_agg_daily_stage1') }}` and appends DOD, WOW, rolling 10-day (avg/std/min/max/sum), MTD and YTD metric rows via `UNION ALL`.

```sql
{{ config(materialized='table') }}

SELECT date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value
FROM {{ ref('fact_product_agg_daily_stage1') }}

UNION ALL
(
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 1) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_day_value
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit', 'cost')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_dod' AS metric_key,
    COALESCE(metric_value - prev_day_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_day_value IS NOT NULL
)

UNION ALL
(
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 1) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_day_value
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_dod_pct' AS metric_key,
    CASE 
        WHEN prev_day_value = 0 THEN 0
        ELSE ((metric_value - prev_day_value) / NULLIF(prev_day_value, 0)) * 100
    END AS metric_value
FROM metric_with_lag
WHERE prev_day_value IS NOT NULL
)

UNION ALL
(
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 7) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_week_value
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_wow' AS metric_key,
    COALESCE(metric_value - prev_week_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_week_value IS NOT NULL
)

UNION ALL
(
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        STDDEV(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS std_10d
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_std_10d' AS metric_key,
    COALESCE(std_10d, 0) AS metric_value
FROM rolling_window
)

UNION ALL
(
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        AVG(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS avg_10d
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_avg_10d' AS metric_key,
    COALESCE(avg_10d, 0) AS metric_value
FROM rolling_window
)

UNION ALL
(
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        MIN(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS min_10d
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_min_10d' AS metric_key,
    COALESCE(min_10d, 0) AS metric_value
FROM rolling_window
)

UNION ALL
(
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        MAX(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS max_10d
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_max_10d' AS metric_key,
    COALESCE(max_10d, 0) AS metric_value
FROM rolling_window
)

UNION ALL
(
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS sum_10d
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_sum_10d' AS metric_key,
    COALESCE(sum_10d, 0) AS metric_value
FROM rolling_window
)

UNION ALL
(
WITH mtd_calc AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY 
                dim_key_grouping, 
                dim_value, 
                metric_key,
                DATE_TRUNC('month', date)
            ORDER BY date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS mtd_sum
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_mtd' AS metric_key,
    COALESCE(mtd_sum, 0) AS metric_value
FROM mtd_calc
)

UNION ALL
(
WITH ytd_calc AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY 
                dim_key_grouping, 
                dim_value, 
                metric_key,
                DATE_TRUNC('year', date)
            ORDER BY date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS ytd_sum
    FROM {{ ref('fact_product_agg_daily_stage1') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_ytd' AS metric_key,
    COALESCE(ytd_sum, 0) AS metric_value
FROM ytd_calc
)
```
''',
    '03_fact_product_agg_daily.md': '''\
# dbt model: `fact_product_agg_daily`

Copy into `models/fact_product_agg_daily.sql` in your dbt project. This is a **real dbt model** — a `SELECT` plus `{{ config(...) }}`; dbt creates/materializes the table for you (no `DROP`/`CREATE`/`INSERT`). Test with `dbt run --select fact_product_agg_daily`.

The final model. Reads `{{ ref('fact_product_agg_daily_stage2') }}` and appends YOY, DODLY, rolling-YOY, period-YOY, LY/LW lookups, rank and pct-of-total metric rows via `UNION ALL`.

```sql
{{ config(materialized='table') }}

SELECT date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value
FROM {{ ref('fact_product_agg_daily_stage2') }}

UNION ALL
(
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit', 'cost')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_yoy' AS metric_key,
    COALESCE(metric_value - prev_year_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_year_value IS NOT NULL
)

UNION ALL
(
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_yoy_pct' AS metric_key,
    CASE 
        WHEN prev_year_value = 0 THEN 0
        ELSE ((metric_value - prev_year_value) / NULLIF(prev_year_value, 0)) * 100
    END AS metric_value
FROM metric_with_lag
WHERE prev_year_value IS NOT NULL
)

UNION ALL
(
WITH dod_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS dod_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_dod' 
      AND metric_key NOT LIKE '%_dod_pct'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_dod', '_dodly') AS metric_key,
    COALESCE(metric_value - dod_last_year, 0) AS metric_value
FROM dod_current
WHERE dod_last_year IS NOT NULL
)

UNION ALL
(
WITH dod_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS dod_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_dod' 
      AND metric_key NOT LIKE '%_dod_pct'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_dod', '_dodly_pct') AS metric_key,
    CASE 
        WHEN dod_last_year = 0 THEN 0
        ELSE ((metric_value - dod_last_year) / NULLIF(ABS(dod_last_year), 0)) * 100
    END AS metric_value
FROM dod_current
WHERE dod_last_year IS NOT NULL
)

UNION ALL
(
WITH std_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS std_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_std_10d'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_std_10d', '_std_10d_yoy') AS metric_key,
    COALESCE(metric_value - std_last_year, 0) AS metric_value
FROM std_current
WHERE std_last_year IS NOT NULL
)

UNION ALL
(
WITH avg_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS avg_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_avg_10d'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_avg_10d', '_avg_10d_yoy') AS metric_key,
    COALESCE(metric_value - avg_last_year, 0) AS metric_value
FROM avg_current
WHERE avg_last_year IS NOT NULL
)

UNION ALL
(
WITH prev_year_lookup AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_ly' AS metric_key,
    COALESCE(prev_year_value, 0) AS metric_value
FROM prev_year_lookup
WHERE prev_year_value IS NOT NULL
)

UNION ALL
(
WITH prev_week_lookup AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        LAG(metric_value, 7) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_week_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_lw' AS metric_key,
    COALESCE(prev_week_value, 0) AS metric_value
FROM prev_week_lookup
WHERE prev_week_value IS NOT NULL
)

UNION ALL
(
WITH mtd_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS mtd_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_mtd'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_mtd', '_mtd_yoy') AS metric_key,
    COALESCE(metric_value - mtd_last_year, 0) AS metric_value
FROM mtd_current
WHERE mtd_last_year IS NOT NULL
)

UNION ALL
(
WITH ytd_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS ytd_last_year
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key LIKE '%_ytd'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_ytd', '_ytd_yoy') AS metric_key,
    COALESCE(metric_value - ytd_last_year, 0) AS metric_value
FROM ytd_current
WHERE ytd_last_year IS NOT NULL
)

UNION ALL
(
WITH ranked AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        RANK() OVER (
            PARTITION BY date, dim_key_grouping, metric_key
            ORDER BY metric_value DESC
        ) AS rank_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_rank' AS metric_key,
    rank_value AS metric_value
FROM ranked
)

UNION ALL
(
WITH totals AS (
    SELECT 
        date,
        dim_key_grouping,
        metric_key,
        SUM(metric_value) AS total_value
    FROM {{ ref('fact_product_agg_daily_stage2') }}
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
    GROUP BY date, dim_key_grouping, metric_key
),
with_totals AS (
    SELECT 
        f.date,
        f.dim_key,
        f.dim_key_grouping,
        f.dim_value,
        f.metric_key,
        f.metric_value,
        t.total_value
    FROM {{ ref('fact_product_agg_daily_stage2') }} f
    INNER JOIN totals t 
        ON f.date = t.date 
        AND f.dim_key_grouping = t.dim_key_grouping 
        AND f.metric_key = t.metric_key
    WHERE f.metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_pct_of_total' AS metric_key,
    CASE 
        WHEN total_value = 0 THEN 0
        ELSE (metric_value / NULLIF(total_value, 0)) * 100
    END AS metric_value
FROM with_totals
)
```
''',
    '04_seed_dim_cube_config.md': '''\
# dbt seed: `dim_cube_config`

Static reference data for the cube. Save as `seeds/dim_cube_config.csv` and load with `dbt seed` (or `dbt build`, which loads seeds before models). `fact_product_agg_daily_stage1` reads it via `{{ ref('dim_cube_config') }}`. Empty `filter_values`/`exclude_values`/`max_cardinality` load as NULL (they are optional cube filters — unset by default).

```csv
config_name,dimension_order,dimension_name,dimension_column,include_in_cube,is_required,filter_values,exclude_values,max_cardinality,description,active
product,1,product,product_name,true,false,,,,Product dimension - always include,true
category,2,category,category_name,true,false,,,,Category dimension,true
region,3,region,region_name,true,false,,,,Region dimension,true
sub_region,4,sub_region,sub_region_name,true,false,,,,Sub-region dimension - drill down from region,true
store,5,store,store_name,false,false,,,,Store dimension - excluded by default to reduce cardinality,true
```
''',
    '05_seed_dim_cube_filter_rules.md': '''\
# dbt seed: `dim_cube_filter_rules`

Static KEEP/EXCLUDE rules read by the `passes_cube_filters` UDF (on-run-start hook). Save as `seeds/dim_cube_filter_rules.csv`. `dimension_pattern` is JSON — type it as `jsonb` in the seed config:

```yaml
# dbt_project.yml
seeds:
  your_project:
    dim_cube_filter_rules:
      +column_types:
        dimension_pattern: jsonb
```

```csv
rule_name,rule_type,rule_order,dimension_pattern,description,active
require_product,KEEP,1,"{""product"": ""NOT NULL""}",Always require product dimension - no product=NULL combinations,true
no_subregion_without_region,EXCLUDE,2,"{""region"": ""NULL"", ""sub_region"": ""NOT NULL""}",Cannot have sub-region without region,true
no_store_without_region,EXCLUDE,3,"{""region"": ""NULL"", ""store"": ""NOT NULL""}",Cannot have store without region,true
```
''',
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
    "Task 00 uses the PostgresqlExecuteSQL operator with connection dbt_postgresql "
    "to create the fact_sales_daily table and populate it with 500,000 synthetic rows using "
    "a single INSERT ... SELECT FROM generate_series(0, 499999) — do NOT use stored "
    "procedures or CALL statements as these are rejected by the SQL validator. "
    "Task 01 uses the DBTRunModel operator with connection dbt_server and payload "
    "{\"model\": \"fact_product_agg_daily_stage1\"} to run the CUBE aggregation stage. "
    "Task 02 uses DBTRunModel with payload {\"model\": \"fact_product_agg_daily_stage2\"} "
    "to compute DOD, WOW, and rolling metrics. "
    "Task 03 uses DBTRunModel with payload {\"model\": \"fact_product_agg_daily\"} "
    "to compute YOY, rank, and penetration metrics. "
    "Task 04 uses the PostgresqlGenerateHtmlTableReport operator with connection "
    "dbt_postgresql to generate a Sales Performance HTML dashboard "
    "(product × region metrics, 30-day rolling window). "
    "Task 05 uses PostgresqlGenerateHtmlTableReport with connection dbt_postgresql "
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

#### 1. PostgreSQL connection — `dbt_postgresql`
| Field | Value |
|-------|-------|
| `host` | `postgres` |
| `port` | `5432` |
| `database` | `postgres` |
| `user` | `keto` |
| `password` | `secret` |

#### 2. dbt-server connection — `dbt_server`
| Field | Value |
|-------|-------|
| `url` | `http://dbt-server:8001` |

#### 3. dbt model files
Three model files must exist in the dbt project's `models/` directory. **The full dbt model SQL for each
is in this usecase's skills** (`01_/02_/03_fact_product_agg_daily*.md`) — copy each into the matching file.
They are real dbt models (a `SELECT` + `{{ config(materialized='table') }}`); dbt handles
DROP/CREATE/materialization. Test a model with `dbt run --select <model>`.
- `models/fact_product_agg_daily_stage1.sql`
- `models/fact_product_agg_daily_stage2.sql`
- `models/fact_product_agg_daily.sql`

Stage 1 also needs supporting dbt objects (all included in this usecase's skills): a `sources.yml`
declaring `fact_sales_daily`; two **seeds** — `dim_cube_config` (skill 04) and `dim_cube_filter_rules`
(skill 05), with full CSV data; and three SQL UDFs created via an `on-run-start` hook (in skill 01).
Run with `dbt build` (or `dbt seed` then `dbt run`) so the seeds load before the models. Stage 2 and the
final model only `{{ ref(...) }}` their upstream model.

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
    "tags": ["flavor:S+P", "lifecycle:transformation", "dbt-invocation", "dbt", "postgresql", "analytics", "etl", "sales", "metrics", "cube", "yoy", "dod", "reporting", "html", "dashboard"],
    "category": "Transformation",
}

publisher = "LeastAction"
