# Marketplace API

**Prefix**: `/api/v1/marketplace`
**Authentication**: Required (Bearer token)

---

## POST `/api/v1/marketplace/import`

Import an item from the external Marketplace service and create it in the local catalog.

### Prerequisites

The user must have a marketplace access token stored. Use [POST /user/marketplace/token](/path?laui=getting-started-10-reference-api-10-user&itemtype=doc.file&itemname=10%20User#post-apiv1usermarketplacetoken) to set one.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `marketplace_item_id` | string | Yes | ID of the item in the Marketplace |
| `parent_laui` | string | Yes | LAUI of the parent folder to import into |

### Request Example

```json
{
  "marketplace_item_id": "mkt_item_a1b2c3d4e5f6",
  "parent_laui": "507f1f77bcf86cd799439011"
}
```

### Import Process

1. Validates the user has a marketplace access token
2. Calls the Marketplace API: `GET /api/v1/marketplace/catalog/item/{marketplace_item_id}`
3. Converts the marketplace item to the local format:
   - Preserves `item_type`, `name`, and all content fields
   - Sets `parent_laui` to the provided value
   - Sets `is_root` to `false`
   - Strips internal fields: `_id`, `laui`, `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `version`
4. Creates the item via the catalog create pipeline (with full schema validation)

### Success Response

**Status**: 200 OK

```json
{
  "item_laui": "60d5ecb54b24a67d8c8b9012",
  "message": "Item imported successfully from Marketplace"
}
```

### Error Responses

**400 Bad Request** — No marketplace token stored
```json
{"detail": "Marketplace access token not found. Please connect to Marketplace first."}
```

**401 Unauthorized** — User not authenticated
```json
{"detail": "User not authenticated"}
```

**401 Unauthorized** — Invalid marketplace token
```json
{"detail": "Invalid Marketplace access token"}
```

**404 Not Found** — Item not found in Marketplace
```json
{"detail": "Item not found in Marketplace"}
```

**422 Unprocessable Entity** — Schema validation failure during local create
```json
{
  "detail": {
    "summary": "errors found in operator.json",
    "validation_context": {
      "name": "required field missing"
    }
  }
}
```

**500 Internal Server Error** — Marketplace connection failure
```json
{"detail": "Error connecting to Marketplace: Connection refused"}
```

**500 Internal Server Error** — Marketplace API error
```json
{"detail": "Error fetching item from Marketplace: Internal server error"}
```

**500 Internal Server Error** — Generic error
```json
{"detail": "Internal server error: <message>"}
```

---

## Imported Item Types

The following item types can be imported from the Marketplace:

- `operator` — Reusable task operators
- `action` — Executable actions
- `payload` — Payload templates
- `config` — Configuration templates
- `connection` — Connection templates

The imported item's `item_type` is preserved from the Marketplace source. The `parent_laui` must point to a folder that supports the item type (see [Catalog Hierarchy](/path?laui=getting-started-04-concepts-01-items-and-catalog&itemtype=doc.file&itemname=Catalog%20Hierarchy)).
