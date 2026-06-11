# Never Miss a Pipeline Event: Notify and Manage at Every Hook

Pipelines run in silence. Teams find out something went wrong when a business user asks why the report is missing, or when a downstream system fails because data was never refreshed. By the time anyone looks, the failure happened hours ago.

LeastAction lets you attach notification actions at any hook — before a task runs, after it completes, on failure, or triggered manually from the UI. The notification target — Slack, email, SNS, Teams, PagerDuty, any webhook — is a detail of the action, not a constraint of the platform.

LeastAction ships with `LeastActionSlackNotify` built in. For other targets, writing a notification action is a few lines of Python and a connection with the endpoint credentials.

---

## How It Works

Every task and workflow in LeastAction supports action hooks:

| Hook | When it fires |
|------|--------------|
| `pre_actions` | Before the task operator runs |
| `post_actions` | After the task operator completes (can filter by state) |
| UI action on task | Manually triggered from the table or task view |
| UI action on catalog item | Triggered from an asset, report, or any catalog item |

Attach a notify action to any of these. The action receives task context — name, date, partition, state, workflow — and sends a message.

---

## The Built-in: LeastActionSlackNotify

`LeastActionSlackNotify` ships with LeastAction and sends messages to a Slack channel via an Incoming Webhook. No code to write — configure a Slack Incoming Webhook URL in a connection and reference the action.

```json
{
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

For other targets — email, SNS, Teams, HTTP — write a small action that reads credentials from the connection and posts a message. The pattern is identical regardless of destination.

---

## Task Context Variables

Use these in message strings to make notifications actionable:

| Variable | What it contains |
|----------|-----------------|
| `{{task_name}}` | Name of the task that fired the action |
| `{{logical_date}}` | The task's logical date |
| `{{workflow_name}}` | The workflow the task belongs to |
| `{{partition}}` | The task's partition value |
| `{{state}}` | Current task state (`success`, `failed`, `skipped`) |
| `{{last_run_date}}` | Timestamp of when the task last ran |

---

## Use Cases

### 1. Task failure alert

Notify the data team the moment a task fails — with enough context to act immediately.

```json
{
  "actions": {
    "post_actions": [
      {
        "action": "LeastActionSlackNotify",
        "run_on_states": ["failed"],
        "variables": {
          "webhook_url": "{{connection.webhook_url}}",
          "message": "Task {{task_name}} failed on {{logical_date}} | Partition: {{partition}} | Workflow: {{workflow_name}}"
        }
      }
    ]
  }
}
```

Same pattern with an email action, an SNS publish, or a PagerDuty trigger — swap the action, keep the message template.

### 2. Approval needed

When a report or artifact lands in a review folder, a postAction notifies the reviewer with a direct link to the catalog item. The reviewer opens it, reviews inline, and triggers the approval action — no dashboard polling.

```json
{
  "message": "Finance Close Report is ready for review. Date: {{logical_date}}. Open: {{catalog_item_url}}. Trigger ApproveAndSendReport when ready."
}
```

See [Report Approval Workflow](/path?laui=getting-started-examples-reporting_asset_management-report-approval-workflow&itemtype=doc.file&itemname=Report%20Approval%20Workflow) for the full pattern.

### 3. Data quality gate — notify and block

A postAction checks a quality score or row count after the task completes. If it fails the threshold, the action returns `false` — blocking downstream tasks — and fires a notification.

Chain two postActions: the quality-check action first (custom Python, returns true/false), then the notify action on failure. Downstream tasks are blocked. The team is alerted with enough context to investigate.

### 4. SLA / late-running alert

For time-sensitive pipelines, combine a timing-check action with a notification. If the task completed outside its expected window, send an escalation before the business user notices.

```json
{
  "message": "SLA breach: {{task_name}} completed outside the expected window on {{logical_date}}. Last run: {{last_run_date}}. Downstream tasks may be delayed."
}
```

### 5. Pipeline complete digest

Add a notify postAction to the final task in a workflow. When it succeeds, the team gets a summary confirming the pipeline ran, the date covered, and where outputs are published.

For a richer digest with per-task status, write a custom action that queries the catalog for all tasks in the workflow, formats a summary, and passes it to the notification target.

### 6. Bulk status notify from the UI

Select any set of tasks in the table view and trigger a notify action. `task_lauis` is auto-filled from the selection. Useful for ad-hoc updates — confirming a backfill completed, flagging tasks as reviewed, escalating a batch of failures.

### 7. Notify then act

Notifications don't have to stand alone. Chain them with control actions:

- Notify + `LeastActionSkipSubtree` — alert and skip all downstream tasks for a bad partition
- Notify + `LeastActionRerun` — alert and immediately retry
- Notify + a catalog write action — alert and update an item's status in the catalog

Multiple postActions run in sequence. The notify fires first (or last), the control action follows.

---

## One Pattern, Any Target

| Target | How |
|--------|-----|
| Slack | `LeastActionSlackNotify` — built in, just needs a webhook URL |
| Email | SMTP action — see [Report Approval Workflow](/path?laui=getting-started-examples-reporting_asset_management-report-approval-workflow&itemtype=doc.file&itemname=Report%20Approval%20Workflow) |
| AWS SNS | Custom action: `boto3.client('sns').publish(...)` |
| MS Teams | Custom action: HTTP POST to Teams incoming webhook |
| PagerDuty | Custom action: HTTP POST to PagerDuty Events API |
| Any HTTP endpoint | Custom action: `requests.post(webhook_url, json=payload)` |

Each is a small Python action with a connection holding the credentials. The hook configuration — which task, which state, which message — is the same regardless of target.

---

## This Is Just a Starting Point

The notify pattern shown here is one example of what actions can do at pipeline hooks. The same slot can write to a database, update a dashboard, trigger an external API, create a catalog item, or start a downstream pipeline. What happens at the hook is entirely up to you.
