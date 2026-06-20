# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 01_data_contracts  |  Flavor: KB (skills-only knowledge bundle)
# Define a data contract as a versioned config item (schema, types, nullability, freshness SLA, owner,
# semantics). The contract is the spec; enforcement (postgresql-datacontract-enforcement) turns it into checks.
payloads = {}

skills = {
    "00_datacontract_definition.md": """\
# Defining a data contract

## Lifecycle & prerequisites
**Stage:** Data Contracts (undercurrent — sits before ingestion/transformation). Knowledge bundle: the
agent reads this and creates a contract as a catalog `config` item, then wires it to producers/consumers.
Prerequisite: catalog write access. Pairs with `postgresql-datacontract-enforcement` (turns the contract
into runnable checks).

## What a data contract is
A contract-as-code agreement between a data producer and its consumers about a dataset's shape and
guarantees — so changes are explicit and breakage is caught early.

| Element | What it pins down |
|---|---|
| `dataset` | table / view / file path the contract governs + the `connection` it lives on |
| `columns` | name, type, nullable (true/false), description, and (optional) allowed values / ranges |
| `primary_key` / `unique` | key columns; uniqueness expectations |
| `freshness` | max acceptable lag (e.g. data for `{logical_date}` must exist; `max(updated_at)` within N hours) |
| `volume` | expected row-count range / non-empty |
| `owner` | team + contact (email / Slack) responsible |
| `semantics` | units, grain, currency, timezone — meaning, not just shape |
| `version` | contract version; bump on any breaking change |

## Encode it as a config item
Store the contract as a catalog `config` item so it is versioned, permissioned, and referenceable:
```
create_catalog_item(
  name="contract_fact_sales_daily",
  item_type="config",
  parent_laui="<configs folder>",
  extra_fields={
    "config_type": "task",
    "content": {
      "dataset": {"table": "fact_sales_daily", "connection_name": "postgresql"},
      "owner": {"team": "Sales Analytics", "email": "sales-data@company.com", "slack": "#sales-data"},
      "version": "1.0.0",
      "freshness": {"column": "updated_at", "max_lag_hours": 26, "must_have_date": "{logical_date}"},
      "volume": {"min_rows": 1},
      "primary_key": ["sale_id"],
      "columns": [
        {"name": "sale_id",     "type": "bigint",  "nullable": false},
        {"name": "sale_date",   "type": "date",    "nullable": false},
        {"name": "revenue",     "type": "numeric", "nullable": false, "min": 0},
        {"name": "units_sold",  "type": "integer", "nullable": false, "min": 0}
      ]
    }
  }
)
```

## How it is used
- **Producers** attach the contract to the producing task (as a `config`) and run
  `postgresql-datacontract-enforcement` as a post-action gate — a contract violation fails the task / skips
  downstream before bad data spreads.
- **Consumers** read the contract to know the schema/semantics they can rely on.
- **Change management:** edit the config → version bumps; the catalog keeps history. A breaking change is a
  visible, reviewable diff, not a silent surprise.

## Adapting
The same config shape works for any source `inspect_data` supports. Keep one contract per dataset; bump
`version` on breaking changes; reference it from both the producer's enforcement check and consumer docs.
""",
}

prompt = (
    "Knowledge bundle for defining a data contract in LeastAction as a versioned catalog config item: "
    "dataset+connection, columns (name/type/nullable/ranges), primary key, freshness SLA, volume, owner, "
    "semantics (units/grain/timezone), and version. The contract is the producer<->consumer spec; producers "
    "attach it and enforce it via postgresql-datacontract-enforcement as a post-action gate, consumers read "
    "it to know what they can rely on, and edits are versioned/reviewable in the catalog."
)

description = (
    "Data Contracts (KB): define a dataset's contract — schema, types, nullability, freshness SLA, volume, "
    "owner, semantics, version — as a versioned catalog config item. The spec that enforcement turns into "
    "checks. The agent reads this and creates the contract, then wires it to producers/consumers."
)

guide_docs = """\
# Defining Data Contracts

**Lifecycle stage:** Data Contracts. **Flavor:** skills-only knowledge bundle — the agent reads the skill
and creates a contract as a catalog `config` item; there are no tasks to deploy.

## What it teaches
A data contract is a contract-as-code agreement about a dataset's shape and guarantees: columns/types/
nullability, primary key, freshness SLA, volume, owner, semantics (units/grain/timezone), and a version.
Stored as a `config` item it becomes versioned, permissioned, and referenceable — breaking changes show
up as reviewable diffs instead of silent surprises.

## Prerequisites
- Catalog write access. Pairs with `postgresql-datacontract-enforcement` to make the contract executable.

## Using
> "use the leastaction-datacontract-definition usecase to write a contract for fact_sales_daily"

The agent creates the contract config; attach it to the producing task and gate it with
`postgresql-datacontract-enforcement`.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Data Contracts",
    "tags": ["flavor:KB", "lifecycle:data-contracts", "contract", "schema", "governance", "freshness", "owner"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
