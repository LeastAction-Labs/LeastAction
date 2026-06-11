<action/doc done>

You are an AI data engineer, lets write a manage-with-notify pattern — actions that send notifications at key pipeline moments so teams can react, approve, escalate, or just stay informed without watching dashboards

Context:
 - Notifications can be sent at any action hook: preAction, postAction, or UI action on any item
 - Common notification targets: SMTP email, Slack webhook, AWS SNS, PagerDuty webhook, MS Teams webhook, generic HTTP POST
 - connection will hold the credentials/endpoints for the notification target (webhook url, smtp creds, SNS arn, etc.)
 - action variables carry context: task name, workflow, date, status, recipients, message, thresholds
 - when using UI action, fields like task_lauis and item_lauis is auto filled based on table item selection, it will be an array
 - task context available in action: task name, logical_date, state, last_run_date, partition, project
 - this action is just an example, what an action can do is upto the users imagination
 - when using API to get list of items for children always send the item type, cause the item could have n, and it could be an expensive n loops to get, so folder to child folders get folder, for folder with child reports or task get them specifically
 - action can be added using config LeastAction/frontend/docs/advanced/action.md

 Notify use cases to cover (pick the ones most relevant or do all):
  - task failure alert: postAction on failure, sends to on-call team, includes task name, date, error context
  - SLA breach alert: preAction or postAction that checks if task is running late vs expected window, sends escalation
  - data quality gate: postAction that checks row count or a quality score table, sends alert and optionally holds downstream (returns false)
  - approval needed: postAction that notifies a reviewer that a report or artifact is ready for review (links to catalog item)
  - pipeline complete digest: postAction on the final task, sends a summary of all task states in the workflow for that date
  - bulk status notify from UI: UI action on selected tasks, sends a status email or Slack with the selected tasks state
  - Notify then skip: postAction or UI action that sends a notification and marks tasks as skipped (useful for known-bad partitions)

Output options (choose one or both):
 - code: location LeastAction/backend/bootstrap/ideas/done/[folder name], files: name.py, name.connection, name.bashblock, name.action_variables, copy this skill to the folder, add skill name as comment header
 - doc: location LeastAction/frontend/docs/examples/, add a folder with appropriate name, format md, blog-style title, target audience AI data engineer building for leadership

 - Expand on any of context and also mention use existing example to learn how to create actions that can do this, if context does not have specifics.
 - Don't add info to other links as the final rendering is done by react
 - for doc: this action is just an example, what an action can do is upto the users imagination
 - update the usecases_skills_doc that is a mismatch, this skill context is the correct one
 - update or add to LeastAction/frontend/docs/examples/ if a doc mismatch exists

Examples:
 - LeastAction/backend/bootstrap/ideas/done/ApproveAndSendReport/ — action that notifies + acts on catalog items
 - LeastAction/backend/bootstrap/ideas/done/GitToTask/ — action structure reference
 - LeastAction/frontend/docs/examples/reporting_asset_management/report-approval-workflow.md — notify-then-approve pattern
 - LeastAction/frontend/docs/examples/managing_at_scale/backfill-and-dependency-at-scale.md — pipeline scale context
 - LeastAction/backend/onboarding_setup - built in stuff
 - for doc skill used in past: LeastAction/backend/bootstrap/ideas/usecases_skills_doc/asset_ui_actions_ai_reporting.md
