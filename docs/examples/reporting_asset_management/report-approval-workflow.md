# Report Approval and Email Workflow

Sending a report is easy. Knowing *what* was sent, *to whom*, and *whether it was reviewed before it went out* — that is harder. This example shows how to build a structured report distribution workflow in LeastAction that keeps a permanent record, enforces review where needed, and handles both manual and automatic approval paths.

This builds on the folder structure described in [Organizing Reports in LeastAction](/path?laui=getting-started-examples-reporting_asset_management-reports-organizing&itemtype=doc.file&itemname=Reports%20Organizing). Read that first if you haven't.

---

## What This Workflow Does

Every report takes one of two paths:

```
Pipeline runs → report generated
        │
        ├── Auto-approved ──────────────────────────────────────────────────────→
        │   postAction writes report to dev/ and fires ApproveAndSendReport      │
        │   Email sent + archive updated automatically                            ↓
        │                                                              report published
        └── Requires approval ─────────────────────────────────────────────────→
            postAction writes to dev/pending-approval/finance/                   │
            Analyst receives notification                                         │
            Analyst opens LeastAction catalog, selects the report                │
            Analyst triggers ApproveAndSendReport                                │
            Email sent + archived + latest in business/ updated                  ↓
                                                                        report published
```

The path a report takes is determined by the task or its postAction. Sensitive reports — finance close, executive summaries, preliminary figures — go through manual review. Operational reports — daily sales, hourly dashboards — are auto-approved.

---

## What You Need

### Folder structure in the LeastAction catalog

Two root folders — `dev/` and `business/` — with department subfolders under each. The `dev/pending-approval/` tree is where reports land before review. The `business/` tree is what gets published. See [Organizing Reports](/path?laui=getting-started-examples-reporting_asset_management-reports-organizing&itemtype=doc.file&itemname=Reports%20Organizing) for the full structure and access control setup.

### The `ApproveAndSendReport` action

A UI action that reads recipient metadata from each selected report, sends email, archives, and publishes. A ready-to-use implementation ships with LeastAction bootstrap under `ApproveAndSendReport/`.

### An SMTP connection

A connection in the LeastAction catalog with these fields:

```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "reports@yourcompany.com",
  "smtp_password": "your_smtp_password",
  "smtp_use_tls": true,
  "from_email": "reports@yourcompany.com"
}
```

### A reporting pipeline

Any pipeline that generates HTML reports and saves them to the LeastAction catalog as `html_report` items. See the [PostgreSQL Sales Reporting example](/path?laui=getting-started-examples-postgres_sales_reporting-postgres-sales-reporting&itemtype=doc.file&itemname=Postgres%20Sales%20Reporting) for a complete example.

---

## The ApproveAndSendReport Action

`ApproveAndSendReport` is a UI action that operates on one or more `html_report` items selected from the catalog table. When triggered, it processes each selected item and:

1. Reads recipient, subject, and date metadata stored on the report item
2. Sends the HTML content as an email to every recipient
3. Creates `business/<department>/archive/<yyyy>/<mm>/<dd>/` folders if they don't exist, then copies the report there
4. Replaces the latest item in `business/<department>/` (deletes the old one, publishes the new)
5. Deletes the source item from `dev/pending-approval/<department>/`

One action, triggered once, handles the entire publication flow — email, archive, and catalog update.

### What the action reads from each report

These fields must be present in the `html_report` item when it is created by the pipeline:

| Field | Description |
|-------|-------------|
| `html` | The full HTML content to send and display |
| `recipients` | List of email addresses to send to |
| `subject` | Email subject line |
| `report_date` | `yyyy-mm-dd` — used to build the archive path |
| `description` | Optional — carried to the archived copy |

The pipeline sets these when creating the item. The action just reads and acts. SMTP credentials come from the connection attached to the action — not from the report.

### Action variables

`ApproveAndSendReport` takes three variables:

| Variable | Description |
|----------|-------------|
| `item_lauis` | Array of report laui(s) to approve — **auto-filled from table selection** |
| `business_latest_folder_laui` | The folder that always holds the single latest published report |
| `archive_base_folder_laui` | The base archive folder — `yyyy/mm/dd` subfolders are created automatically |

Set `business_latest_folder_laui` and `archive_base_folder_laui` as folder config defaults on your `dev/pending-approval/<department>/` folder. Anyone who triggers the action from that folder gets these pre-filled. `item_lauis` fills automatically from whichever items are selected in the table — no manual entry needed.

---

## Manual Approval Path — Step by Step

### 1. Pipeline generates the report

The reporting task generates the HTML and saves it to `dev/pending-approval/finance/` via the catalog API. The item must carry the recipient and date fields that the action will read:

```json
{
  "item_type": "html_report",
  "name": "Finance Close Report — March 2026",
  "html": "<html>...</html>",
  "recipients": ["cfo@company.com", "finance-team@company.com"],
  "subject": "Finance Close Report — March 2026",
  "report_date": "2026-03-07",
  "description": "Monthly finance close — March 2026",
  "parent_laui": "<laui of dev/pending-approval/finance/>"
}
```

### 2. Analyst is notified

A postAction on the reporting task sends a notification — Slack, email, or SNS — to the analyst responsible for that report. The notification includes a direct link to the report in the LeastAction catalog.

The analyst receives a link, clicks it, and lands on the report item in the pending-approval folder.

### 3. Analyst reviews

The analyst opens the report item. The full HTML renders inline. They review figures, formatting, and content.

If changes are needed, they flag it back to the data team. The pipeline re-runs, a new version lands in the pending folder, and the process repeats. The archive only lives in `business/` — `dev/` is just a staging area.

### 4. Analyst approves and sends

When the report is ready, the analyst selects it in the catalog table (or selects multiple pending reports at once) and triggers `ApproveAndSendReport`. The `item_lauis` field is auto-filled from the selection. The action:

- Sends the email to every address in the recipient list
- Creates `business/finance/archive/2026/03/07/` if it doesn't exist and archives a copy there
- Publishes this report as the new latest in `business/finance/` (replacing the previous one)
- Deletes the item from `dev/pending-approval/finance/`

The analyst sees a success confirmation. The CFO receives the email within seconds. The catalog now shows the published report as the current item in `business/finance/`.

---

## Auto-Approval Path — Step by Step

For operational reports that do not require review, the pipeline skips `dev/pending-approval/` entirely.

### 1. Pipeline generates the report

Same generation step. The task creates the `html_report` item with the same recipient/date fields.

### 2. postAction runs ApproveAndSendReport automatically

Add `ApproveAndSendReport` as a postAction on the reporting task. It fires automatically when the task completes successfully. The `item_lauis` is set to the laui of the report item the task just created:

```json
{
  "actions": {
    "post_actions": [
      {
        "action": "ApproveAndSendReport",
        "variables": {
          "item_lauis": ["{{output_item_laui}}"],
          "business_latest_folder_laui": "<laui of business/sales/>",
          "archive_base_folder_laui": "<laui of business/sales/archive/>"
        }
      }
    ]
  }
}
```

No human step. The report is generated, sent, and archived automatically.

---

## Keeping the Catalog Clean

The `business/<department>/` folder holds exactly one item at all times — the latest published report. `ApproveAndSendReport` manages this: it deletes the existing `html_report` in that folder before publishing the new one.

The archive tree (`archive/yyyy/mm/dd/`) grows over time but never needs manual maintenance. Every approved report is preserved. Retention policies can be added as a scheduled action that prunes entries older than a configurable window.

The `dev/pending-approval/` folders should stay lean — ideally one item per department at a time. If a new report is generated before the previous one is approved, the postAction can replace the pending item or add alongside it, depending on your workflow.

---

## This Is Just an Example

`ApproveAndSendReport` is one example of what a UI action can do. The same pattern — select items from a catalog table, trigger an action, run arbitrary logic — applies to any workflow: bulk archiving, re-running failed reports, exporting items to an external system, triggering downstream pipelines, annotating catalog items with quality scores. What the action does is entirely up to you.

---

## The Full Picture

```
Data pipeline runs (hourly / daily / on trigger)
        │
        ▼
PostgresqlGenerateHtmlTableReport (or equivalent)
        │
        ├── creates html_report in dev/pending-approval/finance/
        │   with fields: html, recipients, subject, report_date
        │
        └── postAction: NotifyReviewer → Slack/email to analyst

Analyst opens LeastAction catalog → dev/pending-approval/finance/
        │
        └── Selects report(s) in table → triggers ApproveAndSendReport
                │
                ├── Email sent to recipients
                ├── archive/yyyy/mm/dd/ created if needed
                ├── Report copied to archive/yyyy/mm/dd/
                ├── Latest replaced in business/finance/
                └── Pending item deleted

Finance lead opens LeastAction catalog → business/finance/
        └── Sees latest report (1 item, always current)
        └── Navigates to business/finance/archive/ for history
```
