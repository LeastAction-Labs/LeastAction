# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 01_data_contracts  |  Flavor: S+P (skills + runnable payload)
# Enforce a data contract by turning it into PostgresqlValidatorSQL checks (schema, types, nullability,
# uniqueness, volume, freshness). Run as a gate post-action so a violation fails/skip-subtrees downstream.
payloads = {
    "00_contract_check.yaml": """\
/*
{
  "name": "00_contract_check.yaml",
  "frequency": "0 7 * * *",
  "operator_name": "PostgresqlValidatorSQL",
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
# Contract enforcement for fact_sales_daily (derived from a data contract — see
# leastaction-datacontract-definition). Each check maps to one contract clause. REPLACE output_parent_laui
# with your validation-reports folder laui. Single-brace {logical_date} is templated by the operator.
report_title: 'Data Contract Enforcement — fact_sales_daily'
output_table: 'contract_reports'
output_parent_laui: 'REPLACE_WITH_CONTRACT_REPORTS_FOLDER_LAUI'

queries:
  - name: 'Schema — required columns present'
    description: 'Contract columns must exist with the expected type'
    sql: |
      SELECT COUNT(*) AS missing
      FROM (VALUES ('sale_id','bigint'),('sale_date','date'),('revenue','numeric'),('units_sold','integer')) AS c(col, typ)
      LEFT JOIN information_schema.columns ic
        ON ic.table_name='fact_sales_daily' AND ic.column_name=c.col AND ic.data_type=c.typ
      WHERE ic.column_name IS NULL
    severity: critical
    pass_condition: 'missing == 0'
    display: scalar

  - name: 'Nullability — required columns NOT NULL'
    description: 'No nulls allowed in contract NOT NULL columns for this date'
    sql: |
      SELECT COUNT(*) AS null_rows FROM fact_sales_daily
      WHERE sale_date = '{logical_date}'
        AND (sale_id IS NULL OR sale_date IS NULL OR revenue IS NULL OR units_sold IS NULL)
    severity: critical
    pass_condition: 'null_rows == 0'
    display: scalar

  - name: 'Primary key — sale_id unique'
    description: 'Contract PK must be unique (no duplicate sale_id)'
    sql: |
      SELECT sale_id, COUNT(*) AS dupes FROM fact_sales_daily
      GROUP BY sale_id HAVING COUNT(*) > 1
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Domain — revenue and units non-negative'
    description: 'Contract range: revenue >= 0 and units_sold >= 0'
    sql: |
      SELECT sale_id, revenue, units_sold FROM fact_sales_daily
      WHERE sale_date = '{logical_date}' AND (revenue < 0 OR units_sold < 0)
    severity: warning
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Volume — partition non-empty'
    description: 'Contract volume: at least 1 row for the logical_date'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily WHERE sale_date = '{logical_date}'"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Freshness — updated within SLA'
    description: 'Contract freshness: data updated within 26 hours'
    sql: |
      SELECT COUNT(*) AS stale FROM (
        SELECT MAX(updated_at) AS m FROM fact_sales_daily WHERE sale_date = '{logical_date}'
      ) t WHERE m IS NULL OR m < NOW() - INTERVAL '26 hours'
    severity: warning
    pass_condition: 'stale == 0'
    display: scalar
""",
}

skills = {
    "00_contract_check.md": """\
# Enforcing a data contract as checks

## Lifecycle & prerequisites
**Stage:** Data Contracts (enforcement). Turns the contract spec (see `leastaction-datacontract-definition`)
into runnable `PostgresqlValidatorSQL` checks. Prerequisites: operator `PostgresqlValidatorSQL` (core), a
PostgreSQL `connection`, and a catalog folder for the report (`output_parent_laui`).

## Contract clause -> check mapping
| Contract clause | Check |
|---|---|
| `columns` (name+type) | join `information_schema.columns` — count missing/mismatched (critical) |
| `nullable:false` | count NULLs in required columns for `{logical_date}` (critical) |
| `primary_key`/`unique` | GROUP BY key HAVING COUNT(*)>1 — show duplicates (critical) |
| `columns[].min/max`/allowed | range/domain check — show violating rows (warning) |
| `volume.min_rows` | row count for the partition (critical) |
| `freshness.max_lag_hours` | `MAX(updated_at)` recency (warning) |

`critical` failures should fail the gate; `warning` surfaces in the report without blocking (tune per
contract). The report shows the **actual violating rows**, so a breach is actionable, not just a boolean.

## Run it as a gate
- As a **post-action** on the producing task (run on `success`): if a critical check fails, chain
  `LeastActionSkipSubtree` + `LeastActionSlackNotify` (see `leastaction-pipelines-control`) so bad data
  never flows downstream.
- Or as a **standalone task** scheduled after the producer, with downstream tasks depending on it via
  `LeastActionCheckIfParentsAreDone`.

## Adapting
Generate the `queries` directly from a contract config's `columns`/`freshness`/`volume` (one check per
clause). Point `connection_name`/table at your dataset; replace `output_parent_laui`. This is the
executable half of `leastaction-datacontract-definition`.
""",
}

prompt = (
    "Enforce a data contract by compiling it into PostgresqlValidatorSQL checks: required columns exist with "
    "expected types (information_schema), NOT NULL columns have no nulls, primary key is unique, value "
    "ranges/domains hold, the partition is non-empty (volume), and data is fresh (max(updated_at) within "
    "SLA). Run as a post-action gate that fails/skip-subtrees downstream on a critical breach, or as a "
    "standalone validation task. The executable counterpart to leastaction-datacontract-definition."
)

description = (
    "Data Contracts (S+P): enforce a contract by turning its clauses (schema, types, nullability, key "
    "uniqueness, ranges, volume, freshness) into PostgresqlValidatorSQL checks that fail the gate and skip "
    "downstream on a critical breach — showing the actual violating rows. The runnable half of the contract."
)

guide_docs = """\
# Enforcing Data Contracts

**Lifecycle stage:** Data Contracts. **Flavor:** skills + runnable payload. Compiles a contract into
`PostgresqlValidatorSQL` checks (one per clause) and runs them as a gate.

## Step
| Step | File | Operator | What it does |
|---|---|---|---|
| 0 | `00_contract_check.yaml` | `PostgresqlValidatorSQL` | Runs schema/null/PK/range/volume/freshness checks and publishes a pass/fail report with violating rows |

## Prerequisites
- Operator `PostgresqlValidatorSQL` (core), a PostgreSQL `connection`, a folder for the report.
- A contract to enforce — see `leastaction-datacontract-definition`.

## Required edit (deploy time)
Replace `output_parent_laui` with your contract-reports folder laui; point `connection_name`/table at
your dataset; regenerate the `queries` from your contract's clauses.

## Using as a gate
Attach as a post-action on the producing task and, on a critical failure, chain `LeastActionSkipSubtree`
+ notify (see `leastaction-pipelines-control`) so a contract breach stops bad data spreading.

## Deploy
> "deploy usecase postgresql-datacontract-enforcement"
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Data Contracts",
    "tags": ["flavor:S+P", "lifecycle:data-contracts", "contract", "enforcement", "validation", "data-quality", "postgresql"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
