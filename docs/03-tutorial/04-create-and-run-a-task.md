# Tutorial 4 — Create and Run a Task

A **task** combines everything: operator + connection + payload (+ config + actions).

## Create it

1. Navigate to your workflow folder.
2. Click **Create Task**.
3. Fill in:
   - **Name** — e.g. `process_daily_events`
   - **Operator** — e.g. `PostgresqlExecuteSQL`
   - **Connection** — e.g. `postgres-prod`
   - **Frequency** — `ADHOC` for one-off, or a cron expression (e.g. `0 2 * * *`)
   - **Payload** — your SQL/JSON from the previous step
   - **Config** — optional: attach a config for retries, parameters, default actions
   - **Start / End Dates** — required for scheduled tasks; leave empty for ADHOC
4. Click **Create Task**.

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

Open the **Logs** section, or the task's **Parent-Child / history** views, to see timestamps, per-step messages, state, and action results in real time. Or ask the AI: *"run task process_daily_events and check its status."*

See [Monitoring & Logs](/path?laui=getting-started-05-building-pipelines-04-monitoring-and-logs&itemtype=doc.file&itemname=Monitoring%20And%20Logs) and [Task States](/path?laui=getting-started-04-concepts-08-task-states&itemtype=doc.file&itemname=Task%20States).

## Next

→ [Tutorial 5 — Schedule & backfill](/path?laui=getting-started-03-tutorial-05-schedule-and-backfill&itemtype=doc.file&itemname=Schedule%20And%20Backfill)
