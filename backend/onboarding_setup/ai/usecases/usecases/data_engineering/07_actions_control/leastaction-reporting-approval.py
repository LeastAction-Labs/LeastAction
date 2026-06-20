# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 07_actions_control  |  Flavor: KB (skills-only knowledge bundle)
# Report approval + email distribution via the ApproveAndSendReport UI action: manual review path and
# auto-approval postAction path; keeps a permanent archive and a single latest in the catalog.
payloads = {}

skills = {
    "00_report_approval.md": """\
# Report approval & email workflow

## Lifecycle & prerequisites
**Stage:** Actions & Control (approval/distribution). Knowledge bundle. Prerequisites:
- The `ApproveAndSendReport` action (ships in bootstrap).
- An SMTP `connection` (see fields below) attached to the action.
- The dev/business folder structure (see the `leastaction-reporting-distribution` usecase).
- A reporting pipeline that writes `html_report` items to the catalog.

## Two paths
- **Auto-approved:** the reporting task adds `ApproveAndSendReport` as a `post_actions` entry — fires on
  success, emails + archives + publishes automatically. For operational reports (daily sales, hourly).
- **Requires approval:** the task writes the report to `dev/pending-approval/<dept>/` and a notify
  postAction pings the reviewer; the analyst opens it in the catalog, selects it, and triggers
  `ApproveAndSendReport` from the UI. For sensitive reports (finance close, executive).

## The ApproveAndSendReport action
Operates on one or more selected `html_report` items. For each it: reads recipient/subject/date metadata
→ emails the HTML to all recipients → creates `business/<dept>/archive/<yyyy>/<mm>/<dd>/` and copies the
report there → replaces the single latest in `business/<dept>/` → deletes the source from
`dev/pending-approval/<dept>/`.

### Fields the report item must carry (set by the pipeline at create time)
| Field | Purpose |
|---|---|
| `html` | Full HTML to send + display |
| `recipients` | List of email addresses |
| `subject` | Email subject |
| `report_date` | `yyyy-mm-dd` — builds the archive path |
| `description` | Optional — carried to the archived copy |

### Action variables
| Variable | Notes |
|---|---|
| `item_lauis` | Array of report laui(s) — **auto-filled from table selection** |
| `business_latest_folder_laui` | Folder that always holds the single latest published report |
| `archive_base_folder_laui` | Base archive folder — `yyyy/mm/dd` created automatically |

Set `business_latest_folder_laui` and `archive_base_folder_laui` as folder-config defaults on the
`dev/pending-approval/<dept>/` folder so they pre-fill for anyone who triggers the action there.

## SMTP connection
```json
{ "smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "reports@yourcompany.com",
  "smtp_password": "your_smtp_password", "smtp_use_tls": true, "from_email": "reports@yourcompany.com" }
```
SMTP creds come from the connection attached to the action — never from the report item.

## Adapting
`ApproveAndSendReport` is one example of a select-items → trigger-action → run-logic UI pattern: bulk
archive, re-run failed reports, export to an external system, annotate items with quality scores.
""",
}

prompt = (
    "Knowledge bundle for a structured report approval + email distribution workflow using the "
    "ApproveAndSendReport UI action. Two paths: auto-approval (ApproveAndSendReport as a post_action that "
    "emails+archives+publishes on success) and manual review (report lands in dev/pending-approval/<dept>/, "
    "a notify postAction pings the analyst, who selects it in the catalog table and triggers "
    "ApproveAndSendReport — item_lauis auto-filled). The action reads html/recipients/subject/report_date "
    "from each report item, emails via an SMTP connection, archives to business/<dept>/archive/yyyy/mm/dd/, "
    "and replaces the single latest in business/<dept>/. Pairs with the reporting-distribution folder structure."
)

description = (
    "Actions & Control (KB): report approval + email distribution via ApproveAndSendReport — manual review "
    "and auto-approval paths, with permanent archive and a single always-current latest in the catalog. "
    "The agent reads this and wires the action (post_action for auto, UI action for manual review)."
)

guide_docs = """\
# Report Approval & Email Workflow

**Lifecycle stage:** Actions & Control. **Flavor:** skills-only knowledge bundle — the agent reads the
skill and wires `ApproveAndSendReport` (as a postAction for auto-approval, or a UI action for review).

## What it teaches
Sending a report is easy; knowing what was sent, to whom, and whether it was reviewed is the hard part.
`ApproveAndSendReport` reads recipient/date metadata off each `html_report`, emails it, archives a dated
copy, and keeps one always-current latest in `business/<dept>/`. Two paths: auto (postAction) and manual
(review in `dev/pending-approval/`, then trigger from the UI — `item_lauis` auto-fills).

## Prerequisites
- `ApproveAndSendReport` action (bootstrap) + an SMTP connection.
- The dev/business folder structure — see `leastaction-reporting-distribution`.
- A pipeline that writes `html_report` items with `html`, `recipients`, `subject`, `report_date`.

## Using
> "use the leastaction-reporting-approval usecase to auto-send the daily sales report and archive it"

The agent adds `ApproveAndSendReport` as a post_action with the latest/archive folder lauis. For the
folder layout and access control, deploy/read `leastaction-reporting-distribution` first.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Actions & Control",
    "tags": ["flavor:KB", "lifecycle:actions-control", "approval", "email", "smtp", "report", "distribution", "html_report"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
