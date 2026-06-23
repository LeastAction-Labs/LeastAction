# Backfill & Scale

Reprocessing history and running pipelines at scale are simple in LeastAction because **the date is a dimension of a task** (`logical_date`), not baked into the run. The same operator/SQL/Python runs for any date you assign.

## Backfill methods

- **Set the date at import** — `LeastActionGitToTask` takes `logical_date` in the import payload; loop over a date range to create one instance per date. See [CI/CD: Git-to-Task](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Git%20To%20Task).
- **Bulk reschedule (UI)** — select tasks in the table view and trigger a reschedule action to set a new `logical_date` on many tasks at once.
- **Ask the AI** — *"backfill daily sales from 2024-01-01 to today."*

Catch-up is automatic (see [Scheduling](/path?laui=getting-started-04-concepts-09-scheduling&itemtype=doc.file&itemname=Scheduling)); dependencies hold per date.

## Partitions — parallel & sharded runs

A **partition** is part of a task's primary key. Same name + same project + different partition = an independent instance with its own state, run date, and dependency chain. Use it for sharding (one partition per region), multi-tenant pipelines (one per client), or parallel report variants. A child depending on `partition: NORTH_AMERICA` waits only for that partition.

## Run it — the worked example

The **`leastaction-pipelines-orchestration`** usecase (in `ai/usecases`) is the runnable, AI-implementable version of this guide: backfill methods, dependency wiring, partitions, and catch-up. Deploy it, or ask the AI to apply the pattern to your tasks.

## Test before you use

Bulk actions (reschedule, skip-subtree, rerun-subtree) have broad effects — test on a few tasks first; keep action code in Git so changes are reversible.
