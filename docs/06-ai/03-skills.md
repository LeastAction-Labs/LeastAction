# Skills — Guide

A **skill** is a catalog item of type `skill`. Skills contain markdown-formatted instructions that the AI reads during generation or execution. They let you encode reusable context — coding standards, schema definitions, generation rules, domain knowledge — that gets injected into AI prompts without you having to retype it every session.

---

## What Skills Are For

Skills fill two roles:

**During AI generation (Service AI):** When you generate an operator, action, or payload, you can attach one or more skills. The skill content is prepended to the system prompt, so the AI follows your conventions when writing code — table naming patterns, error handling standards, which libraries to use, etc.

**Via MCP (Claude Code):** When connected via MCP, the agent can load and execute skills from the catalog. Built-in skills (Operator Dev, Customer Query, Report, etc.) are shipped as skill items. You can create custom skills and publish them to the marketplace for others to use.

---

## Skill Format

A skill is a markdown file. It can contain:

- Plain instructions ("always use `psycopg2` for PostgreSQL, never `pg8000`")
- Schema descriptions or table definitions
- Example patterns you want the AI to follow
- Provider-specific guidance (e.g., a Claude-specific skill can use Claude's extended thinking features)

Skills can be provider-specific. A skill targeting Claude can use Claude-specific capabilities; a skill targeting GPT-4 can be structured differently. Tag the skill accordingly so users know which AI it is designed for.

---

## Creating a Skill

1. Open the catalog and navigate to the folder where you want to save the skill
2. Create a new item with `item_type: skill`
3. Write the skill content in markdown in the `codeblock` field
4. Save the skill — it is now available in the AI generation UI and any MCP-connected agent

**Example skill — team SQL conventions:**

```markdown
# SQL Conventions

- Always use `schema.table` qualified names, never unqualified table names
- Date partitioning: use `WHERE date_col = '{{ds}}'` with the `{{ds}}` variable
- Prefer `INSERT INTO ... SELECT` over `CREATE TABLE AS SELECT`
- All tables must have a `created_at TIMESTAMP DEFAULT NOW()` column
- Use `LIMIT 1000` in development queries; remove for production
```

---

## Attaching Skills During Generation

In the Service AI interface (`AI > Operator`, `AI > Action`, `AI > Payload`):

1. Before generating, click the **Skills** selector
2. Choose one or more skills from the catalog
3. Generate — the AI applies all selected skill content

Multiple skills are concatenated in order. Keep skills focused on one concern each so they compose well.

---

## Attaching Skills via MCP (Claude Code)

When using Claude Code connected to LeastAction via MCP, skills are referenced by name in your conversation. The MCP agent loads the skill content from the catalog and applies it as generation context — the same way as the Service AI generation wizard, but driven conversationally.

Skills attached this way are scoped to your user permissions. If a skill is not in your accessible items, the agent cannot load it.

---

## Skills in the Report Explorer

Skills serve a third role in the Report Explorer: they wire the AI chat widget to a specific context when users navigate the folder tree.

Set `skill_laui` on a `folder.asset` or report item and the Explorer automatically loads that skill when the user navigates there. The skill tells the AI what data it can access (`inspect_data` tables), which actions it can call (Slack, email, task triggers), and how to behave in that domain.

The resolution order is: **report skill** (overrides all) → **folder skill** (inherits up the folder tree) → **project asset root skill** (general fallback).

This is distinct from generation skills — Explorer skills are written for end users, not for code generation. They describe business context, available actions, and guard rails in plain language.

For the full guide on writing Explorer skills, publishing actions, and wiring `skill_laui` at setup time, see [asset.md — Wiring AI Skills to Folders and Reports](/path?laui=getting-started-07-working-in-the-ui-01-assets-and-reports&itemtype=doc.file&itemname=Assets%20And%20Reports).

---

## Publishing Skills to the Marketplace

Skills can be published like any other catalog item:

1. Open the skill in the catalog
2. Click **Publish**
3. Fill in version, category, tags, and description
4. Submit — the skill appears in the marketplace

Published skills can be imported by other LeastAction users. This is how built-in LeastAction skills (Operator Dev, Customer Query, etc.) are distributed.

---

## Built-in Skills

The following skills are available from the LeastAction official marketplace:

| Skill | Purpose |
|---|---|
| Operator Dev | Guides operator generation following the 4-method contract |
| Customer Query | Generates customer-facing query operators |
| Report | Generates HTML report output operators and actions |
| Run Action | Generates actions that run other actions or tasks |
| Send Slack | Generates Slack notification actions |
| Send Email | Generates email notification actions |

Import these from the marketplace and attach them during generation to get output that follows LeastAction's conventions out of the box.
