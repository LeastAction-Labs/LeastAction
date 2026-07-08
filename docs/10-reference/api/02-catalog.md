# Catalog API

Base URL: `/api/v1/catalog`

All endpoints require authentication via a Bearer token in the `Authorization` header.

```
Authorization: Bearer <token>
```

---

## Table of Contents

1. [POST /catalog/create](#1-create-item)
2. [POST /catalog/create/link](#2-create-link)
3. [GET /catalog/get/tasks_ready_to_run/{project_laui}](#3-get-tasks-ready-to-run)
4. [GET /catalog/get](#4-get-items)
5. [GET /catalog/get/item_revisions](#5-get-item-revisions)
6. [POST /catalog/delete](#6-delete-item)
7. [POST /catalog/restore/{item_laui}](#7-restore-item)
8. [POST /catalog/search](#8-search)
9. [GET /catalog/item-types/supported-types](#9-get-supported-types)
10. [POST /catalog/bootstrap](#10-bootstrap-project)
11. [POST /catalog/validate](#11-validate-codeblock)

---

## 1. Create Item

Creates a new catalog item. The `item_type` field determines which schema (`config/schema/{item_type}.json`) is used to validate the remaining fields.

```
POST /api/v1/catalog/create
```

### Description

Accepts a JSON body with `item_type` as a required field plus any additional fields defined in that item type's schema. The request model uses `extra="allow"`, so all schema-defined fields are passed as top-level keys alongside `item_type`.

Every item type schema defines `unique_constraints` -- a set of fields that together must be unique. Attempting to create a duplicate results in a `409 Conflict`.

### Access Control

Access is validated internally within the catalog service's `create_item` method. The service checks permissions on the parent item and any referenced items during creation.

**Note**: This is the only catalog endpoint where access checks remain in the service layer rather than at the router level, ensuring atomic validation during item creation.

### Item Type Restrictions

**⚠️ Important**: The following item types **cannot** be created via this endpoint:
- `task`
- `action`

These item types have dedicated creation and execution endpoints:
- Use `POST /api/v1/task` to create and run tasks
- Use `POST /api/v1/action` to create and execute actions

**Rationale**: Tasks and actions require specialized validation, permission checks, and lifecycle management that are handled by their dedicated endpoints. This restriction prevents bypassing security checks and ensures proper workflow execution.

#### Error Response for Restricted Types

**422 Unprocessable Entity** — Attempted to create restricted item type
```json
{
  "message": "Invalid item type passed",
  "detail": "use /api/v1/task api to create task"
}
```

or

```json
{
  "message": "Invalid item type passed",
  "detail": "use /api/v1/action api to create action"
}
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_type` | string | Yes | The type of item to create. Must match a schema file in `config/schema/`. |
| `name` | string | Yes | Name of the item. Validation rules (regex, length) depend on `item_type`. |
| `parent_laui` | ObjectId | Conditional | Required if `is_root` is `false` or omitted. The LAUI of the parent item. |
| `is_root` | boolean | No | Set to `true` for root-level items. Cannot be combined with `parent_laui`. Default: `false`. |
| `access_patch` | object | No | Access control patch. Default adds the creating user as owner. |
| _...extra fields_ | varies | Depends on schema | Additional fields defined in the item type's schema. |

### Parent/Root Rules

- If `is_root` is `true`, then `parent_laui` must not be present.
- If `is_root` is `false` (or omitted), then `parent_laui` must be a valid ObjectId string.

### Item Type Hierarchy

The parent item type must allow the child item type according to `config/catalog.json`. Key mappings:

| Parent Type | Allowed Children |
|---|---|
| `folder.account` | `folder.project`, `folder.trash`, `folder.users` |
| `folder.project` | `folder.action`, `folder.asset`, `folder.workflow`, `folder.operator`, `folder.payload`, `folder.connection`, `folder.bootstrap`, `folder.config`, `folder.ai` |
| `folder.workflow` | `folder.workflow`, `task`, `config`, `connection`, `payload`, `operator`, `action` |
| `folder.operator` | `folder.operator`, `operator` |
| `folder.connection` | `folder.connection`, `connection` |
| `folder.payload` | `folder.payload`, `payload` |
| `folder.config` | `folder.config`, `config` |
| `folder.asset` | `folder.asset`, `folder.report`, `folder.table`, `html_report`, `table`, `config` |
| `folder.ai` | `folder.ai`, `folder.chat`, `folder.skill` |
| `folder.chat` | `folder.chat`, `chat` |
| `folder.skill` | `folder.skill`, `skill` |
| `folder.user` | `chat_history` |

### Examples

#### 1a. Create a project folder

```json
POST /api/v1/catalog/create

{
  "item_type": "folder.project",
  "name": "ETL Pipeline Project",
  "description": "Production ETL pipelines for analytics",
  "parent_laui": "507f1f77bcf86cd799439011",
  "folder_metadata": {}
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e01"
}
```

#### 1b. Create a workflow folder

```json
{
  "item_type": "folder.workflow",
  "name": "Daily Ingestion",
  "description": "Daily data ingestion workflow",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e01",
  "folder_metadata": {
    "state": "ACTIVE"
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e02"
}
```

#### 1c. Create an operator

The `name` field must match regex `^[a-zA-Z0-9_\-]+\.operator$`.

```json
{
  "item_type": "operator",
  "name": "s3-download.operator",
  "description": "Downloads files from S3 buckets",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e03",
  "codeblock": {
    "language": "python",
    "code": "import boto3\n\ndef execute(connection, payload, config):\n    s3 = boto3.client('s3', **connection)\n    s3.download_file(payload['bucket'], payload['key'], payload['dest'])\n    return {'status': 'downloaded'}"
  },
  "bashblock": {
    "language": "bash",
    "code": "pip install boto3"
  },
  "connection": {
    "aws_access_key_id": "",
    "aws_secret_access_key": "",
    "region_name": "us-east-1"
  },
  "payload": {
    "bucket": "my-bucket",
    "key": "data/file.csv",
    "dest": "/tmp/file.csv"
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e04"
}
```

#### 1d. Create an action

The `name` field must match regex `^[a-zA-Z0-9_\-]+\.action$`.

```json
{
  "item_type": "action",
  "name": "notify-slack.action",
  "description": "Sends a notification to a Slack channel",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "codeblock": {
    "language": "python",
    "code": "import requests\n\ndef execute(connection, action_variables):\n    requests.post(connection['webhook_url'], json={'text': action_variables['message']})"
  },
  "bashblock": {
    "language": "bash",
    "code": "pip install requests"
  },
  "project_laui": "60d5ec49f1b2c72b8c9a1e01",
  "account_laui": "507f1f77bcf86cd799439011"
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e05"
}
```

#### 1e. Create a connection

```json
{
  "item_type": "connection",
  "name": "postgresql",
  "description": "Connection to the bundled postgres-demo database",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e06",
  "content": {
    "host": "postgres-demo",
    "port": 5432,
    "database": "postgres_demo_db",
    "user": "postgres"
  },
  "max_parallelism": 5,
  "sort_dict": {}
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e07"
}
```

#### 1f. Create a payload

```json
{
  "item_type": "payload",
  "name": "ingestion-params",
  "description": "Parameters for the daily ingestion job",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "content": {
    "source_table": "raw_events",
    "target_table": "staged_events",
    "batch_size": 10000,
    "dedup_keys": ["event_id", "timestamp"]
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e08"
}
```

#### 1g. Create config items (all config_type values)

The `config_type` field must be one of: `system`, `task`, `UIaction`, `taskAction`, `connection`, `workflow`.

**System config:**

```json
{
  "item_type": "config",
  "name": "global-settings",
  "description": "System-wide configuration",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "system",
  "content": {
    "max_concurrent_tasks": 50,
    "default_timeout_seconds": 3600,
    "log_level": "INFO"
  }
}
```

**Task config:**

```json
{
  "item_type": "config",
  "name": "task-retry-policy",
  "description": "Default retry policy for tasks",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "task",
  "content": {
    "total_retries": 3,
    "retry_interval": 5,
    "backoff_factor": 2
  }
}
```

**UIaction config:**

```json
{
  "item_type": "config",
  "name": "dashboard-actions",
  "description": "UI action button configuration",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "UIaction",
  "content": {
    "buttons": [
      {"label": "Run All", "action": "run_all_tasks"},
      {"label": "Pause", "action": "pause_workflow"}
    ]
  }
}
```

**taskAction config:**

```json
{
  "item_type": "config",
  "name": "pre-run-checks",
  "description": "Actions to execute before task runs",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "taskAction",
  "content": {
    "pre_actions": ["validate_schema", "check_connection"],
    "post_actions": ["send_notification"]
  }
}
```

**Connection config:**

```json
{
  "item_type": "config",
  "name": "connection-pool-settings",
  "description": "Connection pool configuration",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "connection",
  "content": {
    "pool_size": 10,
    "max_overflow": 5,
    "pool_timeout": 30
  }
}
```

**Workflow config:**

```json
{
  "item_type": "config",
  "name": "workflow-defaults",
  "description": "Default settings for workflow execution",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e09",
  "config_type": "workflow",
  "content": {
    "max_active_runs": 1,
    "catchup": false,
    "default_priority": 1
  }
}
```

**Response** (same for all config types) `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0a"
}
```

#### 1h. Create a task (full example)

```json
{
  "item_type": "task",
  "name": "ingest-raw-events",
  "description": "Ingests raw events from source into staging",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "partition": "ANALYTICS",
  "project_laui": "60d5ec49f1b2c72b8c9a1e01",
  "account_laui": "507f1f77bcf86cd799439011",
  "operator_laui": "60d5ec49f1b2c72b8c9a1e04",
  "connection_laui": "60d5ec49f1b2c72b8c9a1e07",
  "start_date": "2026-03-01T00:00:00Z",
  "end_date": null,
  "logical_date": "2026-03-19T06:00:00Z",
  "frequency": "0 6 * * *",
  "state": "scheduled",
  "payload_laui": "60d5ec49f1b2c72b8c9a1e08",
  "payload": {
    "source_table": "raw_events",
    "target_table": "staged_events",
    "batch_size": 10000
  },
  "attached_config_lauis": ["60d5ec49f1b2c72b8c9a1e0a"],
  "config": {},
  "total_retries": 3,
  "retry_interval": 5,
  "priority": 2,
  "actions": {
    "create_actions": [],
    "pre_actions": ["60d5ec49f1b2c72b8c9a1e05"],
    "running_actions": [],
    "post_actions": []
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0b"
}
```

#### 1i. Create a table

```json
{
  "item_type": "table",
  "name": "raw_events",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e0c",
  "source_system": "REDSHIFT",
  "location_uri": "jdbc:redshift://cluster.abc123.us-east-1.redshift.amazonaws.com:5439/analytics",
  "status": "ACTIVE",
  "load_strategy": "INCREMENTAL",
  "row_count": 5842310,
  "quality_score": 98.7,
  "schema_definition": {
    "columns": [
      {"name": "event_id", "type": "VARCHAR(64)", "nullable": false},
      {"name": "event_type", "type": "VARCHAR(128)", "nullable": false},
      {"name": "timestamp", "type": "TIMESTAMP", "nullable": false},
      {"name": "payload", "type": "SUPER", "nullable": true}
    ]
  },
  "etl_watermarks": {
    "max_updated_at": "2026-03-18T23:59:59Z"
  },
  "lineage_metadata": {
    "upstream_sources": ["s3://data-lake/raw/events/"],
    "transformation_job_id": "60d5ec49f1b2c72b8c9a1e0b"
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0d"
}
```

#### 1j. Create an html_report

The `name` field must match regex `^[a-zA-Z0-9_\-]+\.action$`.

```json
{
  "item_type": "html_report",
  "name": "weekly-summary.action",
  "description": "Weekly pipeline execution summary",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e0e",
  "html": "<html><body><h1>Weekly Summary</h1><p>Total runs: 142</p><p>Success rate: 97.2%</p></body></html>"
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0f"
}
```

#### 1k. Create a skill

```json
{
  "item_type": "skill",
  "name": "SQL Generation",
  "description": "Generates optimized SQL queries from natural language descriptions",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e10",
  "content": "You are a SQL expert. When the user describes a data query, generate an optimized SQL statement. Always use CTEs for readability. Prefer window functions over subqueries where applicable."
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e11"
}
```

#### 1l. Create an chat_history

```json
{
  "item_type": "chat_history",
  "name": "Operator Gen Session - March 19",
  "description": "AI session that generated the S3 download operator",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e12",
  "created_item_type": "operator",
  "ai_provider": "anthropic",
  "connection_laui": "60d5ec49f1b2c72b8c9a1e13",
  "connection_name": "Claude API Key",
  "messages": [
    {"role": "user", "content": "Create an operator that downloads files from S3"},
    {"role": "assistant", "content": "Here is the operator code..."}
  ],
  "generated_content": {
    "codeblock": "import boto3\ndef execute(connection, payload, config): ..."
  }
}
```

**Response** `200 OK`

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e14"
}
```

### Error Responses

#### 422 Unprocessable Entity -- Schema validation failure

Returned when the request body fails validation against the item type's schema.

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["name"],
      "msg": "String should match pattern '^[a-zA-Z0-9_\\-]+\\.operator$'",
      "input": "invalid name!",
      "expected_format": {
        "name": "name",
        "datatype": "string",
        "required": true,
        "regex": "^[a-zA-Z0-9_\\-]+\\.operator$"
      }
    },
    {
      "parent_laui": {"name": "parent_laui", "required": false, "datatype": "ObjectId", "default": null},
      "is_root": {"name": "is_root", "required": false, "datatype": "boolean", "default": false},
      "rules": {
        "valid_requests": [
          {"is_root": true},
          {"is_root": false, "parent_laui": "valid objectid string"},
          {"parent_laui": "valid objectid string"}
        ],
        "info": [
          "If value passed for is_root is true then parent_laui cannot be present.",
          "If value passed for is_root is false or if you do not pass value to is_root then parent_laui must be present."
        ]
      }
    }
  ]
}
```

#### 422 Unprocessable Entity -- Invalid hierarchy

Returned when the `item_type` is not allowed under the given `parent_laui`.

```json
{
  "detail": {
    "message": "invalid item_type for the passed parent_laui",
    "item_type_passed": "task",
    "allowed_item_types": ["folder.operator", "operator"]
  }
}
```

#### 422 Unprocessable Entity -- Schema file errors

Returned when the schema file for the given `item_type` has validation issues.

```json
{
  "detail": {
    "summary": "errors found in unknown_type.json",
    "validation_context": { }
  }
}
```

#### 400 Bad Request -- Invalid argument

```json
{
  "detail": "Invalid argument: <description>"
}
```

#### 403 Forbidden -- Access denied

```json
{
  "detail": "Access denied"
}
```

#### 409 Conflict -- Unique constraint violation

Returned when an item with the same unique key combination already exists.

```json
{
  "detail": "Item already exists with the same unique key"
}
```

#### 503 Service Unavailable -- Write conflict

Returned when a MongoDB write conflict occurs (error code 112), typically due to concurrent transaction contention.

```json
{
  "detail": "write_conflict"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 2. Create Link

Creates a parent-child link between two existing catalog items.

```
POST /api/v1/catalog/create/link
```

### Description

Links establish relationships between items. A link records the parent item, child item, their respective types, and whether the parent is the "true parent" (used for containment hierarchy and access inheritance) or a soft reference.

### Access Control

| Check | Permission | Target |
|-------|-----------|--------|
| Parent | EDIT | `parent_laui` |
| Child | VIEW | `child_laui` |

Both checks must pass. If the caller lacks EDIT on the parent or VIEW on the child, the request is rejected with `403`.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_laui` | ObjectId | Yes | The LAUI of the parent item. |
| `child_laui` | ObjectId | Yes | The LAUI of the child item. |

### Example

```json
POST /api/v1/catalog/create/link

{
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "child_laui": "60d5ec49f1b2c72b8c9a1e0b"
}
```

### Success Response

`200 OK`

```json
{
  "link_laui": "60d5ec49f1b2c72b8c9a2a01"
}
```

### Error Responses

#### 403 Forbidden -- Insufficient permissions

```json
{
  "detail": "Access denied"
}
```

#### 404 Not Found -- Parent or child does not exist

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e02"
}
```

#### 422 Unprocessable Entity -- Validation error

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["parent_laui"],
      "msg": "value is not a valid ObjectId"
    }
  ]
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 3. Get Tasks Ready to Run

Returns all tasks under a project that are eligible for execution based on scheduling, state, and retry policies.

```
GET /api/v1/catalog/get/tasks_ready_to_run/{project_laui}
```

### 🔒 System-Only Endpoint

**Authentication**: Requires **both**:
1. Bearer token (user context)
2. `X-System-Auth-Token` header (system authentication)

**Why**: This endpoint is called by cron schedulers to discover tasks eligible for execution. The system token prevents external clients from querying scheduled tasks, which could reveal infrastructure details and execution patterns.

**External Access**: Attempting to call this endpoint without the system token results in a `401 Unauthorized` error.

### Description

Uses a MongoDB aggregation pipeline to find tasks that meet all of the following criteria:

- `item_type` is `task`
- `project_laui` matches the path parameter
- Not soft-deleted (`deleted_at` is `null`)
- `start_date` is before the current time
- `user_set_state` is not `cancel`
- Either `end_date` is null or `logical_date <= end_date`
- One of:
  - **Normal path:** state is `scheduled` or `success`, and `logical_date <= now`
  - **Retry path:** state is `error` or `timeout`, `total_retries > 0`, `retry_number < total_retries`, and `last_run_date + (retry_interval * 60000ms) <= now`
- The parent workflow's `folder_metadata.state` is not `PAUSE`

### Access Control

**Router-Level Authorization**: User must have **own** permission on the project before tasks are returned.

| Check | Permission | Target |
|-------|-----------|--------|
| Project | OWN | `project_laui` |

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_laui` | ObjectId | Yes | The LAUI of the project containing the tasks. |

### Example

```
GET /api/v1/catalog/get/tasks_ready_to_run/60d5ec49f1b2c72b8c9a1e01
```

### Success Response

`200 OK`

Returns an array of task objects.

```json
[
  {
    "laui": "60d5ec49f1b2c72b8c9a1e0b",
    "item_type": "task",
    "name": "ingest-raw-events",
    "partition": "ANALYTICS",
    "project_laui": "60d5ec49f1b2c72b8c9a1e01",
    "account_laui": "507f1f77bcf86cd799439011",
    "operator_laui": "60d5ec49f1b2c72b8c9a1e04",
    "connection_laui": "60d5ec49f1b2c72b8c9a1e07",
    "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": null,
    "logical_date": "2026-03-19T06:00:00Z",
    "frequency": "0 6 * * *",
    "state": "scheduled",
    "iteration": 41,
    "total_retries": 3,
    "retry_interval": 5,
    "retry_number": 0,
    "priority": 2,
    "payload": {
      "source_table": "raw_events",
      "target_table": "staged_events",
      "batch_size": 10000
    },
    "config": {},
    "actions": {
      "create_actions": [],
      "pre_actions": ["60d5ec49f1b2c72b8c9a1e05"],
      "running_actions": [],
      "post_actions": []
    },
    "actions_status": {
      "pre_actions": [],
      "running_actions": [],
      "post_actions": []
    }
  },
  {
    "laui": "60d5ec49f1b2c72b8c9a1e15",
    "item_type": "task",
    "name": "transform-events",
    "partition": "ANALYTICS",
    "project_laui": "60d5ec49f1b2c72b8c9a1e01",
    "account_laui": "507f1f77bcf86cd799439011",
    "operator_laui": "60d5ec49f1b2c72b8c9a1e16",
    "connection_laui": "60d5ec49f1b2c72b8c9a1e07",
    "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": null,
    "logical_date": "2026-03-19T07:00:00Z",
    "frequency": "0 7 * * *",
    "state": "error",
    "iteration": 39,
    "total_retries": 2,
    "retry_interval": 10,
    "retry_number": 1,
    "priority": 1,
    "last_run_date": "2026-03-19T07:01:23Z",
    "payload": null,
    "config": {},
    "actions": {
      "create_actions": [],
      "pre_actions": [],
      "running_actions": [],
      "post_actions": []
    },
    "actions_status": {
      "pre_actions": [],
      "running_actions": [],
      "post_actions": []
    }
  }
]
```

### Error Responses

#### 403 Forbidden -- Not project owner

```json
{
  "detail": "Access denied"
}
```

#### 404 Not Found -- Project does not exist

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e01"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 4. Get Items

Retrieves catalog items by LAUI, root status, or hierarchy traversal with pagination.

```
GET /api/v1/catalog/get
```

### Description

A flexible endpoint for fetching items. Supports looking up a single item by its LAUI, fetching root-level items, traversing parent-child hierarchies, and filtering by item type -- all with pagination.

### Access Control

| Scenario | Permission | Target |
|----------|-----------|--------|
| `is_root=true` | Skipped | (Returns items the user has access to) |
| Only `item_laui` passed (no `item_type`, `parent_or_child`, or `is_root`) | Skipped | (Returns the item directly) |
| `item_laui` + other filters | VIEW | `item_laui` |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_laui` | ObjectId | Conditional | -- | The LAUI of the item to fetch or traverse from. Required if `is_root` is not `true`. |
| `is_root` | boolean | Conditional | -- | Set to `true` to fetch root-level items. Required if `item_laui` is not provided. |
| `item_type` | string | No | -- | Filter results by item type. |
| `parent_or_child` | `"parent"` or `"child"` | No | -- | Direction of hierarchy traversal from `item_laui`. |
| `depth` | integer | No | `1` | Number of hierarchy levels to traverse. |
| `per_page` | integer | No | `10` | Results per page. Range: `0`-`1000`. |
| `page` | integer | No | `1` | Page number. Minimum: `1`. |
| `is_deleted` | boolean | No | `true` | Whether to include soft-deleted items. |
| `page_token` | string | No | -- | Opaque token for cursor-based pagination (used for shared items). |
| `item_permission` | string | No | -- | Filter by permission level. Values: `view`, `edit`, `own`, `delete`, `true_parent_edit`, `is_true_parent`. |
| `sort_by` | string | No | -- | Field name to sort results by. |
| `filter_state` | string | No | -- | Filter items by their `state` field value. |

### Validation Rules

- **Either `item_laui` or `is_root` must be provided.** If neither is passed, the endpoint returns `400`.
- **If `is_root` is `true`**, the following fields cannot be passed: `item_laui`, `item_type`, `parent_or_child`. Passing any of them returns `400`.
- **Pagination bounds:** `per_page` must be between `0` and `1000`; `page` must be at least `1`. Out-of-range values return `400`.

### Examples

#### 4a. Get a single item by LAUI

```
GET /api/v1/catalog/get?item_laui=60d5ec49f1b2c72b8c9a1e0b
```

**Response** `200 OK`

When only `item_laui` is passed (no additional filters), returns a flat item object:

```json
{
  "laui": "60d5ec49f1b2c72b8c9a1e0b",
  "item_type": "task",
  "name": "ingest-raw-events",
  "description": "Ingests raw events from source into staging",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "is_root": false,
  "state": "scheduled",
  "project_laui": "60d5ec49f1b2c72b8c9a1e01",
  "account_laui": "507f1f77bcf86cd799439011",
  "operator_laui": "60d5ec49f1b2c72b8c9a1e04",
  "connection_laui": "60d5ec49f1b2c72b8c9a1e07",
  "frequency": "0 6 * * *",
  "logical_date": "2026-03-19T06:00:00Z",
  "start_date": "2026-03-01T00:00:00Z",
  "end_date": null,
  "priority": 2,
  "total_retries": 3,
  "retry_interval": 5,
  "created_at": "2026-03-01T10:00:00Z",
  "version": 3
}
```

#### 4b. Get root items

```
GET /api/v1/catalog/get?is_root=true
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "507f1f77bcf86cd799439011",
      "item_type": "folder.account",
      "name": "My Organization",
      "is_root": true,
      "children": [
        {
          "laui": "60d5ec49f1b2c72b8c9a1e01",
          "item_type": "folder.project",
          "name": "ETL Pipeline Project"
        }
      ]
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 4c. Get children of an item

```
GET /api/v1/catalog/get?item_laui=60d5ec49f1b2c72b8c9a1e02&parent_or_child=child
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "name": "ingest-raw-events",
      "children": []
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e15",
      "item_type": "task",
      "name": "transform-events",
      "children": []
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0a",
      "item_type": "config",
      "name": "workflow-defaults",
      "children": []
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 4d. Get parents of an item (breadcrumb)

```
GET /api/v1/catalog/get?item_laui=60d5ec49f1b2c72b8c9a1e0b&parent_or_child=parent&depth=3
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e02",
      "item_type": "folder.workflow",
      "name": "Daily Ingestion",
      "children": []
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e01",
      "item_type": "folder.project",
      "name": "ETL Pipeline Project",
      "children": []
    },
    {
      "laui": "507f1f77bcf86cd799439011",
      "item_type": "folder.account",
      "name": "My Organization",
      "children": []
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 4e. Get children filtered by item type with pagination

```
GET /api/v1/catalog/get?item_laui=60d5ec49f1b2c72b8c9a1e02&parent_or_child=child&item_type=task&per_page=5&page=2
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e20",
      "item_type": "task",
      "name": "archive-old-events",
      "children": []
    }
  ],
  "pagination": {
    "current_page": 2,
    "per_page": 5,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 4f. Get items with permission filter

```
GET /api/v1/catalog/get?item_laui=60d5ec49f1b2c72b8c9a1e01&parent_or_child=child&item_permission=edit
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e02",
      "item_type": "folder.workflow",
      "name": "Daily Ingestion",
      "children": []
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

### Error Responses

#### 400 Bad Request -- Neither item_laui nor is_root provided

```json
{
  "detail": "either one of item_laui or is_root must be passed"
}
```

#### 400 Bad Request -- Invalid pagination parameters

```json
{
  "detail": {
    "issue": "invalid pagination params passed",
    "expected pagination params": {
      "per_page": {"min": 0, "max": 1000},
      "page": {"min": 1}
    }
  }
}
```

#### 400 Bad Request -- Invalid field combination with is_root

```json
{
  "detail": {
    "error_type": "Invalid Field Combination",
    "message": "Invalid fields passed when 'is_root' is set to True.",
    "invalid_fields_passed": ["item_type"],
    "fields_disallowed_for_root": ["item_type", "item_laui", "parent_or_child"]
  }
}
```

#### 403 Forbidden -- Insufficient view access

```json
{
  "detail": "Access denied"
}
```

#### 404 Not Found

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e0b"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 5. Get Item Revisions

Retrieves the version history for a catalog item, or a specific version snapshot.

```
GET /api/v1/catalog/get/item_revisions
```

### Description

Every time a versioned field on an item is updated, a revision is created. This endpoint returns either the full list of revisions (as projections with LAUI and item_laui) or a specific revision by version number (as a full `ItemRevision`).

### Access Control

No explicit access check at the route level.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_laui` | ObjectId | Yes | The LAUI of the item whose revisions to fetch. |
| `version` | integer | No | A specific version number. If omitted, returns all revisions. |

### Examples

#### 5a. Get all revisions for an item

```
GET /api/v1/catalog/get/item_revisions?item_laui=60d5ec49f1b2c72b8c9a1e0b
```

**Response** `200 OK`

Returns `List[ItemRevisionProjection]`:

```json
[
  {
    "laui": "60d5ec49f1b2c72b8c9a3a01",
    "item_laui": "60d5ec49f1b2c72b8c9a1e0b"
  },
  {
    "laui": "60d5ec49f1b2c72b8c9a3a02",
    "item_laui": "60d5ec49f1b2c72b8c9a1e0b"
  },
  {
    "laui": "60d5ec49f1b2c72b8c9a3a03",
    "item_laui": "60d5ec49f1b2c72b8c9a1e0b"
  }
]
```

#### 5b. Get a specific version

```
GET /api/v1/catalog/get/item_revisions?item_laui=60d5ec49f1b2c72b8c9a1e0b&version=2
```

**Response** `200 OK`

Returns a single `ItemRevision`:

```json
{
  "laui": "60d5ec49f1b2c72b8c9a3a02",
  "item_laui": "60d5ec49f1b2c72b8c9a1e0b",
  "name": "ingest-raw-events",
  "item_type": "task",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "is_root": false,
  "description": "Ingests raw events from source into staging (v2 - added dedup)",
  "connection_laui": "60d5ec49f1b2c72b8c9a1e07",
  "payload": {
    "source_table": "raw_events",
    "target_table": "staged_events",
    "batch_size": 10000,
    "dedup_keys": ["event_id"]
  },
  "created_at": "2026-03-10T14:22:00Z",
  "created_by": "507f1f77bcf86cd799439099",
  "updated_by": "507f1f77bcf86cd799439099"
}
```

### Error Responses

#### 404 Not Found -- Item or version does not exist

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e0b"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 6. Delete Item

Soft-deletes or hard-deletes a catalog item.

```
POST /api/v1/catalog/delete
```

### Description

By default, performs a soft delete (sets `deleted_at` timestamp). When `hard_delete` is `true`, permanently removes the item and its data from the database.

If `parent_laui` is provided, the delete operation also removes the link between the parent and the item.

### Access Control

| Check | Permission | Target |
|-------|-----------|--------|
| Item | DELETE | `item_laui` |

### Request Body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `item_laui` | ObjectId | Yes | -- | The LAUI of the item to delete. |
| `parent_laui` | ObjectId | No | -- | The LAUI of the parent item. If provided, removes the link as well. |
| `hard_delete` | boolean | No | `false` | If `true`, permanently deletes the item. If `false`, soft-deletes (sets `deleted_at`). |

### Examples

#### 6a. Soft delete

```json
POST /api/v1/catalog/delete

{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0b",
  "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
  "hard_delete": false
}
```

**Response** `200 OK`

```json
{
  "message": "Item deleted successfully"
}
```

#### 6b. Hard delete

```json
{
  "item_laui": "60d5ec49f1b2c72b8c9a1e0f",
  "hard_delete": true
}
```

**Response** `200 OK`

```json
{
  "message": "Item deleted successfully"
}
```

### Error Responses

#### 403 Forbidden -- No delete permission

```json
{
  "detail": "Access denied"
}
```

#### 404 Not Found

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e0b"
}
```

#### 422 Unprocessable Entity -- Validation error

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["item_laui"],
      "msg": "value is not a valid ObjectId"
    }
  ]
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 7. Restore Item

Restores a previously soft-deleted item.

```
POST /api/v1/catalog/restore/{item_laui}
```

### Description

Clears the `deleted_at` timestamp on a soft-deleted item, making it active again in the catalog.

### Access Control

| Check | Permission | Target |
|-------|-----------|--------|
| Item | DELETE | `item_laui` |

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_laui` | ObjectId | Yes | The LAUI of the item to restore. |

### Example

```
POST /api/v1/catalog/restore/60d5ec49f1b2c72b8c9a1e0b
```

### Success Response

`200 OK`

```json
{
  "message": "Item restored successfully"
}
```

### Error Responses

#### 403 Forbidden -- No delete permission

```json
{
  "detail": "Access denied"
}
```

#### 404 Not Found -- Item does not exist

```json
{
  "detail": "Item not found with laui: 60d5ec49f1b2c72b8c9a1e0b"
}
```

#### 422 Unprocessable Entity -- Invalid ObjectId

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["item_laui"],
      "msg": "value is not a valid ObjectId"
    }
  ]
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 8. Search

Searches catalog items or links with flexible filters, optional projections, and pagination.

```
POST /api/v1/catalog/search
```

### Description

A powerful search endpoint that supports two mutually exclusive search modes:

- **Item search:** Finds items by type, name, parent, batch LAUIs, or primary key lookup. Supports field projection (include/exclude).
- **Link search:** Finds links by parent, child, parent type, child type, or true_parent flag.

Exactly one of `item_filter` or `link_filter` must be provided. Providing both or neither results in a `422` error.

### Access Control

No explicit access check at the route level.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_filter` | SearchItemsFilter | Conditional | Filter for item search. Mutually exclusive with `link_filter`. |
| `link_filter` | SearchLinksFilter | Conditional | Filter for link search. Mutually exclusive with `item_filter`. |
| `pagination` | PaginationRequest | No | Pagination settings. |
| `projection` | SearchItemsProjection | No | Field projection for item searches. Ignored for link searches. |

#### SearchItemsFilter

| Field | Type | Description |
|-------|------|-------------|
| `item_laui` | ObjectId | Find a specific item by LAUI. |
| `is_root` | boolean | Filter by root status. |
| `item_type` | string | Filter by item type. |
| `name` | string | Filter by name (exact match). |
| `parent_laui` | ObjectId | Filter by parent LAUI. |
| `item_lauis` | List[ObjectId] | Batch lookup by multiple LAUIs. |
| `get_by_pk` | boolean | If `true`, look up by primary key. Requires `item_type` and all PK fields for that type. Default: `false`. |
| _...extra fields_ | varies | Any additional fields to filter on (e.g., `state`, `project_laui`). Model uses `extra="allow"`. |

#### SearchLinksFilter

| Field | Type | Description |
|-------|------|-------------|
| `parent_laui` | ObjectId | Filter links by parent LAUI. |
| `child_laui` | ObjectId | Filter links by child LAUI. |
| `true_parent` | boolean | Filter links by true_parent flag. |
| `parent_type` | string | Filter links by parent item type. |
| `child_type` | string | Filter links by child item type. |

#### SearchItemsProjection

| Field | Type | Description |
|-------|------|-------------|
| `include` | List[string] | Fields to include in the response. `item_type` and `pk` are always included. |
| `exclude` | List[string] | Fields to exclude from the response. |

#### PaginationRequest

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | `1` | Page number. |
| `per_page` | integer | `10` | Results per page. |
| `sort_order` | `"asc"` or `"desc"` | `"asc"` | Sort direction by `created_at`. |
| `page_token` | string | -- | Opaque cursor token for pagination. |

### Examples

#### 8a. Search items by item_type

```json
POST /api/v1/catalog/search

{
  "item_filter": {
    "item_type": "task"
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "sort_order": "desc"
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e15",
      "item_type": "task",
      "pk": "transform-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS",
      "name": "transform-events",
      "state": "error",
      "frequency": "0 7 * * *"
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "pk": "ingest-raw-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS",
      "name": "ingest-raw-events",
      "state": "scheduled",
      "frequency": "0 6 * * *"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 20,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8b. Search items by name

```json
{
  "item_filter": {
    "name": "ingest-raw-events"
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "pk": "ingest-raw-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8c. Search items by parent_laui

```json
{
  "item_filter": {
    "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
    "item_type": "task"
  },
  "pagination": {
    "per_page": 50
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "pk": "ingest-raw-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS"
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e15",
      "item_type": "task",
      "pk": "transform-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8d. Batch search by item_lauis

```json
{
  "item_filter": {
    "item_lauis": [
      "60d5ec49f1b2c72b8c9a1e0b",
      "60d5ec49f1b2c72b8c9a1e15",
      "60d5ec49f1b2c72b8c9a1e04"
    ]
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "pk": "ingest-raw-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS"
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e15",
      "item_type": "task",
      "pk": "transform-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS"
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a1e04",
      "item_type": "operator",
      "pk": "s3-download.operator-60d5ec49f1b2c72b8c9a1e03"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8e. Search by primary key (get_by_pk)

When `get_by_pk` is `true`, the `item_type` is required plus all fields listed in that type's `unique_constraints`. For a task, the primary keys are `name`, `project_laui`, `account_laui`, and `partition`.

```json
{
  "item_filter": {
    "get_by_pk": true,
    "item_type": "task",
    "name": "ingest-raw-events",
    "project_laui": "60d5ec49f1b2c72b8c9a1e01",
    "account_laui": "507f1f77bcf86cd799439011",
    "partition": "ANALYTICS"
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e0b",
      "item_type": "task",
      "pk": "507f1f77bcf86cd799439011-ANALYTICS-ingest-raw-events-60d5ec49f1b2c72b8c9a1e01"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8f. Search by extra fields with projection

Using `extra="allow"` on `SearchItemsFilter`, you can pass any field present on the items in the database as a filter. The projection controls which fields are returned.

```json
{
  "item_filter": {
    "item_type": "task",
    "state": "error",
    "project_laui": "60d5ec49f1b2c72b8c9a1e01"
  },
  "projection": {
    "include": ["name", "state", "logical_date", "last_run_date", "retry_number", "total_retries"]
  },
  "pagination": {
    "per_page": 100,
    "sort_order": "desc"
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e15",
      "item_type": "task",
      "pk": "transform-events-60d5ec49f1b2c72b8c9a1e01-507f1f77bcf86cd799439011-ANALYTICS",
      "name": "transform-events",
      "state": "error",
      "logical_date": "2026-03-19T07:00:00Z",
      "last_run_date": "2026-03-19T07:01:23Z",
      "retry_number": 1,
      "total_retries": 2
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 100,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8g. Search items with exclusion projection

```json
{
  "item_filter": {
    "item_type": "operator",
    "parent_laui": "60d5ec49f1b2c72b8c9a1e03"
  },
  "projection": {
    "exclude": ["codeblock", "bashblock", "connection", "payload"]
  }
}
```

**Response** `200 OK`

```json
{
  "items": [
    {
      "laui": "60d5ec49f1b2c72b8c9a1e04",
      "item_type": "operator",
      "pk": "s3-download.operator-60d5ec49f1b2c72b8c9a1e03",
      "name": "s3-download.operator",
      "description": "Downloads files from S3 buckets"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8h. Search links by parent

```json
{
  "link_filter": {
    "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
    "true_parent": true
  }
}
```

**Response** `200 OK`

```json
{
  "links": [
    {
      "laui": "60d5ec49f1b2c72b8c9a2a01",
      "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
      "child_laui": "60d5ec49f1b2c72b8c9a1e0b",
      "parent_type": "folder.workflow",
      "child_type": "task",
      "true_parent": true
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a2a02",
      "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
      "child_laui": "60d5ec49f1b2c72b8c9a1e15",
      "parent_type": "folder.workflow",
      "child_type": "task",
      "true_parent": true
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a2a03",
      "parent_laui": "60d5ec49f1b2c72b8c9a1e02",
      "child_laui": "60d5ec49f1b2c72b8c9a1e0a",
      "parent_type": "folder.workflow",
      "child_type": "config",
      "true_parent": true
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "next_page_token": null
  }
}
```

#### 8i. Search links by child type

```json
{
  "link_filter": {
    "child_type": "task",
    "parent_type": "connection"
  },
  "pagination": {
    "per_page": 5
  }
}
```

**Response** `200 OK`

```json
{
  "links": [
    {
      "laui": "60d5ec49f1b2c72b8c9a2a10",
      "parent_laui": "60d5ec49f1b2c72b8c9a1e07",
      "child_laui": "60d5ec49f1b2c72b8c9a1e0b",
      "parent_type": "connection",
      "child_type": "task",
      "true_parent": false
    },
    {
      "laui": "60d5ec49f1b2c72b8c9a2a11",
      "parent_laui": "60d5ec49f1b2c72b8c9a1e07",
      "child_laui": "60d5ec49f1b2c72b8c9a1e15",
      "parent_type": "connection",
      "child_type": "task",
      "true_parent": false
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 5,
    "has_next": false,
    "next_page_token": null
  }
}
```

### Error Responses

#### 422 Unprocessable Entity -- Both filters provided

```json
{
  "detail": "Only one of item_filter or link_filter can be passed not both"
}
```

#### 422 Unprocessable Entity -- Neither filter provided

```json
{
  "detail": "Atleast one of item_filter or link_filter must be passed"
}
```

#### 422 Unprocessable Entity -- get_by_pk without item_type

```json
{
  "detail": "if get_by_pk is true then item_type must be passed"
}
```

#### 422 Unprocessable Entity -- get_by_pk with missing primary keys

```json
{
  "detail": "following primary keys:['account_laui', 'partition'] are missing for the item_type:task"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 9. Get Supported Types

Returns the allowed child and parent item types for a given item type.

```
GET /api/v1/catalog/item-types/supported-types
```

### Description

Looks up the catalog hierarchy configuration and returns which item types can be children of the given type and which types can be its parents. Useful for validation before creating links or items.

### Access Control

No explicit access check.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_type` | string | Yes | The item type to look up (e.g., `task`, `folder.workflow`). |

### Example

```
GET /api/v1/catalog/item-types/supported-types?item_type=folder.workflow
```

### Success Response

`200 OK`

```json
{
  "supported_children_types": ["folder.workflow", "task", "config", "connection", "payload", "operator", "action"],
  "supported_parent_types": ["folder.project", "folder.workflow"]
}
```

### Error Responses

#### 422 Unprocessable Entity — Unknown item type

```json
{
  "detail": "Unknown item_type: folder.workflow"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## 10. Bootstrap Project

Initializes the standard folder structure for a newly created project.

```
POST /api/v1/catalog/bootstrap
```

### Description

Creates the default set of sub-folders under a project (`folder.workflow`, `folder.operator`, `folder.action`, `folder.payload`, `folder.connection`, `folder.config`, `folder.asset`, `folder.ai`, `folder.bootstrap`). Idempotent — folders that already exist are skipped.

### Access Control

No explicit access check at the route level. The caller must have sufficient access on the project to create child items.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_laui` | string | Yes | The LAUI of the project to bootstrap. |

### Example

```
POST /api/v1/catalog/bootstrap?project_laui=60d5ec49f1b2c72b8c9a1e01
```

### Success Response

`200 OK`

```json
{
  "project_laui": "60d5ec49f1b2c72b8c9a1e01",
  "folders": [
    "60d5ec49f1b2c72b8c9a1e20",
    "60d5ec49f1b2c72b8c9a1e21",
    "60d5ec49f1b2c72b8c9a1e22"
  ]
}
```

The `folders` array contains the LAUIs of the created (or pre-existing) folder items.

### Error Responses

#### 400 Bad Request — Invalid project LAUI

```json
{
  "detail": "Invalid argument: <description>"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## 11. Validate Codeblock

Statically validates a codeblock for syntax and structural correctness.

```
POST /api/v1/catalog/validate
```

### Description

Runs static analysis on the provided codeblock without executing it. For `operator` types, checks that the four required methods (`run`, `initialize`, `check_completion`, `finish`) are present. Returns errors and warnings.

### Access Control

No explicit access check.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `codeblock` | object | Yes | Map of language to code string, e.g. `{"python": "def run(context): ..."}`. |
| `item_type` | string | Yes | The item type the codeblock belongs to (`operator`, `action`, `chat`, `agent`). |

### Example

```json
POST /api/v1/catalog/validate

{
  "codeblock": {
    "python": "import boto3\n\ndef initialize(context):\n    pass\n\ndef run(context):\n    return {}\n\ndef check_completion(context):\n    return True\n\ndef finish(context):\n    pass"
  },
  "item_type": "operator"
}
```

### Success Response

`200 OK`

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### With errors

```json
{
  "valid": false,
  "errors": [
    {
      "code": "missing_method",
      "message": "Required method 'initialize' is not defined",
      "file": null,
      "line": null
    }
  ],
  "warnings": []
}
```

#### ValidationResult fields

| Field | Type | Description |
|-------|------|-------------|
| `valid` | bool | `true` if no errors were found. |
| `errors` | array | List of `CodeblockValidationEntry` objects. |
| `warnings` | array | List of `CodeblockValidationEntry` objects (non-fatal). |

#### CodeblockValidationEntry fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Error/warning code identifier. |
| `message` | string | Human-readable description. |
| `file` | string \| null | Source file where the issue was found, if applicable. |
| `line` | integer \| null | Line number, if applicable. |

### Error Responses

#### 500 Internal Server Error

```json
{
  "detail": "Internal server error: <message>"
}
```

---

## Appendix: Item Type Schemas

Quick reference for the unique constraints (primary key fields) of each item type. The `pk` value stored in the database is the sorted PK field values joined by `-`.

| Item Type | Unique Constraints |
|-----------|-------------------|
| `folder` | `parent_laui`, `name` |
| `operator` | `parent_laui`, `name` |
| `action` | `project_laui`, `name`, `account_laui` |
| `connection` | `parent_laui`, `name` |
| `payload` | `parent_laui`, `name` |
| `config` | `parent_laui`, `name` |
| `task` | `name`, `project_laui`, `account_laui`, `partition` |
| `table` | `source_system`, `name` |
| `html_report` | `parent_laui`, `name` |
| `chat` | `parent_laui`, `name` |
| `skill` | `parent_laui`, `name` |
| `chat_history` | `parent_laui`, `name` |

## Appendix: Permission Enum Values

Used with the `item_permission` query parameter on `GET /catalog/get`.

| Value | Description |
|-------|-------------|
| `view` | Read access to the item. |
| `edit` | Write access to the item. |
| `own` | Full ownership of the item. |
| `delete` | Permission to delete the item. |
| `true_parent_edit` | Edit access inherited from the true parent. |
| `is_true_parent` | Indicates the user is the true parent of the item. |
