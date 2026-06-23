# Quickstart

Install LeastAction and run your first task in a few minutes. For a deeper, manual walkthrough see the [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection).

## 1. Install (single machine, Docker)

From the repo root:

```bash
# First install (zero-downtime blue/green stack: backend, workers, frontend, infra)
./blue-green-run.sh --fresh

# Developers: build images from local source instead of pulling
./blue-green-run.sh --fresh --build
```

The app comes up at **<http://localhost:8080>** — default login `admin@example.com` / `admin123` (override via `deploy/.env`). The first run also loads the **bootstrap catalog** (sample operators, connections, configs, skills, and usecases) so there's something to run immediately.

> Details, flags, configuration, and how the blue/green deploy works: [Installation](/path?laui=getting-started-02-installation-01-docker-compose&itemtype=doc.file&itemname=Docker%20Compose) and [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green).

## 2. Run your first task — the fast path

The bootstrap ships a minimal pipeline (`postgresql-demo-foundations`: create table → insert → update) wired to the included `postgres-demo` database. Two ways to run it:

**A — Deploy a usecase with the AI (recommended).** Open the AI chat (or connect via MCP) and say:

> "deploy usecase postgresql-demo-foundations, then run it and check the status"

The agent creates the three tasks, runs them in order, and reports state + logs.

**B — From the UI.** Browse to the workflow folder → **Create Task** → pick the `PostgresqlExecuteSQL` operator and the `postgresql` connection → paste a SQL payload → **Create**, then **Run**.

## 3. Verify the data

Confirm rows landed — ask the AI:

> "inspect the people table on the postgresql connection"

or run `SELECT * FROM people ORDER BY id` via `inspect_data`. You should see the rows the pipeline wrote.

## 4. Where to go next

- [Tutorial](/path?laui=getting-started-03-tutorial-01-create-a-connection&itemtype=doc.file&itemname=Create%20A%20Connection) — build a pipeline from scratch (connection → operator → payload → task → schedule → dependencies).
- [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) — the model behind it all.
- [AI overview](/path?laui=getting-started-06-ai-01-overview&itemtype=doc.file&itemname=Overview) — generate operators, use skills/usecases, connect via MCP.
- Browse `ai/usecases` in the catalog for runnable, lifecycle-organized examples.
