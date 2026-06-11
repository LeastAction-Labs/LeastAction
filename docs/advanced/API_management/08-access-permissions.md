# Access & Permissions API

**Prefix**: `/api/v1/access`
**Authentication**: Required (Bearer token)

---

## GET `/api/v1/access/get/permission`

Get the permission level a user or group has on a specific item.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_laui` | string | Yes | Item to check permissions on |
| `user_email` | string | Conditional | Email of user to check (provide this or `group_name`) |
| `group_name` | string | Conditional | Name of group to check (provide this or `user_email`) |

At least one of `user_email` or `group_name` must be provided.

### Variation 1: Check User Permission

```
GET /api/v1/access/get/permission?item_laui=507f1f77bcf86cd799439011&user_email=john@example.com
```

### Variation 2: Check Group Permission

```
GET /api/v1/access/get/permission?item_laui=507f1f77bcf86cd799439011&group_name=data-engineers
```

### Variation 3: Check Both User and Group

```
GET /api/v1/access/get/permission?item_laui=507f1f77bcf86cd799439011&user_email=john@example.com&group_name=data-engineers
```

### Success Response

**Status**: 200 OK

```json
{
  "permission": "edit",
  "user_laui": "60d5ecb54b24a67d8c8b4567",
  "group_laui": null
}
```

When checking a group:

```json
{
  "permission": "view",
  "user_laui": null,
  "group_laui": "60d5ecb54b24a67d8c8b9012"
}
```

When no permission exists:

```json
{
  "permission": "none",
  "user_laui": "60d5ecb54b24a67d8c8b4567",
  "group_laui": null
}
```

### Permission Values

| Permission | Description |
|------------|-------------|
| `own` | Full control — can view, edit, delete, and manage access |
| `edit` | Can view and modify the item |
| `view` | Can read the item |
| `delete` | Can delete the item |
| `true_parent_edit` | Can edit as the true parent |
| `is_true_parent` | Check for true parent relationship |
| `none` | No permission |

### Error Responses

**422 Unprocessable Entity** — Neither user_email nor group_name provided
```json
{"detail": "Either one of user_email or group_name must be passed"}
```

**404 Not Found** — User or group not found
```json
{"detail": "User not found"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## GET `/api/v1/access/get/users_groups`

Get all access relations (users and groups) that the current authenticated user has access to.

### Request Example

```
GET /api/v1/access/get/users_groups
```

No query parameters. Uses the authenticated user from the Bearer token.

### Success Response

**Status**: 200 OK

```json
[
  {
    "item_laui": "507f1f77bcf86cd799439011",
    "subject_laui": "60d5ecb54b24a67d8c8b4567",
    "subject_type": "user",
    "subject_permission": "own",
    "item_permission": "own"
  },
  {
    "item_laui": "507f1f77bcf86cd799439011",
    "subject_laui": "60d5ecb54b24a67d8c8b9012",
    "subject_type": "group",
    "subject_permission": "edit",
    "item_permission": "own"
  },
  {
    "item_laui": "60d5ecb54b24a67d8c8baaaa",
    "subject_laui": "60d5ecb54b24a67d8c8b4567",
    "subject_type": "user",
    "subject_permission": "view",
    "item_permission": "view"
  }
]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `item_laui` | string | The item's LAUI |
| `subject_laui` | string | The user or group LAUI |
| `subject_type` | string | `"user"` or `"group"` |
| `subject_permission` | Permission | The subject's permission on the item |
| `item_permission` | Permission | The requesting user's permission on the item |

### Error Responses

**401 Unauthorized** — Not authenticated
```json
{"detail": "Unauthorized"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## Relations vs Permissions

**Relations** define how subjects are connected to resources:

| Relation | Description |
|----------|-------------|
| `owners` | Full control members |
| `editors` | Can modify members |
| `viewers` | Read-only members |
| `true_parent` | Primary parent relationship |
| `false_parents` | Secondary parent relationships |
| `""` (empty) | No specific relation |
| `all` | All relations |

**Permissions** are derived from relations and define what actions are allowed:

| Permission | Derived From |
|------------|--------------|
| `own` | `owners` relation |
| `edit` | `editors` relation (or higher) |
| `view` | `viewers` relation (or higher) |
| `delete` | `owners` relation |
| `true_parent_edit` | `true_parent` relation |
| `is_true_parent` | `true_parent` relation |
