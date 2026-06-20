# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 08_distribution  |  Flavor: KB (skills-only knowledge bundle)
# Organize reports as catalog assets: dev/ (staging + pending-approval) vs business/ (latest + dated
# archive), per-department access control. The serving/distribution layer the approval workflow publishes into.
payloads = {}

skills = {
    "00_report_organization.md": """\
# Organizing reports in the catalog

## Lifecycle & prerequisites
**Stage:** Distribution / serving. Knowledge bundle — the agent reads this and creates the folder
structure + permissions, then points pipelines at it. Prerequisite: catalog write access; reports are
`html_report` items created by pipelines (e.g. `PostgresqlGenerateHtmlTableReport`) via the catalog API.

## The folder structure
```
catalog/
├── dev/
│   ├── pending-approval/{finance,sales,marketing,product}/   <- generated, not yet reviewed
│   └── drafts/                                                <- operator output during development
└── business/
    └── {finance,sales,marketing,product}/
        ├── (html_report)        <- the single latest published report (always one item)
        └── archive/YYYY/MM/DD/(html_report)   <- every prior version, nothing deleted
```

- **dev/** — pipeline output lands here first; analysts review here; nothing here is "published".
  `pending-approval/<dept>/` holds reports awaiting human sign-off. Access: data team only.
- **business/** — what stakeholders see. Each department folder holds ONE latest item plus a
  date-partitioned `archive/`. Access: granted per department (finance leads see `business/finance/` only).

## How reports get in
Pipelines write to `dev/pending-approval/<dept>/` (NOT directly to `business/`). The move to `business/`
happens on approval (or automatically if pre-approved) via `ApproveAndSendReport` — see the
`leastaction-reporting-approval` usecase. Any operator/action that calls catalog-create with
`item_type:"html_report"` can publish.

## Access control
Set folder permissions in the catalog: `dev/` data-team only; `business/<dept>/` = that department +
data team. The item-based permission system enforces it — a finance analyst sees `business/finance/`,
never `dev/` or other departments. See the access docs.

## What business users see
Open `business/finance/` → one item: the current report, full HTML inline (no download). Navigate
`archive/YYYY/MM/` → every report published that month, one per date. "What did we send on the 6th?" is
one click.

## Creating it
Build the tree once (UI or a setup action calling catalog-create with `item_type:"folder"`). To add a
department: create `business/<dept>/` + its `archive/`, create `dev/pending-approval/<dept>/`, set
permissions on `business/<dept>/`, and point that department's pipeline output at the pending folder.
""",
}

prompt = (
    "Knowledge bundle for organizing reports as catalog assets. A dev/ tree (pending-approval/<dept> + "
    "drafts) for unpublished output, restricted to the data team; and a business/ tree where each "
    "department folder holds a single always-current latest html_report plus a date-partitioned archive/, "
    "with per-department access control. Pipelines write html_report items to dev/pending-approval/<dept>/; "
    "the move to business/ happens via ApproveAndSendReport. Teaches the folder structure, access control, "
    "how reports enter the catalog, and how to create/extend the structure."
)

description = (
    "Distribution (KB): organize reports in the catalog — dev/ (staging + pending-approval, data-team only) "
    "vs business/ (single latest + dated archive, per-department access). The serving layer the approval "
    "workflow publishes into. The agent reads this and creates the folders + permissions."
)

guide_docs = """\
# Organizing & Distributing Reports

**Lifecycle stage:** Distribution / serving. **Flavor:** skills-only knowledge bundle — the agent reads
the skill and builds the folder structure + permissions; there are no tasks to deploy.

## What it teaches
The problem isn't generating reports — it's organization: what was sent, to whom, when. The catalog
solves it: `dev/` (staging + `pending-approval/<dept>/`, data-team only) and `business/<dept>/` (one
always-current latest + a dated `archive/`, granted per department). Pipelines write to
`dev/pending-approval/<dept>/`; publication to `business/` happens via `ApproveAndSendReport`.

## Prerequisites
- Catalog write access; the per-folder access/permission model; a reporting pipeline producing
  `html_report` items.

## Using
> "use the leastaction-reporting-distribution usecase to set up finance + sales report folders with access control"

The agent creates the dev/business tree and sets per-department permissions. Pair with
`leastaction-reporting-approval` for the publish/email step.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Distribution",
    "tags": ["flavor:KB", "lifecycle:distribution", "reporting", "catalog", "assets", "access-control", "archive"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
