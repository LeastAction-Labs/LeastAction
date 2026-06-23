# **LeastAction Monitor - Feature Guide**

## **Overview**

LeastAction provides four complementary monitoring surfaces — each answering a different question at a different level of detail:

| Surface | Where | Purpose |
|---------|-------|---------|
| **Task Monitoring** | Task → Logs tab in UI | Track execution history, sessions, and status for a specific task |
| **Task Logs (Files)** | `logs/` directory on disk | Raw JSON log files for programmatic analysis and DuckDB queries |
| **Log Folder Types** | Log directory structure | Understand which folder contains what, and how to navigate to the right log |
| **Service Monitoring** | Monitoring panel in UI | Browse all log folders, view API/service/performance logs, explore the full log tree |

---

## **1. Task Monitoring**

Task monitoring is the primary day-to-day view for tracking how a specific task is running. Access it by opening any task in the UI and clicking the **Logs** tab.

### **Layout**

The Task Logs view has two panels:

**Left sidebar — Timeline:**
- **Date range picker**: Select the start and end date for the history you want to see (defaults to today)
- **VIEW TASK HISTORY button**: Returns to the execution log list from a selected session
- **Recent Sessions section**: Shows a date card for each day that had executions. Each day card contains:
  - Colored blocks — one per execution session. Color indicates status:
    - Green = success
    - Red = failed / error
    - Purple = cancelled
    - Gray = pending / other
  - A summary line showing the count of successful and failed sessions for that day
  - Click any block to drill into that session

**Right panel — Execution Log / Session Detail:**
- Shows the **Execution Log** (history list) by default
- Switches to **Session Detail** when a session block is clicked

---

### **Execution Log (History List)**

The execution log shows all runs for the task in the selected date range.

**Filtering:**
- Status filter chips at the top: All / Success / Error / Cancelled — click to filter the list

**Each run card shows:**
- **Session ID** (first 5 characters)
- **Status badge** (success, error, failed, running, cancelled, pending)
- **Start Time** — when the execution actually started
- **Duration** — formatted as ms, seconds, or minutes
- **Frequency** — the cron expression or ADHOC
- **Retry #** — which retry attempt this was (0 = first attempt)
- **Error message** — shown inline for failed/error runs (extracted from task output)

**Grouping:**
- Runs that share the same `logical_date` (the scheduled slot they belong to, e.g. a retry of the same scheduled execution) are grouped together with a "N runs · same schedule slot" label.

**Latest Actions section:**
- Collapsed by default, appears above the run list when action logs exist
- Shows the most recent log for each action type (preAction, postAction, etc.) — one `latest_*` file per action
- Click an action to expand and view its full log inline
- Useful for quickly checking what the last preAction or postAction did, without finding a specific session

---

### **Session Detail View**

Clicking a session block or run card opens the Session Detail for that specific execution.

**Header:**
- Session ID (first 8 characters)
- Execution date
- Refresh button — reloads all category logs for this session
- Download button — downloads all session logs as a single `session_{id}.log` text file

**Category tabs:**
Each session's logs are split by category. Tabs appear for each category that has log files:

| Tab | What it shows |
|-----|--------------|
| **TASK** | The main task execution log — operator output, payload results, status changes |
| **PRE_ACTIONS** | Logs from all preActions that ran before this execution |
| **POST_ACTIONS** | Logs from all postActions that ran after completion |
| **RUNNING_ACTIONS** | Logs from SLA and interval actions that ran during execution |
| **CREATE_ACTIONS** | Logs from createActions that ran at task creation |
| **API** | API request/response logs for this session (has its own date range picker for multi-day API traces) |
| **CELERY** | Celery worker logs for this session |

**Log viewer features (per category):**
- **Search** — full-text search across all log lines
- **Level filter tabs** — All / Info / Warning / Error / Debug
- **Paginated loading** — latest 400 lines shown first; scroll to top to load older lines
- **Jump to latest** button — appears when scrolled up, returns to the newest log line
- **Download** — save the individual log file
- Multiple files in a category are shown as collapsible sections

---

## **2. Task Logs (Files)**

All logs are written to the `logs/` directory configured in `config/system.yml` (`logs.directory`). They are **newline-delimited JSON** (NDJSON) — one JSON object per line — stored in a **Hive-partitioned** folder structure for fast reads with DuckDB or any analytics tool.

### **Log Entry Schema**

Every log line is a JSON object with these fields:

| Field | Always Present | Description |
|-------|----------------|-------------|
| `timestamp` | Yes | ISO timestamp of the log entry |
| `level` | Yes | Log level: `info`, `warning`, `error`, `critical`, `debug` |
| `step` | Yes | Step name within the operation (e.g., `start`, `complete`, `error`) |
| `session_id` | Yes | Unique ID for this execution session — groups all logs for one run |
| `message` | Yes | Human-readable message or nested JSON payload |
| `category` | No | Log category: `TASK`, `API`, `PRE_ACTIONS`, `CRON`, etc. |
| `operation` | No | The specific operation being logged (e.g., `execute`, `validate`) |
| `task_laui` | No | The task's unique identifier |
| `task_name` | No | Task name string |
| `logical_date` | No | The logical execution date for this run (scheduled slot) |
| `project_laui` | No | Project identifier |
| `action_name` | No | Name of the action if this log is from an action |

**Example log entry:**
```json
{
  "timestamp": "2026-03-06T14:30:00.123",
  "level": "info",
  "step": "complete",
  "session_id": "a3f9b2c1d4e5f678",
  "message": "{\"status\": \"success\", \"duration_seconds\": 42.5, \"output\": {\"rows_processed\": 1500}}",
  "category": "TASK",
  "operation": "execute",
  "task_laui": "6997d6f277dcb18b47e47968",
  "task_name": "daily_sales_load",
  "logical_date": "2026-03-06T00:00:00",
  "project_laui": "6997d6f177dcb18b47e47966"
}
```

> **Note**: The `message` field sometimes contains a nested JSON string. The UI automatically parses and displays it. When reading raw files, parse `message` as JSON if it starts with `{`.

### **Querying Logs with DuckDB**

Because files use Hive partitioning (`yyyy=`, `mm=`, `dd=`, `category=`, etc.), DuckDB can filter at the filesystem level — reading only the relevant partitions instead of scanning all logs.

**Example: All errors for a specific task on a date:**
```sql
SELECT timestamp, step, message
FROM read_ndjson_auto(
  'logs/verbose=TASK/yyyy=2026/mm=03/dd=06/task_laui=6997d6f277dcb18b47e47968/**/*.log',
  ignore_errors=true
)
WHERE level = 'error'
ORDER BY timestamp;
```

**Example: Task history summary across a week:**
```sql
SELECT task_name, COUNT(*) as runs,
       SUM(CASE WHEN level='error' THEN 1 ELSE 0 END) as errors
FROM read_ndjson_auto(
  'logs/category=TASK_HISTORY/task_laui=*/yyyy=2026/mm=03/**/*.log',
  ignore_errors=true
)
GROUP BY task_name;
```

**Example: API logs for a session:**
```sql
SELECT timestamp, operation, message
FROM read_ndjson_auto(
  'logs/verbose=NON_TASK/yyyy=2026/mm=03/dd=06/session_id=a3f9b2c1d4e5f678/category=API/*.log',
  ignore_errors=true
)
ORDER BY timestamp;
```

---

## **3. Log Folder Types**

All logs land under the `logs/` root. Understanding the folder structure helps you navigate directly to the right log — either in the file system or via the Logs Explorer in the UI.

### **Folder Overview**

```
logs/
├── verbose=TASK/             ← Full task execution logs (detailed, per session)
├── verbose=NON_TASK/         ← API and service logs (per session)
├── verbose=OTHER/            ← Miscellaneous / catch-all
├── category=TASK_HISTORY/    ← Task history snapshots (powers the UI history view)
├── category=CRON/            ← Cron scheduler logs (per project)
└── category=PERFORMANCE/     ← Service performance metrics
```

---

### **`verbose=TASK/` — Detailed Task Execution Logs**

Contains the full log output for every task execution, organized so you can drill down by date, task, and session.

**Path structure:**
```
verbose=TASK/
└── yyyy={year}/mm={month}/dd={day}/
    └── task_laui={task_laui}/
        └── session_id={session_id}/
            └── category={TASK|PRE_ACTIONS|POST_ACTIONS|RUNNING_ACTIONS|ACTION|CREATE_ACTIONS}/
                └── {task_name}.log          ← for TASK category
                └── {action_name}.log        ← for action categories
```

**Categories inside:**

| Category folder | Contents |
|-----------------|----------|
| `category=TASK` | Main task execution log — operator output, timing, status |
| `category=PRE_ACTIONS` | Logs from all preActions, one file per action |
| `category=POST_ACTIONS` | Logs from all postActions, one file per action |
| `category=RUNNING_ACTIONS` | SLA and interval action logs |
| `category=CREATE_ACTIONS` | createAction logs |

**When to use:** Finding the detailed log for a specific task execution. If you know the task_laui, date, and session_id, navigate directly here.

---

### **`verbose=NON_TASK/` — Service & API Logs**

Contains non-task logs grouped by session: API requests, Celery worker events, and tracebacks.

**Path structure:**
```
verbose=NON_TASK/
└── yyyy={year}/mm={month}/dd={day}/
    └── session_id={session_id}/
        └── category={API|CELERY|API_TRACEBACK}/
            └── {operation}.log
```

**Categories inside:**

| Category folder | Contents |
|-----------------|----------|
| `category=API` | API request/response logs for the session |
| `category=CELERY` | Celery worker lifecycle events |
| `category=API_TRACEBACK` | Full Python tracebacks for API errors |

**When to use:** Debugging API errors, understanding why a Celery task failed at the worker level, or investigating tracebacks.

---

### **`category=TASK_HISTORY/` — Task History Snapshots**

This is what powers the task Logs tab in the UI. It stores a compact history record per task execution and the latest action snapshots.

**Path structure:**
```
category=TASK_HISTORY/
└── task_laui={task_laui}/
    └── yyyy={year}/mm={month}/dd={day}/
        ├── {timestamp}__{session_id}__{task_name}.log    ← one per execution
        └── latest_{action_type}_{task_name}_{action_name}.log  ← overwritten each run
```

**Files:**
- **`{timestamp}__{session_id}__{task_name}.log`** — execution summary written when the task completes. Contains `status`, `start_time`, `duration_seconds`, `frequency`, `logical_date`, `retry_number`, `output`. One file per session.
- **`latest_{action_type}_{task_name}_{action_name}.log`** — rolling log for each action. Cleared at the start of each run and written fresh. Always reflects the most recent execution of that action. Shown in the "Latest Actions" section in the UI.

**When to use:** Querying task run history in bulk (DuckDB), checking the history of a specific task over time.

---

### **`category=CRON/` — Scheduler Logs**

Logs from the cron scheduler that checks for tasks ready to run.

**Path structure:**
```
category=CRON/
└── project={project_laui}/
    └── yyyy={year}/mm={month}/dd={day}/
        └── cron.log
```

**When to use:** Investigating why a scheduled task didn't trigger, or understanding scheduling cadence for a project.

---

### **`category=PERFORMANCE/` — Performance Metrics**

Service-level performance logs for monitoring system health.

**Path structure:**
```
category=PERFORMANCE/
└── yyyy={year}/mm={month}/dd={day}/
    └── {operation}.log
```

**When to use:** Service health monitoring, performance dashboard, identifying slow operations.

---

### **`verbose=OTHER/` — Miscellaneous**

Catch-all for log categories that don't fit the above buckets.

**Path structure:**
```
verbose=OTHER/
└── yyyy={year}/mm={month}/dd={day}/
    └── session_id={session_id}/
        └── category={category}/
            └── event={operation}/
                └── {timestamp}_{step}.log
```

---

## **4. Service Monitoring (Logs Explorer)**

The Logs Explorer provides a full tree-view browser of all log folders in the UI. It is used for:
- Browsing logs that aren't tied to a specific task (API errors, service health, cron)
- Navigating the raw log structure visually
- Viewing the performance dashboard

### **Navigating the Log Tree**

The explorer shows a collapsible tree matching the folder structure in `logs/`:
- Click a folder to expand it and load its children
- Folders load lazily — children are fetched on first expand
- Click any `.log` file to open it in a popup viewer

**Tree is sorted newest-first** within each folder — the most recent date folder appears at the top.

### **Log File Popup Viewer**

Clicking a log file opens a popup with formatted content:
- Each JSON log entry is rendered as a structured card:
  - **Timestamp** and **level badge** (color-coded: green=INFO, orange=WARNING, red=ERROR)
  - **Logger name** (category + operation + session)
  - **Key-value pairs** from the JSON object, displayed with blue keys and readable values
- Non-JSON lines are displayed as plain monospace text

### **Monitoring Paths for Common Use Cases**

| Use case | Navigate to |
|----------|-------------|
| Why did a task fail? | `verbose=TASK/yyyy=.../mm=.../dd=.../task_laui=.../session_id=...` |
| What did preAction log? | `verbose=TASK/.../session_id=.../category=PRE_ACTIONS/` |
| API error investigation | `verbose=NON_TASK/.../session_id=.../category=API/` |
| Python traceback | `verbose=NON_TASK/.../session_id=.../category=API_TRACEBACK/` |
| Why didn't my task schedule? | `category=CRON/project=.../yyyy=.../` |
| Service performance | `category=PERFORMANCE/yyyy=.../mm=.../dd=.../` |
| Task run history (bulk) | `category=TASK_HISTORY/task_laui=.../yyyy=.../` |

---

## **Log Levels**

All logs use standard levels:

| Level | Color in UI | Meaning |
|-------|------------|---------|
| `info` | Green | Normal operation, status updates, expected flow |
| `warning` | Orange | Non-fatal issues, config problems, skipped items |
| `error` | Red | Failures, exceptions, items that could not be processed |
| `critical` | Red (bright) | System-level failures requiring immediate attention |
| `debug` | Gray | Verbose detail for development and troubleshooting |

---

## **Troubleshooting**

### **Task Logs Tab Shows No Sessions**

- Change the date range — logs exist only for dates when the task actually ran
- For adhoc tasks: select the exact date the task was triggered
- Verify the task has been executed at least once (scheduled tasks show no logs until first run)

### **Session Shows Empty Category Tabs**

- The category only appears if logs exist for it — if preAction didn't run, no PRE_ACTIONS tab
- Try refreshing the session (refresh button in the session header)
- Check that the task's session_id matches what you expect (verify in the task's execution record)

### **Latest Actions Section Not Showing**

- Latest action files (`latest_*`) are created only when an action runs as part of task execution
- If the task ran but has no preActions configured, the section won't appear

### **Log Files Missing from Disk**

- Verify `logs.directory` in `config/system.yml` points to the correct path
- Check disk space — logs are written to disk and can fill up on high-volume deployments
- The log directory is created automatically on first write; check permissions if logs are absent

### **DuckDB Query Returns No Results**

- Double-check the partition values in your path — `mm=` uses zero-padded month (`03` not `3`)
- Use `ignore_errors=true` in `read_ndjson_auto` to skip malformed lines
- Verify the `logs/` root path is correct (check `system.yml → logs.directory`)
