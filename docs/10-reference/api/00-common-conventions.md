# Common Conventions

## Base URL

```
{scheme}://{host}/api/v1
```

Default local development: `http://localhost:8000/api/v1`

## Authentication

LeastAction uses **dual authentication** for different endpoint types:

### User Authentication (Standard)

Protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

This token identifies the user making the request and is used for permission checks.

### System Authentication (Internal)

System-only endpoints require **both** a Bearer token and a system authentication header:

```
Authorization: Bearer <access_token>
X-System-Auth-Token: <system_jwt>
```

The `X-System-Auth-Token` proves the request originates from trusted infrastructure (Celery workers, cron schedulers).

**System-Only Endpoints:**

- `POST /api/v1/task/update/{task_laui}`
- `POST /api/v1/task/finish/{task_laui}`
- `GET /api/v1/catalog/get/tasks_ready_to_run/{project_laui}`

See [Security & Authorization](13-security.md) for details.

### Protected Routes

The following route prefixes require authentication:

- `/api/v1/catalog/`
- `/api/v1/check/`
- `/api/v1/access`
- `/api/v1/group`
- `/api/v1/task`
- `/api/v1/action`
- `/api/v1/cron/`
- `/api/v1/user`
- `/api/v1/marketplace`

### Public Routes

- `/api/v1/auth/*` (signup, login, token, logout, etc.)
- `/api/v1/ai/*`
- `/api/v1/logs/*`
- `/api/v1/health`
- `/`

### Unauthorized Response

```json
// 401 Unauthorized
{ "detail": "Unauthorized" }
```

```json
// 401 Unauthorized (missing system token)
{
  "message": "Unauthenticated",
  "detail": "Missing X-System-Auth-Token"
}
```

## ObjectId (LAUI)

Items are identified by a **LAUI** (Least Action Universal Identifier), which is a MongoDB ObjectId — a 24-character hexadecimal string.

```
Example: "507f1f77bcf86cd799439011"
```

## Error Response Format

All errors follow a consistent structure:

```json
{
  "detail": "<string or object>"
}
```

The `detail` field can be either a plain string message or a structured object depending on the error type.

### Exception Hierarchy

| Exception                     | HTTP Status | When                                            |
| ----------------------------- | ----------- | ----------------------------------------------- |
| `InvalidArgumentError`        | 400         | Invalid request parameters                      |
| `AuthorizationError`          | 403         | Insufficient permissions                        |
| `NotFoundError`               | 404         | Resource not found                              |
| `ConflictError`               | 409         | Duplicate resource or state conflict            |
| `UnprocessableEntityError`    | 422         | Business logic validation failure               |
| `SchemaError`                 | 422         | Schema validation failure                       |
| `InvalidOperatorError`        | 422         | Operator is invalid or missing required methods |
| `PartialGenerationError`      | 206         | AI generation partially completed               |
| `AIError`                     | 500         | AI provider failure                             |
| `CeleryExecutionError`        | 500         | Task execution failure                          |
| `OperationFailure (code 112)` | 503         | MongoDB write conflict                          |

### Error Examples

**400 Bad Request**

```json
{ "detail": "either one of item_laui or is_root must be passed" }
```

**400 Bad Request (structured)**

```json
{
  "detail": {
    "issue": "invalid pagination params passed",
    "expected pagination params": {
      "per_page": { "min": 0, "max": 1000 },
      "page": { "min": 1 }
    }
  }
}
```

**403 Forbidden**

```json
{ "detail": "Access denied" }
```

**404 Not Found**

```json
{ "detail": "Item not found" }
```

**409 Conflict**

```json
{ "detail": "User already exists" }
```

**422 Unprocessable Entity (schema validation)**

```json
{
  "detail": {
    "summary": "errors found in operator.json",
    "validation_context": {
      "name": "regex pattern ^[a-zA-Z0-9_\\-]+\\.operator$ not matched"
    }
  }
}
```

**422 Unprocessable Entity (hierarchy)**

```json
{
  "detail": {
    "message": "invalid item_type for the passed parent_laui",
    "item_type_passed": "task",
    "allowed_item_types": ["folder.workflow", "config"]
  }
}
```

**503 Write Conflict**

```json
{ "detail": "write_conflict" }
```

## Pagination

### Request Parameters

| Parameter    | Type   | Default | Constraints         | Description                       |
| ------------ | ------ | ------- | ------------------- | --------------------------------- |
| `page`       | int    | 1       | min: 1              | Page number                       |
| `per_page`   | int    | 10      | min: 0, max: 1000   | Items per page                    |
| `sort_order` | string | —       | `"asc"` or `"desc"` | Sort direction                    |
| `page_token` | string | —       | —                   | Token for cursor-based pagination |

### Response

```json
{
  "items": [...],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "has_next": true,
    "next_page_token": "eyJ..."
  }
}
```

## Server-Sent Events (SSE)

The `/api/v1/logs/*` endpoints return SSE streams with `Content-Type: text/event-stream`.

### SSE Format

```
event: <event_type>
data: <JSON>

```

### Common SSE Events

| Event      | Description                |
| ---------- | -------------------------- |
| `status`   | Processing state indicator |
| `data`     | Main data payload          |
| `metadata` | File/resource metadata     |
| `chunk`    | Partial content chunk      |
| `log`      | Single log entry           |
| `done`     | Stream completion signal   |
| `error`    | Error occurred             |

### SSE Headers

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

## Access Control

The system uses **Keto** for permission management.

### Relations

| Relation        | Description                    |
| --------------- | ------------------------------ |
| `owners`        | Full control over the resource |
| `editors`       | Can modify the resource        |
| `viewers`       | Can view the resource          |
| `true_parent`   | Primary parent relationship    |
| `false_parents` | Secondary parent relationships |

### Permissions

| Permission         | Description             |
| ------------------ | ----------------------- |
| `view`             | Read access             |
| `edit`             | Write access            |
| `own`              | Full control            |
| `delete`           | Can delete the resource |
| `true_parent_edit` | Can edit as true parent |
| `is_true_parent`   | Check if true parent    |
