# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 05_reporting  |  Flavor: KB (skills-only knowledge bundle — no payloads)
# Teaches an AI agent how to turn a plain-English question into a live answer and a published report:
# inspect_data (read live) -> generate HTML -> save as html_report asset -> notify (Slack/email).
# Pattern 3: the agent reads these skills and implements the flow itself over MCP.
payloads = {}

skills = {
    "00_overview.md": """\
# Ask Your Data — overview & prerequisites

## Lifecycle stage
Reporting / serving. This is a **knowledge bundle** (no payloads): an AI agent reads these skills and
implements the flow on demand. Two paths are taught — the short MCP/chat way (skill 01) and the
packaged one-click action (skill 02).

## When to use
Ad-hoc questions not worth a dedicated pipeline; a stakeholder needs an answer now; exploring a dataset
before productionizing. For recurring, deterministic dashboards use a scheduled reporting pipeline
(see `03_transformation` sales reporting), not AI-generated SQL.

## Prerequisites in core
- A read connection to the data (PostgreSQL/MySQL/Redshift/BigQuery/Athena/S3/GCS/Azure) for `inspect_data`.
- To publish/notify: a catalog folder for the report asset; for the packaged path the
  `PostgresqlToClaudeChatToHtmlReportToAsset` action; for notify the `LeastActionWebhookNotify`
  (Slack) and/or `LeastActionSMTPEmail` (email) actions.

## Verify success
The agent answered from live data (not memory); if a report was requested, an `html_report` asset
exists in the target folder; if notify was requested, `run_action` returned a real `session_id` and success.
""",

    "01_short_way_mcp.md": """\
# Path A — Just ask (MCP / Service Chat)

The fastest path: the agent reads live data and answers, then optionally saves and sends — all in one
turn. This is the Pattern-3 "AI reads and implements" recipe.

## Tool chain
1. **Read live data** — `inspect_data(connection_laui=<conn>, sql="SELECT ...")`. Read-only (SELECT/WITH;
   DDL/DML blocked). Find the connection with `search_catalog(item_type="connection")`. For ad-hoc
   questions this single call is often the whole answer.
2. **Understand schema first when needed** —
   `inspect_data(sql="SELECT column_name, data_type FROM information_schema.columns WHERE table_name='<t>'")`
   then a `SELECT * ... LIMIT 20` to see real values before writing the analytic query.
3. **Generate a report (optional)** — render the result as a styled HTML report and save it as an
   `html_report` asset in the catalog folder the user names (this is what makes the answer shareable
   and versioned). Use the report skill / the packaged action in skill 02 to produce the html.
4. **Notify (optional)** —
   - Slack: `run_action(action_laui=<LeastActionWebhookNotify>, action_variables={webhook_url, message})`
   - Email: `run_action(action_laui=<LeastActionSMTPEmail>, action_variables={to, subject, body, is_html})`
   Keep the returned `session_id`; report the real outcome (never claim a send that didn't happen).

## Example request the agent fulfills end-to-end
> "Revenue by product category for the last 30 days, ranked, with MoM change. Save it as a report in
> business/finance/ai-reports and post the highlights to #sales."

inspect_data (schema + query) -> generate HTML -> save html_report asset -> run_action Slack.

## Rules
- Always answer from `inspect_data` against live data — never from memory.
- Confirm a cloud path (`s3://`/`gs://`/`azure://`) and the connection with the user before inspecting it.
- Everything is scoped to the user's catalog permissions.
""",

    "02_packaged_action.md": """\
# Path B — One-click packaged action

When the same outcome should be a repeatable button (non-technical user, fixed folder/table), use the
bootstrap action `PostgresqlToClaudeChatToHtmlReportToAsset`. It bundles the read -> generate -> save loop
as a two-turn AI action triggered from a folder.

## What it does
1. Connect to PostgreSQL, read the table schema, sample rows.
2. Claude turn 1: schema + sample + prompt -> a valid SQL query.
3. Execute the query.
4. Claude turn 2: prompt + SQL + results -> styled HTML.
5. Save an `html_report` item under the triggering folder.

## Setup
A PostgreSQL connection that ALSO carries the Claude fields (the action reads both from
`least_action_action_object.get('connection', {})`):
```json
{ "host": "...", "port": 5432, "database": "...", "user": "...", "password": "...",
  "claude_api_key": "sk-ant-...", "claude_model": "claude-sonnet-4-6", "claude_token_limit": 4096 }
```
Attach the action to a catalog folder; the report saves to that folder.

## Run variables
| Variable | Value |
|---|---|
| `parent_laui` | pre-filled from folder config — where the report is saved |
| `source_table_name` | the table to query (e.g. `fact_sales_daily`) |
| `chat_prompt` | the question in plain English |

## Generalizes
Same pattern works for any source `inspect_data` supports, any output format (HTML/JSON/Markdown), and
chaining further actions (notify, trigger a task, start an approval). Read
`PostgresqlToClaudeChatToHtmlReportToAsset.py` in the bootstrap catalog as a template for your own.
""",
}

prompt = (
    "Knowledge bundle teaching an AI agent to answer plain-English data questions and produce reports: "
    "use inspect_data to read live data (PostgreSQL/MySQL/Redshift/BigQuery/Athena/S3/GCS/Azure), generate "
    "a styled HTML report, save it as an html_report catalog asset, and notify via LeastActionWebhookNotify "
    "(Slack) or LeastActionSMTPEmail (email). Also covers the packaged PostgresqlToClaudeChatToHtmlReportToAsset "
    "UI action. Skills-only (Pattern 3): the agent reads these and implements the flow over MCP."
)

description = (
    "Reporting (KB): teach the AI to turn a question into a live answer and a published report — "
    "inspect_data -> generate HTML -> save as a catalog asset -> notify. Two paths: the short MCP/chat "
    "way and the packaged one-click action. No payloads; the agent implements it."
)

guide_docs = """\
# Ask Your Data — Natural-Language Reports

**Lifecycle stage:** Reporting / serving. **Flavor:** skills-only knowledge bundle — an AI agent reads
the skills and implements the flow (Pattern 3); there are no pre-built tasks to deploy.

## The short way (Path A)
Ask in plain English via MCP (Claude Code / claude.ai) or the in-app Service Chat. The agent:
`inspect_data` (read live, SELECT-only) -> generate a styled HTML report -> save it as an `html_report`
asset in the folder you name -> `run_action` to post Slack (`LeastActionWebhookNotify`) / email
(`LeastActionSMTPEmail`). All in one request; everything scoped to your permissions.

## The packaged way (Path B)
For a repeatable one-click button, use the `PostgresqlToClaudeChatToHtmlReportToAsset` action on a
folder: schema read -> Claude SQL -> execute -> Claude HTML -> saved `html_report`. Needs a PostgreSQL
connection that also carries `claude_api_key`/`claude_model`.

## Prerequisites
- A read connection for `inspect_data`.
- To publish: a catalog folder for the report asset.
- To notify: `LeastActionWebhookNotify` (Slack) and/or `LeastActionSMTPEmail` (email).
- For Path B: the `PostgresqlToClaudeChatToHtmlReportToAsset` action + Claude creds on the connection.

## When NOT to use
Recurring, deterministic dashboards should be a scheduled reporting pipeline (pre-written SQL + template),
not AI-generated SQL — see the sales-reporting usecase in `03_transformation`. AI generation is for
exploration and ad-hoc answers.

## Deploying / using
This is a knowledge bundle — there is nothing to "deploy as tasks." Use it by asking the agent:
> "use the ask-your-data usecase to report revenue by region for last week and post it to #sales"

The agent reads these skills and runs the inspect -> generate -> save -> notify chain.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Reporting",
    "tags": ["flavor:KB", "lifecycle:reporting", "ai", "ask-your-data", "inspect_data", "html_report", "notify"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
