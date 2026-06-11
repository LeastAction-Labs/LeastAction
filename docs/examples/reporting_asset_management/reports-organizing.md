# Organizing Reports in LeastAction

Most teams already generate reports automatically — SQL jobs, Python scripts, BI tool exports. The problem is not generation. It is organization: knowing what was sent, to whom, when, and why. When a stakeholder asks "what did we send finance last month?" the answer should not require searching inboxes.

LeastAction's catalog solves this. Because every report is a first-class item in a folder hierarchy, your report library is browsable, searchable, permissioned, and persistent — the same system that runs your pipelines also holds every report they produce.

---

## The Folder Structure

A well-organized reporting catalog separates work-in-progress from published output, and organizes published output by department and time.

```
catalog/
├── dev/
│   ├── pending-approval/
│   │   ├── finance/          ← reports generated but not yet reviewed
│   │   ├── sales/
│   │   ├── marketing/
│   │   └── product/
│   └── drafts/               ← operator output during development
│
└── business/
    ├── finance/
    │   ├── (html_report)     ← latest published report — always one item
    │   └── archive/
    │       └── 2026/
    │           └── 03/
    │               └── 06/
    │                   └── (html_report)   ← historical copy
    ├── sales/
    │   ├── (html_report)
    │   └── archive/ ...
    ├── marketing/
    │   ├── (html_report)
    │   └── archive/ ...
    └── product/
        ├── (html_report)
        ├── archive/ ...
        └── sub-products/
            ├── (html_report)
            └── archive/ ...
```

### The dev folder

The `dev` folder is where pipeline output lands first. Jobs write reports here. Analysts review them here. Nothing in `dev` is considered published.

The `pending-approval` subfolder holds reports that require a human sign-off before distribution. Each department has its own subfolder so reviewers can filter to their area without seeing everything.

Access to `dev` is restricted to the team that operates the pipelines — analysts, data engineers, and admins. Business stakeholders do not have visibility into `dev`.

### The business folder

The `business` folder is what external stakeholders and department leads see. Each department has a folder. Inside it:

- **The latest report** — a single `html_report` item representing the current published version. This is what a finance director sees when they open the finance folder. One item, always current.
- **The archive** — a date-partitioned folder tree (`archive/2026/03/06/`) holding every previously published version. Nothing is deleted. Any historical report is one click away.

Access to `business` can be granted per department. Finance leads get access to `business/finance/` only. Sales leads get `business/sales/` only. No one outside the data team ever sees `dev`.

---

## How Reports Get Into the Catalog

Reports are written to the catalog by the pipeline that generates them. The `PostgresqlGenerateHtmlTableReport` operator (covered in the [PostgreSQL Sales Reporting example](/path?laui=getting-started-examples-postgres_sales_reporting-postgres-sales-reporting&itemtype=doc.file&itemname=Postgres%20Sales%20Reporting)) saves output directly to a catalog folder via the catalog API. Any operator or action that calls `/api/v1/catalog/create` with `item_type: "html_report"` does the same.

For the organizing pattern to work, the pipeline writes to `dev/pending-approval/<department>/` — not directly to `business/`. The move to `business/` only happens after approval (or automatically if the report is pre-approved).

---

## Access Control

Folder permissions are set in the LeastAction catalog. An admin configures:

- `dev/` — accessible to data team only
- `business/finance/` — accessible to finance team + data team
- `business/sales/` — accessible to sales team + data team
- `business/marketing/` — accessible to marketing team + data team
- `business/product/` — accessible to product team + data team

When a finance analyst logs into LeastAction, they see `business/finance/` in their catalog. They do not see `dev/`. They cannot browse reports that are not yet published. They cannot see other departments' folders.

This is enforced by the catalog's item-based permission system. See the [access documentation](/path?laui=getting-started-advanced-UI_management-access&itemtype=doc.file&itemname=Access) for how to configure permissions per folder.

---

## What Business Users See

When a business user opens `business/finance/`, they see one item: the latest published Finance report. Clicking it opens the full HTML report inline — no download, no email attachment to hunt for.

To see historical reports, they navigate into `archive/2026/03/` and see every Finance report published that month, one per date folder. Every report that was ever sent is here. The question "what did we send on the 6th?" has a one-click answer.

---

## Creating This Structure

Set up the folder tree manually in the LeastAction catalog UI, or automate it with a setup action that calls `/api/v1/catalog/create` with `item_type: "folder"` for each node. The folder structure only needs to be created once.

When adding a new department or sub-product reporting area:
1. Create the department folder inside `business/`
2. Create the `archive/` subfolder inside it
3. Create the matching folder inside `dev/pending-approval/`
4. Set permissions on the new `business/<department>/` folder

The pipeline for that department points its output to `dev/pending-approval/<department>/`. Everything else follows automatically.

---

