# Task Module

The Task module is a core component of the LeastAction system responsible for orchestrating, validating, and executing tasks. It provides a complete lifecycle management system for tasks that includes configuration merging, connection validation, action execution, and integration with Celery for asynchronous task processing.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Task Models](#task-models)
- [Task Lifecycle](#task-lifecycle)
- [Components](#components)
  - [TaskManager](#taskmanager)
  - [TaskValidationManager](#taskvalidationmanager)
  - [ActionManager](#actionmanager)
  - [ConnectionManager](#connectionmanager)
  - [ConfigManager](#configmanager)
- [Actions System](#actions-system)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The Task module provides:
- **Task Creation Validation**: Validates task structure, dependencies, and constraints before creation
- **Task Execution Validation**: Validates tasks are ready for execution (connection-operator mapping, payload constraints, placeholder replacement)
- **Configuration Management**: Merges configs from 3 sources during task creation (workflow config + attached config + inline task config) and replaces placeholders
- **Connection Validation**: Ensures connection-operator compatibility
- **Action Lifecycle**: Manages pre-actions, running-actions, and post-actions
- **Async Execution**: Integrates with Celery for distributed task execution

## Architecture

```
TaskManager (Orchestrator)
    ├── TaskValidationManager (Validation Logic)
    │   ├── ConfigManager (Config Merging & Placeholder Replacement)
    │   ├── ConnectionManager (Connection-Operator Validation)
    │   └── CatalogService (Item Retrieval)
    ├── ActionManager (Action Execution)
    │   └── CeleryOrchestrator (Async Actions)
    └── CeleryOrchestrator (Async Task Execution)
```

## Task Models

### BaseTaskModel

Core data structure for a task:

```python
class BaseTaskModel(ItemBase):
    name: str                                    # Task name
    operator_laui: PydanticObjectId              # Operator to execute
    connection_laui: PydanticObjectId            # Connection to use
    payload_laui: Optional[PydanticObjectId]     # Optional payload item reference
    payload: Optional[str]                       # Optional inline payload
    parent_laui: PydanticObjectId                # Parent workflow
    frequency: str = "ADHOC"                     # Execution frequency (ADHOC or cron)
    start_date: Optional[datetime]               # Start date for scheduled tasks
    end_date: Optional[datetime]                 # End date for scheduled tasks
    config: Dict[str, Any]                       # Task configuration
    attached_config_lauis: List[PydanticObjectId]# Attached config items
    project_laui: PydanticObjectId               # Project reference
    account_laui: PydanticObjectId               # Account reference
    actions: Dict[str, Any]                      # Action definitions
    state: str                                   # Task state
```

### TaskCreationValidationModel

Used during task creation, extends `BaseTaskModel` with extra field allowance.

### TaskValidationModel

Used during task execution, adds runtime context:

```python
class TaskValidationModel(BaseTaskModel):
    laui: PydanticObjectId                       # Task ID
    connection: Optional[Dict[str, Any]]         # Resolved connection data
```

## Task Lifecycle

### 1. Task Creation Flow

```
User Input → validate_task_creation() → Validation Steps → 3-Tier Config Merge → Saved Task (with merged config)
```

**Validation Steps:**
1. Validate frequency (ADHOC or valid cron expression)
2. Validate dates (required for scheduled tasks, end_date >= start_date)
3. Validate payload constraints (only one of payload or payload_laui)
4. Fetch and validate all referenced items (operator, connection, workflow, payload)
5. Validate item types match expected types
6. Validate connection-operator compatibility
7. Merge configurations from all 3 sources (workflow configs queried as children of parent workflow, attached task configs, inline task config)
8. Extract `total_retries` and `retry_interval` from merged config

**Config merging only happens at task creation time.** The merged config is persisted to the database so that subsequent reads and execution use the pre-merged result.

### 2. Task Execution Flow

```
Task Items → validate_task_execution() → Validated Tasks → Pre-Actions → Celery Execution → Task Results
```

**Execution Steps:**
1. Convert task items to TaskValidationModel
2. Batch fetch all required items (operators, connections)
3. Validate each task individually (connection-operator mapping, payload constraints)
4. Replace placeholders in payload using already-merged config parameters
5. Execute pre-actions (blocks until complete)
6. Submit to Celery for execution
7. Return execution result IDs

**Note:** Config merging does NOT occur during execution validation. Tasks already have their merged config from creation time. The execution phase only performs placeholder replacement via `process_task_execution()`.

## Components

### TaskManager

**File**: `task_manager.py`

Main orchestrator for task operations. Coordinates validation, action execution, and Celery submission.

**Key Methods:**

#### `validate_task_creation(task_data: TaskCreationValidationModel) -> TaskCreationValidationModel`

Validates a task for creation.

```python
task_manager = TaskManager(validation_manager, action_manager, celery_orchestrator)
validated_task = await task_manager.validate_task_creation(task_data)
```

#### `validate_task_execution(tasks: List[TaskValidationModel]) -> List[TaskValidationModel]`

Validates multiple tasks for execution, returns successfully validated tasks.

```python
validated_tasks = await task_manager.validate_task_execution(tasks)
```

#### `execute_tasks(task_items: List[Item]) -> List[Dict[str, Any]]`

Complete task execution pipeline:
1. Convert items to TaskValidationModel
2. Validate tasks
3. Execute pre-actions
4. Submit to Celery
5. Return execution results

```python
results = await task_manager.execute_tasks(task_items)
# Returns: [{"task_laui": "...", "execution_result_id": "..."}]
```

### TaskValidationManager

**File**: `task_validation_manager.py`

Handles all validation logic for task creation and execution.

**Key Methods:**

#### `validate_task_creation(task_data: TaskCreationValidationModel) -> TaskCreationValidationModel`

Comprehensive validation for task creation:
- Validates frequency and dates
- Validates payload constraints
- Fetches and validates all referenced items
- Validates connection-operator mapping
- Merges configurations
- Parses payload with placeholder replacement

#### `validate_task_execution(tasks: List[TaskValidationModel]) -> List[TaskValidationModel]`

Batch validation for task execution (no config merging):
- Fetches all required items in batch (efficient)
- Validates each task individually (connection-operator mapping, payload constraints)
- Replaces placeholders in payloads using already-merged config parameters
- Returns only successfully validated tasks (failures are logged)

**Validation Rules:**

| Rule | Description |
|------|-------------|
| Frequency | Must be "ADHOC" or valid 5-part cron expression |
| Dates | Required for scheduled tasks; end_date >= start_date |
| Payload | Only one of `payload` or `payload_laui` allowed |
| Item Types | Operator, connection, workflow must have correct item_type |
| Connection-Operator | Connection must support the operator type |

**Private Helper Methods:**

- `_validate_frequency()`: Validates cron expressions
- `_validate_dates()`: Validates date constraints
- `_validate_payload_constraints()`: Ensures payload XOR payload_laui
- `_validate_item_type()`: Validates item types
- `_validate_workflow_item_type()`: Ensures workflow supports tasks
- `_validate_all_items_exists()`: Checks all referenced items exist
- `_validate_individual_task_execution()`: Validates single task for execution
- `_get_multiple_non_deleted_items()`: Batch fetches items from catalog
- `_get_all_attached_configs()`: Fetches workflow configs (queried as children of parent workflow by parent_laui) and attached task configs (by attached_config_lauis)
- `_get_merged_config()`: Merges all configs using ConfigManager
- `_parse_payload()`: Parses payload with placeholder replacement

### ActionManager

**File**: `action/action_manager.py`

Manages the action lifecycle for tasks. Actions are operations that run before, during, or after task execution.

**Action Types:**

| Type | When Executed | Blocking | Use Case |
|------|---------------|----------|----------|
| `create_actions` | During task creation | No | Setup operations when task is created |
| `pre_actions` | Before task execution | **Yes** | Validation, resource checks, preconditions |
| `running_actions` | During task execution | No | Monitoring, logging, parallel operations |
| `post_actions` | After task execution | No | Cleanup, notifications, post-processing |

**Key Methods:**

#### `pre_actions(la_actions_object: Actions, task_laui: str) -> bool`

Executes pre-actions with timeout. **Blocks and returns True/False** for success.

```python
success = action_manager.pre_actions(actions, task_laui)
if success:
    # Proceed with task execution
```

#### `running_actions(la_actions_object: Actions, task_laui: str) -> None`

Executes running-actions in fire-and-forget mode.

#### `post_actions(la_actions_object: Actions, task_laui: str) -> None`

Executes post-actions in fire-and-forget mode.

#### `create_actions(la_actions_object: Actions, task_laui: str) -> bool`

Executes create-actions during task creation.

**Configuration:**

The action timeout is configured in `system.yml`:
```yaml
action_timeout_seconds: 30
```

**Behavior:**
- Pre-actions block task execution if they fail or timeout
- Running and post-actions are fire-and-forget (don't block)
- Each action gets session_id and task_laui injected
- All actions are executed via Celery for async processing

### ConnectionManager

**File**: `connection/connection_manager.py`

Validates that connections and operators are compatible based on system configuration.

**Key Method:**

#### `validate_connection_operator_mapping(connection: ItemProjection, operator: ItemProjection) -> bool`

Validates connection-operator compatibility using mappings from `config/system.yml`.

```python
connection_manager.validate_connection_operator_mapping(connection, operator)
# Raises UnprocessableEntityError if invalid
```

**Configuration Format** (`config/system.yml`):

```yaml
connection_operator_mapping:
  connection.python:
    - operator.python
    - operator.bash
  connection.postgres:
    - operator.sql
  connection.http:
    - operator.http_request
```

**Validation Logic:**
1. Extracts connection subtype (e.g., "python" from "connection.python")
2. Extracts operator subtype (e.g., "python" from "operator.python")
3. Looks up allowed operators for the connection type
4. Validates operator is in the allowed list

### ConfigManager

**File**: `config/config_manager.py`

See [Config Manager README](./config/README.md) for detailed documentation.

**Key Responsibilities:**
- Merges configs from 3 sources during task creation: workflow configs (auto-discovered as children of parent workflow), attached task configs (via `attached_config_lauis`), and inline task config
- Enforces parameter override policies
- Replaces placeholders with values from parameters and system variables during task execution
- Provides built-in variables (ds, ts)

## Actions System

### Action Schema

**File**: `action/schema.py`

```python
class ActionItem(BaseAction):
    laui: str                                # Action operator LAUI
    task_laui: Optional[str]                 # Injected by ActionManager
    session_id: Optional[str]                # Injected by ActionManager
    connection_laui: Optional[str]           # Connection for action
    connection: Optional[str]                # Connection details
    action_variables: Dict[str, Any]         # Action-specific parameters
    sla: Optional[int]                       # Service level agreement (seconds)

class Actions(BaseModel):
    create_actions: List[ActionItem] = []
    pre_actions: List[ActionItem] = []
    running_actions: List[ActionItem] = []
    post_actions: List[ActionItem] = []
```

### Action Execution Flow

```
ActionManager._run_action_with_timeout()
    ↓
Inject session_id and task_laui into ActionItem
    ↓
Submit to CeleryOrchestrator.run_action()
    ↓
(if wait_for_result) Wait for completion with timeout
    ↓
Return success/failure status
```

## Usage Examples

### Example 1: Creating a Task

```python
from src.core.task.schema import TaskCreationValidationModel
from src.core.task.task_manager import TaskManager

# Define task data
task_data = TaskCreationValidationModel(
    name="Daily ETL Job",
    operator_laui=operator_id,
    connection_laui=connection_id,
    parent_laui=workflow_id,
    frequency="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 12, 31),
    config={
        "parameters": {
            "table_name": "analytics_data_{{ ds }}",
            "batch_size": 1000
        }
    },
    project_laui=project_id,
    account_laui=account_id,
    actions={
        "pre_actions": [{
            "laui": "check_table_exists_action_laui",
            "connection_laui": "db_connection_laui",
            "action_variables": {"table": "analytics_data"}
        }]
    },
    state="active"
)

# Validate and create
validated_task = await task_manager.validate_task_creation(task_data)
```

### Example 2: Executing Tasks

```python
from src.core.catalog.item.schema import Item

# Fetch task items (from database)
task_items = [...]  # List[Item]

# Execute tasks
results = await task_manager.execute_tasks(task_items)

# Results format
# [{"task_laui": "...", "execution_result_id": "celery-task-id"}]
```

### Example 3: Task with Inline Payload

```python
task_data = TaskCreationValidationModel(
    name="Send Notification",
    operator_laui=http_operator_id,
    connection_laui=http_connection_id,
    parent_laui=workflow_id,
    frequency="ADHOC",
    payload='{"message": "Task completed at {{ ts }}", "severity": "info"}',
    config={
        "parameters": {
            "api_endpoint": "https://api.example.com/notify"
        }
    },
    # ... other fields
)
```

### Example 4: Task with Payload Reference

```python
task_data = TaskCreationValidationModel(
    name="Execute SQL Query",
    operator_laui=sql_operator_id,
    connection_laui=postgres_connection_id,
    parent_laui=workflow_id,
    frequency="ADHOC",
    payload_laui=sql_query_payload_id,  # References a payload item with SQL query
    config={
        "parameters": {
            "database": "analytics"
        }
    },
    # ... other fields
)
```

### Example 5: Task with Actions

```python
actions = {
    "pre_actions": [
        {
            "laui": "validate_schema_action",
            "connection_laui": "db_connection",
            "action_variables": {"schema_version": "v2"}
        }
    ],
    "running_actions": [
        {
            "laui": "monitor_progress_action",
            "action_variables": {"interval_seconds": 60}
        }
    ],
    "post_actions": [
        {
            "laui": "send_completion_email_action",
            "action_variables": {
                "recipients": ["team@example.com"],
                "subject": "Task {{ task_name }} completed"
            }
        }
    ]
}

task_data = TaskCreationValidationModel(
    name="Complex ETL Pipeline",
    # ... other fields
    actions=actions
)
```

## Best Practices

### 1. Task Design

- **Use ADHOC for one-time tasks**: Scheduled tasks require valid cron expressions and dates
- **Choose payload vs payload_laui wisely**: Use `payload_laui` for reusable payloads, `payload` for task-specific content
- **Validate connection-operator compatibility**: Ensure your connection type supports the operator before creating tasks
- **Use descriptive task names**: Include context about what the task does

### 2. Configuration Management

- **Config merging happens only at task creation**: The merged config is persisted to the database; execution uses the pre-merged result
- **Workflow configs are auto-discovered**: Any `config` item that is a child of the parent workflow is automatically included as a workflow config
- **Attached task configs are explicit**: Pass config LAUIs via `attached_config_lauis` for task-specific configs
- **Use override policies**: Mark sensitive parameters as `not_overridable` in workflow configs
- **Leverage system variables**: Use `{{ ds }}` and `{{ ts }}` for date/timestamp injection
- **Structure parameters hierarchically**: Group related parameters in nested dictionaries

### 3. Actions

- **Use pre-actions for validation**: Block task execution if preconditions aren't met
- **Keep pre-actions fast**: They block execution, so timeout is configured (default 30s)
- **Use running-actions for monitoring**: Don't block task completion, run in parallel
- **Use post-actions for cleanup**: Fire-and-forget operations after task completes
- **Design idempotent actions**: Actions may be retried on failure

### 4. Payload Design

- **Use placeholders liberally**: `{{ parameter_name }}` for dynamic values
- **Validate JSON payloads**: If using JSON strings, ensure they're valid
- **Keep payloads focused**: Each task should do one thing well
- **Document expected payload structure**: Especially for custom operators

### 5. Error Handling

- **Check validation results**: `validate_task_execution()` returns only successful tasks
- **Monitor pre-action failures**: They prevent task execution
- **Log errors appropriately**: Use structured logging for debugging
- **Design for failure**: Tasks may fail; ensure system degrades gracefully

### 6. Performance

- **Batch task operations**: Use `execute_tasks()` for multiple tasks rather than one-by-one
- **Leverage catalog projections**: Fetch only needed fields to reduce database load
- **Monitor Celery queue**: Ensure worker capacity matches task volume
- **Use connection pooling**: Especially for database connections

### 7. Testing

- **Test with mock items**: Use test fixtures for operators, connections, payloads
- **Test validation failures**: Ensure proper error messages for common mistakes
- **Test config merging**: Verify complex config hierarchies merge correctly
- **Test placeholder replacement**: Ensure all edge cases (undefined vars, nested objects) work
- **Test action execution**: Mock Celery to test action orchestration

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Item with laui X not found" | Referenced item doesn't exist or is deleted | Verify item exists and is not deleted |
| "Invalid cron expression" | Malformed frequency string | Use valid 5-part cron or "ADHOC" |
| "end_date must be greater than start_date" | Date constraint violated | Fix date values |
| "Both payload and payload_laui provided" | Ambiguous payload source | Choose one: payload or payload_laui |
| "Invalid connection-operator mapping" | Incompatible types | Check system.yml mappings |
| "Pre-action timed out" | Pre-action exceeded timeout | Optimize action or increase timeout |
| "Task validation failed" | Multiple validation errors | Check logs for specific failures |

### Debugging Tips

1. **Enable detailed logging**: Set log level to INFO or DEBUG
2. **Check merged config**: Log `task.config` after validation to see final config
3. **Verify placeholders**: Log payload before and after replacement
4. **Test actions independently**: Run actions outside task context first
5. **Check Celery logs**: Review worker logs for execution details
6. **Validate system.yml**: Ensure connection-operator mappings are correct

## Related Documentation

- [Config Manager README](./config/README.md) - Configuration merging and placeholder replacement
- [Action Development Guide](../../../docs/action_development.md) - Creating custom actions
- [Operator Development Guide](../../../docs/operator_development.md) - Creating custom operators
