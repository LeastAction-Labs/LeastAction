<action/doc done>

You are an AI data engineer, lets write an advanced manage-with-running-actions pattern — actions that don't just notify but actively control pipeline execution: cancel stuck tasks, start child tasks, enforce SLA windows, skip bad partitions, and chain reactions automatically

This is the next level beyond the notify pattern in manage_with_notify_actions.md — actions that observe state and act on it, not just report it.

Context:
 - Running actions combine observation (check task state, timing, data quality) with execution (cancel, run, skip, rerun) and optionally notification
 - Built-in task control actions available: LeastActionRun, LeastActionRerun, LeastActionRerunSubtree, LeastActionCancel, LeastActionSkip, LeastActionSkipSubtree
 - LeastActionSlackNotify is built in for notification as part of a chain
 - These can be chained: check → act → notify, all as postActions or preActions in sequence
 - connection holds credentials for any external system (monitoring, quality DB, external APIs)
 - action variables carry thresholds, target task identifiers, SLA windows, partition filters
 - when using UI action, fields like task_lauis and item_lauis is auto filled based on table item selection, it will be an array
 - task context available in action: task name, logical_date, state, last_run_date, partition, project, laui
 - when using API to get list of items for children always send the item type — folder to child folders: get folder, folder with child tasks: get task — avoids expensive n loops
 - Catalog API for task lookup and state: LeastAction/frontend/src/services/catalog.service.ts
 - LeastActionCheckIfParentsAreDone.py — reference for how to query task state and timing from within an action
 - this action is just an example, what an action can do is upto the users imagination
 - action can be added using config LeastAction/frontend/docs/advanced/action.md
 - also make a note of test before use, depending on what the action does it could create mess, keep all code in git

 Running action use cases to cover (pick the most relevant or do all):
  - SLA watchdog: preAction that checks how long the task has been running, if over threshold cancel it and notify — prevents stuck tasks from blocking the pipeline
  - SLA start gate: preAction that checks if upstream conditions are met within an SLA window, if not skip self and notify — avoids running with stale data
  - Auto-retry on failure: postAction on failure that reruns the task (with max attempt guard), then notifies if max retries hit
  - Cancel and skip subtree: UI action or postAction that cancels a running task and skips all downstream — useful when bad data is confirmed mid-run
  - Start child on success: postAction that directly triggers a specific child task (by name/partition) rather than waiting for scheduler — useful for event-driven sub-pipelines
  - Data quality enforce: postAction that queries a quality score table, if below threshold skips downstream subtree and notifies — harder gate than just returning false
  - Partition triage: UI action on selected tasks that checks each partition's state, skips the failed ones, reruns the pending ones, notifies with a summary
  - SLA breach escalation chain: postAction that checks timing, if breached: notify tier-1 → wait → if still not done cancel and notify tier-2 escalation

Output options (choose one or both):
 - code: location LeastAction/backend/bootstrap/ideas/done/[folder name], files: name.py, name.connection, name.bashblock, name.action_variables, copy this skill to the folder, add skill name as comment header
 - doc: location LeastAction/frontend/docs/examples/, add a folder with appropriate name, format md, blog-style title, target audience AI data engineer building for leadership

 - Expand on any of context and also mention use existing example to learn how to create actions that can do this, if context does not have specifics.
 - Don't add info to other links as the final rendering is done by react
 - for doc: mention manage_with_notify_actions doc as the simpler starting point, this is the advanced version
 - for doc: this action is just an example, what an action can do is upto the users imagination
 - update the usecases_skills_doc that is a mismatch, this skill context is the correct one
 - update or add to LeastAction/frontend/docs/examples/ if a doc mismatch exists

Examples:
 - LeastAction/backend/onboarding_setup/actions/LeastActionLabs/LeastActionCheckIfParentsAreDone.py — how to query task state + timing from within an action
 - LeastAction/backend/bootstrap/ideas/done/ApproveAndSendReport/ — action that reads catalog state and acts
 - LeastAction/frontend/docs/examples/notify_and_manage/notify-and-manage-pipelines.md — the simpler notify-first version, reference and link from the new doc
 - LeastAction/frontend/docs/examples/managing_at_scale/backfill-and-dependency-at-scale.md — task control actions context
 - LeastAction/backend/onboarding_setup — built-in action reference
 - for doc skill used in past: LeastAction/backend/bootstrap/ideas/usecases_skills_doc/manage_with_notify_actions.md
