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

_08 = '''\
/*
{
  "name": "08_report_daily_attendance",
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
    "report_title": "Daily Attendance Report",
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

_09 = '''\
/*
{
  "name": "09_report_weekly_attendance",
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
    "report_title": "Weekly Attendance Report",
    "output_table": "badge_attendance_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "modern_teal",
      "header_bg_color": "#00796B",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#fafafa",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#E0F2F1",
      "border_color": "#B2DFDB",
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
      "table": "fct_attendance_weekly",
      "date_filter": "week_start_date >= CURRENT_DATE - INTERVAL '2 weeks'",
      "limit": null
    }
  }
}
'''

_10 = '''\
/*
{
  "name": "10_report_absent_summary",
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
    "report_title": "Absence Summary Report",
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

_11 = '''\
/*
{
  "name": "11_report_attendance_summary",
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
    "report_title": "Comprehensive Attendance Summary",
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

_12 = '''\
/*
{
  "name": "12_report_student_attendance",
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
    "report_title": "Student Attendance Report",
    "output_table": "badge_attendance_reports",
    "output_parent_laui": "{{output_parent_laui}}",
    "report_style": {
      "theme": "academic_purple",
      "header_bg_color": "#6A1B9A",
      "header_text_color": "#FFFFFF",
      "row_bg_color_even": "#faf5fc",
      "row_bg_color_odd": "#ffffff",
      "row_hover_color": "#F3E5F5",
      "border_color": "#CE93D8",
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
      "date_filter": "person_type = 'student'",
      "limit": null
    }
  }
}
'''

payloads = {
    "00_dbt_seed":              _00,
    "01_stg_badge_events":      _01,
    "02_int_badge_sessions":    _02,
    "03_int_multiday_sessions": _03,
    "04_int_absent_badges":     _04,
    "05_fct_attendance_daily":  _05,
    "06_fct_attendance_weekly": _06,
    "07_mart_attendance_summary": _07,
    "08_report_daily_attendance":   _08,
    "09_report_weekly_attendance":  _09,
    "10_report_absent_summary":     _10,
    "11_report_attendance_summary": _11,
    "12_report_student_attendance": _12,
}

prompt = (
    "Thirteen-step badge attendance pipeline with dbt models and HTML reports: "
    "(0) dbt seed to load students and teachers reference CSV data; "
    "(1-7) run dbt models via DBTRunModel — stg_badge_events, int_badge_sessions, "
    "int_multiday_sessions, int_absent_badges, fct_attendance_daily, "
    "fct_attendance_weekly, mart_attendance_summary; "
    "(8-12) generate 5 styled HTML reports via PostgresqlGenerateHtmlReport — "
    "daily attendance, weekly attendance, absence summary, comprehensive summary, "
    "student-only attendance. Reports are published as html_report items in the asset folder."
)

description = (
    "Badge attendance data pipeline with reports — fully dbt-powered. "
    "Seeds 20 students and 10 teachers via dbt seed, runs 7 dbt models via the "
    "dbt-demo server, then generates 5 styled HTML dashboard reports. "
    "Runs as a 13-task DAG: dbt tasks via DBTRunModel, reports via "
    "PostgresqlGenerateHtmlReport, chained via LeastActionCheckIfParentsAreDone."
)

guide_docs = """\
# DBT Badge Attendance Pipeline — Setup Guide

## What it does
Builds a complete badge attendance data mart using real dbt models and generates
5 styled HTML dashboard reports — all in a single 13-task usecase.

| Step | Task name | Source | Operator |
|------|-----------|--------|----------|
| 0 | `00_dbt_seed` | dbt seed (CSV) | DBTRunModel |
| 1 | `01_stg_badge_events` | stg_badge_events | DBTRunModel |
| 2 | `02_int_badge_sessions` | int_badge_sessions | DBTRunModel |
| 3 | `03_int_multiday_sessions` | int_multiday_sessions | DBTRunModel |
| 4 | `04_int_absent_badges` | int_absent_badges | DBTRunModel |
| 5 | `05_fct_attendance_daily` | fct_attendance_daily | DBTRunModel |
| 6 | `06_fct_attendance_weekly` | fct_attendance_weekly | DBTRunModel |
| 7 | `07_mart_attendance_summary` | mart_attendance_summary | DBTRunModel |
| 8 | `08_report_daily_attendance` | fct_attendance_daily | PostgresqlGenerateHtmlReport |
| 9 | `09_report_weekly_attendance` | fct_attendance_weekly | PostgresqlGenerateHtmlReport |
| 10 | `10_report_absent_summary` | int_absent_badges | PostgresqlGenerateHtmlReport |
| 11 | `11_report_attendance_summary` | mart_attendance_summary | PostgresqlGenerateHtmlReport |
| 12 | `12_report_student_attendance` | mart_attendance_summary | PostgresqlGenerateHtmlReport |

## DAG structure
```
00_dbt_seed (dbt seed)
 └── 01_stg_badge_events
      ├── 02_int_badge_sessions    ──┐
      ├── 03_int_multiday_sessions ──┤──► 05_fct_attendance_daily
      └── 04_int_absent_badges         ├── 06_fct_attendance_weekly
                                       └── 07_mart_attendance_summary
                                            ├── 08_report_daily_attendance
                                            ├── 09_report_weekly_attendance
                                            ├── 10_report_absent_summary
                                            ├── 11_report_attendance_summary
                                            └── 12_report_student_attendance
```

## Prerequisites
- `postgres-demo` container running (bundled with docker-compose)
- `dbt-demo` container running (bundled with docker-compose, depends on postgres-demo)
- Connection `dbt_server` — dbt-server URL (http://dbt-demo:8001)
- Connection `dbt_postgresql` — PostgreSQL credentials for report tasks
- Operator `DBTRunModel` installed
- Operator `PostgresqlGenerateHtmlReport` installed
- Action `LeastActionCheckIfParentsAreDone` available
"""

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Data Engineering",
    "tags": [
        "dbt", "badge", "attendance", "postgresql", "pipeline",
        "dbt-server", "reporting", "html", "usecase",
    ],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
