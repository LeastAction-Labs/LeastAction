# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
_08 = '''\
/*
{
  "name": "08_report_daily_attendance",
  "frequency": "0 8 * * *",
  "operator_name": "PostgresClaudeReportDebug",
  "connection_name": "dbt_postgresql_plus_claude",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "07_mart_attendance_summary"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "source_table_name": "fct_attendance_daily",
  "chat_prompt": "Generate a professional HTML attendance report from this data. Title: Daily Attendance Report. Show a table with columns: badge_id, full_date, total_hours (rounded to 2 decimal places), total_sessions, first_in_time (time only, HH:MM), last_out_time (time only, HH:MM), avg_session_hours (rounded to 2 decimal places). Sort by full_date DESC then total_hours DESC. Use a blue header (#1565C0 white text). Highlight rows where total_hours > 8 in light green (#E8F5E9). Highlight rows where total_sessions = 0 in light red (#FFEBEE). Add a summary row at the bottom showing: average total_hours, total sessions count, and count of distinct badge_ids. Include a subtitle showing the date range covered."
}
'''

_09 = '''\
/*
{
  "name": "09_report_weekly_attendance",
  "frequency": "0 9 * * 0",
  "operator_name": "PostgresClaudeReportDebug",
  "connection_name": "dbt_postgresql_plus_claude",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "07_mart_attendance_summary"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "source_table_name": "fct_attendance_weekly",
  "chat_prompt": "Generate a professional HTML weekly attendance report from this data. Title: Weekly Attendance Report. Show a table with columns: badge_id, week_start_date, week_end_date, year, week_of_year, total_hours (rounded to 2 decimal places), total_sessions, days_present, earliest_in (time only HH:MM), latest_out (time only HH:MM), avg_session_hours (rounded to 2 decimal places). Sort by week_start_date DESC then days_present ASC. Use a teal header (#00796B white text). Highlight rows where days_present < 3 in light orange (#FFF3E0) with a note icon. Highlight rows where total_hours > 40 in light green (#E8F5E9). Add a summary section showing: average days_present across all badges and weeks, average total_hours per week, count of badges with days_present < 3 in the latest week. Include a subtitle showing the week range covered."
}
'''

_10 = '''\
/*
{
  "name": "10_report_absent_summary",
  "frequency": "0 8 * * *",
  "operator_name": "PostgresClaudeReportDebug",
  "connection_name": "dbt_postgresql_plus_claude",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "07_mart_attendance_summary"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "source_table_name": "int_absent_badges",
  "chat_prompt": "Generate a professional HTML absence summary report from this data. Title: Absence Summary Report. Include two sections: (1) A department summary table showing: department, person_type, total_absence_days, distinct_badges_absent, avg_absences_per_badge — sorted by total_absence_days DESC. Use a red header (#C62828 white text). Highlight the top 3 departments with highest absences in light red (#FFEBEE). (2) A detailed absence table showing: badge_id, name, department, person_type, event_date — sorted by event_date DESC then department. Highlight teachers (person_type = teacher) in light blue (#E3F2FD). Add a summary card at the top showing: total absence records, distinct badges absent, date range, and most absent department."
}
'''

_11 = '''\
/*
{
  "name": "11_report_attendance_summary",
  "frequency": "0 8 * * *",
  "operator_name": "PostgresClaudeReportDebug",
  "connection_name": "dbt_postgresql_plus_claude",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "07_mart_attendance_summary"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "source_table_name": "mart_attendance_summary",
  "chat_prompt": "Generate a professional HTML comprehensive attendance summary report from this data. Title: Daily Attendance Summary. Include four sections: (1) Summary cards showing: report_date, total people, present count, absent count, overall attendance percentage, count still on campus, count early exits, count with absence streaks >= 3. (2) Department breakdown table: department, present_count, absent_count, attendance_pct, avg_total_hours — sorted by attendance_pct ASC. Use a navy header (#1A237E white text). (3) Flags table showing badges with any of: still_on_campus = true, early_exit = true, absence_streak_days >= 3 — columns: name, department, person_type, attendance_status, still_on_campus, early_exit, absence_streak_days. Highlight still_on_campus in orange (#FFF3E0), early_exit in yellow (#FFFDE7), absence_streak >= 3 in red (#FFEBEE). (4) Full attendance table: name, department, person_type, attendance_status, total_hours (2 dp), first_in_time (HH:MM), last_out_time (HH:MM), avg_session_hours (2 dp) — sorted by attendance_status DESC then department. Absent rows in light red (#FFEBEE), present rows with hours > 8 in light green (#E8F5E9)."
}
'''

_12 = '''\
/*
{
  "name": "12_report_student_attendance",
  "frequency": "0 8 * * *",
  "operator_name": "PostgresClaudeReportDebug",
  "connection_name": "dbt_postgresql_plus_claude",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "07_mart_attendance_summary"
            }
          ]
        }
      }
    ]
  }
}
*/
{
  "source_table_name": "mart_attendance_summary",
  "chat_prompt": "Generate a professional HTML student-only attendance report from this data. Filter to only rows where person_type = 'student'. Title: Student Attendance Report. Include three sections: (1) Summary cards showing: total students, present count, absent count, student attendance percentage, count with absence streaks >= 3, count with early exits. (2) A department breakdown table showing department, present_count, absent_count, attendance_pct, avg_total_hours — sorted by attendance_pct ASC. Use a purple header (#6A1B9A white text). (3) A detailed student table with columns: name, department, attendance_status, total_hours (rounded to 2 decimal places), first_in_time (HH:MM), last_out_time (HH:MM), early_exit, absence_streak_days — sorted by absence_streak_days DESC then attendance_status. Highlight absent students in light red (#FFEBEE). Highlight students with absence_streak_days >= 3 in orange (#FFF3E0) with bold name. Highlight early_exit = true in light yellow (#FFFDE7). Add a footer showing the report_date."
}
'''

payloads = {
    "08_report_daily_attendance":   _08,
    "09_report_weekly_attendance":  _09,
    "10_report_absent_summary":     _10,
    "11_report_attendance_summary": _11,
    "12_report_student_attendance": _12,
}

skills = {
    "08_report_daily_attendance.md": """\
# Report 08 — Daily Attendance Report

Generates an HTML report from `fct_attendance_daily` showing per-badge daily hours,
sessions, first-in and last-out times. Highlights badges over 8 hours and zero-session days.

## Source table
`fct_attendance_daily` — one row per badge per day.

## Operator
`PostgresClaudeReportDebug` — queries the table, sends schema + data to Claude,
generates HTML, strips script tags, saves as `html_report` asset in catalog.

## Connection
`dbt_postgresql_plus_claude` — PostgreSQL credentials + Claude API key.

## Dependency
Waits for `07_mart_attendance_summary` (`LeastActionCheckIfParentsAreDone`).
Runs in parallel with reports 09–12.
""",

    "09_report_weekly_attendance.md": """\
# Report 09 — Weekly Attendance Report

Generates an HTML report from `fct_attendance_weekly` showing per-badge weekly hours,
days present, earliest in and latest out. Highlights badges present fewer than 3 days.
Runs on Sundays (`0 9 * * 0`) after the weekly rollup completes.

## Source table
`fct_attendance_weekly` — one row per badge per ISO week.

## Dependency
Waits for `07_mart_attendance_summary` (`LeastActionCheckIfParentsAreDone`).
""",

    "10_report_absent_summary.md": """\
# Report 10 — Absence Summary Report

Generates an HTML report from `int_absent_badges` showing absence counts by
department and person type across all dates. Highlights departments with highest
absence rates.

## Source table
`int_absent_badges` — one row per absent badge per date.

## Dependency
Waits for `07_mart_attendance_summary` (`LeastActionCheckIfParentsAreDone`).
""",

    "11_report_attendance_summary.md": """\
# Report 11 — Comprehensive Attendance Summary Report

Generates an HTML report from `mart_attendance_summary` for the latest date.
Shows present vs absent counts by department, flags still-on-campus and early exits,
highlights 3+ day absence streaks, and includes an overall attendance percentage.

## Source table
`mart_attendance_summary` — one row per badge for the latest report date.

## Dependency
Waits for `07_mart_attendance_summary` (`LeastActionCheckIfParentsAreDone`).
""",

    "12_report_student_attendance.md": """\
# Report 12 — Student-Only Attendance Report

Generates an HTML report from `mart_attendance_summary` filtered to `person_type = student`.
Shows attendance status, hours, department breakdown, absence streaks, and early exits
for students only.

## Source table
`mart_attendance_summary` filtered to students.

## Adapting this step
- **Teacher report**: Change `chat_prompt` to filter `person_type = teacher`.
- **Department filter**: Add department name to the `chat_prompt` to scope to one department.

## Dependency
Waits for `07_mart_attendance_summary` (`LeastActionCheckIfParentsAreDone`).
""",
}

prompt = (
    "Five HTML report tasks for the badge attendance pipeline. "
    "All run after mart_attendance_summary completes. "
    "Report 08: daily attendance per badge from fct_attendance_daily. "
    "Report 09: weekly attendance per badge from fct_attendance_weekly (Sundays). "
    "Report 10: absence summary by department from int_absent_badges. "
    "Report 11: comprehensive daily summary from mart_attendance_summary with flags. "
    "Report 12: student-only attendance from mart_attendance_summary. "
    "All use PostgresClaudeReportDebug operator on dbt_postgresql_plus_claude connection, "
    "chained via LeastActionCheckIfParentsAreDone waiting on 07_mart_attendance_summary."
)

description = (
    "Five HTML report tasks that run after the dbtBadgeAttendancePipeline completes. "
    "Reports 08, 10, 11, 12 run daily. Report 09 runs weekly on Sundays. "
    "All wait on mart_attendance_summary and run in parallel. "
    "Each report queries a different table, sends schema + data to Claude AI, "
    "and publishes a styled HTML report to the LeastAction catalog. "
    "Uses PostgresClaudeReportDebug operator with dbt_postgresql_plus_claude connection."
)

guide_docs = """\
# dbtBadgeAttendanceReports — Setup Guide

## What it does
Generates 5 styled HTML reports from the badge attendance data mart
and publishes them to the LeastAction catalog.

| Step | Task name | Source table | Frequency | Description |
|------|-----------|---|---|---|
| 8 | `08_report_daily_attendance` | `fct_attendance_daily` | `0 8 * * *` | Per-badge daily hours and sessions |
| 9 | `09_report_weekly_attendance` | `fct_attendance_weekly` | `0 9 * * 0` | Per-badge weekly rollup (Sundays) |
| 10 | `10_report_absent_summary` | `int_absent_badges` | `0 8 * * *` | Absence counts by department |
| 11 | `11_report_attendance_summary` | `mart_attendance_summary` | `0 8 * * *` | Full daily summary with flags |
| 12 | `12_report_student_attendance` | `mart_attendance_summary` | `0 8 * * *` | Student-only attendance |

## DAG structure
All 5 reports wait on `07_mart_attendance_summary` and run in parallel:
```
07_mart_attendance_summary
 ├── 08_report_daily_attendance
 ├── 09_report_weekly_attendance
 ├── 10_report_absent_summary
 ├── 11_report_attendance_summary
 └── 12_report_student_attendance
```

## Prerequisites
- `dbtBadgeAttendancePipeline` must have run successfully through step 07
- Connection named `dbt_postgresql_plus_claude` with fields:
  `host`, `port`, `database`, `user`, `password`, `claude_api_key`, `la_base_url`, `user_access_token`
- Operator `PostgresClaudeReportDebug` installed
- A `folder.report` asset folder exists in catalog to receive the html_report items

## Deploying
Use the **Usecase Deploy Skill** in the LeastAction AI assistant:
> "deploy usecase dbtBadgeAttendanceReports"

Run after `dbtBadgeAttendancePipeline` step 07 has succeeded.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `relation does not exist` | Run dbtBadgeAttendancePipeline first through step 07 |
| `Content blocked: HTML contains script tags` | Already handled in operator — check operator version |
| Report not appearing in catalog | Verify `parent_laui` in connection points to a valid `folder.report` item |
| `Claude API key invalid` | Update `claude_api_key` in the `dbt_postgresql_plus_claude` connection |
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Reporting",
    "tags": [
        "dbt", "badge", "attendance", "reporting", "html", "claude",
        "dashboard", "usecase", "postgresql",
    ],
    "airflow_equivalent": "BashOperator",
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
