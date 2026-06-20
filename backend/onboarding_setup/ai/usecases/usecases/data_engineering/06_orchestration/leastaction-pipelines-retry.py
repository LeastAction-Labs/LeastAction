# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 06_orchestration  |  Flavor: KB (skills-only knowledge bundle)
# Make tasks resilient: built-in retry fields (total_retries/retry_interval), the LeastActionReschedule
# action for auto re-schedule on error/fail, and when to escalate to a custom retry-with-attempt-cap action.
payloads = {}

skills = {
    "00_retry_and_reschedule.md": """\
# Retry & reschedule

## Lifecycle & prerequisites
**Stage:** Orchestration. Knowledge bundle — the agent reads this and makes a task resilient. Two
mechanisms: the task's built-in retry fields, and the `LeastActionReschedule` action (used by the
`PostgresqlDemoWorkflow` config). For richer logic, the auto-retry control pattern.

## 1. Built-in retry fields (simplest)
A task carries retry fields in its schema — set them on the task or via a `config`:
| Field | Meaning |
|---|---|
| `total_retries` | max retry attempts allowed |
| `retry_interval` | minutes between retries |
| `retry_number` | current attempt (system-managed) |
| `can_retry` / `retry_run_date` | system-managed retry scheduling |
On failure the scheduler retries up to `total_retries`, waiting `retry_interval` minutes each time. Good
for transient errors (network blips, deadlocks).

## 2. LeastActionReschedule action (config-driven)
Attach `LeastActionReschedule` as an action on `error`/`fail` states (the `PostgresqlDemoWorkflow` config
does this for every task it's attached to). It re-schedules the task to run again automatically — useful
to express "always self-heal on failure" as a reusable workflow config rather than per-task fields. Put it
in a workflow `config` and every task inheriting that config gets the behavior.

## 3. Custom auto-retry with attempt cap + escalation (full control)
When you need backoff, attempt tracking, or escalation, use the auto-retry pattern from
`leastaction-pipelines-control`: a postAction on `failed` that reruns (`LeastActionRerun`), tracks the
attempt count (in task metadata or an external store), notifies on the 2nd, and stops + escalates on the
3rd. This avoids infinite rerun loops (always cap attempts) and distinguishes flaky from broken.

## Choosing
| Need | Use |
|---|---|
| Transient errors, fixed interval | built-in `total_retries` / `retry_interval` |
| "Self-heal on failure" as a shared default | `LeastActionReschedule` in a workflow config |
| Backoff / attempt cap / escalation / conditional retry | custom auto-retry control action |

## Rules
- **Always cap attempts** — a rerun without a guard runs forever.
- Don't retry deterministic failures (bad SQL, schema mismatch) — fix them; retry only transient ones.
- Pair with notify so repeated failures surface instead of silently looping.
""",
}

prompt = (
    "Knowledge bundle for retry and reschedule in LeastAction. Three mechanisms: (1) built-in task retry "
    "fields total_retries/retry_interval/retry_number for transient errors; (2) the LeastActionReschedule "
    "action attached on error/fail via a workflow config (as PostgresqlDemoWorkflow does) to express "
    "self-heal-on-failure as a reusable default; (3) a custom auto-retry control action with attempt cap, "
    "backoff, notify-on-Nth, and escalation (from leastaction-pipelines-control). Always cap attempts; "
    "retry transient not deterministic failures; pair with notify."
)

description = (
    "Orchestration (KB): make tasks resilient — built-in retry fields (total_retries/retry_interval), the "
    "LeastActionReschedule action for config-driven self-heal on error/fail, and a capped custom auto-retry "
    "with escalation. The agent reads this and picks the right mechanism (always capping attempts)."
)

guide_docs = """\
# Retry & Reschedule

**Lifecycle stage:** Orchestration. **Flavor:** skills-only knowledge bundle — the agent reads the skill
and applies the right resilience mechanism; no tasks to deploy.

## What it teaches
Three ways to handle failure: built-in task retry fields (`total_retries`/`retry_interval`) for transient
errors; the `LeastActionReschedule` action in a workflow `config` to make "self-heal on failure" a shared
default (as `PostgresqlDemoWorkflow` does); and a capped custom auto-retry control action with backoff +
escalation for full control. Always cap attempts; retry transient, not deterministic, failures.

## Prerequisites
- For mechanism 2: the `LeastActionReschedule` action + a workflow `config`. For mechanism 3: see
  `leastaction-pipelines-control` (auto-retry pattern) + `LeastActionRerun` and `LeastActionSlackNotify`.

## Using
> "use the leastaction-pipelines-retry usecase to retry daily_load 3x at 5-min intervals, then alert"

The agent sets `total_retries`/`retry_interval` (or wires `LeastActionReschedule`/a capped auto-retry with
a notify on exhaustion).
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Orchestration",
    "tags": ["flavor:KB", "lifecycle:orchestration", "retry", "reschedule", "resilience", "backoff", "escalation"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
