# Notify & Control Pipelines

Actions run at lifecycle hooks (pre / running / post / UI). Two families: **notify** (tell a human) and **control** (act on the pipeline).

## Notify

Attach a notification action at any hook. `LeastActionWebhookNotify` ships built-in (configure a Slack webhook in a connection); email is `LeastActionSMTPEmail`; any other target (SNS, Teams, PagerDuty, HTTP) is a small custom action. Message strings template from task context (`{{task_name}}`, `{{logical_date}}`, `{{state}}`, `{{partition}}`, …). Common uses: failure alerts (`run_on_states: ["failed"]`), approval-needed pings, SLA breaches, pipeline-complete digests.

→ Worked example: the **`leastaction-pipelines-notify`** usecase.

## Control

Built-in control actions compose at a hook to observe state, decide, and act:

`LeastActionRunTask` · `LeastActionRerun` · `LeastActionRerunSubtree` · `LeastActionCancelTask` · `LeastActionSkip` · `LeastActionSkipSubtree`

Patterns: SLA watchdog (cancel stuck tasks), auto-retry with attempt cap, start-child-on-success (event-driven sub-pipelines), data-quality enforce (skip the subtree on bad output), partition triage from the UI, staged escalation.

→ Worked example: the **`leastaction-pipelines-control`** usecase.

## Report approval & distribution

For report workflows, `ApproveAndSendReport` emails + archives + publishes a report (manual review or auto-approval). → the **`leastaction-reporting-approval`** + **`leastaction-reporting-distribution`** usecases, and [Assets & Reports](/path?laui=getting-started-07-working-in-the-ui-01-assets-and-reports&itemtype=doc.file&itemname=Assets%20And%20Reports).

## Reference

- Action lifecycle, configuration, and the full built-in list: [Action concept](/path?laui=getting-started-04-concepts-06-action&itemtype=doc.file&itemname=Action) and [Write an Action](/path?laui=getting-started-05-building-pipelines-02-write-an-action&itemtype=doc.file&itemname=Write%20An%20Action).
- UI actions: [UI Actions](/path?laui=getting-started-07-working-in-the-ui-02-ui-actions&itemtype=doc.file&itemname=Ui%20Actions).

> Always test control actions on one task / a small partition first — they make real changes.
