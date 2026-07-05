# Claude Code + MCP — Setup Guide

Connect Claude Code to your LeastAction instance so you can manage catalog items, run tasks, debug failures, and query pipeline status directly from your terminal or IDE.

---

## How It Works

LeastAction exposes an MCP (Model Context Protocol) server over streamable HTTP at `/mcp/`. When connected, Claude Code has access to 25+ catalog tools — search, run, debug, create, and manage items — scoped to your user permissions. The connection is authenticated with a JWT bearer token issued by your LeastAction instance.

### Multi-user model

`.mcp.json` is a **local file on each developer's laptop** — not a shared file on the server. Every developer on your team has their own copy with their own personal bearer token pointing at the shared backend. The server authenticates each connection independently and scopes all tool calls to that user's catalog permissions.

```
Developer A laptop              Developer B laptop
.mcp.json  ← token A            .mcp.json  ← token B
      │                                │
      └──── HTTP ──→  https://something.com/mcp/  ←── HTTP ────┘
                              │
                     MCPAuthMiddleware
                     validates token → resolves user identity
                     all tools scoped to that user's permissions
```

**`.mcp.json` must never be committed to git** — it contains a personal token. Add it to `.gitignore`:

```
.mcp.json
```

Each developer generates their own by running the login flow. The file is never shared.

---

## Prerequisites

- LeastAction backend running (locally via Docker Compose or remotely)
- Claude Code installed — [claude.ai/code](https://claude.ai/code)
- A LeastAction user account (created by your admin via the UI or `setup.py`)

---

## Login (one-time setup)

**Step 1 — Log in to your LeastAction instance** (local: `http://localhost:5173`, remote: your deployment URL).

**Step 2 — Open the MCP token page:**

Navigate to **Settings → Claude Code** (top-right menu), or go directly to `/mcp-token`.

**Step 3 — Copy the `.mcp.json` snippet** shown on the page and paste it into `.mcp.json` at your project root.

**Step 4 — Restart Claude Code.** The `leastaction` server will show as connected.

Tokens are valid for 24 hours. Return to the same page to get a fresh snippet after re-logging in.

---

## What Gets Written

After login, `.mcp.json` at the project root will look like:

```json
{
  "mcpServers": {
    "leastaction": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

Tokens are valid for 24 hours. Return to the `/mcp-token` page to get a fresh snippet.

---

## Available MCP Tools

### Access & Schema

| Tool | Description |
|------|-------------|
| `get_my_access` | See which tools are enabled for your account |
| `get_item_schema` | Get the JSON schema for an item type (task, operator, action, connection, payload, config, folder, chat, agent, skill) |

### Documentation

| Tool | Description |
|------|-------------|
| `list_docs` | List all available documentation and AI prompt files |
| `get_doc` | Read a documentation or AI prompt file by its relative path |

### Search & Retrieve

| Tool | Description |
|------|-------------|
| `search_catalog` | Search items by type (task, operator, action, connection, payload, config, folder.workflow, chat, agent, skill, html_report), optionally filter by name or parent |
| `get_catalog_item` | Fetch full item details by LAUI |
| `get_item_by_pk` | Fetch an item by its primary key fields (faster than search when all PK fields are known) |
| `get_root_items` | List top-level (root) catalog items |
| `get_children` | List children of a parent item, optionally filtered by item_type |

### Create / Link / Delete

| Tool | Description |
|------|-------------|
| `create_catalog_item` | Create a new catalog item (reads creation rules and schema first) |
| `create_link` | Create a soft link (parent-child relationship) between two items |
| `delete_item` | Delete a catalog item (soft delete to trash by default, or hard delete) |
| `restore_item` | Restore a previously deleted item from trash |

### Task Execution & Management

| Tool | Description |
|------|-------------|
| `run_task` | Run a task by LAUI |
| `update_task` | Update task fields (state, user_set_state, logical_date, priority, etc.) |
| `reset_task` | Reset a task back to 'scheduled' state (use with caution) |
| `get_task_status` | Get current state, last_run_session_id, and prev_interval_start for a task |
| `get_task_history` | Get all past runs for a task — session_id, status, duration, output, date range |
| `get_task_logs` | Fetch full parsed execution logs for a specific session |
| `list_session_log_files` | List all log files available for a session (use before `read_log_file`) |
| `read_log_file` | Read a specific log file by path (paginated, newest lines last) |

### Actions

| Tool | Description |
|------|-------------|
| `run_action` | Execute a standalone action by its LAUI, with optional connection and action_variables |

### Marketplace

| Tool | Description |
|------|-------------|
| `search_marketplace` | Search the marketplace for reusable operators, actions, payloads, skills, and usecases — filter by name, item_type, publisher, category, division, or tags |
| `get_marketplace_item` | Get full details of a marketplace item by its LAUI |

All tools enforce your catalog permissions — you can only access and operate on items your token grants.

---

## Debugging Task Failures

The standard flow to debug a failed task:

**Step 1 — Find the failed session**

```
get_task_history(task_laui="<laui>")
```

Returns all past runs sorted newest-first. Each entry has:
- `session_id` — unique ID for that run
- `status` — `success`, `error`, `cancelled`
- `output` — run output or error message
- `prev_interval_start` — the logical date the task ran for (use the `YYYY-MM-DD` portion as `date` in the next step)
- `start_time`, `duration_seconds`

**Step 2 — Fetch the execution logs**

```
get_task_logs(
  task_laui="<laui>",
  session_id="<session_id from step 1>",
  date="<YYYY-MM-DD from prev_interval_start>"
)
```

Returns every log line for that session, parsed as JSON with `timestamp`, `level`, `step`, `message`, `operation`. Use `tail=50` to return only the last N lines.

> **Why `prev_interval_start` and not `last_run_date`?**
> Tasks always execute for a past interval — logs are stored under the *logical date* of that interval, not the actual wall-clock date the task ran. If you pass the wrong date, logs won't be found.

**Example**

```
get_task_history(task_laui="6a03ef89...")
→ session_id: "ee952d3b", status: "error", prev_interval_start: "2026-05-11T00:00:00"

get_task_logs(task_laui="6a03ef89...", session_id="ee952d3b", date="2026-05-11")
→ [
    { "step": "extracting_connection_details", "level": "info", ... },
    { "step": "creating_connection",           "level": "info", ... },
    { "step": "postgresql_error",              "level": "error",
      "message": "Connection refused — Is the server running on port 5432?" }
  ]
```

**Alternative — browse raw log files**

If you need to explore what log files exist for a session:

```
list_session_log_files(session_id="<session_id>")
→ { "logs": [{ "path": "verbose=TASK/...", "name": "...", "size": ... }] }

read_log_file(file_path="<path from above>")
→ { "content": "...", "total_lines": 12, "has_more": false }
```

---

## Per-User Tool Access Control

Admins can restrict which MCP tools each user can call. By default all tools are enabled. When a tool is disabled for your account, calling it returns an error instead of executing.

### For admins — managing tool access

1. Go to **Admin → MCP Access** tab
2. Find the user and click the edit (pencil) icon
3. Check or uncheck individual tools, then click **Save**

Unchecking all tools blocks the user from all MCP tool calls. Checking all tools restores full access (stored as "no restriction" — the user automatically picks up any new tools added in future releases).

**Note:** The root/admin account is subject to the same restrictions as any other user. If you want to protect yourself from accidental destructive operations (e.g. `delete_item`, `reset_task`), uncheck those tools for your own account.

### For users — checking your own access

Call `get_my_access` at any time to see exactly which tools are enabled for your account:

```
get_my_access
```

Returns:

```json
{
  "user_laui": "...",
  "is_root_user": false,
  "has_full_access": false,
  "allowed_tools": ["search_catalog", "get_catalog_item", "list_docs", ...]
}
```

If a tool you expect is missing from `allowed_tools`, contact your admin to enable it.

---

## Troubleshooting

**401 Unauthorized from MCP tools**
Your token may have expired (24-hour TTL). Go to `/mcp-token`, copy the fresh snippet, update `.mcp.json`, and restart Claude Code.

**Claude Code shows MCP server as disconnected**
Ensure the backend is running and the URL in `.mcp.json` is correct (`http://localhost:8000/mcp/` for local, your deployment URL for remote).
