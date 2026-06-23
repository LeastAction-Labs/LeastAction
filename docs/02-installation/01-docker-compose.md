# Install with Docker Compose (development & testing)

LeastAction is self-hosted and ships as Docker images (backend, frontend) plus infra (MongoDB, Redis, PostgreSQL, Keto). There are two install paths:

| Path | Use it for | This page |
|------|-----------|-----------|
| **Docker Compose** | Development & testing | ← you are here |
| **Blue-Green** | Production / self-hosting | [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green) |

## Requirements
- Docker (>= 24) + Docker Compose v2
- A free port **8080** (the app's entry point)

## Install

From the repo root:

```bash
git clone https://github.com/LeastAction-Labs/LeastAction.git
cd LeastAction

# First time — build images and start
docker compose up -d --build

# Subsequent starts — reuse already-built images
docker compose up -d
```

`--build` compiles the `backend` and `frontend` images locally; the Celery workers reuse the backend image by tag. Pass `--build` again any time you pull new source changes.

The app comes up at **<http://localhost:8080>** (default login `admin@example.com` or username `admin123` / password `admin123`). The first run also runs the **setup helper**, which creates the root user, loads the bootstrap catalog (operators, connections, configs, skills, usecases), and bundles a **dbt** runner plus a **`postgres-demo`** database. On a fresh install it seeds a demo Postgres workflow that **starts running on its own within ~3 minutes** — see the [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart).

| Port | URL | What's there |
|------|-----|--------------|
| 8080 | http://localhost:8080 | UI, REST API (`/api/`), MCP endpoint (`/mcp/`) |
| 5555 | http://localhost:5555 | Flower — Celery worker monitor |

## Scale workers

Every Celery queue is its own service — all of them can be scaled with `--scale`, individually or together:

```bash
docker compose up -d --scale celery-task-worker=3 \
                     --scale celery-action-worker=2 \
                     --scale celery-cron-worker=2
```

## Stop

```bash
docker compose down       # stop
docker compose down -v    # stop and wipe all data
```

## Configure

Copy `deploy/.env.example` to `deploy/.env` to override defaults (image repo, root login, public URL, host port, drain/health timeouts). Everything works with no `.env` at all. See [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration).

## Going to production?

Use the blue-green deploy for zero-downtime, self-hosted production — it runs two slots and switches traffic only when the new one is healthy. (It also can't run at the same time as the compose stack, since both use port 8080.) See [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green).

## Next
- [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration) — `system.yml`, secrets, environment knobs.
- [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart) — run your first task.
