# Cron Scheduler System

A robust, distributed cron scheduling system that manages periodic task execution for projects in the Least Action Platform. The system uses Celery for asynchronous job execution and maintains task state through heartbeat monitoring.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Status Lifecycle](#status-lifecycle)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Guide](#usage-guide)
- [Monitoring & Heartbeat](#monitoring--heartbeat)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Overview

The cron scheduler system enables:
- **Periodic task execution** - Run tasks at defined intervals for each project
- **Distributed processing** - Uses Celery for asynchronous execution across workers
- **Health monitoring** - Heartbeat mechanism to detect stale or crashed schedulers
- **Graceful shutdown** - Clean stop signals with state tracking
- **Error recovery** - Resilient error handling with detailed logging

### Key Features

- ✅ Per-project configurable intervals (default: 5 seconds)
- ✅ Heartbeat-based liveness detection
- ✅ Status tracking with multiple states (STARTED, RUNNING, STOPPED, ERROR)
- ✅ Timezone-aware datetime handling (UTC)
- ✅ Batch task execution support
- ✅ Comprehensive logging and error reporting

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │           CronManager (request handler)          │   │
│  │  - start_cron()  - Stop existing cron jobs       │   │
│  │  - stop_cron()   - Start new cron jobs           │   │
│  │  - _cron_exists() - Check if cron is running     │   │
│  └──────────────────────────────────────────────────┘   │
│                        │                                │
│                        │ orchestrates                   │
│                        ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │        CeleryOrchestrator (task runner)          │   │
│  │  - run_cron() - Submits async job to Celery      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         │ submits async job
                         ▼
┌─────────────────────────────────────────────────────────┐
│          Celery Worker Process (Background)             │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │        CronExecutor (periodic worker)            │   │
│  │  - run() - Main scheduler loop                   │   │
│  │  - _trigger_task_ready_to_run() - Job iteration  │   │
│  │  - _update_project_status() - State tracking     │   │
│  │  - _update_project_metadata() - Heartbeat update │   │
│  └──────────────────────────────────────────────────┘   │
│                        │                                │
│                        │ at intervals                   │
│                        ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Task Execution Loop (infinite)          │   │
│  │  1. Query tasks ready to run                     │   │
│  │  2. Execute tasks via API client                 │   │
│  │  3. Update heartbeat                             │   │
│  │  4. Sleep for interval duration                  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                       
```

### Data Flow

1. **Start Request**: API receives `/cron/manage` request with `action: START`
2. **Manager Processing**: `CronManager.start_cron()` validates and initializes project
3. **Celery Submission**: `CeleryOrchestrator.run_cron()` submits async job
4. **Executor Loop**: `CronExecutor.run()` starts infinite loop in background worker
5. **Task Polling**: Every `interval` seconds, queries for ready tasks
6. **Task Execution**: Executes batch of tasks via API
7. **Heartbeat Update**: Updates `latest_heartbeat` timestamp
8. **Shutdown**: `CronManager.stop_cron()` signals executor to gracefully stop
9. **Cleanup**: Executor detects STOP signal and transitions to STOPPED state

---

## Components

### CronManager

**Location**: `cron_manager.py`

The main entry point for cron operations. Handles starting, stopping, and monitoring cron jobs.

#### Key Methods

```python
async def start_cron(project_laui: PydanticObjectId) -> bool
```
- Starts a new cron scheduler for a project
- Validates project exists and is a `folder.project`
- Initializes metadata with `STARTED` status
- Submits executor job to Celery
- **Raises**: `ConflictError` if already running, `NotFoundError` if project missing

```python
async def stop_cron(project_laui: PydanticObjectId) -> bool
```
- Requests graceful shutdown of cron scheduler
- Sets status to `STOP` (executor will transition to `STOPPED`)
- Updates `stop_date` timestamp
- **Raises**: `NotFoundError` if cron not running

```python
async def _cron_exists(project_laui: PydanticObjectId) -> bool
```
- Checks if a cron job is actively running
- Verifies status is `STARTED` or `RUNNING`
- **Heartbeat validation**: Returns `False` if heartbeat is stale (>4x interval)
- Handles timezone-aware datetime comparison

```python
def _get_cron_interval_for_project(project_name: str) -> int
```
- Retrieves per-project interval from config
- Falls back to global `project_scheduler_interval` (default: 5 seconds)
- Config key format: `{project_name}_cron_interval`

### CronExecutor

**Location**: `cron_executor.py`

Runs in a background Celery worker process. Executes the periodic task loop.

**Constructor:**
```python
def __init__(
    self,
    project_id: str,
    interval: int,
    api_client: APIClient,
    system_auth_token: str
)
```
- `project_id`: Project LAUI to manage cron for
- `interval`: Polling interval in seconds
- `api_client`: Shared API client instance
- `system_auth_token`: Bearer token for API authentication

#### Key Methods

```python
async def run() -> None
```
- Main scheduler loop (infinite until stop signal)
- Updates status to `RUNNING` when started
- Polls for ready tasks every `interval` seconds
- Handles stop signals and error conditions
- Includes exception handling for graceful error logging
- Passes `system_auth_token` to all API calls

```python
async def _trigger_task_ready_to_run() -> bool
```
- Executes one iteration of the cron job
- **Returns**: `True` if should stop, `False` to continue
- Queries API for tasks ready to run (with auth token)
- Executes multiple tasks in batch (with auth token)
- Updates heartbeat timestamp
- Detects and handles `STOP`/`ERROR` status signals

```python
async def _update_project_status(status: str, error_message: Optional[str] = None) -> None
```
- Updates project `cron_status` in metadata
- Optionally sets error message
- Updates heartbeat timestamp
- Communicates via API client (with system auth token)

```python
async def _handle_scheduler_error(error_message: str) -> None
```
- Gracefully handles scheduler errors
- Attempts to update status to `ERROR`
- Logs any update failures without re-raising

### Schema Definitions

**Location**: `schema.py`

#### CronStatus Enum
```python
class CronStatus(str, Enum):
    STARTED = "STARTED"      # Initial state, executor starting up
    RUNNING = "RUNNING"      # Active and polling tasks
    STOP = "STOP"            # Stop signal sent (transition state)
    STOPPED = "STOPPED"      # Executor has stopped
    ERROR = "ERROR"          # Fatal error occurred
```

#### CronAction Enum
```python
class CronAction(str, Enum):
    START = "START"          # Request to start cron
    STOP = "STOP"            # Request to stop cron
```

#### CronManageRequest
```python
{
    "project_laui": "ObjectId as string",
    "action": "START" | "STOP"
}
```

#### CronManageResponse
```python
{
    "success": true,
    "message": "Descriptive message",
    "project_laui": "project_laui_string",
    "action": "START" | "STOP"
}
```

---

## Status Lifecycle

### State Machine

```
                    ┌─────────────────┐
                    │    STOPPED      │
                    │   (Terminal)    │
                    └────────▲────────┘
                             │
                             │
                    ┌────────┴──────────┐
                    │                   │
              ┌─────┴──────┐      ┌─────┴──────┐
              │ (start)    │      │ (timeout)  │
              └────────────┘      └────────────┘
                    │                   │
                    ▼                   ▼
            ┌──────────────┐      ┌──────────────┐
            │   STARTED    │◄────┤    ERROR     │
            │ (starting)   │      │ (fatal error)│
            └──────┬───────┘      └──────────────┘
                   │                   ▲
                   │ (run begins)      │
                   │                   │
                   ▼                   │
            ┌──────────────┐           │
            │  RUNNING     ├───────────┘
            │ (active loop)│ (error during execution)
            └──────┬───────┘
                   │
                   │ (stop requested)
                   ▼
            ┌──────────────┐
            │    STOP      │
            │ (transitional)│
            └──────┬───────┘
                   │
                   │ (executor sees STOP)
                   ▼
            ┌──────────────┐
            │  STOPPED     │
            │ (terminal)   │
            └──────────────┘
```

### Heartbeat & Liveness Detection

**Purpose**: Detect stale or crashed scheduler processes

**Mechanism**:
- Heartbeat updated on each execution loop iteration
- Stored as ISO 8601 UTC timestamp in `folder_metadata.latest_heartbeat`
- Checked by `_cron_exists()` before allowing new start requests

**Timeout Logic**:
- Calculate max allowed delay: `interval * 4`
- If `now() - latest_heartbeat > max_delay`, consider cron dead
- Default: 5s × 4 = 20 seconds before timeout (configurable per project)

**Example**:
```
Project A: interval=5s
- Heartbeat should update every 5 seconds
- Allowed max delay: 20 seconds
- If no heartbeat for 21+ seconds, scheduler considered dead

Project B: interval=10s (custom config)
- Heartbeat should update every 10 seconds
- Allowed max delay: 40 seconds
- If no heartbeat for 41+ seconds, scheduler considered dead
```

---

## Configuration

### System Configuration File

Configuration loaded from system config (via `load_system_config()`), typically in `config.yaml` or environment-based.

#### Global Parameters

```yaml
# Default interval for all projects (seconds)
project_scheduler_interval: 5  # Default: 5 seconds

# Per-project override (optional)
TODO : for future
```

### Project Metadata Structure

Stored in `Item.folder_metadata` (MongoDB document):

```json
{
  "cron_status": "RUNNING",
  "latest_heartbeat": "2024-01-15T10:35:45.123456+00:00",
  "start_date": "2024-01-15T10:30:00.000000+00:00",
  "stop_date": null,
  "error": null
}
```

#### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `cron_status` | CronStatus enum | Current execution state |
| `latest_heartbeat` | ISO 8601 string | Last execution timestamp (UTC) |
| `start_date` | ISO 8601 string | When cron was started |
| `stop_date` | ISO 8601 string \| null | When cron was stopped |
| `error` | string \| null | Error message if status=ERROR |

### Environment Requirements

**Celery Configuration**:
- Active Celery workers listening for `run_cron` tasks
- Message broker (Redis/RabbitMQ) configured
- Task result backend configured

**API Client**:
- `APIClient` instance with valid credentials
- Endpoints: `get_project()`, `get_tasks_ready_to_run()`, `run_multiple_tasks()`, `update_project_metadata()`

**Database**:
- MongoDB connection with read/write access to project documents

---

## API Reference

### Start Cron Job

**Endpoint**: `POST /cron/manage`

**Request**:
```json
{
  "project_laui": "507f1f77bcf86cd799439011",
  "action": "START"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Cron started successfully for project",
  "project_laui": "507f1f77bcf86cd799439011",
  "action": "START"
}
```

**Error Responses**:
- `409 Conflict` - Cron already running for this project
  ```json
  {
    "detail": "Cron is already running for this project",
    "project_laui": "507f1f77bcf86cd799439011"
  }
  ```

- `404 Not Found` - Project doesn't exist
  ```json
  {
    "detail": "Project not found"
  }
  ```

- `400 Bad Request` - Item is not a project
  ```json
  {
    "detail": "Item is not a project",
    "item_type": "folder.document"
  }
  ```

**Example cURL**:
```bash
curl -X POST http://localhost:8000/cron/manage \
  -H "Content-Type: application/json" \
  -d '{
    "project_laui": "507f1f77bcf86cd799439011",
    "action": "START"
  }'
```

### Stop Cron Job

**Endpoint**: `POST /cron/manage`

**Request**:
```json
{
  "project_laui": "507f1f77bcf86cd799439011",
  "action": "STOP"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Cron stopped successfully for project",
  "project_laui": "507f1f77bcf86cd799439011",
  "action": "STOP"
}
```

**Error Responses**:
- `404 Not Found` - Cron not running for this project
  ```json
  {
    "detail": "Cron is not running for this project",
    "project_laui": "507f1f77bcf86cd799439011"
  }
  ```

**Example cURL**:
```bash
curl -X POST http://localhost:8000/cron/manage \
  -H "Content-Type: application/json" \
  -d '{
    "project_laui": "507f1f77bcf86cd799439011",
    "action": "STOP"
  }'
```

### Check Cron Status

**Implementation**: Not exposed via direct endpoint, but can be queried by:
1. Reading project metadata from catalog service
2. Checking `folder_metadata.cron_status` field

**Status Values**:
- `STARTED` - Starting up, may not be executing yet
- `RUNNING` - Active and polling for tasks
- `STOP` - Stop signal received, executor shutting down
- `STOPPED` - Fully stopped (terminal state)
- `ERROR` - Fatal error occurred (check `error` field)

---

## Usage Guide

### Starting a Cron Scheduler

**Prerequisites**:
- Project must exist with `item_type` = `"folder.project"`
- Celery workers must be running
- No cron already running for the project

**Steps**:

1. **Via API**:
   ```bash
   curl -X POST http://localhost:8000/cron/manage \
     -H "Content-Type: application/json" \
     -d '{
       "project_laui": "507f1f77bcf86cd799439011",
       "action": "START"
     }'
   ```

2. **Via Python Code**:
   ```python
   from src.core.cron.cron_manager import CronManager
   from pydantic_mongo import PydanticObjectId

   cron_manager = request.app.state.cron_manager
   project_laui = PydanticObjectId("507f1f77bcf86cd799439011")

   try:
       success = await cron_manager.start_cron(project_laui)
       print(f"Cron started: {success}")
   except ConflictError as e:
       print(f"Cron already running: {e}")
   except NotFoundError as e:
       print(f"Project not found: {e}")
   except InvalidArgumentError as e:
       print(f"Invalid project type: {e}")
   ```

**What Happens**:
1. Validates project exists and is a folder.project
2. Initializes metadata with `STARTED` status and current timestamp
3. Submits async task to Celery (`CronExecutor.run()`)
4. Returns immediately (executor runs in background)

### Stopping a Cron Scheduler

**Steps**:

1. **Via API**:
   ```bash
   curl -X POST http://localhost:8000/cron/manage \
     -H "Content-Type: application/json" \
     -d '{
       "project_laui": "507f1f77bcf86cd799439011",
       "action": "STOP"
     }'
   ```

2. **Via Python Code**:
   ```python
   cron_manager = request.app.state.cron_manager
   project_laui = PydanticObjectId("507f1f77bcf86cd799439011")

   try:
       success = await cron_manager.stop_cron(project_laui)
       print(f"Cron stop requested: {success}")
   except NotFoundError as e:
       print(f"Cron not running: {e}")
   ```

**What Happens**:
1. Validates cron is running (`_cron_exists()`)
2. Sets status to `STOP` (signaling executor)
3. Updates `stop_date` with current timestamp
4. Executor detects `STOP` on next iteration and transitions to `STOPPED`

**Note**: Stop is graceful—executor finishes current iteration before exiting.

### Configuring Intervals

**Global Configuration** (config.yaml):
```yaml
project_scheduler_interval: 5  # Default for all projects
```

**Per-Project Override** (config.yaml):
```yaml
project_scheduler_interval: 5        # Default

```

**How It Works**:
- On startup, `CronManager._get_cron_interval_for_project()` looks for `{project_name}_cron_interval`
- Falls back to `project_scheduler_interval` if not found
- Interval used when creating executor: `CeleryOrchestrator.run_cron(project_laui, interval)`

### Celery Task Entry Point

**Location**: `registry/crons.py`

The Celery task that serves as the entry point for cron execution.

**Task:**

#### `run_cron(project_laui: str, interval: int, system_auth_token: str) -> None`

Entry point for cron job execution.

**Configuration:**
- Name: `least_action.run_cron`
- Queue: Configured cron queue
- Bind: True (receives self reference for task introspection)

**Parameters:**
- `project_laui`: LAUI of the project to run cron jobs for
- `interval`: Interval in seconds for cron execution
- `system_auth_token`: System authentication token for API calls (Bearer token)

**Behavior:**
- Generates a unique session ID for the cron run via `generate_session_id()`
- Sets session context for structured logging (`project_laui`, `interval`, `cron_run=True`)
- Creates new event loop for async execution
- Initializes `CronExecutor` with project LAUI, interval, shared API client, and system auth token
- Executes cron jobs via `CronExecutor.run()`
- Comprehensive error logging with full tracebacks
- Ensures loop cleanup and context cleanup in finally block
- Propagates exceptions to mark Celery task as FAILED

**Use Case:**
- Periodic execution of scheduled tasks within a project
- Triggered by Celery Beat or manual scheduling
- Maintains session context for traceability across all cron-triggered tasks
- Passes authentication token explicitly to all API operations

---

## Monitoring & Heartbeat

### Health Checks

**Manual Status Check**:

```python
async def check_cron_health(project_laui):
    """Check if cron is actively running"""
    try:
        is_alive = await cron_manager._cron_exists(project_laui)
        return {"healthy": is_alive, "project_laui": str(project_laui)}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
```

**What's Checked**:
1. Status is `STARTED` or `RUNNING`
2. Heartbeat timestamp is recent (within 3× interval)
3. Project exists and is not deleted

### Heartbeat Monitoring

**Heartbeat Updates**:
- Updated by `CronExecutor._update_project_metadata()` on each loop iteration
- Stored as ISO 8601 UTC timestamp
- Never null during active execution

**Monitoring Approach**:

```python
from datetime import datetime, timezone, timedelta

def get_heartbeat_status(project):
    """Analyze heartbeat health"""
    metadata = project.get("folder_metadata", {})
    heartbeat_str = metadata.get("latest_heartbeat")

    if not heartbeat_str:
        return "No heartbeat recorded"

    heartbeat = datetime.fromisoformat(heartbeat_str)
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=timezone.utc)

    age_seconds = (datetime.now(timezone.utc) - heartbeat).total_seconds()

    return {
        "last_heartbeat": heartbeat_str,
        "age_seconds": age_seconds,
        "status": "alive" if age_seconds < 15 else "stale"
    }
```

### Logs to Monitor

**Log Format**:
```
[2024-01-15 10:35:45] module=cron | class=CronExecutor | method=run | level=INFO
"[project_id] Heartbeat updated successfully at 2024-01-15T10:35:45..."
```

**Key Log Patterns**:

| Pattern | Meaning | Action |
|---------|---------|--------|
| `Starting scheduler for project_id` | Executor started | Monitor for progress |
| `Status updated to RUNNING` | Ready for tasks | System operational |
| `Heartbeat updated successfully` | Normal iteration | Expected in logs |
| `Found N tasks ready to run` | Tasks discovered | Execution in progress |
| `Error in job iteration` | Non-fatal error | Check details, continues |
| `Scheduler cancelled` | Graceful shutdown | Expected during stop |
| `Heartbeat is stale` | Scheduler dead | Requires investigation |

---

## Error Handling

### Error Types & Recovery

#### ConflictError (409)
**Cause**: Attempting to start cron when already running

**Handling**:
```python
try:
    await cron_manager.start_cron(project_laui)
except ConflictError as e:
    # Option 1: Wait and retry
    await asyncio.sleep(5)
    await cron_manager.start_cron(project_laui)

    # Option 2: Stop then start
    await cron_manager.stop_cron(project_laui)
    await cron_manager.start_cron(project_laui)

    # Option 3: Fail gracefully
    logger.error(f"Cron already running: {e.detail}")
    return {"error": "Cron already active"}
```

#### NotFoundError (404)
**Cause**: Project doesn't exist or cron not running

**Handling**:
```python
try:
    await cron_manager.stop_cron(project_laui)
except NotFoundError as e:
    # Project or cron was already deleted/stopped
    logger.info(f"Cron not running: {e.detail}")
    return {"status": "already_stopped"}
```

#### InvalidArgumentError (400)
**Cause**: Item is not a project

**Handling**:
```python
try:
    await cron_manager.start_cron(item_laui)
except InvalidArgumentError as e:
    logger.error(f"Invalid item type: {e.detail}")
    return {"error": f"Item must be a project, got {e.detail['item_type']}"}
```

### Executor Error Handling

**Non-Fatal Errors** (Continues execution):
- Individual task execution failures
- API timeouts during task querying
- Metadata update delays

**Fatal Errors** (Stops execution):
- Project not found (invalid laui)
- Database connection failure
- Unrecoverable API errors

**Error Logging**:
```python
# In CronExecutor.run()
except Exception as job_error:
    error_msg = f"Error in job iteration: {str(job_error)}"
    log_error("cron", "CronExecutor", "run",
             f"[{self.project_id}] {error_msg}\n{traceback.format_exc()}")
    # Continues running despite error
```

### Status = ERROR

**When Set**: Fatal unrecoverable error in executor

**Handling**:
1. `_handle_scheduler_error()` called
2. Status updated to `ERROR` with error message
3. Executor terminates gracefully
4. Project requires manual intervention (need to fix issue, then restart)

**Recovery**:
```python
# 1. Investigate error
project = await catalog_service.find_item(project_laui)
error_msg = project.folder_metadata.get("error")
print(f"Error details: {error_msg}")

# 2. Fix underlying issue (e.g., restore database connection)

# 3. Restart cron
await cron_manager.start_cron(project_laui)
```

---

## Troubleshooting

### Cron Won't Start

**Symptom**: `ConflictError: Cron is already running`

**Diagnosis**:
```python
is_running = await cron_manager._cron_exists(project_laui)
print(f"Is actually running: {is_running}")

project = await catalog_service.find_item(project_laui)
status = project.folder_metadata.get("cron_status")
heartbeat = project.folder_metadata.get("latest_heartbeat")
print(f"Status: {status}, Heartbeat: {heartbeat}")
```

**Solutions**:

1. **If status is STOPPED but error says running**:
   - Metadata might be stale
   - Force update status:
   ```python
   folder_metadata = project.folder_metadata or {}
   folder_metadata["cron_status"] = "STOPPED"
   await catalog_service.create_item(updated_project)
   ```

2. **If heartbeat is stale (> 15s old)**:
   - Executor may have crashed
   - Safe to stop and restart:
   ```python
   # This will bypass the _cron_exists() check since status is old
   # But verify no processes are actually running first
   await cron_manager.stop_cron(project_laui)
   await cron_manager.start_cron(project_laui)
   ```

3. **If Celery workers not running**:
   - Check Celery service:
   ```bash
   celery -A src.core.celery.tasks inspect active
   ```
   - Start workers if needed:
   ```bash
   celery -A src.core.celery.tasks worker -l info
   ```

### Cron Stops Without Request

**Symptom**: Status transitions to STOPPED/ERROR unexpectedly

**Diagnosis**:
```bash
# Check logs for error messages
grep -E "ERROR|Scheduler error" logs/application.log

# Check project metadata
db.items.findOne({laui: ObjectId("...")}).folder_metadata
```

**Common Causes**:

1. **Executor crashed** (status = ERROR):
   - Check error message in metadata
   - Review logs for exception
   - Likely causes: API failures, database issues, bad configuration

2. **Heartbeat timeout**:
   - Worker process hung or paused
   - Check if worker is responsive:
   ```bash
   celery -A src.core.celery.tasks inspect active
   ```

3. **Manager crash**:
   - If API restarted, internal state lost
   - Metadata may still show RUNNING
   - Safe to restart cron as shown above

### High CPU/Memory Usage

**Symptom**: Executor consuming excessive resources

**Diagnosis**:
1. Check task execution frequency:
   ```python
   config_interval = cron_manager._get_cron_interval_for_project(project_name)
   print(f"Interval: {config_interval}s")
   ```

2. Check task volume:
   ```python
   tasks_ready = await api_client.get_tasks_ready_to_run(project_laui)
   print(f"Tasks to execute: {len(tasks_ready)}")
   ```

**Solutions**:

1. **Increase interval** (less frequent polling):
   ```yaml
   # config.yaml
   my_project_cron_interval: 30  # Instead of 5
   ```

2. **Implement task batching limit**:
   - Modify `CronExecutor._trigger_task_ready_to_run()`
   - Add max tasks limit to prevent bulk execution

3. **Check for task bottleneck**:
   - If tasks take longer than interval, they queue up
   - Monitor actual execution time vs interval

### Tasks Not Executing

**Symptom**: Cron running but no tasks execute

**Diagnosis**:
```python
# Check status
project = await catalog_service.find_item(project_laui)
status = project.folder_metadata.get("cron_status")
print(f"Status: {status}")

# Check if tasks exist
tasks_ready = await api_client.get_tasks_ready_to_run(project_laui)
print(f"Tasks ready: {len(tasks_ready)}")

# Check logs
grep "trigger_task_ready_to_run" logs/worker.log | tail -20
```

**Common Causes**:

1. **No tasks in "ready" state**:
   - Check task scheduling
   - Verify task prerequisites are met

2. **API client errors**:
   - Check if `run_multiple_tasks()` is failing
   - Verify API credentials
   - Check network connectivity

3. **Silent failures**:
   - Non-fatal errors continue execution without throwing
   - Check executor logs for detailed error messages

### Metadata Update Failures

**Symptom**: Heartbeat not updating, status stuck

**Diagnosis**:
```bash
# Check database transaction logs
tail -f logs/mongo.log | grep -E "transactionAbort|writeConflict"

# Verify catalog service is responsive
curl http://localhost:8000/health
```

**Solutions**:

1. **Transient update failure**:
   - Executor will retry on next iteration
   - No action needed unless persistent

2. **Database lock**:
   - Kill blocking operations:
   ```javascript
   db.currentOp() // Find blocking operations
   db.killOp(opid) // Kill specific operation
   ```

3. **Connection pool exhausted**:
   - Check database connection limit
   - Scale API instances or increase pool size

---

## Development Notes

### TODO Items in Code

**cron_manager.py:133**
```python
# TODO: Add cron_started_by parameter to track who started the cron
```
Consider adding user/service identifier to metadata for audit trail.

**cron_manager.py:210**
```python
# TODO: Add stopped_by parameter to track who stopped the cron
```
Consider adding user/service identifier when stopping.

**cron_manager.py:239**
```python
# TODO: Handle retry for update fail due to transaction
```
Implement exponential backoff for metadata update failures.

### Testing

**Unit Test Template**:
```python
import pytest
from src.core.cron.cron_manager import CronManager

@pytest.mark.asyncio
async def test_start_cron_success(cron_manager, project_laui):
    """Test successful cron startup"""
    result = await cron_manager.start_cron(project_laui)
    assert result is True

    # Verify metadata updated
    project = await cron_manager.catalog_service.find_item(project_laui)
    assert project.folder_metadata["cron_status"] == "STARTED"

@pytest.mark.asyncio
async def test_start_cron_already_running(cron_manager, project_laui):
    """Test conflict when cron already running"""
    await cron_manager.start_cron(project_laui)

    with pytest.raises(ConflictError):
        await cron_manager.start_cron(project_laui)
```

### Integration with Other Systems

**CatalogService**: Used for project metadata storage
- Method: `find_item(item_laui)`, `create_item(item)`
- Must support `folder_metadata` field updates

**CeleryOrchestrator**: Task submission to async queue
- Method: `run_cron(project_laui, interval) -> task_id`
- Must support background task execution

**APIClient** (in executor): Direct HTTP communication
- Methods: `get_project()`, `get_tasks_ready_to_run()`, `run_multiple_tasks()`, `update_project_metadata()`
- Async HTTP client required

---

## Performance Characteristics

### Scalability

| Aspect | Capacity | Notes |
|--------|----------|-------|
| Projects per instance | 100-1000 | Limited by worker count |
| Tasks per iteration | Configurable | Default: no limit (batch all ready) |
| Heartbeat interval | 2-60s | Configurable per project |
| Concurrent projects | 100+ | Scales with Celery workers |

### Resource Usage

**Per Active Cron** (idle):
- Memory: ~50-100MB (executor + API client)
- CPU: Minimal (sleeping on interval)
- Database connections: 1
- Network: Minimal (heartbeat update only)

**Per Active Cron** (executing tasks):
- Memory: +100-500MB (task execution)
- CPU: 50-100% (during execution)
- Database connections: 2-3 (metadata updates + task queries)
- Network: High (API calls to task service)

---

## See Also

- [CatalogService Documentation](../catalog/README.md)
- [CeleryOrchestrator Documentation](../task/README.md)
- [API Endpoints Documentation](../../routes/README.md)

