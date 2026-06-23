# Actions in the UI — Guide

This guide covers how to work with actions through the LeastAction UI: attaching UI actions to items, configuring task control actions on workflows, and running actions manually.

For the full action reference (lifecycle types, configuration format, available actions, AI generation), see the [Action Feature Guide](/path?laui=getting-started-04-concepts-06-action&itemtype=doc.file&itemname=Action%20Aka%20Hook).

---

## UI Actions

UI Actions appear as buttons on catalog items (tasks, assets, workflows). When clicked, they open a form, collect input, and execute the action.

### Attaching UI Actions

UI actions are attached via config. Add them to the `uiActions` array in a workflow config or task config:

```json
{
  "uiActions": [
    {
      "action": "LeastActionImportPostgres",
      "connection": "PostgresProd",
      "variables": {
        "schema": "public",
        "tables": ["all"],
        "importViews": false
      }
    }
  ]
}
```

Any variables defined here become form defaults. Users can override them before running.

### Running a UI Action

1. Open the item in the catalog (task, asset, or workflow folder)
2. The action button appears in the item's action bar
3. Click the button — a form opens with the action's fields pre-filled from config defaults
4. Fill in or adjust any fields
5. Click **Run** — execution result (true/false) and logs are shown immediately

---

## Task Control Actions

Task control actions appear as buttons on tasks in the task list or task detail view. They control task state (run, rerun, cancel, skip).

### Attaching Task Control Actions

Configure them in the `taskControlActions` array on the workflow config:

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionCancel",
      "variables": {
        "taskStatus": ["running", "scheduled"]
      }
    },
    {
      "action": "LeastActionRerun",
      "variables": {
        "taskStatus": ["error", "failed"]
      }
    },
    {
      "action": "LeastActionSkipSubtree",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
      }
    }
  ]
}
```

The `taskStatus` filter controls when each button is visible. A **Cancel** button only appears when the task is `running` or `scheduled`; a **Rerun** button only appears when the task is in `error` or `failed`.

### Available Task Control Actions

| Action | Effect |
|---|---|
| `LeastActionRun` | Start execution |
| `LeastActionRerun` | Re-execute |
| `LeastActionRerunSubtree` | Re-execute task and all children |
| `LeastActionCancel` | Stop a running task |
| `LeastActionSkip` | Mark as skipped |
| `LeastActionSkipSubtree` | Skip task and all children |
| `LeastActionSkipPostDoneS3` | Skip and write S3 completion marker |

---

## Config UI Actions and Task Control

Config items themselves can also be assigned UI actions and task control actions. This means the same config attached to a workflow automatically installs those buttons on every task in that workflow — without configuring each task individually.

See [Config Guide](/path?laui=getting-started-04-concepts-05-config&itemtype=doc.file&itemname=Config) for the full config structure including `defaults.taskControlActions` and `defaults.uiActions`.

---

## Discovering and Importing Actions

Community-built actions are available in the [Marketplace](/path?laui=getting-started-07-working-in-the-ui-03-marketplace&itemtype=doc.file&itemname=Marketplace). Browse by type, import compatible actions into your catalog, and reference them by name in your config.
