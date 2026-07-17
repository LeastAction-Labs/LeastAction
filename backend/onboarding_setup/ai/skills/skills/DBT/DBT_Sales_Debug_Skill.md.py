# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = {
    "description": "Debug skill for the dbt sales reporting pipeline — calls an AI agent with pipeline and data-contract skills plus task state, and routes the resulting report to email, Slack, or a catalog asset.",
    "content": """\
# dbt Sales Pipeline — Debug Skill

## Purpose

Use this skill to diagnose a failing task in the `dbt_sales_reporting` workflow.
It drives the `LeastActionAgentDebug` action, which fetches named skills and the
current task state from the catalog, calls an AI agent to produce a structured
root-cause analysis, and routes the report to whichever `notify` destination is
configured (email, Slack, catalog asset, or local file).

## When to use

Attach `LeastActionAgentDebug` as a **post_action** on any task in the pipeline that is
failing or producing unexpected output. The agent's analysis is routed per `notify`;
if no destination is configured, the report is logged to the task logs instead.

## LeastActionAgentDebug action_variables

```json
{
  "skill_names": [
    "DBT_Postgresql_Sales_Pipelines_Skill",
    "DBT_Postgresql_Sales_Data_Contract"
  ],
  "connection_laui": "<claude-connection-laui>",
  "chat_laui": "<agent-chat-item-laui>",
  "include_task_context": true,
  "notify": {
    "email": "you@example.com",
    "slack_url": "https://hooks.slack.com/services/xxx/yyy/zzz",
    "asset_laui": "<folder-asset-laui-to-write-report-under>"
  }
}
```

`notify` is conditional — only the keys you set are used: set `notify.email` to send
by email, `notify.slack_url` to post to Slack, `notify.asset_laui` to save the report
as a catalog asset. Any combination can be set at once.

To add only the pipeline skill (lighter context, no notify — report goes to logs):

```json
{
  "skill_names": ["DBT_Postgresql_Sales_Pipelines_Skill"],
  "include_task_context": true
}
```

## What the agent receives and produces

| Section | Content |
|---------|---------|
| Task state | Full task document fetched from catalog (state, payload, actions_status, …) |
| `SKILL: <name>` | Full `content` field of each named skill document |
| `SKILL PROMPT: <name>` | The `prompt` field of each named skill (the AI prompt used by the orchestrator) |
| Agent analysis | Structured root-cause analysis returned by the AI agent, included at the top of the report |

## Common failure patterns and fixes

| Symptom | Where to look | Fix |
|---------|---------------|-----|
| `dbt-server unreachable` | CURRENT TASK payload → connection | `docker compose up -d dbt-demo` |
| `model file missing` | SKILL content → dbt models table | Copy model SQL into `dbt-server/demo_project/models/` |
| Contract gate failed | `00b_sales_contract` task state | Inspect the failing clause: schema/type (e.g. `product_name` length changed), referential (category/region/product_id), domain (negative profit / units<=0), freshness or volume band. Confirm the seed produced ~400k rows |
| `03b` reconciliation / anomaly fail | `03b_sales_validation` task state | Reconciliation fail (Σ product revenue ≠ grand total) ⇒ a source **fan-out** — check the stage1 CUBE + the seed join grain. WoW / 3σ / YoY trip ⇒ decide **real spike vs fan-out** by inspect_data around the date before editing |
| Revenue looks "10x" on a dashboard | `fact_product_agg_daily` by date | Usually **real** Nov/Dec holiday seasonality — confirm with the reconciliation + WoW checks before assuming a bug |
| Rolling metrics empty | `02_rolling_metrics` task state | Ensure stage1 produced rows; widen date range in payload |
| HTML report empty | `04`/`05` task state | Widen `date_filter` in the report payload |
| Task stuck in `scheduled` | CURRENT TASK → `state`, `actions_status` | Parent hasn't reached `success`; check pre_actions logs |

## Pipeline DAG reminder

```
00_fact_sales_daily (seed ~400k rows, realistic 5-yr tech-retail)
    ├── 00b_sales_contract (data-contract gate)
    └── 01_cube_aggregation (DBTRunModel — stage1)
            └── 02_rolling_metrics (DBTRunModel — stage2)
                    └── 03_final_metrics (DBTRunModel — final)
                            ├── 03b_sales_validation (PostgresqlValidatorSQL)
                            ├── 04_sales_performance_report
                            └── 05_category_performance_report
```

## On-call loop — act like a human engineer

For an **incident** (Sev-1: a Tier-1 table stale or wrong), work it end to end and pull in a human
only for **approval** or genuinely **out-of-scope** work:
1. **Triage** — `get_task_logs` on the failing step + `inspect_data` on `postgres_demo_db` to confirm the hypothesis.
2. **Fix forward** — correct the seed / dbt model / report payload; never hand-mutate a table (reruns full-rebuild).
3. **Re-run the chain** — the failed step AND every downstream step through `03_final_metrics` → `04`/`05`.
4. **Verify** — confirm `03b_sales_validation` is green (reconciliation, freshness, WoW, 3σ anomaly, YoY).
5. **Communicate on Slack** — post status, then an all-clear, to `#px-data-incidents`. Discover the tool, don't
   hardcode the secret: `search_catalog(action, "slack"/"webhook")` → `connection.slack`, then
   `run_action(LeastActionWebhookNotify, connection_laui=<slack>, action_variables={"message": "<summary>"})`.
   The webhook lives in the vaulted connection — you never handle the URL. Escalate in-thread if unresolved.

`LeastActionAgentDebug` already **auto-triages** a failing task (it feeds this skill + the pipeline/contract
skills to an AI agent and routes the analysis via `notify`). Use that analysis as your starting point, then
close the loop above.

## Related skills

- `DBT_Postgresql_Sales_Pipelines_Skill` — full pipeline orchestration reference
- `DBT_Postgresql_Sales_Data_Contract` — data contract clauses and YAML payload
""",
}

prompt = (
    "Debug a failing dbt sales pipeline task: attach LeastActionDebug as a post_action "
    "with skill_names=[DBT_Postgresql_Sales_Pipelines_Skill, DBT_Postgresql_Sales_Data_Contract] "
    "and include_task_context=true to log the full skill content and task state. "
    "Use the logged output to identify which contract clause failed, which dbt model is missing, "
    "or why a task is stuck in scheduled state."
)

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Debug",
    "tags": ["dbt", "postgresql", "sales", "debug", "pipeline", "skill", "inspect"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
