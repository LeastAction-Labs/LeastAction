# Beyond Notifications: Actions That Control Your Pipeline

[Notify and manage](/path?laui=getting-started-examples-notify_and_manage-notify-and-manage-pipelines&itemtype=doc.file&itemname=Notify%20And%20Manage%20Pipelines) covers the basics — send a message when something happens and let a human decide what to do next. That works well for approvals, digests, and low-urgency alerts.

But some situations don't need a human in the loop. A task that has been running for three hours should be cancelled. A partition with confirmed bad data should be skipped before it wastes compute. A child pipeline should start the moment its parent finishes — not when the scheduler next wakes up.

This is what running actions do. They observe state, make a decision, and act — cancel, skip, rerun, start — optionally notifying a human at the end. The hook is the same as any action. The difference is what happens inside.

---

## Built-in Control Actions

LeastAction ships with task control actions that can be composed into any running action:

| Action | What it does |
|--------|-------------|
| `LeastActionRun` | Start a task |
| `LeastActionRerun` | Re-execute a task from the beginning |
| `LeastActionRerunSubtree` | Re-execute a task and all its downstream children |
| `LeastActionCancel` | Stop a running task |
| `LeastActionSkip` | Mark a task as skipped without running it |
| `LeastActionSkipSubtree` | Skip a task and all its downstream children |

These can be chained with notification actions and custom logic. A single postAction sequence can: check a condition → act → notify. The human gets informed. The pipeline keeps moving.

---

## Task Context Available to Every Action

| Variable | What it contains |
|----------|-----------------|
| `{{task_name}}` | Name of the task |
| `{{logical_date}}` | The task's logical date |
| `{{workflow_name}}` | The workflow it belongs to |
| `{{partition}}` | The task's partition value |
| `{{state}}` | Current state: `success`, `failed`, `running`, `skipped` |
| `{{last_run_date}}` | When the task last ran |
| `{{laui}}` | The task's unique catalog identifier |

---

## Use Cases

### 1. SLA watchdog — cancel stuck tasks automatically

A preAction that checks how long the current task has been running. If it exceeds a configurable threshold, it cancels the task and notifies the team. No task stays stuck overnight.

```
preAction runs → checks elapsed time since task started
    ├── within SLA window → return true, task continues
    └── over threshold → LeastActionCancel → LeastActionSlackNotify → return false
```

Action variables:
```json
{
  "sla_minutes": 120,
  "notify_webhook": "{{connection.webhook_url}}",
  "message": "Task {{task_name}} exceeded SLA of 120 minutes on {{logical_date}}. Cancelled automatically."
}
```

The same pattern applies to any external timeout source — a row in a monitoring table, a CloudWatch metric, an external API response.

### 2. SLA start gate — skip self if conditions aren't ready

A preAction that checks whether upstream data is ready within an acceptable window. If the data is stale or the parent ran outside the expected time, the task skips itself rather than running on bad inputs.

```
preAction runs → checks parent last_run_date against expected window
    ├── parent ran on time → return true, task runs normally
    └── parent stale or missing → LeastActionSkip → LeastActionSlackNotify
```

This is a gentler version of `LeastActionCheckIfParentsAreDone` — instead of blocking (returning false and waiting for retry), it skips and moves on. Use this when stale data for one date is acceptable and you don't want the task to sit in a waiting state.

### 3. Auto-retry on failure

A postAction that fires on `failed` state, reruns the task, and tracks attempt count. On the first failure, rerun silently. On the second, rerun and notify. On the third, stop retrying and escalate.

```
postAction (on failed) → check attempt count
    ├── attempt 1 → LeastActionRerun (silent)
    ├── attempt 2 → LeastActionRerun + notify team
    └── attempt 3 → stop + notify escalation channel
```

The attempt count can be stored in the task's metadata via the catalog API, or in a lightweight external store. This keeps flaky tasks from requiring human intervention on every transient failure without hiding real problems.

### 4. Cancel and skip subtree

When bad data is confirmed mid-run — a source system returned corrupt records, a file was malformed — there is no point letting downstream tasks run. A UI action or postAction cancels the running task and skips everything downstream.

Select the task in the table view, trigger the action. `task_lauis` is auto-filled from the selection. The action:

```
for each selected task:
    → LeastActionCancel (if running)
    → LeastActionSkipSubtree (marks all children skipped)
    → LeastActionSlackNotify (summary of what was cancelled/skipped)
```

The pipeline is isolated. Other partitions and workflows continue unaffected.

### 5. Start child task on success — event-driven sub-pipelines

A postAction that fires on `success` and directly triggers a specific child task by name and partition — without waiting for the scheduler to next tick.

```
postAction (on success) → look up child task by name + partition via catalog API
    → LeastActionRun on the child task's laui
    → optionally notify: "downstream pipeline started"
```

This turns scheduled pipelines into event-driven ones at the task level. The child starts the moment the parent finishes. Useful for sub-pipelines that are logically triggered by a parent's output rather than a clock.

### 6. Data quality enforce — skip downstream on bad data

A postAction that queries a quality score or row count from a metrics table after the task completes. If the output is below threshold, it skips the entire downstream subtree — harder than just returning false (which would block and retry).

```
postAction (on success) → query quality_scores table for this task + date
    ├── score above threshold → return true, downstream runs
    └── score below threshold → LeastActionSkipSubtree → notify with score details
```

This pattern is common in data pipelines where a task can "succeed" (the SQL ran, no errors) but the output is wrong (zero rows, null values, outlier counts). The operator reports success; the quality check catches the problem.

### 7. Partition triage — manage many at once from the UI

Select a group of tasks across partitions in the table view. A triage action evaluates each one and takes the appropriate action per partition:

```
for each task_laui in item_lauis (auto-filled from table selection):
    → fetch task state
    ├── failed → LeastActionRerun
    ├── running (over SLA) → LeastActionCancel
    ├── pending (stale) → LeastActionSkip
    └── success → no action
→ LeastActionSlackNotify with triage summary
```

One trigger. Dozens of tasks handled. The notification tells the team exactly what was done to which partition.

### 8. SLA breach escalation chain

For pipelines with hard SLA requirements, a multi-stage escalation that gets louder the longer the problem persists:

```
postAction checks timing
    └── breached → notify tier-1 (data team Slack)
                → if still running after N minutes → LeastActionCancel
                → notify tier-2 (on-call + management channel)
                → LeastActionSkipSubtree (unblock downstream)
```

This requires a stateful check — the action stores the first-alert timestamp (in task metadata or an external table), and subsequent runs of the action check whether enough time has passed to escalate. The catalog API or a small external store handles the state.

---

## Composing Actions

Running actions are most powerful when composed. A single postAction sequence can:

1. Check a condition (timing, quality, state)
2. Act (cancel, skip, rerun, run)
3. Notify (Slack, email, SNS)
4. Return true or false to control whether the task itself is considered done

Each step is a separate action in the `post_actions` array. They run in order. If any returns false, subsequent actions in the chain can be configured to still run or to stop — giving you precise control over the reaction sequence.

---

## Test Before You Use

Running actions make changes. A skip subtree action applied to the wrong task will mark dozens of tasks as skipped. A rerun loop without an attempt guard will run forever. An auto-cancel that fires too eagerly will kill tasks that were just slow.

**Test on a single task or a small isolated partition first.** Confirm the behavior matches intent before attaching to a production workflow. Keep all action code in Git — what the action does, it can be reversed if the code is available to reason about.

---

## This Is Just a Starting Point

The use cases here are examples of a general pattern: observe state, make a decision, act. The same hook — preAction, postAction, UI action — can do anything a Python function can do. Query an external API, write to a database, call an ML model, rebalance a queue. What the action does at the hook is entirely up to you.

For the simpler version of this pattern — notify only, no control actions — see [Notify and Manage Pipelines](/path?laui=getting-started-examples-notify_and_manage-notify-and-manage-pipelines&itemtype=doc.file&itemname=Notify%20And%20Manage%20Pipelines).
