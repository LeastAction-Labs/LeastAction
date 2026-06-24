# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "postgresql"

connection = {
  "host": "postgres-demo",
  "port": 5432,
  "database": "postgres_demo_db",
  "user": "postgres",
  "password": "postgres"
}

prompt = "Connect to the internal demo PostgreSQL database (postgres-demo) for DBT Badge Attendance pipeline tasks."

install_docs = """# dbt_postgresql — Connection Setup

Points to the `postgres-demo` container that ships with the LeastAction docker-compose
stack (service `postgres-demo`, database `postgres_demo_db`). Used by the
DBTBadgeAttendancePipeline report tasks (PostgresqlGenerateHtmlReport).

## Fields
| Field | Value | Notes |
|---|---|---|
| host | postgres-demo | Internal docker hostname |
| port | 5432 | |
| database | postgres_demo_db | |
| user | postgres | |
| password | postgres | |
"""

guide_docs = """# dbt_postgresql — Connection Guide

Used by `PostgresqlGenerateHtmlReport` report tasks in the DBT Badge Attendance usecase,
referenced as `dbt_postgresql` via `connection_name`.
"""

description = "PostgreSQL connection for DBT Badge Attendance report tasks — points to the internal postgres-demo database by default."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "dbt", "database", "connection", "demo"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
