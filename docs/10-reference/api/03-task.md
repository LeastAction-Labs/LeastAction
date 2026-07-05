# Task API

**Prefix:** `/api/v1/task`
**Auth:** Required (Bearer token)

---

## Endpoints

- [POST /task/run](#1-post-taskrun) -- Create and/or run a task
- [POST /task/multiple_tasks](#2-post-taskmultiple_tasks) -- Run multiple existing tasks
- [POST /task/update/{task_laui}](#3-post-taskupdatetask_laui) -- Update task fields
- [POST /task/finish/{task_laui}](#4-post-taskfinishtask_laui) -- Finish/dequeue task
- [POST /task/dangerously_reset/{task_laui}](#5-post-taskdangerously_resettask_laui) -- Reset task to scheduled state
- [GET /task/diagnose/{task_laui}](#6-get-taskdiagnosetask_laui) -- Diagnose why a task isn't running

---

## 1. POST `/task/run`

Create and/or run a task. This endpoint has **dual behavior**:

| Scenario | Condition | What happens |
|----------|-----------|--------------|
| **Create + Run** | `item_laui` is **not** provided | Creates a new task in the catalog, then runs it |
| **Run Existing** | `item_laui` **is** provided | Fetches the existing task, then runs it |

### Access Control

**Router-Level Authorization**: This endpoint validates access permissions **before** reaching the service layer using FastAPI dependencies.

**Permission Checks**:
- If `item_laui` is provided (running existing task): User must have **edit** permission on the task
- If creating a new task:
  - User must have **edit** permission on `parent_laui`
  - User must have **view** permission on `operator_laui`, `connection_laui`, `payload_laui` (if provided)
  - User must have **view** permission on all action LAUIs referenced in the `actions` field

**Why It Matters**: This is the **only** way to create task items. The generic `/api/v1/catalog/create` endpoint explicitly blocks `task` item types, ensuring all task creation flows through this controlled endpoint with proper permission validation.

### Request Body

`BaseCreateItemRequest` with `extra="allow"` -- accepts any additional task fields beyond `item_type`.

**Common fields (from task.json schema):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `item_type` | string | yes | -- | Must be `"task"` |
| `item_laui` | ObjectId | no | -- | If provided, runs existing task instead of creating |
| `name` | string | yes (create) | -- | Unique task name within project/account/partition |
| `parent_laui` | ObjectId | yes (create) | -- | Workflow (or folder.workflow) LAUI |
| `project_laui` | ObjectId | yes (create) | -- | Project LAUI (also used as cron name) |
| `account_laui` | ObjectId | yes (create) | -- | Account LAUI |
| `operator_laui` | ObjectId | yes (create) | -- | Operator to execute |
| `connection_laui` | ObjectId | yes (create) | -- | Connection for execution |
| `frequency` | string | no | `"ADHOC"` | `"ADHOC"` or a valid 5-part cron expression |
| `start_date` | datetime | conditional | `null` | Required for non-ADHOC tasks |
| `end_date` | datetime | conditional | `null` | Required for non-ADHOC tasks |
| `logical_date` | datetime | no | `null` | The data period this task is computing. For ADHOC: defaults to current UTC. For scheduled: initialized to `start_date`, then advances one cron step on each successful run. Floored to cron granularity (daily → midnight, monthly → 1st of month, sub-hourly → exact cron minute). Available as `{{ds}}` / `{{logical_date}}` in payloads. |
| `payload` | any | no | `null` | Inline payload (SQL, JSON, etc.) -- supports Jinja2 templates |
| `payload_laui` | ObjectId | no | `null` | Reference to a payload item (overrides inline `payload` at execution time) |
| `config` | object | no | `{}` | Task-level configuration with `parameters`, `overridable`, `not_overridable` |
| `attached_config_lauis` | array | no | `[]` | List of config item LAUIs to merge |
| `actions` | object | no | `{...}` | Pre/create/running/post actions (see Variation 5) |
| `description` | string | no | `null` | Human-readable description |
| `partition` | string | no | `"ALL"` | Partition for multi-tenancy |
| `priority` | int | no | `1` | Execution priority (used in connection queue sorting) |
| `total_retries` | int | no | `0` | Max number of automatic retries on error/timeout |
| `retry_interval` | int | no | `1` | Seconds between retries |

### Variation 1: Create + Run New ADHOC Task

The simplest case -- creates a task and immediately executes it.

```bash
curl -X POST http://localhost:8000/api/v1/task/run \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "task",
    "name": "etl-daily-load",
    "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
    "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
    "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
    "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
    "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
    "frequency": "ADHOC",
    "payload": "SELECT * FROM source_table WHERE created_at > '\''2024-01-01'\''"
  }'
```

**Response** `200 OK`:
```json
{
  "item_laui": "6650a1b2c3d4e5f6a7b8c9e0"
}
```

### Variation 2: Run Existing Task by LAUI

Runs a task that was already created. The server fetches the task from the catalog, validates it, and dispatches execution.

```bash
curl -X POST http://localhost:8000/api/v1/task/run \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "task",
    "item_laui": "6650a1b2c3d4e5f6a7b8c9e0"
  }'
```

You can optionally override `logical_date` at run time:

```json
{
  "item_type": "task",
  "item_laui": "6650a1b2c3d4e5f6a7b8c9e0",
  "logical_date": "2025-06-15T08:00:00Z"
}
```

**Response** `200 OK`:
```json
{
  "item_laui": "6650a1b2c3d4e5f6a7b8c9e0"
}
```

### Variation 3: Create Scheduled Task with Cron

`frequency` must be a valid **5-part cron expression** (minute hour day-of-month month day-of-week). `start_date` and `end_date` are **required** for non-ADHOC tasks. The `logical_date` is automatically set to `start_date`.

```json
{
  "item_type": "task",
  "name": "hourly-sync-users",
  "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
  "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
  "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
  "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
  "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
  "frequency": "0 * * * *",
  "start_date": "2025-07-01T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "payload": "CALL sync_users_proc()"
}
```

### Variation 4: Task with payload_laui Reference

Instead of inlining the payload, reference a `payload` item stored in the catalog. At execution time, the system fetches the payload item's `content` field and uses it as the task payload.

```json
{
  "item_type": "task",
  "name": "run-etl-script",
  "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
  "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
  "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
  "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
  "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
  "frequency": "ADHOC",
  "payload_laui": "6650a1b2c3d4e5f6a7b8c9d5"
}
```

If both `payload` and `payload_laui` are provided, `payload_laui` takes precedence at execution time (the `content` from the referenced payload item replaces whatever was in `payload`).

### Variation 5: Task with Actions

Actions are lifecycle hooks executed at different stages of the task pipeline. Each action references an `action` item in the catalog and can have its own connection, variables, SLA, and timeout.

**Action stages:**

| Stage | When it runs | Blocks execution? |
|-------|-------------|-------------------|
| `create_actions` | During task creation (before persist) | Yes -- if any returns `false`, creation fails |
| `pre_actions` | After validation, before connection queue | Yes -- if any returns `false`, task is skipped |
| `running_actions` | While operator is running, triggered by SLA threshold | No -- fire-and-forget |
| `post_actions` | After operator finishes (success or failure) | No -- fire-and-forget |

**ActionItem schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `laui` | ObjectId | yes | LAUI of the action item in the catalog |
| `name` | string | no | Auto-populated from the action item's name |
| `connection_laui` | string | no | Connection for this action (independent of task connection) |
| `action_variables` | object | yes | Key-value variables passed to the action |
| `sla` | int | no | SLA threshold in **minutes** (only for `running_actions`) |
| `timeout` | int | no | Timeout in seconds (minimum is system `action_timeout_seconds`) |
| `action_type` | string | no | Auto-populated: `"pre_actions"`, `"create_actions"`, `"running_actions"`, `"post_actions"` |

```json
{
  "item_type": "task",
  "name": "etl-with-actions",
  "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
  "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
  "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
  "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
  "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
  "frequency": "ADHOC",
  "payload": "SELECT * FROM orders",
  "actions": {
    "create_actions": [],
    "pre_actions": [
      {
        "laui": "6650a1b2c3d4e5f6a7b8ca01",
        "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
        "action_variables": {
          "parents": [
            {"task_name": "upstream-extract-task"}
          ]
        },
        "sla": null,
        "timeout": 300,
        "action_type": "pre_actions"
      }
    ],
    "running_actions": [
      {
        "laui": "6650a1b2c3d4e5f6a7b8ca02",
        "connection_laui": "6650a1b2c3d4e5f6a7b8ca10",
        "action_variables": {
          "channel": "#alerts",
          "message": "Task {{name}} exceeded SLA"
        },
        "sla": 30,
        "timeout": 60,
        "action_type": "running_actions"
      }
    ],
    "post_actions": [
      {
        "laui": "6650a1b2c3d4e5f6a7b8ca03",
        "connection_laui": "6650a1b2c3d4e5f6a7b8ca10",
        "action_variables": {
          "channel": "#data-team",
          "message": "Task {{name}} completed with status {{state}}"
        },
        "sla": null,
        "timeout": 60,
        "action_type": "post_actions"
      }
    ]
  }
}
```

### Variation 6: Task with attached_config_lauis

Config items are merged in a specific precedence order. Higher-precedence configs override lower-precedence ones.

**Config merge precedence** (lowest to highest):

1. **Workflow configs** -- config items that are children of the parent workflow
2. **Task attached configs** -- configs referenced by `attached_config_lauis`
3. **Task inline config** -- the `config` field on the task itself

Within the same precedence level, configs within `workflow_configs` or `task_configs` are merged in array order. A key set by an earlier config at the same level wins (first-writer-wins within a level); a higher-precedence level always overrides a lower one.

The `parameters` sub-key has special merge semantics controlled by `overridable` and `not_overridable` lists in the config.

```json
{
  "item_type": "task",
  "name": "etl-with-configs",
  "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
  "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
  "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
  "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
  "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
  "frequency": "ADHOC",
  "payload": "SELECT * FROM {{schema}}.{{table}}",
  "attached_config_lauis": [
    "6650a1b2c3d4e5f6a7b8ca20",
    "6650a1b2c3d4e5f6a7b8ca21"
  ],
  "config": {
    "parameters": {
      "schema": "public",
      "table": "people"
    }
  }
}
```

In this example, if config `ca20` defines `{"parameters": {"schema": "staging"}}` and the inline config defines `{"parameters": {"schema": "public"}}`, the inline config wins because it has higher precedence.

### Variation 7: Task with Retry Configuration

`total_retries` and `retry_interval` can be set directly on the task or derived from the merged config. On error or timeout, the system increments `retry_number`. The cron scheduler picks up tasks eligible for retry when `retry_number < total_retries`.

```json
{
  "item_type": "task",
  "name": "resilient-api-call",
  "parent_laui": "6650a1b2c3d4e5f6a7b8c9d0",
  "project_laui": "6650a1b2c3d4e5f6a7b8c9d1",
  "account_laui": "6650a1b2c3d4e5f6a7b8c9d2",
  "operator_laui": "6650a1b2c3d4e5f6a7b8c9d3",
  "connection_laui": "6650a1b2c3d4e5f6a7b8c9d4",
  "frequency": "ADHOC",
  "payload": "{\"url\": \"https://api.example.com/data\", \"method\": \"GET\"}",
  "total_retries": 3,
  "retry_interval": 60,
  "config": {
    "total_retries": 3,
    "retry_interval": 60,
    "parameters": {
      "api_key": "sk-example-key"
    }
  }
}
```

### Success Response

`200 OK`

```json
{
  "item_laui": "6650a1b2c3d4e5f6a7b8c9e0"
}
```

The returned `item_laui` is the task's LAUI. Execution is asynchronous -- the task has been dispatched to Celery. Query the task's `state` field via the catalog API to track progress.

### Error Responses

**422 -- Wrong item_type**
```json
{
  "detail": "Only tasks can be executed"
}
```

**422 -- Invalid frequency**
```json
{
  "detail": "Invalid cron expression: every-day"
}
```

**422 -- Date validation failures**
```json
{
  "detail": "start_date and end_date are required for scheduled tasks"
}
```
```json
{
  "detail": "end_date must be greater than or equal to start_date"
}
```

**422 -- Connection-operator mapping invalid**
```json
{
  "detail": "Invalid connection-operator mapping: snowflake does not support python. Allowed: operator.snowflake, operator.dbt"
}
```

**422 -- Referenced items not found or deleted**
```json
{
  "detail": "Operator item not found: 6650a1b2c3d4e5f6a7b8c9d3; Connection item not found: 6650a1b2c3d4e5f6a7b8c9d4"
}
```

**422 -- Create action failed**
```json
{
  "detail": {
    "task_name": "etl-with-actions",
    "message": "One or more create actions returned false"
  }
}
```

**404 -- Task not found (when item_laui given)**
```json
{
  "detail": "Item not found"
}
```

**500 -- Internal/Celery execution error**
```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 2. POST `/task/multiple_tasks`

Run multiple existing tasks through the full execution pipeline. Each task is independently validated, passes through pre-actions, connection queue load balancing, payload processing, and Celery dispatch.

### Request Body

```json
{
  "task_lauis": [
    "6650a1b2c3d4e5f6a7b8c9e0",
    "6650a1b2c3d4e5f6a7b8c9e1",
    "6650a1b2c3d4e5f6a7b8c9e2"
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_lauis` | array of ObjectId | yes | LAUIs of existing tasks to run |

### Success Response

`200 OK`

```json
{
  "task_results": [
    {
      "task_laui": "6650a1b2c3d4e5f6a7b8c9e0",
      "execution_result_id": "a3f1c2d4-e5b6-7890-abcd-ef1234567890"
    },
    {
      "task_laui": "6650a1b2c3d4e5f6a7b8c9e1",
      "execution_result_id": "b4f2d3e5-f6c7-8901-bcde-f12345678901"
    }
  ]
}
```

The `execution_result_id` is the Celery async result ID. Tasks that fail validation or pre-actions are silently excluded from `task_results` -- only successfully dispatched tasks appear.

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | One or more task LAUIs not found |
| 422 | Validation failures (connection-operator mapping, etc.) |
| 500 | Internal server error |

---

## 3. POST `/task/update/{task_laui}`

Update system-managed fields on a task. Used by the executor (Celery worker), the cron scheduler, and internal services to update task state during execution.

### 🔒 System-Only Endpoint

**Authentication**: Requires **both**:
1. Bearer token (user context)
2. `X-System-Auth-Token` header (system authentication)

**Why**: This endpoint is called by Celery workers during task execution to update task state, retry counts, and execution metadata. The `X-System-Auth-Token` header ensures the request originates from trusted system infrastructure, not external clients.

**Access Control**: Router-level dependency validates that the authenticated user has **edit** permission on the task before processing the update.

**External Access**: Attempting to call this endpoint without the system token results in a `401 Unauthorized` error.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_laui` | ObjectId | LAUI of the task to update |

### Request Body

`TaskUpdateRequest` -- all fields are **optional**. Only provided fields are updated.

| Field | Type | Description |
|-------|------|-------------|
| `state` | enum | Task state (see [Task States](#task-states)) |
| `user_set_state` | enum | User-requested state: `"cancel"` |
| `logical_date` | datetime | Next/current run logical datetime |
| `last_run_date` | datetime | When the task last finished |
| `last_system_updated_date` | datetime | Last system-level update timestamp |
| `latest_heartbeat` | datetime | Most recent heartbeat from the executing worker |
| `last_run_output` | object | Output from the last execution (status, errors, etc.) |
| `payload` | any | Updated payload |
| `config` | object | Updated config (after merge) |
| `iteration` | int | Lifetime execution count |
| `duration` | int | Execution duration in seconds |
| `task_instance` | string | Worker instance identifier |
| `last_run_session_id` | string | Session ID for the last run |
| `retry_number` | int | Current retry count |
| `actions_status` | object | Status of pre/running/post actions |
| `task_instance_start_date` | datetime | When the current instance started |
| `task_instance_end_date` | datetime | When the current instance ended |
| `session_id` | string | Current session LAUI |
| `data_interval_start` | datetime | Start of the current data interval |
| `data_interval_end` | datetime | End of the current data interval |
| `prev_interval_start` | datetime | Start of the previous data interval |
| `prev_interval_end` | datetime | End of the previous data interval |
| `next_run_date` | datetime | Next scheduled run datetime |
| `executor` | string | Celery worker ID that executed the task |

Note: The `duration` field accepts any numeric type and is automatically converted to `int`.

### Example: Update State to Running

```bash
curl -X POST http://localhost:8000/api/v1/task/update/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "running",
    "latest_heartbeat": "2025-07-15T10:30:00Z",
    "task_instance_start_date": "2025-07-15T10:30:00Z",
    "data_interval_start": "2025-07-15T00:00:00Z",
    "data_interval_end": "2025-07-16T00:00:00Z",
    "session_id": "sess_abc123"
  }'
```

### Example: Cancel a Task

Set `user_set_state` to `"cancel"`. The executing worker polls for this value and will gracefully terminate.

```bash
curl -X POST http://localhost:8000/api/v1/task/update/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_set_state": "cancel"
  }'
```

### Example: Heartbeat Update

Workers send periodic heartbeats while executing. If heartbeats stop, the task may be considered stale.

```bash
curl -X POST http://localhost:8000/api/v1/task/update/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "latest_heartbeat": "2025-07-15T10:35:00Z",
    "state": "running"
  }'
```

### Example: Set Output After Completion

```bash
curl -X POST http://localhost:8000/api/v1/task/update/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "success",
    "last_run_output": {
      "run_output": {
        "status": "success",
        "rows_processed": 15420,
        "output": "ETL completed successfully"
      }
    },
    "duration": 347,
    "last_run_date": "2025-07-15T10:35:47Z",
    "task_instance_end_date": "2025-07-15T10:35:47Z",
    "last_run_session_id": "sess_abc123",
    "prev_interval_start": "2025-07-15T00:00:00Z",
    "prev_interval_end": "2025-07-16T00:00:00Z",
    "logical_date": "2025-07-16T00:00:00Z",
    "retry_number": 0
  }'
```

### Success Response

`200 OK`

```json
{
  "item_laui": "6650a1b2c3d4e5f6a7b8c9e0"
}
```

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Task with given LAUI not found |
| 422 | Invalid field values (e.g., invalid state enum) |
| 500 | Internal server error |

---

## 4. POST `/task/finish/{task_laui}`

Dequeue a task from the connection queue and decrement the connection's `current_parallelism` counter. Called by the Celery worker after task execution completes (regardless of success or failure).

### 🔒 System-Only Endpoint

**Authentication**: Requires **both**:
1. Bearer token (user context)
2. `X-System-Auth-Token` header (system authentication)

**Why**: This endpoint is called by Celery workers to clean up task execution state and free connection capacity. The system token ensures only workers can perform this critical infrastructure operation.

**External Access**: Attempting to call this endpoint without the system token results in a `401 Unauthorized` error.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_laui` | ObjectId | LAUI of the task to finish |

### Request Body

None.

### Example

```bash
curl -X POST http://localhost:8000/api/v1/task/finish/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>"
```

### Success Response

`200 OK`

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Task not found in the connection queue |
| 500 | Internal server error (e.g., database write conflict after retries) |

The dequeue operation uses optimistic concurrency with up to 5 retries and exponential backoff (100ms base) to handle MongoDB write conflicts and Redis lock errors.

---

## Task States

Tasks move through the following states during their lifecycle:

| State | Value | Description |
|-------|-------|-------------|
| `created` | `"created"` | Task item exists in catalog but has not been scheduled |
| `scheduled` | `"scheduled"` | Default state. Task is eligible for the cron scheduler to pick up |
| `queued_for_connection` | `"queued_for_connection"` | Task is in the connection queue, waiting for parallelism capacity |
| `queued_in_redis` | `"queued_in_redis"` | Task has been dispatched to the Celery broker (Redis) |
| `running` | `"running"` | Celery worker is actively executing the operator |
| `success` | `"success"` | Execution completed successfully |
| `error` | `"error"` | Execution failed with a recoverable error |
| `timeout` | `"timeout"` | Execution exceeded the configured timeout |
| `cancelled` | `"cancelled"` | User requested cancellation via `user_set_state: "cancel"` |
| `fail` | `"fail"` | Permanent failure (e.g., invalid operator, missing codeblock) |

### User-Settable States

| State | Value | Description |
|-------|-------|-------------|
| `cancel` | `"cancel"` | Request graceful cancellation of a running task |

---

## Business Logic

### Task Execution Pipeline

When a task is submitted via `/task/run` or `/task/multiple_tasks`, it passes through the following pipeline:

```
Request
  |
  v
1. Create (if no item_laui)
  |
  v
2. Validate
  |  - frequency validation
  |  - date validation
  |  - connection-operator mapping
  |  - referenced items exist and are not deleted
  |  - item type validation (operator is operator, connection is connection, etc.)
  |  - config merging
  |
  v
3. Pre-actions (blocking)
  |  - Each pre_action is dispatched to Celery and awaited
  |  - If any returns false, task is skipped
  |
  v
4. Connection Queue Load Balancing
  |  - Filter out tasks already in queue
  |  - Group by connection
  |  - Enqueue into connection-specific queues
  |  - Pick runnable tasks based on available parallelism
  |
  v
5. Payload Processing
  |  - Jinja2 template rendering
  |  - Builtin variable substitution
  |  - Config parameter substitution
  |
  v
6. Celery Dispatch
  |  - Generate user access token for worker
  |  - Send to execute_task queue
  |
  v
7. Worker Execution
   - Update state to "running"
   - Set data_interval_start, data_interval_end
   - Load operator codeblock
   - Initialize operator
   - Run operator in managed thread
   - Poll for completion + cancellation + SLA actions
   - Execute post-actions
   - Update final state, duration, output
   - Dequeue from connection queue (finish)
```

### Validation Pipeline

**Frequency validation:**
- `"ADHOC"` -- always valid, no schedule
- Any other value must be a valid 5-part cron expression (split by spaces, exactly 5 parts)

**Date validation (non-ADHOC only):**
- Both `start_date` and `end_date` are required
- `end_date` must be >= `start_date`

**Connection-operator mapping:**
Subtype validation is optional and controlled by `enforce_connection_operator_mapping` in `system.yml`. When `true`, the system validates that the connection subtype supports the operator subtype (e.g., `connection.snowflake` → `operator.snowflake`). Subtypes are extracted from the `item_type` field (e.g., `"connection.snowflake"` → `"snowflake"`). When `false`, no validation is performed and any connection-operator pair is accepted.

**Config merging (precedence order, lowest to highest):**
1. Workflow configs (config items that are children of the parent workflow)
2. Task attached configs (items in `attached_config_lauis`, merged in array order)
3. Task inline config (the `config` field on the task)

The `parameters` sub-key has special handling: parameters listed in `not_overridable` cannot be overridden by higher-precedence configs, while those listed in `overridable` can. Within the same precedence level, first-writer-wins -- a parameter set by an earlier config cannot be overridden by a later config at the same level.

After merge, `total_retries` and `retry_interval` are extracted from the merged config and set on the task.

### Jinja2 Payload Templating

The payload and action variables support Jinja2 template syntax using `{{variable}}` placeholders. Variables are resolved from two sources:

1. **Config parameters** -- from the merged `config.parameters`
2. **Builtin system variables** -- see table below (these take precedence over config parameters)

Additionally, all task model fields (excluding `description`, `actions`, `payload`, `config`) are available as template variables.

Undefined variables are preserved as-is in the output (e.g., `{{unknown_var}}` remains `{{unknown_var}}`).

### Builtin Template Variables

Derived from the task's `logical_date` (or current UTC time if `logical_date` is null):

| Variable | Format | Example |
|----------|--------|---------|
| `ds` | `%Y-%m-%d` | `2025-07-15` |
| `ds_nodash` | `%Y%m%d` | `20250715` |
| `ts` | ISO 8601 | `2025-07-15T00:00:00+00:00` |
| `ts_nodash_with_tz` | `%Y%m%dT%H%M%S%z` | `20250715T000000+0000` |
| `ts_nodash` | `%Y%m%dT%H%M%S` | `20250715T000000` |
| `current_date` | `%Y-%m-%d` | `2025-07-15` (always UTC now) |
| `current_timestamp` | ISO 8601 | `2025-07-15T10:30:00.123456+00:00` (always UTC now) |

**Example payload with templates:**

```sql
SELECT *
FROM events
WHERE event_date = '{{ds}}'
  AND region = '{{region}}'
  AND batch_id = '{{ds_nodash}}_{{name}}'
```

If the task's `logical_date` is `2025-07-15T00:00:00Z`, `name` is `"etl-daily-load"`, and `config.parameters.region` is `"us-east-1"`, this renders to:

```sql
SELECT *
FROM events
WHERE event_date = '2025-07-15'
  AND region = 'us-east-1'
  AND batch_id = '20250715_etl-daily-load'
```

### Connection Queue Load Balancing

The connection queue system prevents overwhelming external systems by limiting concurrency per connection.

**Key metrics per connection:**

| Metric | Description |
|--------|-------------|
| `max_parallelism` | Maximum concurrent tasks allowed for this connection |
| `current_parallelism` | Number of tasks currently running on this connection |
| `in_queue` | Number of tasks waiting in the queue |
| `sort_dict` | Sort criteria for queue ordering (field -> ascending/descending) |

**Load balancing algorithm:**

1. **Filter duplicates** -- tasks already in the queue are skipped
2. **Group by connection** -- incoming tasks are grouped by `connection_laui`
3. **Enqueue** -- new tasks are added to their connection's queue with state `queued_for_connection`
4. **Pick runnable** -- for each connection, calculate `available = max_parallelism - current_parallelism`, then pop `min(available, in_queue)` tasks from the front of the sorted queue
5. **Dispatch** -- selected tasks proceed to Celery dispatch

Tasks that remain in the queue (because the connection is at capacity) will be picked up on the next scheduling cycle.

Enqueue and dequeue operations use optimistic concurrency with up to 5 retries and exponential backoff to handle write conflicts.

### State Transitions During Execution

```
scheduled
  |
  |  (cron picks up or /task/run called)
  v
queued_for_connection
  |
  |  (parallelism available)
  v
queued_in_redis
  |
  |  (Celery worker picks up)
  v
running  <-- heartbeat updates --+
  |                               |
  |  (poll loop)                  |
  |                               |
  +-------------------------------+
  |
  +---> success     (operator returned status=success)
  |       |
  |       +-- logical_date advanced one cron step (data period)
  |       +-- next_run_date advanced one cron interval from previous next_run_date
  |             (if still ≤ UTC now, cron dispatches the next run immediately — catch-up)
  |       +-- retry_number reset to 0
  |       +-- prev_interval_start/end set
  |
  +---> error       (operator exception or status=failed)
  |       |
  |       +-- retry_number incremented
  |       +-- eligible for retry if retry_number < total_retries
  |
  +---> timeout     (exceeded check_completion_timeout_seconds)
  |       |
  |       +-- retry_number incremented
  |       +-- eligible for retry if retry_number < total_retries
  |
  +---> cancelled   (user set user_set_state="cancel")
  |       |
  |       +-- operator.finish() called, then thread cancelled
  |
  +---> fail        (invalid operator, missing codeblock -- permanent)
```

After any terminal state, the worker:
1. Calls `operator.finish()` (unless cancelled -- already called)
2. Updates the task with final state, `duration`, `last_run_output`, `last_run_date`, `task_instance_end_date`
3. Executes post-actions (fire-and-forget)
4. Calls `/task/finish/{task_laui}` to dequeue from the connection queue

### Unique Constraints

Tasks are uniquely identified by the combination of:
- `name`
- `project_laui`
- `account_laui`
- `partition`

Attempting to create a task with the same combination will return the existing task's LAUI rather than creating a duplicate.

---

## 5. POST `/task/dangerously_reset/{task_laui}`

Reset a task back to `scheduled` state. This is a destructive operation intended for recovering stuck or corrupted tasks — it wipes all in-progress execution state.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_laui` | ObjectId | LAUI of the task to reset |

### Request Body

None.

### What it does

1. Removes the task from the connection queue (if currently enqueued)
2. Resets `state` → `"scheduled"`
3. Clears `last_run_output` → `{}`
4. Clears `user_set_state` → `null`
5. Resets `actions_status` → `{pre_actions: [], running_actions: [], post_actions: []}`
6. Sets `last_system_updated_date` → current UTC time

### Example

```bash
curl -X POST http://localhost:8000/api/v1/task/dangerously_reset/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>"
```

### Success Response

`200 OK`

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Task not found |
| 500 | Internal server error |

---

## 6. GET `/task/diagnose/{task_laui}`

Run a series of diagnostic checks on a task to explain why it is not running or not being scheduled. Returns a dict of checks with severity levels.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_laui` | ObjectId | LAUI of the task to diagnose |

### Request Body

None.

### Example

```bash
curl http://localhost:8000/api/v1/task/diagnose/6650a1b2c3d4e5f6a7b8c9e0 \
  -H "Authorization: Bearer <access_token>"
```

### Success Response

`200 OK` — returns a dict of diagnostic check results. Each check has a `severity` and a human-readable `title`/`details`.

### Diagnostic Checks

| # | Title | Severity | Trigger condition |
|---|-------|----------|-------------------|
| 1 | Next run date in future | `info` | `next_run_date > now` |
| 2 | Scheduler not running | `blocking` | Non-ADHOC task but no active cron for the project |
| 3 | Pre-action failed | `blocking` | One or more pre-actions have a failed status |
| 4 | State is cancelled | `blocking` | `state == "cancelled"` |
| 5 | User cancellation requested | `blocking` | `user_set_state == "cancel"` |
| 6 | End date passed | `blocking` | `end_date < now` |
| 7 | State not schedulable | `warning` | State not in `["scheduled", "success"]` |
| 8 | Required item deleted | `blocking` | Operator, connection, payload, workflow, or attached config is missing/deleted |
| 9 | Stuck in connection queue | `blocking` | State is `running` and heartbeat is stale |
| 10 | Celery not running | `warning` | State is `queued_in_redis` and no worker heartbeat detected |

**Severity meanings:**

| Severity | Meaning |
|----------|---------|
| `blocking` | This condition is actively preventing the task from running |
| `warning` | Something looks wrong but may not be the root cause |
| `info` | Informational — task will run when this condition resolves |

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Task not found |
| 500 | Internal server error |
