# Blue-Green Deploys (local / self-hosted)

`blue-green-run.sh` (repo root) installs and redeploys LeastAction on a single
machine with Docker, with **zero downtime**: the app runs in one of two slots
(`blue` / `green`); each deploy brings the inactive slot up next to the active
one, switches traffic only after the new backend is verified healthy, and lets
the old slot finish its in-flight work before being removed. If the new slot
fails to come up, the active one just keeps serving.

## Quick start

```bash
# First install
./blue-green-run.sh --fresh

# Redeploy — zero downtime (swaps blue <-> green)
./blue-green-run.sh

# Developers: build images from local source instead of pulling
./blue-green-run.sh --fresh --build
./blue-green-run.sh --build
```

The app comes up at <http://localhost:8080> (default login
`admin@example.com` / `admin123` — override via `deploy/.env`).

> Images are pulled from Docker Hub
> ([leastactionlabs/leastaction](https://hub.docker.com/r/leastactionlabs/leastaction),
> tags `backend` / `frontend`). If the repo isn't published yet, the script
> warns and builds from the local source tree automatically — so it works out
> of the box before any image is pushed.

## Flags

| Flag | Effect |
|---|---|
| `--build` | Build the images from the local source tree (skip the pull attempt). |
| `--fresh` | Tear down any existing deployment first and install from scratch (data volumes are kept). |
| `--delete-volumes` | With `--fresh`: also delete all data volumes. **Destroys all data.** |
| `--backend-only` | Swap the backend/workers slot only; skip the frontend image. |
| `--frontend-only` | Update only the frontend image (brief blip); no slot swap. |

## Configuration

Copy [.env.example](.env.example) to `deploy/.env` to override defaults —
image repo, root login, public URL, host port (`LEASTACTION_HTTP_PORT`), drain/health
timeouts, flower, etc. Everything works with no `.env` at all.

## How it works

```
Browser ──► leastaction-frontend :8080   (project leastaction-edge — stable entry point)
                 │   nginx conf rewritten + reloaded on each deploy
                 ▼
        leastaction-green-backend :8000        leastaction-blue-backend   (old — drained, removed)
        (project leastaction-green)            (project leastaction-blue)
                 │
        project leastaction-infra: mongodb · redis · postgres · keto · key-init
        shared: network leastaction_network, volumes leastaction_mongodb_data / leastaction_postgres_data
                / leastaction_logs / leastaction_keys
```

Three kinds of compose projects share one Docker network:

1. **`leastaction-infra`** ([docker-compose.infra.yml](docker-compose.infra.yml)) —
   databases, keto, and the one-time JWT key generation. Started once,
   untouched by redeploys. Owns the shared volumes, so slots come and go
   without touching data.
2. **`leastaction-blue` / `leastaction-green`** ([docker-compose.app.yml](docker-compose.app.yml)) —
   the app slots (only one active at a time, both briefly up during a swap):
   backend, three celery workers, change streamers, the one-shot setup helper,
   and (profile-gated) flower. The backend gets a predictable container name
   (`leastaction-<slot>-backend`) that the edge nginx targets.
3. **`leastaction-edge`** ([docker-compose.frontend.yml](docker-compose.frontend.yml)) —
   the stable frontend nginx on port 8080. Its config is bind-mounted from
   `deploy/.runtime/nginx/` so the script can rewrite it and `nginx -s reload`
   to switch traffic atomically.

A deploy runs through these steps:

1. Ensure infra is up and healthy (no-op after the first run).
2. Acquire images: pull `backend` / `frontend` from Docker Hub and pin the
   backend locally as `leastaction-backend:<slot>` (or `docker build` with `--build`,
   or automatically build if the repo isn't published yet).
3. Start the inactive slot alongside the active one (backend + streamers) and
   wait for its backend healthcheck. **If it never turns healthy, the new
   slot is removed and the active slot keeps serving (exit 1).**
4. Switch traffic: rewrite the edge nginx config to point at
   `leastaction-<slot>-backend`, reload nginx, and verify end-to-end through port 8080.
   The edge depends only on the backend healthcheck, not on setup — so traffic
   moves as soon as the new backend is healthy. On failure the config is
   switched back to the old slot and the new slot removed.
5. Bring up `setup-helper` (root user, onboarding catalog) and the celery
   workers — all gate on backend health, not on each other — and wait for
   setup to finish. **If setup fails, traffic is switched back to the old slot
   (still running until drained) and the new slot removed.**
6. Record the now-active slot in `deploy/.deploy_state`.
7. Drain the old slot's workers in order: **hard-kill the cron worker** (so it
   stops firing scheduled work immediately), then **gracefully drain the task
   worker** (SIGTERM, wait for it to finish in-flight tasks), then the
   **action worker** the same way. Each graceful worker gets up to
   `LEASTACTION_DRAIN_TIMEOUT` (default 600s); with `LEASTACTION_DRAIN_HARD_KILL=1` (default)
   it is killed after that, with `=0` the deploy waits indefinitely. Then the
   old slot is removed. The old slot's image `leastaction-backend:<old-slot>` is kept
   for rollback; `docker image prune` reclaims the space.

## Rollback

A failed deploy rolls back automatically (steps 3/4/5 above). After a
*successful* deploy, the previous slot's image (`leastaction-backend:blue` or
`leastaction-backend:green`) is kept, so you can roll back one step by redeploying —
the swap brings the previous slot back with the same zero-downtime flow.

## Files in this directory

| File | Purpose |
|---|---|
| `docker-compose.infra.yml` | Shared infra project (`leastaction-infra`) |
| `docker-compose.app.yml` | App slot stack (`leastaction-blue` / `leastaction-green`) |
| `docker-compose.frontend.yml` | Stable edge frontend (`leastaction-edge`) |
| `nginx.template.conf` | Edge nginx config; `__BACKEND_HOST__` substituted per deploy |
| `.env.example` | All supported configuration knobs |
| `.runtime/` *(generated)* | Live nginx config mounted into the edge container |
| `.deploy_state` *(generated)* | The active slot (`blue` or `green`) |

## Notes & caveats

- The root `docker-compose.yml` dev flow and this deploy flow can't run at
  the same time (both want port 8080). The script detects this and tells you
  what to stop.
- Both slots' celery workers briefly consume from the same queues during the
  swap — that's by design; tasks are processed exactly once either way.
- In-flight tasks that outlive `LEASTACTION_DRAIN_TIMEOUT` (default 600s) are killed
  and lost (Celery `acks_late` is off). Raise the timeout in `deploy/.env` if
  you run long tasks, or set `LEASTACTION_DRAIN_HARD_KILL=0` to never kill — the
  deploy then waits for the old workers indefinitely, warning every 60s that
  the previous slot is taking too long to close.
- Database schema is shared between slots during the overlap, so releases
  should keep migrations backward-compatible with the previous one.
