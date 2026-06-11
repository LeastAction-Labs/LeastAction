# User API

**Prefix**: `/api/v1/user`
**Authentication**: Required (Bearer token)

---

## POST `/api/v1/user/marketplace_access_token/update`

Update the marketplace access token for the current authenticated user. This token is used to authenticate with the external Marketplace service for importing items.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `marketplace_access_token` | string | Yes | Access token from the Marketplace platform |

### Request Example

```json
{
  "marketplace_access_token": "mp_tk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

### Success Response

**Status**: 200 OK

```json
{
  "message": "Marketplace access token updated successfully",
  "user_id": "507f1f77bcf86cd799439011"
}
```

### Error Responses

**401 Unauthorized** — User not authenticated
```json
{"detail": "User not authenticated"}
```

**404 Not Found** — User not found
```json
{"detail": "User not found"}
```

**422 Unprocessable Entity** — Missing field
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "marketplace_access_token"],
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

## GET `/api/v1/user/marketplace_access_token/get`

Retrieve the marketplace access token stored for the current authenticated user.

### Request Example

```
GET /api/v1/user/marketplace_access_token/get
```

No query parameters required.

### Success Response

**Status**: 200 OK

```json
{
  "marketplace_access_token": "mp_tk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

Returns `null` for `marketplace_access_token` if no token has been stored yet.

### Error Responses

**401 Unauthorized** — User not authenticated
```json
{"detail": "User not authenticated"}
```

**404 Not Found** — User not found
```json
{"detail": "User not found"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## GET `/api/v1/user/me`

Get the current authenticated user's profile.

### Request Example

```
GET /api/v1/user/me
```

### Success Response

**Status**: 200 OK

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "chat_agent_laui": "507f1f77bcf86cd799439011",
  "chat_connection_laui": "60d5ecb54b24a67d8c8b4567",
  "chat_agent_name": "My Agent"
}
```

Fields `chat_agent_laui`, `chat_connection_laui`, and `chat_agent_name` may be `null` if not configured.

### Error Responses

**401 Unauthorized** — User not authenticated
```json
{"detail": "User not authenticated"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```

---

## POST `/api/v1/user/change-password`

Change the current user's password. Required on first login when `must_change_password` is `true`.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_password` | string | Yes | The user's existing password |
| `new_password` | string | Yes | The new password to set |

### Request Example

```json
{
  "current_password": "oldPassword123",
  "new_password": "newSecurePassword456"
}
```

### Success Response

**Status**: 200 OK

```json
{
  "message": "Password changed successfully"
}
```

### Error Responses

**401 Unauthorized** — User not authenticated or current password wrong
```json
{"detail": "User not authenticated"}
```

**500 Internal Server Error**
```json
{"detail": "Internal server error: <message>"}
```
