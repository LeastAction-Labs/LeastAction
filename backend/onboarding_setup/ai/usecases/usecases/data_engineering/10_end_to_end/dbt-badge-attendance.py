# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

_00 = '''\
/*
{
  "name": "00_dbt_seed",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2099-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/
{"action": "seed"}
'''

_01 = '''\
/*
{
  "name": "01_stg_badge_events",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "00_dbt_seed"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "stg_badge_events"}
'''

_02 = '''\
/*
{
  "name": "02_int_badge_sessions",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "int_badge_sessions"}
'''

_03 = '''\
/*
{
  "name": "03_int_multiday_sessions",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "int_multiday_sessions"}
'''

_04 = '''\
/*
{
  "name": "04_int_absent_badges",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "01_stg_badge_events"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "int_absent_badges"}
'''

_05 = '''\
/*
{
  "name": "05_fct_attendance_daily",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "02_int_badge_sessions"
            },
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "03_int_multiday_sessions"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "fct_attendance_daily"}
'''

_06 = '''\
/*
{
  "name": "06_fct_attendance_weekly",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "05_fct_attendance_daily"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "fct_attendance_weekly"}
'''

_07 = '''\
/*
{
  "name": "07_mart_attendance_summary",
  "frequency": "ADHOC",
  "operator_name": "DBTRunModel",
  "connection_name": "dbt_server",
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
              "task_name": "05_fct_attendance_daily"
            }
          ]
        }
      }
    ]
  }
}
*/
{"model": "mart_attendance_summary"}
'''

_00b = '''\
/*
{
  "name": "00b_contract_check",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlValidatorSQL",
  "connection_name": "dbt_postgresql",
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
              "task_name": "00_dbt_seed"
            }
          ]
        }
      }
    ]
  }
}
*/
report_title: 'Data Contract — Seed Reference Tables'
output_table: 'badge_attendance_contracts'

queries:
  - name: 'Schema — students columns'
    description: 'Contract: students must have badge_id, name, department, year_or_sem'
    sql: |
      SELECT COUNT(*) AS missing
      FROM (VALUES ('badge_id','character varying'),('name','character varying'),('department','character varying'),('year_or_sem','bigint')) AS c(col, typ)
      LEFT JOIN information_schema.columns ic
        ON ic.table_name='students' AND ic.column_name=c.col AND ic.udt_name=c.typ
      WHERE ic.column_name IS NULL
    severity: critical
    pass_condition: 'missing == 0'
    display: scalar

  - name: 'Schema — teachers columns'
    description: 'Contract: teachers must have badge_id, name, department'
    sql: |
      SELECT COUNT(*) AS missing
      FROM (VALUES ('badge_id','character varying'),('name','character varying'),('department','character varying')) AS c(col, typ)
      LEFT JOIN information_schema.columns ic
        ON ic.table_name='teachers' AND ic.column_name=c.col AND ic.udt_name=c.typ
      WHERE ic.column_name IS NULL
    severity: critical
    pass_condition: 'missing == 0'
    display: scalar

  - name: 'PK — students badge_id unique'
    description: 'Contract: no duplicate badge_ids in students'
    sql: "SELECT badge_id, COUNT(*) AS dupes FROM students GROUP BY badge_id HAVING COUNT(*) > 1"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'PK — teachers badge_id unique'
    description: 'Contract: no duplicate badge_ids in teachers'
    sql: "SELECT badge_id, COUNT(*) AS dupes FROM teachers GROUP BY badge_id HAVING COUNT(*) > 1"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Nullability — students no nulls'
    description: 'Contract: no null values in required columns'
    sql: "SELECT COUNT(*) AS null_rows FROM students WHERE badge_id IS NULL OR name IS NULL OR department IS NULL"
    severity: critical
    pass_condition: 'null_rows == 0'
    display: scalar

  - name: 'Nullability — teachers no nulls'
    description: 'Contract: no null values in required columns'
    sql: "SELECT COUNT(*) AS null_rows FROM teachers WHERE badge_id IS NULL OR name IS NULL OR department IS NULL"
    severity: critical
    pass_condition: 'null_rows == 0'
    display: scalar

  - name: 'Volume — students count'
    description: 'Contract: exactly 20 students expected'
    sql: "SELECT COUNT(*) AS row_count FROM students"
    severity: critical
    pass_condition: 'row_count == 20'
    display: scalar

  - name: 'Volume — teachers count'
    description: 'Contract: exactly 10 teachers expected'
    sql: "SELECT COUNT(*) AS row_count FROM teachers"
    severity: critical
    pass_condition: 'row_count == 10'
    display: scalar

  - name: 'Domain — departments valid'
    description: 'Contract: only 6 allowed departments'
    sql: |
      SELECT DISTINCT department FROM (
        SELECT department FROM students UNION ALL SELECT department FROM teachers
      ) t WHERE department NOT IN ('Engineering','Science','Business','Arts','Medicine','Law')
    severity: warning
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Referential — no badge_id overlap'
    description: 'Contract: student and teacher badge_ids must not overlap'
    sql: "SELECT s.badge_id FROM students s INNER JOIN teachers t ON s.badge_id = t.badge_id"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table
'''

_07b = '''\
/*
{
  "name": "07b_validate_attendance",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlValidatorSQL",
  "connection_name": "dbt_postgresql",
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
report_title: 'Badge Attendance Pipeline Validation'
output_table: 'badge_attendance_validation'
output_parent_laui: '{{output_parent_laui}}'

queries:
  - name: 'Event types valid'
    description: 'All events must be IN or OUT only'
    sql: "SELECT DISTINCT event_type FROM stg_badge_events WHERE event_type NOT IN ('IN', 'OUT')"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'No orphan badge_ids'
    description: 'All badge_ids in sessions must exist in reference tables'
    sql: |
      SELECT DISTINCT s.badge_id
      FROM int_badge_sessions s
      WHERE s.badge_id NOT IN (SELECT badge_id FROM students UNION SELECT badge_id FROM teachers)
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Session hours non-negative'
    description: 'No negative session durations'
    sql: "SELECT COUNT(*) AS negative_count FROM int_badge_sessions WHERE session_hours < 0"
    severity: critical
    pass_condition: 'negative_count == 0'
    display: scalar

  - name: 'Total hours <= 24 per day'
    description: 'No badge should exceed 24 hours in a single day'
    sql: "SELECT badge_id, full_date, total_hours FROM fct_attendance_daily WHERE total_hours > 24"
    severity: warning
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Mart has all 30 people'
    description: '20 students + 10 teachers'
    sql: "SELECT COUNT(*) AS person_count FROM mart_attendance_summary"
    severity: critical
    pass_condition: 'person_count == 30'
    display: scalar

  - name: 'Attendance status valid'
    description: 'Only present or absent'
    sql: "SELECT DISTINCT attendance_status FROM mart_attendance_summary WHERE attendance_status NOT IN ('present', 'absent')"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'No future dates'
    description: 'No records with dates beyond today'
    sql: "SELECT COUNT(*) AS future_count FROM fct_attendance_daily WHERE full_date > CURRENT_DATE"
    severity: warning
    pass_condition: 'future_count == 0'
    display: scalar

  - name: 'Absence streak non-negative'
    description: 'absence_streak_days >= 0'
    sql: "SELECT COUNT(*) AS negative_streaks FROM mart_attendance_summary WHERE absence_streak_days < 0"
    severity: critical
    pass_condition: 'negative_streaks == 0'
    display: scalar
'''

_08 = '''\
/*
{
  "name": "08_report_attendance_overview",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlGenerateHtmlReport",
  "connection_name": "dbt_postgresql",
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
  "data": {
    "report_title": "Attendance Overview — Present, Absent & Flags",
    "output_table": "badge_attendance_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "corporate_navy",
      "header_bg_color": "#1A237E",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#f5f5fa",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#E8EAF6",
      "border_color": "#C5CAE9",
      "font_family": "Segoe UI, Arial, sans-serif"
    },
    "database": {
      "host": "postgres-demo",
      "port": 5432,
      "database": "postgres_demo_db",
      "user": "postgres",
      "password": "postgres"
    },
    "query": {
      "table": "mart_attendance_summary",
      "date_filter": "1=1",
      "limit": null
    }
  }
}
'''

_09 = '''\
/*
{
  "name": "09_report_daily_trends",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlGenerateHtmlReport",
  "connection_name": "dbt_postgresql",
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
  "data": {
    "report_title": "Daily Attendance Trends — Hours & Sessions",
    "output_table": "badge_attendance_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "corporate_blue",
      "header_bg_color": "#1565C0",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#f9f9f9",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#E3F2FD",
      "border_color": "#BBDEFB",
      "font_family": "Segoe UI, Arial, sans-serif"
    },
    "database": {
      "host": "postgres-demo",
      "port": 5432,
      "database": "postgres_demo_db",
      "user": "postgres",
      "password": "postgres"
    },
    "query": {
      "table": "fct_attendance_daily",
      "date_filter": "full_date >= CURRENT_DATE - INTERVAL '3 days'",
      "limit": null
    }
  }
}
'''

_10 = '''\
/*
{
  "name": "10_report_department_absence",
  "frequency": "ADHOC",
  "operator_name": "PostgresqlGenerateHtmlReport",
  "connection_name": "dbt_postgresql",
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
  "data": {
    "report_title": "Department Absence Report",
    "output_table": "badge_attendance_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "alert_red",
      "header_bg_color": "#C62828",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#fff8f8",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#FFEBEE",
      "border_color": "#FFCDD2",
      "font_family": "Segoe UI, Arial, sans-serif"
    },
    "database": {
      "host": "postgres-demo",
      "port": 5432,
      "database": "postgres_demo_db",
      "user": "postgres",
      "password": "postgres"
    },
    "query": {
      "table": "int_absent_badges",
      "date_filter": "event_date >= CURRENT_DATE - INTERVAL '3 days'",
      "limit": null
    }
  }
}
'''

payloads = {
    "00_dbt_seed":                  _00,
    "00b_contract_check":           _00b,
    "01_stg_badge_events":          _01,
    "02_int_badge_sessions":        _02,
    "03_int_multiday_sessions":     _03,
    "04_int_absent_badges":         _04,
    "05_fct_attendance_daily":      _05,
    "06_fct_attendance_weekly":     _06,
    "07_mart_attendance_summary":   _07,
    "07b_validate_attendance":      _07b,
    "08_report_attendance_overview": _08,
    "09_report_daily_trends":       _09,
    "10_report_department_absence": _10,
}

prompt = (
    "Thirteen-step badge attendance pipeline — seed, data contract, dbt models, validation, reports: "
    "(0) dbt seed; (0b) data contract enforcement on seed tables — schema, PKs, nullability, "
    "volume, domain checks (independent, publishes contract report); "
    "(1-7) dbt models via DBTRunModel; "
    "(7b) pipeline validation — 8 data quality checks on model outputs (independent, publishes validation report); "
    "(8-10) 3 distinct HTML reports via PostgresqlGenerateHtmlReport — "
    "attendance overview from mart, daily trends from fct_attendance_daily, "
    "department absence from int_absent_badges. "
    "Contract and validation run independently — do not block the pipeline or reports."
)

description = (
    "Badge attendance end-to-end pipeline — fully dbt-powered with data contracts, "
    "validation, and reports. Seeds reference data, enforces a data contract on inputs, "
    "runs 7 dbt models, validates all outputs, and generates 3 distinct HTML reports. "
    "Contract (00b) and validation (07b) run independently alongside the pipeline — "
    "they publish their own reports but do not block downstream tasks."
)

guide_docs = """\
# DBT Badge Attendance Pipeline — Setup Guide

## What it does
End-to-end badge attendance pipeline: seed → contract → transform → validate → report.

| Step | Task name | What | Operator |
|------|-----------|------|----------|
| 0 | `00_dbt_seed` | Load CSV seed data | DBTRunModel |
| 0b | `00b_contract_check` | Enforce data contract on seed tables | PostgresqlValidatorSQL |
| 1 | `01_stg_badge_events` | Generate synthetic swipe events | DBTRunModel |
| 2 | `02_int_badge_sessions` | Pair same-day IN/OUT events | DBTRunModel |
| 3 | `03_int_multiday_sessions` | Pair cross-day sessions | DBTRunModel |
| 4 | `04_int_absent_badges` | Identify absent badges | DBTRunModel |
| 5 | `05_fct_attendance_daily` | Daily attendance grain | DBTRunModel |
| 6 | `06_fct_attendance_weekly` | Weekly rollup | DBTRunModel |
| 7 | `07_mart_attendance_summary` | Final summary mart | DBTRunModel |
| 7b | `07b_validate_attendance` | Validate pipeline outputs | PostgresqlValidatorSQL |
| 8 | `08_report_attendance_overview` | Present/absent/flags overview | PostgresqlGenerateHtmlReport |
| 9 | `09_report_daily_trends` | Daily hours & sessions trends | PostgresqlGenerateHtmlReport |
| 10 | `10_report_department_absence` | Absence by department | PostgresqlGenerateHtmlReport |

## Data contract checks (00b) — runs after seed, independent
| Check | Severity | What |
|-------|----------|------|
| Schema — students columns | critical | badge_id, name, department, year_or_sem exist with correct types |
| Schema — teachers columns | critical | badge_id, name, department exist with correct types |
| PK — students unique | critical | No duplicate badge_ids |
| PK — teachers unique | critical | No duplicate badge_ids |
| Nullability — students | critical | No nulls in required columns |
| Nullability — teachers | critical | No nulls in required columns |
| Volume — students | critical | Exactly 20 rows |
| Volume — teachers | critical | Exactly 10 rows |
| Domain — departments | warning | Only 6 allowed departments |
| Referential — no overlap | critical | Student and teacher badge_ids don't overlap |

## Pipeline validation checks (07b) — runs after mart, independent
| Check | Severity | What |
|-------|----------|------|
| Event types valid | critical | Only IN/OUT |
| No orphan badge_ids | critical | All sessions reference valid badges |
| Session hours >= 0 | critical | No negative durations |
| Total hours <= 24/day | warning | No impossible daily hours |
| Mart = 30 people | critical | 20 students + 10 teachers |
| Status valid | critical | Only present/absent |
| No future dates | warning | No records beyond today |
| Streak >= 0 | critical | No negative absence streaks |

## DAG structure
```
00_dbt_seed
 ├── 00b_contract_check (independent — publishes contract report)
 └── 01_stg_badge_events
      ├── 02_int_badge_sessions    ──┐
      ├── 03_int_multiday_sessions ──┤──► 05_fct_attendance_daily
      └── 04_int_absent_badges         ├── 06_fct_attendance_weekly
                                       └── 07_mart_attendance_summary
                                            ├── 07b_validate_attendance (independent — publishes validation report)
                                            ├── 08_report_attendance_overview
                                            ├── 09_report_daily_trends
                                            └── 10_report_department_absence
```

## Prerequisites
- `postgres-demo` and `dbt-demo` containers (bundled with docker-compose)
- Connections: `dbt_server`, `dbt_postgresql`
- Operators: `DBTRunModel`, `PostgresqlValidatorSQL`, `PostgresqlGenerateHtmlReport`
- Action: `LeastActionCheckIfParentsAreDone`
"""

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Data Engineering",
    "tags": [
        "dbt", "badge", "attendance", "postgresql", "pipeline",
        "dbt-server", "reporting", "validation", "data-contract",
        "end-to-end", "usecase",
    ],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
