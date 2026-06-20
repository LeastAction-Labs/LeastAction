# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 06_orchestration  |  Flavor: KB (skills-only knowledge bundle)
# Sensors: a preAction that polls an EXTERNAL condition (file in S3, row in a table, API status) before a
# task runs — wait, skip, or proceed — plus SLA timeouts. Distinct from LeastActionCheckIfParentsAreDone.
payloads = {}

skills = {
    "00_sensor_and_sla.md": """\
# Sensors & SLA gates

## Lifecycle & prerequisites
**Stage:** Orchestration. Knowledge bundle — the agent reads this and adds a sensor preAction. A sensor is
a small custom action (Python) that checks an external condition and returns true/false; package it with a
connection holding any endpoint credentials. `LeastActionSlackNotify` to alert on timeout.

## Sensor vs LeastActionCheckIfParentsAreDone
`LeastActionCheckIfParentsAreDone` waits on **another LeastAction task's state**. A **sensor** waits on
**something outside LeastAction** — a file landing in S3, a row appearing in a table, an external API
returning ready, a partition existing upstream. Use a sensor when the trigger is external data, not a
sibling task.

## How a sensor works (preAction)
```
preAction runs -> check external condition
   |-- condition met      -> return true  -> task proceeds
   |-- not met, within SLA -> return false -> task waits; the scheduler retries on the next tick
   `-- not met, over SLA   -> LeastActionSkip (or Cancel) + LeastActionSlackNotify
```
Returning `false` keeps the task waiting and re-checks on retry (poke-style). Bound the wait with an SLA
so it doesn't wait forever — when the deadline passes, skip/cancel and alert.

## Common sensors
| Wait for | Check |
|---|---|
| S3/GCS object | `inspect_data` or SDK head-object: key exists for `{{logical_date}}` |
| DB row / partition | `SELECT 1 ... WHERE date = '{{logical_date}}' LIMIT 1` |
| External API ready | HTTP GET status == ready/200 |
| Upstream file count | count files in a prefix >= expected |

## SLA timeout (standalone)
For tasks that must finish by a deadline, pair a timing check with action: a preAction SLA-start-gate
(skip if inputs are stale) or a postAction/watchdog that cancels a run exceeding `sla_minutes` and alerts
(see `leastaction-pipelines-control`). Store first-seen/started timestamps in task metadata for stateful
deadlines.

## Adapting
- Keep the poke interval = the task's cron frequency (each scheduler tick re-checks).
- Always bound a sensor with an SLA + notify so a never-arriving dependency surfaces instead of hanging.
- Combine with `LeastActionCheckIfParentsAreDone` when a task waits on BOTH an upstream task AND external data.
""",
}

prompt = (
    "Knowledge bundle for sensors and SLA gates in LeastAction. A sensor is a preAction (small custom "
    "action) that polls an external condition before a task runs — an S3/GCS object for {{logical_date}}, a "
    "DB row/partition, an external API status, a file count — returning false to wait (re-checked each "
    "scheduler tick, poke-style) until the condition is met, and on SLA timeout running LeastActionSkip/"
    "Cancel + LeastActionSlackNotify. Distinct from LeastActionCheckIfParentsAreDone (which waits on a task "
    "state). Covers poke interval, SLA bounding, and combining sensor + parent-check."
)

description = (
    "Orchestration (KB): sensors — a preAction that polls an external condition (S3 object, DB row, API "
    "status) before a task runs, waiting (poke-style) until ready and skipping/cancelling + alerting on SLA "
    "timeout. Distinct from parent-state checks. The agent reads this and adds the right sensor + SLA bound."
)

guide_docs = """\
# Sensors & SLA Gates

**Lifecycle stage:** Orchestration. **Flavor:** skills-only knowledge bundle — the agent reads the skill
and adds a sensor preAction; no tasks to deploy.

## What it teaches
A sensor waits on something **outside** LeastAction (a file in S3, a row in a table, an API status) —
unlike `LeastActionCheckIfParentsAreDone`, which waits on a task's state. The sensor preAction returns
false to wait (re-checked each scheduler tick) until the condition is met, and on SLA timeout runs
`LeastActionSkip`/`Cancel` + notify so a never-arriving dependency surfaces instead of hanging.

## Prerequisites
- A small custom sensor action (+ connection for endpoint creds); `LeastActionSlackNotify` for timeout alerts.

## Using
> "use the leastaction-pipelines-sensor usecase to wait for today's file in s3://drop/ before loading, max 3h"

The agent adds a sensor preAction (head-object on the `{{logical_date}}` key) bounded by a 3h SLA + notify.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Orchestration",
    "tags": ["flavor:KB", "lifecycle:orchestration", "sensor", "sla", "poke", "external-dependency", "wait"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
