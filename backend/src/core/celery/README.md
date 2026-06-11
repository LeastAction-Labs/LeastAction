# Celery Module Documentation

## Overview

The Celery module provides distributed task execution capabilities for the LeastAction system. It enables asynchronous execution of tasks and actions using Celery workers, supporting both synchronous and asynchronous operator patterns.

**Key Features:**
- **Dual execution modes**: Synchronous and asynchronous operator support
- **Action lifecycle management**: Pre-actions (blocking), running-actions (SLA-based), and post-actions (cleanup)
- **Task cancellation**: User-initiated graceful cancellation during execution
- **Heartbeat monitoring**: Automatic heartbeat updates and health tracking
- **Session context**: Structured logging with session and task context
- **Background execution**: Operator `run()` executed in background thread for better control
- **Comprehensive error handling**: Detailed error context and graceful degradation

## Recent Updates

This documentation reflects the latest architecture with the following major changes:

1. **Registry-based architecture**: Task, action, and cron entry points moved to `registry/` directory
2. **Shared API client**: Single unauthenticated API client instance shared across all tasks
3. **Per-request authentication**: Bearer token passed as first parameter to all API calls (NEW)
4. **Task & action authentication**: Tasks and actions now receive `user_access_token` for internal API calls (NEW)
5. **Cron execution**: New `run_cron` task for scheduled cron job execution
6. **Worker initialization**: Automatic logger reinitialization in worker processes
7. **Enhanced API client**: Added methods for batch operations, project management, and task finishing
8. **Environment variable support**: Configuration supports `API_CLIENT_BASE_URL` and `REDIS_HOST` from env
9. **Improved worker configuration**: Additional worker settings for memory limits, task lifecycle, and event tracking
10. **Cancellation support**: User can cancel tasks via `user_set_state` field
11. **Background threading**: `run()` executes in background thread with polling loop for control
12. **Session context**: All logging uses session context for traceability

## Architecture

### Architectural Overview

The Celery module uses a **registry-based architecture** where task definitions are organized in the `registry/` directory and automatically loaded on application startup. This provides:

1. **Separation of Concerns**: Entry points (registry/) are separated from execution logic (executors/)
2. **Shared Resources**: Single authenticated API client instance reduces overhead and ensures consistency
3. **Worker Lifecycle Management**: Automatic logger initialization in each worker process
4. **Authentication**: Built-in Bearer token authentication for all API requests
5. **Multi-Queue Support**: Separate queues for tasks, actions, and cron jobs for better resource allocation

### Core Components

```
celery/
├── app.py                        # Celery application initialization
├── config.py                     # Configuration management
├── worker_init.py                # Worker process initialization
├── shared_client.py              # Shared authenticated API client instance
├── client.py                     # API client for backend communication
├── schema.py                     # Pydantic models for requests
├── utils.py                      # Utility functions
├── registry/                     # Task registration directory
│   ├── __init__.py               # Imports all registered tasks
│   ├── tasks.py                  # Celery task entry point for tasks
│   ├── actions.py                # Celery task entry point for actions
│   └── crons.py                  # Celery task entry point for cron jobs
└── executors/                    # Execution service implementations
    ├── task_executor.py          # Task execution orchestration
    ├── action_executor.py        # Action execution service
    └── operator_executor.py      # Operator lifecycle management
```

## File Descriptions

### `app.py`
Initializes the Celery application instance with broker and backend configuration.

**Key Components:**
- `get_celery_config()`: Returns the singleton CeleryConfig instance
- `app`: Main Celery application instance configured with Redis broker

**Configuration:**
- Worker prefetch multiplier
- Task acknowledgment settings (acks_late, acks_on_failure_or_timeout)
- Task tracking options (track_started, send_task_events)
- Worker lifecycle settings (max_tasks_per_child, max_memory_per_child)
- Connection loss handling (cancel_long_running_tasks_on_connection_loss, reject_on_worker_lost)

**Imports:**
- Automatically imports `worker_init` module to register signal handlers
- Automatically imports `registry` module to register all task definitions

---

### `worker_init.py`
Handles worker process initialization and logger setup.

**Signal Handlers:**

#### `@signals.worker_process_init.connect`
- Triggered when each Celery worker process starts
- Reinitializes the logger in the worker process with proper configuration
- Ensures each worker has its own logger instance with correct settings

**Why this is needed:**
When Celery spawns worker processes, they inherit file descriptors but need their own logger configuration. This module ensures each worker process has a properly configured logger instance.

---

### `shared_client.py`
Provides a single shared API client instance for all Celery tasks.

**Exports:**
- `api_client`: Shared `APIClient` instance configured with:
  - Base URL from config (or `API_CLIENT_BASE_URL` environment variable)
  - No authentication token stored (passed per-request)

**Benefits:**
- Single client instance reduces overhead
- Flexible authentication (token passed per-request by caller)
- Centralized configuration management

**Usage:**
```python
from src.core.celery.shared_client import api_client

# Use in any task/action/cron
# Pass auth_token as first parameter to each API call
result = await api_client.get_item(auth_token, item_laui, session_id)
```

---

### `config.py`
Manages Celery configuration from `system.yml`.

**Class: `CeleryConfig`**

**Validation:**
Ensures all required configuration keys exist:
- `broker_url`: Redis broker URL (supports `REDIS_HOST` env variable for Docker)
- `result_backend`: Redis result backend URL (supports `REDIS_HOST` env variable)
- `operators_dir`: Directory for operator modules
- `actions_dir`: Directory for action modules
- Task/action time limits (soft and hard)
- Queue names for tasks, actions, and cron jobs

**Properties:**
- `broker_url`: Message broker URL (env-aware, replaces localhost with `REDIS_HOST` if set)
- `result_backend`: Result storage backend (env-aware, replaces localhost with `REDIS_HOST` if set)
- `task_soft_time_limit`: Soft timeout for tasks (seconds)
- `task_hard_time_limit`: Hard timeout for tasks (seconds)
- `action_soft_time_limit`: Soft timeout for actions (seconds)
- `action_hard_time_limit`: Hard timeout for actions (seconds)
- `task_queue`: Queue name for task execution
- `action_queue`: Queue name for action execution
- `cron_queue`: Queue name for cron job execution
- `worker_config`: Worker-specific configuration dictionary
- `api_client_base_url`: Base URL for API client (supports `API_CLIENT_BASE_URL` env variable)
- `api_auth_token`: Authentication token loaded via `load_access_token()` (returns empty string on error)

---

### `registry/__init__.py`
Central task registration module that imports all task definitions.

**Imports:**
- `registry.tasks` - Task execution entry points
- `registry.actions` - Action execution entry points
- `registry.crons` - Cron job execution entry points

**Purpose:**
This module is imported by `app.py` to automatically register all Celery tasks when the application starts. This ensures all task definitions are available to the Celery worker.

---

### `registry/tasks.py`
Defines the Celery task entry point for task execution.

**Dependencies:**
- Uses `shared_client.api_client` for API communication
- Creates `TaskExecutionService` instance with shared client
- Creates `ActionManager` instance for action lifecycle management

**Task:**

#### `execute_task(self, la_task_object: dict)`
Main entry point for task execution.

**Configuration:**
- Name: `least_action.execute_task`
- Queue: Configured task queue
- Soft time limit: From config
- Hard time limit: From config
- Bind: True (receives self reference for task introspection)

**Behavior:**
- Extracts and validates `last_run_session_id` and `laui` from task object
- Sets session context for structured logging (`session_id`, `task_id`, `logical_date`)
- Creates new event loop for async execution
- Bridges synchronous Celery → async task execution via `TaskExecutionService`
- Handles `SoftTimeLimitExceeded` gracefully
- Ensures loop cleanup and context cleanup in finally block
- Propagates exceptions to mark Celery task as FAILED

---

### `registry/actions.py`
Defines the Celery task entry point for action execution.

**Dependencies:**
- Uses `shared_client.api_client` for API communication
- Creates `ActionExecutionService` instance with shared client

**Task:**

#### `execute_action(self, la_action_object: dict)`
Entry point for action execution.

**Configuration:**
- Name: `least_action.execute_action`
- Queue: Configured action queue
- Soft time limit: From config
- Hard time limit: From config
- Bind: True (receives self reference for task introspection)

**Behavior:**
- Extracts and validates `session_id` from action object
- Parses `connection` from JSON string to dict if needed
- Sets session context for structured logging (`session_id`, `task_laui`, `logical_date`)
- Creates new event loop for async execution
- Bridges synchronous Celery → async action execution via `ActionExecutionService`
- Handles `SoftTimeLimitExceeded` gracefully
- Ensures loop cleanup and context cleanup in finally block
- Propagates exceptions to mark Celery task as FAILED

---

### `registry/crons.py`
Defines the Celery task entry point for scheduled cron job execution.

**Dependencies:**
- Uses `shared_client.api_client` for API communication
- Uses `CronExecutor` from `src.core.cron.cron_executor` for cron logic

**Task:**

#### `run_cron(self, project_laui: str, interval: int)`
Entry point for cron job execution.

**Configuration:**
- Name: `least_action.run_cron`
- Queue: Configured cron queue
- Bind: True (receives self reference for task introspection)

**Parameters:**
- `project_laui`: LAUI of the project to run cron jobs for
- `interval`: Interval in seconds for cron execution

**Behavior:**
- Generates a unique session ID for the cron run via `generate_session_id()`
- Sets session context for structured logging (`project_laui`, `interval`, `cron_run=True`)
- Creates new event loop for async execution
- Initializes `CronExecutor` with project LAUI, interval, and shared API client
- Executes cron jobs via `CronExecutor.run()`
- Comprehensive error logging with full tracebacks
- Ensures loop cleanup and context cleanup in finally block
- Propagates exceptions to mark Celery task as FAILED

**Use Case:**
- Periodic execution of scheduled tasks within a project
- Triggered by Celery Beat or manual scheduling
- Maintains session context for traceability across all cron-triggered tasks

---

### `executors/task_executor.py`
Orchestrates the complete lifecycle of task execution with support for synchronous/asynchronous operators, cancellation, heartbeats, and action execution.

**Class: `TaskExecutionService`**

**Dependencies:**
- `APIClient`: For API communication
- Operator directory from config
- Celery configuration for timeouts and polling

**Main Method: `execute_task(task: TaskRequest)`**

**Execution Flow:**
1. Fetch operator codeblock from API
2. Create temporary Python module from codeblock
3. Load and validate operator module via `OperatorExecutor`
4. Initialize operator (synchronous)
5. Start operator `run()` in background thread using `asyncio.to_thread()`
6. Enter continuous polling loop:
   - Update heartbeat every poll interval
   - Check for user-initiated cancellation (`user_set_state == "cancel"`)
   - Execute SLA-triggered running actions when elapsed time exceeds SLA threshold
   - Check if `run()` task is complete
   - For async operators: poll `check_completion()` until status != "running"/"pending"
   - For sync operators: break after run() completes
7. Handle timeout if elapsed time exceeds `check_completion_timeout_seconds`
8. Calculate next logical date (for scheduled tasks)
9. Execute post-actions in finally block
10. Update task status in API
11. Cleanup modules and files

**Operator Execution Types:**

**Synchronous:**
```python
{
    "status": "success",  # or "failed"
    "output": {...}
}
```
Execution completes immediately after `run()` returns.

**Asynchronous:**
```python
{
    "execution_type": "async",
    "job_id": "...",
    ...
}
```
Followed by continuous polling via `check_completion()` until status != "running"/"pending".

**Heartbeat & Cancellation:**
- Updates `latest_heartbeat` and `state` in API every poll interval
- Checks `user_set_state` field for cancellation requests
- If cancelled: sets `operator_exec.cancelled = True`, cancels run task, updates status to ERROR

**SLA Actions (Running Actions):**
- Each running action can have an optional `sla` field (in minutes)
- During polling loop, executes action when `elapsed_time > sla * 60 seconds`
- Tracks executed SLA actions to prevent re-execution
- Actions are dispatched asynchronously via `execute_action.apply_async()`

**Post Actions:**
- Executed in finally block after task completion (regardless of success/failure)
- Dispatched asynchronously via `execute_action.apply_async()`
- All post-actions are fire-and-forget (not awaited)

**Error Handling:**
- Catches all exceptions during execution
- Updates task state to ERROR
- Stores error details in `last_run_output`
- Ensures cleanup in finally block (operator finish, file cleanup, API update, post-actions)

**Helper Methods:**
- `_update_heartbeat()`: Updates task heartbeat and state in API
- `_check_cancellation()`: Checks if user requested cancellation
- `_cleanup()`: Removes modules and deletes temporary files

---

### `executors/action_executor.py`
Handles execution of individual actions with comprehensive validation and error handling.

**Class: `ActionExecutionService`**

**Dependencies:**
- `APIClient`: For fetching action codeblock
- `action_dir`: Directory for temporary action modules

**Responsibilities:**
- Load action codeblock from API
- Create temporary action module
- Validate action module structure
- Execute action with provided variables
- Comprehensive error handling and logging
- Cleanup temporary files and modules

**Validation Rules:**
- Module must have a `run` function
- `run` must be callable
- `run` must be synchronous (not async)

**Method: `execute_action(la_action_object: ActionRequest)`**

**Execution Flow:**
1. Fetch action item from API via `_get_action_item()`
2. Extract codeblock (raise `NotFoundError` if missing)
3. Create temporary Python files via `create_module_from_codeblock()`
4. Load action module via `load_module()`
5. Validate module structure via `_validate_action_module()`
6. Convert action object to dict
7. Execute `run(action_object_dict, **action_variables)`
8. Return result wrapped in dict: `{"result": result}`
9. Cleanup module and files in finally block

**Helper Methods:**
- `_get_action_item()`: Fetches action from API, raises `NotFoundError` or `UnprocessableEntityError`
- `_validate_action_module()`: Validates run() exists, is callable, and is synchronous

**Error Handling:**
- `NotFoundError`: Action not found or missing codeblock
- `InvalidArgumentError`: Invalid input parameters
- `UnprocessableEntityError`: File creation or module load failure
- `CeleryExecutionError`: Action execution failure
- All errors include detailed context (action_laui, error message, etc.)

**Cleanup:**
- Removes module from `sys.modules`
- Deletes all created temporary files via `file_path.unlink()`
- Runs even if execution fails
- Logs cleanup operations

---

### `executors/operator_executor.py`
Encapsulates the lifecycle of a single operator execution with validation and error handling.

**Class: `OperatorExecutor`**

**Attributes:**
- `module`: The loaded operator module
- `task`: TaskRequest object
- `client`: Operator client (initialized by operator's initialize())
- `result`: Result from operator's run()
- `completion_details`: Result from operator's check_completion()
- `cancelled`: Boolean flag for cancellation state

**Operator Contract:**
Every operator module must implement:
- `initialize(task_dict)`: Setup - Returns client object (synchronous)
- `run(task_dict, client)`: Main logic - Returns execution result (MUST be synchronous)
- `check_completion(task_dict, client, result)`: Status check (synchronous)
- `finish(task_dict, client, completion_details, result)`: Cleanup (synchronous, doesn't raise)

**Lifecycle Methods:**

#### `validate()`
Validates operator module structure:
- Checks for required methods: `initialize`, `run`, `check_completion`, `finish`
- Ensures all methods are callable
- Enforces `run()` is synchronous (not async)
- Raises `CeleryExecutionError` with detailed context if validation fails

**Why the async check is required:**
The `run()` method is executed in a background thread via `asyncio.to_thread()` (see `task_executor.py:108-110`), which only works with synchronous functions. Async functions would return coroutine objects that cannot execute in regular threads. This validation prevents confusing runtime errors by catching the mistake early with a clear message directing developers to use `execution_type='async'` if they need async behavior.

#### `initialize()`
Calls operator's `initialize()` method:
- Converts task to dict via `task.model_dump()`
- Creates operator client
- Stores client for later use
- Raises `CeleryExecutionError` on failure

#### `run()`
Calls operator's `run()` method:
- Requires client to be initialized
- Converts task to dict via `task.model_dump()`
- Must be synchronous (executed in background thread by TaskExecutionService)
- Returns execution result
- Result determines execution type (sync vs async)
- Raises `CeleryExecutionError` on failure

#### `check_completion()`
Polls for async operation completion:
- Converts task to dict via `task.model_dump()`
- Calls operator's `check_completion(task_dict, client, result)`
- Returns completion status payload
- Called repeatedly until status != "running"/"pending"
- Raises `CeleryExecutionError` on failure

#### `finish()`
Cleanup operator resources:
- Converts task to dict via `task.model_dump()`
- Calls operator's `finish(task_dict, client, completion_details, result)`
- Catches all exceptions (doesn't raise)
- Only called if client is initialized

---

### `celery_orchestrator.py`
High-level API for submitting and managing Celery tasks.

**Class: `CeleryOrchestrator`**

**Methods:**

#### `run_task(task: TaskRequest) -> str`
Submits a task for execution.
- Returns: Celery task ID
- Uses `apply_async()` for non-blocking submission

#### `run_action(action: ActionRequest) -> str`
Submits an action for execution.
- Returns: Celery task ID

#### `cancel_execution(task_id: str)`
Gracefully cancels a running task.
- Allows cleanup via finally blocks
- Uses `revoke(terminate=False)`

#### `force_cancel_execution(task_id: str)`
Emergency kill of a task.
- No cleanup guaranteed
- Uses `SIGKILL` signal
- Use only when graceful cancel fails

**Dependency Injection:**
```python
def get_celery_orchestrator(request: Request) -> CeleryOrchestrator:
    return request.app.state.celery_orchestrator
```

---

### `client.py`
HTTP client for communicating with the LeastAction API with authentication support.

**Class: `APIClient`**

**Constructor:**
- `__init__(base_url: str, auth_token: Optional[str] = None)`: Initialize client with base URL and optional auth token

**Configuration:**
- Base URL from config or environment variable
- 30-second timeout for all requests
- Optional Bearer token authentication

**Authentication:**

#### `_build_headers(additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]`
Builds request headers with authentication token.
- Adds `Authorization: Bearer {token}` header if auth_token is set
- Merges with additional headers if provided
- Used internally by all API methods

**Methods:**

#### `async get_item(auth_token: str, item_laui: str, session_id: Optional[str] = None) -> Item`
Fetches an item by LAUI.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `item_laui`: Item identifier
  - `session_id`: Optional session identifier
- Endpoint: `GET /catalog/get?item_laui={item_laui}`
- Returns: `Item` object
- Includes Bearer token authentication header

#### `async update_item(auth_token: str, task: TaskRequest, update_data: TaskUpdateData) -> str`
Updates a task item.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `task`: Task object containing laui and session info
  - `update_data`: Data to update on the task
- Endpoint: `POST /task/update/{task.laui}`
- Headers: `X-Session-ID` from task, plus Bearer token authentication
- Excludes None values from update payload
- Uses JSON serialization for proper type handling
- Returns: task LAUI string
- Logs errors with detailed payload and response information

#### `async finish_task(auth_token: str, task_laui: str, session_id: Optional[str] = None)`
Marks a task as finished.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `task_laui`: Task identifier
  - `session_id`: Optional session identifier
- Endpoint: `POST /task/finish/{task_laui}`
- Includes Bearer token authentication header
- Raises on HTTP errors

#### `async get_tasks_ready_to_run(auth_token: str, project_laui: PydanticObjectId) -> List[Dict]`
Fetches all tasks ready to run for a project.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `project_laui`: Project identifier
- Endpoint: `GET /catalog/get/tasks_ready_to_run/{project_laui}`
- Returns: List of task dictionaries
- Includes Bearer token authentication header
- Logs task count for monitoring

#### `async run_multiple_tasks(auth_token: str, task_lauis: List[str]) -> Dict[str,Any]`
Triggers execution of multiple tasks in batch.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `task_lauis`: List of task identifiers to execute
- Endpoint: `POST /task/multiple_tasks`
- Payload: `{"task_lauis": [...]}`
- Includes Bearer token authentication header
- Logs execution results and errors
- Returns: Execution result dictionary

#### `async get_project(auth_token: str, item_laui: PydanticObjectId) -> Dict[str,Any]`
Fetches a project by LAUI.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `item_laui`: Project identifier
- Endpoint: `GET /catalog/get?item_laui={item_laui}`
- Returns: Project dictionary with name and type
- Includes Bearer token authentication header
- Logs project metadata

#### `async update_project_metadata(auth_token: str, item_laui: str, item_type: str, name: str, parent_laui: Optional[str], folder_metadata: Dict) -> str`
Creates or updates project metadata.
- **Parameters:**
  - `auth_token`: Bearer token for authentication (required)
  - `item_laui`: Item identifier
  - `item_type`: Type of item (e.g., "folder.project")
  - `name`: Item name
  - `parent_laui`: Parent folder identifier (optional)
  - `folder_metadata`: Metadata dictionary including cron_status
- Endpoint: `POST /catalog/create`
- Payload includes item details and folder_metadata (e.g., cron_status)
- Includes Bearer token authentication header
- Logs update status and errors
- Returns: Item LAUI from response

---

### `schema.py`
Pydantic models for request validation and task state management.

**Models:**

#### `TaskRequest`
Represents a task execution request.

**Fields:**
- `laui`: Unique task identifier
- `last_run_session_id`: Session ID for the run
- `operator_laui`: LAUI of the operator to execute
- `connection`: Connection configuration (optional)
- `payload`: Task payload data
- `actions`: Actions object with pre/running/post action lists
- `frequency`: Cron expression or "ADHOC"
- `logical_date`: Scheduled execution time

**Config:**
- Allows extra fields via `extra="allow"`

#### `ActionRequest`
Represents an action execution request.

**Fields:**
- `laui`: Unique action identifier
- `task_laui`: LAUI of the associated task (optional)
- `session_id`: Session ID
- `connection_laui`: Connection LAUI (optional)
- `action_variables`: Dict of variables to pass to action
- `task_result`: Optional task result (for chaining)

**Config:**
- Allows extra fields via `extra="allow"`

#### `ActionItem` (from `src.core.task.action.schema`)
Represents a single action item in an action list.

**Fields:**
- `laui`: Unique action identifier
- `task_laui`: Associated task LAUI (optional, set at runtime)
- `session_id`: Session ID (optional, set at runtime)
- `connection_laui`: Connection LAUI (optional)
- `action_variables`: Dict of variables for the action
- `sla`: Optional SLA threshold in minutes (for running_actions)

#### `Actions` (from `src.core.task.action.schema`)
Container for different action lifecycle stages.

**Fields:**
- `create_actions`: List[ActionItem] - Actions executed when task is created
- `pre_actions`: List[ActionItem] - Actions executed before task submission (blocking)
- `running_actions`: List[ActionItem] - Actions with SLA triggers during execution
- `post_actions`: List[ActionItem] - Actions executed after task completion

#### `TaskState` (Enum)
Valid task states for mapping operator status.

**Values:**
- `PENDING`: Task is queued
- `RUNNING`: Task is executing
- `SUCCESS`: Task completed successfully
- `ERROR`: Task failed or was cancelled
- `TIMEOUT`: Task exceeded time limit

**Helper Function:**
- `task_state_map(status: str) -> TaskState`: Maps operator status strings to TaskState enum

---

### `utils.py`
Utility functions for module management and scheduling.

**Functions:**

#### `create_module_from_codeblock(codeblock: Dict[str, str], base_dir: Path) -> Path`
Creates Python files from code strings.

**Parameters:**
- `codeblock`: Dictionary mapping filename → code content
- `base_dir`: Directory to create files in

**Behavior:**
- Creates timestamped files: `{name}_{timestamp}.py`
- Validates all files are `.py` files
- Returns path to the first created file
- Cleans up all files on error

**Returns:** A list of paths to the created module files

**Exceptions:**
- `InvalidArgumentError`: Empty codeblock
- `UnprocessableEntityError`: Non-Python file or write failure

#### `load_module(path: Path) -> ModuleType`
Dynamically loads a Python module from file path.

**Parameters:**
- `path`: Path to Python file

**Behavior:**
- Generates unique module name: `leastAction_{uuid}`
- Loads module spec and executes
- Adds to `sys.modules`

**Returns:** Loaded module object

**Exceptions:**
- `UnprocessableEntityError`: Load failure

#### `calculate_logical_date(frequency: str, logical_date: datetime) -> datetime`
Calculates next run time from cron expression.

**Parameters:**
- `frequency`: Cron expression (e.g., "0 */6 * * *")
- `logical_date`: Current logical date

**Returns:** Next scheduled datetime

**Exceptions:**
- `ValueError`: Invalid cron expression

---

## Execution Flow

### Complete Task Execution Flow (with Actions)

```
1. API receives task execution request
   ↓
2. ItemOrchestrator.execute_task()
   ↓
3. Validate task creation/execution
   ↓
4. Execute pre-actions (ActionManager.pre_actions())
   │  - Blocks and waits for all pre-actions to complete
   │  - Returns False if any pre-action fails
   │  - Each pre-action executes via Celery worker
   ↓
5. If pre-actions successful → TaskManager.execute_task()
   ↓
6. CeleryOrchestrator.run_task() → submits to Celery
   ↓
7. Celery worker picks up task
   ↓
8. execute_task() entry point (tasks.py)
   │  - Sets session context
   │  - Creates event loop
   ↓
9. TaskExecutionService.execute_task()
   │
   ├─→ Fetch operator codeblock from API
   ├─→ Create temporary Python module
   ├─→ Load and validate operator module
   ├─→ OperatorExecutor.initialize()
   ├─→ Start OperatorExecutor.run() in background thread
   │
   ├─→ Polling Loop (until timeout or completion):
   │   ├─→ Update heartbeat
   │   ├─→ Check for user cancellation
   │   ├─→ Execute running-actions if SLA threshold exceeded
   │   ├─→ Check if run() task completed
   │   ├─→ For async: poll OperatorExecutor.check_completion()
   │   └─→ Sleep poll_interval
   │
   ├─→ Calculate next logical_date (if scheduled)
   │
   └─→ Finally block:
       ├─→ OperatorExecutor.finish()
       ├─→ Execute post-actions (fire-and-forget)
       ├─→ Update task status in API
       └─→ Cleanup modules and files
```

### Action Execution Flow

```
1. Action triggered (pre-action, running-action with SLA, or post-action)
   ↓
2. For pre-actions: ActionManager._run_action_with_timeout() blocks
   For running/post: execute_action.apply_async() (fire-and-forget)
   ↓
3. Celery worker picks up action
   ↓
4. execute_action() entry point (actions.py)
   │  - Sets session context
   │  - Creates event loop
   ↓
5. ActionExecutionService.execute_action()
   ↓
6. Fetch action codeblock from API
   ↓
7. Create temporary Python module
   ↓
8. Load action module
   ↓
9. Validate module has run() function (and is sync)
   ↓
10. Execute action.run(action_object_dict, **action_variables)
    ↓
11. Return {"result": result}
    ↓
12. Finally: Cleanup modules and files
```

### Cron Execution Flow

```
1. Cron task triggered (via Celery Beat or manual scheduling)
   ↓
2. run_cron() entry point (registry/crons.py)
   │  - Generates unique session ID
   │  - Sets session context with project_laui and interval
   │  - Creates event loop
   ↓
3. CronExecutor.run()
   │
   ├─→ Fetch project details from API
   ├─→ Get all tasks ready to run for this project
   ├─→ Filter tasks based on frequency and logical_date
   ├─→ Execute qualifying tasks via run_multiple_tasks()
   │
   └─→ Update project metadata with cron status
   ↓
4. Finally: Cleanup event loop and session context
```

**Cron Job Characteristics:**
- Each cron run gets a unique session ID for traceability
- Uses shared authenticated API client
- Handles batch task execution for efficiency
- Updates project-level cron status metadata
- Full error logging with stack traces

---

### Action Lifecycle Stages

**1. Create Actions**
- Executed when a task item is first created (not during execution)
- Handled by ActionManager.create_actions()

**2. Pre-Actions**
- Executed BEFORE task is submitted to Celery
- Blocking - waits for all pre-actions to complete
- If any pre-action fails, task execution is aborted
- Use case: Prerequisites, validation, resource preparation

**3. Running Actions (with SLA)**
- Executed DURING task execution
- Triggered when elapsed time > SLA threshold (in minutes)
- Asynchronous - fire-and-forget
- Tracked to prevent duplicate execution
- Use case: Progress notifications, timeout alerts

**4. Post-Actions**
- Executed AFTER task completion (in finally block)
- Asynchronous - fire-and-forget
- Runs regardless of task success/failure
- Use case: Cleanup, notifications, logging

## Configuration

### Required `system.yml` Structure

```yaml
celery:
  broker_url: "redis://localhost:6379/0"          # Supports REDIS_HOST env variable
  result_backend: "redis://localhost:6379/0"      # Supports REDIS_HOST env variable
  api_client_base_url: "http://localhost:8000"    # Can be overridden by API_CLIENT_BASE_URL env

  operators_dir: "./temp/operators"
  actions_dir: "./temp/actions"

  task:
    soft_time_limit: 3600    # 1 hour
    hard_time_limit: 3900    # 1 hour 5 minutes

  action:
    soft_time_limit: 300     # 5 minutes
    hard_time_limit: 330     # 5.5 minutes

  queues:
    task_queue: "least_action_tasks"
    action_queue: "least_action_actions"
    cron_queue: "least_action_crons"      # New: Queue for cron job execution

  worker:
    prefetch_multiplier: 1
    acks_late: true
    track_started: true
    reject_on_worker_lost: true           # New: Reject tasks if worker crashes
    acks_on_failure_or_timeout: false     # New: Don't ack failed/timed out tasks
    max_tasks_per_child: 100              # New: Recycle worker after N tasks
    max_memory_per_child: 524288          # New: Recycle worker after 512MB
    cancel_long_running_tasks_on_connection_loss: true  # New: Cancel tasks on disconnect
    send_task_events: true                # New: Send task lifecycle events
    send_sent_event: true                 # New: Send task-sent events

  check_completion_timeout_seconds: 7200  # 2 hours (max time for async operations)
  poll_interval_seconds: 2                # Heartbeat/completion check interval

action_timeout_seconds: 300                # Timeout for pre-action execution (5 minutes)
```

**Environment Variables:**
- `REDIS_HOST`: Overrides `localhost` in `broker_url` and `result_backend` (useful for Docker)
- `API_CLIENT_BASE_URL`: Overrides `api_client_base_url` from config
- Authentication token: Loaded automatically via `load_access_token()` from IAM module

## Operator Contract

Operators must implement the following four methods:

### `initialize(task_dict: dict) -> Any`
**Purpose:** Setup operator client/resources

**Requirements:**
- MUST be synchronous
- Receives task object as dictionary (from TaskRequest.model_dump())
- Returns client object for use in other methods

### `run(task_dict: dict, client: Any) -> dict`
**Purpose:** Execute the main operator logic

**Requirements:**
- MUST be synchronous (executed in background thread)
- Receives task object as dictionary and client from initialize()
- Returns execution result dictionary

**Why run() Must Be Synchronous:**
The `run()` method is executed using `asyncio.to_thread()` in a background thread (see `task_executor.py:108-110`). This design allows the main async event loop to continue polling for cancellation, heartbeats, and SLA-based actions while `run()` executes.

`asyncio.to_thread()` expects a synchronous callable - if `run()` were async:
1. Calling it would return a coroutine object instead of executing
2. Coroutines cannot run in regular threads (they require an event loop)
3. This would cause runtime failures

The validation in `operator_executor.py` catches this mistake early with: `"Async run() is not allowed. Use execution_type='async'."` If your operator needs async I/O, use synchronous blocking calls in `run()` and return `{"execution_type": "async", "job_id": "..."}` to enable polling via `check_completion()`.

**Return Formats:**
- **Synchronous execution:** `{"status": "success|failed", "output": {...}}`
- **Asynchronous execution:** `{"execution_type": "async", "job_id": "...", ...}`

### `check_completion(task_dict: dict, client: Any, result: Any) -> dict`
**Purpose:** Check status of async operation

**Requirements:**
- Called periodically until status != "running"/"pending"
- Receives task dict, client from initialize(), and result from run()
- Returns status dictionary: `{"status": "running|pending|success|failed", "output": {...}}`

### `finish(task_dict: dict, client: Any, completion_details: Any, result: Any) -> None`
**Purpose:** Cleanup resources

**Requirements:**
- Called in finally block regardless of success/failure
- Should NOT raise exceptions
- Receives task dict, client, completion_details from check_completion(), and result from run()
- Returns None

## Action Contract

Actions must implement a single method:

### `run(action_object_dict: dict, **action_variables) -> Any`
**Purpose:** Execute the action

**Requirements:**
- MUST be synchronous
- Receives action object as dictionary (from ActionRequest.model_dump())
- Receives unpacked action variables as keyword arguments
- Returns any JSON-serializable value

**Input Parameters:**
- `action_object_dict`: Contains laui, task_laui, session_id, connection_laui, action_variables
- `**action_variables`: Unpacked from action_object_dict["action_variables"]

**Return Value:**
- Any JSON-serializable value
- Result is wrapped in `{"result": <return_value>}` by ActionExecutionService

## Error Handling

### Exception Hierarchy

- `NotFoundError`: Resource not found (operator, action, item)
- `InvalidArgumentError`: Invalid input parameters
- `UnprocessableEntityError`: Processing failure (file creation, module load)
- `CeleryExecutionError`: Execution failure (operator/action run)

### Retry Strategy

- Soft time limit: Raises `SoftTimeLimitExceeded`
  - Task can handle gracefully
  - Cleanup runs in finally block

- Hard time limit: Force kills task
  - No cleanup guaranteed
  - Use as last resort

### Cleanup Guarantees

All execution paths ensure:
1. Modules removed from `sys.modules`
2. Temporary files deleted
3. API status updated
4. Operator `finish()` called (if initialized)

## Usage

### Starting Celery Worker

**Command:**
```bash
celery -A src.core.celery.app worker --loglevel=info --queues=least_action_tasks,least_action_actions,least_action_crons --concurrency=4
```

**Parameters:**
- `-A src.core.celery.app`: Application module path
- `--loglevel`: Set to info, debug, warning, or error
- `--queues`: Comma-separated list of queue names (task_queue, action_queue, and cron_queue)
- `--concurrency`: Number of worker processes (adjust based on CPU cores)

**Worker Initialization:**
- Logger is automatically reinitialized in each worker process via `worker_init.py`
- All task definitions from `registry/` are automatically loaded
- Shared API client with authentication is available to all tasks

### Submitting a Task

Tasks are submitted via `CeleryOrchestrator.run_task(task: TaskRequest)` which returns a Celery task ID.

**Required TaskRequest fields:**
- `laui`: Unique task identifier
- `last_run_session_id`: Session ID for tracking
- `operator_laui`: Operator to execute
- `actions`: Actions object with pre/running/post action lists
- `frequency`: Cron expression or "ADHOC"
- `logical_date`: Scheduled execution time

**Optional fields:**
- `connection`: Connection configuration
- `payload`: Task-specific data

### Submitting an Action

Actions are submitted via `CeleryOrchestrator.run_action(action: ActionItem)` which returns a Celery task ID.

**Required ActionItem fields:**
- `laui`: Unique action identifier
- `action_variables`: Dictionary of variables for the action

**Optional fields:**
- `task_laui`: Associated task identifier
- `session_id`: Session ID
- `connection_laui`: Connection identifier
- `sla`: SLA threshold in minutes (for running_actions)

### Canceling a Task

**Graceful cancellation:** `orchestrator.cancel_execution(task_id)` - Allows cleanup in finally blocks
**Force kill:** `orchestrator.force_cancel_execution(task_id)` - Emergency termination with SIGKILL

## Monitoring

### Task Status
Query task status using `AsyncResult(task_id, app=app)` which provides:
- `state`: Current task state (PENDING, STARTED, SUCCESS, FAILURE, etc.)
- `result`: Task return value or exception
- `successful()`: Boolean indicating success

### Worker Status
**Active tasks:** `celery -A src.core.celery.app inspect active`
**Worker statistics:** `celery -A src.core.celery.app inspect stats`

## Integration with ActionManager

The `ActionManager` (from `src.core.task.action.action_manager`) orchestrates action execution at different lifecycle stages:

**Class: `ActionManager`**

**Methods:**

### `pre_actions(la_actions_object: Actions, task_laui: str) -> bool`
- Executes pre-actions BEFORE task submission to Celery
- Blocks and waits for all pre-actions to complete
- Returns `True` if all succeed, `False` if any fails
- Uses `_run_action_with_timeout()` with `wait_for_result=True`
- Timeout configured via `action_timeout_seconds` in system config

### `running_actions(la_actions_object: Actions, task_laui: str) -> None`
- Fire-and-forget execution (not used in current flow)
- Running actions are actually executed by TaskExecutionService based on SLA

### `post_actions(la_actions_object: Actions, task_laui: str) -> None`
- Fire-and-forget execution (not used in current flow)
- Post-actions are actually executed by TaskExecutionService in finally block

### `_run_action_with_timeout(actions_list, action_type, task_laui, wait_for_result=False)`
- Internal method for executing action lists
- Sets `session_id` and `task_laui` on each action
- Dispatches via `celery_orchestrator.run_action()`
- If `wait_for_result=True`: blocks with timeout using `async_result.get(timeout=self.timeout)`
- Returns `False` if any action fails or times out

## Session Context and Logging

All Celery tasks use session context for structured logging to enable request tracing across distributed components.

**Session Context Functions:**
- `set_session_id(session_id)`: Sets the current session ID for logging
- `set_logger_context(dict)`: Adds contextual metadata (task_id, logical_date, etc.)
- `clear_session_id()`: Clears session ID (called in finally block)
- `clear_logger_context()`: Clears context metadata (called in finally block)

**Logging Functions:**
- `log_info(component, class_name, method_name, message)`: Info-level logging
- `log_error(component, class_name, method_name, message)`: Error-level logging

**Usage Pattern:**
1. Set session context at task entry point
2. Use structured logging throughout execution
3. Clear context in finally block to prevent leakage

## Authentication & Per-Request Authorization

### Overview

The authentication architecture has been redesigned to enable **tasks and actions to call internal APIs with user-specific authorization**. Previously, the API client stored a global authentication token at initialization. Now, authentication tokens are passed per-request, allowing each task/action execution to use the appropriate user's credentials.

### Key Changes

**Before:**
- API client initialized with a single static token
- All API calls used the same authentication
- Limited ability to support user-specific authorization

**After (NEW):**
- Shared API client has NO stored authentication token
- Each API call receives an explicit `auth_token` parameter
- Tasks and actions receive `user_access_token` from their request objects
- Full support for user-specific authorization policies

### Architecture

```
┌──────────────────────────────────────┐
│  Task/Action Request Object          │
│  - user_access_token: str (NEW)      │
│  - Contains Bearer token for user    │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Task/Action Execution                │
│  - Extract user_access_token         │
│  - Pass to all API calls             │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Shared API Client                   │
│  - No stored token                   │
│  - Receives token per request        │
│  - Builds Authorization header       │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Internal API Endpoints               │
│  - Validates Bearer token             │
│  - Enforces user-specific policies    │
└──────────────────────────────────────┘
```

### Practical Benefits

**1. User-Scoped Authorization**
- Each task execution inherits the user's permissions
- Tasks cannot access resources beyond user's scope
- Audit trail shows which user's token was used

**2. Cron Jobs with System Tokens**
- Cron executor receives `system_auth_token`
- Runs with system-level permissions for background jobs
- Separate from user-specific task execution

**3. Flexible Token Management**
- Tokens can be refreshed independently
- No need to restart workers for token updates
- Each request gets current valid token

### Implementation Details

#### In TaskRequest
```python
class TaskRequest(Task):
    user_access_token: str  # NEW: Bearer token from user's session
    # ... other fields
```

#### In ActionRequest
```python
class ActionRequest(ActionItem):
    user_access_token: str  # NEW: Bearer token from user's session
    # ... other fields
```

#### API Client Usage
```python
# OLD (no longer used)
# self.auth_token = token  # Stored at init

# NEW: Pass token to each method
await api_client.get_item(auth_token, item_laui, session_id)
await api_client.update_item(auth_token, task, update_data)
await api_client.get_tasks_ready_to_run(auth_token, project_laui)
```

#### In TaskExecutionService
```python
async def _update_heartbeat(self, la_task_object: TaskRequest) -> None:
    # Pass user's token to API call
    await self.api_client.update_item(
        la_task_object.user_access_token,  # NEW: Explicit token
        la_task_object,
        update_data=TaskUpdateData(...)
    )
```

#### In CronExecutor
```python
def __init__(self, project_id: str, interval: int, api_client: APIClient, system_auth_token: str):
    # ... 
    self.system_auth_token = system_auth_token  # System-level permissions
    
async def _trigger_task_ready_to_run(self) -> bool:
    # Use system token for background cron operations
    tasks = await self.api_client.get_tasks_ready_to_run(
        self.system_auth_token,  # NEW: System token
        project_laui
    )
```

### Migration Path

**For Existing Operators:**
1. No changes needed - tokens are handled by the framework
2. Operators receive tasks with `user_access_token` included
3. If operators call APIs directly, pass the token from task object:
   ```python
   # In operator code
   user_token = task_dict.get("user_access_token")
   result = await some_api_call(auth_token=user_token, ...)
   ```

**For New Operators:**
- Follow the token-per-request pattern
- Extract `user_access_token` from task dictionary
- Pass it to all internal API calls

### Security Implications

1. **Token Scope**: Each token carries specific user permissions
2. **No Token Leakage**: Tokens are passed in function arguments, not stored globally
3. **Audit Trail**: Each API call includes authenticated user identity
4. **Token Rotation**: System can rotate tokens without affecting in-flight requests
5. **Expiration Handling**: Expired tokens fail gracefully with 401 errors

---

## Cancellation Support

Tasks can be cancelled by the user through the API:

**User-Initiated Cancellation:**
1. User sets `user_set_state = "cancel"` on the task item via API
2. `TaskExecutionService._check_cancellation()` polls this field during execution
3. If cancelled: sets `operator_exec.cancelled = True`, cancels background run task
4. Updates task state to ERROR with message "Task cancelled by user"

**Graceful Cancellation:**
- Background run task is cancelled via `asyncio.Task.cancel()`
- `CancelledError` is caught and suppressed
- `operator_exec.finish()` is still called for cleanup
- Task status is updated in API

## Best Practices

1. **Time Limits**: Set soft limits 5-10% lower than hard limits to allow graceful cleanup
2. **Cleanup**: Always use try/finally for resource cleanup in operators
3. **Idempotency**: Design tasks to be safely retryable (important for Celery retries)
4. **Logging**: Use structured logging with session context for traceability
5. **Modularity**: Keep operators small and focused on a single responsibility
6. **Testing**: Test operators independently before integration
7. **Error Messages**: Include detailed context in exception details for debugging
8. **Heartbeats**: Heartbeats are automatically updated during polling loop
9. **Action Design**: Keep actions lightweight and fast (especially pre-actions)
10. **SLA Thresholds**: Set realistic SLA values for running-actions to avoid spam
11. **Operator Finish**: Never raise exceptions in finish() - it runs in finally block
12. **Session Context**: Always clean up session context in finally blocks
13. **Shared Client**: Use `shared_client.api_client` for all API operations (don't create new client instances)
14. **Authentication**: Never hardcode auth tokens; always use `load_access_token()` from IAM module
15. **Registry Organization**: Place new task types in appropriate `registry/` subdirectory
16. **Worker Configuration**: Monitor worker memory usage and adjust `max_memory_per_child` as needed
17. **Environment Variables**: Use env vars for deployment-specific config (Docker, staging, prod)
18. **Cron Jobs**: Ensure cron tasks are idempotent since they may run multiple times on failure

## Troubleshooting

### Common Issues

**Task hangs indefinitely:**
- Check `check_completion_timeout_seconds` in config
- Verify operator `check_completion()` returns proper status (not stuck on "running")
- Review `poll_interval_seconds` setting
- Check operator `run()` doesn't have infinite loops

**Pre-actions block task execution:**
- Check pre-action execution time vs `action_timeout_seconds`
- Review pre-action logs for errors or timeouts
- Ensure pre-action `run()` functions return properly
- Verify Celery workers are available to execute actions

**Running actions not executing:**
- Verify `sla` field is set on running actions (in minutes)
- Check that task execution time exceeds SLA threshold
- Review logs for "Executing running action" messages
- Ensure action queue workers are running

**Post-actions not executing:**
- Check task_executor logs in finally block
- Verify action queue workers are running
- Review for exceptions during post-action dispatch
- Check Celery worker logs for action execution

**Module not found errors:**
- Ensure `operators_dir`/`actions_dir` exist and have write permissions
- Check file permissions
- Verify codeblock is valid Python syntax
- Review temporary file creation logs

**Connection refused to Redis:**
- Confirm Redis is running: `redis-cli ping`
- Check `broker_url` and `result_backend` in config
- Verify network connectivity
- Check Redis max connections

**Tasks not picked up:**
- Verify Celery worker is running and consuming from correct queues
- Check queue names match in config and worker startup
- Review worker logs for errors
- Verify task is being dispatched: check Celery logs

**Cleanup not happening:**
- Check finally blocks execute (review logs)
- Ensure operator `finish()` doesn't raise exceptions
- Review `_cleanup()` method logs
- Verify temporary files are being deleted

**Session context errors:**
- Ensure `set_session_id()` is called before logging
- Verify `clear_session_id()` is in finally block
- Check that `last_run_session_id` exists in task object

**Task cancellation not working:**
- Verify `user_set_state` field is being set in database
- Check `_check_cancellation()` is being called in polling loop
- Review cancellation logs
- Ensure polling loop is running (not stuck in operator run())

**Operator finish() receives wrong arguments:**
- **BREAKING CHANGE**: `finish()` now receives 4 arguments: `task_dict`, `client`, `completion_details`, `result`
- Update operator code to match new signature
- Check logs for "Error in operator finish()" messages

**Authentication errors (401 Unauthorized):**
- Verify `load_access_token()` is returning a valid token
- Check IAM module configuration and token generation
- Review API client logs for authentication header details
- Ensure backend API is properly validating Bearer tokens
- For local development, authentication may be disabled (empty token)

**Cron jobs not executing:**
- Verify cron queue workers are running: check `--queues` includes `least_action_crons`
- Check Celery Beat is running if using scheduled cron jobs
- Review CronExecutor logs for task filtering logic
- Verify project metadata has correct cron configuration
- Check that tasks have proper `frequency` and `logical_date` fields

**Worker process logger not working:**
- Ensure `worker_init.py` is being imported by `app.py`
- Check worker process init signal handler is registered
- Verify Config() is accessible in worker processes
- Review worker startup logs for initialization errors

**Environment variable not being used:**
- Check env variable is exported: `echo $REDIS_HOST` or `echo $API_CLIENT_BASE_URL`
- Restart Celery workers after setting environment variables
- Verify config property correctly checks environment first
- For Docker, ensure env variables are passed to container

## Security Considerations

1. **Code Execution**: Operators execute arbitrary Python code
   - Validate code before storing in catalog
   - Consider sandboxing or containerization

2. **API Authentication**: ✓ Now implemented with Bearer token
   - API client uses authentication token from IAM module
   - Token loaded via `load_access_token()` and included in all API requests
   - Falls back to empty string on error (allows local development without auth)
   - All API requests include `Authorization: Bearer {token}` header

3. **File Permissions**: Temporary files stored on disk
   - Ensure proper directory permissions
   - Clean up orphaned files periodically

4. **Connection Strings**: May contain credentials
   - Store securely in vault
   - Never log connection details

5. **Environment Variables**: Sensitive configuration
   - `REDIS_HOST`: Used for Docker deployments
   - `API_CLIENT_BASE_URL`: Can override API endpoint
   - Authentication token: Managed by IAM module, not via environment variable

## Future Enhancements

### Completed ✓
- [x] Add comprehensive logging with session context
- [x] Support for action lifecycle (pre/running/post actions)
- [x] Implement SLA-based action triggers
- [x] Add task cancellation support
- [x] Heartbeat monitoring during execution
- [x] Background thread execution for operator run()
- [x] Add API authentication for client (Bearer token)
- [x] Registry-based task organization
- [x] Shared API client instance across tasks
- [x] Worker process initialization with logger setup
- [x] Cron job execution support
- [x] Environment variable configuration support
- [x] Enhanced worker lifecycle management

### Planned
- [ ] Implement metrics and monitoring (Prometheus/Grafana)
- [ ] Add retry policies for failed tasks
- [ ] Support multiple brokers (RabbitMQ, AWS SQS)
- [ ] Implement result caching for completed tasks
- [ ] Add task priority support (high/medium/low queues)
- [ ] Create operator testing framework with mocking
- [ ] Implement rate limiting per operator type
- [ ] Support task dependencies/DAGs
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Add support for dynamic operator loading from registry
- [ ] Create web UI for monitoring task execution
- [ ] Add support for task chaining and result passing
- [ ] Implement dead letter queue for failed tasks
- [ ] Add Celery Beat integration for scheduled cron jobs
- [ ] Implement task result callbacks and webhooks
