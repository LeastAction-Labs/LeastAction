# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = """\
# Data Contract — fact_sales_daily

## Contract summary
Enforces data quality guarantees on the `fact_sales_daily` table before downstream
dbt models consume it. Run after Task 00 (seed) succeeds.

## Contract clauses

| Clause | Check | Severity |
|--------|-------|----------|
| Schema — required columns | `sale_id`, `sale_date`, `revenue`, `units_sold`, `cost`, `product_id`, `category_id`, `region_id`, `store_id` exist with expected types | critical |
| Primary key — `sale_id` unique | No duplicate `sale_id` values | critical |
| Nullability — NOT NULL columns | `sale_date`, `revenue`, `units_sold`, `cost`, `product_id`, `category_id`, `region_id`, `store_id` have no NULLs | critical |
| Domain — revenue non-negative | `revenue >= 0` for all rows | warning |
| Domain — units_sold positive | `units_sold > 0` for all rows | warning |
| Domain — cost non-negative | `cost >= 0` for all rows | warning |
| Volume — partition non-empty | At least 1 row exists | critical |
| Volume — expected row count | At least 100,000 rows (synthetic data has 500,000) | warning |
| Referential — valid categories | All `category_name` values are in the expected set (Electronics, Peripherals, Audio, Lighting, Furniture) | warning |
| Referential — valid regions | All `region_name` values are in the expected set (North America, Europe, Asia Pacific, Latin America, Middle East) | warning |

## PostgresqlValidatorSQL payload

```yaml
report_title: 'Data Contract — fact_sales_daily'
output_table: 'sales_contract_reports'

queries:
  - name: 'Schema — required columns present'
    description: 'Contract columns must exist with expected types'
    sql: |
      SELECT COUNT(*) AS missing
      FROM (VALUES
        ('sale_id','bigint'),('sale_date','date'),('revenue','numeric'),
        ('units_sold','integer'),('cost','numeric'),('product_id','character varying'),
        ('category_id','character varying'),('region_id','character varying'),
        ('store_id','character varying')
      ) AS c(col, typ)
      LEFT JOIN information_schema.columns ic
        ON ic.table_name='fact_sales_daily' AND ic.column_name=c.col AND ic.data_type=c.typ
      WHERE ic.column_name IS NULL
    severity: critical
    pass_condition: 'missing == 0'
    display: scalar

  - name: 'Primary key — sale_id unique'
    description: 'No duplicate sale_id values'
    sql: |
      SELECT sale_id, COUNT(*) AS dupes FROM fact_sales_daily
      GROUP BY sale_id HAVING COUNT(*) > 1
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Nullability — required columns NOT NULL'
    description: 'No NULLs in contract NOT NULL columns'
    sql: |
      SELECT COUNT(*) AS null_rows FROM fact_sales_daily
      WHERE sale_date IS NULL OR revenue IS NULL OR units_sold IS NULL
        OR cost IS NULL OR product_id IS NULL OR category_id IS NULL
        OR region_id IS NULL OR store_id IS NULL
    severity: critical
    pass_condition: 'null_rows == 0'
    display: scalar

  - name: 'Domain — revenue non-negative'
    description: 'Contract range: revenue >= 0'
    sql: "SELECT COUNT(*) AS negative_count FROM fact_sales_daily WHERE revenue < 0"
    severity: warning
    pass_condition: 'negative_count == 0'
    display: scalar

  - name: 'Domain — units_sold positive'
    description: 'Contract range: units_sold > 0'
    sql: "SELECT COUNT(*) AS invalid_count FROM fact_sales_daily WHERE units_sold <= 0"
    severity: warning
    pass_condition: 'invalid_count == 0'
    display: scalar

  - name: 'Volume — partition non-empty'
    description: 'At least 1 row exists'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Volume — expected row count'
    description: 'At least 100,000 rows expected (synthetic = 500k)'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily"
    severity: warning
    pass_condition: 'row_count >= 100000'
    display: scalar

  - name: 'Referential — valid categories'
    description: 'Only 5 allowed categories'
    sql: |
      SELECT DISTINCT category_name FROM fact_sales_daily
      WHERE category_name NOT IN ('Electronics','Peripherals','Audio','Lighting','Furniture')
    severity: warning
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Referential — valid regions'
    description: 'Only 5 allowed regions'
    sql: |
      SELECT DISTINCT region_name FROM fact_sales_daily
      WHERE region_name NOT IN ('North America','Europe','Asia Pacific','Latin America','Middle East')
    severity: warning
    pass_condition: 'row_count == 0'
    display: table
```

## How to use
- **As a standalone task:** Create a task with operator `PostgresqlValidatorSQL`, connection
  `dbt_postgresql`, and the YAML payload above. Add `LeastActionCheckIfParentsAreDone`
  pointing to `00_fact_sales_daily`.
- **As a gate:** Attach as a post-action on `00_fact_sales_daily`. If a critical check fails, chain
  `LeastActionSkipSubtree` to prevent bad data from flowing into the dbt models.
- **In the seeded pipeline** this runs as task `00b_sales_contract` (a subset — schema, PK, nullability,
  revenue domain, volume). The full clause set above is the target contract.

## Connection
Uses `dbt_postgresql` (same as the seed and report tasks).
"""

description = "Data contract enforcement for fact_sales_daily — schema, PK, nullability, domain, volume, and referential integrity checks via PostgresqlValidatorSQL."

prompt = "Enforce the data contract on fact_sales_daily: verify schema columns and types, primary key uniqueness, NOT NULL constraints, revenue/units/cost domain ranges, row volume, and referential integrity of categories and regions."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Data Contracts",
    "tags": ["dbt", "postgresql", "sales", "data-contract", "validation", "fact_sales_daily"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
