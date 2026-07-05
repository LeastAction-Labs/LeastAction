# Usecase — Guide

A **usecase** is a catalog item of type `usecase` that bundles a complete, reusable pipeline definition: payload files (SQL, Python, config), optional AI skill files, scheduling metadata, and dependency chains. Usecases let you package and share multi-step pipelines so they can be deployed to any workspace with minimal configuration.

---

## What Usecases Are For

A usecase encodes a pipeline pattern — not running tasks, but the blueprint for creating them. Once deployed, each payload in the usecase becomes a scheduled task in your catalog.

Common uses:
- Distribute a standard ETL pattern (e.g. extract → transform → load → report) that teams can adapt to their own connections and schemas
- Share a tested pipeline structure via the marketplace so others can import and deploy it
- Capture a pipeline design alongside its AI skill context so the generation inputs are preserved for future modification

---

## Usecase Structure

A usecase stores three parallel dictionaries, all keyed by a shared filename stem with a zero-padded step prefix (`00_`, `01_`, `02_`, …):

| Dict | Key format | Value |
|---|---|---|
| `payloads` | `00_step_name.sql` / `.py` | Full file content — header comment block + SQL or Python body |
| `skills` | `00_step_name.md` | AI skill instructions for that step (optional per step) |

Steps that do not need a skill omit that key from `skills`. The stem must match exactly across dicts for the same step.

### Name constraint

The `name` field must end with `.usecase` and contain only alphanumeric characters, hyphens, and underscores:

```
my-pipeline.usecase
sales_cube_daily.usecase
```

### Unique constraint

Usecases are unique by `name` + `publisher`. In the core catalog, `publisher` is the workspace owner.

---

## Payload Header Format

Every payload file inside a usecase begins with a JSON comment block that carries the scheduling and operator metadata for that step:

```sql
/*
{
  "name": "00_step.sql",
  "frequency": "0 * * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "00_previous_step.sql"
            }
          ]
        }
      }
    ]
  }
}
*/
SELECT ...
```

**Key header fields:**

| Field | Description |
|---|---|
| `operator_name` | Catalog operator the task will use — must exist in core before deploying |
| `connection_name` | Connection the task will use — must exist in core before deploying |
| `frequency` | Cron expression for the task schedule |
| `start_date` / `end_date` | Schedule window — override at deploy time |
| `partition` | Runtime partition value — usually `{{partition}}` template variable |
| `actions.pre_actions` | Dependency chain — step 0 has none; each subsequent step waits on the previous |

Fields with `{{...}}` are template variables resolved at runtime. Do not hard-code values for `account_laui`, `project_laui`, or `partition` — leave them as templates.

---

## Dependency Chain Rules

- **Step 0:** no `pre_actions`
- **Step N (N > 0):** one `LeastActionCheckIfParentsAreDone` pre-action pointing to step N−1's filename
- All `account_laui`, `project_laui`, `partition` references use `{{...}}` template variables

This ensures tasks run in order and each step waits for the previous one to complete for the same logical date.

---

## Deploying a Usecase

Deploying reads the usecase item and creates one task per payload in a target workflow. There is no import API — payloads are read directly and tasks are created individually.

The MCP agent **Usecase Deploy Skill** automates this. Trigger it with: *"deploy usecase X"*, *"create tasks from usecase X"*, or *"use this usecase"*.

### Three deploy patterns

**Pattern 1 — Payloads as-is:** The usecase has `payloads` and you want to run them with only connection and date overrides. The skill presents a step table, asks for confirmation, then creates one task per payload in order.

**Pattern 2 — Payloads adapted by skills:** The usecase has both `payloads` and `skills`. The skill reads the matching skill file for each step and applies its guidance (schema changes, connection rules, business logic) before creating the task.

**Pattern 3 — Skills only:** The usecase has only `skills` (a knowledge bundle). The skill uses those files as generation context to build new payloads from scratch, then creates the tasks.

### Prerequisites

Before deploying, the following must exist in your core catalog:
- Every `operator_name` referenced in the payload headers
- Every `connection_name` referenced in the payload headers
- The target workflow folder

If any prerequisite is missing, the deploy stops and reports what is absent.

---

## Importing from the Marketplace

Usecases published to the marketplace can be browsed, inspected, and imported into your catalog. See the [Marketplace guide](/path?laui=getting-started-07-working-in-the-ui-03-marketplace&itemtype=doc.file&itemname=Marketplace) for details on browsing, filtering, and importing items.

Once imported, the usecase lives in your catalog and can be deployed using the Usecase Deploy Skill or inspected and modified directly.

---

## Creating a Usecase

Use the MCP agent **Usecase Creation Skill**: *"create a usecase for X"* or *"build me a pipeline for X"*.

The skill will:
1. Ask for your data sources, targets, and which operators/connections exist in core
2. Search for similar usecases in the marketplace as a structural reference
3. Present a step table for confirmation before creating anything
4. Generate payload files with correct headers and dependency chains
5. Create the usecase item in your catalog with `payloads`, `skills`, `guide_docs`, and `prompt` fields populated

You can also create a usecase manually via `create_catalog_item`:

```
create_catalog_item(
  name="my-pipeline.usecase",
  item_type="usecase",
  parent_laui="<folder_laui>",
  extra_fields={
    "description": "What this pipeline does",
    "prompt": "Verbatim user request + skill content used as input",
    "guide_docs": "<markdown guide covering steps, template variables, prerequisites>",
    "payloads": {
      "00_step_one.sql": "/*\n{...header...}\n*/\nSELECT ...",
      "01_step_two.sql": "/*\n{...header...}\n*/\nINSERT ..."
    },
    "skills": {
      "00_step_one.md": "<skill content for step 0>"
    },
    "tags": ["etl", "postgresql"],
    "category": "Analytics"
  }
)
```

Omit `skills` if no steps need AI skill context.

---

## Schema Reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Must end with `.usecase`; alphanumeric, hyphens, underscores only |
| `description` | string | no | Shown in catalog and marketplace listings |
| `prompt` | string | no | Verbatim user request + input skills — preserved for reproducibility |
| `install_docs` | string (markdown) | no | Setup instructions shown before import |
| `guide_docs` | string (markdown) | no | Step-by-step guide, template variables, prerequisites |
| `payloads` | object | no | Dict of filename → file content strings |
| `skills` | object | no | Dict of filename → skill markdown strings |
| `tags` | array of strings | no | Up to 20 tags; used in marketplace search |
| `category` | string | no | e.g. `Analytics`, `ETL`, `DevOps` |
| `division` | string | no | Division within the publishing organization |
| `publisher` | string | no | Publishing entity — use `LeastAction` for official items |
| `version_compatibility` | object | no | e.g. `{"core": ["1.*"]}` — empty array means all versions |
| `version_details` | object | no | Source, versioning, and publishing metadata |
