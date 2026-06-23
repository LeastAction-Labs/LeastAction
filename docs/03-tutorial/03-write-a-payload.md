# Tutorial 3 — Write a Payload

The **payload** is the task-specific input — the **WHAT** the operator should do this particular run. It can be any format the operator expects (SQL, JSON, Python, plain string).

## Example — a PostgreSQL payload

```sql
INSERT INTO reports.daily_summary
SELECT * FROM staging.events WHERE date = '{{ds}}'
```

## Runtime variables

- **`{{ds}}`** — built-in, replaced at runtime with the task's logical date (e.g. `2026-03-30`).
- **`{{logical_date}}`**, `{{partition}}`, and config parameters (`{{parameter_name}}`) are also available.
- Undefined `{{ ... }}` placeholders are left as-is in the output (not an error).

This is what makes one payload work for every date and partition — the values are injected per run. See [Scheduling](/path?laui=getting-started-04-concepts-09-scheduling&itemtype=doc.file&itemname=Scheduling) for how `{{ds}}` is derived, and the [Payload concept](/path?laui=getting-started-04-concepts-04-payload&itemtype=doc.file&itemname=Payload) for the full variable reference and resolution order.

> **Tip:** generate a payload with AI — go to **AI > Payload**, pick the operator, and describe what the task should do; the AI produces a compatible payload with placeholders to fill in.

## Next

→ [Tutorial 4 — Create and run a task](/path?laui=getting-started-03-tutorial-04-create-and-run-a-task&itemtype=doc.file&itemname=Create%20And%20Run%20A%20Task)
