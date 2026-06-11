# Log Navigator — Fetching & Debugging Logs

Use this skill whenever you need to locate, read, or query logs to debug a failure, trace a session, or inspect task/action execution.

---

## Log Storage Layout

All logs live under `{logs_dir}` (from `Config().logs_dir`). Every log entry is a JSON line.

### Category → Directory mapping

| Category | Path pattern | Filename |
|---|---|---|
| **API** | `verbose=NON_TASK/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category=API/` | `{operation}.log` |
| **CELERY** | `verbose=NON_TASK/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category=CELERY/` | `{operation}.log` |
| **API_TRACEBACK** | `verbose=NON_TASK/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category=API_TRACEBACK/` | `{operation}.log` |
| **TASK** | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category=TASK/` | `{task_name}.log` |
| **PRE_ACTIONS** | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category=PRE_ACTIONS/` | `{action_name}.log` |
| **POST_ACTIONS** | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category=POST_ACTIONS/` | `{action_name}.log` |
| **RUNNING_ACTIONS** | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category=RUNNING_ACTIONS/` | `{action_name}.log` |
| **CREATE_ACTIONS** | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category=CREATE_ACTIONS/` | `{action_name}.log` |
| **ACTION** (resolved to action_type) | `verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category={ACTION_TYPE}/` | `{action_name}.log` |
| **TASK_HISTORY** | `category=TASK_HISTORY/task_laui={laui}/yyyy={Y}/mm={M}/dd={D}/` | `{ts}__{sid}__{task_name}.log` (task) or `latest_{action_type}_{task_name}_{action_name}.log` (action) |
| **CRON** | `category=CRON/project={project_laui}/yyyy={Y}/mm={M}/dd={D}/` | `cron.log` |
| **PERFORMANCE** | `category=PERFORMANCE/yyyy={Y}/mm={M}/dd={D}/` | `{operation}.log` |
| **OTHER** | `verbose=OTHER/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category={cat}/event={op}/` | `{timestamp}_{step}.log` |

**Dual-write rule:** When category=`ACTION` and action_type=`PRE_ACTIONS`, the logger writes to **both**:
1. `TASK_HISTORY` — `latest_pre_actions_{task_name}_{action_name}.log` (overwritten each run)
2. `PRE_ACTIONS` — the normal rolling action log

---

## How to Find Logs

### By session_id
Two glob patterns cover all session logs:
```
{logs_dir}/**/session_id={session_id}/**/*.log        # API, CELERY, TASK, actions
{logs_dir}/**/*__{session_id}__*.log                   # TASK_HISTORY task snapshots
```
Use the API: `GET /api/v1/logs/session/{session_id}` → streams a list of matching files.
Then read individual files: `GET /api/v1/logs/file/{relative_path}`.

### By task (task_laui)
Task-related logs live under two roots:
- **Rolling logs:** `verbose=TASK/yyyy=*/mm=*/dd=*/task_laui={task_laui}/session_id=*/category=*/`
- **History snapshot:** `category=TASK_HISTORY/task_laui={task_laui}/yyyy=*/mm=*/dd=*/`

Browse: `GET /api/v1/logs/listItems/verbose=TASK` then drill into the date/task_laui folders.
Or query: `POST /api/v1/logs/query` with SQL (see DuckDB section below).

### By action (action_name)
Actions log to the category matching their `action_type` (e.g. `PRE_ACTIONS`, `POST_ACTIONS`):
```
verbose=TASK/yyyy={Y}/mm={M}/dd={D}/task_laui={laui}/session_id={sid}/category={ACTION_TYPE}/{action_name}.log
```

### Celery worker logs
```
verbose=NON_TASK/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category=CELERY/{operation}.log
```
Browse: `GET /api/v1/logs/listItems/verbose=NON_TASK`

### API request tracebacks
```
verbose=NON_TASK/yyyy={Y}/mm={M}/dd={D}/session_id={sid}/category=API_TRACEBACK/{operation}.log
```

### Cron job logs
```
category=CRON/project={project_laui}/yyyy={Y}/mm={M}/dd={D}/cron.log
```
Browse: `GET /api/v1/logs/listItems/category=CRON`

### Performance logs
```
category=PERFORMANCE/yyyy={Y}/mm={M}/dd={D}/{operation}.log
```
Browse: `GET /api/v1/logs/listItems/category=PERFORMANCE`

---

## API Endpoints

All endpoints are under the router mounted at `/api/v1/logs` (verify prefix in main app).

| Method | Path | Description |
|---|---|---|
| `GET` | `/listItems/{folder_path}` | SSE — lists files/dirs under a logs subfolder. Use `.` for root. |
| `GET` | `/file/{file_path}` | SSE — streams file content. Add `?reverse=true&skip=0&limit=200` for tail paging. |
| `GET` | `/session/{session_id}` | SSE — lists all log files matching the session. |
| `GET` | `/session/{session_id}/content` | JSON — parses and returns log entries. Supports `?level=error&category=API&page=1&per_page=50`. |
| `POST` | `/query` | JSON — runs a DuckDB SELECT over all logs. Body: `{"sql": "SELECT ..."}`. |

---

## DuckDB Query Interface

`POST /api/v1/logs/query` creates an in-memory DuckDB view over every `.log` file:
```sql
CREATE VIEW logs AS SELECT * FROM read_json_auto('{logs_dir}/**/*.log', union_by_name=True, ignore_errors=True)
```
Only `SELECT` and `WITH` queries are allowed (no semicolons).

**Useful query patterns:**

```sql
-- All errors for a session
SELECT timestamp, level, category, operation, step, message
FROM logs
WHERE session_id = 'abc123' AND level = 'error'
ORDER BY timestamp

-- All logs for a specific task
SELECT * FROM logs
WHERE task_laui = 'task-laui-value'
ORDER BY timestamp

-- Recent errors across all sessions (today)
SELECT session_id, category, operation, message, timestamp
FROM logs
WHERE level = 'error'
  AND timestamp >= '2025-01-01'
ORDER BY timestamp DESC
LIMIT 100

-- Action execution trace for a task
SELECT action_name, category, step, message, timestamp
FROM logs
WHERE task_laui = 'task-laui-value'
  AND category IN ('PRE_ACTIONS', 'RUNNING_ACTIONS', 'POST_ACTIONS')
ORDER BY timestamp

-- Celery failures
SELECT * FROM logs
WHERE category = 'CELERY' AND level IN ('error', 'critical')
ORDER BY timestamp DESC
LIMIT 50
```

Log entry fields (from logger.py `_write_to_file`):
- `timestamp` — ISO8601
- `level` — debug / info / warning / error / critical
- `step` — caller-supplied step name
- `session_id`
- `message`
- `category` — when present
- `operation` — when present
- `task_laui` — when present
- `task_name` — when present
- `logical_date` — when present
- `project_laui` — when present
- `action_name` — when present

---

## Debug Workflow

1. **Have a session_id?** → `GET /session/{session_id}/content?level=error` to see all errors, then `GET /session/{session_id}` for the file list to find which component failed.

2. **Have a task_laui?** → Check `TASK_HISTORY` snapshot first (`latest_*` files show the last run). Then look at the rolling logs under `verbose=TASK/.../task_laui={laui}/`.

3. **Have an action that failed?** → Find its `action_type`, then look in `verbose=TASK/.../category={ACTION_TYPE}/{action_name}.log`.

4. **Celery worker crash?** → `GET /listItems/verbose=NON_TASK` → drill into date → session → `category=CELERY`.

5. **API 500 error?** → Check `category=API_TRACEBACK` logs for the session; they contain full Python tracebacks.

6. **Cross-session analysis?** → Use `POST /query` with DuckDB SQL for aggregations, time-range filtering, or multi-session comparisons.
