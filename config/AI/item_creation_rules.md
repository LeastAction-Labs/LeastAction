# Item Creation Rules

These rules are enforced by the platform. Items that violate them will be rejected at creation time.

---

## Naming Conventions

| Item type | Rule | Regex | Example |
|-----------|------|-------|---------|
| operator | Must end with `.operator` | `^[a-zA-Z0-9_\-]+\.operator$` | `AWSAthenaExecuteSQL.operator` |
| action | Must end with `.action` | `^[a-zA-Z0-9_\-]+\.action$` | `SendSlackMessage.action` |
| usecase | Must end with `.usecase` | `^[a-zA-Z0-9_\-]+\.usecase$` | `etl-pipeline.usecase` |
| folder, config, payload, skill | Alphanumeric, hyphens, underscores, spaces | `^[a-zA-Z0-9_\-\s]+$` | `My Folder` |
| task | Free text (no suffix required) | — | `daily_sync` |

---

## Unique Constraints (duplicate = update in-place)

| Item type | Unique on |
|-----------|-----------|
| operator, action, folder, config, payload, connection | `parent_laui` + `name` |
| task | `name` + `project_laui` + `account_laui` + `partition` |
| usecase | `name` + `publisher` |

---

## Required Fields by Item Type

### Operator (`item_type: "operator"` or `"operator.<subtype>"`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | string | yes | Must end with `.operator` |
| parent_laui | string | yes | Parent folder LAUI |
| codeblock | dict | yes | `{"main.py": "<python code>"}` — main.py is mandatory |
| bashblock | dict | yes | `{"main.sh": "pip install <packages>"}` |
| description | string | no | Max 1000 chars |
| connection | dict | no | Sample connection JSON for docs |
| payload | any | no | Sample payload for docs |
| tags | list[str] | no | Max 20 tags |

### Action (`item_type: "action"`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | string | yes | Must end with `.action` |
| parent_laui | string | yes | Parent folder LAUI |
| codeblock | dict | yes | `{"main.py": "<python code>"}` — main.py is mandatory |
| bashblock | dict | yes | `{"main.sh": "pip install <packages>"}` |
| action_variables | dict | no | Default values for run() kwargs |
| description | string | no | Max 1000 chars |
| connection | dict | no | Sample connection JSON |
| tags | list[str] | no | Max 20 tags |

### Task (`item_type: "task"`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | string | yes | Free text |
| parent_laui | string | yes | Workflow folder LAUI |
| project_laui | string | yes | Project LAUI |
| account_laui | string | yes | Account LAUI |
| operator_laui | string | yes | Operator to execute |
| connection_laui | string | yes | Connection with credentials |
| frequency | string | no | Cron expression or `"ADHOC"` (default) |
| payload | string/dict | no | Business logic: SQL, code, JSON config |
| state | string | no | Default `"scheduled"` |
| partition | string | no | Default `"ALL"` |
| start_date | datetime | no | Execution window start |
| end_date | datetime | no | Execution window end |
| priority | int | no | Default 1 |

### Folder (`item_type: "folder.workflow"`)

| Field | Type | Required |
|-------|------|----------|
| name | string | yes |
| parent_laui | string | yes |

---

## Operator Code Rules

The `main.py` in the codeblock must define exactly **4 synchronous functions**. The platform calls them in order: `initialize` -> `run` -> `check_completion` -> `finish`.

### Function Signatures

```python
from src.common.logger.logger import log_info, log_error

def initialize(least_action_task_object):
    """Create client/connection. Called once per execution."""
    connection = least_action_task_object.get('connection', {})
    # Build and return your client
    return client  # MUST return non-None

def run(least_action_task_object, client):
    """Execute the main operation."""
    payload = least_action_task_object.get('payload')
    # Do work...
    return {
        "status": "success",          # REQUIRED: "success", "pending", "running", "error", "failed"
        "execution_type": "sync",     # REQUIRED: "sync" or "async"
        "result": {...}               # operation output
    }

def check_completion(least_action_task_object, client, run_details):
    """Check if async operation completed. For sync ops, return success immediately."""
    if run_details.get('execution_type') == 'sync':
        return {"status": "success", "message": "Synchronous operation completed"}
    # Poll for async completion...
    return {
        "status": "success",   # REQUIRED: "success", "pending", or "failed"
        "message": "...",
        "output": {...}
    }

def finish(least_action_task_object, client, completion_details, run_details):
    """Cleanup resources. Always called, even after errors."""
    # Close connections, release resources
    return None  # MUST return None
```

### least_action_task_object Fields

Access via `.get()`: `laui`, `connection` (dict with credentials), `payload` (business logic), `config` (dict), `frequency`, `logical_date`, `last_run_session_id`, `actions`, `operator_laui`, `connection_laui`.

### Logging Convention

```python
# type is always "task" for operators
log_info("task", "initialize", "creating_client", f"Connecting to region: {region}")
log_error("task", "run", "query_failed", f"Error: {str(e)}")
```

Parameters: `(type, function_name, step_name, description)`. Step names are lowercase descriptive: `creating_client`, `executing_query`, `checking_status`.

---

## Action Code Rules

The `main.py` must define exactly **1 synchronous function**: `run`.

### Function Signature

```python
from src.common.logger.logger import log_info, log_error

def run(least_action_action_object, webhook_url, message, channel=None):
    """Execute the action. Extra kwargs come from action_variables."""
    log_info("action", "run", "start", "Starting action")

    connection = least_action_action_object.get('connection', {})
    # Do work using connection credentials and kwargs...

    log_info("action", "run", "complete", "Action finished")
    return True  # MUST return True (success) or False (failure)
```

### least_action_action_object Fields

Access via `.get()`: `laui`, `session_id`, `connection` (dict with credentials), `action_variables` (dict), `task` (full task dict or `{}`), `connection_laui`.

### Logging Convention

```python
# type is always "action" for actions
log_info("action", "run", "sending_request", f"Sending to {url}")
log_error("action", "run", "request_failed", f"Error: {str(e)}")
```

---

## Validation Rules (Automatic — Code Rejected if Violated)

These checks run automatically on every operator and action codeblock at creation time.

### Forbidden Imports
`subprocess`, `ctypes`, `pickle`, `threading`, `multiprocessing`, `marshal`, `pty`, `tty`, `signal`

### Forbidden Calls
`eval()`, `exec()`, `__import__()`, `os.system()`, `os.popen()`, `os.spawn*()`, `pickle.loads()`, `marshal.loads()`, `ctypes.*()`, `sys.modules` manipulation, `os.environ` access, `socket.*` usage

### Structural Rules
- **No `async def`** — all functions must be synchronous
- **No dunder access** — `__init__`, `__call__`, `__dict__` etc. are forbidden
- **No relative imports** — use `from helpers import foo`, not `from .helpers import foo`
- **No file writes to ANY absolute path** — `open()` with write mode (`w`, `a`, `x`, `+`) to ANY path starting with `/` or `~` is **forbidden**. This includes `/tmp`, `/var`, `/home`, `/etc`, `/usr` — ALL absolute paths. Only relative paths are allowed for file writes.
- **Logger restriction** — only `from src.common.logger.logger import log_info, log_error` (never `import logging` or `logging.getLogger()`)
- **bashblock main file must be named `main.sh`** — not `setup.sh`, not `install.sh`, must be exactly `main.sh`

**WRONG — will be rejected:**
```python
open("/tmp/output.txt", "w")      # absolute path /tmp
open("/home/user/data.csv", "w")  # absolute path /home
open("~/file.txt", "w")           # home path ~
```
**CORRECT:**
```python
open("output.txt", "w")           # relative path — allowed
```

### Action Design Rule: Use action_variables for runtime values
If an action needs file paths, URLs, messages, channel names, or any user-configurable value — put them in `action_variables`, not hardcoded in code. The user fills these in when invoking the action.

**WRONG:**
```python
def run(least_action_action_object):
    requests.post("https://hooks.slack.com/hardcoded-url", json={"text": "hello"})
```
**CORRECT:**
```python
def run(least_action_action_object, webhook_url, message):
    requests.post(webhook_url, json={"text": message})
    return True

# action_variables: {"webhook_url": "", "message": ""}
```

### Secret Leak Prevention
**NEVER** print or log `least_action_task_object` or `least_action_action_object` directly — they contain connection secrets. Only access specific fields:
```python
# WRONG — will be rejected
log_info("task", "run", "debug", f"Object: {least_action_task_object}")
print(least_action_task_object)

# CORRECT
task_laui = least_action_task_object.get('laui')
log_info("task", "run", "debug", f"Task: {task_laui}")
```

### Multi-File Codeblocks
If you split code across files, all files must be in the codeblock dict and use absolute local imports:
```python
# codeblock: {"main.py": "...", "helpers.py": "..."}
# In main.py:
from helpers import my_function  # absolute local import
```

---

## Complete Examples

### Example: Create an Operator

```
create_catalog_item(
    name="PostgresqlExecuteSQL.operator",
    item_type="operator.python",
    parent_laui="<folder_laui>",
    extra_fields={
        "codeblock": {
            "main.py": "import psycopg2\nfrom src.common.logger.logger import log_info, log_error\n\ndef initialize(least_action_task_object):\n    conn = least_action_task_object.get('connection', {})\n    log_info('task', 'initialize', 'connecting', f\"Host: {conn.get('host')}\")\n    client = psycopg2.connect(\n        host=conn.get('host'), port=conn.get('port', 5432),\n        database=conn.get('database'), user=conn.get('user'),\n        password=conn.get('password')\n    )\n    log_info('task', 'initialize', 'connected', 'PostgreSQL connection established')\n    return client\n\ndef run(least_action_task_object, client):\n    sql = least_action_task_object.get('payload', '')\n    log_info('task', 'run', 'executing_query', 'Running SQL payload')\n    cursor = client.cursor()\n    cursor.execute(sql)\n    client.commit()\n    rows = cursor.rowcount\n    log_info('task', 'run', 'query_complete', f'Affected rows: {rows}')\n    return {'status': 'success', 'execution_type': 'sync', 'result': {'rows_affected': rows}}\n\ndef check_completion(least_action_task_object, client, run_details):\n    return {'status': 'success', 'message': 'Synchronous operation completed'}\n\ndef finish(least_action_task_object, client, completion_details, run_details):\n    if client:\n        client.close()\n        log_info('task', 'finish', 'cleanup', 'Connection closed')\n    return None"
        },
        "bashblock": {"main.sh": "pip install psycopg2-binary"},
        "description": "Executes SQL queries on PostgreSQL databases"
    }
)
```

### Example: Create an Action

```
create_catalog_item(
    name="SendSlackMessage.action",
    item_type="action",
    parent_laui="<folder_laui>",
    extra_fields={
        "codeblock": {
            "main.py": "import requests\nimport json\nfrom src.common.logger.logger import log_info, log_error\n\ndef run(least_action_action_object, webhook_url, message, channel=None):\n    log_info('action', 'run', 'start', 'Sending Slack message')\n    payload = {'text': message}\n    if channel:\n        payload['channel'] = channel\n    try:\n        resp = requests.post(webhook_url, data=json.dumps(payload),\n                             headers={'Content-Type': 'application/json'}, timeout=30)\n        if resp.status_code == 200:\n            log_info('action', 'run', 'success', 'Message sent')\n            return True\n        log_error('action', 'run', 'failed', f'Status: {resp.status_code}')\n        return False\n    except Exception as e:\n        log_error('action', 'run', 'error', f'Error: {str(e)}')\n        return False"
        },
        "bashblock": {"main.sh": "pip install requests"},
        "action_variables": {"webhook_url": "", "message": "", "channel": "#general"}
    }
)
```

### Example: Create a Task

```
create_catalog_item(
    name="daily_sales_sync",
    item_type="task",
    parent_laui="<workflow_laui>",
    extra_fields={
        "project_laui": "<project_laui>",
        "account_laui": "<account_laui>",
        "operator_laui": "<operator_laui>",
        "connection_laui": "<connection_laui>",
        "frequency": "0 2 * * *",
        "payload": "SELECT * FROM sales WHERE date = '{{ds}}'",
        "state": "scheduled"
    }
)
```

### Example: Create a Folder

```
create_catalog_item(
    name="AWS Analytics",
    item_type="folder.workflow",
    parent_laui="<parent_folder_laui>"
)
```
