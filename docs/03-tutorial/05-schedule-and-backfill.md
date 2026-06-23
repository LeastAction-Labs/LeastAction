# Tutorial 5 — Schedule & Backfill

## Two clocks per scheduled task

| Field | What it represents |
|---|---|
| `logical_date` | The **data period** the task computes — injected as `{{ds}}`/`{{logical_date}}`. Floored to the cron granularity (daily → midnight, monthly → 1st). |
| `next_run_date` | The **scheduler trigger** — when `next_run_date ≤ UTC now`, the task dispatches. |

Both start at `start_date` and advance one cron interval per successful run. For a daily cron at 11:01, `logical_date = 2026-05-15 00:00:00` while `next_run_date = 2026-05-15 11:01:00`.

## Catch-up is automatic

On each success, `next_run_date` advances one interval **from the previous `next_run_date`** — not from wall-clock time. So if the scheduler was down for 5 days, it runs 5 times in a row (one per missed slot, each with its own `logical_date`) until current. This is equivalent to Airflow's `catchup=True` and is always on.

## Backfilling history

Because the date is a **dimension of the task** (assigned, not baked into the run), backfilling is trivial:

- **Set the date at import** with `LeastActionGitToTask` (loop over a date range), or
- **Bulk-reschedule** existing tasks from the table view, or
- **Ask the AI:** *"backfill daily sales from 2024-01-01 to today."*

Each date gets its own instance; dependencies hold per date automatically.

> Full mechanics and patterns: [Backfill & Scale](/path?laui=getting-started-05-building-pipelines-05-backfill-and-scale&itemtype=doc.file&itemname=Backfill%20And%20Scale) and the runnable `leastaction-pipelines-orchestration` usecase. Concept depth: [Scheduling](/path?laui=getting-started-04-concepts-09-scheduling&itemtype=doc.file&itemname=Scheduling).

## Next

→ [Tutorial 6 — Add dependencies](/path?laui=getting-started-03-tutorial-06-add-dependencies&itemtype=doc.file&itemname=Add%20Dependencies)
