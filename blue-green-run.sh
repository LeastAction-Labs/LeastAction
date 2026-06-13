#!/usr/bin/env bash
# ============================================================================
# Local blue-green deploy for LeastAction. See deploy/README.md.
#
#   ./blue-green-run.sh --fresh         first install
#   ./blue-green-run.sh                 zero-downtime redeploy (blue<->green)
#   ./blue-green-run.sh --build         deploy from local source
#
# How it works: shared infra (mongo/redis/postgres/keto) runs once as project
# leastaction-infra. The app runs in one of two slots — leastaction-blue / leastaction-green. Each deploy
# brings the *inactive* slot up next to the active one, waits for it to be
# healthy, repoints the stable edge nginx (leastaction-frontend, port 8080) at it with a
# config reload, then drains and removes the old slot. If the new slot never
# becomes healthy, it is torn down and the active slot keeps serving.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY="$ROOT/deploy"
STATE_FILE="$DEPLOY/.deploy_state"   # holds the active slot: "blue" or "green"
RUNTIME="$DEPLOY/.runtime"

INFRA_FILE="$DEPLOY/docker-compose.infra.yml"
APP_FILE="$DEPLOY/docker-compose.app.yml"
EDGE_FILE="$DEPLOY/docker-compose.frontend.yml"

# Optional config — every var has a default below.
if [ -f "$DEPLOY/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$DEPLOY/.env"
    set +a
fi

: "${LEASTACTION_IMAGE_REPO:=leastactionlabs/leastaction}"
: "${LEASTACTION_HTTP_PORT:=8080}"
: "${LEASTACTION_DRAIN_TIMEOUT:=600}"
: "${LEASTACTION_DRAIN_HARD_KILL:=1}"
: "${LEASTACTION_HEALTH_TIMEOUT:=300}"
: "${LEASTACTION_ENABLE_FLOWER:=0}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

log()   { echo -e "${GREEN}[deploy]${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $1"; }
err()   { echo -e "${RED}[error]${NC} $1" >&2; exit 1; }
phase() { echo -e "\n${BOLD}═══ $1 ═══${NC}"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

  (no flags)          Zero-downtime redeploy: bring up the inactive slot
                      (blue<->green), switch traffic, drain the old slot.
                      Pulls ${LEASTACTION_IMAGE_REPO}:backend / :frontend, falling back
                      to building from source if the repo isn't published yet
  --build             Build images from local source (skip the pull attempt)
  --fresh             Fresh install: tear everything down first, start on blue
  --delete-volumes    With --fresh: also wipe all data volumes (DESTROYS DATA)
  --backend-only      Skip the frontend image; swap the backend slot only
  --frontend-only     Update only the frontend image; no slot swap
  --help              Show this help

Configuration is read from deploy/.env if present (see deploy/.env.example).
EOF
}

FRESH_INSTALL=false
DELETE_VOLUMES=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
BUILD_FROM_SOURCE=false

while [ $# -gt 0 ]; do
    case "$1" in
        --build)          BUILD_FROM_SOURCE=true ;;
        --fresh)          FRESH_INSTALL=true ;;
        --delete-volumes) DELETE_VOLUMES=true ;;
        --backend-only)   BACKEND_ONLY=true ;;
        --frontend-only)  FRONTEND_ONLY=true ;;
        --help|-h)        usage; exit 0 ;;
        *)                err "Unknown option: $1 (see --help)" ;;
    esac
    shift
done

[ "$BACKEND_ONLY" = true ] && [ "$FRONTEND_ONLY" = true ] && err "--backend-only and --frontend-only are mutually exclusive"
[ "$DELETE_VOLUMES" = true ] && [ "$FRESH_INSTALL" = false ] && err "--delete-volumes only makes sense with --fresh"

# ── helpers ─────────────────────────────────────────────────────────────────

other_slot() { [ "$1" = "blue" ] && echo "green" || echo "blue"; }

# Run docker compose against an app slot ("blue"/"green"). LEASTACTION_SLOT must be set
# even for stop/down — compose validates ${LEASTACTION_SLOT:?} regardless of subcommand.
app_compose() {
    local slot="$1"; shift
    LEASTACTION_SLOT="$slot" docker compose -f "$APP_FILE" -p "leastaction-$slot" "$@"
}

infra_compose() { docker compose -f "$INFRA_FILE" -p leastaction-infra "$@"; }
edge_compose()  { docker compose -f "$EDGE_FILE" -p leastaction-edge "$@"; }

wait_healthy() {
    local name="$1" timeout="$2" waited=0 status
    until status=$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null) \
          && [ "$status" = "healthy" ]; do
        if [ "$waited" -ge "$timeout" ]; then
            return 1
        fi
        sleep 3
        waited=$((waited + 3))
    done
}

wait_exited_ok() {
    local name="$1" timeout="$2" waited=0 status code
    while true; do
        status=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo "")
        if [ "$status" = "exited" ]; then
            code=$(docker inspect -f '{{.State.ExitCode}}' "$name" 2>/dev/null || echo "")
            [ "$code" = "0" ] && return 0
            return 1   # exited non-zero — fail fast, don't wait out the timeout
        fi
        if [ "$waited" -ge "$timeout" ]; then
            return 1
        fi
        sleep 3
        waited=$((waited + 3))
    done
}

write_nginx_conf() {
    local slot="$1"
    # `mkdir -p` should be a no-op on an existing dir, but on WSL's /mnt drvfs
    # it can fail with "File exists" — so only create it when missing.
    [ -d "$RUNTIME/nginx" ] || mkdir -p "$RUNTIME/nginx"
    sed "s/__BACKEND_HOST__/leastaction-${slot}-backend/g" \
        "$DEPLOY/nginx.template.conf" > "$RUNTIME/nginx/default.conf"
}

reload_edge_nginx() {
    docker exec leastaction-frontend nginx -t >/dev/null 2>&1 || err "Generated nginx config is invalid (deploy/.runtime/nginx/default.conf)"
    docker exec leastaction-frontend nginx -s reload
}

verify_edge() {
    local attempts="${1:-10}"
    for _ in $(seq 1 "$attempts"); do
        if curl -fsS -o /dev/null "http://localhost:${LEASTACTION_HTTP_PORT}/api/v1/health" 2>/dev/null; then
            return 0
        fi
        sleep 2
    done
    return 1
}

build_backend_image() {
    local slot="$1"
    cd "$ROOT"
    log "Building backend image from source..."
    docker build -f backend/Dockerfile -t "leastaction-backend:$slot" . || err "Backend build failed"
}

build_frontend_image() {
    cd "$ROOT"
    log "Building frontend image from source..."
    docker build \
        ${VITE_MARKETPLACE_BACKEND_URL:+--build-arg VITE_MARKETPLACE_BACKEND_URL="$VITE_MARKETPLACE_BACKEND_URL"} \
        -f frontend/Dockerfile \
        -t leastaction-frontend:latest \
        . || err "Frontend build failed"
}

# Pull an image; if the repo/tag isn't published yet, fall back to building
# from source. Network/auth failures stay fatal so real problems aren't masked.
# Returns 0 if pulled (caller should pin/tag it), 1 if built from source
# (the build helper already tagged the image).
#   pull_or_build <image-ref> <build-fn> [build-args...]
pull_or_build() {
    local ref="$1"; shift
    local out
    log "Pulling ${ref}..."
    if out=$(docker pull "$ref" 2>&1); then
        return 0
    fi
    echo "$out" >&2
    if echo "$out" | grep -qiE "manifest unknown|not found|no such manifest|repository does not exist"; then
        warn "${ref} is not published — building from source instead (pass --build to skip the pull attempt)."
        "$@"
        return 1
    fi
    err "Failed to pull ${ref} (see error above)"
}

# Acquire the backend (pinned to the target slot) and, unless --backend-only,
# the frontend image.
acquire_images() {
    local slot="$1"
    phase "Acquiring Images"
    cd "$ROOT"

    local need_frontend=false
    if [ "$BACKEND_ONLY" = false ] || ! docker image inspect leastaction-frontend:latest >/dev/null 2>&1; then
        need_frontend=true
    fi

    if [ "$BUILD_FROM_SOURCE" = true ]; then
        build_backend_image "$slot"
        [ "$need_frontend" = true ] && build_frontend_image
        return
    fi

    # Pin the pulled backend to this slot's tag so the two slots stay distinct
    # and the old slot's image survives for rollback.
    if pull_or_build "${LEASTACTION_IMAGE_REPO}:backend" build_backend_image "$slot"; then
        docker tag "${LEASTACTION_IMAGE_REPO}:backend" "leastaction-backend:$slot"
    fi

    if [ "$need_frontend" = true ]; then
        if pull_or_build "${LEASTACTION_IMAGE_REPO}:frontend" build_frontend_image; then
            docker tag "${LEASTACTION_IMAGE_REPO}:frontend" leastaction-frontend:latest
        fi
    fi
}

acquire_frontend_image() {
    phase "Acquiring Frontend Image"
    cd "$ROOT"
    if [ "$BUILD_FROM_SOURCE" = true ]; then
        build_frontend_image
        return
    fi
    if pull_or_build "${LEASTACTION_IMAGE_REPO}:frontend" build_frontend_image; then
        docker tag "${LEASTACTION_IMAGE_REPO}:frontend" leastaction-frontend:latest
    fi
}

preflight() {
    command -v docker >/dev/null 2>&1 || err "docker is not installed or not on PATH"
    docker info >/dev/null 2>&1 || err "docker daemon is not running"

    # Another stack (e.g. the root docker-compose.yml dev flow) already on our port?
    local holder
    holder=$(docker ps --filter "publish=${LEASTACTION_HTTP_PORT}" --format '{{.Names}}' | grep -v '^leastaction-frontend$' || true)
    if [ -n "$holder" ]; then
        err "Port ${LEASTACTION_HTTP_PORT} is already used by container(s): ${holder}. If this is the dev stack from the root docker-compose.yml, stop it first: docker compose -p leastaction down"
    fi
}

start_infra() {
    phase "Starting Infrastructure"
    # Shared by both slots but mounted by no infra service, so compose won't
    # create it on its own.
    docker volume create leastaction_logs >/dev/null
    infra_compose up -d
    log "Waiting for mongodb..."
    wait_healthy leastaction-infra-mongodb-1 180 || err "mongodb did not become healthy (docker logs leastaction-infra-mongodb-1)"
    log "Waiting for keto..."
    wait_healthy leastaction-infra-keto-1 180 || err "keto did not become healthy (docker logs leastaction-infra-keto-1)"
    log "Waiting for key generation..."
    wait_exited_ok leastaction-infra-key-init-1 120 || err "key-init did not complete (docker logs leastaction-infra-key-init-1)"
    log "Infrastructure is ready"
}

# SIGTERM a worker (Celery warm shutdown: finish in-flight tasks, accept no
# new ones) and wait for it to exit. With LEASTACTION_DRAIN_HARD_KILL=1, SIGKILL it
# after LEASTACTION_DRAIN_TIMEOUT; with =0, wait indefinitely, warning every 60s.
drain_worker_soft() {
    local slot="$1" worker="$2"
    local cname="leastaction-${slot}-${worker}-1"

    docker inspect "$cname" >/dev/null 2>&1 || return 0

    log "Draining ${worker} gracefully (SIGTERM)..."
    docker kill --signal=SIGTERM "$cname" 2>/dev/null || true

    local waited=0
    while docker inspect -f '{{.State.Running}}' "$cname" 2>/dev/null | grep -q true; do
        if [ "$waited" -ge "$LEASTACTION_DRAIN_TIMEOUT" ]; then
            if [ "$LEASTACTION_DRAIN_HARD_KILL" = "1" ]; then
                warn "${worker} still draining after ${LEASTACTION_DRAIN_TIMEOUT}s — hard killing (in-flight tasks lost). Raise LEASTACTION_DRAIN_TIMEOUT or set LEASTACTION_DRAIN_HARD_KILL=0 in deploy/.env."
                docker kill "$cname" 2>/dev/null || true
                break
            fi
            if [ $(( waited % 60 )) -lt 5 ]; then
                warn "Taking too long to close ${worker} (${waited}s) — still finishing in-flight tasks (LEASTACTION_DRAIN_HARD_KILL=0)..."
            fi
        fi
        sleep 5
        waited=$((waited + 5))
    done
    log "${worker} is down (after ${waited}s)"
}

drain_old() {
    local slot="$1"
    phase "Draining Old Slot ($slot)"

    # Stop the change-stream consumers quickly — both slots process the same
    # events while they overlap.
    app_compose "$slot" stop -t 10 db-change-streamer keto-access-writer 2>/dev/null || true

    # Cron worker first: hard kill (SIGKILL) so it stops firing scheduled work
    # immediately — its in-flight cron tick is sacrificed on purpose.
    log "Hard-killing old cron worker..."
    docker kill "leastaction-${slot}-celery-cron-worker-1" 2>/dev/null || true

    # Then drain the task and action workers gracefully, one at a time: SIGTERM
    # the task worker and wait for it to exit before touching the action worker.
    drain_worker_soft "$slot" celery-task-worker
    drain_worker_soft "$slot" celery-action-worker

    log "Removing old slot leastaction-$slot..."
    app_compose "$slot" down --remove-orphans
    log "Old slot removed (image leastaction-backend:$slot kept for rollback; run 'docker image prune' to reclaim space)"
}

teardown_everything() {
    phase "Tearing Down Existing Deployment"

    if [ "$DELETE_VOLUMES" = true ]; then
        warn "Deleting volumes — ALL DATA WILL BE LOST!"
    fi

    local slot
    for slot in blue green; do
        log "Removing leastaction-$slot..."
        app_compose "$slot" down --remove-orphans 2>/dev/null || true
    done

    edge_compose down --remove-orphans 2>/dev/null || true

    if [ "$DELETE_VOLUMES" = true ]; then
        infra_compose down --remove-orphans --volumes 2>/dev/null || true
        docker volume rm -f leastaction_mongodb_data leastaction_postgres_data leastaction_logs leastaction_keys 2>/dev/null || true
    else
        infra_compose down --remove-orphans 2>/dev/null || true
    fi

    # Best-effort: under WSL on a Windows drive (/mnt/...) the .runtime dir can
    # stay briefly locked by Docker Desktop after the edge stops, and it's
    # regenerated on the next deploy anyway, so don't let cleanup abort here.
    rm -f "$STATE_FILE" 2>/dev/null || true
    rm -rf "$RUNTIME" 2>/dev/null || rm -rf "$RUNTIME"/* 2>/dev/null || true
    log "Teardown complete"
}

deploy_frontend_only() {
    phase "Frontend-Only Deploy"
    [ -f "$STATE_FILE" ] || err "No existing deployment found — run a full deploy first"
    local active
    active=$(cat "$STATE_FILE")

    acquire_frontend_image
    write_nginx_conf "$active"

    log "Replacing frontend container (brief downtime)..."
    edge_compose up -d
    wait_healthy leastaction-frontend 60 || err "Frontend did not become healthy (docker logs leastaction-frontend)"
    verify_edge || err "Edge verification failed (curl http://localhost:${LEASTACTION_HTTP_PORT}/api/v1/health)"

    log "Frontend deploy complete — http://localhost:${LEASTACTION_HTTP_PORT}"
}

main_deploy() {
    local active new_slot
    active=$(cat "$STATE_FILE" 2>/dev/null || true)
    if [ -n "$active" ]; then
        new_slot=$(other_slot "$active")
    else
        new_slot=blue
    fi

    phase "Deploying to $new_slot$( [ -n "$active" ] && echo " (active: $active)" || true )"

    start_infra
    acquire_images "$new_slot"

    # Clear any leftover containers in the target slot (e.g. from a previous
    # failed deploy) so we start clean.
    app_compose "$new_slot" down --remove-orphans 2>/dev/null || true

    phase "Starting App Slot ($new_slot)"
    app_compose "$new_slot" up -d backend keto-access-writer db-change-streamer

    log "Waiting for backend to be healthy (up to ${LEASTACTION_HEALTH_TIMEOUT}s)..."
    if ! wait_healthy "leastaction-${new_slot}-backend" "$LEASTACTION_HEALTH_TIMEOUT"; then
        warn "New backend never became healthy. Logs:"
        docker logs "leastaction-${new_slot}-backend" --tail 50 2>&1 || true
        log "Tearing down failed slot leastaction-$new_slot — current slot keeps serving"
        app_compose "$new_slot" down --remove-orphans
        err "Deploy aborted: new backend unhealthy"
    fi
    log "New backend is healthy"

    # Switch traffic as soon as the backend is healthy — the edge depends only
    # on the backend healthcheck, not on setup. Setup and workers come up
    # afterwards (the old slot keeps handling tasks until it's drained).
    phase "Switching Traffic to $new_slot"
    write_nginx_conf "$new_slot"

    local edge_existed=false
    docker inspect leastaction-frontend >/dev/null 2>&1 && edge_existed=true
    edge_compose up -d
    wait_healthy leastaction-frontend 60 || err "Edge frontend did not become healthy (docker logs leastaction-frontend)"
    # `up -d` recreates the container only when its image changed; otherwise
    # the rewritten conf needs an explicit reload.
    if [ "$edge_existed" = true ]; then
        reload_edge_nginx
    fi

    if ! verify_edge; then
        if [ -n "$active" ]; then
            warn "Edge verification failed — switching traffic back to $active"
            write_nginx_conf "$active"
            reload_edge_nginx
        else
            edge_compose down 2>/dev/null || true
        fi
        app_compose "$new_slot" down --remove-orphans
        err "Deploy aborted: edge verification failed${active:+, $active restored}"
    fi
    log "Traffic switched to $new_slot"

    # Bring up setup-helper and the workers (all gate on backend health, not on
    # each other). Wait for setup to finish; on failure roll back to the old
    # slot (which is still running until drain).
    phase "Running Setup & Workers"
    app_compose "$new_slot" up -d

    log "Waiting for setup to complete..."
    if ! wait_exited_ok "leastaction-${new_slot}-setup-helper-1" "$LEASTACTION_HEALTH_TIMEOUT"; then
        warn "Setup did not complete successfully. Logs:"
        docker logs "leastaction-${new_slot}-setup-helper-1" --tail 50 2>&1 || true
        if [ -n "$active" ]; then
            warn "Switching traffic back to $active"
            write_nginx_conf "$active"
            reload_edge_nginx
        else
            edge_compose down 2>/dev/null || true
        fi
        log "Tearing down failed slot leastaction-$new_slot"
        app_compose "$new_slot" down --remove-orphans
        err "Deploy aborted: setup failed${active:+, $active restored}"
    fi
    log "Setup complete"

    echo "$new_slot" > "$STATE_FILE"

    if [ -n "$active" ]; then
        drain_old "$active"
    fi

    if [ "$LEASTACTION_ENABLE_FLOWER" = "1" ]; then
        log "Starting flower..."
        app_compose "$new_slot" --profile flower up -d flower
    fi

    phase "Deploy Complete"
    log "Slot:  $new_slot"
    log "App:   http://localhost:${LEASTACTION_HTTP_PORT}"
    if [ -z "$active" ]; then
        log "Login: ${ROOT_EMAIL:-admin@example.com} / ${ROOT_PASSWORD:-admin123}"
    fi
    log "Logs:  docker logs leastaction-${new_slot}-backend -f"
}

# A plain deploy assumes there is something running. If neither the infra stack
# nor an active slot exists, confirm the user actually wants a first-time
# install rather than silently creating one (catches typos like running the
# script on the wrong machine or after a manual teardown).
confirm_fresh_if_nothing_deployed() {
    local missing=""
    docker inspect leastaction-infra-mongodb-1 >/dev/null 2>&1 || missing="infra stack"
    if [ ! -f "$STATE_FILE" ]; then
        missing="${missing:+$missing and }active slot"
    fi
    [ -z "$missing" ] && return 0

    warn "No existing deployment detected ($missing not found)."
    if [ -t 0 ]; then
        local ans
        read -r -p "Run a fresh install instead? [y/N] " ans
        case "$ans" in
            y|Y|yes|YES) FRESH_INSTALL=true ;;
            *) err "Aborted. Run with --fresh for a first-time install." ;;
        esac
    else
        err "No existing deployment found. Run with --fresh for a first-time install."
    fi
}

main() {
    phase "LeastAction Blue-Green Deploy"
    preflight

    if [ "$FRONTEND_ONLY" = true ]; then
        deploy_frontend_only
        return
    fi

    if [ "$FRESH_INSTALL" = false ]; then
        confirm_fresh_if_nothing_deployed
    fi

    if [ "$FRESH_INSTALL" = true ]; then
        teardown_everything
    fi

    main_deploy
}

main
