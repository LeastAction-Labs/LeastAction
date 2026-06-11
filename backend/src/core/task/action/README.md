# Action System

The Action System provides a flexible mechanism for executing operations both as part of task lifecycle and independently. Actions are self-contained units of work that can perform validations, monitoring, notifications, data processing, and other operations either standalone or in coordination with task execution.

## Table of Contents

- [Overview](#overview)
- [Action Execution Modes](#action-execution-modes)
- [Action Types (Task Lifecycle)](#action-types-task-lifecycle)
- [Independent Action Execution](#independent-action-execution)
- [Architecture](#architecture)
- [Action Schema](#action-schema)
- [ActionManager](#actionmanager)
- [Action Lifecycle](#action-lifecycle)
- [Creating Actions](#creating-actions)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Actions in LeastAction are operations that can be executed in two distinct modes:

1. **Task Lifecycle Actions**: Execute at specific points during task execution (pre, running, post, create)
2. **Independent Actions**: Execute standalone via API, not tied to any task

Unlike the main task operation, actions are:

- **Asynchronous**: Executed via Celery workers
- **Independent**: Can succeed or fail without directly affecting other operations
- **Configurable**: Each action has its own variables and optional SLA
- **Session-aware**: Automatically injected with session and context
- **Reusable**: Can be executed multiple times with different parameters

**Key Benefits:**
- Decouple validation logic from task execution
- Execute operations on-demand without creating tasks
- Add monitoring without modifying core task logic
- Implement cleanup operations independently
- Enable conditional task execution via pre-actions
- Provide extensibility points for custom workflows

## Action Execution Modes

### 1. Task Lifecycle Actions

Actions attached to tasks that execute at specific points in the task lifecycle:

```python
task = {
    "name": "ETL Job",
    "actions": {
        "pre_actions": [...],      # Before task execution
        "running_actions": [...],   # During task execution
        "post_actions": [...]       # After task execution
    }
}
```

**Use Cases:**
- Pre-flight validation before expensive operations
- Monitoring task progress
- Cleanup after task completion

### 2. Independent Actions

Actions executed standalone via REST API, not tied to any task:

```bash
POST /api/action/run
{
    "item_type": "action",
    "item_laui": "existing_action_id",  # Optional
    "connection_laui": "connection_id",  # Optional
    "action_variables": {
        "param1": "value1"
    }
}
```

**Use Cases:**
- On-demand data processing
- Ad-hoc notifications
- Manual operations
- Testing action operators
- Utility functions (data validation, file cleanup, etc.)

## Action Types (Task Lifecycle)

When used as part of task lifecycle, actions are categorized into four types based on when they execute and their blocking behavior:

| Type | When Executed | Blocks Task? | Wait for Result? | Timeout | Use Cases |
|------|---------------|--------------|------------------|---------|-----------|
| **create_actions** | During task creation | No | No | N/A | Initialize resources, register callbacks, create audit logs |
| **pre_actions** | Before task execution | **YES** | **YES** | `action_timeout_seconds` | Validate preconditions, check resource availability, acquire locks |
| **running_actions** | During task execution | No | No | N/A | Monitor progress, send status updates, log metrics |
| **post_actions** | After task execution | No | No | N/A | Cleanup resources, send notifications, update dependent systems |

### create_actions

**Execution Point**: When a task is created in the system

**Characteristics:**
- Fire-and-forget (asynchronous)
- Does not block task creation
- Useful for setup operations that don't need to complete immediately

**Example Use Cases:**
- Register task in external monitoring system
- Create audit log entry
- Initialize workspace or temporary resources
- Send creation notification to stakeholders

### pre_actions

**Execution Point**: Immediately before task execution

**Characteristics:**
- **Blocking**: Task will NOT execute if pre-actions fail
- **Synchronous**: Waits for completion with timeout
- **Critical**: Failure prevents task execution
- Configured timeout (default from `system.yml`)

**Example Use Cases:**
- Validate data prerequisites exist
- Check API rate limits
- Verify database connectivity
- Acquire distributed locks
- Validate schema compatibility
- Check disk space availability

**Important**: Keep pre-actions fast and focused. They block task execution, so slow pre-actions delay workflows.

### running_actions

**Execution Point**: Concurrently with task execution

**Characteristics:**
- Fire-and-forget (asynchronous)
- Does not block or wait
- Runs in parallel with main task

**Example Use Cases:**
- Monitor task progress
- Log real-time metrics
- Send status updates to dashboards
- Update progress bars in UI
- Publish status to message queues

### post_actions

**Execution Point**: After task execution completes

**Characteristics:**
- Fire-and-forget (asynchronous)
- Does not block task completion
- Runs regardless of task success/failure

**Example Use Cases:**
- Send completion notifications
- Cleanup temporary files
- Release acquired resources
- Update dependent systems
- Archive results
- Trigger downstream workflows

## Independent Action Execution

Actions can be executed independently via the REST API without being attached to any task. This provides a flexible way to run operations on-demand.

### API Endpoint

**URL**: `POST /api/action/run`

**Purpose**: Execute an action independently, either by referencing an existing action item or creating a new one inline.

### Request Format

```json
{
    "item_type": "action",
    "item_laui": "existing_action_laui",    // Optional: Reference existing action
    "connection_laui": "connection_laui",   // Optional: Connection to use
    "action_variables": {                   // Required: Parameters for the action
        "param1": "value1",
        "param2": "value2"
    }
}
```

### Execution Flow

```
REST API Request
    ↓
ItemOrchestrator.execute_action()
    ↓
┌─────────────────────────────────────┐
│ If item_laui provided:              │
│   - Fetch existing action item      │
│   - Validate item_type is "action"  │
│ Else:                                │
│   - Create new action item          │
│   - Store in catalog                │
└─────────────────────────────────────┘
    ↓
Fetch connection (if connection_laui provided)
    ↓
Construct ActionItem
    ├─> laui: action_laui
    ├─> task_laui: action_laui (self-reference)
    ├─> session_id: current session
    ├─> connection_laui: from request
    ├─> connection: parsed connection content
    └─> action_variables: from request
    ↓
ActionManager.create_actions()
    ↓
Submit to Celery (async, fire-and-forget)
    ↓
Return response with action_laui
```

### Two Execution Modes

#### Mode 1: Execute Existing Action

Execute a previously created action item with new parameters.

**Request:**
```json
{
    "item_type": "action",
    "item_laui": "507f1f77bcf86cd799439011",
    "connection_laui": "507f1f77bcf86cd799439012",
    "action_variables": {
        "recipient": "user@example.com",
        "message": "Hello from action!"
    }
}
```

**Use Cases:**
- Reuse configured actions with different inputs
- Test actions before attaching to tasks
- Manual operations using predefined actions

#### Mode 2: Create and Execute Action

Create a new action item and execute it immediately.

**Request:**
```json
{
    "item_type": "action",
    "name": "Send Notification",
    "operator_laui": "507f1f77bcf86cd799439013",
    "connection_laui": "507f1f77bcf86cd799439014",
    "action_variables": {
        "channel": "#alerts",
        "message": "System maintenance starting"
    },
    "project_laui": "507f1f77bcf86cd799439015",
    "account_laui": "507f1f77bcf86cd799439016"
}
```

**Use Cases:**
- One-off operations
- Dynamic action creation
- Ad-hoc workflows

### Response Format

```json
{
    "item_laui": "507f1f77bcf86cd799439017"
}
```

The response contains the LAUI of the executed action. The action runs asynchronously in Celery.

### Key Characteristics

- **Asynchronous**: Returns immediately, action runs in background
- **Fire-and-forget**: No status or result returned directly
- **Session-aware**: Automatically tagged with session_id for tracking
- **Self-referencing**: task_laui points to action_laui (not part of a task)
- **Connection support**: Can use connections just like task-based actions

### Differences from Task Lifecycle Actions

| Feature | Task Lifecycle Actions | Independent Actions |
|---------|------------------------|---------------------|
| Execution trigger | Task creation/execution | REST API call |
| task_laui | Points to parent task | Points to action itself |
| Typed (pre/post/etc) | Yes | No (always fire-and-forget) |
| Blocking capability | Yes (pre_actions) | No |
| Return value | Success/failure for pre_actions | Just action_laui |
| Use case | Task orchestration | On-demand operations |

### Example Use Cases

#### 1. Manual Data Validation

```bash
curl -X POST /api/action/run \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "action",
    "item_laui": "validate_data_action_laui",
    "connection_laui": "database_connection_laui",
    "action_variables": {
      "table": "users",
      "schema_version": "v2.0",
      "sample_size": 1000
    }
  }'
```

#### 2. Send Ad-hoc Notification

```bash
curl -X POST /api/action/run \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "action",
    "item_laui": "slack_notification_action_laui",
    "connection_laui": "slack_connection_laui",
    "action_variables": {
      "channel": "#incidents",
      "message": "Database backup completed manually",
      "priority": "low"
    }
  }'
```

#### 3. Test Action Before Task Integration

```bash
# Test an action operator with sample data
curl -X POST /api/action/run \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "action",
    "item_laui": "new_action_operator_laui",
    "action_variables": {
      "test_param": "test_value",
      "dry_run": true
    }
  }'
```

#### 4. Cleanup Utility

```bash
curl -X POST /api/action/run \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "action",
    "item_laui": "cleanup_temp_files_action_laui",
    "connection_laui": "file_system_connection_laui",
    "action_variables": {
      "directory": "/tmp/old_data",
      "older_than_days": 7
    }
  }'
```

### Implementation Details

**File**: `src/core/catalog/orchestrator.py` (lines 112-153)

**Key Logic:**
1. Check if `item_laui` is provided
   - If yes: Fetch existing action item, validate it's type "action"
   - If no: Create new action item using provided fields
2. If `connection_laui` provided, fetch and parse connection
3. Construct `ActionItem` with:
   - laui, task_laui (self-ref), session_id
   - connection_laui, connection content
   - action_variables from request
4. Execute via `ActionManager.create_actions()`
5. Return action LAUI

**Validation:**
- Item must be of type "action"
- Connection (if provided) must be of type "connection"
- Request item_type must be "action"

### Monitoring Independent Actions

Since independent actions are fire-and-forget, monitoring requires:

1. **Session ID tracking**: Filter logs by session_id
   ```bash
   grep "session_id: abc123" logs/celery.log
   ```

2. **Action LAUI tracking**: Search for action_laui in execution logs
   ```bash
   grep "action_laui: 507f1f77bcf86cd799439017" logs/celery.log
   ```

3. **Celery task monitoring**: Use Celery tools to track async results
   ```python
   from celery.result import AsyncResult
   result = AsyncResult(task_id)
   print(result.state)  # PENDING, SUCCESS, FAILURE
   ```

4. **Custom logging**: Implement logging within action operators
   ```python
   def my_action_operator(action_item: ActionItem):
       log_info(
           "action",
           "MyAction",
           "execute",
           f"Action {action_item.laui} executing with vars: {action_item.action_variables}"
       )
   ```

## Architecture

```
Task Execution Flow with Actions
─────────────────────────────────

1. Task Creation
   └─> create_actions (async) ───> Celery Worker

2. Task Validation
   └─> TaskValidationManager

3. Pre-Actions (Blocking)
   └─> ActionManager.pre_actions()
       ├─> Inject session_id & task_laui
       ├─> Submit to Celery
       └─> WAIT for result (timeout: action_timeout_seconds)
           ├─> Success: Continue to task execution
           └─> Failure: Abort task execution

4. Task Execution
   ├─> running_actions (async) ───> Celery Worker
   └─> CeleryOrchestrator.run_task()

5. Post-Execution
   └─> post_actions (async) ───> Celery Worker
```

## Action Schema

### ActionItem

Represents a single action to be executed.

**File**: `schema.py`

```python
class ActionItem(BaseAction):
    laui: str                                # Action operator LAUI (required)
    task_laui: Optional[str] = None          # Task LAUI (injected by ActionManager)
    session_id: Optional[str] = None         # Session ID (injected by ActionManager)
    connection_laui: Optional[str] = None    # Connection to use (optional)
    connection: Optional[str] = None         # Connection details (optional)
    action_variables: Dict[str, Any]         # Action-specific parameters
    sla: Optional[int] = None                # Service Level Agreement in seconds
```

**Field Descriptions:**

- **laui**: The operator LAUI that defines what this action does. Points to an operator item in the catalog.
- **task_laui**: Automatically injected by ActionManager. Links action execution to parent task.
- **session_id**: Automatically injected by ActionManager. Provides session context for logging/tracking.
- **connection_laui**: Optional. If action needs to connect to external system (DB, API, etc.)
- **connection**: Optional. Parsed connection details available during execution.
- **action_variables**: Dictionary of parameters specific to this action. Structure depends on the operator.
- **sla**: Optional. Expected completion time in seconds. Can be used for monitoring/alerting.

### Actions

Container for all action types associated with a task.

```python
class Actions(BaseModel):
    create_actions: List[ActionItem] = []
    pre_actions: List[ActionItem] = []
    running_actions: List[ActionItem] = []
    post_actions: List[ActionItem] = []
```

**Usage in Task Model:**

```python
task = TaskValidationModel(
    name="ETL Job",
    # ... other fields ...
    actions={
        "pre_actions": [
            {
                "laui": "validate_schema_operator_laui",
                "action_variables": {"schema_version": "v2.0"}
            }
        ],
        "post_actions": [
            {
                "laui": "send_email_operator_laui",
                "connection_laui": "smtp_connection_laui",
                "action_variables": {
                    "to": "team@example.com",
                    "subject": "ETL completed"
                }
            }
        ]
    }
)
```

### ActionType Enum

```python
class ActionType(str, Enum):
    PRE_ACTIONS = "pre_actions"
    POST_ACTIONS = "post_actions"
    RUNNING_ACTIONS = "running_actions"
    CREATE_ACTIONS = "create_actions"
```

## ActionManager

**File**: `action_manager.py`

The ActionManager orchestrates action execution, handles timeouts, and integrates with Celery.

### Initialization

```python
class ActionManager:
    def __init__(self, celery_orchestrator: CeleryOrchestrator):
        self.timeout = int(load_system_config()["action_timeout_seconds"])
        self.celery_orchestrator = celery_orchestrator
```

**Configuration** (`config/system.yml`):

```yaml
action_timeout_seconds: 30  # Timeout for blocking actions (pre_actions)
```

### Key Methods

#### `create_actions(la_actions_object: Actions, task_laui: str) -> bool`

Executes create-time actions (fire-and-forget).

```python
result = action_manager.create_actions(actions, task_laui)
# Returns immediately without waiting
```

#### `pre_actions(la_actions_object: Actions, task_laui: str) -> bool`

Executes pre-actions with blocking and timeout.

**Returns**: `True` if all actions succeeded, `False` if any failed or timed out

```python
success = action_manager.pre_actions(actions, task_laui)
if not success:
    # Abort task execution
    log_error("Pre-actions failed, task will not execute")
    return
# Proceed with task execution
```

**Behavior:**
- Waits for each action to complete
- Respects `action_timeout_seconds` timeout
- Returns `False` on first failure (fail-fast)
- Each action failure is logged

#### `running_actions(la_actions_object: Actions, task_laui: str) -> None`

Executes running actions (fire-and-forget).

```python
action_manager.running_actions(actions, task_laui)
# Returns immediately, actions run in background
```

#### `post_actions(la_actions_object: Actions, task_laui: str) -> None`

Executes post-execution actions (fire-and-forget).

```python
action_manager.post_actions(actions, task_laui)
# Returns immediately, actions run in background
```

### Private Helper: `_run_action_with_timeout()`

Core execution logic for all action types.

**Parameters:**
- `actions_list`: List of ActionItem to execute
- `action_type`: String identifier (for logging)
- `task_laui`: Task identifier
- `wait_for_result`: Whether to block and wait (default: False)

**Process:**
1. Inject `session_id` and `task_laui` into each ActionItem
2. Submit action to Celery via `celery_orchestrator.run_action()`
3. If `wait_for_result=True`:
   - Call `async_result.get(timeout=self.timeout)`
   - Return `False` on timeout or failure
   - Return `True` if all succeed
4. If `wait_for_result=False`:
   - Return immediately after submission
   - Return `None` (no result)

**Error Handling:**
- Logs each action dispatch
- Logs timeouts and failures
- Continues to next action unless `wait_for_result=True` and action fails

## Action Lifecycle

### Complete Lifecycle Example

```python
# 1. Task Creation
task = create_task({
    "name": "Data Import",
    "actions": {
        "create_actions": [...],
        "pre_actions": [...],
        "running_actions": [...],
        "post_actions": [...]
    }
})

# create_actions executed here (async)
action_manager.create_actions(Actions(**task.actions), str(task.laui))

# 2. Task Validation
validated_task = await task_manager.validate_task_creation(task)

# 3. Task Execution Request
# ... time passes ...

# 4. Pre-Actions (BLOCKING)
pre_success = action_manager.pre_actions(
    Actions(**task.actions),
    str(task.laui)
)

if not pre_success:
    # Task execution aborted
    log_error("Pre-actions failed")
    return

# 5. Task Execution + Running Actions
action_manager.running_actions(Actions(**task.actions), str(task.laui))
result = celery_orchestrator.run_task(task)

# 6. Post-Actions (after task completes)
action_manager.post_actions(Actions(**task.actions), str(task.laui))
```

## Creating Actions

### Step 1: Define Action Operator

Actions are executed by operators. First, create an operator that defines the action logic.

**Example**: Email notification operator

```python
# In your operator implementation
def send_email_action(action_item: ActionItem):
    to = action_item.action_variables['to']
    subject = action_item.action_variables['subject']
    body = action_item.action_variables.get('body', '')

    # Use connection if provided
    if action_item.connection:
        smtp_config = action_item.connection
        # ... send email using smtp_config

    return True  # Success
```

### Step 2: Register Operator in Catalog

Create an operator item in the catalog with your action logic.

```python
operator = {
    "name": "Email Notification Action",
    "item_type": "operator.email",
    "codeblock": "...",  # Your action implementation
    # ... other operator fields
}
```

### Step 3: Use Action in Task Definition

Reference the operator LAUI in your task's actions.

```python
task = {
    "name": "Daily Report",
    "actions": {
        "post_actions": [
            {
                "laui": "email_operator_laui",
                "connection_laui": "smtp_connection_laui",
                "action_variables": {
                    "to": "team@example.com",
                    "subject": "Daily Report Complete",
                    "body": "The daily report has been generated successfully."
                },
                "sla": 10  # Expected to complete in 10 seconds
            }
        ]
    }
}
```

## Usage Examples

### Example 1: Pre-Action for Resource Validation

**Scenario**: Validate that source data exists before running expensive ETL job.

```python
actions = {
    "pre_actions": [
        {
            "laui": "check_s3_file_exists_operator",
            "connection_laui": "s3_connection",
            "action_variables": {
                "bucket": "data-lake",
                "key": "raw/{{ ds }}/input.csv",
                "min_size_bytes": 1000
            },
            "sla": 5
        }
    ]
}

task = TaskCreationValidationModel(
    name="ETL Job",
    operator_laui=etl_operator,
    connection_laui=warehouse_connection,
    actions=actions,
    # ... other fields
)
```

**Result**: ETL job only runs if input file exists and meets size requirement.

### Example 2: Running Action for Progress Monitoring

**Scenario**: Send progress updates to dashboard while long-running task executes.

```python
actions = {
    "running_actions": [
        {
            "laui": "publish_progress_operator",
            "connection_laui": "redis_connection",
            "action_variables": {
                "channel": "task_progress",
                "interval_seconds": 30
            }
        }
    ]
}

task = TaskCreationValidationModel(
    name="Large Data Processing",
    operator_laui=processing_operator,
    connection_laui=spark_connection,
    actions=actions,
    # ... other fields
)
```

**Result**: Progress updates published every 30 seconds while task runs.

### Example 3: Multiple Pre-Actions (Sequential)

**Scenario**: Multiple validations must pass before task execution.

```python
actions = {
    "pre_actions": [
        {
            "laui": "check_api_rate_limit_operator",
            "connection_laui": "api_connection",
            "action_variables": {
                "min_remaining": 100
            },
            "sla": 2
        },
        {
            "laui": "validate_schema_operator",
            "connection_laui": "db_connection",
            "action_variables": {
                "table": "target_table",
                "expected_schema": "v2.0"
            },
            "sla": 5
        },
        {
            "laui": "acquire_lock_operator",
            "connection_laui": "redis_connection",
            "action_variables": {
                "lock_key": "etl_job_lock",
                "ttl_seconds": 3600
            },
            "sla": 3
        }
    ]
}
```

**Result**: Task runs only if all three validations pass. They execute sequentially.

### Example 4: Post-Actions for Cleanup and Notification

**Scenario**: After task completes, cleanup temp files and notify stakeholders.

```python
actions = {
    "post_actions": [
        {
            "laui": "cleanup_temp_files_operator",
            "connection_laui": "file_system_connection",
            "action_variables": {
                "directory": "/tmp/task_{{ task_laui }}",
                "max_age_hours": 0  # Delete immediately
            }
        },
        {
            "laui": "send_slack_notification_operator",
            "connection_laui": "slack_connection",
            "action_variables": {
                "channel": "#data-ops",
                "message": "Task {{ task_name }} completed at {{ ts }}"
            }
        },
        {
            "laui": "update_data_catalog_operator",
            "connection_laui": "catalog_api_connection",
            "action_variables": {
                "dataset_id": "analytics_daily",
                "last_updated": "{{ ts }}"
            }
        }
    ]
}
```

**Result**: Cleanup and notifications happen asynchronously after task completion.

### Example 5: Complete Action Lifecycle

**Scenario**: Complex workflow with actions at every stage.

```python
actions = {
    "create_actions": [
        {
            "laui": "create_audit_log_operator",
            "connection_laui": "audit_db_connection",
            "action_variables": {
                "event_type": "task_created",
                "task_name": "{{ task_name }}"
            }
        }
    ],
    "pre_actions": [
        {
            "laui": "validate_prerequisites_operator",
            "action_variables": {
                "checks": ["data_available", "resources_ready"]
            },
            "sla": 10
        }
    ],
    "running_actions": [
        {
            "laui": "monitor_metrics_operator",
            "connection_laui": "metrics_connection",
            "action_variables": {
                "metrics": ["cpu_usage", "memory_usage"],
                "interval_seconds": 60
            }
        }
    ],
    "post_actions": [
        {
            "laui": "cleanup_resources_operator",
            "action_variables": {
                "resource_types": ["temp_files", "cache"]
            }
        },
        {
            "laui": "send_completion_email_operator",
            "connection_laui": "smtp_connection",
            "action_variables": {
                "recipients": ["team@example.com"]
            }
        }
    ]
}
```

### Example 6: Independent Action Execution

**Scenario**: Execute actions on-demand via API without creating tasks.

#### 6a. Execute Existing Action with New Parameters

Execute a pre-configured validation action with different parameters:

```bash
curl -X POST http://localhost:8000/api/action/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "item_type": "action",
    "item_laui": "507f1f77bcf86cd799439011",
    "connection_laui": "507f1f77bcf86cd799439012",
    "action_variables": {
      "database": "analytics",
      "table": "user_events",
      "check_type": "row_count",
      "min_rows": 1000
    }
  }'
```

**Response:**
```json
{
  "item_laui": "507f1f77bcf86cd799439011"
}
```

**Result**: Validation runs immediately in background. Check logs with session_id to track progress.

#### 6b. Create and Execute New Action

Create a new notification action and execute it immediately:

```bash
curl -X POST http://localhost:8000/api/action/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "item_type": "action",
    "name": "Emergency Alert",
    "operator_laui": "507f1f77bcf86cd799439013",
    "connection_laui": "507f1f77bcf86cd799439014",
    "action_variables": {
      "severity": "high",
      "channel": "#incidents",
      "message": "Production database CPU usage exceeded 90%",
      "mentions": ["@oncall"]
    },
    "project_laui": "507f1f77bcf86cd799439015",
    "account_laui": "507f1f77bcf86cd799439016"
  }'
```

**Response:**
```json
{
  "item_laui": "507f1f77bcf86cd799439017"
}
```

**Result**: New action item created in catalog and executed immediately.

#### 6c. Cleanup Utility Action

Execute a cleanup action to delete old temporary files:

```bash
curl -X POST http://localhost:8000/api/action/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "item_type": "action",
    "item_laui": "cleanup_action_laui",
    "connection_laui": "s3_connection_laui",
    "action_variables": {
      "bucket": "temporary-data",
      "prefix": "exports/",
      "older_than_days": 30,
      "dry_run": false
    }
  }'
```

**Result**: S3 cleanup runs asynchronously, deleting files older than 30 days.

#### 6d. Test Action Before Task Integration

Test a new action operator before attaching it to tasks:

```python
import requests

# Test with various inputs
test_cases = [
    {"input": "valid_data.csv", "expected": "success"},
    {"input": "empty_data.csv", "expected": "failure"},
    {"input": "malformed.csv", "expected": "error"}
]

for test in test_cases:
    response = requests.post(
        "http://localhost:8000/api/action/run",
        headers={"Cookie":f"frontend_token={token}"},
        json={
            "item_type": "action",
            "item_laui": "file_validator_action_laui",
            "connection_laui": "file_system_connection_laui",
            "action_variables": {
                "file_path": f"/test/data/{test['input']}",
                "validation_rules": ["not_empty", "valid_csv"]
            }
        }
    )
    print(f"Test {test['input']}: {response.json()}")
```

**Result**: Multiple test executions validate action behavior before production use.

#### 6e. Python SDK Example

```python
from least_action_client import ActionClient

client = ActionClient(api_url="http://localhost:8000", token=token)

# Execute existing action
result = client.execute_action(
    action_laui="data_export_action_laui",
    connection_laui="postgres_connection_laui",
    action_variables={
        "query": "SELECT * FROM orders WHERE created_at >= '2026-01-01'",
        "output_format": "parquet",
        "s3_path": "s3://exports/orders/2026-01-08.parquet"
    }
)

print(f"Action executed: {result['item_laui']}")

# Create and execute new action
result = client.create_and_execute_action(
    name="Weekly Report Generation",
    operator_laui="report_generator_operator_laui",
    connection_laui="reporting_connection_laui",
    action_variables={
        "report_type": "weekly_sales",
        "week_start": "2026-01-01",
        "recipients": ["management@example.com"]
    },
    project_laui=project_id,
    account_laui=account_id
)

print(f"New action created and executed: {result['item_laui']}")
```

## Best Practices

### 1. Action Design

- **Single Responsibility**: Each action should do one thing well
- **Idempotency**: Actions should be safe to retry without side effects
- **Error Handling**: Actions should handle errors gracefully and return meaningful status
- **Logging**: Use structured logging with session_id and task_laui for traceability
- **Timeouts**: Set realistic SLA values based on action complexity

### 2. Pre-Actions

- **Keep Fast**: Pre-actions block task execution - aim for < 10 seconds
- **Fail Fast**: Return `False` quickly if precondition not met
- **Critical Only**: Only use pre-actions for truly blocking validations
- **Order Matters**: Place fastest/most likely to fail checks first
- **Avoid External Dependencies**: Minimize network calls when possible

**Good Pre-Action Examples:**
- Check file existence
- Validate configuration
- Verify resource availability
- Acquire locks

**Bad Pre-Action Examples:**
- Complex data transformations (use task instead)
- Long-running API calls (use async pre-fetch in create_actions)
- Heavy database queries (cache results if possible)

### 3. Running Actions

- **Fire-and-Forget**: Don't expect results from running actions
- **Independent**: Running actions should not depend on each other
- **Non-Critical**: Task should succeed even if running action fails
- **Periodic**: Use intervals for monitoring rather than continuous polling

**Good Running Action Examples:**
- Send progress updates
- Log metrics
- Update status indicators

**Bad Running Action Examples:**
- Modifying task data (race conditions)
- Critical validations (use pre-actions)
- Resource cleanup (use post-actions)

### 4. Post-Actions

- **Cleanup**: Perfect for releasing resources, deleting temp files
- **Notifications**: Inform stakeholders of completion
- **Independent**: Don't assume task succeeded - check status if needed
- **Async-Friendly**: Can take longer since they don't block

**Good Post-Action Examples:**
- Send notifications
- Update downstream systems
- Archive results
- Release locks

**Bad Post-Action Examples:**
- Critical operations that must complete (no guarantee of execution)
- Actions that must run before next task (use workflow dependencies)

### 5. Action Variables

- **Explicit**: Clearly name parameters
- **Documented**: Comment expected structure for complex variables
- **Validated**: Validate within action operator implementation
- **Typed**: Use consistent types (don't mix strings and objects)
- **Defaults**: Provide sensible defaults when possible

```python
# Good
action_variables = {
    "retry_attempts": 3,
    "retry_delay_seconds": 60,
    "timeout_seconds": 300
}

# Bad
action_variables = {
    "config": "3,60,300"  # Unclear structure
}
```

### 6. Error Handling

- **Log Context**: Include task_laui, session_id in error logs
- **Specific Errors**: Use specific exception types for different failures
- **Graceful Degradation**: Non-critical actions should not crash
- **Retry Logic**: Implement retry logic for transient failures
- **Status Reporting**: Return clear success/failure indication

### 7. Testing Actions

- **Unit Tests**: Test action operators independently
- **Integration Tests**: Test action execution via ActionManager
- **Timeout Tests**: Verify timeout behavior for pre-actions
- **Failure Tests**: Test task behavior when actions fail
- **Mock Celery**: Use mocks to avoid actual Celery infrastructure in tests

```python
# Example test structure
def test_pre_action_failure_aborts_task():
    # Mock pre-action to fail
    mock_action = create_failing_action()

    # Execute
    success = action_manager.pre_actions(mock_action, task_laui)

    # Assert
    assert success is False
    # Task should not have been executed
```

### 8. Independent Action Execution

- **Purpose-Built**: Create action items specifically designed for independent execution
- **Reusability**: Design actions that can work both in task lifecycle and independently
- **Parameter Validation**: Always validate action_variables since they come from API requests
- **Connection Management**: Explicitly provide connection_laui when needed
- **Monitoring**: Implement proper logging since there's no task context
- **Error Handling**: Handle errors gracefully as failures are fire-and-forget

**Good Independent Action Use Cases:**
- Manual data validation or cleanup
- On-demand notifications or alerts
- Testing action operators before task integration
- Utility operations (file cleanup, data exports)
- Administrative tasks

**Bad Independent Action Use Cases:**
- Operations that need task orchestration (use tasks instead)
- Operations requiring blocking/waiting for results (use synchronous endpoints)
- Complex workflows with dependencies (use tasks and workflows)

**API Usage Best Practices:**

```bash
# Good: Explicit parameters, clear purpose
curl -X POST /api/action/run -d '{
  "item_type": "action",
  "item_laui": "cleanup_action_laui",
  "connection_laui": "s3_connection_laui",
  "action_variables": {
    "bucket": "temp-data",
    "older_than_days": 7,
    "dry_run": false
  }
}'

# Bad: Unclear parameters, missing context
curl -X POST /api/action/run -d '{
  "item_type": "action",
  "item_laui": "some_action",
  "action_variables": {
    "data": "something"
  }
}'
```

**Operator Design for Independent Actions:**

```python
def independent_action_operator(action_item: ActionItem):
    # Always validate inputs
    required_vars = ['param1', 'param2']
    for var in required_vars:
        if var not in action_item.action_variables:
            log_error("action", "Operator", "execute", f"Missing required variable: {var}")
            return False

    # Log context for traceability
    log_info(
        "action",
        "Operator",
        "execute",
        f"Executing independent action {action_item.laui} "
        f"with session {action_item.session_id}"
    )

    # Implement idempotent logic
    # ... action logic ...

    return True
```

**When to Create vs. Reference Actions:**

- **Reference existing (item_laui)**: When you have a configured action you want to reuse with different parameters
- **Create new**: When you need a one-off operation or testing a new action operator

## Troubleshooting

### Common Issues

#### Pre-Action Timeout

**Symptom**: Task not executing, logs show "pre_action timed out"

**Causes:**
- Action taking longer than `action_timeout_seconds`
- Network latency to external services
- Action operator hanging or deadlocked

**Solutions:**
1. Increase timeout in `config/system.yml`:
   ```yaml
   action_timeout_seconds: 60  # Increase from 30
   ```
2. Optimize action operator for speed
3. Move slow operations to create_actions or post_actions
4. Use async patterns in action operator

#### Pre-Action Returns False

**Symptom**: Task not executing, logs show "Pre_actions execution completed: False"

**Causes:**
- Precondition not met (expected behavior)
- Action operator error

**Solutions:**
1. Check action operator logs for specific failure reason
2. Verify preconditions are actually met
3. Add detailed logging to action operator
4. Test action operator independently

#### Actions Not Executing

**Symptom**: No action logs, actions seem to be skipped

**Causes:**
- Empty actions list
- Celery workers not running
- Action submission error

**Solutions:**
1. Verify actions list is not empty: `log_info(actions)`
2. Check Celery worker status: `celery -A app worker -l info`
3. Check for submission errors in ActionManager logs
4. Verify action LAUIs exist in catalog

#### Action Variables Not Accessible

**Symptom**: KeyError when accessing action_variables in operator

**Causes:**
- Variables not passed correctly
- Variable name mismatch
- Variables not JSON-serializable (for Celery)

**Solutions:**
1. Log action_variables in ActionManager before submission
2. Use `.get()` with defaults in operators:
   ```python
   value = action_item.action_variables.get('key', default_value)
   ```
3. Ensure all variables are JSON-serializable (no custom objects)

#### Session Context Missing

**Symptom**: session_id or task_laui is None in action operator

**Causes:**
- ActionManager not injecting context
- Old action submission bypassing ActionManager

**Solutions:**
1. Always use ActionManager methods, not direct Celery calls
2. Verify ActionManager version includes injection logic
3. Check logs for injection confirmation

### Debug Checklist

When actions aren't working as expected:

- [ ] Check ActionManager logs for execution attempts
- [ ] Verify Celery workers are running and processing tasks
- [ ] Confirm action operator LAUIs exist in catalog
- [ ] Validate action_variables structure matches operator expectations
- [ ] Check system.yml for correct timeout configuration
- [ ] Review action operator logs for errors
- [ ] Test action operator independently (outside task context)
- [ ] Verify connections (if used) are valid and accessible
- [ ] Check for Celery task serialization errors
- [ ] Confirm session_id and task_laui are injected correctly

### Logging for Debugging

Enable detailed logging:

```python
# In action operator
log_info(
    "api",
    "CustomAction",
    "execute",
    f"Executing action with variables: {action_item.action_variables}, "
    f"session_id: {action_item.session_id}, task_laui: {action_item.task_laui}"
)
```

Check ActionManager logs:
```bash
# Filter for action-related logs
grep "ActionManager" logs/api.log
```

Monitor Celery worker logs:
```bash
# Watch Celery worker output
celery -A app worker -l debug
```

## Related Documentation

- [Task Module README](../README.md) - Complete task system documentation
- [Config Manager README](../config/README.md) - Configuration and placeholder replacement
- [Operator Development Guide](../../../../docs/operator_development.md) - Creating action operators
- [Celery Integration](../../../celery/README.md) - Async execution infrastructure

## Configuration Reference

### system.yml Settings

```yaml
# Action timeout for blocking pre-actions (seconds)
action_timeout_seconds: 30

# Connection-operator mappings (for actions using connections)
connection_operator_mapping:
  connection.http:
    - operator.http_request
  connection.smtp:
    - operator.email
  # ... other mappings
```

## API Reference

### ActionManager Methods

```python
class ActionManager:
    def __init__(self, celery_orchestrator: CeleryOrchestrator)

    def create_actions(
        self,
        la_actions_object: Actions,
        task_laui: str
    ) -> bool

    def pre_actions(
        self,
        la_actions_object: Actions,
        task_laui: str
    ) -> bool

    def running_actions(
        self,
        la_actions_object: Actions,
        task_laui: str
    ) -> None

    def post_actions(
        self,
        la_actions_object: Actions,
        task_laui: str
    ) -> None
```

### Schema Classes

```python
class ActionItem(BaseAction):
    laui: str
    task_laui: Optional[str] = None
    session_id: Optional[str] = None
    connection_laui: Optional[str] = None
    connection: Optional[str] = None
    action_variables: Dict[str, Any]
    sla: Optional[int] = None

class Actions(BaseModel):
    create_actions: List[ActionItem] = []
    pre_actions: List[ActionItem] = []
    running_actions: List[ActionItem] = []
    post_actions: List[ActionItem] = []

class ActionType(str, Enum):
    PRE_ACTIONS = "pre_actions"
    POST_ACTIONS = "post_actions"
    RUNNING_ACTIONS = "running_actions"
    CREATE_ACTIONS = "create_actions"
```
