# Production Deploys (Blue-Green)

`blue-green-run.sh` (repo root) installs and redeploys LeastAction on a single machine with Docker, **zero downtime**. The app runs in one of two slots (`blue` / `green`); each deploy brings the inactive slot up next to the active one, switches traffic only after the new backend is verified healthy, and drains the old slot's in-flight work before removing it. If the new slot fails to come up, the active one keeps serving.

> The canonical, always-current reference is [`deploy/README.md`](../../deploy/README.md) in the repo. This page summarizes it.

## Commands

```bash
./blue-green-run.sh --fresh            # first install (data volumes kept)
./blue-green-run.sh                     # redeploy, zero downtime (swap blue <-> green)
./blue-green-run.sh --build             # build images from local source
```

| Flag | Effect |
|---|---|
| `--build` | Build images from local source (skip the pull). |
| `--fresh` | Tear down existing deployment first, install from scratch (volumes kept). |
| `--delete-volumes` | With `--fresh`, also delete data volumes. **Destroys all data.** |
| `--backend-only` | Swap the backend/workers slot only. |
| `--frontend-only` | Update only the frontend image (brief blip). |

## How it works

Three Docker Compose projects share one network:

1. **`leastaction-infra`** — MongoDB, Redis, PostgreSQL, Keto, one-time JWT key gen. Owns the shared volumes; untouched by redeploys.
2. **`leastaction-blue` / `leastaction-green`** — the app slots: backend, three Celery workers (cron, task, action), change streamers, the setup helper, and (optional) Flower.
3. **`leastaction-edge`** — the stable frontend nginx on port 8080; its config is rewritten + reloaded to switch traffic atomically.

A deploy: ensure infra healthy → acquire images → start the inactive slot and wait for its backend healthcheck → switch nginx to the new backend and verify end-to-end → run setup-helper + workers → record the active slot → drain the old slot (hard-kill cron worker, gracefully drain task then action workers) → remove it. Any failure rolls back to the old slot automatically.

## Rollback

A failed deploy rolls back automatically. After a *successful* deploy the previous slot's image is kept, so you can roll back one step by redeploying.

## Caveats

- The root `docker-compose.yml` dev flow and this deploy can't run at once (both want port 8080).
- In-flight tasks that outlive `LEASTACTION_DRAIN_TIMEOUT` (default 600s) are killed unless `LEASTACTION_DRAIN_HARD_KILL=0`. Raise the timeout for long tasks.
- The DB schema is shared between slots during the overlap — keep migrations backward-compatible with the previous release.

See [`deploy/README.md`](../../deploy/README.md) for the full step-by-step, the files in `deploy/`, and all `.env` knobs.
