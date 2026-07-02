# Scheduling

LeastAction separates *what data a run computes* from *when the scheduler fires it* — the key to trivial backfill and automatic catch-up.

## Two date fields

| Field | Meaning | Advances by |
|---|---|---|
| `logical_date` | The **data epoch** the task processes — injected as `{{ds}}` (date, `YYYY-MM-DD`) and `{{ts}}` (timestamp, ISO format) in the payload, and determines the log storage path. Also available as `{{ds_nodash}}`, `{{ts_nodash}}`, `{{ts_nodash_with_tz}}`. Floored to the cron's granularity (daily → midnight, monthly → 1st, yearly → Jan 1, sub-hourly → exact minute). | one cron tick forward |
| `next_run_date` | The **scheduler trigger** — compared against UTC wall-clock; when `next_run_date ≤ now`, the task dispatches (pre-actions, then the operator). | one cron interval forward from the **previous `next_run_date`** (not from physical run time) |

Both start equal to `start_date` and advance together on each successful run.

## Catch-up (always on)

Because `next_run_date` advances from the *previous* `next_run_date`, a scheduler outage or an in-progress backfill leaves it in the past, so the cron immediately dispatches the next slot after each success — one logical date at a time — until `next_run_date > now`. Equivalent to Airflow's `catchup=True`.

## Cron

`frequency` is a standard cron expression (or `ADHOC`). See the [Cron API reference](/path?laui=getting-started-10-reference-api-06-cron&itemtype=doc.file&itemname=06%20Cron) for the scheduler endpoints and cron-status details.

## Related

- [Tutorial 5 — Schedule & backfill](/path?laui=getting-started-03-tutorial-05-schedule-and-backfill&itemtype=doc.file&itemname=Schedule%20And%20Backfill)
- [Backfill & Scale](/path?laui=getting-started-05-building-pipelines-05-backfill-and-scale&itemtype=doc.file&itemname=Backfill%20And%20Scale)
- [Task States](/path?laui=getting-started-04-concepts-08-task-states&itemtype=doc.file&itemname=Task%20States)
