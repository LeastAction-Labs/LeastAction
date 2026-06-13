# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
config_type = "task"

prompt = "Task config for the PostgresqlDemo 3-step workflow (create/insert/update on the 'people' table). Reschedules tasks automatically on error or fail states."

install_docs = """# PostgresqlDemoWorkflow — Config Guide

Attach this config to each task in the PostgresqlDemo usecase via `config_name`.
It configures:
- LeastActionReschedule on error/fail states, so a transient connection issue
  retries automatically instead of leaving the demo stuck.
"""

guide_docs = """# PostgresqlDemoWorkflow — Config Guide

Workflow config for the PostgresqlDemo demo (create_table -> insert_rows -> update_rows).
No git sync is needed since the demo's SQL payloads are bundled directly in the usecase.
"""

description = "Task config for the PostgresqlDemo workflow with auto-reschedule on error/fail."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Configuration",
    "tags": ["postgresql", "demo", "workflow", "config"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

config = {
  "defaults": {
    "task": {},
    "cron": {},
    "taskControlActions": [],
    "uiActions": [
      {
        "action": "LeastActionReschedule",
        "variables": {
          "state": [
            "error",
            "fail"
          ]
        }
      }
    ]
  },
  "parameters": {},
  "partition": "",
  "git": {},
  "priority": [],
  "overridable": [],
  "not_overridable": {}
}
