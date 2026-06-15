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

prompt = "Connect to the internal demo PostgreSQL database (postgres-demo) bundled with LeastAction. Used by the PostgresqlDemo 3-task workflow (create/insert/update on the 'people' table)."

install_docs = """# Postgresql — Connection Setup

Points to the `postgres-demo` container that ships with the LeastAction docker-compose
stack (service `postgres-demo`, database `postgres_demo_db`). No additional setup is
required when running the bundled demo stack.

## Fields
| Field | Value | Notes |
|---|---|---|
| host | postgres-demo | Internal docker hostname |
| port | 5432 | |
| database | postgres_demo_db | |
| user | postgres | |
| password | postgres | |

To point this connection at your own PostgreSQL instance, replace host/port/database/user/password
with your database's credentials.
"""

guide_docs = """# Postgresql — Connection Guide

Used by `PostgresqlExecuteSQL` tasks in the `PostgresqlDemo` usecase, named `postgresql`
via `connection_name`. Provides plain psycopg2-style credentials (host, port, database,
user, password).
"""

description = "PostgreSQL connection for the bundled PostgresqlDemo workflow — points to the internal postgres-demo database by default."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Demo",
    "tags": ["postgresql", "database", "connection", "demo"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
