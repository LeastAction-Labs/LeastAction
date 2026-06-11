# Action API

**Prefix**: `/api/v1/action`
**Authentication**: Required (Bearer token)

---

## POST `/api/v1/action/run`

Execute an action. Can either execute an existing action by LAUI or create and execute a new action.

**Access Control**: Inherits from catalog create/access patterns.

### Request Body

`BaseCreateItemRequest` with `extra="allow"`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_type` | string | Yes | Must be `"action"` |
| `item_laui` | ObjectId | Conditional | LAUI of existing action (if running existing) |
| `name` | string | Conditional | Required for new actions. Regex: `^[a-zA-Z0-9_\-]+\.action$` |
| `parent_laui` | ObjectId | Conditional | Required for new actions |
| `project_laui` | ObjectId | Conditional | Required for new actions |
| `account_laui` | ObjectId | Conditional | Required for new actions |
| `codeblock` | object | Conditional | Required for new actions. Python code to execute |
| `bashblock` | object | Conditional | Required for new actions. Bash setup code |
| `connection_laui` | ObjectId | No | Connection to use during execution |
| `action_variables` | object | No | Variables passed to the action |

### Variation 1: Execute Existing Action

```json
{
  "item_type": "action",
  "item_laui": "507f1f77bcf86cd799439011",
  "connection_laui": "60d5ecb54b24a67d8c8b4567",
  "action_variables": {
    "target_table": "users",
    "batch_size": 1000,
    "dry_run": false
  }
}
```

### Variation 2: Create and Execute New Action

```json
{
  "item_type": "action",
  "name": "cleanup-temp-files.action",
  "parent_laui": "60d5ecb54b24a67d8c8b1234",
  "project_laui": "60d5ecb54b24a67d8c8b5678",
  "account_laui": "60d5ecb54b24a67d8c8b9012",
  "codeblock": {
    "language": "python",
    "content": "import os\n\ndef run(context):\n    target_dir = context.get('action_variables', {}).get('target_dir', '/tmp')\n    count = 0\n    for f in os.listdir(target_dir):\n        if f.endswith('.tmp'):\n            os.remove(os.path.join(target_dir, f))\n            count += 1\n    return {'deleted_files': count}"
  },
  "bashblock": {
    "content": "pip install boto3"
  },
  "connection_laui": "60d5ecb54b24a67d8c8b4567",
  "action_variables": {
    "target_dir": "/tmp/staging"
  }
}
```

### Variation 3: Action Without Connection

```json
{
  "item_type": "action",
  "item_laui": "507f1f77bcf86cd799439011",
  "action_variables": {
    "message": "Hello from action"
  }
}
```

### Variation 4: Action With Empty Variables

```json
{
  "item_type": "action",
  "item_laui": "507f1f77bcf86cd799439011",
  "connection_laui": "60d5ecb54b24a67d8c8b4567"
}
```

### Success Response

**Status**: 200 OK

```json
{
  "result": {
    "deleted_files": 42,
    "status": "completed"
  }
}
```

The response shape depends on what the action's `run()` function returns.

### Error Responses

**422 Unprocessable Entity** — Wrong item type
```json
{"detail": "Only Action can be executed"}
```

**422 Unprocessable Entity** — item_type not action
```json
{"detail": "Request item_type must be 'action'"}
```

**422 Unprocessable Entity** — Schema validation failure
```json
{
  "detail": {
    "summary": "errors found in action.json",
    "validation_context": {
      "name": "regex pattern ^[a-zA-Z0-9_\\-]+\\.action$ not matched"
    }
  }
}
```

**404 Not Found** — Action not found
```json
{"detail": "Item not found"}
```

**500 Internal Server Error** — Execution failure
```json
{"detail": "Internal server error: Action execution timed out"}
```

---

## Action Types in Task Context

Actions can also be attached to tasks and executed at different stages of the task lifecycle. See [Task API](/path?laui=getting-started-advanced-API_management-03-task&itemtype=doc.file&itemname=03%20Task) for details.

| Action Type | When Executed | Blocking |
|-------------|--------------|----------|
| `create_actions` | During task creation, before the item is persisted | Yes — task is not created if action fails |
| `pre_actions` | After validation, before dispatch | Yes — task is not dispatched if action fails |
| `running_actions` | During execution, triggered by SLA | No — runs alongside the main task |
| `post_actions` | After task completes (success or failure) | No — runs asynchronously |

### Action Item Schema (in task context)

```json
{
  "laui": "507f1f77bcf86cd799439011",
  "name": "notify-slack.action",
  "session_id": "sess_abc123",
  "connection_laui": "60d5ecb54b24a67d8c8b4567",
  "connection": {},
  "action_variables": {"channel": "#alerts"},
  "user_laui": "60d5ecb54b24a67d8c8b9012",
  "sla": 5,
  "timeout": 300,
  "action_type": "pre_actions"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `laui` | ObjectId | Action item LAUI |
| `name` | string | Action name |
| `session_id` | string | Session identifier |
| `connection_laui` | ObjectId | Connection to use |
| `connection` | object | Connection content (fetched at runtime) |
| `action_variables` | object | Variables passed to the action |
| `user_laui` | ObjectId | User who triggered the action |
| `sla` | int | SLA threshold in minutes (for running_actions) |
| `timeout` | int | Maximum execution time in seconds |
| `action_type` | string | One of: `create_actions`, `pre_actions`, `running_actions`, `post_actions` |
