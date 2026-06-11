# LeastAction Asset — Feature Guide

LeastAction is not just a workflow orchestrator. It is also a content management system. Every item in LeastAction — operators, connections, configs, actions, tasks, workflows — lives in a folder hierarchy stored in MongoDB. That same hierarchy is open for you to use as a catalog for any content your team produces: reports, tables, datasets, documentation, or any structured metadata you want to manage, version, and share.

---

## The Catalog as a Content Management System

The LeastAction catalog is a tree of folders and items. Folders can contain other folders or items, and each item has a type. Types determine what fields an item can hold, what it can be nested inside, and what actions are available on it.

```
catalog root
├── folder (workflow)
│   ├── task
│   ├── task
│   └── ...
├── folder (operator)
│   ├── operator
│   └── ...
├── folder (asset)            ← your content lives here
│   ├── folder (report)
│   │   ├── html_report
│   │   ├── powerbi_report
│   │   ├── looker_report
│   │   ├── quicksight_report
│   │   └── tableau_report
│   ├── folder (table)
│   │   └── table
│   └── ...
```

An asset folder is a section of the catalog you control. You can nest folders inside it to organize content any way you like — by team, project, domain, or data source. Items inside hold whatever metadata you want to store in MongoDB: structured fields, HTML content, schema definitions, dates, tags.

---

## Item Types

Item types are defined in two places:

- `config/schema/` — one JSON schema file per item type, defining the fields the item holds
- `config/catalog.json` — defines which folders can contain which item types

Adding a new asset type is two files: a schema definition and an entry in catalog.json. No code changes to the platform are required.

### Launched asset types

| Type | Description |
|------|-------------|
| `html_report` | AI-generated HTML report, written by a task and stored in the catalog |
| `powerbi_report` | Live Power BI dashboard, embedded via a short-lived token — credentials stay on the backend |
| `looker_report` | Live Looker Enterprise dashboard, embedded via a signed one-time URL — `embed_secret` stays on the backend |
| `looker_studio_report` | Live Looker Studio (Google Data Studio) report — no backend credentials needed; access controlled by Google account in the browser |
| `quicksight_report` | Live QuickSight dashboard, embedded via the QuickSight embed API — supports EC2 instance profile (no keys in catalog) |
| `tableau_report` | Live Tableau dashboard, embedded via a Connected App JWT — no extra Python library required |
| `table` | A reference to an RDBMS table, registered in the catalog after a task runs |

---

## html_report: AI-Generated Reports

The `html_report` asset is created by the `PostgresqlToClaudeChatToHtmlReportToAsset` action. This is a UI action — it runs interactively when a user triggers it from a folder in the catalog.

### What it does

1. Connects to a PostgreSQL database using connection credentials
2. Reads the schema and a sample of rows from a source table
3. Sends the schema, sample data, and your prompt to Claude
4. Claude generates a SQL query to answer the question
5. LeastAction executes the SQL against the database
6. Results are sent to Claude, which generates a complete HTML report
7. The HTML report is saved as an `html_report` item in the catalog under the folder you ran it from

### How to use it

1. Navigate to an asset folder in the catalog
2. Run the `PostgresqlToClaudeChatToHtmlReportToAsset` UI action on the folder
3. Provide:
   - **Source table name** — the table to query
   - **Prompt** — a natural language description of the report you want (e.g., "Show monthly revenue by region for the last 12 months")
4. The action connects to your database, generates SQL via Claude, runs the query, and writes the HTML report back to the catalog

### Connection requirements

The connection used must include:

- Standard PostgreSQL fields: `host`, `port`, `database`, `username`, `password`
- Claude API fields: `claude_api_key`, `claude_model`, `claude_token_limit`

### Result

The report is saved as an `html_report` item named after your prompt (truncated to 100 characters). It is immediately viewable in the catalog and accessible to anyone with permission to the folder.

---

## BI Embed Reports

Five report types surface live BI dashboards in the Report Explorer without moving data or rebuilding dashboards in LeastAction. There are two distinct embed models depending on the tool.

---

### Model A — Backend credential exchange (Power BI, Looker Enterprise, QuickSight, Tableau)

The backend holds all credentials. When a user opens the report, the backend exchanges those credentials for a short-lived embed URL. Credentials never reach the browser.

```
User opens report
       ↓
Frontend calls POST /api/v1/embed/token { item_laui }
       ↓
Backend fetches report item → reads connection_laui
       ↓
Backend fetches connection content (server-side only)
       ↓
Backend calls BI API → gets short-lived embed URL (5–600 min)
       ↓
Returns { embed_url, expires_in } — no credentials in response
       ↓
Frontend renders <iframe src={embed_url} />
Frontend refreshes token automatically before expiry
```

**Auth: prefer keyless where possible**

| Report type | Connection type | Recommended auth |
|---|---|---|
| `powerbi_report` | `connection.azure` | `use_managed_identity: true` (Azure Managed Identity) |
| `looker_report` | `connection.gcp` | `embed_secret` field — symmetric, server-side only |
| `quicksight_report` | `connection.AWSIAMRole` | EC2 instance profile — no keys in catalog |
| `tableau_report` | `connection.tableau` | Connected App JWT — `client_id`, `secret_id`, `secret_value` |

Explicit key fallbacks (`client_secret` for Power BI, `aws_access_key_id`/`aws_secret_access_key` for QuickSight) are supported but not recommended.

**Token lifetimes**

| Tool | Session lifetime | Frontend refresh before |
|---|---|---|
| Power BI | 10 min | 9 min |
| Looker Enterprise | 5 min (one-time use) | 4.5 min |
| QuickSight | 600 min | 595 min |
| Tableau | 10 min | 9 min |

The viewer component handles refresh automatically. No page reload is required.

**Creating a Model A report item**

1. Create (or reuse) a connection item of the appropriate type:
   - **Power BI** (`connection.azure`): `workspace_id`, `tenant_id`, `client_id`, and either `use_managed_identity: true` or `client_secret`
   - **Looker Enterprise** (`connection.gcp`): `host`, `embed_secret`, `embed_domain`
   - **QuickSight** (`connection.AWSIAMRole`): `region`, `account_id` — no keys needed on EC2
   - **Tableau** (`connection.tableau`): `server_url`, `client_id`, `secret_id`, `secret_value`; optionally `site_id` for Tableau Cloud multi-site
2. Create the report item in a `folder.report` or `folder.asset` folder with `connection_laui` and the type-specific fields.
3. Open the report in the Report Explorer — the dashboard renders as a full-page iframe.

---

### Model B — Browser session auth (Looker Studio / Google Data Studio)

`looker_studio_report` works differently. Looker Studio has no server-side embed API — there are no credentials to exchange. Instead:

- The embed URL is stored directly on the report item (no `connection_laui` needed)
- The backend returns it as-is; no signing or token exchange occurs
- The iframe authenticates using the **Google session already in the user's browser**

```
User opens report
       ↓
Frontend calls POST /api/v1/embed/token { item_laui }
       ↓
Backend reads embed_url from the report item
       ↓
Returns { embed_url } — no credential exchange
       ↓
Frontend renders <iframe src={embed_url} />
       ↓
Google checks browser session cookie → renders report if authorized
```

**How access works**

Access is controlled at two layers:

| Layer | Controlled by | Effect |
|---|---|---|
| Who sees the report item | LeastAction catalog permissions | Users without folder access never see the item or URL |
| Who can view the embedded report | Google account in the browser | Report renders if the user is signed into an authorized Google account |

For the embed to render without a sign-in prompt, the user must be signed into Google in their browser with an account that has access to the Looker Studio report. In practice, anyone signed into Chrome with a company Google Workspace account will see it load automatically — no extra login step.

**Looker Studio has no native folder view** — its home page shows flat lists (Recent, Shared with me, Owned by me). Organization is via Google Drive. This is why using LeastAction's Report Explorer as the consumption layer makes sense: business users get real folder navigation, mixed report types, and LeastAction permissions in one place, while the data team uses Looker Studio's editor to author reports.

**Sharing settings required in Looker Studio**

- File → Share → Add the authorized emails or your Google Workspace domain
- File → Share → Embed report → enable "Allow embedding"
- Do not set to "Anyone with the link" unless you want truly public access — restricting to specific accounts or a domain keeps it private while still rendering seamlessly for signed-in users

**Creating a Looker Studio report item**

1. In Looker Studio: File → Share → Embed report → copy the embed URL
2. Create a `looker_studio_report` item in a `folder.report` or `folder.asset` folder:
   - `name`: display name
   - `embed_url`: the embed URL from Looker Studio (format: `https://lookerstudio.google.com/embed/reporting/{id}/page/{page}`)
   - `description`: optional
3. Open the report in the Report Explorer — renders immediately if the user is signed into an authorized Google account in their browser.

---

## table: RDBMS Table Registration

The `table` asset registers an RDBMS table in the catalog as a catalog item. This is created by the `LeastActionTaskToTableAsset` postAction — it runs automatically after a task completes successfully.

### What it does

When a task finishes with state `success`, the postAction creates a `table` item in the catalog with:

- The table name (from a configured variable, or the task name if not specified)
- The parent folder in the catalog (configured via `parent_laui`)
- The last run date and logical date from the task run

If the task does not succeed, no catalog item is created.

### How to configure it

Add `LeastActionTaskToTableAsset` as a postAction on a workflow or task. Set the action variables:

```json
{
  "parent_laui": "<laui of the asset folder to register the table in>",
  "table_name": "fact_sales_daily"
}
```

If `table_name` is omitted, the task name is used as the table name.

### Result

After each successful task run, the table is registered (or updated) in the catalog. The catalog entry records when the table was last populated and what logical date the run corresponds to. Teams can browse the catalog to see which tables exist, when they were last refreshed, and trace them back to the tasks that populate them.

---

## Folder Structure for Assets

Assets are organized in the catalog through the folder hierarchy. A typical asset section looks like:

```
folder (asset) — "Data Assets"
├── folder (report) — "Sales Reports"
│   ├── html_report — "Monthly Revenue by Region"
│   ├── html_report — "Customer Cohort Analysis Q1"
│   └── ...
├── folder (table) — "Core Tables"
│   ├── table — "fact_sales_daily"
│   ├── table — "dim_customer"
│   └── ...
└── folder (asset) — "Finance"
    └── ...
```

Folder nesting is arbitrary. You can structure assets by team, domain, project, or any other dimension. Containment rules (which folders can hold which item types) are defined in `config/catalog.json`.

---

## Adding New Asset Types

To define a new asset type:

1. **Create a schema file** at `config/schema/<item_type>.json` — define the fields the item holds using JSON schema
2. **Update `config/catalog.json`** — add an entry specifying which folder types can contain the new item type
3. **Write actions** (optional) — create UI actions or postActions that create items of the new type via the catalog API

No platform restart is required. New item types are available immediately.

### Example: registering a new type

Add `config/schema/ml_model.json` defining fields like `model_version`, `framework`, `accuracy`, `artifact_path`. Update `catalog.json` so `folder.asset` can contain `ml_model`. Write a postAction `RegisterMLModelAsset` that calls the catalog API after a training task succeeds. The new item type is live.

---

## UI Actions on Assets

UI actions are not limited to creating assets. They can act on items that are already in the catalog — either a selected set of items in the folder view, or the item currently open in detail view.

This means you can attach any workflow to an asset after it exists. Some examples:

- **Approve and publish** — a reviewer selects an `html_report` and triggers an "Approve Report" action, which sets an approval flag, notifies stakeholders, and pushes the report to a shared location
- **Send report** — trigger an action on a selected report that emails or Slacks the HTML content to a distribution list
- **Refresh table** — select a `table` item and trigger a re-run of the task that populates it
- **Archive** — bulk-select items in a folder and trigger an action that marks them archived or moves them to a different folder
- **Validate** — run a data quality check action on a selected table item, writing results back as a child item

The scope of what a UI action can do is unlimited — it is Python code with access to the item's metadata, the user's identity, and any connection in the catalog. The only limit is what you want to build.

### Variable defaults from folder config

UI action variables are pre-filled from config defaults attached to the folder. When you assign a config to a folder in the catalog, any parameters defined in that config become the default values for action variables when a UI action is triggered from that folder.

This means you can configure a folder once — set the target connection, parent laui, environment, or any other parameter — and every UI action run from that folder inherits those defaults automatically. Users triggering actions from the folder do not need to re-enter values that are already known from context.

For example, a "Sales Reports" folder might have a config that sets:

```json
{
  "parent_laui": "699b9c2b30bf86a5a20cb16b",
  "source_table_name": "fact_sales_daily",
  "environment": "production"
}
```

Any UI action triggered from that folder — generate report, send report, refresh — receives these values as pre-filled defaults. Users can override them at run time if needed.

---

## The Catalog API

Assets are created and queried through the LeastAction catalog API. Actions that create assets POST to `/api/v1/catalog/create` with a payload like:

```json
{
  "item_type": "html_report",
  "name": "Monthly Revenue by Region",
  "html": "<html>...</html>",
  "parent_laui": "<laui of the parent folder>"
}
```

```json
{
  "item_type": "table",
  "name": "fact_sales_daily",
  "description": "Table loaded from task fact_sales_daily details",
  "parent_laui": "<laui of the parent folder>",
  "last_run_date": "2026-03-06T10:00:00",
  "last_logical_date": "2026-03-05"
}
```

The `user_access_token` from the action's execution context is passed in the `Authorization: Bearer` header. Permissions on the target folder are enforced by the API.

---

## Report Explorer Branding

The Report Explorer header logo and title are configurable in `config/system.yml`:

```yaml
explore_view:
  name: "Report Explorer"
  logo_url: "https://ui-avatars.com/api/?name=Acme&background=7c3aed&color=fff&size=32&bold=true&rounded=true"
```

| Field | Description |
|---|---|
| `name` | Text label displayed next to the logo in the header |
| `logo_url` | URL to any publicly accessible image (PNG, SVG, generated avatar, CDN) |

The frontend fetches this from `/api/v1/system/info` on load. If `logo_url` is set, the image is rendered at 24×24px with rounded corners. If omitted, the default "LA" text is shown.

**Suitable image sources (no account required):**

| Service | Example URL |
|---|---|
| `ui-avatars.com` | `https://ui-avatars.com/api/?name=Acme&background=3b82f6&color=fff&size=32&bold=true&rounded=true` |
| Clearbit Logo API | `https://logo.clearbit.com/yourcompany.com` |
| Your CDN / S3 | `https://assets.yourcompany.com/logo.png` |

Changes to `system.yml` take effect on the next page load — no server restart needed.

---

## Wiring AI Skills to Folders and Reports

Every folder and report in the asset hierarchy can have a `skill_laui` field that points to a `skill` item in the catalog. When a user opens the Report Explorer, the AI chat widget automatically loads the skill(s) relevant to where they are navigating — no manual skill selection required.

### How the skill context is resolved

| Where the user is | Skill loaded |
|---|---|
| Home (all projects) | All project asset-folder skills combined |
| Inside a folder | The folder's own skill + all ancestor folder skills (asset root → current folder) |
| Viewing a specific report (has `skill_laui`) | Only that report's skill — overrides all folder-level skills |
| Viewing a specific report (no `skill_laui`) | Inherits from the folder hierarchy above it |

The hierarchy is intentional: reports with their own skill get a specialist assistant; reports without one inherit from the folder, giving them a reasonable default without any extra configuration.

### Setting `skill_laui` on a folder

Set it at creation time or update the item in the catalog:

```json
{
  "item_type": "folder.asset",
  "name": "Sales Reports",
  "skill_laui": "<laui of the skill item>"
}
```

In `onboarding_setup/setup.py`, the asset org folder is created last — after skills are registered — so the Report Explorer skill LAUI can be wired in at creation time:

```python
skill_laui = skill_items.get("ReportExplorer/report_explorer_assistant")
folders["asset"] = await get_or_create_asset_folder(project_laui, account_laui, skill_laui)
```

### Setting `skill_laui` on a report

Add `skill_name` to the report's `.py` file in `onboarding_setup/assets/`:

```python
item_type = "html_report"
skill_name = "ReportExplorer/report_explorer_assistant"
```

The setup script resolves this to the actual LAUI at creation time using the skill items registered earlier in the same run.

### The ⓘ icon

When a folder or report card has a `skill_laui`, an **ⓘ** icon appears in the top-right corner of the card, and on project section headers. Clicking it opens a Markdown preview of the skill's content — letting users see exactly what the AI knows and what questions it's built to answer before they start chatting.

### Skill hierarchy example

```
asset folder        → skill: "Report Explorer Assistant"   (general fallback)
└── reports/
    └── sales/      → skill: "Sales Analytics Assistant"   (specialist)
        ├── Q1 Pipeline Report  (no own skill → inherits Sales + Report Explorer)
        └── Top Accounts Review → skill: "Report Explorer Assistant"  (own skill → overrides)
    └── marketing/  → skill: "Marketing Insights Assistant"
        └── Campaign Performance  (no own skill → inherits Marketing + Report Explorer)
```

### What skills can enable — actions for Explorer users

Skills do more than provide context. They tell the AI which actions it is authorised to call on behalf of the user. Engineers publish actions (Slack notifications, email delivery, task triggers, live SQL queries) and describe them in the skill Markdown. When users ask "send this to the sales team" or "refresh this report", the AI reads the skill to know what to call and how.

```
User: "Email this report to the CFO"
       ↓
AI reads skill Markdown → sees "Use SendEmailReport action to email reports"
       ↓
AI calls run_action(action_laui, variables={recipient: "cfo@co.com", report_laui: ...})
       ↓
Python run() executes → email sent
```

#### Tier 1 — Notifications (Slack, Email, Webhook)

**`LeastActionWebhookNotify`** is the built-in action. It posts to any webhook URL — Slack Incoming Webhooks, Teams, Discord, PagerDuty, or any HTTP endpoint. Register a connection item with the `webhook_url` and reference the action in your skill.

```python
# action: SendSlackUpdate
def run(least_action_action_object, webhook_url, message, **kwargs):
    import requests
    requests.post(webhook_url, json={"text": message}).raise_for_status()
    return True
```

For email: an action that reads SMTP credentials from a `connection` item and sends via `smtplib`. Pattern is identical to webhook — swap the transport.

**Skill excerpt:**

```markdown
## Available Actions

**SendSlackUpdate** — posts to the sales team Slack channel.
Use when the user asks to notify, alert, or update the team.
Input: `message` (string). Webhook URL is pre-configured — do not ask the user for it.

**EmailReport** — emails an HTML report to a recipient.
Use when the user says "email this" or "send this to [person]".
Input: `recipient` (email address), `report_laui` (from current report context).
```

#### Tier 2 — Task Triggers (Pipeline Runs, Report Generation)

**`LeastActionRunTask`** invokes any task in the catalog using the user's own access token — permissions are enforced at the user level, not bypassed.

List authorised task LAUIs explicitly in the skill. This acts as an allowlist: the AI can only run what you name.

```markdown
## Tasks You Can Trigger

**daily_revenue** (task_laui: abc123) — regenerates the daily revenue HTML report.
Trigger when the user asks to "refresh", "regenerate", or "get the latest" report.

**send_report_email** (task_laui: def456) — runs the email delivery pipeline.
Trigger when the user asks to send or distribute the current report.

Do not trigger any task not listed here.
```

#### Tier 3 — Live Data Research (SQL, Inspect Data)

For deeper questions — "why is Northeast revenue down?" or "show me top products by margin this week" — the AI can query your database directly using `inspect_data`. This runs read-only SQL against a connection you authorise, returns results inline, and lets the AI reason over real numbers rather than a cached report.

Describe allowed tables and guard rails in the skill:

```markdown
## Live Data Access

Use `inspect_data` for follow-up questions the current report does not answer.
Database: PostgreSQL — `ecomm_sales` schema
Tables:
- `fact_sales_daily` — daily revenue by channel, region, product
- `dim_product` — product master with margin_pct

Always LIMIT 1000. Summarise results in plain English — do not show raw SQL to users.
```

**Example end-to-end flow:**

```
User: "Is the Northeast drop a data problem or real?"
       ↓
AI: inspect_data → SELECT SUM(revenue) WHERE region='Northeast' ...
       ↓
AI: compares current vs prior week
       ↓
AI: "Revenue down 18%, orders down 14%. Looks real — no null dates or zero rows."
       ↓
User: "Send a message to the sales team"
       ↓
AI: run_action(SendSlackUpdate, message="Northeast revenue down 18%...")
```

#### Complete skill example

```markdown
# Sales Analytics Assistant

You help the sales team interpret reports and act on findings.

## Data You Know About
Reports in this folder cover daily revenue, regional performance, and product margins.
Source: ecomm_sales PostgreSQL, refreshed nightly at 02:00 UTC.

## Live Data Access
Use `inspect_data` for follow-up questions. Tables: fact_sales_daily, dim_product. Read-only. LIMIT 1000.

## Actions You Can Take
- **SendSlackUpdate** — notify the sales Slack channel. Use when user asks to alert or notify.
- **EmailReport** — email the current report. Use when user says "send" or "email".
- **RefreshSalesReport** (task_laui: abc123) — regenerate report from live data. Use for "refresh" or "latest".

## Guard Rails
Do not speculate. Use inspect_data to verify before drawing conclusions.
Do not trigger tasks not listed above.
Summarise findings in plain English — never show raw SQL output.
```

#### Registering actions and wiring the skill

1. **Write the action** — Python file in `onboarding_setup/actions/`. Single `run(least_action_action_object, ...)` method returning `True`/`False`. Register via `setup.py` or create manually in the catalog.
2. **Create the skill** — Python file in `onboarding_setup/ai/skills/`. The `content` field is the Markdown the AI reads. Name actions and task LAUIs explicitly.
3. **Attach the skill to a folder** — set `skill_laui` on the `folder.asset` item. `setup.py` does this automatically when you declare `skill_name` in the onboarding file.
4. **Attach the skill to a report** — set `skill_name` in the report's `.py` onboarding file. Overrides the folder-level skill for that report.

---

## Summary

| Capability | Detail |
|------------|--------|
| **Catalog model** | Folder hierarchy, any nesting depth, MongoDB storage |
| **Item types** | Defined by schema files + catalog.json — no code changes |
| **html_report** | AI-generated HTML report from a natural language prompt, stored as a catalog item |
| **powerbi_report** | Live Power BI embed — backend mints a short-lived token; `connection.azure` |
| **looker_report** | Live Looker Enterprise embed — backend signs a one-time URL via HMAC; `connection.gcp` |
| **looker_studio_report** | Live Looker Studio embed — no backend credentials; renders via Google browser session |
| **quicksight_report** | Live QuickSight embed — backend calls embed API; `connection.AWSIAMRole` (no keys) |
| **tableau_report** | Live Tableau embed — backend issues a Connected App JWT; `connection.tableau` |
| **table** | RDBMS table registration in the catalog, created by a postAction after task success |
| **Access** | Permissions inherited from catalog folder |
| **Embed API** | `POST /api/v1/embed/token { item_laui }` → `{ embed_url, expires_in }` |
| **Catalog API** | `/api/v1/catalog/create` — usable from any custom action |
| **skill_laui** | Optional field on any folder or report — wires the AI chat to a specific skill; inherits up the folder hierarchy |
| **ⓘ icon** | Appears on cards and project headers when `skill_laui` is set — click to preview the skill's Markdown content |
