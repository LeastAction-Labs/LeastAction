# Install with Docker

LeastAction is self-hosted and ships as Docker images (backend, frontend) plus infra (MongoDB, Redis, PostgreSQL, Keto). The repo includes a one-command installer that brings the whole stack up.

## Requirements
- Docker + Docker Compose
- A free port **8080** (the app's entry point)

## Recommended: one-command install

From the repo root:

```bash
# First install — brings up infra + app + frontend (zero-downtime blue/green stack)
./blue-green-run.sh --fresh

# Build images from local source instead of pulling from Docker Hub
./blue-green-run.sh --fresh --build
```

The app comes up at **<http://localhost:8080>** (default login `admin@example.com` / `admin123`). The first run also runs the **setup helper**, which creates the root user and loads the bootstrap catalog (operators, connections, configs, skills, usecases).

Images are pulled from Docker Hub (`leastactionlabs/leastaction`, tags `backend` / `frontend`); if the repo isn't published, the script automatically builds from local source.

## Redeploy (zero downtime)

```bash
./blue-green-run.sh            # swaps blue <-> green; verifies health before switching traffic
./blue-green-run.sh --backend-only   # update backend/workers only
./blue-green-run.sh --frontend-only  # update frontend only
```

See [Production (Blue-Green)](/path?laui=getting-started-02-installation-03-production-blue-green&itemtype=doc.file&itemname=Production%20Blue%20Green) for the full flag list, rollback, and how the deploy works.

## Local development

The repo's root `docker-compose.yml` is the development flow (also on port 8080 — it can't run at the same time as the blue/green deploy; the script detects the conflict and tells you what to stop). Use the blue/green installer above for the simplest "just run it" experience.

## Configure

Copy `deploy/.env.example` to `deploy/.env` to override defaults (image repo, root login, public URL, host port, drain/health timeouts). Everything works with no `.env` at all. See [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration).

## Next
- [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration) — `system.yml`, secrets, environment knobs.
- [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart) — run your first task.
