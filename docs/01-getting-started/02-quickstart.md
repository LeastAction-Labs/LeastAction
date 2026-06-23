# Quickstart

Install LeastAction and run your first task in a few minutes. For a deeper, manual walkthrough see the [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection).

## 1. Install (single machine, Docker)

From the repo root:

```bash
# Development & testing — Docker Compose
docker compose up -d --build   # first time / after pulling new source
docker compose up -d           # subsequent starts
```

> This is the **development & testing** path. For production/self-hosting use the zero-downtime blue-green deploy — see [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green).

The app comes up at **<http://localhost:8080>** — default login `admin@example.com` (or username `admin123`) / password `admin123` (override via `deploy/.env`). The install bundles a **dbt** runner and a **`postgres-demo`** database, and loads the **bootstrap catalog** (sample operators, connections, configs, skills, and usecases).

> Details, flags, configuration, and how the blue/green deploy works: [Installation](/path?laui=getting-started-02-installation-01-docker-compose&itemtype=doc.file&itemname=Docker%20Compose) and [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green).

## 2. Run your first task

**You don't have to build anything for the first run.** A fresh install **pre-creates** a Postgres demo workflow — three dependent tasks (create table → insert rows → update rows) on the included `postgres-demo` database, scheduled every 3 minutes. They **start running on their own within ~3 minutes** of setup and run for about 30 minutes.

- **Watch it run** — open the workflow folder in the UI and you'll see the three tasks move through their states (the insert/update wait on their parent via a dependency action).
- **Trigger it now** — don't want to wait? Open a task and click **Run** to fire it immediately.
- **Re-enable later** — after the ~30-minute window (or anytime), use the **Schedule** action (`LeastActionSchedule`) on a task to (re)start its schedule.

**Want to deploy a pipeline yourself?** Do it through the AI instead of building by hand — open the AI chat (or connect via MCP) and say:

> "deploy usecase postgresql-demo-foundations, then run it and check the status"

The agent creates the tasks, runs them in order, and reports state + logs. This is the recommended way to stand up new pipelines (see the [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection) for the manual UI path).

## 3. Verify the data

Confirm rows landed — ask the AI:

> "inspect the people table on the postgresql connection"

or run `SELECT * FROM people ORDER BY id` via `inspect_data`. You should see the rows the pipeline wrote.

## 4. Where to go next

- [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection) — build a pipeline from scratch (connection → operator → payload → task → schedule → dependencies).
- [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) — the model behind it all.
- [AI overview](/path?laui=getting-started-06-ai-01-overview&itemtype=doc.file&itemname=Overview) — generate operators, use skills/usecases, connect via MCP.
- Browse `ai/usecases` in the catalog for runnable, lifecycle-organized examples.
