# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
config_type = "task"

prompt = "Task config for PostgreSQL sales reporting workflow. Configures GitToTask action for syncing demo tasks and auto-reschedule on error/fail states."

install_docs = """# PostgresqlSalesReportingForWorkflow — Config Guide

This config is attached to a workflow task and configures:
- uiActions: LeastActionGitToTask to sync demo tasks from GitHub
- LeastActionReschedule on error/fail states
"""

guide_docs = """# PostgresqlSalesReportingForWorkflow — Config Guide

Workflow config for the PostgreSQL sales reporting demo. Attaches git sync and reschedule
actions to the workflow task. No cron or parameter overrides needed.
"""

description = "Task config for PostgreSQL sales reporting demo workflow with GitToTask and auto-reschedule actions."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Configuration",
    "tags": ["postgresql", "sales", "reporting", "workflow", "config"]
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
        "action": "LeastActionGitToTask",
        "variables": {
          "git_repo_url": "https://github.com/LeastAction-Labs/LeastAction-samples.git",
          "git_branch": "main",
          "folder_path": "DemoSaleReportingTasks_Postgresql",
          "workflow_folder_name": "workflow",
          "partition": "ALL",
          "state": [
            "running"
          ]
        }
      },
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