# Group API

**Prefix**: `/api/v1/group`
**Authentication**: Required (Bearer token)

---

## POST `/api/v1/group/create`

Create a new group or update an existing one. If a group with the same name exists and the user has edit/own access, it will be updated instead.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Group name |
| `description` | string | No | Group description |
| `access_patch` | object | No | Access control modifications |

### Access Patch Structure

```json
{
  "add": {
    "owners": {"<user_or_group_laui>": "true"},
    "editors": {"<user_or_group_laui>": "true"},
    "viewers": {"<user_or_group_laui>": "true"}
  },
  "remove": {
    "owners": {"<user_or_group_laui>": "true"},
    "editors": {"<user_or_group_laui>": "true"},
    "viewers": {"<user_or_group_laui>": "true"}
  }
}
```

### Variation 1: Create Basic Group

```json
{
  "name": "data-engineers",
  "description": "Data engineering team"
}
```

The creator is automatically set as an owner.

### Variation 2: Create Group with Access

```json
{
  "name": "analytics-team",
  "description": "Analytics and reporting team",
  "access_patch": {
    "add": {
      "owners": {
        "60d5ecb54b24a67d8c8b4567": "true"
      },
      "editors": {
        "60d5ecb54b24a67d8c8b9012": "true",
        "60d5ecb54b24a67d8c8baaaa": "true"
      },
      "viewers": {
        "60d5ecb54b24a67d8c8bbbbb": "true"
      }
    }
  }
}
```

### Variation 3: Update Existing Group (Add/Remove Members)

If a group named `"data-engineers"` already exists and the user has edit or own access:

```json
{
  "name": "data-engineers",
  "description": "Updated description",
  "access_patch": {
    "add": {
      "editors": {
        "60d5ecb54b24a67d8c8bcccc": "true"
      }
    },
    "remove": {
      "viewers": {
        "60d5ecb54b24a67d8c8bbbbb": "true"
      }
    }
  }
}
```

### Success Response

**Status**: 200 OK

No response body (void).

### Error Responses

**403 Forbidden** — No edit/own access on existing group
```json
{"detail": "Access denied"}
```

**422 Unprocessable Entity** — Validation error
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required"
    }
  ]
}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## GET `/api/v1/group/get`

Get groups filtered by the current user's relation to them.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `relation` | enum | Yes | Filter by relation type |

### Relation Values

| Value | Description |
|-------|-------------|
| `owners` | Groups the user owns |
| `editors` | Groups the user can edit |
| `viewers` | Groups the user can view |
| `false_parents` | Groups with false parent relation |
| `true_parent` | Groups with true parent relation |
| `""` (empty) | No specific relation filter |
| `all` | All relations |

### Variation 1: Get Groups User Owns

```
GET /api/v1/group/get?relation=owners
```

### Variation 2: Get All Groups User Has Access To

```
GET /api/v1/group/get?relation=all
```

### Variation 3: Get Groups User Can Edit

```
GET /api/v1/group/get?relation=editors
```

### Success Response

**Status**: 200 OK

```json
[
  {
    "laui": "507f1f77bcf86cd799439011",
    "name": "data-engineers",
    "description": "Data engineering team",
    "access": {
      "owners": {"60d5ecb54b24a67d8c8b4567": "true"},
      "editors": {"60d5ecb54b24a67d8c8b9012": "true"},
      "viewers": {}
    },
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  {
    "laui": "60d5ecb54b24a67d8c8baaaa",
    "name": "analytics-team",
    "description": "Analytics and reporting team",
    "access": {
      "owners": {"60d5ecb54b24a67d8c8b4567": "true"},
      "editors": {},
      "viewers": {"60d5ecb54b24a67d8c8bbbbb": "true"}
    },
    "created_at": "2024-01-12T09:00:00Z",
    "updated_at": "2024-01-12T09:00:00Z"
  }
]
```

### Error Responses

**422 Unprocessable Entity** — Invalid relation value
```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["query", "relation"],
      "msg": "Input should be 'owners', 'viewers', 'editors', 'false_parents', 'true_parent', '' or 'all'"
    }
  ]
}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## GET `/api/v1/group/get/{group_laui}`

Get a specific group by its LAUI.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `group_laui` | ObjectId | Group's LAUI |

### Request Example

```
GET /api/v1/group/get/507f1f77bcf86cd799439011
```

### Success Response

**Status**: 200 OK

```json
{
  "laui": "507f1f77bcf86cd799439011",
  "name": "data-engineers",
  "description": "Data engineering team",
  "access": {
    "owners": {"60d5ecb54b24a67d8c8b4567": "true"},
    "editors": {"60d5ecb54b24a67d8c8b9012": "true"},
    "viewers": {}
  },
  "created_at": "2024-01-10T08:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Error Responses

**404 Not Found**
```json
{"detail": "Group not found"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## DELETE `/api/v1/group/delete`

Delete a group.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `group_laui` | ObjectId | Yes | Group's LAUI |

### Request Example

```
DELETE /api/v1/group/delete?group_laui=507f1f77bcf86cd799439011
```

### Success Response

**Status**: 200 OK

No response body (void).

### Error Responses

**404 Not Found**
```json
{"detail": "Group not found"}
```

**403 Forbidden** — No delete/own access
```json
{"detail": "Access denied"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```
