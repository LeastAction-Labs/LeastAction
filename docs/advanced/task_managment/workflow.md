# LeastAction Workflow - Feature Guide

## Overview

A **workflow** in LeastAction is a logical collection of tasks organized within a folder structure. Workflows group related data pipeline operations, orchestrate task dependencies, and manage execution schedules. Think of a workflow as a directed acyclic graph (DAG) where each node is a task that performs a specific operation.

### Key Concepts

**laui**: LeastAction unique identifier, all items in LeastAction have an unique identifier, connection, operator or a task, a task combines many of lauis to create a task.

**Workflow**: A folder of type "workflows" that contains multiple tasks working together to achieve a data processing goal.

**Task**: The fundamental execution unit in LeastAction with type "task". Each task combines:

- **Operator**: Code that executes the task logic (e.g., running SQL, invoking Lambda, loading data), Input as Operator laui
- **Connection**: Reusable resource configuration that provides credentials, endpoints, and execution limits. **Required for all tasks** — even for locally-run scripts, connections serve as an admin control layer that governs what an operator is allowed to do. Input as connection laui
- **Config**: (Optional) Configuration applied at task creation time that defines defaults, parameters, and runtime behavior. Input as config laui or direct form.
- **Payload**: The actual work to be performed (SQL query, Python script, API call, etc.). Input as payload laui or direct form.
- **Actions**: Lifecycle hooks that execute at different stages (preAction, createAction, runningIntervalAction, runningAction, postAction). Input as laui with needed details.

**Operator**: Executable code containing the business logic. Operators define how tasks interact with external systems. Each operator has a specific structure with `initialize()`, `run()`, `check_completion()`, and `finish()` functions.

**Connection**: A reusable configuration that manages computational resources, credentials, and execution limits. Subtypes (e.g., `connection.AWSIAMRole`) are optional labels — compatibility with operator subtypes is only enforced when `enforce_connection_operator_mapping: true` in `system.yml`.

**Action**: Reusable functions that execute at specific points in a task's lifecycle, enabling monitoring, notifications, validation, and cleanup operations.

**Partition**: An optional string field on a task that scopes it within a workflow. Two tasks can have the same name as long as they have different partitions — partition is part of the task's primary key alongside `name`, `project_laui`, and `account_laui`. Use partitions to manage parallel runs, isolate data domains, or run the same task definition against different datasets. `LeastActionCheckIfParentsAreDone` uses the `partition` field in the `parents` array so that a parent task in one partition cannot inadvertently block a task in another partition.

### Task Execution Model

Tasks execute payload code by using the operator's logic and the connection's configuration. The config is applied to the payload at task creation time using Jinja templating (e.g., `{{ table_name }}`).

**Note**: Parameters are accessed directly by name (e.g., `{{database_name}}`), NOT with a prefix like `{{parameters.database_name}}`.

### Workflow Hierarchy

```
▼ 📁 Account (type=folder.account, is_root=true)
   📋 Metadata: Organization-level settings, users
   
  ▼ 📁 Project (type=folder.project)
     📋 Metadata: Project-level permissions, settings, Cron status
    
    ▶ 🔌 Connections/ (type=connection.*)
      • lambda-prod.AWSIAMRole
    
    ▶ ⚙️ Configs/ (type=config.*)
      • lambdaDefaults.config (default workflow settings)
    
    ▶ 🔧 Operators/ (type=operator.*)
      • AWSLambdaInvokeFunction.AWSIAMRole
    
    ▶ 🎬 Actions/ (type=action.*)
      • AWSCheckS3FileExists
      • LeastActionCancelTask
      • LeastActionCheckIfParentsAreDone
    
    ▶ 📝 Payloads/ (type=payload.*)
      • payload.python (transform_script.py)
    
    ▶ 📊 Monitoring/ (type=monitor.*)
    
    ▼ 📂 Workflow/ (type=folder.workflow)
       🔗 Link: configs=[lambdaDefaults.config]
               taskActions: [LeastActionCancelTask]
      
      ▼ 📄 Task 1: extract_sales_data (type=task)
         🔧 Operator: AWSLambdaInvokeFunction (using: operator_laui)
         🔌 Connection: lambda-prod (using: connection_laui)
         ⚙️ Configs:
          • Inherited from: workflow.config (using: config_laui)
          • Defined in Task Form : { parameters:[""] } 
         📝 Payload: transform_script.py (config parameters applied)
         🎬 Actions: (lifecycle hooks)
             preAction:
             • LeastActionCheckS3FileExists
               └─ 🔌 connection: "lambda-prod" (using: connection_laui)
               └─ 📋 variables: {s3_path: "{{s3_bucket}}/raw/{{ds}}/"}
             createAction
             runningIntervalAction
             runningAction
             postAction
```

## Task Creation and Execution Lifecycles

### Adhoc Run

Adhoc runs allow immediate, one-time task execution without scheduling. Adhoc task run can be initiated from:

- Operator AI interface
- Payload AI interface
- Saved operator
- Saved payload

#### Required Fields for Adhoc Tasks

**Mandatory:**

- **Workflow**: Required to create a dynamic task (folder of type "workflows")
- **Operator**: The operator to execute (`operator_laui`)
- **Connection**: The connection to use (`connection_laui`)
- **Frequency**: Must be set to "ADHOC"

**Optional:**

- **Payload**: Can be preselected (via `payload_laui`) or typed directly (via `payload` field)
- **Configs**:
  - Workflow configs are auto-attached
  - All defaults (retry, timeout, actions, etc.) are loaded from workflow config
  - When a new config is selected, list of configs is shown
  - Configs are merged at creation and before runtime to apply the parameters and runtime parameters
  - **Note**: Config parameters are applied on payload at creation time, the payload in task will reflect it (for both laui based or typed directly)
  - For runtime-only config changes, use runtime parameters which only show in logs
- **Actions**: preAction, createAction, runningIntervalAction, runningAction, postAction

**Config Resolution Clarified:**

- **Parameters**: Resolved at task creation time and applied to payload (payload is transformed). Defined in each config's `parameters` block and accessed directly as `{{ name }}` in payload templates.
- **Built-in Variables**: `{{ ds }}` (current date, `YYYY-MM-DD`) and `{{ ts }}` (current timestamp, ISO format) are always available and **always override** any config parameter with the same name.
- **Undefined Placeholders**: If a `{{ variable }}` in the payload has no matching parameter or built-in, it is **kept as-is** in the output (not an error).
- **Runtime Parameters**: All config parameters are applied at runtime — they are resolved immediately before the task executes, using the current value of each parameter at that moment. This means you can update a parameter and the next execution will use the new value without recreating the task.

**Config Merge Rules (from code):**

Configs are processed in order: `workflow_configs` → `task_configs` → inline `config`. The merge behaves differently for parameters vs other keys:

| Key Type | Within a Group (multiple configs) | Across Groups |
|----------|----------------------------------|---------------|
| **Parameters** | First config in group wins | Later groups CAN override, UNLESS the parameter is in the `not_overridable` list set by an earlier group |
| **Other keys** (retry_count, timeout, etc.) | First config in group wins | Later groups override (last group wins) |
| **Nested dicts** (e.g. defaults.task) | Deep-merged recursively | Deep-merged across groups |

So for example:
- If `workflow_configs` sets `retry_count: 3`, a `task_config` can override it to `retry_count: 5` (non-parameter key, later group wins).
- If `workflow_configs` sets `parameters.environment: production` AND lists `environment` in `not_overridable`, then `task_configs` and inline `config` **cannot** change it (warning logged, value ignored).
- If `workflow_configs` sets `parameters.s3_bucket` but does NOT list it in `not_overridable`, then `task_configs` or inline `config` CAN change it.
- `overridable` list explicitly marks parameters that are allowed to be overridden even if they appear protected.

#### Lifecycle

1. **Create Task**: Define task with operator, connection (required), payload, config (optional), and actions (optional)
2. **Validate**: If `enforce_connection_operator_mapping: true` in `system.yml`, system validates operator-connection subtype compatibility
3. **Apply Config**: Jinja templates in payload/actions are resolved using config parameters
4. **Schedule**: Task moves to `scheduled` state
5. **Queue for Connection**: If connection has available capacity, task proceeds; otherwise enters `queued_for_connection` state
6. **Queue in Redis**: Task enters `queued_in_redis` state when system resources are available
7. **Celery Execution**: Task picked up by Celery worker and enters `running` state
8. **Complete**: Task transitions to `success`, `error`, or `timeout` state
9. **Manual Cancellation**: User can cancel via the task control actions (e.g. LeastActionCancel) or the UI cancel button at any point, moving task to `cancelled` state

### Backdated Schedule

Backdated schedules allow running tasks for historical dates, useful for backfilling data or reprocessing. Scheduling task can be initiated from:

- Operator AI interface
- Payload AI interface
- Saved operator
- Saved payload
- Manual form filling with required fields

#### Required Fields for Scheduled Tasks

**Mandatory:**

- **Workflow**: Required (folder of type "workflows")
- **Operator**: The operator to execute (`operator_laui`)
- **Connection**: The connection to use (`connection_laui`)
- **Frequency**: Valid cron expression (e.g., "0 2 * * *")
- **Start Date**: Required for cron-based schedules (`start_date`)
- **End Date**: Required for cron-based schedules (`end_date`)

**Optional:**

- **Payload**: Can be preselected (via `payload_laui`) or typed directly (via `payload` field)
- **Configs**:
  - Workflow configs are auto-attached
  - All defaults are loaded from workflow config
  - When a new config is selected, list of configs is shown
  - Final merged config is only shown after execution
  - All configs are treated as runtime-use
  - Config modifications are applied at runtime
  - **Note**: Config is applied on payload at creation time, the payload will reflect it
  - For runtime-only config changes, use runtime parameters which only show in logs
- **Actions**: preAction, createAction, runningIntervalAction, runningAction, postAction
- **Schedule details**: Cron expression, start/end dates

#### Lifecycle

1. **Create Scheduled Task**: Define task with cron schedule and start/end dates
2. **Generate Task Instances**: System generates task instances for each schedule interval between start and end dates
3. **Validate Dependencies**:
   1. Check if upstream tasks for each date have completed (using `LeastActionCheckIfParentsAreDone()` action)
   2. When `LeastActionCheckIfParentsAreDone` is added, the tasks are internally linked for dependency management using `LeastActionLinkParents` action, which is a default action for all workflows.
4. **Apply Config**: Workflow, Task or Task form.
5. **Schedule Instances**: Each instance moves through states: `scheduled` → `queued_for_connection` → `queued_in_redis`
6. **Priority Ordering**: Tasks execute based on priority levels (lower number = higher priority) and based on sort order in connection
7. **Celery Execution**: Instances execute in parallel (respecting connection `max_parallelism`)
8. **Dependency Resolution**: Downstream tasks only execute after upstream dependencies complete (managed via actions)
9. **Completion**: Each instance reaches `success`, `error`, or `timeout`
10. **Retry Logic**: Failed instances retry based on `retry_count` and `retry_interval` config

**Backfill Execution:**

- System generates 15 task instances (one per day from Jan 1-15)
- Each instance has unique `logical_date` (execution date)
- Instances execute in parallel up to connection's `max_parallelism` limit
- Failed instances retry automatically based on config

## Task State Transitions

Tasks progress through well-defined states during their lifecycle:

### State Flow

```
scheduled   
↓  
queued_for_connection (system_lastupdated_date set)  
↓  
queued_in_redis (system_lastupdated_date updated)  
↓  
running (last_run_date = current_time)  
↓  
├─→ success (system_last_updated_date set)  
├─→ error (system_last_updated_date set) → retry logic  
├─→ timeout (system_last_updated_date set) → retry logic  
└─→ cancelled (via API, system_last_updated_date set)
```

### State Definitions

**scheduled**: Task created and waiting to be queued

- Initial state after task creation
- Config has been applied, Jinja templates resolved
- Dependencies validated (if using dependency actions)

**queued_for_connection**: Waiting for connection capacity

- Connection at `max_parallelism`, task waiting in priority queue
- `system_last_updated_date` timestamp recorded
- Priority determines execution order
- Sort order in connection also affects execution order

**queued_in_redis**: Waiting for system resources (Celery workers)

- Connection capacity available
- Waiting for Celery worker to pick up task
- `system_last_updated_date` updated

**running**: Active execution in Celery worker

- `state = running`
- `last_run_date = current_time`
- Operator's `initialize()` → `run()` → `check_completion()` executing

**success**: Task completed successfully

- Operator returned success status
- `system_last_updated_date` updated
- Downstream dependencies can now execute

**error**: Task failed during execution

- Operator raised exception or returned error status
- `system_last_updated_date` updated
- Retry logic applies if `retry_count > 0`

**timeout**: Task exceeded configured timeout

- Execution time exceeded `timeout` config parameter
- `system_last_updated_date` updated
- Considered a failure for retry logic

**cancelled**: Manually cancelled via API

- User invoked cancel operation
- `system_last_updated_date` updated
- Task immediately stops (if running) or removed from queue

### Retry Logic

When a task enters `error` or `timeout` state and `retry_count > 0`:

```
retry_date = last_run_date + retry_interval
```

**Example Retry Configuration:**

```json
{
  "config": {
    "retry_count": 3,
    "retry_interval": 300
  }
}
```

- Task fails at 10:00:00
- First retry scheduled at 10:05:00 (300 seconds later)
- If fails again, retry at 10:10:00
- If fails again, retry at 10:15:00
- After 3 retries, task remains in `error` state

## Prerequisites

### Required Components

To create and execute a task, you need:

1. **Operator Definition**: The operator code must exist and be accessible
2. **Connection**: Required for all tasks. Even operators that run locally (e.g., Python scripts) require a connection — this gives admins control over what each operator is permitted to do. Subtype matching with the operator is optional and only enforced when `enforce_connection_operator_mapping: true` in `system.yml`.
3. **Workflow**: A folder of type "workflows" to contain the task
4. **Permissions**: User must have execute permissions on the workflow and has access to operator, connection and configs.
   1. All parts of LeastAction are treated as a content management system, the user needs to have access to needed parts to be able to use it.
5. **Account and Project**: Required for task creation (`account_laui` and `project_laui`)

### Connection-Operator Compatibility

Subtype matching between connections and operators is **optional** and controlled by `enforce_connection_operator_mapping` in `config/system.yml`:

- **`true`** (default): The system validates that the connection subtype is allowed for the selected operator subtype. The UI dropdown filters to show only compatible connections. Pre-configured mappings cover AWS, Python, Docker, Kubernetes, Spark, Databricks, Anthropic, Slack, PostgreSQL, and Airflow.
- **`false`**: Any connection can be paired with any operator regardless of subtype. No filtering in the UI.

> **Admin Note**: Adding a new mapping requires updating `config/system.yml`. **No service restart is required** — the mapping is reloaded automatically on each task creation.

**Valid Example:**

```json
{
  "operator": "operator.AWSIAMRole",
  "connection": "lambda-prod"
}
```

Where connection `lambda-prod` has:

```json
{
  "type": "connection.AWSIAMRole"
}
```

And `system.yml` contains:

```yaml
connection_operator_mapping:
  connection.AWSIAMRole:
    - operator.AWSIAMRole  # Handles Lambda, S3, EC2, Athena, and other AWS services
```

**Invalid Example:**

```json
{
  "operator": "operator.postgres",
  "connection": "lambda-prod"
}
```

This fails because `connection.AWSIAMRole` doesn't map to `operator.postgres` in `system.yml`. The API returns a clear validation error directly to the UI, for example:

> *"Invalid connection-operator mapping: AWSIAMRole does not support postgres. Allowed: AWSIAMRole"*

Or if the connection type has no mapping at all:

> *"No mapping defined for connection type 'myCustomType'. Available mappings: [AWSIAMRole, python, docker, ...]"*

These errors appear directly in the UI at task creation time — no log-diving needed.

### Scheduled Task Requirements

For tasks with cron-based scheduling:

- **Frequency**: Must be valid cron expression (NOT "ADHOC")
- **Start Date**: Required (ISO 8601 format)
- **End Date**: Required (ISO 8601 format)
- **Date Validation**: `end_date` must be after `start_date`

For adhoc tasks:

- **Frequency**: Must be "ADHOC"
- **Start Date**: Not required
- **End Date**: Not required

### Optional Configurations

- **Config**: Define workflow or task-level configurations
- **Actions**: Add lifecycle hooks (preAction, postAction, etc.)
- **Partitions**: Isolate tasks into logical groups for advanced dependency management
- **Priority**: Control execution order and sort order
- **Payload**: Can be provided directly as JSON string or reference via `payload_laui`

## Observability & Monitoring

Handled with 3 parts folder style navigation, logging and linked data

All of LeastAction data is stored in folder style with permission management similar to google drive, enabling easy personalized management of tasks and workflows and all related data. Even the workflows can be personalized as who can read, write.

LeastAction generates logs in hive format and is stored in local drive, which is exposed in each project as a folder to navigate API/task/action logs, and also provides the same folder drilldown for each task/action and its history of run. Logs can be moved to cloud storage using post actions like LeastActionLogsToS3 etc.

All of LeastAction while in folder style is also a linked data, each item can be linked to any other based on what's defined in the catalog config, with this tasks lineage is linked to task, configs, connections and other data. Enabling task level visual graphs and parent child drill down at each item.

## Testing Framework

Use AI editor or code editor and test operator code, action code, payload or even connection before saving it and using it in workflows, no external tools needed, all testing can be done on LeastAction UI.

## Dynamic Task Generation

Task action can be used to dynamically generate tasks from config, and a AI can be used to generate the action. Explore prebuild task action like import* which imports all * models to a workflow as task and adds dependency

## Task Return Value Handling

- How do tasks pass data to downstream tasks

## Ecosystem & Community

> **Note**: Few things to clarify action is the core of the software that lets user do more that just manage task life life cycle, task action can be used to dynamically generate tasks from config, and a AI can be used to generate the action, making the actions more powerful in some ways. Not sure if count of operator in airflow matters as nearly all of it can be generated using the operator AI, and more, the marketplace is a place to share the operators, this is in development. Last thing, all data i.e item in leastaction is based on item and link design, user can choose to link any task using actions and preset it, so depends_on is just another config, that can trigger an action that can link the data, and a task graph is viewable. The graph is not only for task but also for other element.

## Usage - Implementing Tasks in Workflows

### Basic Task Structure

```json
{
  "task_id": "unique_task_identifier",
  "workflow": "workflow_folder_name",
  "operator": "operator.TypeName",
  "connection": "connection_name",
  "account_laui": "account_identifier",
  "project_laui": "project_identifier",
  "parent_laui": "workflow_laui",
  "frequency": "ADHOC",
  "state": "scheduled",
  "configs": {
    "workflow_configs": [],
    "task_configs": []
  },
  "config": {
    "retry_count": 3,
    "retry_interval": 300,
    "timeout": 3600,
    "parameters": {}
  },
  "payload": {},
  "actions": {
    "preAction": [],
    "createAction": [],
    "runningIntervalAction": [],
    "runningAction": [],
    "postAction": []
  }
}
```

> **Config Layers Explained**: Both `configs` and `config` are used together. They represent three layers of configuration:
> 1. **`configs.workflow_configs`** (linked configs at workflow level): Set by the workflow owner to enforce defaults and rules that tasks should not override (e.g., `not_overridable` parameters like environment, security settings). All tasks in the workflow inherit these.
> 2. **`configs.task_configs`** (linked configs at task level): Reusable configs linked to individual tasks for common repeated settings shared across multiple tasks (e.g., common retry policies, shared parameters).
> 3. **`config`** (inline task form input): Task-specific config entered directly in the task creation form. Used for one-off settings that are unique to that task or values the user needs to fill in at creation time.
>
> All three layers merge together at task creation time. Workflow configs take precedence for `not_overridable` fields, then task configs, then inline config for the rest.

### Workflow Configuration Pattern

**Step 1: Create Workflow Config** (`workflow.config`)

```json
{
  "defaults": {
    "task": {
      "retry_count": 3,
      "retry_interval": 300,
      "timeout": 3600,
      "preAction": [
        {
          "action": "LeastActionGitSync",
          "connection": "github-main",
          "variables": {}
        }
      ],
      "postAction": [
        {
          "action": "LeastActionSlackWebhook",
          "connection": "slack-alerts",
          "variables": {
            "message": "Task {{ task_id }} completed"
          }
        }
      ]
    },
    "taskControlActions": [
      {
        "action": "LeastActionCancel",
        "variables": {
          "taskStatus": ["running", "scheduled"]
        }
      },
      {
        "action": "LeastActionRerun",
        "variables": {
          "taskStatus": ["error", "failed", "canceled"]
        }
      },
      {
        "action": "LeastActionRerunSubtree",
        "variables": {
          "taskStatus": ["error", "failed"]
        }
      },
      {
        "action": "LeastActionSkip",
        "variables": {
          "taskStatus": ["scheduled", "waiting"]
        }
      },
      {
        "action": "LeastActionSkipSubtree",
        "variables": {
          "taskStatus": ["scheduled", "waiting"]
        }
      }
    ],
    "uiActions": []
  },
  "parameters": {
    "environment": "production",
    "s3_bucket": "s3://data-lake-prod",
    "database_name": "analytics"
  },
  "partition": "daily_etl",
  "priority": [
    {
      "level": 0,
      "tasks": ["extract_*"]
    },
    {
      "level": 1,
      "tasks": ["transform_*"]
    },
    {
      "level": 2,
      "tasks": ["load_*"]
    }
  ]
}
```

**Task Control Actions in Workflow Config:**

Task control actions are lifecycle control actions that can be added to workflow view defaults config settings or directly to workflows as child action items. These actions manage task execution state and can be invoked via UI, API, or programmatically.

**Available Task Control Actions:**

- **LeastActionRun** - Start task execution
- **LeastActionRerun** - Re-execute a task
- **LeastActionRerunSubtree** - Re-execute task and all children
- **LeastActionCancel** - Stop a running task
- **LeastActionSkip** - Mark task as skipped
- **LeastActionSkipSubtree** - Skip task and all children
- **LeastActionSkipPostDoneS3** - Skip and write completion marker

**Characteristics:**

- Change task execution state
- Can use connection resources if needed (e.g., a custom action to skip and drop S3 file)
- Can be invoked via UI, API, or programmatically in tasks (use with caution)
- Use APIs like UpdateTask, sendToExecution, RecursiveListChildren
- Can be filtered by task status when configured as UI actions
- Task control actions will only appear in the UI when the task's current status matches one of the statuses in the `taskStatus` array

**Example with Connection Resource:**

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionSkipPostDoneS3",
      "connection": "s3-prod",
      "variables": {
        "taskStatus": ["scheduled", "waiting"],
        "s3Prefix": "s3://bucket/done-markers/",
        "fileName": "{{taskId}}.done"
      }
    }
  ]
}
```

**Step 2: Create Tasks Using Config**

Tasks automatically inherit workflow config:

```json
{
  "task_id": "extract_sales_data",
  "workflow": "etl_pipeline",
  "operator": "operator.python",
  "connection": "python-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "ADHOC",
  "state": "scheduled",
  "payload": {
    "script": "extract_sales.py",
    "args": ["--bucket", "{{ s3_bucket }}"]
  }
}
```

This task inherits:

- `retry_count: 3`
- `timeout: 3600`
- `preAction` and `postAction` from workflow config
- `taskControlActions` (Cancel, Rerun, Skip, etc.) from workflow config
- `parameters.s3_bucket` available in payload via Jinja

> **Note**: Task control actions are configured at the **workflow level only** — either via the workflow's defaults config or by adding them directly to the workflow. They are not set on individual tasks. All tasks within the workflow inherit the same set of task control actions.

### Dependency Management

Tasks can depend on other tasks within the same partition. Dependency management is implemented using actions, specifically the `LeastActionCheckIfParentsAreDone()` action.

**Dependency Rules:**

- Dependencies are managed via actions, not natively by the system
- Tasks can only depend on tasks in the same partition
- Circular dependencies are not allowed
- Upstream tasks must complete successfully before downstream tasks execute

**Example Dependency Using Actions:**

```json
{
  "task_id": "transform_sales_data",
  "workflow": "etl_pipeline",
  "operator": "operator.python",
  "connection": "python-prod",
  "frequency": "ADHOC",
  "state": "scheduled",
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckIfParentsAreDone",
        "variables": {
          "parent_tasks": ["extract_sales_data"],
          "partition": "daily_etl"
        }
      }
    ]
  },
  "payload": {
    "script": "transform_sales.py"
  }
}
```

### Using Actions in Tasks

#### Action Merging Behavior

Task-level actions **APPEND** to workflow default actions — they do NOT replace them. If the workflow config defines `preAction: [A, B]` and a task defines `preAction: [C]`, the task ends up with `preAction: [A, B, C]`.

**Key rules:**
- Actions from workflow defaults are inherited by all tasks automatically
- Task-level actions are appended after the workflow defaults for each lifecycle hook
- If a task specifies the **same action** that already exists in workflow defaults, the action's `variables` are **auto-filled from the workflow default** — the user can then update specific variables or use config parameters to override them
- Workflow default action variables can contain config parameters (e.g., `{{ task_id }}`, `{{ ds }}`) which are resolved at execution time

**Example:**

Workflow default config:
```json
{
  "defaults": {
    "task": {
      "preAction": [
        {
          "action": "LeastActionGitSync",
          "connection": "github-main",
          "variables": {}
        }
      ]
    }
  }
}
```

Task adds one more preAction:
```json
{
  "preAction": [
    {
      "action": "LeastActionCheckS3FileExists",
      "connection": "s3-prod",
      "variables": {
        "s3_path": "{{ s3_bucket }}/input/{{ ds }}/"
      }
    }
  ]
}
```

**Result** — task executes with both:
```json
{
  "preAction": [
    {
      "action": "LeastActionGitSync",
      "connection": "github-main",
      "variables": {}
    },
    {
      "action": "LeastActionCheckS3FileExists",
      "connection": "s3-prod",
      "variables": {
        "s3_path": "{{ s3_bucket }}/input/{{ ds }}/"
      }
    }
  ]
}
```

#### Task Control Actions - Manage Task Execution State

Task control actions manage task execution metadata and state. These are typically triggered by users or automation to control running tasks.

```json
{
  "actions": {
    "taskControlActions": [
      {
        "action": "LeastActionCancel",
        "variables": {
          "taskStatus": ["running", "scheduled"]
        }
      },
      {
        "action": "LeastActionRerun",
        "variables": {
          "taskStatus": ["error", "failed", "canceled"]
        }
      },
      {
        "action": "LeastActionRerunSubtree",
        "variables": {
          "taskStatus": ["error", "failed"]
        }
      },
      {
        "action": "LeastActionSkip",
        "variables": {
          "taskStatus": ["scheduled", "waiting"]
        }
      },
      {
        "action": "LeastActionSkipSubtree",
        "variables": {
          "taskStatus": ["scheduled", "waiting"]
        }
      }
    ]
  }
}
```

**Task Control Action Characteristics:**

- **Status Filtering**: Actions only appear in UI when task status matches `taskStatus` array
- **Invocation Methods**: Can be invoked via UI, API, or programmatically
- **State Changes**: Directly modify task execution state (scheduled, canceled, etc.)
- **Connection Support**: Can use connection resources for custom operations (e.g., S3 file operations)
- **Subtree Operations**: Some actions (RerunSubtree, SkipSubtree) affect task and all children

**Common Task Control Patterns:**

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionCancel",
      "variables": {
        "taskStatus": ["running", "scheduled", "queued_for_connection", "queued_in_redis"]
      }
    },
    {
      "action": "LeastActionRerun",
      "variables": {
        "taskStatus": ["error", "failed", "canceled", "timeout"]
      }
    },
    {
      "action": "LeastActionSkipPostDoneS3",
      "connection": "s3-prod",
      "variables": {
        "taskStatus": ["scheduled", "waiting"],
        "s3Prefix": "s3://bucket/done/{{yyyymmdd}}/",
        "fileName": "{{taskId}}.done"
      }
    }
  ]
}
```

#### preAction - Execute Before Task Starts

```json
{
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckS3FileExists",
        "connection": "s3-prod",
        "variables": {
          "s3_path": "s3://bucket/data/{{ ds }}/input.csv"
        }
      }
    ]
  }
}
```

#### createAction - Execute When Task is Created

```json
{
  "actions": {
    "createAction": [
      {
        "action": "LeastActionValidateConfig",
        "variables": {
          "required_params": ["database_name", "table_name"]
        }
      }
    ]
  }
}
```

#### runningIntervalAction - Execute Periodically While Running

```json
{
  "actions": {
    "runningIntervalAction": [
      {
        "action": "LeastActionUpdateConnectionUtilization",
        "interval": 300,
        "connection": "postgres-prod",
        "variables": {
          "metric": "cpu_utilization"
        }
      }
    ]
  }
}
```

#### runningAction - Execute if SLA is Breached

```json
{
  "actions": {
    "runningAction": [
      {
        "action": "LeastActionSlackWebhook",
        "sla": 1800,
        "connection": "slack-alerts",
        "variables": {
          "message": "ALERT: Task {{ task_id }} exceeded 30 min SLA",
          "channel": "#critical-alerts"
        }
      }
    ]
  }
}
```

#### postAction - Execute After Task Completes

```json
{
  "actions": {
    "postAction": [
      {
        "action": "LeastActionUpdateMetadata",
        "variables": {
          "status": "completed",
          "rows_processed": "{{ task_output.row_count }}"
        }
      }
    ]
  }
}
```

## Task Control in Workflows

### Controlling Task Execution

Task control actions provide powerful capabilities to manage task execution state across workflows. These actions are configured at the **workflow level only** — either via the workflow's defaults config or by adding them directly to the workflow. All tasks in the workflow inherit the same task control actions.

Task control actions can be added to a workflow in two ways:
1. **Via defaults config**: Define them in the workflow config's `defaults.taskControlActions` array
2. **Directly on the workflow**: Add action items to the workflow in the folder tree (visible under workflow > `.action` in the folder tree view, or in item details > child details tab)

**Workflow-Level Task Control:**

```json
{
  "defaults": {
    "taskControlActions": [
      {
        "action": "LeastActionCancel",
        "variables": {
          "taskStatus": ["running", "scheduled"]
        }
      },
      {
        "action": "LeastActionRerun",
        "variables": {
          "taskStatus": ["error", "failed"]
        }
      }
    ]
  }
}
```

All tasks in this workflow inherit these control actions, making them available in the UI when task status matches.

> **Note**: Task control actions are workflow-level only. They cannot be configured per-task. All tasks in a workflow share the same task control actions defined at the workflow level.

### Task Control Action Reference

| Action | Description | Common Status Filters | Connection Required |
|--------|-------------|----------------------|---------------------|
| **LeastActionRun** | Start task execution | scheduled, waiting | No |
| **LeastActionRerun** | Re-execute a task | error, failed, canceled, timeout | No |
| **LeastActionRerunSubtree** | Re-execute task and all children | error, failed | No |
| **LeastActionCancel** | Stop a running task | running, scheduled, queued_for_connection | No |
| **LeastActionSkip** | Mark task as skipped | scheduled, waiting | No |
| **LeastActionSkipSubtree** | Skip task and all children | scheduled, waiting | No |
| **LeastActionSkipPostDoneS3** | Skip and write S3 completion marker | scheduled, waiting | Yes (S3) |

### Advanced Task Control Patterns

**Pattern 1: Conditional Rerun with Subtree**

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionRerun",
      "variables": {
        "taskStatus": ["error", "timeout"]
      }
    },
    {
      "action": "LeastActionRerunSubtree",
      "variables": {
        "taskStatus": ["error", "failed"]
      }
    }
  ]
}
```

This pattern provides two rerun options:
- Single task rerun for errors/timeouts
- Full subtree rerun for errors/failures

**Pattern 2: Skip with External Marker**

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionSkip",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
      }
    },
    {
      "action": "LeastActionSkipPostDoneS3",
      "connection": "s3-prod",
      "variables": {
        "taskStatus": ["scheduled", "waiting"],
        "s3Prefix": "s3://data-lake/done-markers/{{yyyymmdd}}/",
        "fileName": "{{taskId}}.done"
      }
    }
  ]
}
```

This pattern provides:
- Simple skip (internal state change only)
- Skip with S3 marker (for external system coordination)

**Pattern 3: Comprehensive Control**

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionRun",
      "variables": {
        "taskStatus": ["scheduled"]
      }
    },
    {
      "action": "LeastActionCancel",
      "variables": {
        "taskStatus": ["running", "scheduled", "queued_for_connection", "queued_in_redis"]
      }
    },
    {
      "action": "LeastActionRerun",
      "variables": {
        "taskStatus": ["error", "failed", "canceled", "timeout"]
      }
    },
    {
      "action": "LeastActionRerunSubtree",
      "variables": {
        "taskStatus": ["error", "failed"]
      }
    },
    {
      "action": "LeastActionSkip",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
      }
    },
    {
      "action": "LeastActionSkipSubtree",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
      }
    }
  ]
}
```

This comprehensive pattern provides all control options, filtered by appropriate task states.

### Programmatic Task Control

Task control actions can be invoked programmatically via API or within other tasks. **Use with caution** to avoid cascading effects.

**API Invocation:**

```bash
POST /actions/control/execute
{
  "action": "LeastActionRerun",
  "variables": {
    "task_ids": [123, 456, 789],
    "task_status": ["error"]
  }
}
```

**Within Task Actions:**

```json
{
  "postAction": [
    {
      "action": "LeastActionRerunFailedChildren",
      "variables": {
        "taskStatus": ["error", "failed"]
      }
    }
  ]
}
```

## Examples - Real-World Workflows

### Example 1: Daily Sales ETL Pipeline

**Workflow Structure:**

```
sales_etl_pipeline/
├── extract_sales_data
├── transform_sales_data
├── load_sales_data
└── validate_sales_data
```

**Workflow Config:**

```json
{
  "defaults": {
    "task": {
      "retry_count": 3,
      "retry_interval": 300,
      "timeout": 3600,
      "preAction": [
        {
          "action": "LeastActionGitSync",
          "connection": "github-main",
          "variables": {}
        }
      ]
    }
  },
  "parameters": {
    "s3_bucket": "s3://data-lake-prod/sales",
    "database": "analytics",
    "table_prefix": "fact_"
  },
  "schedule": {
    "cron": "0 2 * * *"
  },
  "partition": "sales_daily"
}
```

**Task 1: Extract**

```json
{
  "task_id": "extract_sales_data",
  "workflow": "sales_etl_pipeline",
  "operator": "operator.python",
  "connection": "python-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "0 2 * * *",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "state": "scheduled",
  "payload": {
    "script": "extract_sales.py",
    "args": [
      "--date", "{{ ds }}",
      "--output", "{{ s3_bucket }}/raw/{{ ds }}/"
    ]
  },
  "actions": {
    "postAction": [
      {
        "action": "LeastActionCheckS3FileExists",
        "connection": "s3-prod",
        "variables": {
          "s3_path": "{{ s3_bucket }}/raw/{{ ds }}/sales.csv"
        }
      }
    ]
  }
}
```

**Task 2: Transform**

```json
{
  "task_id": "transform_sales_data",
  "workflow": "sales_etl_pipeline",
  "operator": "operator.spark",
  "connection": "spark-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "0 2 * * *",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "state": "scheduled",
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckIfParentsAreDone",
        "variables": {
          "parent_tasks": ["extract_sales_data"],
          "partition": "sales_daily"
        }
      }
    ]
  },
  "payload": {
    "script": "transform_sales.py",
    "args": [
      "--input", "{{ s3_bucket }}/raw/{{ ds }}/",
      "--output", "{{ s3_bucket }}/processed/{{ ds }}/"
    ]
  }
}
```

**Task 3: Load**

```json
{
  "task_id": "load_sales_data",
  "workflow": "sales_etl_pipeline",
  "operator": "operator.AWSredshift",
  "connection": "redshift-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "0 2 * * *",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "state": "scheduled",
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckIfParentsAreDone",
        "variables": {
          "parent_tasks": ["transform_sales_data"],
          "partition": "sales_daily"
        }
      }
    ],
    "runningAction": [
      {
        "action": "LeastActionSlackWebhook",
        "sla": 3600,
        "connection": "slack-alerts",
        "variables": {
          "message": "Load task exceeded 1 hour SLA"
        }
      }
    ]
  },
  "payload": {
    "sql": "COPY {{ database }}.{{ table_prefix }}sales FROM '{{ s3_bucket }}/processed/{{ ds }}/' IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftRole' FORMAT AS PARQUET;"
  }
}
```

**Task 4: Validate**

```json
{
  "task_id": "validate_sales_data",
  "workflow": "sales_etl_pipeline",
  "operator": "operator.python",
  "connection": "python-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "0 2 * * *",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "state": "scheduled",
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckIfParentsAreDone",
        "variables": {
          "parent_tasks": ["load_sales_data"],
          "partition": "sales_daily"
        }
      }
    ],
    "postAction": [
      {
        "action": "LeastActionSlackWebhook",
        "connection": "slack-alerts",
        "variables": {
          "message": "Sales ETL completed successfully for {{ ds }}"
        }
      }
    ]
  },
  "payload": {
    "script": "validate_sales.py",
    "args": ["--date", "{{ ds }}"]
  }
}
```

### Example 2: AWS Lambda Data Processing Workflow

**Workflow: Real-time Event Processing**

```json
{
  "task_id": "process_events_lambda",
  "workflow": "event_processing",
  "operator": "operator.AWSIAMRole",
  "connection": "lambda-prod",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "ADHOC",
  "state": "scheduled",
  "payload": {
    "function_name": "process-user-events",
    "invoke_payload": {
      "date": "{{ ds }}",
      "bucket": "{{ s3_bucket }}",
      "batch_size": 1000
    },
    "invocation_type": "RequestResponse",
    "log_type": "Tail"
  },
  "config": {
    "retry_count": 5,
    "retry_interval": 60,
    "timeout": 900,
    "parameters": {
      "s3_bucket": "s3://events-prod"
    }
  },
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckS3FileExists",
        "connection": "s3-prod",
        "variables": {
          "s3_path": "{{ s3_bucket }}/events/{{ ds }}/"
        }
      }
    ],
    "postAction": [
      {
        "action": "LeastActionUpdateMetadata",
        "variables": {
          "function_name": "{{ payload.function_name }}",
          "execution_date": "{{ ds }}",
          "status": "completed"
        }
      }
    ]
  }
}
```

**Connection Configuration:**

```json
{
  "name": "Lambda Production",
  "type": "connection.AWSIAMRole",
  "max_parallelism": 10,
  "enabled": true,
  "content": {
    "aws": {
      "role_arn": "arn:aws:iam::123456789:role/LambdaRole",
      "region": "us-east-1"
    }
  }
}
```

### Example 3: Multi-Stage ML Pipeline

**Workflow: Model Training and Deployment**

```
ml_pipeline/
├── prepare_training_data
├── train_model
├── evaluate_model
└── deploy_model
```

**Task 1: Prepare Data**

```json
{
  "task_id": "prepare_training_data",
  "workflow": "ml_pipeline",
  "operator": "operator.databricks",
  "connection": "databricks-ml",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "ADHOC",
  "state": "scheduled",
  "payload": {
    "notebook_path": "/notebooks/prepare_data",
    "base_parameters": {
      "input_path": "{{ s3_bucket }}/raw/{{ ds }}/",
      "output_path": "{{ s3_bucket }}/training/{{ ds }}/"
    }
  }
}
```

**Task 2: Train Model**

```json
{
  "task_id": "train_model",
  "workflow": "ml_pipeline",
  "operator": "operator.python",
  "connection": "python-gpu",
  "account_laui": "account_123",
  "project_laui": "project_456",
  "parent_laui": "workflow_789",
  "frequency": "ADHOC",
  "state": "scheduled",
  "config": {
    "timeout": 14400,
    "retry_count": 1
  },
  "actions": {
    "preAction": [
      {
        "action": "LeastActionCheckIfParentsAreDone",
        "variables": {
          "parent_tasks": ["prepare_training_data"]
        }
      }
    ],
    "runningIntervalAction": [
      {
        "action": "LeastActionLogMetrics",
        "interval": 600,
        "variables": {
          "metrics": ["training_loss", "validation_accuracy"]
        }
      }
    ]
  }
}
```
