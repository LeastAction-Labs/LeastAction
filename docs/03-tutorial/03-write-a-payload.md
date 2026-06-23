# Tutorial 3 — Write a Payload

The **payload** is the task-specific input — the **WHAT** the operator should do this particular run. It can be any format the operator expects (SQL, JSON, Python, plain string).

## Example — a PostgreSQL payload

```sql
INSERT INTO people (name, age, logical_date)
VALUES ('Alice', 28, '{{logical_date}}')
```

This is the same `people` table the bundled `postgresql-demo-foundations` demo uses, so you can run it against the included `postgres-demo` database right away.

## Runtime variables

- **`{{ds}}`** — built-in, replaced at runtime with the task's logical date (e.g. `2026-03-30`).
- **`{{logical_date}}`**, `{{partition}}`, and config parameters (`{{parameter_name}}`) are also available.
- Undefined `{{ ... }}` placeholders are left as-is in the output (not an error).

This is what makes one payload work for every date and partition — the values are injected per run. See [Scheduling](/path?laui=getting-started-04-concepts-09-scheduling&itemtype=doc.file&itemname=Scheduling) for how `{{ds}}` is derived, and the [Payload concept](/path?laui=getting-started-04-concepts-04-payload&itemtype=doc.file&itemname=Payload) for the full variable reference and resolution order.

> **Tip:** generate a payload with AI — go to **AI > Payload**, pick the operator, and describe what the task should do; the AI produces a compatible payload with placeholders to fill in. (You can also ask the Service AI / an MCP client directly.)

## Recommended: keep payloads and tasks in Git

For anything beyond a quick experiment, store your task `.py` files in a Git repo and import them with the **`LeastActionGitToTask`** action (or just ask the AI to run it). It clones the repo, scans a folder, and **creates or updates** the matching catalog tasks — variables: `git_repo_url`, `git_branch`, `folder_path`, `workflow_folder_laui` (auth via a `git_username` + `git_token` connection).

Why this is the recommended path:

- **Fast recovery / reproducibility** — your tasks are version-controlled; re-import to rebuild a workflow exactly.
- **A/B testing & parallel parameter runs** — keep payload/parameter variants as separate task files (or partitions) and import them side by side to compare runs.
- **Review & CI/CD** — payload changes go through pull requests like any other code.

Full setup: [Git to Task](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Git%20To%20Task).

## Next

→ [Tutorial 4 — Create and run a task](/path?laui=getting-started-03-tutorial-04-create-and-run-a-task&itemtype=doc.file&itemname=Create%20And%20Run%20A%20Task)
