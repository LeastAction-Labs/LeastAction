# Glossary

| Term | Meaning |
|---|---|
| **Item** | Any first-class object in the catalog (operator, connection, payload, config, action, task, folder, report, asset, skill, agent, chat, usecase, table). |
| **Catalog** | The folder hierarchy that holds all items — the shared context the AI and the team work from. |
| **laui** | LeastAction Unique Identifier — the id of any catalog item. |
| **Operator** | Python code defining *how* a task runs (4 methods: `initialize`, `run`, `check_completion`, `finish`). |
| **Connection** | Credentials + resource config + concurrency controls for an external system. |
| **Payload** | The task-specific input (SQL, JSON, Python, string). |
| **Config** | Defaults, schedule, retries, SLA, parameters — shared via an N-level hierarchy with locked/overridable values. |
| **Action** | Reusable Python that runs at a lifecycle hook (pre / running / post / UI). |
| **Task** | An instance: connection + operator + payload (+ config + actions), run on a schedule or on demand. |
| **Workflow** | A folder of related tasks. |
| **Partition** | A dimension of a task's primary key — same name + project + different partition = an independent instance. |
| **logical_date** | The data period a run computes, injected as `{{ds}}` / `{{logical_date}}`. |
| **next_run_date** | The scheduler trigger time; the cron fires when `next_run_date ≤ now`. |
| **Backfill** | Running a task for historical dates by assigning past `logical_date`s. |
| **Catch-up** | Automatic replay of missed cron slots after an outage/backfill, one logical date at a time. |
| **Skill** | A markdown knowledge item the AI reads during generation or in the Report Explorer. |
| **Usecase** | A bundled pipeline blueprint (payloads + skills) an AI agent can read and implement; the runnable examples live in `ai/usecases`. |
| **Agent** | A conversational AI item that backs the chat widget (optional MCP tool-calling). |
| **Chat** | The AI item that powers the generation wizard (`AI > Operator/Action/Payload`). |
| **MCP** | Model Context Protocol — connect Claude Code / any MCP client to the catalog with your own AI subscription. |
| **Report Explorer** | The business-user UI: ask in plain English, read live reports; skill-driven and permission-scoped. |
| **Marketplace** | Where you discover, import, and publish operators, actions, payloads, skills, and usecases. |

See also: [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) and the [Concepts](/path?laui=getting-started-04-concepts-01-items-and-catalog&itemtype=doc.file&itemname=Items%20And%20Catalog) section.
