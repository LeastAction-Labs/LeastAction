# Users

Users authenticate to LeastAction and are granted access directly or via [groups](/path?laui=getting-started-09-administration-02-groups&itemtype=doc.file&itemname=Groups). The **root** user is created at setup (from `deploy/.env`).

## What you can do
- Create users; set the user type (root / admin / member).
- Grant access to catalog items directly, or (preferred) via a group.
- Manage each user's **MCP tool allow-list** — e.g. disable `delete_item` / `reset_task` for specific users (Admin → MCP Access). See [MCP](/path?laui=getting-started-06-ai-05-mcp&itemtype=doc.file&itemname=Mcp).
- Issue a marketplace access token per user.

## How
Manage users in the UI (Admin), or via the REST API. Full request/response details: [User API](/path?laui=getting-started-10-reference-api-10-user&itemtype=doc.file&itemname=10%20User) and [Authentication](/path?laui=getting-started-10-reference-api-01-authentication&itemtype=doc.file&itemname=01%20Authentication).

## Related
- [Access & Permissions](/path?laui=getting-started-09-administration-01-access-and-permissions&itemtype=doc.file&itemname=Access%20And%20Permissions)
- [Groups](/path?laui=getting-started-09-administration-02-groups&itemtype=doc.file&itemname=Groups)
