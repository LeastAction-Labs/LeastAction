# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 07_actions_control  |  Flavor: KB (skills-only knowledge bundle)
# Actions that CONTROL the pipeline (not just notify): cancel, skip, rerun, start — observe state,
# decide, act. Built-in control actions + composition patterns (SLA watchdog, auto-retry, DQ enforce).
payloads = {}

skills = {
    "00_control_actions.md": """\
# Beyond notifications: actions that control the pipeline

## Lifecycle & prerequisites
**Stage:** Actions & Control. Knowledge bundle — the agent reads this and composes control actions at a
hook. Prerequisites: the built-in control actions below (core), plus `LeastActionSlackNotify` to notify.
Some patterns need a small custom action for the condition check (timing/quality/state).

## Built-in control actions
| Action | What it does |
|---|---|
| `LeastActionRun` | Start a task |
| `LeastActionRerun` | Re-execute a task from the beginning |
| `LeastActionRerunSubtree` | Re-execute a task and all downstream children |
| `LeastActionCancel` | Stop a running task |
| `LeastActionSkip` | Mark a task skipped without running it |
| `LeastActionSkipSubtree` | Skip a task and all downstream children |

Compose with notify + custom logic: a single postAction sequence can check a condition → act → notify.

## Task context available to every action
`{{task_name}}`, `{{logical_date}}`, `{{workflow_name}}`, `{{partition}}`, `{{state}}`, `{{last_run_date}}`, `{{laui}}`.

## Patterns
1. **SLA watchdog** — preAction checks elapsed time; over threshold → `LeastActionCancel` + notify (vars: `sla_minutes`, `notify_webhook`, `message`).
2. **SLA start-gate (skip self)** — preAction checks parent freshness; stale → `LeastActionSkip` + notify (a gentler `LeastActionCheckIfParentsAreDone` that moves on instead of waiting).
3. **Auto-retry on failure** — postAction on `failed`: attempt 1 → `LeastActionRerun` silent; attempt 2 → rerun + notify; attempt 3 → stop + escalate. Track attempt count in task metadata or an external store.
4. **Cancel + skip subtree** — on confirmed bad data: `LeastActionCancel` (if running) → `LeastActionSkipSubtree` → notify. From the UI, `task_lauis` auto-fills from selection.
5. **Start child on success (event-driven)** — postAction on `success` looks up the child by name+partition and `LeastActionRun`s it immediately — no scheduler wait.
6. **Data-quality enforce** — postAction queries a quality score/row count; below threshold → `LeastActionSkipSubtree` + notify (catches tasks that "succeed" but produce wrong output).
7. **Partition triage (UI)** — over `item_lauis` from a table selection: failed→Rerun, running-over-SLA→Cancel, stale→Skip, success→none; then one notify with the triage summary.
8. **Escalation chain** — staged, stateful: breach → notify tier-1; still running after N min → `LeastActionCancel` + notify tier-2 + `LeastActionSkipSubtree`. Store the first-alert timestamp in task metadata/external store.

## Composing
Each step is a separate entry in `post_actions`/`pre_actions`; they run in order. An action's
true/false return controls whether the task is considered done and whether the chain continues.

## Test before you use
Control actions make changes — a wrong skip-subtree marks many tasks skipped; a rerun loop without an
attempt guard runs forever. Test on one task / a small isolated partition first; keep action code in git.

## Relationship to notify
This is the control superset of `leastaction-pipelines-notify` (notify-only). Use notify when a human
decides; use control when the action should act. They compose: act then notify.
""",
}

prompt = (
    "Knowledge bundle for pipeline-control actions in LeastAction. Built-in actions LeastActionRun, "
    "LeastActionRerun, LeastActionRerunSubtree, LeastActionCancel, LeastActionSkip, LeastActionSkipSubtree "
    "compose at pre/post/UI hooks with notify and a custom condition check to: SLA-watchdog cancel stuck "
    "tasks, skip-self start-gates, auto-retry with attempt tracking, cancel+skip-subtree on bad data, "
    "start-child-on-success event-driven sub-pipelines, data-quality enforce via skip-subtree, partition "
    "triage over UI selections, and staged escalation chains. Observe state, decide, act, optionally notify."
)

description = (
    "Actions & Control (KB): actions that control the pipeline — cancel, skip, rerun, start — not just "
    "notify. Built-in control actions plus composition patterns (SLA watchdog, auto-retry, DQ enforce, "
    "partition triage, escalation). The agent reads this and composes the right reaction at a hook."
)

guide_docs = """\
# Pipeline Control Actions

**Lifecycle stage:** Actions & Control. **Flavor:** skills-only knowledge bundle — no tasks to deploy;
the agent reads the skill and composes control actions at a hook.

## What it teaches
Some situations don't need a human: a 3-hour task should be cancelled, a bad partition skipped, a child
started the moment its parent finishes. Control actions observe state, decide, and act. Built-ins:
`LeastActionRun/Rerun/RerunSubtree/Cancel/Skip/SkipSubtree`. Compose them with a condition check and a
notify into one postAction/preAction sequence.

## Prerequisites
- Built-in control actions (core); `LeastActionSlackNotify` to notify; a small custom action for the
  condition (timing/quality/state) where a pattern needs one.

## Using
> "use the leastaction-pipelines-control usecase to cancel daily_etl if it runs over 2 hours and alert #oncall"

The agent adds a preAction (SLA watchdog) composing `LeastActionCancel` + notify. For notify-only, see
`leastaction-pipelines-notify`. **Test on one task first** — control actions make real changes.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Actions & Control",
    "tags": ["flavor:KB", "lifecycle:actions-control", "control", "cancel", "skip", "rerun", "sla", "retry", "data-quality"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
