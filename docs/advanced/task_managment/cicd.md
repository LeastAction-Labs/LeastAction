# **LeastAction CI/CD**

## **Overview**

LeastAction CI/CD lets you manage your task definitions in Git and deploy them into LeastAction automatically. Instead of creating tasks manually in the UI every time, you define tasks as files in a Git repository and use the **LeastActionGitToTask** action to sync them into your workflow.

This means your task catalog is version-controlled, reviewable via pull requests, and deployable with a single click — or automatically before your workflow runs.

> **Public examples**: Working sample task files and workflow configs are available at [https://github.com/LeastAction-Labs/LeastAction-samples](https://github.com/LeastAction-Labs/LeastAction-samples)

---

## **How It Works**

The **LeastActionGitToTask** action:

1. Clones your Git repository (using a Git connection for credentials)
2. Walks a specified folder path inside the repo
3. Reads each task file, parses its metadata and payload
4. Creates any new tasks it finds in LeastAction under your workflow folder
5. Skips tasks that already exist (unless `over_ride: true` is set in the file)

**Two ways to trigger it:**

| Mode | How | When to use |
|------|-----|-------------|
| **Manual** (UI Action) | Click the action button on a workflow or folder | On-demand deploys, first-time setup |
| **Automatic** (PreAction) | Attach as `preAction` on a root task | Auto-deploy before every workflow run |

---

## **Task File Format**

Each file in your Git repo represents one task. Supported file types: `.py`, `.sql`, `.yaml`.

The file has two parts:
1. **Metadata block** — a JSON comment at the top describing how to create the task
2. **Payload** — the actual code/query/script that runs (everything after the metadata)

### **Metadata Fields**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Task name (defaults to filename without extension) |
| `operator_name` | Yes | Name of the operator in LeastAction catalog |
| `connection_name` | Yes | Name of the connection in LeastAction catalog |
| `config_name` | No | Config name(s) to attach — string or list of strings |
| `frequency` | No | Cron expression (default: `"*/3 * * * *"`) or `"ADHOC"` |
| `partition` | No | Partition name (default: `"ALL"`) |
| `start_date` | No | Task start date |
| `end_date` | No | Task end date |
| `over_ride` | No | `true` to force re-create even if task already exists (default: `false`) |
| `actions` | No | Pre/running/post actions to attach to the task |

### **Format Examples**

**Python file (`/* */` comment block):**
```python
/*
{
  "name": "daily_sales_load",
  "operator_name": "AWSLambdaInvokeFunction",
  "connection_name": "aws-prod",
  "config_name": "sales-workflow-config",
  "frequency": "0 6 * * *",
  "partition": "ALL"
}
*/

import boto3

def handler(event, context):
    # actual task logic here
    pass
```

**SQL file (`/* */` comment block):**
```sql
/*
{
  "name": "transform_daily_revenue",
  "operator_name": "AthenaExecuteSQL",
  "connection_name": "aws-prod",
  "frequency": "0 7 * * *"
}
*/

INSERT INTO analytics.daily_revenue
SELECT date, SUM(amount) as revenue
FROM raw.transactions
WHERE date = '{{ ds }}'
GROUP BY date
```

**Python file (leading `#` comment block):**
```python
# {
#   "name": "run_spark_job",
#   "operator_name": "SparkSubmitJob",
#   "connection_name": "databricks-prod",
#   "config_name": ["spark-config", "env-config"],
#   "frequency": "0 8 * * *"
# }

spark.sql("SELECT * FROM events WHERE date = '{{ ds }}'")
```

**YAML file:**
```yaml
# {
#   "name": "export_to_s3",
#   "operator_name": "AWSS3MoveData",
#   "connection_name": "aws-prod",
#   "frequency": "ADHOC"
# }

source: analytics.daily_revenue
destination: s3://data-lake/exports/{{ ds }}/
```

### **Attaching Actions in Task Files**

You can also define pre/running/post actions inside the task metadata:

```python
/*
{
  "name": "pipeline_start",
  "operator_name": "PythonScript",
  "connection_name": "python-env",
  "frequency": "0 5 * * *",
  "actions": {
    "pre_actions": [
      {
        "action_name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {}
      }
    ],
    "post_actions": [
      {
        "action_name": "LeastActionFindTasksReadyToRun",
        "action_variables": {}
      }
    ],
    "running_actions": []
  }
}
*/

# task code here
```

### **Force Re-create**

By default, `LeastActionGitToTask` skips tasks that already exist. To force re-creation:

```python
/*
{
  "name": "my_task",
  "operator_name": "PythonScript",
  "connection_name": "python-env",
  "over_ride": true
}
*/
```

> **Note**: If a task was deleted and is now in the Trash, it cannot be re-imported until you restore it or permanently delete it from the Trash.

---

## **Git Repository Folder Structure**

The `folder_path` variable tells the action where to look inside your repo. All `.py`, `.sql`, and `.yaml` files found recursively under that path are treated as task files.

```
my-repo/
└── tasks/                    ← set folder_path = "tasks"
    ├── extract_sales.sql
    ├── transform_revenue.py
    ├── load_to_warehouse.sql
    └── daily_summary.yaml
```

---

## **Setting Up CI/CD**

### **Prerequisites**

1. A Git repository with task files
2. A **Git connection** in LeastAction with your credentials (`git_username` and `git_token`)
3. The **LeastActionGitToTask** action available in your catalog (from LeastAction Labs or marketplace)
4. Your `workflow_folder_laui` — visible in the item details panel in the UI

---

### **Option 1: Manual Deploy (UI Action)**

This is the simplest setup. You click a button in the UI to pull and deploy tasks from Git.

**Step 1: Add LeastActionGitToTask as a UI Action via Config**

Create or update your workflow config to include `LeastActionGitToTask` in `uiActions` with default variables pre-filled:

```json
{
  "defaults": {
    "uiActions": [
      {
        "action": "LeastActionGitToTask",
        "connection": "my-github-connection",
        "variables": {
          "git_repo_url": "https://github.com/my-org/my-repo.git",
          "git_branch": "main",
          "folder_path": "tasks/",
          "partition": "ALL",
          "workflow_folder_laui": "<your-workflow-folder-laui>"
        }
      }
    ]
  }
}
```

Attach this config to your workflow folder. The next time you open the workflow in the UI, the `LeastActionGitToTask` button will appear with all fields pre-filled.

**Step 2: Run the Action**

1. Navigate to your workflow folder in the UI
2. Click the **LeastActionGitToTask** action button
3. The form opens — all fields are pre-filled from the config defaults
4. Select your **Git connection** (with your `git_username` and `git_token`)
5. Click **Run**

LeastAction will clone your repo, find all task files under `folder_path`, and create any new tasks in your workflow.

---

### **Option 2: Automatic Deploy (PreAction on Root Task)**

This pattern automatically deploys tasks from Git before every workflow run. Useful when your task definitions change frequently and you want them always in sync.

**How it works:**
- You designate one task as the "root" of your workflow (the first task that runs, with no parents)
- `LeastActionGitToTask` is set as a `preAction` on that root task
- Every time the workflow runs, the root task first syncs tasks from Git, then the rest of the workflow proceeds

**Step 1: Set up default preAction via Config**

```json
{
  "defaults": {
    "task": {
      "preAction": [
        {
          "action": "LeastActionGitToTask",
          "connection": "my-github-connection",
          "variables": {
            "git_repo_url": "https://github.com/my-org/my-repo.git",
            "git_branch": "main",
            "folder_path": "tasks/",
            "partition": "ALL",
            "workflow_folder_laui": "<your-workflow-folder-laui>"
          }
        }
      ]
    }
  }
}
```

Attach this config to your workflow. All tasks in the workflow will inherit this preAction.

**Step 2: Limit the preAction to only the root task**

Since you only want the root task to run the sync (not every task), remove the preAction from individual tasks and add it only to the root task's task-level config or define it explicitly on that task during creation.

Alternatively, keep the default config simple and attach the preAction directly when creating the root task via the task creation form's `actions` field:

```json
{
  "preAction": [
    {
      "action": "LeastActionGitToTask",
      "connection": "my-github-connection",
      "variables": {
        "git_repo_url": "https://github.com/my-org/my-repo.git",
        "git_branch": "main",
        "folder_path": "tasks/",
        "partition": "ALL",
        "workflow_folder_laui": "<your-workflow-folder-laui>"
      }
    },
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {}
    }
  ]
}
```

---

## **Action Variables Reference**

| Variable | Description | Example |
|----------|-------------|---------|
| `git_repo_url` | Full URL of the Git repository | `https://github.com/org/repo.git` |
| `git_branch` | Branch to clone | `main` |
| `folder_path` | Path inside repo to scan for task files | `tasks/pipelines/` |
| `partition` | Partition for all created tasks | `ALL` |
| `start_date` | Default start date for created tasks | `2026-01-01` |
| `end_date` | Default end date for created tasks | `2026-12-31` |
| `workflow_folder_laui` | Folder where tasks will be created | `<laui of workflow folder>` |

> **Note**: `start_date` and `end_date` from action variables override values set in task file metadata. Dates are skipped for `ADHOC` tasks.

## **Connection Reference**

The Git connection must have:

| Field | Description |
|-------|-------------|
| `git_username` | Git username or service account name |
| `git_token` | Personal access token (PAT) or password |

For public repositories, the connection is still required but `git_username` and `git_token` can be left blank.

---

## **CI/CD Workflow Example: End-to-End**

**Scenario**: You have a daily ETL pipeline defined in Git. When a developer merges a PR, the next workflow run automatically picks up the new task definitions.

**Repository structure:**
```
data-pipelines/
└── production/
    ├── extract_crm.sql
    ├── transform_opportunities.py
    └── load_to_warehouse.sql
```

**extract_crm.sql:**
```sql
/*
{
  "name": "extract_crm_daily",
  "operator_name": "AthenaExecuteSQL",
  "connection_name": "aws-prod",
  "config_name": "etl-workflow-config",
  "frequency": "0 5 * * *",
  "partition": "ALL"
}
*/

SELECT * FROM crm.opportunities WHERE updated_date = '{{ ds }}'
```

**Workflow config** (attached to the workflow folder in LeastAction):
```json
{
  "defaults": {
    "uiActions": [
      {
        "action": "LeastActionGitToTask",
        "connection": "github-service-account",
        "variables": {
          "git_repo_url": "https://github.com/my-org/data-pipelines.git",
          "git_branch": "main",
          "folder_path": "production",
          "partition": "ALL",
          "workflow_folder_laui": ""
        }
      }
    ]
  },
  "parameters": {
    "environment": "production",
    "s3_bucket": "s3://data-lake-prod"
  },
  "not_overridable": ["environment", "s3_bucket"]
}
```

**Deploy flow:**
1. Developer opens PR with a new task file
2. PR is reviewed and merged to `main`
3. In LeastAction, user navigates to the workflow and clicks **LeastActionGitToTask**
4. New task appears in the workflow — no manual form filling needed

---

## **Troubleshooting**

### **Task already exists — not re-created**

By default the action skips existing tasks. If you want to force re-creation, add `"over_ride": true` to the task file metadata.

### **Task is in Trash — import fails**

The action cannot re-import tasks that are in the Trash. Restore the task from the Trash or permanently delete it, then run the action again.

### **Operator / Connection not found**

The `operator_name` and `connection_name` in your task file must exactly match the `name` field of items in the LeastAction catalog (case-sensitive). Check the catalog for the correct name.

### **Config not found**

Same as above — `config_name` must match the exact name of a config item in the catalog.

### **Action fails with authentication error**

Verify your Git connection has the correct `git_username` and `git_token`. For GitHub, use a Personal Access Token with `repo` scope.

### **No tasks created — folder path wrong**

The `folder_path` is relative to the root of the cloned repo. Double-check the path exists in the branch you specified.
