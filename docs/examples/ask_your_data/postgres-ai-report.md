# AI Data Engineer: Natural Language Reports from PostgreSQL

Writing a report the traditional way means writing SQL, checking it runs correctly, building a template, formatting the output, and iterating when the question changes. For recurring reports this is worth it. For ad-hoc questions — something the CFO asked this morning, an anomaly someone spotted in yesterday's numbers — it rarely is.

This example shows how a single UI action in LeastAction replaces that entire cycle. You type a question in plain English. The action connects to your database, understands the table, writes the SQL, runs it, and produces a professional HTML report — all without you writing a line of code or SQL. The report lands in the catalog instantly, ready to share or send.

---

## What the Action Does

`PostgresqlToClaudeChatToHtmlReportToAsset` is a UI action that performs a two-turn AI reasoning loop:

```
You type a prompt:
"Show me revenue by product category for the last 30 days,
 ranked by total revenue with month-over-month change"

        │
        ▼
Step 1 — Understand the data
    Connect to PostgreSQL
    Read table schema (column names, types, nullability)
    Sample 5 rows to understand real values
        │
        ▼
Step 2 — Generate SQL (Claude turn 1)
    Send: schema + sample data + your prompt
    Receive: a valid PostgreSQL query that answers the question
        │
        ▼
Step 3 — Execute
    Run the generated query against the database
    Collect results
        │
        ▼
Step 4 — Generate the report (Claude turn 2)
    Send: your original prompt + the SQL + the results
    Receive: a complete, styled HTML document
        │
        ▼
Step 5 — Save to catalog
    POST to /api/v1/catalog/create
    item_type: html_report
    Saved under the folder you triggered the action from
```

The result is an `html_report` item in the catalog — viewable inline, shareable, and persistent. Every report generated this way is stored permanently. You can always go back and see exactly what was produced, from what data, for what question.

---

## What You Need

### A PostgreSQL connection

Add a connection in the LeastAction catalog with the following fields:

```json
{
  "host": "your-postgres-host",
  "port": 5432,
  "database": "your_database",
  "user": "your_user",
  "password": "your_password",
  "claude_api_key": "sk-ant-...",
  "claude_model": "claude-sonnet-4-6",
  "claude_token_limit": 4096
}
```

The Claude fields live in the same connection as the database credentials. The action reads both from `least_action_action_object.get('connection', {})`.

### A catalog folder

The action saves the report to the folder it is triggered from. Create an asset folder in the catalog to hold the output — for example, `assets/ad-hoc-reports/` or `business/finance/ai-reports/`. Set permissions so the right people can see the generated reports.

### The action in your catalog

`PostgresqlToClaudeChatToHtmlReportToAsset` is available in the LeastAction bootstrap catalog. To add it to a folder, configure it as a UI action on that folder via the action configuration. See the Action guide for how to attach actions to catalog folders and set variable defaults.

---

## Running It

Navigate to the folder in the LeastAction catalog. Trigger `PostgresqlToClaudeChatToHtmlReportToAsset` from the folder's action menu. Fill in:

| Variable | What to enter |
|----------|--------------|
| `parent_laui` | Pre-filled from folder config — the folder where the report will be saved |
| `source_table_name` | The PostgreSQL table to query (e.g. `fact_sales_daily`) |
| `chat_prompt` | Your question in plain English |

The action runs. When it completes, the report appears as a new `html_report` item in the folder. Click it to view the full styled HTML inline.

---

## Example Prompts

The prompt is unconstrained — the action sends it directly to Claude along with the table schema and sample data. Claude adapts the SQL to what the table actually contains.

**Sales analysis**
> "Show me total revenue and units sold by product category for the last 7 days, sorted by revenue descending. Include the percentage each category contributes to the total."

**Anomaly investigation**
> "Find any products where revenue yesterday was more than 50% higher or lower than their 7-day average. Show the product name, yesterday's revenue, and the 7-day average."

**Executive summary**
> "Summarize this month's sales performance. Show total revenue, total orders, average order value, and top 5 products by revenue. Compare to last month where possible."

**Regional breakdown**
> "Break down total revenue by region and sub-region for Q1 2026. Rank regions by revenue and show what percentage of total each represents."

**Trend report**
> "Show me daily revenue for the last 30 days with a 7-day rolling average. Flag any days where actual revenue was more than 15% below the rolling average."

Each of these produces a different query and a different styled HTML report. You do not write the SQL. You do not build the template. You ask the question.

---

## What Claude Receives

To generate accurate SQL, Claude sees the full table schema — column names, types, nullability — and 5 sample rows showing real values. This is why it can handle questions that reference dimension values (`"North America"`, `"Electronics"`) without being told the exact values in advance — it reads them from the sample.

For the HTML generation, Claude receives the original prompt, the SQL that was executed, and the full query results. The HTML it produces includes the data formatted appropriately (table, summary cards, or other layout depending on the data shape), the SQL used, and the generation timestamp.

---

## Where This Fits in a Larger Workflow

`PostgresqlToClaudeChatToHtmlReportToAsset` is a UI action — designed for interactive, on-demand use triggered by a person. It is the right tool when:

- The question is ad-hoc and not worth building a dedicated pipeline for
- A stakeholder needs an answer quickly and the data is already in a known table
- You want to explore a dataset before deciding whether to productionize a report

For **recurring scheduled reports** — daily revenue dashboards, weekly executive summaries — the right pattern is a pipeline with pre-written SQL and a report template, as covered in the PostgreSQL Sales Reporting example. Scheduled reports should be deterministic and auditable; AI-generated SQL is better for exploration.

For **approval and distribution**, combine this with the `ApproveAndSendReport` action covered in the Report Approval Workflow example. The AI-generated report lands in the catalog → an analyst reviews it → one click sends it and archives it.

---

## The Pattern Is Not Specific to This Action

`PostgresqlToClaudeChatToHtmlReportToAsset` is one example of what a LeastAction action can do when combined with an AI API. The pattern — read data context, send to AI, execute result, send output back to AI, save to catalog — works for many things:

- **Any database**: the same pattern works for Redshift, BigQuery, MySQL, or any database where you can read schema and run queries
- **Any output format**: instead of HTML, the action could produce a JSON summary, a Markdown document, or a structured dataset
- **Any question type**: SQL generation is one task. The same structure works for anomaly detection explanations, data quality narratives, automated commentary on metric changes
- **Multi-step reasoning**: this action does two AI turns. More complex actions can chain more steps — validate the generated SQL before running it, retry if the query fails, ask for a revised approach

The action file is the starting point. Read through `PostgresqlToClaudeChatToHtmlReportToAsset.py` in the bootstrap catalog to understand how it is structured — the schema read, the two Claude calls, the catalog API call — and use it as a template for building your own AI-powered actions.

For how to write and configure actions in LeastAction, see the Action guide.
