# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
skill = {
    "description": "Data engineer scale evaluation for LeastAction — 200 tasks across 5 Bronze-to-Serving workflows, mixed operators (Dummy + PostgresqlExecuteSQL), partition-aware dependency chains on ALL non-root tasks, backfill simulation, intentional error detection and self-fix, config/parameter injection verification, and 4 weekly Sunday notification tasks with webhook post-action. Use this when a data engineer wants to stress-test or evaluate LeastAction at org scale via MCP.",
    "content": """
# LeastAction Scale Evaluation — Data Engineer Guide

## Context

Evaluate LeastAction for org-wide adoption at scale using MCP tools only. Tests real data engineering workflows: layered pipelines, partitioned tasks, dependency chains, backfill, adhoc reruns, intentional error detection + fix, and config/parameter passing.

**Key platform facts:**
- Task PK = `name + project_laui + account_laui + partition` — same name + partition + parent in `create_catalog_item` overwrites in place (version increments). **Overwriting without the `actions` field silently wipes pre/post_actions.**
- Pre-actions and post-actions are stored as `actions.pre_actions` / `actions.post_actions` — passing them as top-level keys in `extra_fields` is silently discarded; always nest inside `actions: {}`
- Each pre/post action entry **must include a `laui` field** (catalog LAUI of the action, not marketplace LAUI); omitting it causes `Field required` error
- Marketplace operator/action LAUIs cannot be used directly — must create a catalog copy first via `create_catalog_item`
- `LeastActionDummy` — configurable `delay_seconds`, no real DB needed
- `PostgresqlExecuteSQL` — executes non-SELECT SQL via psycopg2; **payload must be a raw SQL string, not `{"sql": "..."}` dict**; template variables in table names are not safe (use static table names)
- `update_task` only supports: `state`, `user_set_state`, `logical_date`, `priority`, `duration` — it silently ignores `start_date`, `total_retries`, `retry_interval`; use `create_catalog_item` overwrite for those fields
- `get_task_history` filters by **logical date**, not wall-clock run date — always pass `date_from` matching the task's `start_date` or the logical date you're looking for

**Scheduling model (two independent clocks):**

| Field | Meaning | Advances on success |
|---|---|---|
| `logical_date` | Data epoch the task processes — injected as `{{ logical_date }}` in payload | `croniter(frequency, logical_date).get_next()` |
| `next_run_date` | Wall-clock trigger — scheduler fires when `next_run_date ≤ now` | one cron interval from previous `next_run_date` |

Both start equal to `start_date`. On success both advance by one cron step. Because `next_run_date` advances from the *previous* `next_run_date` (not from physical run time), if `next_run_date` is in the past (backfill scenario), the scheduler immediately dispatches the next run after each success — catching up one logical slot per consecutive run — until `next_run_date > UTC now`.

---

## Before Running This Test — Ask the User

**Required inputs before starting any phase:**

1. **Webhook URL** (for Phase E notification tasks):
   > "What webhook URL should the weekly notification tasks POST to? (e.g. a Slack incoming webhook or custom endpoint)"
   Store as `webhook_url`. This will be used in post_actions for the 4 weekly summary tasks.

Do NOT proceed to Phase E without collecting this. Phases 0–D can run without it.

---

## Phase 0: Scaffolding

### 0.0 — Capture project_laui and account_laui (do this first, before anything else)

```
get_root_items() → find the item with item_type="folder.project" → store its laui as project_laui
get_root_items() → find the item with item_type="folder.account" → store its laui as account_laui
```

Both values are required on every task. `project_laui` must be the `folder.project` laui — NOT the workflow folder laui. `account_laui` is the `folder.account` laui at the root level. If either is wrong, tasks are created silently but the scheduler will never pick them up.

### 0.1 — Operators (two, from marketplace)

> **⚠️ Marketplace LAUIs cannot be used directly as `operator_laui` in task creation.** You must create a catalog copy first. Using a marketplace LAUI directly returns "Operator item not found" at task creation time.

**For each operator:**
1. `search_marketplace(name="LeastActionDummy")` → get marketplace LAUI
2. `get_marketplace_item(item_laui=<marketplace_laui>)` → read the full item (codeblock, bashblock, payload contract)
3. `create_catalog_item(...)` using the data from step 2 → store the resulting **catalog** LAUI as `dummy_operator_laui`

Repeat for `PostgresqlExecuteSQL` → store catalog LAUI as `pg_operator_laui`.

The canonical PostgresqlExecuteSQL payload is a **raw SQL string** — not a dict. Creating a task with `{"sql": "..."}` fails silently at `extracting_payload` with `500 Failed to run operator` and no error log line.

### 0.2 — Connections (two)

**Connection 1 — Dummy (for LeastActionDummy tasks):**

> **⚠️ Connection schema:** `host`/`port`/`timeout` must go inside `content: {}`, not top-level. `max_parallelism` is top-level.

```json
{
  "content": { "host": "dummy", "port": 0, "timeout": 30 },
  "max_parallelism": 20
}
```
Name: `stress_dummy_connection`. Pass these as `extra_fields` in `create_catalog_item`.

**Connection 2 — PostgresPlus (for PostgresqlExecuteSQL tasks):**
Use the existing `PostgresqlPlusClaude` connection in the catalog:
```
search_catalog(name="PostgresqlPlusClaude", item_type="connection")
```

### 0.3 — 5 workflow folders (Bronze → Serving stack)
| # | Name | Layer |
|---|---|---|
| 1 | `wf_ingest` | Bronze — raw ingestion |
| 2 | `wf_transform` | Silver — cleaning/joins |
| 3 | `wf_validate` | Gold — quality checks |
| 4 | `wf_load` | Gold — warehouse load |
| 5 | `wf_report` | Serving — reports/exports |

### 0.4 — Shared config with parameters

> **⚠️ Config schema:** requires `config_type: "task"` (enum) and parameters nested inside `content: {parameters: {...}}`. Passing bare `parameters` at the top level is rejected.

Create a catalog config item named `stress_test_config`:
```json
{
  "config_type": "task",
  "content": {
    "parameters": {
      "batch_size": 1000,
      "env": "stress_test",
      "team": "data_engineering"
    }
  }
}
```
Pass as `extra_fields` in `create_catalog_item`. Attach to ~50 tasks (all wf_ingest + 10 from wf_transform) via `attached_config_lauis: [<config_laui>]` at task creation time.

> `total_retries` and `retry_interval` are direct task fields — set them at `create_catalog_item` time, **not** in config and **not** via `update_task` (silently ignored).

### 0.5 — Locate dependency pre-action

> **⚠️ Critical — do not skip or reuse from another project.** The `laui` field in every `pre_actions` entry must be a valid action item in the catalog. If you skip this step or use a stale laui, all dependency chains will silently fail (pre-action never fires, child runs without waiting for parent).

Search within the catalog **of the current project** being tested:
```
search_catalog(name="LeastActionCheckIfParentsAreDone", item_type="action") → store LAUI as parents_done_laui
```
If the search returns multiple results (one per project), pick the one whose `pk` contains the current project's connection/action folder laui. If none found in the target project, the action is shared at the account level — use the first result but verify it resolves correctly by checking `get_catalog_item(laui)`.

### 0.6 — Locate webhook post-action

```
search_marketplace(name="webhook") → look for a POST/HTTP webhook action → store marketplace LAUI
```
If not found in marketplace, try:
```
search_catalog(name="webhook", item_type="action")
```

> **⚠️ Post-actions require a catalog LAUI, not a marketplace LAUI.** If the action is found only in the marketplace, import it via `create_catalog_item` before Phase E (same pattern as operators in 0.1). Store the resulting catalog LAUI as `webhook_action_laui`.

Read the action schema to understand the required `action_variables`:
```
get_catalog_item(item_laui=<webhook_action_laui>) → read payload/variables format
```

---

## Phase A: 200 Tasks — Mixed Operators

> **⚠️ CRITICAL — Read before creating any task.**
>
> Every task's `project_laui` field must be the **`folder.project` laui** — the root workspace item — NOT the `folder.workflow` laui of `wf_ingest`, `wf_transform`, etc.
>
> **Why this matters:** The scheduler's MongoDB query does an exact `project_laui` match. If you pass the workflow-folder laui (which sits one level below the project), the tasks are created successfully but the scheduler will **never pick them up**. You get `Picked up 0 task(s): []` in cron logs with no error — a silent failure with no recovery path short of recreating every task.
>
> **How to get the correct `project_laui` (do this once at Phase 0):**
> ```
> get_root_items() → find the item with item_type="folder.project" for this workspace
> ```
> Store it as `project_laui`. Use this exact value in `extra_fields.project_laui` on every `create_catalog_item` call in Phase A.
>
> **Verification:** After creating your first task (e.g. the first `wf_ingest` task), call `get_catalog_item(task_laui)` and confirm its `project_laui` matches the `folder.project` laui. If it contains the workflow-folder laui instead, stop and recreate with the correct value before continuing. Every subsequent task will have the same bug.
>
> **What NOT to use as `project_laui`:**
> - The `parent_laui` of the task (that's the workflow folder laui)
> - The laui returned by `search_catalog(name="wf_ingest")` or any `folder.workflow` item
> - Any laui from `get_children` of the project that has `item_type="folder.workflow"`

**4 partitions × 10 names × 5 workflows = 200 tasks**

### Partitions
`REGION_US`, `REGION_EU`, `REGION_APAC`, `GLOBAL`

### Operator assignment
- **LeastActionDummy (170 tasks):** all tasks in `wf_ingest`, `wf_transform`, `wf_validate`, `wf_report`
- **PostgresqlExecuteSQL (30 tasks):** all `wf_load` tasks for REGION_US, REGION_EU, REGION_APAC (GLOBAL in wf_load → Dummy)

### Task names per workflow (10 names each)
`orders, customers, products, inventory, events, sessions, returns, payments, logistics, suppliers`

Prefixed: `ingest_orders`, `transform_orders`, `validate_orders`, `load_orders`, `report_orders`

### Schedule (all 200 tasks)
```
frequency:  0 6 * * *
start_date: 2026-04-15
end_date:   2026-07-15
```

### Dependency Chains — Read This Before Creating Any Non-Root Task

> **⚠️ MANDATORY — not optional, not a sample. Every non-root task must have its dependency wired at creation time. Do not create tasks first and add pre-actions later. There is no deferred step. Missing pre-actions are silent — tasks run without waiting for parents and no error is raised.**

**Rule:**
- `wf_ingest` tasks = **roots** — no pre-actions for any partition including GLOBAL
- `wf_transform`, `wf_validate`, `wf_load`, `wf_report` for **REGION_US, REGION_EU, REGION_APAC** = must include pre-action at creation pointing to same-partition parent in the previous layer
- **GLOBAL** partition tasks in all non-ingest layers = **no pre-actions** (always runs independently)

**Per-layer parent mapping:**

| Task being created | Parent task_name | Pre-action required |
|---|---|---|
| `transform_<entity>` [REGION_X] | `ingest_<entity>` | YES |
| `validate_<entity>` [REGION_X] | `transform_<entity>` | YES |
| `load_<entity>` [REGION_X] | `validate_<entity>` | YES |
| `report_<entity>` [REGION_X] | `load_<entity>` | YES |
| ANY task [GLOBAL] | — | NO (never) |

**Pre-action format in `extra_fields` for `create_catalog_item`:**

> **⚠️ CRITICAL — field nesting.** Pre-actions are stored as `actions.pre_actions`. Passing `pre_actions` as a top-level key in `extra_fields` is silently discarded — the task creates with HTTP 200 but `actions` stays `{}`. Always nest under `actions`:

```json
{
  "actions": {
    "pre_actions": [{
      "laui": "<parents_done_laui from 0.5>",
      "name": "LeastActionCheckIfParentsAreDone",
      "action_variables": {
        "parents": [{
          "task_name": "<parent_task_name>",
          "project_laui": "{{ project_laui }}",
          "account_laui": "{{ account_laui }}",
          "partition": "{{ partition }}"
        }]
      }
    }]
  }
}
```

**Early verification gate — after task 1, before creating the rest:**
After creating your first non-root task, immediately verify:
```
get_catalog_item(task_laui) → actions.pre_actions must be non-empty
```
If `actions: {}`, stop and fix the format. One bad task costs one recreate. 120 bad tasks costs 120.

**Creation order (parent layers must exist before child layers):**
1. All `wf_ingest` — no pre-actions
2. All `wf_transform` — pre-actions for REGION_US/EU/APAC
3. All `wf_validate` — pre-actions for REGION_US/EU/APAC
4. All `wf_load` — pre-actions for REGION_US/EU/APAC
5. All `wf_report` — pre-actions for REGION_US/EU/APAC

### Payloads

**Dummy tasks** (verifies template variable resolution):
```json
{
  "message": "{{ env }} | {{ team }} | {{ partition }} | {{ logical_date }}",
  "operation": "{{ layer }}_{{ entity }}",
  "delay_seconds": 0.1,
  "async_mode": false
}
```
`{{ env }}` and `{{ team }}` come from config parameters — only resolve for tasks with `stress_test_config` attached. `{{ partition }}` and `{{ logical_date }}` resolve from runtime context for all tasks. Flag any unresolved `{{ }}` as a bug.

**PostgresqlExecuteSQL — correct (REGION_US + REGION_EU, 20 tasks):**

> **⚠️ Use static table names in SQL.** Template variables like `{{ logical_date }}` render as `2026-04-15T00:00:00` (colons) — invalid SQL identifier. `{{ ds_nodash }}` is NOT a supported variable in this platform — it causes UndefinedError at payload extraction. Use a static, partition-specific table name:

```sql
CREATE TABLE IF NOT EXISTS stress_load_region_us (
    id SERIAL PRIMARY KEY,
    region VARCHAR(50),
    loaded_at TIMESTAMP DEFAULT NOW()
);
```
For REGION_EU use `stress_load_region_eu`. Pass as a **raw SQL string** in `payload` — no wrapping dict.

**PostgresqlExecuteSQL — intentionally broken (REGION_APAC, 10 tasks):**
```sql
SELEC * FROM nonexistent_table;
```
`SELEC` (missing T) fails SQL validation in `_validate_sql_statement()`. This is the intentional error for AI to detect and fix.

**Verification after Phase A:** Spot-check one transform, one validate, one load, one report task — call `get_catalog_item` and confirm `actions.pre_actions` is non-empty. A missing pre-action means dependency tests in Phase B/E will produce false positives.

---

## Phase B: Adhoc Runs + Error Detection + Fix

### B.1 — Run 100 tasks adhoc
All 40 from `wf_ingest` + all 40 from `wf_transform` + 20 from `wf_validate`:
```
run_task(task_laui) × 100    ← store every session_id
```
**Never batch `create_catalog_item` and `run_task` as parallel tool calls.** Always await the create before calling run — a parallel dispatch may execute with the old payload before the write commits.

### B.2 — Verify template variable resolution
For 20 sampled Dummy sessions:
```
get_task_history(task_laui, date_from="2026-04-14") → session_id + prev_interval_start
get_task_logs(task_laui, session_id, date=YYYY-MM-DD)
```
> `get_task_history` filters by **logical date**, not wall-clock run date. Pass `date_from` at or before the task's `start_date` or logical date — not today's date.

Assert log `message` field contains:
- `stress_test` not `{{ env }}`
- `data_engineering` not `{{ team }}`
- `REGION_US` not `{{ partition }}`
- Actual date not `{{ logical_date }}`

### B.3 — Verify config scoping
Tasks with `stress_test_config` attached → log shows resolved `stress_test`, `data_engineering`.
Tasks without config (wf_validate) → `{{ env }}` stays unresolved — document the platform behavior.

### B.4 — Detect + fix REGION_APAC errors (1 cycle, no human)
```
get_task_history(task_laui, date_from="2026-04-14") for wf_load REGION_APAC → filter status="error"
get_task_logs(task_laui, session_id, date=...) → read error step + message
```

**If `get_task_logs` stops mid-step with no `level: error` line**, escalate to CELERY logs — this means an unhandled operator exception:
```
get_non_task_logs(session_id=<id>, category="CELERY")
```
CELERY logs contain the full Python traceback. They are indexed by logical date — if empty, pass `date` matching `prev_interval_start`.

AI fix flow:
1. Read error from logs — identify broken `SELEC *` payload
2. `get_catalog_item(task_laui)` → read current payload **and current `actions` field**
3. Fix: replace payload with valid `CREATE TABLE IF NOT EXISTS stress_load_region_apac (id SERIAL PRIMARY KEY, region VARCHAR(50), loaded_at TIMESTAMP DEFAULT NOW());` **as a raw SQL string**
4. `create_catalog_item` same name + parent (overwrites in place), **carrying forward the `actions` field from step 2** — overwriting without it silently wipes pre_actions
5. `run_task(task_laui)` → new session_id
6. `get_task_logs` → verify no `level: error`, status: success

**Success:** Logs clean after fix. AI detected and corrected in 1 `create_catalog_item` call.

### B.5 — Rerun for different date (20 tasks)
```
update_task(task_laui, updates={"logical_date": "2026-04-01"}) × 20
run_task(task_laui) × 20
get_task_logs(task_laui, session_id, date="2026-04-01")
```
Assert `logical_date` in logs = `2026-04-01T00:00:00`. New session_id distinct from B.1.

---

## Phase C: Backfill Simulation

### C.1 — Select 50 tasks
All 10 `ingest_*` × 4 partitions = 40, plus 10 from `wf_transform` REGION_US = 50 tasks.

### C.2 — Move start_date back via create_catalog_item overwrite

`update_task` silently ignores `start_date` — use `create_catalog_item` overwrite (same name + partition + parent):
```
create_catalog_item(name=<same>, partition=<same>, parent_laui=<same>, ..., start_date="2026-01-15") × 50
```

> **⚠️ Carry forward `actions` on every overwrite.** Overwriting a task without including the `actions` field silently wipes pre_actions. Always call `get_catalog_item(task_laui)` first, read the `actions` field, and include it verbatim in the overwrite call.

**Backfill catch-up behavior:** After the overwrite, `next_run_date` is reset to `start_date` (in the past). The scheduler immediately dispatches the first run at `logical_date=start_date`. On each success, `next_run_date` advances one cron interval from the *previous* `next_run_date` — which is still in the past — so the cron continues dispatching immediately after each success until `next_run_date > UTC now`. 121 days of backlog will run consecutively without waiting for the next wall-clock cycle.

**Alternative — single specific date (faster for targeted backfill):**
```
update_task(task_laui, updates={"logical_date": "2026-01-15"})
run_task(task_laui)
```
Sets `logical_date` to the target date and triggers the run now. `next_run_date` is unchanged — regular schedule continues.

### C.3 — Verify
```
get_task_history(task_laui, date_from="2026-01-15", date_to="2026-02-15")
```
Assert: `logical_date=2026-01-15T...` in oldest entry. `{{ logical_date }}` in log output resolves to `2026-01-15`. Ingest backfill precedes transform backfill for same logical_date (dependency ordering).

---

## Phase D: Config + Parameter Verification

### D.1 — Verify config parameter inheritance
```
get_catalog_item(task_laui) → confirm attached_config_lauis has stress_test_config
get_task_logs(task_laui, session_id, date=...) → log message contains stress_test, data_engineering
```

### D.2 — Verify tasks WITHOUT config
Tasks from `wf_validate` (no config) → payload `{{ env }}` stays unresolved — document platform behavior.

### D.3 — Retry task field test

`update_task` silently ignores `total_retries` and `retry_interval`. Use `create_catalog_item` overwrite:
```
create_catalog_item(name=<same>, ..., payload="<failing raw SQL>", total_retries=1, retry_interval=60)
```
Pick a failing payload that passes SQL type validation but fails at execution (e.g. `INSERT INTO nonexistent_table (id) VALUES (1);` — passes INSERT validation, fails at cursor.execute).

Run → verify:
- `get_task_history` shows 2 sessions for same logical_date with `retry_number` 0 → 1
- After exhaustion, task object shows `retry_number = total_retries + 1` (cosmetic quirk — `can_retry=false` is the authoritative signal)

Fix payload → confirm clean run.

---

## Phase E: Weekly Notification Tasks (4 tasks)

> **Prerequisite:** You must have collected `webhook_url` from the user before this phase. If not yet asked, ask now:
> "What webhook URL should I use for the weekly notification post-actions?"

Create 4 tasks — one per partition — that act as weekly pipeline health summaries. Each runs every Sunday, waits for the corresponding partition's `wf_report` layer to complete for the week, then fires a webhook notification as a post-action.

### E.1 — Task definitions

| Task name | Partition | Pre-action parent | Schedule |
|---|---|---|---|
| `weekly_notify` | REGION_US | all `report_*` [REGION_US] OR just `report_orders` as sentinel | `0 0 * * 0` |
| `weekly_notify` | REGION_EU | `report_orders` [REGION_EU] | `0 0 * * 0` |
| `weekly_notify` | REGION_APAC | `report_orders` [REGION_APAC] | `0 0 * * 0` |
| `weekly_notify` | GLOBAL | none (GLOBAL never has pre-actions) | `0 0 * * 0` |

> Using `report_orders` as the sentinel parent is sufficient — it's the last task in the chain for its partition. Listing all 10 report tasks as parents is valid but verbose.

### E.2 — Operator + payload

Use `dummy_operator_laui` (LeastActionDummy) for all 4 tasks.

> **Note:** These tasks have no config attached, so `{{ env }}` will not resolve. Use only runtime variables (`{{ partition }}`, `{{ logical_date }}`):

```json
{
  "message": "Weekly pipeline summary complete — partition={{ partition }}, logical_date={{ logical_date }}",
  "delay_seconds": 0.1,
  "async_mode": false
}
```

### E.3 — Pre-action (REGION_US, REGION_EU, REGION_APAC only)

> **⚠️ Same nesting rule as Phase A.** Pre-actions must be under `actions.pre_actions`, not top-level:

```json
{
  "actions": {
    "pre_actions": [{
      "laui": "<parents_done_laui from 0.5>",
      "name": "LeastActionCheckIfParentsAreDone",
      "action_variables": {
        "parents": [{
          "task_name": "report_orders",
          "project_laui": "{{ project_laui }}",
          "account_laui": "{{ account_laui }}",
          "partition": "{{ partition }}"
        }]
      }
    }]
  }
}
```

GLOBAL partition: omit `pre_actions` entirely (or pass empty list).

### E.4 — Post-action (all 4 tasks)

> **⚠️ Same nesting rule.** Post-actions must be under `actions.post_actions`. Include both `pre_actions` and `post_actions` together in the `actions` field — passing them separately in two calls would overwrite the first:

Read the webhook action schema first (`get_catalog_item(webhook_action_laui)`) to confirm the exact `action_variables` field names. Then pass as part of `actions`:

```json
{
  "actions": {
    "pre_actions": [<...from E.3, or [] for GLOBAL>],
    "post_actions": [{
      "laui": "<webhook_action_laui from 0.6>",
      "name": "<webhook action name>",
      "action_variables": {
        "url": "<webhook_url collected from user>",
        "payload": {
          "text": "LeastAction weekly pipeline complete — partition={{ partition }}, date={{ logical_date }}"
        }
      }
    }]
  }
}
```

Adjust `action_variables` to match the actual webhook action's schema.

### E.5 — Verify
1. `get_catalog_item(weekly_notify_task_laui)` → confirm `actions.pre_actions` set (non-GLOBAL) and `actions.post_actions` set (all 4)
2. `run_task(weekly_notify_task_laui)` for REGION_US → confirm pre-action blocks if `report_orders` REGION_US hasn't run, proceeds if it has
3. After success → check webhook received the POST (external verification or webhook.site logs)

---

## What to Check (DE Evaluation Criteria)

### Scheduling
| Check | How | Expectation |
|---|---|---|
| History entries per task | `get_task_history(date_from=start_date)` | Entries for each logical_date since start_date |
| Queue not stuck | `get_task_status` case_id=9 | False |
| Scheduler heartbeat | `get_task_status` case_id=2 | Not stale |
| Parallelism respected | Monitor states | Never >20 running |

### Dependency chain
| Check | How | Expectation |
|---|---|---|
| Child didn't run before parent | Compare start_time in history | Parent last_run_date < child start_time |
| Partition isolation | REGION_US vs REGION_EU | Fully independent |
| Cascade block on failure | Cancel 1 parent → child state | Child stays scheduled |
| GLOBAL independent | Run GLOBAL while REGION_US blocked | Proceeds without waiting |
| All 160 non-root tasks have pre-actions | `get_catalog_item` spot-check per layer | pre_actions non-empty for REGION_US/EU/APAC |

### Template resolution
| Check | How | Expectation |
|---|---|---|
| `{{ partition }}` resolved | Log message field | e.g. REGION_US |
| `{{ logical_date }}` resolved | Log message field | Actual date string |
| Config params resolved | Log message with env/team | stress_test, data_engineering |
| No unresolved `{{ }}` | Check message fields for config-attached tasks | Zero occurrences |
| Tasks without config | `{{ env }}` in log | Stays literal (not an error) |

### Error detection + fix
| Check | How | Expectation |
|---|---|---|
| Error detected from logs | `get_task_logs` on error session | Clear step + message |
| No error line → escalate | `get_non_task_logs(category="CELERY")` | Full traceback visible |
| Fix in 1 MCP call | `create_catalog_item` with corrected raw-string payload | Overwrites in place |
| Post-fix run clean | `get_task_logs` new session | No level:error, reaches executing_sql_command |

### Backfill
| Check | How | Expectation |
|---|---|---|
| start_date persisted | `get_catalog_item` after overwrite | start_date=2026-01-15 |
| logical_date advances correctly | history entries | consecutive dates from 2026-01-15 |
| {{ logical_date }} resolves in backfill run | log output message field | 2026-01-15 00:00:00 |

### Notification tasks
| Check | How | Expectation |
|---|---|---|
| Pre-action blocks without parent | run_task before report runs | Task stays waiting |
| Post-action fires webhook | Check webhook receiver | HTTP POST received |
| GLOBAL has no pre-action | `get_catalog_item` | pre_actions empty |
| Webhook URL resolved | action_variables in post_action | Contains actual URL |

---

## Output Report Template

```
## Workflow Health Summary
| Workflow    | Tasks | Logical dates covered | Success Rate | Avg Duration |

## Operator Mix
- Dummy tasks: 170 | Pass rate: N%
- PostgresqlExecuteSQL tasks: 30 | Pass rate: N%
- Intentionally broken (APAC): 10 | Detected: yes | Fixed in 1 call: yes/no

## Dependency Chain Coverage
- Non-root tasks with pre-actions: N/160 (expected: 160)
- GLOBAL tasks with pre-actions: N (expected: 0)
- Dependency violations (child ran before parent): N (expected: 0)
- Partition isolation (REGION_US block didn't affect EU): yes/no

## Template Variable Resolution
- {{ partition }} resolved: N/20 sessions
- {{ logical_date }} resolved: N/20 sessions
- Config params (env/team) resolved: N/N config-attached sessions
- Tasks without config — {{ env }} stays literal: yes/no (expected: yes)
- Unresolved {{ }} in config-attached tasks: N (expected: 0)

## Error Debugging
- Sessions where TASK logs stopped mid-step: N
- Sessions where CELERY logs revealed traceback: N
- Error log gap (no level:error for operator exceptions): confirmed/not observed

## Config + Parameter Test
- Tasks with config: 50 | Params visible in logs: N/50
- Retry: retried N/1 expected times | retry_number after exhaustion: total_retries+1 (quirk)

## Connection Queue
- Peak concurrent: N (limit: 20)
- Tasks stuck >60s: N

## Dependency Chains
- Chains tested: 40 | Violations: N | Cascades correct: N/40

## Backfill
- Tasks overwritten: 50 | start_date persisted: yes/no
- Catch-up consecutive: yes/no | logical_date template resolved correctly: yes/no

## Weekly Notification Tasks
- Tasks created: 4/4
- Pre-action set for REGION_US/EU/APAC: yes/no
- GLOBAL runs without pre-action: yes/no
- Webhook POST received: yes/no

## DE Inconsistencies Found
1. <description> — severity: blocking/warning/info
```

---

## MCP Tool Sequence

| Phase | Tools | ~Calls |
|---|---|---|
| 0 — Setup | search_marketplace, get_marketplace_item, create_catalog_item, search_catalog | 25 |
| A — 200 tasks | create_catalog_item × 205 | 210 |
| B — Adhoc + fix | run_task × 100, get_task_history, get_task_logs × 30, get_non_task_logs (CELERY), create_catalog_item × 10 | 165 |
| C — Backfill | create_catalog_item × 50 (overwrite), get_task_history × 5 | 60 |
| D — Config + retry | get_catalog_item × 10, get_task_logs × 20, create_catalog_item × 1 (retry), run_task × 1 | 35 |
| E — Notification tasks | create_catalog_item × 4, get_catalog_item × 4, run_task × 4 | 15 |
| **Total** | | **~510 MCP calls** |

Each call target: <2 sec. Flag any call exceeding this as a platform issue.

**Token TTL:** MCP bearer token has a 24h TTL. If tools start returning 404, the token has expired — refresh from `/mcp-token` and update `.mcp.json`. Reconnection requires a new Claude window.
"""
}
