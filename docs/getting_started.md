# LeastAction Documentation

LeastAction is an AI-powered orchestration platform. Most AI tools help you *write* pipeline code — LeastAction gives the AI an operator: it generates the code, deploys it, runs it, reads the logs, queries the data, spots the issue, fixes itself, and reruns. It works on the stack you already have (PostgreSQL, Athena, Redshift, BigQuery, S3, Lambda, dbt, Airflow, any API), self-hosted, with no migration.

Everything lives in one **catalog** — operators, connections, payloads, configs, actions, tasks, reports, and assets. The catalog is the shared context the AI works from, and the same interface engineers use to schedule, monitor, and reuse pipelines across teams.

---

## Start here

| Step | Read |
|---|---|
| **1. Understand it** | [Overview — what & why](/path?laui=getting-started-01-getting-started-01-overview&itemtype=doc.file&itemname=Overview) |
| **2. Install + first task** | [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart) |
| **3. Learn the model** | [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) |
| **4. Build a real pipeline** | [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection) |

---

## The documentation, by journey

1. **Getting Started** — overview, quickstart (install + first task), core concepts.
2. **Installation** — Docker Compose for local/dev, configuration, and zero-downtime production deploys.
3. **Tutorial** — build your first pipeline step by step: connection → operator → payload → run → schedule/backfill → dependencies.
4. **Concepts** — the mental model: items & catalog, connection, operator, payload, config, action, workflow, task states, scheduling.
5. **Building Pipelines** — how-to guides: write an operator/action, task dependencies, monitoring, plus backfill and notify/control (with runnable catalog usecases).
6. **AI** — the four AI modes: service generation, skills, usecases, MCP, and the Report Explorer.
7. **Working in the UI** — assets & reports, UI actions, and the marketplace.
8. **CI/CD** — deploy tasks from Git.
9. **Administration** — access & permissions, groups, users.
10. **Reference** — REST API, schemas, and a glossary.
11. **Comparisons** — honest comparisons vs Airflow, Dagster, and Prefect.

> **Looking for runnable examples?** They ship as **usecases** in the catalog (browse `ai/usecases`), organized by the same data-engineering lifecycle — deploy one and an AI agent can read it and implement it for you. The docs teach the concepts; the usecases are the worked, runnable examples.
