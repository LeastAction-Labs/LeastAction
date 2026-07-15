# LeastAction

Most AI tools help you write pipeline code. LeastAction gives the AI an operator — it generates the code, deploys it, runs it, reads the logs, queries the data, spots the issue, fixes the operator, and reruns. No human in the loop at each step. It works against whatever stack you already have — PostgreSQL, Athena, Redshift, BigQuery, S3, Lambda, dbt, Airflow, any API — with no migration.

Everything lives in a catalog: operators, connections, payloads, configs, actions, tasks, reports, and assets. The catalog is the shared context the AI works from — and the same interface engineers use to schedule, monitor, and reuse pipelines across teams. Self-hosted, one instance per team.

---

## Why LeastAction

Airflow, Dagster, and Prefect are excellent at running pipelines. LeastAction takes a different starting point — an AI operator and a catalog open to the whole team:

- **The AI operates, end to end.** It generates the operator, deploys it, runs it, reads logs, queries the result, fixes its own bug, and reruns — not just code suggestions, but the full loop.
- **Orchestrate without Python.** Engineers write operators in Python (or generate them with AI); everyone else assembles, schedules, and runs pipelines from the UI or Git.
- **Custom operators and connections, no package infrastructure.** Write an operator, save it to the catalog, use it immediately — no provider packages, no per-worker deploy. Connections take any fields your operator needs.
- **Granular control built in.** N-level config with locked/overridable parameters, per-connection parallelism with priority queuing, native Git CI/CD, and 1-click **backfill** for any task and any date.
- **A catalog that's also a CMS.** Register tables, publish AI-generated reports, and browse pipeline outputs in the same system.

Works on the stack you already have, self-hosted, with no migration.

**Honest, detailed comparisons:** [vs Apache Airflow](docs/11-comparisons/airflow.md) · [vs Dagster](docs/11-comparisons/dagster.md) · [vs Prefect](docs/11-comparisons/prefect.md)

---

## Task Management

![Task Management](images/Task_management.png)

Every task follows one formula:

```
Connection + Operator + Payload + Config = Task
```

- **Operator** — Python code that defines how a task runs (invoke Lambda, run SQL, process a file, call an API)
- **Connection** — credentials and concurrency controls for an external system
- **Payload** — the specific parameters for this run (which SQL, which Lambda, which partition)
- **Config** — execution rules: schedule, retry logic, SLA, dependencies, defaults
- **Actions** — lifecycle hooks that run before, during, or after a task. Built-in actions handle dependency checks, SLA alerts, Slack notifications, Git sync, and report generation. Generate custom actions with AI or import from the marketplace.

Tasks run on a schedule or on demand. **Partitions** let you run the same workflow in parallel across regions, customers, or datasets. **Dependencies** are resolved by name across any project — no hard-coded wiring. Logs, state, and run history are visible in real time.

---

## AI & MCP

***The full loop is supported end-to-end without leaving the AI session:***

```
describe a pipeline as SKILL or Usecase → AI generates operator + task → runs it → reads logs → queries the target database → spots a data issue → fixes the operator → reruns → confirms data is correct
```

No terminal switching, no BI tool, no separate database client. The `inspect_data` MCP tool connects directly to any catalog connection (PostgreSQL, MySQL, Athena, Redshift, BigQuery, S3, GCS, Azure Blob) and returns results inline — so the AI can verify what a task wrote, validate row counts, sample loaded data, and self-correct without human intervention at each step.

Admins can restrict which MCP tools each user can access — for example, disabling destructive operations like `delete_item` or `reset_task` for specific users. Managed per-user from **Admin → MCP Access**. See [MCP setup guide](docs/06-ai/05-mcp.md) for details.


![Claude Code + MCP](images/MCP-Claude-VSC.png)

---

## Marketplace

The Marketplace is where you discover, import, and publish LeastAction items — built by LeastAction Labs and the community.

**Item types available:**

| Type | Description |
|------|-------------|
| `operator` | Reusable execution logic (AWS, PostgreSQL, Airflow, and more) |
| `action` | Lifecycle hooks for dependencies, notifications, and CI/CD |
| `payload` | Reusable payload templates compatible with common operators |
| `skill` | AI context bundles — schemas, generation rules, business logic |
| `usecase` | Bundled pipelines: payloads + skills + scheduling metadata, ready to deploy |

Items carry **Official**, **Verified**, and **community** badges with version/compatibility checks. Import any item into your catalog in one click — free in LeastAction core. Publish your own items with a LeastAction account. Comes built-in with AWS and dbt operators. GCP and more coming soon.

![Explore Marketplace](images/Explore_marketplace.png)

---

## Explorer View — Report Explorer (Experimental Preview)

The **Report Explorer** gives business users direct access to reports — organized by project and team — with a context-aware AI chat widget on every report page. From the widget they can get fresh reports, ask follow-up questions against live data, run tasks, check pipeline status, send Slack messages or emails, and trigger actions — without leaving the report. Skills published by the data team control what the AI can answer and reach, and permissions are enforced end to end.

Supported types: `html_report` (AI-generated HTML stored in the catalog) plus live embeds for Power BI, Looker Enterprise, Looker Studio, QuickSight, and Tableau. Each live dashboard (except Looker Studio) points to a `connection`; the backend exchanges credentials for a short-lived embed URL so secrets never reach the browser. Looker Studio needs no connection — it renders via the user's Google browser session.

See [Report Explorer — User Guide](docs/06-ai/06-report-explorer.md) for the full overview.

![Explorer View](images/Explorer-view.png)


---

## Installation

All you need is Docker (>= 24, with Compose v2). Two paths, depending on what you're doing:

| Path | Use it for | Command |
|------|-----------|---------|
| **Docker Compose** | Development & testing | `docker compose up -d --build` |
| **Blue-Green** | Production / self-hosting | `./blue-green-run.sh --fresh` |

### Development & testing — Docker Compose

```bash
git clone https://github.com/LeastAction-Labs/LeastAction.git
cd LeastAction

# First time — build images and start
docker compose up -d --build

# Subsequent starts — reuse already-built images
docker compose up -d
```

`--build` compiles the `backend` and `frontend` images locally; the Celery
workers reuse the backend image by tag. Pass `--build` again any time you pull
new source changes.

Open **http://localhost:8080** — default login `admin@example.com` (or username
`admin123`) / password `admin123`. Override the root login and other defaults
with a `.env` file — see [deploy/.env.example](deploy/.env.example). RSA signing
keys are generated automatically on first run. The install also bundles a **dbt**
runner and a **`postgres-demo`** database, and seeds a small demo workflow that
**starts running on its own within ~3 minutes** — so there's a working pipeline
to watch immediately.

| Port | URL | What's there |
|------|-----|--------------|
| 8080 | http://localhost:8080 | UI, REST API (`/api/`), MCP endpoint (`/mcp/`) |
| 5555 | http://localhost:5555 | Flower — Celery worker monitor |

```bash
docker compose down       # stop
docker compose down -v    # stop and wipe all data
```

**Scaling Celery workers** — every queue has its own service, and **all of them can be scaled** with
`--scale` (independently or together):

```bash
# Scale a single queue
docker compose up -d --scale celery-task-worker=3
docker compose up -d --scale celery-action-worker=3
docker compose up -d --scale celery-cron-worker=3

# Scale all queues at once
docker compose up -d \
  --scale celery-task-worker=3 \
  --scale celery-action-worker=2 \
  --scale celery-cron-worker=2
```

### Production / self-hosting — Blue-Green

The compose flow above restarts everything on each update. For production-style
self-hosting, use the blue-green deploy script instead: it runs the app in two
slots (blue/green), brings the new one up alongside the old, switches traffic
only once it's healthy, and rolls back failed deploys automatically.

```bash
chmod +x blue-green-run.sh    # one-time (or run `bash blue-green-run.sh ...`)

./blue-green-run.sh --fresh   # first install
./blue-green-run.sh           # zero-downtime redeploy (swaps blue <-> green)
```

See [deploy/README.md](deploy/README.md) for flags, slots, rollback, and how the deploy works.

---

## Documentation

All product documentation lives in [`docs/`](docs/). Start here:

- [Getting Started](docs/01-getting-started/02-quickstart.md) — core concepts, your first task in under 20 minutes
- [Concepts](docs/04-concepts/) — connections, operators, actions, config, workflows, CI/CD, monitoring
- [Building pipelines](docs/05-building-pipelines/) — real patterns: operators, actions, dependencies, monitoring, backfill
- [Data Inspector](docs/10-reference/api/12-query.md) — (Experimental Preview) `inspect_data` MCP tool + REST endpoint for read-only queries across any catalog connection; primary use is AI-driven post-task verification; UI at `/query` is a debug surface for engineers
- [Production deployment](deploy/README.md) — local blue-green zero-downtime deploys via `./blue-green-run.sh`: two-slot (blue/green) swap from Docker Hub images or local source, automatic rollback on failed health, graceful worker draining

---

## License

The LeastAction core is licensed under the [LeastAction Sustainable Use License](LICENSE.md) — free to self-host for internal use, source available.

Enterprise Edition features (RBAC, SSO/SAML, multi-user beyond 1) are governed by the [Enterprise Edition License](LICENSE_EE.md) and require a commercial license from LeastAction Labs, Inc.

For licensing inquiries: [leastactionlabs.com/contact](https://leastactionlabs.com/contact)
