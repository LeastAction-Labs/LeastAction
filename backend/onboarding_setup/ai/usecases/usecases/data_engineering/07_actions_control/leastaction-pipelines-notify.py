# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 07_actions_control  |  Flavor: KB (skills-only knowledge bundle)
# Teaches notification at any pipeline hook (pre/post/UI), the built-in LeastActionSlackNotify,
# task-context message variables, and notify patterns (failure, approval, DQ gate, SLA, digest).
payloads = {}

skills = {
    "00_notify_at_every_hook.md": """\
# Notify & manage at every hook

## Lifecycle & prerequisites
**Stage:** Actions & Control (notification). Knowledge bundle — the agent reads this and attaches the
right notify action at the right hook. Prerequisites: `LeastActionSlackNotify` (core) for Slack, or a
small custom action + a connection holding the endpoint credentials for any other target.

## Hooks a notify action can attach to
| Hook | When it fires |
|---|---|
| `pre_actions` | Before the task operator runs |
| `post_actions` | After the operator completes (filter with `run_on_states`, e.g. `["failed"]`) |
| UI action on a task | Manually from the table/task view (`task_lauis` auto-filled from selection) |
| UI action on a catalog item | From an asset/report/any item (`item_lauis` auto-filled) |

## Built-in: LeastActionSlackNotify
Ships with LeastAction. Configure a Slack Incoming Webhook in a connection and reference the action —
no code: `{"webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"}`.

## Task-context variables (use in `message`)
`{{task_name}}`, `{{logical_date}}`, `{{workflow_name}}`, `{{partition}}`, `{{state}}`, `{{last_run_date}}`.

## Patterns
1. **Failure alert** — `post_actions` with `run_on_states:["failed"]` → Slack message with task/partition/workflow.
2. **Approval needed** — postAction notifies a reviewer with a deep link when a report lands in a review folder (pairs with `leastaction-reporting-approval`).
3. **DQ gate (notify + block)** — chain a custom quality-check action (returns true/false to block downstream) then a notify action on failure.
4. **SLA / late-run** — a timing-check action + notify when the task finished outside its window.
5. **Pipeline-complete digest** — notify postAction on the final task; for per-task status, a custom action queries the catalog and formats a summary.
6. **Bulk status notify (UI)** — select tasks in the table, trigger a notify action (`task_lauis` auto-filled).
7. **Notify then act** — chain with control actions: notify + `LeastActionSkipSubtree`, notify + `LeastActionRerun`, etc. (see `leastaction-pipelines-control`).

## One pattern, any target
| Target | How |
|---|---|
| Slack | `LeastActionSlackNotify` (built-in; webhook URL) |
| Email | SMTP action (see `leastaction-reporting-approval`) |
| AWS SNS | custom action: `boto3.client('sns').publish(...)` |
| MS Teams / PagerDuty / any HTTP | custom action: `requests.post(webhook_url, json=payload)` |

The hook config (which task, which state, which message) is identical regardless of destination — only
the action's send code differs. Multiple postActions run in sequence.

## Adapting
The notify slot can do anything a Python action can: write to a DB, update a dashboard, create a
catalog item, or start a downstream pipeline. Notification is just one use of the hook.
""",
}

prompt = (
    "Knowledge bundle: attach notification actions at any LeastAction hook (pre_actions, post_actions with "
    "run_on_states, UI actions on tasks/items). Use the built-in LeastActionSlackNotify (webhook in a "
    "connection) or a small custom action for email/SNS/Teams/PagerDuty/any HTTP. Compose message strings "
    "from task-context variables ({{task_name}}, {{logical_date}}, {{state}}, {{partition}}, ...). Covers "
    "failure alerts, approval-needed, DQ gate, SLA, digests, bulk UI notify, and notify-then-act chaining."
)

description = (
    "Actions & Control (KB): never miss a pipeline event — attach notify actions at any hook (pre/post/UI), "
    "use the built-in LeastActionSlackNotify or any custom target, and template messages from task context. "
    "Teaches failure/approval/DQ/SLA/digest patterns. The agent reads this and wires the right hook."
)

guide_docs = """\
# Notify & Manage Pipelines

**Lifecycle stage:** Actions & Control. **Flavor:** skills-only knowledge bundle — no tasks to deploy;
the agent reads the skill and attaches the right notify action at the right hook.

## What it teaches
Pipelines run silently; this makes them speak. Notify actions attach at `pre_actions`, `post_actions`
(filter by state), or as UI actions. `LeastActionSlackNotify` is built in (just a webhook); any other
target (email/SNS/Teams/PagerDuty/HTTP) is a small custom action + a connection. Messages template from
task context (`{{task_name}}`, `{{logical_date}}`, `{{state}}`, ...).

## Prerequisites
- `LeastActionSlackNotify` (core) for Slack, or a custom action + connection for other targets.

## Using
> "use the leastaction-pipelines-notify usecase to alert #data-team whenever daily_sales fails"

The agent adds a `post_actions` entry with `run_on_states:["failed"]` and a templated message. For
control actions (cancel/skip/rerun) see `leastaction-pipelines-control`; for approval/email distribution
see `leastaction-reporting-approval`.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Actions & Control",
    "tags": ["flavor:KB", "lifecycle:actions-control", "notify", "slack", "email", "hooks", "alerting"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
