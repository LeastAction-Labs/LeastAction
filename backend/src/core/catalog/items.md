# Catalog Items — Technical Reference

## Table of Contents
1. [Overview](#overview)
2. [Item Types](#item-types)
3. [Item Schema & Core Fields](#item-schema--core-fields)
4. [Schema Validation System](#schema-validation-system)
5. [Item Type Hierarchy](#item-type-hierarchy)
6. [CRUD Operations](#crud-operations)
7. [Versioning](#versioning)
8. [Access Control](#access-control)
9. [Task-Specific Behavior](#task-specific-behavior)
10. [Search](#search)
11. [API Reference](#api-reference)
12. [Key Files](#key-files)

---

## Overview

An **Item** is the fundamental entity in the LeastAction catalog. Every piece of data — folders, tasks, operators, connections, payloads, configs, actions, tables, reports — is an item. Items are stored in MongoDB's `items` collection and are identified by a **LAUI** (LeastAction Unique Identifier), which is a MongoDB `ObjectId`.

Items are organized in a tree hierarchy using **Links** (see [links.md](links.md)). The hierarchy rules — which item types can contain which — are defined in `config/catalog.json`.

---

## Item Types

### Folder Types (Containers)

| Item Type | Description |
|-----------|-------------|
| `folder.account` | Top-level organizational unit. Can contain `folder.project`, `folder.trash` |
| `folder.project` | Project container. Contains workflow, operator, payload, connection, config, asset, action, bootstrap folders |
| `folder.workflow` | Workflow container. Can contain nested workflow folders, tasks, configs, connections, payloads, operators, actions |
| `folder.operator` | Groups operators. Can contain nested operator folders and `operator` items |
| `folder.connection` | Groups connections. Can contain nested connection folders and `connection` items |
| `folder.payload` | Groups payloads. Can contain nested payload folders and `payload` items |
| `folder.config` | Groups configs. Can contain nested config folders and `config` items |
| `folder.action` | Groups actions. Can contain nested action folders and `action` items |
| `folder.asset` | Asset container. Can contain report/table folders, `html_report`, `table` |
| `folder.report` | Report container. Can contain nested report folders, `html_report`, `config` |
| `folder.table` | Table container. Can contain nested table folders, `table`, `config` |
| `folder.bootstrap` | Bootstrap data container |
| `folder.trash` | Soft-deleted items land here. Can contain `task`, `connection`, `config`, `action`, `operator`, `payload` |

### Non-Folder Types (Leaf Items)

| Item Type | Description | Schema File |
|-----------|-------------|-------------|
| `task` | Executable scheduled unit of work | `config/schema/task.json` |
| `operator` | Code/bash execution component (multi-phase) | `config/schema/operator.json` |
| `connection` | External system connection with credentials | `config/schema/connection.json` |
| `payload` | Data payload attached to tasks | `config/schema/payload.json` |
| `config` | Configuration item (system, task, UI, workflow) | `config/schema/config.json` |
| `action` | Synchronous single-step execution component | `config/schema/action.json` |
| `html_report` | HTML report artifact | `config/schema/html_report.json` |
| `table` | Data table artifact | `config/schema/table.json` |
| `connection_queue` | Queue for managing connection parallelism | `config/schema/connection_queue.json` |

---

## Item Schema & Core Fields

All items share a base set of fields defined in `backend/src/core/catalog/item/schema.py`.

### Base Fields (All Items)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `laui` | `ObjectId` | Auto | MongoDB `_id` — the item's unique identifier |
| `name` | `string` | Yes | Display name of the item |
| `item_type` | `string` | Yes | Type identifier (e.g., `"task"`, `"folder.project"`, `"operator.python"`) |
| `parent_laui` | `ObjectId` | Conditional | Parent item's LAUI. Required when `is_root=false` |
| `is_root` | `bool` | No | `true` for root-level items (e.g., `folder.account`). Default: `false` |
| `pk` | `string` | Auto | Computed primary key for uniqueness checking (joined unique_constraint values) |

### Database Fields (Set Automatically)

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | `datetime` | UTC timestamp when item was created |
| `updated_at` | `datetime` | UTC timestamp of last update |
| `deleted_at` | `datetime` | UTC timestamp when soft-deleted. `null` = active |
| `created_by` | `ObjectId` | LAUI of the user who created the item |
| `updated_by` | `ObjectId` | LAUI of the user who last updated the item |
| `version` | `int` | Version counter, starts at `1`. Incremented on versioned updates |

### Access Fields

| Field | Type | Description |
|-------|------|-------------|
| `access` | `object` | Resolved access control (owners, editors, viewers) — stored in DB |
| `access_patch` | `object` | Add/remove access — used in create/update requests, not persisted directly |

### System Fields (Cannot Be Customized in Schema)

```python
# From constants_mappers.py
system_fields = ["access", "item_type", "parent_laui", "is_root", "version", "pk"]
db_fields = ["created_at", "updated_at", "access", "version", "deleted_at"]
```

### Dynamic Fields

Each item type defines additional fields via its JSON schema file in `config/schema/`. These fields are validated dynamically using Pydantic models generated at runtime by `model_creator.py`. See the [Schema Validation System](#schema-validation-system) section.

### Pydantic Model Hierarchy

```
ItemBase (name, item_type, parent_laui, is_root) + extra="allow"
  ├── CreateItem (+ access_patch)
  │     └── CreateItemInDB (+ access, timestamps, version, created_by)
  │           └── Item (+ laui)
  └── UpdateItem (+ laui, version, set_access, unset_access, updated_by)

ItemProjection (laui, item_type) + extra="allow"
ItemWithPermission (laui, permission)
```

---

## Schema Validation System

Every item type has a JSON schema file at `config/schema/{item_type}.json` that defines its columns, constraints, and behavior.

### Schema File Structure

```json
{
  "columns": [
    {
      "name": "field_name",
      "datatype": "string|int|datetime|ObjectId|object|array|enum|any|boolean|float",
      "required": true|false,
      "default": null,
      "min_length": 1,
      "max_length": 255,
      "regex": "^pattern$",
      "enum_values": ["val1", "val2"],
      "description": "Human readable description"
    }
  ],
  "unique_constraints": ["field1", "field2"],
  "projection_fields": ["name", "state"],
  "version_fields": ["field1", "field2"],
  "user_update_fields": ["field1", "field2"],
  "system_update_fields": ["field1", "field2"],
  "indexes": [...]
}
```

### Schema Properties

| Property | Required | Description |
|----------|----------|-------------|
| `columns` | Yes | Array of column definitions. Must include a `name` column with `datatype: "string"` and `required: true` |
| `unique_constraints` | Yes | Fields that form the primary key (combined with `item_type`). Used for upsert logic |
| `projection_fields` | Yes | Fields included when listing items (table/list views) |
| `version_fields` | No | If specified, a new revision is only created when one of these fields changes. If omitted, every update creates a revision |
| `user_update_fields` | No | Fields that users can modify via the update API. If omitted, all non-system fields are updatable |
| `system_update_fields` | No | Fields that can be modified by the system (e.g., task execution engine). Fields in `system_update_fields` but NOT in `user_update_fields` are silently ignored in user updates |
| `indexes` | No | MongoDB index definitions |

### Supported Datatypes

| Datatype | Python Type | Description |
|----------|-------------|-------------|
| `string` | `str` | Text value. Supports `min_length`, `max_length`, `regex` |
| `int` | `int` | Integer |
| `float` | `float` | Floating point |
| `boolean` | `bool` | True/false |
| `datetime` | `datetime` | ISO 8601 datetime |
| `ObjectId` | `PydanticObjectId` | MongoDB ObjectId reference |
| `object` | `Dict[str, Any]` | JSON object |
| `array` | `List[str]` | List of strings |
| `array[ObjectId]` | `List[PydanticObjectId]` | List of ObjectIds |
| `enum` | `str` (Literal) | Restricted to `enum_values` list |
| `any` | `Any` | Accepts any value |

### Validation Flow

```
API Request (BaseCreateItemRequest)
  │
  ▼
SchemaManager.__init__(item_type)
  │  ├─ schema_loader.load_json(item_type)     → Load config/schema/{item_type}.json
  │  ├─ SchemaValidation.validate_schema_dict() → Validate the schema itself
  │  └─ model_creator.create_item_model()       → Build dynamic Pydantic model
  │
  ▼
CatalogService.validate_item_schema(request)
  │  ├─ item_type_for_schema = item_type.split('.')[0]  → "operator.python" → "operator"
  │  ├─ CreateItemRequest_model.model_validate(item)     → Validate against dynamic model
  │  └─ CreateItem(**validated_data)                     → Return validated item
  │
  ▼
Schema validation errors → UnprocessableEntityError with field-level details
```

### Schema Validation Checks

The `SchemaValidation` class performs:

1. **Column validation**: Each column must have `name`, `datatype`, `required`
2. **System field protection**: Custom validations cannot override system fields
3. **Name column check**: A `name` column with `datatype: "string"` and `required: true` must exist
4. **Unique constraints validation**: All fields in `unique_constraints` must exist in `columns`
5. **Projection fields validation**: All fields in `projection_fields` must exist in `columns`
6. **Version fields validation**: All fields in `version_fields` must exist in `columns`

### Primary Key (PK) Computation

The `pk` field is a composite key computed at creation time:

```python
item.pk = "-".join(
    str(getattr(item, key, None)) if key != "item_type" else item_type_for_schema
    for key in sorted(schema_manager.primary_keys)
)
# primary_keys = set(unique_constraints) | {"item_type"}
```

Example for a task with `unique_constraints: ["name", "project_laui", "account_laui", "partition"]`:
```
pk = "{account_laui}-{name}-{partition}-{project_laui}-task"
```

This `pk` is used to check for existing items before creating. If an item with the same `pk` exists, the operation becomes an **update** (upsert).

---

## Item Type Hierarchy

The file `config/catalog.json` defines which items can contain which via `item_type_link_mapping`:

```
folder.account
  ├── folder.project
  └── folder.trash

folder.project
  ├── folder.action
  ├── folder.asset
  ├── folder.workflow
  ├── folder.operator
  ├── folder.payload
  ├── folder.connection
  ├── folder.bootstrap
  └── folder.config

folder.workflow
  ├── folder.workflow  (nested)
  ├── task
  ├── config
  ├── connection
  ├── payload
  ├── operator
  └── action

folder.config    → folder.config, config
folder.operator  → folder.operator, operator
folder.payload   → folder.payload, payload
folder.connection→ folder.connection, connection
folder.action    → folder.action, action
folder.asset     → folder.asset, folder.report, folder.table, html_report, table
folder.report    → folder.report, html_report, config
folder.table     → folder.table, table, config
folder.trash     → task, connection, config, action, operator, payload

connection → connection_queue, task
operator   → task
task       → task
payload    → task
config     → task
table      → column
database   → schema
schema     → table
```

### Type Compatibility Check

The `SupportedItemTypesManager` (from `config/catalog.json`) and `CatalogService._check_item_type_compatible()` enforce these rules. Type matching supports **prefix matching** for subtypes:

```python
# An item_type of "operator.python" matches "operator" in the supported list
item_type == supported_item_type or item_type.startswith(supported_item_type + ".")
```

The system also walks up the type hierarchy — if `operator.python` has no direct mapping, it checks `operator`.

---

## CRUD Operations

### Create

**Endpoint:** `POST /api/v1/catalog/create`
**Request Body:** `BaseCreateItemRequest` (with `item_type` + extra fields allowed)

**Flow:**

```
ItemOrchestrator.create_item(request)
  │
  ├─ CatalogService.validate_item_schema(request)   → Schema validation
  │     └─ Returns CreateItem model
  │
  ├─ [If task] TaskManager.validate_task_creation()  → Task-specific validation
  │
  └─ CatalogService.create_item(item)
        │
        ├─ Compute pk from unique_constraints
        ├─ Try get_item_by_pk(pk)
        │     ├─ [Found] → update_existing_item()    → UPSERT
        │     └─ [NotFound] →
        │           ├─ [is_root=true]  → _create_root_item()
        │           └─ [is_root=false] → _create_linkable_item()
        │
        └─ [If task & new] → _link_tasks()            → Link to parent tasks
```

**Key behaviors:**
- **Upsert**: If an item with the same primary key exists, the create becomes an update
- **Root items**: `is_root=true` — created without a parent; the creator is automatically set as owner
- **Linkable items**: `is_root=false` — requires `parent_laui`; a hard link to the parent is created automatically
- **Tasks**: On creation, soft links are automatically created to the operator, connection, payload, and config items referenced by the task

**Rules for `is_root` and `parent_laui`:**

| `is_root` | `parent_laui` | Result |
|-----------|---------------|--------|
| `true` | Not provided | Valid — creates root item |
| `false` / omitted | Provided | Valid — creates child item |
| `true` | Provided | Invalid |
| `false` / omitted | Not provided | Invalid |

### Read (Get)

**Endpoint:** `GET /api/v1/catalog/get`
**Query Parameters:** `GetItemsFilter`

| Parameter | Type | Description |
|-----------|------|-------------|
| `item_laui` | `ObjectId` | Item to fetch or pivot on |
| `is_root` | `bool` | Fetch root-level items (cannot combine with `item_laui`, `item_type`, `parent_or_child`) |
| `item_type` | `string` | Filter by type (uses regex prefix matching) |
| `parent_or_child` | `"parent"` or `"child"` | Direction of traversal from `item_laui` |
| `depth` | `int` | Levels of hierarchy to traverse. Default: `1` |
| `page` | `int` | Page number (min: `1`). Default: `1` |
| `per_page` | `int` | Items per page (min: `0`, max: `1000`). Default: `10` |
| `is_deleted` | `bool` | Include soft-deleted items. Default: `false` |

**Query Patterns:**

| Pattern | Parameters | Description |
|---------|-----------|-------------|
| Single item | `item_laui` only | Returns full item detail |
| Root items | `is_root=true` | Returns top-level items the user can access |
| Children | `item_laui` + `parent_or_child=child` | Returns children of item (optionally filtered by `item_type`) |
| Parents | `item_laui` + `parent_or_child=parent` | Returns parent chain (breadcrumb) |
| Deep hierarchy | Add `depth=N` | Traverses N levels deep |

**Validation rules:**
- Either `item_laui` or `is_root` must be provided
- When `is_root=true`, no other filter fields can be set

### Update

Updates happen implicitly via the create endpoint (upsert behavior). When a `POST /api/v1/catalog/create` matches an existing primary key:

1. The existing item is fetched
2. Access is checked (edit access, or own access if changing owners)
3. Only changed fields are applied
4. `user_update_fields` restrictions are enforced — attempting to change a field not in `user_update_fields` raises `UnprocessableEntityError`
5. Fields in `system_update_fields` but not in `user_update_fields` are silently ignored
6. Version is incremented if `version_fields` are affected (or if `version_fields` is not defined)
7. A revision is created before applying changes

### Delete

**Endpoint:** `POST /api/v1/catalog/delete`
**Request Body:**

```json
{
  "item_laui": "ObjectId",
  "parent_laui": "ObjectId",
  "hard_delete": false
}
```

**Three deletion modes:**

| Condition | Mode | What Happens |
|-----------|------|-------------|
| `parent_laui` is the trash folder OR `hard_delete=true` | **Hard Delete** | Permanently removes item + all hard children + all associated links |
| Link is a hard link (`true_parent=true`) | **Soft Delete** | Sets `deleted_at`, moves to trash folder, deletes the hard link |
| Link is a soft link (`true_parent=false`) | **Unlink** | Deletes only the soft link; item remains intact |

**Protection:** The trash folder itself cannot be deleted.

See [delete.md](delete.md) for the detailed deletion flow.

---

## Versioning

Items support version tracking via the `item_revisions` MongoDB collection.

### How It Works

1. **On update**: Before applying changes, the current state of the item is saved as a revision in the `item_revisions` collection
2. **Version increment**: The item's `version` field is incremented
3. **Selective versioning**: If `version_fields` is defined in the schema, a revision is only created when one of those fields changes. If `version_fields` is not defined, every update creates a revision

### Retrieving Revisions

**Endpoint:** `GET /api/v1/catalog/get/item_revisions`

| Parameter | Type | Description |
|-----------|------|-------------|
| `item_laui` | `ObjectId` | The item to get revisions for |
| `version` | `int` (optional) | Specific version to retrieve. If omitted, returns all revisions |

### Example: Connection Versioning

The `connection.json` schema defines:
```json
"version_fields": ["description", "content"]
```

Only changes to `description` or `content` create a new revision. Changes to `max_parallelism` or `sort_dict` do not.

---

## Access Control

Items use a role-based access control system integrated with **Ory Keto**.

### Permission Levels

| Level | Description |
|-------|-------------|
| `owner` | Full control — can manage access, delete, edit |
| `editor` | Can modify the item |
| `viewer` | Read-only access |

### Access Patch (Create/Update)

When creating or updating items, use `access_patch` to add or remove permissions:

```json
{
  "access_patch": {
    "add": {
      "owners": { "U{user_laui}": "" },
      "editors": {},
      "viewers": {}
    },
    "remove": {
      "owners": {},
      "editors": {},
      "viewers": {}
    }
  }
}
```

### Access Checks Per Operation

| Operation | Required Access | Route Check |
|-----------|----------------|-------------|
| Create (under parent) | Edit on parent | `check_item_edit_access(parent_laui)` |
| Read | View on item | `check_item_view_access(item_laui)` |
| Update | Edit on item | `check_item_edit_access(item_laui)` |
| Update owners | Own on item | `check_item_own_access(item_laui)` |
| Delete | Delete on item | `check_item_delete_access(item_laui)` |
| Create link | Edit on parent + View on child | Both checked |
| Get tasks ready to run | Own on project | `check_item_own_access(project_laui)` |

### Access Inheritance

When traversing the hierarchy (parent → child), hard-link children inherit their parent's permission context. The `true_parent_permission` is passed during permission resolution for children with `true_parent=true` links.

---

## Task-Specific Behavior

Tasks (`item_type: "task"`) have specialized behavior beyond regular items.

### Task Schema Fields

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Task display name |
| `project_laui` | `ObjectId` | Project this task belongs to |
| `account_laui` | `ObjectId` | Account this task belongs to |
| `operator_laui` | `ObjectId` | Operator to execute |
| `connection_laui` | `ObjectId` | Connection to use |

**Scheduling fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `start_date` | `datetime` | `null` | When the task becomes eligible to run |
| `end_date` | `datetime` | `null` | When to stop scheduling. `null` = no end |
| `logical_date` | `datetime` | `null` | Next scheduled run date |
| `frequency` | `string` | `"ADHOC"` | Cron expression or `"ADHOC"` |

**State management:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `state` | `enum` | `"scheduled"` | Execution state: `created`, `scheduled`, `queued_for_connection`, `queued_in_redis`, `running`, `success`, `error`, `timeout`, `cancelled`, `fail` |
| `user_set_state` | `enum` | `null` | User override: `"cancel"` stops scheduling |

**Retry policy:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `total_retries` | `int` | `0` | Max retry attempts |
| `retry_interval` | `int` | `1` | Minutes to wait between retries |
| `retry_number` | `int` | `0` | Current retry count |

**Execution tracking:**

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `int` | Total execution count over the task's lifetime |
| `duration` | `int` | Milliseconds taken for last execution |
| `executor` | `string` | Celery worker that ran the task |
| `last_run_date` | `datetime` | When the task last ran |
| `last_run_output` | `object` | Output from last execution |
| `last_run_session_id` | `string` | Session ID of last run |
| `latest_heartbeat` | `datetime` | Most recent heartbeat from running task |

### Task Ready-to-Run Query

The cron executor periodically calls `GET /api/v1/catalog/get/tasks_ready_to_run/{project_laui}` to find tasks eligible for execution. The MongoDB aggregation pipeline checks:

1. `item_type == "task"` and `deleted_at == null`
2. `start_date < current_time`
3. `user_set_state != "cancel"`
4. `project_laui` matches
5. End date: `end_date == null` OR `logical_date <= end_date`
6. State conditions:
   - If `state` in `["scheduled", "success"]`: `logical_date <= current_time`
   - If `state == "error"`: `total_retries > 0`
7. Retry policy: If in error/timeout state, must have `retry_number < total_retries` AND `last_run_date + retry_interval` has passed
8. Workflow parent's `folder_metadata.state != "PAUSE"`

### Automatic Linking on Task Creation

When a new task is created, the system automatically creates **soft links** from referenced items to the task:

| If task has... | Link created | Stored on task as |
|----------------|-------------|-------------------|
| `operator_laui` | operator → task | `link_operator_laui` |
| `connection_laui` | connection → task | `link_connection_laui` |
| `payload_laui` | payload → task | `link_payload_laui` |
| `attached_config_lauis` | config → task (for each) | `link_config_lauis[]` |

### Task Dependency Linking

Tasks can depend on other tasks via the `LeastActionCheckIfAreParentsDone` pre-action. When a task with this pre-action is created:

1. Parent task names are extracted from `action_variables.parents`
2. Parent tasks are searched by name within the same project
3. Soft links are created: parent task → child task
4. At runtime, the pre-action checks if all parent tasks have completed

---

## Search

**Endpoint:** `POST /api/v1/catalog/search`

**Request Body:**

```json
{
  "filter": {
    "item_laui": "ObjectId (optional)",
    "is_root": true,
    "item_type": "task",
    "name": "my-task",
    "parent_laui": "ObjectId",
    "get_by_pk": false
  },
  "pagination": {
    "page": 1,
    "per_page": 10
  },
  "projection": {
    "include": ["name", "state"],
    "exclude": []
  }
}
```

**Key behaviors:**
- `item_type` filter uses regex prefix matching (`^task(\\.|$)`)
- `get_by_pk=true` mode: looks up item by primary key (requires `item_type` and all unique constraint fields)
- Soft-deleted items are always excluded (`deleted_at: null`)
- Results are paginated with `has_next` indicator

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/catalog/create` | Create or update an item (upsert) |
| `GET` | `/api/v1/catalog/get` | Get items with filtering and pagination |
| `GET` | `/api/v1/catalog/get/item_revisions` | Get version history for an item |
| `POST` | `/api/v1/catalog/delete` | Soft or hard delete an item |
| `POST` | `/api/v1/catalog/search` | Search items with filters and projections |
| `POST` | `/api/v1/catalog/create/link` | Create a link between items |
| `GET` | `/api/v1/catalog/get/tasks_ready_to_run/{project_laui}` | Get tasks eligible for execution |

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/core/catalog/item/schema.py` | Item Pydantic models (ItemBase, CreateItem, Item, UpdateItem) |
| `backend/src/core/catalog/item/repo.py` | ItemRepository — MongoDB CRUD for items |
| `backend/src/core/catalog/service.py` | CatalogService — core business logic |
| `backend/src/core/catalog/orchestrator.py` | ItemOrchestrator — coordination layer |
| `backend/src/core/catalog/api_request.py` | API request/response schemas |
| `backend/src/core/api/routes/catalog.py` | FastAPI route definitions |
| `config/catalog.json` | Item type hierarchy (what can contain what) |
| `config/schema/*.json` | Per-type schema definitions |
| `backend/src/core/catalog/utils/schema/schema_manager.py` | SchemaManager — loads and validates schemas |
| `backend/src/core/catalog/utils/schema/schema_validations.py` | Schema validation logic |
| `backend/src/core/catalog/utils/schema/model_creator.py` | Dynamic Pydantic model creation |
| `backend/src/core/catalog/utils/catalog/catalog_manager.py` | SupportedItemTypesManager |
| `backend/src/core/catalog/utils/constants_mappers.py` | System fields, type mappers |
| `backend/src/core/catalog/item_directory.py` | ItemDirectory — tree traversal structure |
| `backend/src/core/catalog/item_revision/repo.py` | ItemRevisionRepository |
| `backend/src/core/catalog/pagination_constants.py` | Pagination limits |
