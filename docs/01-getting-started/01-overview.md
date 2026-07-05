# Overview — What & Why

LeastAction is a workflow orchestration platform that combines a traditional orchestrator with AI-driven development and a visual, folder-based catalog. It runs on the stack you already have — PostgreSQL, Athena, Redshift, BigQuery, S3, Lambda, dbt, Airflow, any API — self-hosted, with no migration.

## What makes it different

Most AI tools stop at code suggestions. LeastAction gives the AI an **operator** and a **catalog**, so it can run the full loop:

```
describe a pipeline (skill or usecase) → AI generates the operator + task → runs it
→ reads the logs → queries the target database → spots a data issue → fixes the operator
→ reruns → confirms the data is correct
```

No terminal switching, no separate BI tool or database client. The `inspect_data` capability connects to any catalog connection and returns results inline, so the AI verifies what a task wrote and self-corrects without a human at each step.

## Why LeastAction

Airflow, Dagster, and Prefect are excellent at *running* pipelines. LeastAction starts from a different place — an AI operator and a catalog open to the whole team:

- **The AI operates, end to end** — generate → deploy → run → read logs → query results → fix → rerun, not just code hints.
- **Orchestrate without Python** — engineers write operators in Python (or generate them with AI); everyone else assembles, schedules, and runs pipelines from the UI or Git.
- **Custom operators & connections, no package infrastructure** — write an operator, save it to the catalog, use it immediately. No provider packages, no per-worker deploy. Connections take whatever fields your operator needs.
- **Granular control built in** — N-level config with locked/overridable parameters, per-connection parallelism with priority queuing, native Git CI/CD, and 1-click backfill for any task and any date.
- **A catalog that's also a CMS** — register tables, publish AI-generated reports, and browse pipeline outputs in the same system.

## Who it's for

- **Engineers / platform admins** — build operators, debug tasks, manage connections, deploy usecases (via the UI, Git, or MCP/Claude Code).
- **Analysts / business users** — ask questions in plain English and read live reports in the **Report Explorer** — no pipeline access required.

## Where to go next

- [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart) — install and run your first task.
- [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) — the `Connection + Operator + Payload + Config = Task` model.
- Honest comparisons: [vs Airflow](/path?laui=getting-started-11-comparisons-airflow&itemtype=doc.file&itemname=Airflow) · [vs Dagster](/path?laui=getting-started-11-comparisons-dagster&itemtype=doc.file&itemname=Dagster) · [vs Prefect](/path?laui=getting-started-11-comparisons-prefect&itemtype=doc.file&itemname=Prefect)
