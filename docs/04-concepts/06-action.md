# **LeastAction Actions \- Feature Guide**

## **Overview**

"Actions" are small, reusable building blocks that can be created using LeastAction's AI and saved to your catalog or marketplace. Actions allow users to manage different parts of the service without depending on service providers for fixed functions.

Instead of building everything into the orchestrator, LeastAction provides a flexible action system that can do ANYTHING, and let AI generate the actions.

**Note 1:** Actions are not permissions. Actions use the permission access management set in the catalog to run.

**Note 2:** Actions can be created using AI, please refer to the "Creating Actions with AI" section below for more details.

**Note 3:** Community driven Actions can be discovered in the marketplace, please refer to the marketplace guide doc on how to search, discover and publish.

## **Action Types**

### **1\. UI Actions**

UI Actions require a form to be filled in the UI and can be attached to any UI item (tasks, assets, workflows, etc.) via config.

**Examples:**

* **Task UI Actions** \- Manage task UI data (e.g., LeastActionGitToTask)
* **Asset UI Actions** \- Manage asset data (e.g., PostgresqlToClaudeChatToHtmlReportToAsset or PostgresqlTestConnection)


**Characteristics:**

* Always invoked manually through the UI
* Can use connection resources
* Require user input via forms
* Form fields can have defaults set in config, unset fields will be empty
* Form fields are derived from the action example template
* Return Boolean (true or false) results directly to the user
* Details of execution are logged and presented on the screen

### **2\. Task Control Actions**

Task Control Actions manage task execution metadata and state. These are typically triggered by users or automation to control running tasks. Task control actions are **workflow-level only** — they are configured on the workflow (via config or directly) and apply to all tasks in that workflow.

**Available Control Actions:**

* **LeastActionRunTask** \- Start task execution
* **LeastActionCancelTask** \- Stop a running task
* **LeastActionScheduleTasks** \- Schedule or reschedule tasks

**Characteristics:**

* Change task execution state
* Can use connection resources if needed (e.g., a custom action to skip and drop S3 file)
* Can be invoked via UI, API, or programmatically in tasks (use with caution)
* Use APIs like UpdateTask, sendToExecution, RecursiveListChildren
* Can be filtered by task status when configured as UI actions

### **3\. Task Lifecycle Actions**

Task Lifecycle Actions are automatically invoked at specific points during a task's lifecycle. These are configured to run automatically and do not include cron scheduling (which runs independently).

**Lifecycle Hooks:**

1. **CreateAction** \- Runs when task is created
2. **PreAction** \- Runs before task execution starts
3. **RunningAction** \- Runs during task execution when SLA(mins) is met
4. **RunningIntervalAction** \- Runs during task execution based on interval(mins) specified
5. **PostAction** \- Runs after task completes

**Common Lifecycle Actions:**

* **LeastActionCheckIfParentsAreDone** (PreAction) \- Validate parent completion
* **LeastActionGitToTask** (PreAction) \- Sync code from Git
* **LeastActionWebhookNotify** (RunningAction/RunningIntervalAction/PostAction) \- Send notifications

**Characteristics:**

* Configured in workflow/task defaults
* Execute automatically without user intervention
* Can use connection resources
* Return Boolean (PreAction/CreateAction) or nothing (RunningAction/RunningIntervalAction/PostAction)
* Can use runtime or create time parameters

## **How Actions Work**

### **Invocation Methods**

| Action Type | Invoked Via | Return Value | User Interaction |
| ----- | ----- | ----- | ----- |
| UI Actions | UI forms | Boolean | Required |
| Task Control | UI, API, tasks | Boolean | Optional |
| CreateAction | Task creation | Boolean | None |
| PreAction | Before execution | Boolean | None |
| RunningAction | During execution | Nothing | None |
| RunningIntervalAction | During execution | Nothing | None |
| PostAction | After execution | Nothing | None |

### **Action Configuration**

Actions are configured in 2 ways:

**Via Config**

Via Config lets users set defaults and these will be used in any task created in a workflow or catalog folder it is attached to.

```json
{
  "defaults": {
    "taskActions": {
      "preAction": [
        {
          "action": "LeastActionCheckIfLocalFileExists",
          "variables": {
            "file_path": "/data/input/{{ds}}/ready.flag"
          }
        },
        {
          "action": "LeastActionCheckIfParentsAreDone",
          "variables": {
            "parents": [
              {
                "task_name": "parent_task_name",
                "project_laui": "{{project_laui}}",
                "account_laui": "{{account_laui}}",
                "partition": "{{partition}}"
              }
            ]
          }
        }
      ],
      "RunningAction": [
        {
          "action": "LeastActionWebhookNotify",
          "sla": 10,
          "connection": "SlackProd",
          "variables": {
            "channel": "#alerts",
            "message": "Task {{name}} exceeded SLA"
          }
        }
      ],
      "runningIntervalAction": [
        {
          "action": "AWSS3KeyExists",
          "interval": 10,
          "connection": "AWSProd",
          "variables": {
            "bucket_name": "data-lake",
            "key": "output/{{ds}}/done.flag"
          }
        }
      ],
      "postAction": [
        {
          "action": "LeastActionTaskToTableAsset",
          "variables": {
            "parent_laui": "<asset-folder-laui>"
          }
        },
        {
          "action": "LeastActionSMTPEmail",
          "connection": "SMTPProd",
          "variables": {
            "to": "team@company.com",
            "subject": "Task {{name}} completed for {{ds}}",
            "body": "Pipeline finished successfully."
          }
        }
      ]
    },
    "taskControlActions": [
      {
        "action": "LeastActionCancelTask",
        "variables": {
          "taskStatus": ["running", "scheduled"]
        }
      },
      {
        "action": "LeastActionRunTask",
        "variables": {
          "taskStatus": ["error", "failed"]
        }
      },
      {
        "action": "LeastActionScheduleTasks",
        "variables": {
          "taskStatus": ["scheduled", "waiting"]
        }
      }
    ],
    "uiActions": [
      {
        "action": "LeastActionGitToTask",
        "connection": "GitHubMain",
        "variables": {
          "git_repo_url": "https://github.com/org/repo.git",
          "git_branch": "main"
        }
      }
    ]
  }
}
```

**Via Task Creation Form Field "actions"**

```json
{
  "preAction": [
    {
      "action": "AWSS3KeyExists",
      "connection": "AWSProd",
      "variables": {
        "bucket_name": "data-lake-prod",
        "key": "raw/{{ds}}/input.csv"
      }
    },
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {
        "parents": [
          {
            "task_name": "parent_task_name",
            "project_laui": "{{project_laui}}",
            "account_laui": "{{account_laui}}",
            "partition": "{{partition}}"
          }
        ]
      }
    }
  ],
  "RunningAction": [
    {
      "action": "LeastActionWebhookNotify",
      "sla": 10,
      "connection": "SlackProd",
      "variables": {
        "channel": "#alerts",
        "message": "Task exceeded SLA"
      }
    }
  ],
  "runningIntervalAction": [
    {
      "action": "AWSS3KeyExists",
      "interval": 5,
      "connection": "AWSProd",
      "variables": {
        "bucket_name": "data-lake",
        "key": "output/{{ds}}/done.flag"
      }
    }
  ],
  "postAction": [
    {
      "action": "LeastActionTaskToTableAsset",
      "variables": {
        "parent_laui": "<asset-folder-laui>",
        "table_name": "daily_sales_{{ds}}"
      }
    },
    {
      "action": "LeastActionSMTPEmail",
      "connection": "SMTPProd",
      "variables": {
        "to": "team@company.com",
        "subject": "Task {{name}} completed",
        "body": "Pipeline finished for {{ds}}"
      }
    }
  ]
}
```

## **Prerequisites**

* Catalog permission access management must be configured
* Actions inherit permissions from catalog settings
* All actions receive execution context data
* Connection resources must be configured before use in actions

## **Core Use Cases**

### **Task Dependency Management**

Using Task Lifecycle Actions to manage dependencies:

**PreAction \+ PostAction Pattern:**

1. **LeastActionCheckIfParentsAreDone** (PreAction) \- Validates parent completion before execution
2. **LeastActionTaskToTableAsset** (PostAction) \- Registers task output as a catalog asset for lineage tracking
3. **LeastActionWebhookNotify** (PostAction) \- Notifies on completion so teams know downstream tasks can proceed

**Example flow of using above actions:**

1. Create workflow (config auto-created/attached)
2. Create task with dependency preAction and post-execution actions
3. Default actions are attached from config (sample below)
4. Before execution, LeastActionCheckIfParentsAreDone validates all parents have completed
5. After execution, LeastActionTaskToTableAsset registers output and LeastActionWebhookNotify sends a notification
6. The cron scheduler picks up downstream tasks that are ready to run at regular intervals

**Sample**

```json
{
  "preAction": [
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {
        "parents": [
          {
            "task_name": "parent_task",
            "project_laui": "{{project_laui}}",
            "account_laui": "{{account_laui}}",
            "partition": "{{partition}}"
          }
        ]
      }
    }
  ],
  "postAction": [
    {
      "action": "LeastActionTaskToTableAsset",
      "variables": {
        "parent_laui": "<asset-folder-laui>"
      }
    },
    {
      "action": "LeastActionWebhookNotify",
      "connection": "SlackProd",
      "variables": {
        "channel": "#pipeline-status",
        "message": "Task {{name}} completed for {{ds}}"
      }
    }
  ]
}
```

### **Pre-Execution File Sensor**

Wait for a file to exist before starting the task. Use `AWSS3KeyExists` for S3 files or `LeastActionCheckIfLocalFileExists` for local files:

**S3 file sensor:**

```json
{
  "preAction": [
    {
      "action": "AWSS3KeyExists",
      "connection": "AWSProd",
      "variables": {
        "bucket_name": "data-lake-prod",
        "key": "raw/{{ds}}/input.csv"
      }
    },
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {
        "parents": [{"task_name": "extract_data", "project_laui": "{{project_laui}}", "account_laui": "{{account_laui}}", "partition": "{{partition}}"}]
      }
    }
  ]
}
```

**Local file sensor:**

```json
{
  "preAction": [
    {
      "action": "LeastActionCheckIfLocalFileExists",
      "variables": {
        "file_path": "/data/input/{{ds}}/ready.flag"
      }
    }
  ]
}
```

### **CI/CD Integration**

LeastAction supports CI/CD via the `LeastActionGitToTask` action:

**Task Catalog Sync (LeastActionGitToTask)**

Deploy task definitions from a Git repo into LeastAction. Task files in Git contain both the metadata (operator, connection, schedule) and the payload (code/SQL). The action reads the repo and creates/updates tasks in your workflow.

Can be used as a **UI action** (manual deploy button on a workflow) or as a **preAction** on a root task (auto-deploy before every workflow run):

```json
{
  "preAction": [
    {
      "action": "LeastActionGitToTask",
      "connection": "GitHubMain",
      "variables": {
        "git_repo_url": "https://github.com/org/repo.git",
        "git_branch": "main",
        "folder_path": "tasks/",
        "partition": "ALL",
        "workflow_folder_laui": "<workflow-folder-laui>"
      }
    }
  ]
}
```

See the [CI/CD guide](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Cicd) for the full setup, task file format, and examples.

### **SLA Monitoring with Notifications**

Monitor task execution time and send alerts:

```json
{
  "RunningAction": [
    {
      "action": "LeastActionWebhookNotify",
      "sla": 60,
      "connection": "SlackProd",
      "variables": {
        "channel": "#data-alerts",
        "message": "Task {{name}} (session: {{session_id}}) exceeded 60 minute SLA",
        "severity": "warning"
      }
    }
  ]
}
```

### **S3 File Monitoring During Execution**

Monitor S3 for a file at regular intervals during task execution:

```json
{
  "runningIntervalAction": [
    {
      "action": "AWSS3KeyExists",
      "interval": 5,
      "connection": "AWSProd",
      "variables": {
        "bucket_name": "data-lake-prod",
        "key": "output/{{ds}}/results.parquet"
      }
    }
  ]
}
```

### **Post-Execution: Register Output & Notify**

After a task completes, register its output as a catalog asset and send a notification:

```json
{
  "postAction": [
    {
      "action": "LeastActionTaskToTableAsset",
      "variables": {
        "parent_laui": "<asset-folder-laui>",
        "table_name": "daily_sales_{{ds}}"
      }
    },
    {
      "action": "LeastActionSMTPEmail",
      "connection": "SMTPProd",
      "variables": {
        "to": "team@company.com",
        "subject": "Task {{name}} completed for {{ds}}",
        "body": "Pipeline finished successfully."
      }
    }
  ]
}
```

### **Conditional Task Control**

Configure task control actions with status filters for UI:

```json
{
  "taskControlActions": [
    {
      "action": "LeastActionCancelTask",
      "variables": {
        "taskStatus": ["running", "scheduled"]
      }
    },
    {
      "action": "LeastActionRunTask",
      "variables": {
        "taskStatus": ["error", "failed", "canceled"]
      }
    },
    {
      "action": "LeastActionScheduleTasks",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
      }
    }
  ]
}
```

**Note:** Task control actions will only appear in the UI when the task's current status matches one of the statuses in the `taskStatus` array.

## **Running Actions with AI**

**Usage** \- How to implement it in a workflows

1. With **Prerequisites** completed at min whats needed is
    1. project
    2. permissions
2. AI \> Action
    1. save connection from AI output with real values \[***coming soon***\]
    2. run
        1. use existing connection.\[subtype\] **← must**
            1. subtype is derived from connection to put in operator subtype
            2. auto save to AI/tempActions/laui
    3. save
        1. when the save user gets to choose a subtype for operator i.e which means that only connection of the same subtype can use this.

## **Creating Actions with AI**

### **File Structure**

When saving actions via AI:

Actions/LeastAction-labs/LeastAction/\[ActionName\]/
\- actionname.py
\- actionname.prompt
\- actionname.bash (if needed)
\- actionname.sample.json (sample variables and connections)

### **Sample AI Prompts**

**Run Task Action:**

Generate a Task Control Action to run or rerun tasks.

API: POST http://localhost:8080/api/v1/task/update/{task_laui}
Body: {"state": "scheduled"}

Action format:
```json
{
  "action": "LeastActionRunTask",
  "variables": {
    "task_status": ["error", "failed"],
    "task_ids": ["list of task_lauis"]
  }
}
```

Reference API: POST http://localhost:8080/api/v1/task/update/{task_laui}

Logic:
- Iterate through task_ids
- For each task, check if current state is in task_status array
- If match, update task to set state to "scheduled"
- Return list of updated task LAUIs

**Cancel Action:**

Generate a Task Control Action to cancel running tasks.

API: POST http://localhost:8080/api/v1/task/update/{task_laui}
Body: {"user_set_state": "cancel"}

Action format:
```json
{
  "action": "LeastActionCancelTask",
  "variables": {
    "task_status": ["running", "scheduled"],
    "task_ids": ["list of task_lauis"]
  }
}
```

Reference API: POST http://localhost:8080/api/v1/task/update/{task_laui}

Logic:
- Only update if current state matches one of the statuses in "task_status" array
- Set user_set_state to "cancel"
- Return list of canceled task LAUIs

**Custom Slack Webhook Action:**

Generate a Lifecycle Action (RunningAction/PostAction) to send Slack notifications.

Connection: SlackWebhook (provides webhook URL)

Action format:
```json
{
  "action": "LeastActionWebhookNotify",
  "sla": 60,
  "connection": "SlackProd",
  "variables": {
    "channel": "#alerts",
    "message": "Task notification",
    "severity": "info"
  }
}
```

Logic:
- Use connection to get webhook URL
- Format message with task context (taskId, taskName, status, runtime)
- Post to Slack webhook
- Return success/failure boolean

## **Available Actions**

### **Task Control Actions**

* **LeastActionRunTask** \- Start task execution. Uses API: sendToExecution, UpdateTask
* **LeastActionCancelTask** \- Stop a running task. Uses API: UpdateTask
* **LeastActionScheduleTasks** \- Schedule or reschedule tasks by updating frequency and dates

### **Task Lifecycle Actions**

**PreActions:**

* **LeastActionCheckIfParentsAreDone** \- Validate parent task completion before execution
* **LeastActionCheckIfLocalFileExists** \- Check if a local file exists before execution
* **AWSS3KeyExists** \- Check if an S3 key exists before execution (requires AWS connection)
* **LeastActionGitToTask** \- Deploy task definitions from Git before execution (requires Git connection)

**RunningActions / RunningIntervalActions:**

* **LeastActionWebhookNotify** \- Send Slack/webhook notifications (requires webhook connection)
* **AWSS3KeyExists** \- Monitor S3 key availability at intervals (requires AWS connection)

**PostActions:**

* **LeastActionWebhookNotify** \- Send completion notifications
* **LeastActionTaskToTableAsset** \- Register task output as a table asset in the catalog
* **LeastActionSMTPEmail** \- Send email notifications (requires SMTP connection)

### **UI Actions**

* **LeastActionGitToTask** \- Deploy task definitions from a Git repo into LeastAction (requires Git connection). Can also be used as a PreAction for automatic CI/CD. See [CI/CD guide](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Cicd).
* **PostgresqlTestConnection** \- Test a PostgreSQL connection (requires Postgres connection)
* **PostgresqlToClaudeChatToHtmlReportToAsset** \- Query PostgreSQL, generate an AI report, and save as an HTML asset
* **DBTImportModel** \- Import dbt models into the catalog
* **LeastActionDeleteItems** \- Delete catalog items
* Custom actions created via AI

### **AWS Actions**

* **AWSS3KeyExists** \- Check if an S3 key exists (requires AWS connection)
* **AWSEC2GitPullAndInstall** \- Pull a Git repository onto an EC2 instance and install dependencies (requires AWS + Git connection)

## **Connection Requirements**

Many actions require connection resources to be configured. Here are common connection types:

| Connection Type | Used By | Purpose |
| ----- | ----- | ----- |
| Git (GitHub/GitLab) | LeastActionGitToTask, AWSEC2GitPullAndInstall | Deploy tasks from Git, Git pull on EC2 |
| Slack / Webhook | LeastActionWebhookNotify | Notifications |
| AWS S3 | AWSS3KeyExists | File monitoring |
| AWS EC2 | AWSEC2GitPullAndInstall | Git pull and install on EC2 |
| PostgreSQL | PostgresqlTestConnection, PostgresqlToClaudeChatToHtmlReportToAsset | DB testing, AI reports |
| SMTP | LeastActionSMTPEmail | Email notifications |

## **Best Practices**

### **Action Configuration**

* Always specify `connection` when an action requires external resources
* Use meaningful variable names that describe their purpose
* Include all required variables with sensible defaults in config
* Use task context variables (e.g., `{{name}}`, `{{session_id}}`, `{{logical_date}}`) for dynamic values

### **Lifecycle Actions**

* **CreateAction**: Keep lightweight, only link/validate metadata
* **PreAction**: Use for validation and setup, always return boolean
* **RunningAction**: Set realistic SLA values to avoid alert fatigue
* **RunningIntervalAction**: Choose intervals appropriate for the resource being monitored
* **PostAction**: Use for cleanup, notifications, and triggering downstream tasks

### **Task Control Actions**

* Filter task control actions by appropriate statuses to avoid invalid operations
* Use caution when invoking programmatically to avoid cascading effects
* Test control actions in non-production first

### **Error Handling**

* All actions should handle failures gracefully
* Use connections with proper error handling and retries
* Log detailed error information for troubleshooting
* Return clear boolean results for PreAction and CreateAction

## **Troubleshooting**

### **Common Issues**

**Action Not Appearing in UI**

* Check if action is properly configured in config's `taskControlActions` or `uiActions`
* Verify `taskStatus` filter matches current task status
* Ensure user has proper permissions

**Action Fails with Connection Error**

* Verify connection is properly configured
* Check connection credentials and permissions
* Ensure connection name matches exactly (case-sensitive)

**PreAction Always Returns False**

* Check parent task IDs are correct
* Verify parent tasks have completed successfully
* Review action logs for specific error messages

**RunningAction Not Triggering**

* Verify SLA value is in minutes
* Check if task runtime exceeds SLA threshold
* Ensure action is properly configured with required variables

**GitToTask Fails**

* Verify Git connection has correct repository URL
* Check branch name is correct
* Ensure authentication credentials are valid
* Verify network access to Git provider

### **Debugging Actions**

* Check action execution logs in task details
* Use the "Play/Run" button in action configuration to test individually
* Verify all required variables are provided
* Test connections separately before using in actions

## **API Reference**

### **Action Execution APIs**

**Execute Action**

```
POST /api/v1/action/run
```
Body:
```json
{
  "action_laui": "<laui of the action>",
  "connection_laui": "<laui of the connection>",
  "action_variables": {
    "git_repo_url": "https://github.com/org/repo.git",
    "git_branch": "main"
  }
}
```

**Update Task State**

```
POST /api/v1/task/update/{task_laui}
```
Body:
```json
{
  "state": "scheduled"
}
```

**Get Action Item**

```
GET /api/v1/catalog/get/{action_laui}
```
Response:
```json
{
  "name": "LeastActionCheckIfParentsAreDone",
  "item_type": "action",
  "codeblock": { "main.py": "..." },
  "action_variables": { "parents": [] }
}
```

**Search Actions in Catalog**

```
GET /api/v1/catalog/search?item_type=action&name={action_name}
```
Response:
```json
{
  "items": [...]
}
```
