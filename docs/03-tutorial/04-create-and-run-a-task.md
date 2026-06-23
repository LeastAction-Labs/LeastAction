# Tutorial 4 — Create and Run a Task

A **task** combines everything: operator + connection + payload (+ config + actions).

## Create it

1. Navigate to your workflow folder.
2. Click **Create Task**.
3. Fill in:
   - **Name** — e.g. `01_insert_rows.sql` (the demo names its steps after the SQL file)
   - **Operator** — e.g. `PostgresqlExecuteSQL`
   - **Connection** — e.g. `postgresql`
   - **Frequency** — `ADHOC` for one-off, or a cron expression (e.g. `0 2 * * *`)
   - **Payload** — your SQL/JSON from the previous step
   - **Config** — optional: attach a config for retries, parameters, default actions
   - **Start / End Dates** — required for scheduled tasks; leave empty for ADHOC
4. Click **Create Task**.

## Or with the AI

The same task can be created and run entirely through the AI (Service AI chat or any MCP client):

> "create a task `01_insert_rows.sql` using operator `PostgresqlExecuteSQL`, connection `postgresql`, and this payload [...], schedule `0 2 * * *`; then run it and check the status."

The agent calls `create_catalog_item` (`item_type: task`), then `run_task` and `get_task_status`. You can also **deploy a whole usecase** in one step — `deploy usecase <name>` — which creates all its tasks at once. See [Usecases](/path?laui=getting-started-06-ai-04-usecases&itemtype=doc.file&itemname=Usecases) and [MCP](/path?laui=getting-started-06-ai-05-mcp&itemtype=doc.file&itemname=Mcp).

## Run it

**Adhoc** — set `frequency: ADHOC`; the task runs immediately when triggered. No schedule, no generated instances.

**Scheduled** — set a cron expression + `start_date`/`end_date`. LeastAction generates one task instance per interval, each with its own `logical_date`:

```
frequency:  0 2 * * *
start_date: 2026-03-01T00:00:00Z
end_date:   2026-03-31T23:59:59Z
```

This creates 31 daily instances, each with the `{{ds}}` for that day.

## View logs & status

Open the **Logs** section, or the task's **Parent-Child / history** views, to see timestamps, per-step messages, state, and action results in real time. Or ask the AI: *"run task 01_insert_rows.sql and check its status."*

See [Monitoring & Logs](/path?laui=getting-started-05-building-pipelines-04-monitoring-and-logs&itemtype=doc.file&itemname=Monitoring%20And%20Logs) and [Task States](/path?laui=getting-started-04-concepts-08-task-states&itemtype=doc.file&itemname=Task%20States).

## Next

→ [Tutorial 5 — Schedule & backfill](/path?laui=getting-started-03-tutorial-05-schedule-and-backfill&itemtype=doc.file&itemname=Schedule%20And%20Backfill)
