# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "dbt"

connection = {
  "dbt_server_url": "http://dbt-demo:8001"
}

prompt = "Connect to the bundled dbt-demo server for running dbt models via the DBTRunModel operator."

install_docs = """# DbtServer — Connection Setup

Points to the `dbt-demo` container that ships with the LeastAction docker-compose
stack. The dbt-server provides /health, /run-model, /run-seed, and /list-models
HTTP endpoints that the DBTRunModel and DBTRunSelectModel operators call.

## Fields
| Field | Value | Notes |
|---|---|---|
| dbt_server_url | http://dbt-demo:8001 | Internal docker hostname + port |
"""

guide_docs = """# DbtServer — Connection Guide

Used by `DBTRunModel` and `DBTRunSelectModel` operators, referenced as
`DbtServer` via `connection_name`. Provides the dbt-server HTTP URL.
"""

description = "dbt-server connection for running dbt models via the bundled dbt-demo container."

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Demo",
    "tags": ["dbt", "dbt-server", "connection", "demo"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
