# LeastActionCheckIfParentsAreDone Action Guide

## Overview

The `LeastActionCheckIfParentsAreDone` action validates that parent tasks are ready for a child task to execute. It performs **two critical validations** on each parent task:

1. **State Validation**: Parent must NOT be in error, fail, cancelled, or cancel states
2. **Timing Validation**: Parent's `prev_interval_start` (the logical date of its last successful run) must cover the interval required by the child's current `logical_date`

Both validations are **mandatory** and cannot be skipped.

---

## What This Action Does

When a child task depends on parent tasks, this action ensures:

- Parent tasks are not in error, fail, cancelled, or cancel states
- Parent tasks have completed the interval corresponding to the child's current `logical_date` — checked via the parent's `prev_interval_start` field
- Timing comparison accounts for cron granularity (minute, hour, day, week, month, year)

**Example**: If a daily child has `logical_date = 2026-05-17 00:00:00` and the parent runs daily at 9 AM, this action verifies `parent.prev_interval_start >= 2026-05-17 00:00:00` (day-truncated). Wall-clock execution time is irrelevant.

---

## Prerequisites

### Dependencies

```bash
pip install requests python-dateutil croniter
```

### Required Fields in Action Object

- `user_access_token`: Authorization token (automatically provided by LeastAction framework)
- `task.laui`: Unique identifier of the current/child task (string)
- `laui`: Action ID (optional, for logging)
- `session_id`: Session ID (optional, for logging)

### Network Access

- HTTP/HTTPS access to `http://backend:8000/api/v1/catalog/search`
- HTTP/HTTPS access to `http://backend:8000/api/v1/catalog/get`

---

## Configuration

### Action Variables

```json
{
  "action_variables": {
    "parents": [
      {
        "task_name": "parent_task_name_example",
        "project_laui": "{{ project_laui }}",
        "account_laui": "{{account_laui}}",
        "partition": "{{ partition}}"
      }
    ]
  }
}
```

#### Parent Descriptor Fields


| Field          | Type   | Required | Description                         |
| -------------- | ------ | -------- | ----------------------------------- |
| `task_name`    | string | Yes      | Name of the parent task to validate |
| `project_laui` | string | Yes      | Project identifier (LAUI format)    |
| `account_laui` | string | Yes      | Account identifier (LAUI format)    |
| `partition`    | string | No       | Data partition (defaults to "ALL")  |


---

---

## Return Values

### Success (Returns `True`)

- All parent tasks have valid state (not error, fail, cancelled, or cancel)
- All parent tasks have valid cron frequency (not ADHOC)
- All parent tasks have a recorded `prev_interval_start` (at least one successful run)
- All parent tasks' `prev_interval_start` covers the interval required by the child's `logical_date`

### Failure (Returns `False`)

Validation fails and returns `False` if:


| Failure Reason                  | Description                                                         |
| ------------------------------- | ------------------------------------------------------------------- |
| Missing task LAUI               | Current task identifier not found                                   |
| Current task fetch failed       | Cannot retrieve current task from catalog                           |
| Missing child logical_date      | Child task has no `logical_date` — cannot determine required interval |
| Parent not found                | Parent task doesn't exist in catalog                                |
| Parent state invalid            | Parent state is `error`, `fail`, `cancelled`, or `cancel`           |
| Parent frequency invalid        | Parent has ADHOC or missing frequency                               |
| Parent no prev_interval_start   | Parent has never completed a successful run                         |
| Parent timing failed            | Parent `prev_interval_start` is before the required logical interval |
| Unexpected error                | Technical error during validation                                   |


---

## Frequency Requirement

Parent and child can have **different cron frequencies**. If the parent runs less frequently than the child (e.g. weekly parent, daily child), the action checks that the parent has completed the interval whose window covers the child's `logical_date`.

## Cron Frequency Handling

### Supported Cron Formats

Standard 5-field cron format: `minute hour day-of-month month day-of-week`

```
0 9 * * *        → 9:00 AM daily
0 */4 * * *      → Every 4 hours
0 9 * * 1-5      → 9:00 AM weekdays
0 0 1 * *        → Midnight on 1st of month
0 0 * * 0        → Midnight Sunday
```

### Granularity Calculation

The action determines cron granularity to perform a tolerance-aware comparison (e.g. a parent scheduled at 9 AM and a child at 10 AM are both "daily" — the exact cron time within the day doesn't matter, only that the parent ran for the same day):


| Granularity | Definition                   | Example                         |
| ----------- | ---------------------------- | ------------------------------- |
| Yearly      | Month AND day-of-month fixed | `0 0 15 3 *` (March 15)         |
| Monthly     | Day-of-month fixed           | `0 0 15 * *` (15th of month)    |
| Weekly      | Day-of-week fixed            | `0 0 * * 1` (Every Monday)      |
| Daily       | Hour fixed                   | `0 9 * * *` (9 AM daily)        |
| Hourly      | Minute fixed                 | `15 * * * *` (15 min past hour) |
| Minute      | All wildcards                | `* * * * *` (every minute)      |


**Example**: For a daily parent (`0 9 * * *`) and a daily child with `logical_date = 2026-05-06 10:00:00`, the required parent interval is `2026-05-06 09:00:00`. Both truncate to `2026-05-06 00:00:00` (day granularity). Parent `prev_interval_start = 2026-05-06 09:00:00` truncates to the same value → PASS.

### Invalid Cron

- `ADHOC` frequency: Not allowed for parents (parents must have regular schedule)
- Malformed expressions: Validation fails

---

## Logging

The action produces detailed structured logs with format:

```
[component] [function] [event_type] [message]
```

### Log Levels

- **INFO**: Normal flow, validation checks, computed times
- **ERROR**: Validation failures, API errors, exceptions

### Key Log Events

```
"function_entry"          → Function started
"input_params"            → Parameters received
"auth_check"              → Authorization check
"parent_loop_start"       → Beginning parent validation
"evaluating_parent"       → Processing specific parent
"fetch_parent_result"     → Parent fetch result
"checking_state"          → State validation
"parent_state_valid"      → Parent state passed (not error/fail/cancelled/cancel)
"timing_validation_start" → Timing check begins
"timing_pass"             → Timing validation passed
"timing_fail"             → Timing validation failed
"parent_loop_end"         → All parents processed
"complete_success"        → All validations passed
"return_true" / "return_false" → Final result
```

---

## Error Handling

### Common Errors and Solutions

#### 1. "Authorization token not found"

**Cause**: `user_access_token` not provided by LeastAction framework (should be automatic)

**Fix**: Verify LeastAction framework is properly initialized and passing auth token to action object. This should happen automatically.

#### 2. "Failed to fetch parent task"

**Cause**: Parent doesn't exist or wrong project/account LAUI

**Fix**: Verify parent configuration

```yaml
parents:
  - task_name: "fetch_data"         # Must exist in catalog
    project_laui: "{{ project_laui }}"   # Must match project
    account_laui: "{{ account_laui }}"   # Must match account
```

#### 3. "Parent state is invalid (error, fail, cancelled, or cancel)"

**Cause**: Parent task failed, was cancelled, or is in an invalid state

**Fix**: Wait for parent to complete successfully or debug parent failure

#### 4. "Parent prev_interval_start is before required logical interval"

**Cause**: Parent hasn't completed the interval that corresponds to the child's `logical_date`

**Fix**: Ensure parent task has run successfully for the required logical date before the child is triggered

---

## Timing Validation Details

### Calculation Process

1. **Get child's `logical_date`** from the current task — this is the scheduled interval the child is running for, not wall-clock time
2. **For each parent**:
   - Compute required parent interval: `_prev_cron_time(parent_frequency, child_logical_date)`
   - Get parent's last successfully completed interval: `parent.prev_interval_start`
   - Truncate both to parent's cron granularity
   - Compare: `parent.prev_interval_start (truncated) >= required_interval (truncated)`

`prev_interval_start` is set to the parent's `logical_date` on each successful run (see `task_executor.py`). It represents *which interval* the parent last successfully processed, not when it physically ran.

### Example

```
Child logical_date: 2026-05-06 10:00:00   (child frequency: 0 10 * * *, running for May 6)

Parent frequency: 0 9 * * *    (daily at 9 AM)
├─ _prev_cron_time(parent_freq, 10:00:00 May 6) → 2026-05-06 09:00:00
├─ Parent granularity: day
├─ Required (truncated to day): 2026-05-06 00:00:00
├─ Parent prev_interval_start: 2026-05-06 09:00:00  (ran successfully for May 6)
├─ Actual (truncated to day): 2026-05-06 00:00:00
└─ Comparison: 2026-05-06 >= 2026-05-06 ✓ PASS

Parent not yet run for May 6 (prev_interval_start = 2026-05-05 09:00:00):
├─ Actual (truncated): 2026-05-05
└─ 2026-05-05 >= 2026-05-06 ✗ FAIL — child waits

Note: Wall-clock execution time is irrelevant. During catch-up, both parent
and child march epoch-by-epoch; the check passes only after each parent slot
completes, never skipping ahead.
```

---


---

## Performance Considerations

- **API Calls**: 1 + N (1 for current task, N for each parent)
- **Timeout**: 30 seconds per API call (configurable)
- **Cron Parsing**: O(1) for standard 5-field cron
- **Network Latency**: Depends on backend availability

---

## Best Practices

1. **Always validate configuration**: Check parent task names, project/account LAUIs match
2. **Set reasonable timeouts**: Increase from 30s if backend is slow
3. **Monitor logs**: Review INFO and ERROR logs for issues
4. **Test with staging**: Validate parent configuration in non-prod first
5. **Use consistent timezones**: Ensure all systems use UTC
6. **Match frequencies**: Parent and child must share the same cron frequency — cross-frequency dependencies are not supported
  - Parent: `0 9 * * *` (daily), Child: `0 10 * * *` (daily) ✓
  - Parent: `0 0 * * 1` (weekly), Child: `0 10 * * *` (daily) ✗
7. **Handle ADHOC parents**: If parent is one-time (ADHOC), use different validation strategy

---

## Troubleshooting

### "Check the logs for details"

1. Enable debug logging in your environment
2. Look for "VALIDATION FAILED" entries
3. Check the specific `failure_reason` field
4. Verify API responses match expected format

### Timing validation inconsistent

- Verify all systems use UTC
- Check parent/child cron expressions are correct
- Confirm parent task is actually running on schedule
- Review cron granularity calculation (via logs)

### API timeout errors

- Check backend service is running
- Verify network connectivity
- Increase timeout parameter if needed
- Check API response times

### Parent task not found

- Verify exact task name matches catalog
- Check project/account LAUIs are correct
- Ensure user has access to parent task
- Check partition setting (use "ALL" if unsure)

---
## Summary

**Key Points**:

- ✓ Validates parent state (must NOT be error, fail, cancelled, or cancel)
- ✓ Validates parent timing using `logical_date` and `prev_interval_start` — not wall clock
- ✓ Uses cron granularity for flexible timing comparisons
- ✓ Supports multiple parents
- ✓ Comprehensive logging for debugging
- ✓ Fails fast on first invalid parent

**When to Use**:

- Child tasks depend on parent task completion
- Need to enforce scheduling dependencies
- Require confidence parent ran successfully

**When NOT to Use**:

- One-time (ADHOC) parent tasks
- Parents without schedules
- Tasks with no dependencies
- Parent is ADHOC (no interval to compare against)

