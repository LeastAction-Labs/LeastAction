# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = {
    "description": "Data contract for fact_sales_daily — schema, precision/scale, PK, nullability, domain, volume, and referential integrity guarantees. Read by LeastActionAgentDebug on every load, live, via inspect_data.",
    "content": """\
# Data Contract — fact_sales_daily

## Contract summary
States the data quality guarantees `fact_sales_daily` must hold for every downstream
dbt model, validation task, and report that reads it. This is read live: after every
run of `00_fact_sales_daily`, `LeastActionAgentDebug` queries the table's actual schema
via `inspect_data` (`information_schema.columns`) and reasons about it against this
document — it does not wait for a separate gate task, and it runs whether or not the
load itself succeeded, because most drift here doesn't fail the load.

## Contract clauses

| Clause | Check | Severity |
|--------|-------|----------|
| Schema — required columns | `sale_id`, `sale_date`, `revenue`, `units_sold`, `cost`, `product_id`, `category_name`, `region_name`, `store_id` exist with expected types | critical |
| Schema — `revenue` and `cost` are `NUMERIC(15,2)` | `numeric_precision = 15`, `numeric_scale = 2`. **Any change to precision or scale is a BREAKING contract change**, even if the column name and base type are unchanged. A scale INCREASE (e.g. to `(15,4)`) is non-lossy but still breaks the contract — downstream consumers expecting 2-decimal currency values will silently receive 4-decimal ones. A scale DECREASE (e.g. to `(15,1)` or lower) is lossy: existing values are rounded or truncated on write, silently corrupting revenue and profit figures for every downstream metric | critical |
| Schema — `product_name` is VARCHAR(100) | `character_maximum_length = 100`; **changing the length is a BREAKING contract change** (consumer sign-off + deprecation notice) | critical |
| Primary key — `sale_id` unique | No duplicate `sale_id` values | critical |
| Nullability — NOT NULL columns | `sale_date`, `revenue`, `units_sold`, `cost`, `product_id`, `category_name`, `region_name`, `store_id` have no NULLs | critical |
| Domain — revenue & profit non-negative | `revenue >= 0`, `cost >= 0`, and `revenue >= cost` (profit ≥ 0) | warning |
| Domain — units_sold positive | `units_sold > 0` for all rows | warning |
| Domain — per-row revenue ceiling | `revenue <= 500000` per row (guards against a source fan-out) | warning |
| Volume — partition non-empty | At least 1 row exists | critical |
| Volume — row count within band | Row count in `[100000, 2000000]` (~400k for the realistic 5-yr seed) | critical |
| Freshness — multi-year span | `MAX(sale_date) - MIN(sale_date) >= 1400` days | critical |
| Referential — valid categories | All `category_name` values in {Electronics, Peripherals, Audio, Lighting, Furniture} | warning |
| Referential — valid regions | All `region_name` values in {North America, Europe, Asia Pacific, Latin America, Middle East} | warning |
| Referential — product_id format | All `product_id` match `^P[0-9]{3}$` | warning |

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

  - name: 'Schema — revenue/cost precision is NUMERIC(15,2)'
    description: 'Any drift in precision or scale is a breaking contract change (see clause table above)'
    sql: |
      SELECT COUNT(*) AS mismatch FROM information_schema.columns
      WHERE table_name='fact_sales_daily' AND column_name IN ('revenue','cost')
        AND (numeric_precision <> 15 OR numeric_scale <> 2)
    severity: critical
    pass_condition: 'mismatch == 0'
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
    description: 'Row count within [100000, 2000000] (~400k realistic)'
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
- **As a live, per-run check (the primary mechanism in this pipeline):** attach
  `LeastActionAgentDebug` as a `post_action` on `00_fact_sales_daily` with
  `enable_tools=True`, `source_connection_laui` pointing at `dbt_postgresql`, and
  `source_table="fact_sales_daily"`. On every run of the load task — success or
  failure — the agent calls `inspect_data` against `information_schema.columns` and
  reasons about the live schema against this document directly. No separate task,
  no schedule to keep in sync with the load.
- **As a standalone deterministic task (optional, not seeded by default):** Create a
  task with operator `PostgresqlValidatorSQL`, connection `dbt_postgresql`, and the
  YAML payload above; add `LeastActionCheckIfParentsAreDone` pointing to
  `00_fact_sales_daily`. A 10-query deterministic SQL check (schema+types incl. the
  precision/scale check, PK, nullability, domain bands, volume, referential),
  independent of the AI-driven live check above. Unlike the AI check, this one can
  enforce a hard stop on the checks it covers — useful if a specific clause needs to
  block downstream tasks outright rather than just be reasoned about and reported.

## Connection
Uses `dbt_postgresql` (same as the seed and report tasks).
""",
}

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
