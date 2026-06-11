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

* **LeastActionRun** \- Start task execution
* **LeastActionRerun** \- Re-execute a task
* **LeastActionRerunSubtree** \- Re-execute task and all children
* **LeastActionCancel** \- Stop a running task
* **LeastActionSkip** \- Mark task as skipped
* **LeastActionSkipSubtree** \- Skip task and all children
* **LeastActionSkipPostDoneS3** \- Skip and write completion marker

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

* **LeastActionLinkParents** (CreateAction) \- Connect parent dependencies
* **LeastActionAutoLinkParents** (CreateAction) \- Parse SQL to auto-detect dependencies
* **LeastActionCheckIfParentsAreDone** (PreAction) \- Validate parent completion
* **LeastActionGitSync** (PreAction) \- Sync code from Git
* **LeastActionSlackWebhook** (RunningAction/RunningIntervalAction/PostAction) \- Send notifications
* **LeastActionFindTasksReadyToRun** \- Identify tasks ready for execution (can be invoked by cron or as PostAction)

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
          "action": "LeastActionGitSync",
          "connection": "GitHubMain",
          "variables": {
            "repository": "org/repo",
            "branch": "main"
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
      "createAction": [
        {
          "action": "LeastActionLinkParents",
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
          "action": "LeastActionSlackWebhook",
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
          "action": "LeastActionAWSEC2UpdateUtilization",
          "interval": 10,
          "connection": "AWSProd",
          "variables": {
            "instanceId": "{{instanceId}}",
            "metricName": "CPUUtilization"
          }
        }
      ],
      "postAction": [
        {
          "action": "LeastActionAWSS3PostDoneFile",
          "connection": "S3IAMLaui",
          "variables": {
            "s3Prefix": "s3://bucket/folder/{{yyyymmdd}}",
            "fileName": "{{taskId}}.done"
          }
        },
        {
          "action": "LeastActionFindTasksReadyToRun",
          "variables": {}
        }
      ]
    },
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
    ],
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
}
```

**Via Task Creation Form Field "actions"**

```json
{
  "preAction": [
    {
      "action": "LeastActionGitSync",
      "connection": "GitHubMain",
      "variables": {
        "repository": "org/repo",
        "branch": "main"
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
  "createAction": [
    {
      "action": "LeastActionLinkParents",
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
      "action": "LeastActionSlackWebhook",
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
      "action": "LeastActionAWSEC2UpdateUtilization",
      "interval": 5,
      "connection": "AWSProd",
      "variables": {
        "instanceId": "i-1234567890"
      }
    }
  ],
  "postAction": [
    {
      "action": "LeastActionPostDoneS3",
      "connection": "S3IAMLaui",
      "variables": {
        "s3Prefix": "s3://bucket/folder/",
        "fileName": "task.done"
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

**CreateAction \+ PreAction \+ PostAction Pattern:**

1. **LeastActionLinkParents** (CreateAction) \- Connects parent tasks to child tasks
    * LeastActionLinkParents takes data from LeastActionCheckIfParentsAreDone to avoid duplicate entries
2. **LeastActionCheckIfParentsAreDone** (PreAction) \- Validates parent completion before execution
3. **LeastActionFindTasksReadyToRun** (PostAction) \- Identifies which tasks can execute

**Note:** LeastActionFindTasksReadyToRun is also invoked by cron at regular intervals. For immediate invocation after a parent is done, using LeastActionFindTasksReadyToRun in post action can speed things up, but is optional.

**Example flow of using above actions:**

1. Create workflow (config auto-created/attached)
2. Create task
3. Default actions are attached from config(sample below):
4. On create/update:
    * Lists current parents
    * Compares with specified parents
    * Deletes missing dependencies
    * Adds new dependencies
5. Before execution, LeastActionCheckIfParentsAreDone validates all parents have completed
6. After execution, LeastActionFindTasksReadyToRun is run to trigger child tasks

**Sample**

```json
{
  "createAction": [{"action": "LeastActionLinkParents"}],
  "preAction": [{"action": "LeastActionCheckIfParentsAreDone", "variables": {"parents": [{"task_name": "parent_task", "project_laui": "{{project_laui}}", "account_laui": "{{account_laui}}", "partition": "{{partition}}"}]}}]
}
```

### **Auto-Linking for SQL Tasks**

Automatically parse SQL and link parent dependencies:

**Configuration:**

```json
{
  "createAction": [
    {
      "action": "LeastActionAutoLinkParents",
      "variables": {
        "sqlQuery": "{{payload.sql}}"
      }
    },
    {
      "action": "LeastActionLinkParents",
      "variables": {
        "parents": []
      }
    }
  ],
  "preAction": [
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {
        "mode": "auto"
      }
    }
  ]
}
```

* **LeastActionAutoLinkParents** analyzes SQL to identify table dependencies
* **LeastActionCheckIfParentsAreDone** with mode "auto" validates auto-detected dependencies
* Falls back to manual LeastActionLinkParents if needed

### **CI/CD Integration**

LeastAction supports two complementary CI/CD patterns:

**Pattern 1: Task Catalog Sync (LeastActionGitToTask)**

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

See the [CI/CD guide](/path?laui=getting-started-advanced-task_managment-cicd&itemtype=doc.file&itemname=Cicd) for the full setup, task file format, and examples.

**Pattern 2: Code Sync (LeastActionGitSync)**

Sync operator or payload code files from Git to the worker before each task execution. Useful when your task's operator code lives in Git and needs to be pulled fresh at runtime:

```json
{
  "preAction": [
    {
      "action": "LeastActionGitSync",
      "connection": "GitHubMain",
      "variables": {
        "repository": "org/repo",
        "branch": "main",
        "syncPath": "/payload"
      }
    },
    {
      "action": "LeastActionCheckIfParentsAreDone",
      "variables": {
        "parents": []
      }
    }
  ]
}
```

* Tasks contain schedule details
* Payload, compute, config, and operators are CI/CD-enabled
* Code syncs before each execution

### **SLA Monitoring with Notifications**

Monitor task execution time and send alerts:

```json
{
  "RunningAction": [
    {
      "action": "LeastActionSlackWebhook",
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

### **Resource Utilization Tracking**

Monitor resource usage during task execution:

```json
{
  "runningIntervalAction": [
    {
      "action": "LeastActionAWSEC2UpdateUtilization",
      "interval": 5,
      "connection": "AWSProd",
      "variables": {
        "instanceId": "{{compute.instanceId}}",
        "metrics": ["CPUUtilization", "MemoryUtilization"],
        "namespace": "LeastAction/Tasks"
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
      "action": "LeastActionCancel",
      "variables": {
        "taskStatus": ["running", "scheduled"]
      }
    },
    {
      "action": "LeastActionRerun",
      "variables": {
        "taskStatus": ["error", "failed", "canceled"]
      }
    },
    {
      "action": "LeastActionRerunSubtree",
      "variables": {
        "taskStatus": ["error", "failed"]
      }
    },
    {
      "action": "LeastActionSkip",
      "variables": {
        "taskStatus": ["scheduled", "waiting"]
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

**Rerun Action:**

Generate a Task Control Action to rerun tasks.

API: PUT http://localhost:8000/tasks/update/{task_id}  
Body: {"last_run_status": "scheduled"}

Action format:
```json
{
  "action": "LeastActionRerun",
  "variables": {
    "task_status": ["error", "failed"],
    "task_ids": ["list of task_ids"]
  }
}
```

Reference API: GET http://localhost:8000/tasks/by-id/{task_id}

Logic:
- Iterate through task_ids
- For each task, check if last_run_status is in task_status array
- If match, update task to set last_run_status to "scheduled"
- Return list of updated task IDs

**Cancel Action:**

Generate a Task Control Action to cancel running tasks.

API: PUT http://localhost:8000/tasks/update/{task_id}  
Body: {"status_user_action": "cancel"}

Action format:
```json
{
  "action": "LeastActionCancel",
  "variables": {
    "task_status": ["running", "scheduled"],
    "task_ids": ["list of task_ids"]
  }
}
```

Reference API: GET http://localhost:8000/tasks/by-id/{task_id}

Logic:
- Only update if "last_run_status" matches one of the statuses in "task_status" array
- Set status_user_action to "cancel"
- Return list of canceled task IDs

**Custom Slack Webhook Action:**

Generate a Lifecycle Action (RunningAction/PostAction) to send Slack notifications.

Connection: SlackWebhook (provides webhook URL)

Action format:
```json
{
  "action": "LeastActionSlackWebhook",
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

## **Available Actions (MVP)**

### **Task Control Actions**

* **LeastActionRun** \- Uses API: sendToExecution, UpdateTask
* **LeastActionRerun** \- Uses API: sendToExecution, UpdateTask
* **LeastActionRerunSubtree** \- Uses API: RecursiveListChildren, UpdateTask
* **LeastActionCancel** \- Uses API: UpdateTask
* **LeastActionSkip** \- Uses API: UpdateTask
* **LeastActionSkipSubtree** \- Uses API: RecursiveListChildren, UpdateTask
* **LeastActionSkipPostDoneS3** \- Uses API: UpdateTask \+ S3 write (requires S3 connection)
* **LeastActionRunWithoutSensorsCompletion** \- Adds done file
* **LeastActionRunWithoutParentsCompletion** \- Adds done file

### **Task Lifecycle Actions**

**CreateActions:**

* **LeastActionLinkParents** \- Uses API: LinkItem
* **LeastActionAutoLinkParents** \- Uses API: AnalyzeSQL, LinkItem

**PreActions:**

* **LeastActionCheckIfParentsAreDone** \- Uses API: ListParents
* **LeastActionGitSync** \- Sync repository (requires Git connection)
* **LeastActionGitSyncPayload** \- Sync task payload (requires Git connection)
* **LeastActionFindTasksReadyToRun** \- Uses API: FindTasksReadyToRun

**RunningActions / RunningIntervalActions:**

* **LeastActionCheckForS3** \- Monitor S3 file availability (requires S3 connection)
* **LeastActionCheckForSQS** \- Monitor SQS queue (requires SQS connection)
* **LeastActionCheckForLAUI** \- Monitor LeastAction UI status
* **LeastActionSlackWebhook** \- Send Slack notifications (requires Slack connection)
* **LeastActionAWSEC2UpdateUtilization** \- Track EC2 utilization (requires AWS connection)

**PostActions:**

* **LeastActionPostDoneS3** \- Write completion marker to S3 (requires S3 connection)
* **LeastActionPostDoneSNS** \- Send SNS notification (requires SNS connection)
* **LeastActionPostWebhook** \- Send HTTP webhook (requires Webhook connection)
* **LeastActionFindTasksReadyToRun** \- Trigger downstream tasks

**Operator Actions:**

* **LeastActionSetSessionAuthUser** \- Set authentication context
* **LeastActionPipInstall** \- Install Python packages
* **LeastActionCloudFormation** \- Deploy CloudFormation stacks (requires AWS connection)

### **UI Actions**

* **LeastActionGitToTask** \- Deploy task definitions from a Git repo into LeastAction (requires Git connection). Can also be used as a PreAction for automatic CI/CD. See [CI/CD guide](/path?laui=getting-started-advanced-task_managment-cicd&itemtype=doc.file&itemname=Cicd).
* **LeastActionImportPostgres** \- Import Postgres schemas (requires Postgres connection)
* **LeastActionImportPostgresTables** \- Import specific Postgres tables (requires Postgres connection)
* Custom actions created via AI

## **Connection Requirements**

Many actions require connection resources to be configured. Here are common connection types:

| Connection Type | Used By | Purpose |
| ----- | ----- | ----- |
| Git (GitHub/GitLab) | LeastActionGitSync, LeastActionGitSyncPayload | Repository sync |
| Slack | LeastActionSlackWebhook | Notifications |
| AWS S3 | LeastActionPostDoneS3, LeastActionCheckForS3, LeastActionSkipPostDoneS3 | File operations |
| AWS SNS | LeastActionPostDoneSNS | Notifications |
| AWS EC2 | LeastActionAWSEC2UpdateUtilization | Monitoring |
| SQS | LeastActionCheckForSQS | Queue monitoring |
| Postgres | LeastActionImportPostgres | Database import |
| Generic Webhook | LeastActionPostWebhook | HTTP notifications |

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
* Test subtree operations (RerunSubtree, SkipSubtree) in non-production first

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

**GitSync Fails**

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

**Execute UI Action**

```
POST /actions/ui/execute
```
Body:
```json
{
  "action": "LeastActionImport",
  "connection": "Cloud",
  "variables": {
    "projectId": "12345"
  }
}
```

**Execute Task Control Action**

```
POST /actions/control/execute
```
Body:
```json
{
  "action": "LeastActionRerun",
  "variables": {
    "task_ids": [1, 2, 3],
    "task_status": ["error"]
  }
}
```

**Get Action Definition**

```
GET /actions/{action_name}
```
Response:
```json
{
  "name": "LeastActionGitSync",
  "type": "PreAction",
  "requiredVariables": ["repository", "branch"],
  "optionalVariables": ["syncPath"],
  "requiresConnection": true,
  "connectionTypes": ["git"]
}
```

**List Available Actions**

```
GET /actions?type={UI|Control|Lifecycle}
```
Response:
```json
{
  "actions": [...]
}
```

