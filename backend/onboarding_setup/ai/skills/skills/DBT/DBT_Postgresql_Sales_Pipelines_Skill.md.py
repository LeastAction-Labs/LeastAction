# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = """\
# dbt Sales Reporting Pipeline — Orchestration Skill

## Pipeline overview
Six-task DAG: seed 500k synthetic sales rows, run 3 dbt transformation stages
(CUBE → rolling metrics → YOY/rank), generate 2 styled HTML dashboard reports.

```
00_fact_sales_daily (PostgresqlExecuteSQL — ADHOC seed)
    └── 01_dbt_stage1 (DBTRunModel — CUBE aggregation, 5 base metrics)
            └── 02_dbt_stage2 (DBTRunModel — DOD/WOW/rolling 10D/MTD/YTD)
                    └── 03_dbt_final (DBTRunModel — YOY/rank/pct/LY/LW)
                            ├── 04_sales_performance_reporting (PostgresqlGenerateHtmlTableReport)
                            └── 05_category_performance_reporting (PostgresqlGenerateHtmlTableReport)
```

## Connections

| Name | Type | Points to |
|------|------|-----------|
| `PostgresqlSalesReportingDB` | `connection.postgresql` | `postgres-demo:5432/postgres_demo_db` |
| `DbtServer` | `connection.dbt` | `http://dbt-demo:8001` |

## Operators

| Operator | Tasks |
|----------|-------|
| `PostgresqlExecuteSQL` | 00 (seed) |
| `DBTRunModel` | 01, 02, 03 (dbt models) |
| `PostgresqlGenerateHtmlTableReport` | 04, 05 (reports) |

## dbt models

| Model | Stage | Input | Output metrics |
|-------|-------|-------|----------------|
| `fact_product_agg_daily_stage1` | CUBE | `fact_sales_daily` | revenue, units_sold, cost, profit, discount per dim combo |
| `fact_product_agg_daily_stage2` | Rolling | stage1 | +DOD, DOD%, WOW, avg/std/min/max/sum 10D, MTD, YTD |
| `fact_product_agg_daily` | Final | stage2 | +YOY, YOY%, DODLY, rank, pct_of_total, LY, LW, MTD-YOY, YTD-YOY |

Total: **45+ metric types** per dimension combination per day.

## Supporting dbt objects

| Object | Type | Purpose |
|--------|------|---------|
| `dim_cube_config` | seed (CSV) | Dimension configuration — which dims to include in CUBE |
| `dim_cube_filter_rules` | seed (CSV) | KEEP/EXCLUDE rules for CUBE combinations |
| `sources.yml` | source | Declares `fact_sales_daily` as `{{ source('sales', 'fact_sales_daily') }}` |
| `generate_dim_key_grouping()` | UDF | Builds `dim_product::dim_category::...` key from dimension values |
| `generate_dim_value()` | UDF | Builds display value from non-NULL dimension values |
| `passes_cube_filters()` | UDF | Evaluates KEEP/EXCLUDE rules against a dimension combination |

UDFs are created via `on-run-start` hook in `dbt_project.yml`.

## Key-value fact table structure

The dbt models produce a key-value (EAV) structure, not a wide table:

| Column | Example | Description |
|--------|---------|-------------|
| `date` | 2024-06-15 | Aggregation date |
| `dim_key` | `dim_product::dim_category::dim_region::dim_subregion::dim_store` | Dimension schema |
| `dim_key_grouping` | `Laptop Pro::Electronics::North America::Northeast::dim_store` | Dimension values (dim_* = aggregated) |
| `dim_value` | `Laptop Pro::Electronics::North America::Northeast` | Non-NULL dimension values only |
| `metric_key` | `revenue_dod` | Metric name |
| `metric_value` | 1234.56 | Metric value |

The `PostgresqlGenerateHtmlTableReport` operator uses `metric_template` to pivot this into a styled HTML table.

## Report configuration

Reports use **pivot mode** — `metric_template` in the payload specifies which dimension×metric combinations
to display as rows, with dates as columns:

```json
{
  "display_name": "Laptop Pro - Revenue by Region",
  "dim_key_grouping": "Laptop Pro::dim_category::*::dim_subregion",
  "metric_key": "revenue",
  "cell_format": "${value:,.2f}",
  "cell_bg_color": "#E8F5E9"
}
```

- `dim_key_grouping` pattern: exact value or `*` (wildcard) per dimension position
- `metric_key`: which metric to display
- `cell_format`, `cell_bg_color`, `cell_text_color`: per-metric cell styling

## Data contract
See `DBT_Postgresql_Sales_Data_Contract` skill for the data contract enforcement
on `fact_sales_daily` — schema, PK, nullability, domain, volume checks.

## Deploying
```
deploy usecase dbt-sales-reporting
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `dbt-server unreachable` | `docker compose up -d dbt-demo` |
| `model file missing` | Copy model SQL from skills 01-03 into `dbt-server/demo_project/models/` |
| `CALL statement fails` | Use `INSERT ... SELECT FROM generate_series()` — not stored procedures |
| Task stuck in `scheduled` | Parent task hasn't reached `success` yet |
| Empty HTML report | Widen `date_filter` in the report payload |
"""

description = "AI orchestration skill for the dbt sales reporting pipeline — 6-task DAG producing 45+ metric types via CUBE aggregation and 2 HTML dashboards."

prompt = "Orchestrate the dbt sales reporting pipeline: seed fact_sales_daily (500k rows), run 3 dbt models (CUBE → rolling metrics → YOY/rank), generate 2 HTML reports. Uses PostgresqlExecuteSQL, DBTRunModel, and PostgresqlGenerateHtmlTableReport operators."

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Data Engineering",
    "tags": ["dbt", "postgresql", "sales", "pipeline", "reporting", "cube", "metrics", "skill"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
