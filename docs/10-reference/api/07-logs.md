# Logs API

**Prefix**: `/api/v1/logs`
**Authentication**: Not required (public route)

All endpoints return **Server-Sent Events (SSE)** streams with `Content-Type: text/event-stream`.

---

## GET `/api/v1/logs/listItems/{folder_path}`

List the contents of a log folder.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_path` | string (path) | Folder path to list (supports nested paths with `/`) |

### Request Example

```
GET /api/v1/logs/listItems/2024/01/15
```

### SSE Stream

```
event: status
data: {"state": "processing"}

event: data
data: {"directory": "2024/01/15", "items": [{"name": "task_507f1f77.log", "type": "file", "size": 15234, "modified": "2024-01-15T10:30:00Z", "path": "2024/01/15/task_507f1f77.log"}, {"name": "actions", "type": "directory", "size": 0, "modified": "2024-01-15T09:00:00Z", "path": "2024/01/15/actions"}], "total_count": 2}

event: done
data: {"state": "complete"}
```

### Error SSE

```
event: error
data: {"message": "Directory not found: 2024/01/32"}
```

---

## GET `/api/v1/logs/file/{file_path}`

Stream the contents of a log file.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string (path) | Path to the log file |

### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `reverse` | bool | `false` | — | Enable reverse/paged reading mode |
| `skip` | int | `0` | `>= 0` | Lines to skip (only used when `reverse=true`) |
| `limit` | int | `200` | `1-5000` | Max lines to return (only used when `reverse=true`) |

### Variation 1: Stream Full File (Normal Mode)

```
GET /api/v1/logs/file/2024/01/15/task_507f1f77.log
```

**SSE Stream:**

```
event: status
data: {"state": "processing"}

event: metadata
data: {"name": "task_507f1f77.log", "path": "2024/01/15/task_507f1f77.log", "size": 15234, "modified": "2024-01-15T10:30:00Z"}

event: chunk
data: {"content": "2024-01-15 10:00:00 INFO Starting task execution...\n2024-01-15 10:00:01 INFO Operator initialized\n..."}

event: chunk
data: {"content": "2024-01-15 10:05:00 INFO Task completed successfully\n"}

event: done
data: {"state": "complete", "total_chunks": 2}
```

### Variation 2: Paged/Reverse Mode

Read the latest lines from a file with pagination.

```
GET /api/v1/logs/file/2024/01/15/task_507f1f77.log?reverse=true&skip=0&limit=50
```

**SSE Stream:**

```
event: status
data: {"state": "processing"}

event: metadata
data: {"name": "task_507f1f77.log", "path": "2024/01/15/task_507f1f77.log", "size": 15234}

event: chunk
data: {"content": "2024-01-15 10:05:00 INFO Task completed successfully"}

event: chunk
data: {"content": "2024-01-15 10:04:59 INFO Writing output..."}

event: done
data: {"state": "complete", "total_chunks": 50}
```

### Variation 3: Paginate Through a Large File

```
GET /api/v1/logs/file/2024/01/15/task_507f1f77.log?reverse=true&skip=50&limit=50
```

### Error SSE

```
event: error
data: {"message": "File not found: 2024/01/15/missing.log"}
```

---

## GET `/api/v1/logs/session/{session_id}`

Stream all log entries for a specific execution session.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Session identifier (set during task/action execution) |

### Request Example

```
GET /api/v1/logs/session/sess_abc123def456
```

### SSE Stream

```
event: status
data: {"state": "processing"}

event: log
data: {"timestamp": "2024-01-15T10:00:00Z", "level": "INFO", "message": "Task execution started", "task_laui": "507f1f77bcf86cd799439011"}

event: log
data: {"timestamp": "2024-01-15T10:00:01Z", "level": "INFO", "message": "Operator initialized successfully"}

event: log
data: {"timestamp": "2024-01-15T10:05:00Z", "level": "INFO", "message": "Task completed", "status": "success", "duration_seconds": 300.5}

event: done
data: {"state": "complete", "total_count": 3}
```

### Error SSE

```
event: error
data: {"message": "Session not found: sess_invalid"}
```

---

## GET `/api/v1/logs/session/{session_id}/content`

Retrieve paginated, parsed JSON log entries for a session. Returns plain JSON (not SSE).

**Authentication**: Not required (public route)

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Session identifier |

### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `level` | string | `null` | — | Filter by log level (e.g. `"error"`, `"info"`) |
| `category` | string | `null` | — | Filter by log category (e.g. `"CELERY"`, `"API"`) |
| `page` | int | `1` | `>= 1` | Page number |
| `per_page` | int | `50` | `1–500` | Entries per page |

### Request Example

```
GET /api/v1/logs/session/sess_abc123?level=error&page=1&per_page=50
```

### Success Response

**Status**: 200 OK

```json
{
  "items": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "level": "error",
      "step": "dequeue_task",
      "session_id": "sess_abc123",
      "message": "Task not found"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "has_next": false
  }
}
```

---

## SSE Client Example

### JavaScript

```javascript
const eventSource = new EventSource('/api/v1/logs/session/sess_abc123');

eventSource.addEventListener('status', (event) => {
  console.log('Status:', JSON.parse(event.data));
});

eventSource.addEventListener('log', (event) => {
  const entry = JSON.parse(event.data);
  console.log(`[${entry.level}] ${entry.message}`);
});

eventSource.addEventListener('done', (event) => {
  const result = JSON.parse(event.data);
  console.log(`Stream complete. Total entries: ${result.total_count}`);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  console.error('Error:', JSON.parse(event.data));
  eventSource.close();
});
```

### Python

```python
import httpx

with httpx.stream("GET", "http://localhost:8000/api/v1/logs/session/sess_abc123") as response:
    for line in response.iter_lines():
        if line.startswith("event:"):
            event_type = line[7:]
        elif line.startswith("data:"):
            data = json.loads(line[6:])
            print(f"[{event_type}] {data}")
```

---

## POST `/api/v1/logs/query`

Run a SQL SELECT query across all application log files using an in-memory DuckDB instance.

**Authentication:** Not required (public route)  
**Content-Type:** `application/json`  
**Returns:** JSON (not SSE)

Log files are scanned via DuckDB `read_json_auto` and exposed as a single `logs` view. Each `category` maps to a different top-level directory with its own partition layout — passing `category` (and `date`) targets only that subtree, keeping queries fast. Schemas are merged by column name across files.

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `sql` | string | yes | A SELECT or WITH query. No semicolons. No DDL or DML. |
| `category` | string | **required** | Log source to scan. Must be one of: `"PERFORMANCE"`, `"CRON"`, `"TASK_HISTORY"`, `"CELERY"`, `"API"`, `"TASK"`. Omitting returns `{"error": "category is required..."}` immediately. |
| `date` | string | recommended | Limit scan to one day — `YYYY-MM-DD`. Without it, the full category directory is scanned. Always pass it when possible. |

> **`category` is required — the endpoint rejects requests without it.** Each category maps to a different directory layout; scanning across all of them on a large log store would always exceed the 30-second timeout.

### Response

```json
{
  "columns": ["timestamp", "level", "category", "session_id", "message"],
  "rows": [["2026-05-21T10:00:00Z", "error", "CRON", "abc123", "dequeue_task not found"]],
  "row_count": 1
}
```

On error (bad SQL, no log files, empty directory):
```json
{ "error": "<duckdb error message>" }
```

> **Empty deployment:** When no `.log` files exist yet, DuckDB cannot scan the directory and returns an error. This is expected — no data has been written yet.

### Log Schema

Columns are auto-detected from JSON fields across all log files. Common columns:

| Column | Categories | Description |
|---|---|---|
| `timestamp` | all | ISO 8601 string |
| `level` | all | `"info"`, `"warning"`, `"error"`, `"critical"` |
| `step` | all | Log step name (e.g. `"heartbeat_resources"`, `"validating_sql_command"`) |
| `session_id` | all | Execution session UUID |
| `message` | all | String or JSON string. PERFORMANCE logs encode `{"execution_time": <seconds>, "error": <string or null>}` |
| `category` | all | `"PERFORMANCE"`, `"CRON"`, `"TASK_HISTORY"`, `"CELERY"`, `"API"`, `"TASK"` |
| `operation` | PERFORMANCE | Function/API name |
| `task_laui` | TASK, TASK_HISTORY | Task LAUI |
| `task_name` | TASK, TASK_HISTORY | Task name |
| `logical_date` | TASK, TASK_HISTORY | Task logical date |
| `project_laui` | CRON | Scheduler project LAUI |

### MCP Tool

The MCP server exposes this endpoint as `query_logs(sql, category, date)`. Always pass `category` and/or `date` to target the scan. Use it for cross-session or cross-task log analysis. For task-specific logs, prefer `get_task_logs` (pre-indexed, faster).

### Query Reference

Each example shows the recommended `category` + `date` parameters alongside the SQL.

**All errors for a day:**
```
category="CRON", date="YYYY-MM-DD"
sql: SELECT timestamp, step, session_id, message FROM logs WHERE level IN ('error', 'critical') ORDER BY timestamp DESC LIMIT 50
```

**All logs for one session:**
```
category="CELERY", date="YYYY-MM-DD"
sql: SELECT timestamp, level, step, message FROM logs WHERE session_id = '<session_id>' ORDER BY timestamp
```

**API performance — call counts, avg and p95 duration, error count per function:**
```
category="PERFORMANCE", date="YYYY-MM-DD"
sql:
SELECT
  operation AS function_name,
  COUNT(*) AS total_calls,
  ROUND(AVG(TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)) * 1000, 2) AS avg_ms,
  ROUND(QUANTILE_CONT(TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE), 0.95) * 1000, 2) AS p95_ms,
  SUM(CASE WHEN json_extract_string(message, '$.error') IS NOT NULL THEN 1 ELSE 0 END) AS errors
FROM logs
GROUP BY operation ORDER BY total_calls DESC
```

**Slowest functions by max duration:**
```
category="PERFORMANCE", date="YYYY-MM-DD"
sql:
SELECT
  operation AS function_name,
  COUNT(*) AS calls,
  ROUND(MAX(TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)) * 1000, 2) AS max_ms,
  ROUND(AVG(TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)) * 1000, 2) AS avg_ms
FROM logs
GROUP BY operation ORDER BY max_ms DESC LIMIT 20
```

**Functions with highest error count:**
```
category="PERFORMANCE", date="YYYY-MM-DD"
sql:
SELECT
  operation AS function_name,
  COUNT(*) AS total_calls,
  SUM(CASE WHEN json_extract_string(message, '$.error') IS NOT NULL THEN 1 ELSE 0 END) AS errors,
  ROUND(SUM(CASE WHEN json_extract_string(message, '$.error') IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS error_rate_pct
FROM logs
GROUP BY operation HAVING errors > 0 ORDER BY errors DESC LIMIT 20
```

**CRON scheduler errors:**
```
category="CRON", date="YYYY-MM-DD"
sql: SELECT timestamp, level, step, session_id, message FROM logs WHERE level IN ('error', 'critical') ORDER BY timestamp DESC LIMIT 50
```

**CRON heartbeat — CPU and memory over time:**
```
category="CRON", date="YYYY-MM-DD"
sql:
SELECT
  timestamp,
  TRY_CAST(json_extract_string(message, '$.cpu_percent_system') AS DOUBLE) AS cpu_system_pct,
  TRY_CAST(json_extract_string(message, '$.memory_rss_mb') AS DOUBLE) AS memory_rss_mb
FROM logs WHERE step = 'heartbeat_resources'
ORDER BY timestamp DESC LIMIT 100
```
