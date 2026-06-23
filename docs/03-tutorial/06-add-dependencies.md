# Tutorial 6 — Add Dependencies

LeastAction resolves dependencies through **actions**, not hard-coded DAG edges — so they're flexible, reusable, and work across projects.

## The built-in dependency action

`LeastActionCheckIfParentsAreDone` runs as a **pre-action**: before a task executes, it confirms every declared parent task succeeded for the same logical date.

Attach it when creating/editing a task and fill in the `parents`:

```json
{
  "parents": [
    {
      "task_name": "extract_data",
      "project_laui": "{{project_laui}}",
      "account_laui": "{{account_laui}}",
      "partition": "{{partition}}"
    }
  ]
}
```

The `{{...}}` placeholders resolve at runtime, so the same definition works across environments and partitions. Because lookup is by **name + project + partition**, a task can even depend on a task in a different project — no shared DAG.

## At scale

For pipelines with many tasks, set `LeastActionCheckIfParentsAreDone` as a **default pre-action in the workflow config** so every task inherits it. See the [Config concept](/path?laui=getting-started-04-concepts-05-config&itemtype=doc.file&itemname=Config).

## Visualize

Every task has a **Parent-Child** tab — a list and an interactive dependency graph. Click a node to focus; expand to add more levels.

> Deeper: [Task Dependencies guide](/path?laui=getting-started-05-building-pipelines-03-task-dependencies&itemtype=doc.file&itemname=Task%20Dependencies) and the [Workflow concept](/path?laui=getting-started-04-concepts-07-workflow&itemtype=doc.file&itemname=Workflow).

## You're done 🎉

You've built a connection, an operator, a payload, a scheduled task, and a dependency chain. Where next:

- **Generate pipelines with AI** — [AI overview](/path?laui=getting-started-06-ai-01-overview&itemtype=doc.file&itemname=Overview)
- **Deploy a ready-made usecase** — browse `ai/usecases` in the catalog
- **Concepts** — [start here](/path?laui=getting-started-04-concepts-01-items-and-catalog&itemtype=doc.file&itemname=Items%20And%20Catalog)
