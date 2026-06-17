# LeastAction AI — Technical Overview

LeastAction has three distinct AI modes. Each serves a different purpose and cost model. In all three, permissions are enforced — users can only access, run, and edit items they have permission to.

---

## AI Item Types

Three catalog item types power the AI layer:

| Item type | Purpose |
|---|---|
| `chat` | Powers the **generation wizard** — structured-output LLM invocation. Drives `AI > Operator`, `AI > Action`, `AI > Payload`. Uses `with_structured_output`. |
| `agent` | Powers the **chat widget** — conversational LLM with optional MCP tool-calling. Uses `bind_tools`. Selected when starting a chat session. |
| `skill` | Injects context into any AI prompt. A markdown file the AI reads before generating or responding. |

These are flat, first-class item types in the catalog. They live under `folder.ai`. `ai_chat` and `ai_skill` are not item types — the correct types are `chat`, `agent`, and `skill`.

---

## Mode 1 — Service AI (Built-in Generator)

This is the AI embedded directly in the LeastAction service, accessed from the UI. It generates operators, actions, payloads, and AI agent code from natural language descriptions.

**Where to access:** `AI > Operator`, `AI > Action`, `AI > Payload`, `AI > AI Chat`, `AI > AI Agent` in the UI

**Supported providers:** Anthropic, OpenAI, Gemini — selected per `connection` item linked to the `chat` configuration.

### What it generates

**Operators** — Python code with a 4-method contract to manage task lifecycle. See [Operator Guide](/path?laui=getting-started-advanced-task_managment-operator&itemtype=doc.file&itemname=Operator) for details.

**Actions** — Python with a single `run` method that executes at a task lifecycle point. See [Action Guide](/path?laui=getting-started-advanced-task_managment-action_aka_hook&itemtype=doc.file&itemname=Action%20Aka%20Hook) for details.

**Payloads** — Any format the operator expects: JSON, SQL, Python, plain string. See [Payload Guide](/path?laui=getting-started-advanced-task_managment-payload&itemtype=doc.file&itemname=Payload) for details.

**AI Chat (`chat`)** — The LLM invocation module that drives the generation wizard. Produces `run(connection, messages)` code using `with_structured_output`.

**AI Agent (`agent`)** — A conversational agent with optional MCP tool-calling. Produces `run(connection, messages, tools=None)` code using `bind_tools`. Once saved, the agent appears in the chat widget's agent selector.

### Skills during generation

When generating, users can **attach skills** — catalog items (`item_type: "skill"`) that inject additional context into the prompt. For example, a skill might contain your internal conventions, a description of your data schema, or generation rules for a specific operator type. The AI follows the skill content when writing the code.

### Session management

Generation sessions are stateful. Users can **resume a previous session** from their user page — picking up the conversation where it left off, continuing to refine the operator or action without starting over.

---

## Mode 2 — Claude Code + MCP (Built-in)

The LeastAction MCP server is built into every instance. Connect any MCP-compatible AI client — Claude Code, claude.ai, or any tool that supports the Model Context Protocol — and get direct, conversational access to catalog operations using your own AI subscription.

**How it works:**
- Log in to your LeastAction instance and navigate to **Settings → Claude Code** (or `/mcp-token`) to copy your personal `.mcp.json` snippet
- Paste it into your project root and restart Claude Code — the `leastaction` MCP server connects immediately
- Every user has their own token; the server scopes all tool calls to that user's catalog permissions

**What you can do with it:**
- Browse and search the catalog conversationally
- Generate and deploy operators end-to-end (describe → generate → run → debug, automatically)
- Run tasks and actions by name
- Retrieve and render HTML reports
- Trigger Slack notifications, emails, and other actions
- Ask questions about pipeline status and get real answers from live data
- Ask what items and pipelines you have access to — `get_my_access` returns your tool permissions and `search_catalog` is scoped to your readable items
- Search the marketplace for reusable operators, actions, payloads, skills, and usecases

**Skills via MCP:** Skills are catalog items that define specific AI behaviors — what actions to run, what data to fetch, what to return. Engineers publish skills; the MCP agent loads and executes them when triggered.

For setup instructions and the full tool reference see the [MCP Setup Guide](/path?laui=getting-started-advanced-AI_managment-mcp&itemtype=doc.file&itemname=MCP).

---

## Mode 3 — Built-in Service Chat (Chat Widget)

The LeastAction service includes an embedded chat interface driven by an **`agent`** item the user selects. This is the embedded conversational path — the AI runs within the service, using an agent (e.g. `AnthropicAgent` with `api_key` and `model`) that the user has set up in the catalog.

**How it works:**
- The user creates an `agent` item (e.g. via `AI > AI Agent` in the generation wizard, or manually in the catalog)
- From the chat widget, the user selects their `agent` and a `connection` to start a session
- The agent handles conversation history and can invoke MCP tools if enabled

**When to use this:** When you want conversational AI embedded in the service web UI — for example, asking questions about pipelines, running actions by name, or querying data in natural language.

**Cost model:** API calls are made using the selected `connection`'s credentials. The team controls which model and API key is used, and can rotate or restrict it via the agent's permissions.

---

## Mode 4 — Report Explorer (Embedded Skill Context)

The Report Explorer is a separate UI mode for non-technical users. It surfaces reports, BI dashboards, and an AI chat widget in a clean folder-browsing interface — no pipeline UI, no catalog management.

AI in the Explorer works differently from the three modes above: it is **skill-driven and context-aware**. Engineers attach `skill` items to folders and reports in the catalog. When a user navigates to a folder or opens a report, the chat widget automatically loads the relevant skill — no model or connection selection required from the user.

The skill Markdown defines everything the AI is allowed to do in that context: what data it can query (`inspect_data`), which actions it can trigger (`run_action`, `run_task`), and what questions it can answer. Engineers publish actions (Slack notifications, email delivery, report refresh tasks) and declare them in the skill — users invoke them in plain English.

**Skill inheritance:** report skill overrides folder skill; folder skill inherits from parent folders up to the project asset root. No skill at a level means inheriting from the level above.

For the user-facing guide see [AI_explore_intro.md](../AI_explore_intro.md). For how to build actions and wire skills to folders and reports see [asset.md](advanced/UI_management/asset.md).

---

## Permissions Across All Modes

Regardless of which AI mode is used, the same catalog permissions apply:

- Users see and can interact with only the items they have access to
- `search_catalog` and `get_children` return only items the user can read
- `run_task` and `run_action` require execute permission on the item
- `create_catalog_item` requires write permission on the parent folder
- Skills are permissioned like any catalog item — publishing a skill to a group restricts who can trigger it

The AI cannot bypass catalog permissions. If a user asks about something outside their access, the response is a clear denial — not a data leak.

---

## Summary — When to Use Which Mode

| Mode | Who uses it | Entry point | AI controlled by |
|---|---|---|---|
| Service AI | Engineers | `AI > Operator / Action / Payload` | `chat` item + skills |
| Claude Code + MCP | Engineers | `.mcp.json` + Claude Code | User token + MCP tool allow-list |
| Service Chat | Engineers | Chat widget, agent selector | `agent` item in catalog |
| Report Explorer | Business users | Explorer View at login | Skill attached to folder/report |

---

## Further Reading

- [Task Intro](/path?laui=getting-started-task_intro&itemtype=doc.file&itemname=Task%20Intro) — Creating and scheduling tasks
- [Operator Guide](/path?laui=getting-started-advanced-task_managment-operator&itemtype=doc.file&itemname=Operator) — Operator structure and the 4-method contract
- [Action Guide](/path?laui=getting-started-advanced-task_managment-action_aka_hook&itemtype=doc.file&itemname=Action%20Aka%20Hook) — Action lifecycle and the run method
- [MCP Setup Guide](/path?laui=getting-started-advanced-AI_managment-mcp&itemtype=doc.file&itemname=MCP) — Connecting Claude Code via MCP, tool reference, and per-user access control

---

> **Security warning — read before connecting MCP to any live environment:**
>
> - **Never point MCP at production.** Create a dedicated connection and project scoped specifically for MCP use. Production databases, warehouses, and APIs should remain completely out of reach.
> - **Enforce the principle of least privilege.** Disable every MCP tool your workflow doesn't require. If you don't need `run_task`, `create_catalog_item`, or `delete_item` — turn them off from **Admin → MCP Access**. An AI session should never have broader rights than a junior read-only analyst.
> - **AI-generated SQL and code runs exactly as written.** There is no sandbox, no dry-run, and no undo. If an AI writes a `DELETE` or `DROP` statement against a live connection, it executes. Treat every AI-initiated action like a production deploy — review before it runs.
> - **Rotate and revoke tokens regularly.** MCP tokens have the same power as the user they belong to. Treat them like API keys: store them in a secrets manager, never in dotfiles or version control, and revoke them the moment they're no longer needed.
> - **Audit AI actions like you audit human ones.** LeastAction logs every task run and catalog change. Review those logs. If something looks wrong, investigate — don't assume the AI "knew what it was doing."
> - **Be especially careful with connections that have write or execute access.** A read-only reporting connection is low risk. A connection that can INSERT, UPDATE, invoke Lambda, or send messages is not. Scope accordingly.
