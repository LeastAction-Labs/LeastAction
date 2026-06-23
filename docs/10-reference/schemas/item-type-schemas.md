# Item Type Schemas Reference

All item schemas are defined in `config/schema/*.json`. Each item stored in the system validates against its corresponding schema.

## System-Managed Fields (All Item Types)

These fields are automatically managed by the system and present on every item:

| Field | Type | Description |
|-------|------|-------------|
| `_id` (LAUI) | ObjectId | Unique identifier |
| `item_type` | string | Item classification (e.g., `task`, `operator`, `folder.project`) |
| `access` | object | Access control structure |
| `parent_laui` | ObjectId | Parent item reference (null for root items) |
| `is_root` | boolean | Whether this is a root-level item (default: `false`) |
| `version` | int | Version number, auto-incremented (default: `1`) |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `deleted_at` | datetime | Soft-delete marker (null if not deleted) |
| `created_by` | ObjectId | Creator user LAUI |
| `updated_by` | ObjectId | Last updater user LAUI |
| `pk` | string | Composite primary key (default: `""`) |

---

## 1. Task (`task.json`)

**Icon**: Task | **Color**: `#3b82f6`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Name of the task |
| `partition` | string | No | `"ALL"` | Partition identifier |
| `project_laui` | ObjectId | Yes | — | Project reference (also used as cron name) |
| `project_instance` | string | No | `null` | IP address for routing tasks |
| `account_laui` | ObjectId | Yes | — | Account reference |
| `description` | string | No | `null` | Description of task |
| `operator_laui` | ObjectId | Yes | — | Operator to execute |
| `start_date` | datetime | No | `null` | Start datetime for execution |
| `end_date` | datetime | No | `null` | End datetime for execution |
| `logical_date` | datetime | No | `null` | Next/current run logical datetime |
| `retry_run_date` | datetime | No | `null` | Retry run datetime for failed tasks |
| `can_retry` | boolean | No | `false` | Whether task can retry |
| `frequency` | string | No | `"ADHOC"` | Cron expression or `"ADHOC"` |
| `data_interval_start` | datetime | No | `null` | Logical datetime at execution start |
| `data_interval_end` | datetime | No | `null` | Logical datetime + frequency at start |
| `prev_interval_start` | datetime | No | `null` | Previous run logical datetime |
| `prev_interval_end` | datetime | No | `null` | Previous run logical datetime + frequency |
| `last_run_date` | datetime | No | `null` | Previous run end datetime |
| `task_instance_start_date` | datetime | No | `null` | Current execution start datetime |
| `task_instance_end_date` | datetime | No | `null` | Current execution end datetime |
| `last_system_updated_date` | datetime | No | `null` | Last system-level update |
| `latest_heartbeat` | datetime | No | `null` | Last worker heartbeat |
| `last_run_output` | object | No | `null` | Output from last execution |
| `actions` | object | No | `{"create_actions":[],"pre_actions":[],"running_actions":[],"post_actions":[]}` | Action definitions |
| `actions_status` | object | No | `{"pre_actions":[],"running_actions":[],"post_actions":[]}` | Action execution statuses |
| `payload_laui` | ObjectId | No | `null` | Reference to a payload item |
| `payload` | any | No | `null` | Inline payload data |
| `connection_laui` | ObjectId | Yes | — | Connection to use |
| `state` | enum | No | `"scheduled"` | Execution state (see [Task States](/path?laui=getting-started-04-concepts-08-task-states&itemtype=doc.file&itemname=Task%20States)) |
| `user_set_state` | enum | No | `null` | User-requested state. Values: `cancel` |
| `attached_config_lauis` | array | No | `[]` | List of config LAUIs to merge |
| `config` | object | No | `{}` | Final merged configuration |
| `prev_interval_config` | object | No | `{}` | Previous interval's config |
| `iteration` | int | No | `0` | Total execution count |
| `duration` | int | No | `null` | Execution time in milliseconds |
| `executor` | string | No | `null` | Celery worker name |
| `task_instance` | string | No | `null` | Instance name |
| `task_reschedule_count` | int | No | `0` | Reschedule count |
| `session_id` | string | No | `null` | Current session ID |
| `last_run_session_id` | string | No | `null` | Previous run session ID |
| `total_retries` | int | No | `0` | Max retry attempts allowed |
| `retry_interval` | int | No | `1` | Minutes between retries |
| `retry_number` | int | No | `0` | Current retry attempt |
| `priority` | int | No | `1` | Execution priority |

### State Enum Values

`created`, `scheduled`, `queued_for_connection`, `queued_in_redis`, `running`, `success`, `error`, `timeout`, `cancelled`, `fail`

### Constraints

- **Unique**: `[name, project_laui, account_laui, partition]`
- **Indexes**:
  - `[project_laui, deleted_at, state, user_set_state, logical_date, start_date, end_date]` filtered to states `[scheduled, success]`
  - `[project_laui, deleted_at, user_set_state, total_retries, retry_number, start_date, end_date, last_run_date, retry_interval]` filtered to states `[error, timeout]`

### Field Categories

- **System Update Fields** (only modifiable by system): `logical_date`, `last_run_date`, `last_system_updated_date`, `latest_heartbeat`, `last_run_output`, `payload`, `config`, `state`, `user_set_state`, `iteration`, `duration`, `task_instance`, `last_run_session_id`, `retry_number`, `actions_status`, `task_instance_start_date`, `task_instance_end_date`, `session_id`, `data_interval_start`, `data_interval_end`, `prev_interval_start`, `prev_interval_end`

- **User Update Fields** (modifiable by user): `description`, `start_date`, `end_date`, `logical_date`, `frequency`, `payload_laui`, `payload`, `state`, `connection_laui`, `user_set_state`, `attached_config_lauis`, `total_retries`, `retry_interval`, `priority`, `actions`, `config`, `operator_laui`

- **Version Fields** (changes trigger version history): `description`, `connection_laui`, `payload`, `payload_laui`, `config`, `actions`, `frequency`, `operator_laui`

- **Projection Fields** (returned in list views): `name`, `partition`, `frequency`, `state`, `actions_status`, `priority`, `retry_number`, `prev_interval_start`, `logical_date`, `last_run_date`, `duration`, `actions`

---

## 2. Action (`action.json`)

**Icon**: FlashOn | **Color**: `#eab308`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-]+\.action$`, max 255 | Must end with `.action` |
| `description` | string | No | — | max 1000 | Optional description |
| `prompt` | string | No | — | max 10000 | AI generation prompt |
| `install_docs` | object | No | — | max 10000 | Install documentation (Markdown) |
| `guide_docs` | object | No | — | max 10000 | Guide documentation (Markdown) |
| `codeblock` | object | Yes | — | max 10000 | Python code to execute |
| `bashblock` | object | Yes | — | max 10000 | Bash setup code |
| `connection` | object | No | — | max 10000 | Connection sample JSON |
| `action_variables` | object | No | — | max 10000 | Payload/variables sample JSON |
| `project_laui` | ObjectId | Yes | — | — | Project reference |
| `account_laui` | ObjectId | Yes | — | — | Account reference |

### Constraints

- **Unique**: `[project_laui, name, account_laui]`
- **Projection Fields**: `name`, `deleted_at`

---

## 3. Operator (`operator.json`)

**Icon**: Build | **Color**: `#f97316`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-]+\.operator$`, max 255 | Must end with `.operator` |
| `description` | string | No | — | max 1000 | Optional description |
| `prompt` | string | No | — | max 10000 | AI generation prompt |
| `install_docs` | string | No | — | max 10000 | Install documentation (Markdown) |
| `guide_docs` | string | No | — | max 10000 | Guide documentation (Markdown) |
| `codeblock` | object | Yes | — | max 10000 | Python code to execute |
| `bashblock` | object | Yes | — | max 10000 | Bash setup code |
| `connection` | object | No | — | max 10000 | Connection sample JSON |
| `payload` | any | No | — | max 10000 | Payload sample JSON |
| `marketplace_laui` | string | No | — | — | Operator version (0 = latest) |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`

---

## 4. Connection (`connection.json`)

**Icon**: Cloud | **Color**: `#06b6d4`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 |
| `description` | string | No | `""` | max 1000 |
| `content` | object | Yes | — | Connection configuration JSON |
| `max_parallelism` | int | No | `10` | Maximum concurrent tasks |
| `current_parallelism` | int | No | `0` | Currently running tasks |
| `in_queue` | int | No | `0` | Tasks waiting in queue |
| `sort_dict` | object | No | `{}` | Custom sort configuration |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `max_parallelism`, `current_parallelism`, `in_queue`
- **Version Fields**: `description`, `content`
- **User Update Fields**: `description`, `content`, `max_parallelism`, `sort_dict`

---

## 5. Payload (`payload.json`)

**Icon**: Storage | **Color**: `#8b5cf6`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Alphanumeric with spaces/hyphens/underscores |
| `description` | string | No | `""` | max 1000 | Optional description |
| `content` | any | Yes | — | — | Payload content (flexible type) |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`, `deleted_at`

---

## 6. Folder (`folder.json`)

**Icon**: Folder | **Color**: `#10b981`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Folder name |
| `description` | string | No | `""` | max 1000 | Optional description |
| `folder_metadata` | object | No | `{}` | max 1000 | Custom metadata (used for cron status, etc.) |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`, `deleted_at`, `folder_metadata`
- **Version Fields**: `description`
- **Indexes**: `folder_metadata.state`

### Validation Rules

- `path_consistency`: Path must be consistent with parent_folder_laui relationship
- `no_circular_references`: Parent folder cannot be a descendant of current folder
- `unique_name_per_parent`: Folder names must be unique within same parent

### Folder Subtypes

Folders use dot-notation subtypes: `folder.account`, `folder.project`, `folder.workflow`, `folder.operator`, `folder.action`, `folder.payload`, `folder.connection`, `folder.config`, `folder.asset`, `folder.report`, `folder.table`, `folder.trash`, `folder.users`, `folder.user`, `folder.bootstrap`, `folder.ai`

AI items (`chat`, `agent`, `skill`) all live under `folder.ai` — there are no `folder.chat`, `folder.agent`, or `folder.skill` subtypes.

---

## 7. Config (`config.json`)

**Icon**: SettingsApplications | **Color**: `#64748b`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Config name |
| `description` | string | No | `""` | max 1000 | Optional description |
| `config_type` | enum | Yes | — | `system`, `task`, `UIaction`, `taskAction`, `connection`, `workflow` | Type of configuration |
| `content` | object | Yes | — | — | Configuration content as JSON |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`, `content`

---

## 8. Connection Queue (`connection_queue.json`)

Internal schema used for task load balancing across connections.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Queue entry name |
| `partition` | string | Yes | Partition identifier |
| `task_laui` | ObjectId | Yes | Task reference |

### Constraints

- **Unique**: `[name, partition, task_laui]`
- **Indexes**: `task_laui`

---

## 9. Table (`table.json`)

**Icon**: TableChart | **Color**: `#4f46e5`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\.]+$` |
| `source_system` | string | Yes | — | Origin: `GLUE`, `REDSHIFT`, `POSTGRES`, `SNOWFLAKE` |
| `location_uri` | string | Yes | — | S3 path or JDBC connection string |
| `status` | string | Yes | `"ACTIVE"` | Lifecycle: `ACTIVE`, `DEPRECATED`, `STALE`, `BROKEN` |
| `last_sync_at` | datetime | No | — | Last successful ETL timestamp |
| `row_count` | int | No | — | Records at last sync |
| `load_strategy` | string | Yes | `"INCREMENTAL"` | `FULL_REFRESH`, `INCREMENTAL`, `SCD_TYPE_2` |
| `quality_score` | float | No | — | Data quality metric (% rows passing validation) |
| `schema_definition` | object | No | — | JSON of columns and data types |
| `etl_watermarks` | object | No | `{}` | `last_processed_id` or `max_updated_at` values |
| `lineage_metadata` | object | No | `{}` | Upstream source tables and job IDs |

### Constraints

- **Unique**: `[source_system, name]`
- **Projection Fields**: `name`, `source_system`, `status`, `last_sync_at`, `row_count`, `quality_score`

---

## 10. HTML Report (`html_report.json`)

**Icon**: Html | **Color**: `#eab308`

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-]+\.action$`, max 255 | Report name |
| `description` | string | No | — | max 1000 | Optional description |
| `html` | string | No | — | max 100000 | HTML content |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`, `deleted_at`

---

## 11. AI Item Types — `chat`, `agent`, `skill`

`chat`, `agent`, and `skill` are flat, first-class item types. They live under `folder.ai` in the catalog. There are no `ai_chat` or `ai_skill` item types — the correct item type strings are `chat`, `agent`, and `skill`.

| Item type | Role |
|---|---|
| `chat` | Powers the **generation wizard** (`AI > Operator`, `AI > Action`, etc.). Uses `with_structured_output`. |
| `agent` | Powers the **chat widget**. Conversational LLM with optional MCP tool-calling. Uses `bind_tools`. |
| `skill` | Injects context into any AI prompt. Markdown file prepended to the system prompt. |

### 11a. AI Chat (`chat`)

**Icon**: SmartToy | **Color**: `#8b5cf6`

The LLM invocation module that drives the generation service. Contains a `run(connection, messages)` function that returns structured JSON using `with_structured_output`.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Item name |
| `description` | string | No | `""` | max 1000 | Optional description |
| `codeblock` | object | No | — | max 10000 | Python code — `run(connection, messages)` |
| `bashblock` | object | No | — | max 10000 | Bash dependencies |
| `connection` | object | No | — | max 10000 | LLM provider credentials — api_key, model, token_limit |

### 11b. AI Agent (`agent`)

**Icon**: SmartToy | **Color**: `#8b5cf6`

A conversational agent that backs the chat widget. Contains a `run(connection, messages, tools=None)` function. When MCP tools are available, uses `bind_tools` and returns both a content string and any tool calls invoked.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Item name |
| `description` | string | No | `""` | max 1000 | Optional description |
| `codeblock` | object | No | — | max 10000 | Python code — `run(connection, messages, tools=None)` |
| `bashblock` | object | No | — | max 10000 | Bash dependencies |
| `connection` | object | No | — | max 10000 | LLM provider credentials — api_key, model, token_limit |

**Return value from `run`:**
```json
{
  "content": "<text response, or empty string when tool calls are made>",
  "tool_calls": [
    { "name": "tool_name", "id": "call_id", "arguments": {} }
  ]
}
```
`tool_calls` is only present when the LLM invoked tools.

### 11c. Skill (`skill`)

**Icon**: SmartToy | **Color**: `#8b5cf6`

A markdown-formatted skill that injects context into the AI prompt during generation or execution.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | — | regex: `^[a-zA-Z0-9_\-\s]+$`, max 255 | Skill name |
| `description` | string | No | `""` | max 1000 | What this skill does |
| `content` | string | No | — | max 50000 | Text prepended to AI system prompt |

### Shared Fields (`chat`, `agent`, `skill`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version_compatibility` | object | No | Declares compatible Core major versions |
| `version_details` | object | No | Source, versioning, and publishing metadata |
| `image_url` | string | No | URL to a custom icon/image for marketplace (max 500) |
| `tags` | array | No | Searchable tags, max 20 items |
| `category` | string | No | Top-level category (max 100) |
| `publisher` | string | No | Publishing entity (max 100) |
| `verified` | boolean | No | True if verified/endorsed by the marketplace |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `description`, `parent_laui`

---

## 12. AI History (`chat_history.json`)

**Icon**: History | **Color**: `#8b5cf6`

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | AI session name (max 255) |
| `description` | string | No | — | Session description (max 1000) |
| `created_item_type` | string | Yes | — | Type created: `action`, `operator`, `payload`, `chat`, `agent` |
| `ai_provider` | string | No | — | AI provider used |
| `connection_laui` | string | No | — | Connection LAUI used |
| `connection_name` | string | No | — | Connection name used |
| `messages` | any | No | — | Array of prompts and responses |
| `generated_content` | any | No | — | Latest generated content |

### Constraints

- **Unique**: `[parent_laui, name]`
- **Projection Fields**: `name`, `created_item_type`, `ai_provider`

---

## Supported Data Types

| Type | Description |
|------|-------------|
| `ObjectId` | MongoDB ObjectId (24-char hex string) |
| `string` | Text value |
| `int` | Integer |
| `float` | Decimal number |
| `boolean` | `true` / `false` |
| `datetime` | ISO 8601 timestamp |
| `object` | JSON object |
| `array` | JSON array (of strings) |
| `enum` | One of a fixed set of values |
| `any` | Flexible type (string, object, array, etc.) |
