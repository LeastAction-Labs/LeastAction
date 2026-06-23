# **LeastAction Config - Feature Guide**

## **Overview**

"Config" provides a way to set defaults and configurations for LeastAction core components, tasks, and workflows. Configs define common static settings that are applied during task execution. While configs can be updated via GitSync or API, they are passed to tasks at scheduling time and remain static during execution.

**Note 1:** All configs except system.yml use JSON format with Jinja templating support.

**Note 2:** System and catalog are backend config. `system.yml` changes take effect immediately on the next task creation — no restart required. Catalog is the core of data management; any changes could break things, please run all test cases before making any changes.

**Note 3:** Configs follow a three-tier hierarchy: System(variables) → Workflow → Task. System(parameters) coming soon.

## **User Config Types**

### **Config**

Config items can be created in config folders, these items define how something like a folder or workflow or task should behave, also can control what actions and buttons show up at a location.

### **Attached Config to Workflow or Task**

Configuration for a specific workflow and all tasks within it.

**Purpose:**
* Set default actions (preAction, createAction, etc.)
* Define parameters
* Configure partitions for dependency management
* Set task defaults (retry, timeout, priority)
* Define Git sync settings
* Configure UI actions

**Format:** JSON (UI-based)

**Scope:** Workflows and its tasks

**Relationship:** 1:n with workflow and config

### **Task Config**

Note: Task-specific configuration that can override workflow config where permitted.

**Purpose:**
* Override specific workflow defaults
* Set task-specific retry and timeout values
* Define task-specific actions
* Customize parameters for individual tasks

**Format:** JSON

**Scope:** Single task

**Override Rules:** Can only override workflow config parameters marked as overridable: true

## **Configuration Hierarchy**

Workflow Config (workflow.config)
    ↓ (overrideable where allowed)
Task Config (task config)

> **Note**: `system.yml` is an infrastructure config (operator-connection mappings, worker settings, scheduler). It is not part of the user-facing parameter config hierarchy. System parameter config is coming soon.
>
> **Connection-operator subtype enforcement**: `system.yml` contains `enforce_connection_operator_mapping: true/false`. When `true`, only connection-operator subtype pairs defined in `connection_operator_mapping` are allowed when creating a task. When `false`, any connection can be used with any operator. Subtypes themselves (e.g., `connection.AWSIAMRole`) are always optional labels.

**How Config merging Works Internally:**

When a task is executed, LeastAction performs a three-step process:

**Step 1: Config Merging** - Configs are merged in order: workflow_configs → task_configs → task.config (configurations attached to task directly)
1. Later configs override earlier ones based on override rules
2. Parameters are handled specially with overridable/not_overridable logic

**Step 2: System Variables Replacement** - Built-in system variables are replaced:
1. {{ds}} - Date Stamp in YYYY-MM-DD format
2. {{ts}} - Time Stamp in ISO format

**Step 3: Merged Parameter Replacement** - User-defined parameters from merged config are replaced in the payload
1. Supports nested objects
2. Undefined variables are preserved as {{parameter_name}} (not replaced)

## **Configuration Duplication**

1. Same level - date most recent
   1. Troubleshooting (warn duplicate)
2. Multi Level based on Hierarchy next will overwrite before if override is not allowed.
   1. Troubleshooting (warn override)

**Hierarchy Rules:**
1. **System Config**: Never overrideable, applies globally
2. **Workflow Config**: Can be overridden by task config only if marked overrideable: true
3. **Task Config**: Can only override explicitly allowed workflow parameters

## **Config Structure**

Configs are JSON files that define controls and defaults, they can be attached to a workflow that all tasks can use or attached to task or directly added to create task form field config. Note action field and config field are different in task create form.

All Task Fields will be treated as parameters. Built-in variables can be used in task payload and action variables.

### **Structure for predefined config i.e config laui**

Defaults - Coming soon

```json
{
  "defaults": {
    "task": {},
    "taskControlActions": [ covered in config_action.md],
    "uiActions": [covered in config_action.md]
  },
  "parameters": {},
  "partition": "",
  "git": {},
  "priority": [],
  "overridable": [],
  "not_overridable": []
}
```

### **Structure for task form config**

Note: task form config is direct input config for a task, a task can use predefined config i.e config_laui

```json
{
  "parameters": {},
  "partition": "",
  "priority": [],
  "actions": {}
}
```

### **Task Defaults**

Define default actions and settings for all tasks in the workflow.

```json
{
  "defaults": {
    "task": {
      "preAction": [...],
      "createAction": [...],
      "runningSLAAction": [...],
      "postAction": [...],
      "retry_count": 3,
      "retry_interval": 300,
      "timeout": 3600
    }
  }
}
```

### **Parameters**

Static parameters available to all tasks in the workflow. Support Jinja templating.

```json
{
  "parameters": {
    "s3_bucket": "s3://data-lake-prod",
    "database_name": "analytics",
    "environment": "production",
    "table_prefix": "dim_"
  }
}
```

**Usage in tasks:**
```json
{
  "sql": "SELECT * FROM {{database_name}}.{{table_prefix}}users"
}
```

**Note**: Parameters are accessed directly by name (e.g., `{{database_name}}`), NOT with a prefix like `{{parameters.database_name}}`.

### **Partition**

Define partition for dependency management. Tasks can only depend on other tasks within the same partition.

```json
{
  "partition": "daily_batch"
}
```

**Use Case:**
* Separate real-time from batch workflows
* Isolate different data domains
* Prevent cross-partition dependencies


### **Priority Configuration**

Set priority levels for tasks in the workflow.

```json
{
  "priority": [
    {
      "level": 0,
      "tasks": ["critical_task_a", "critical_task_b"]
    },
    {
      "level": 1,
      "tasks": ["important_task_x", "important_task_y"]
    },
    {
      "level": 50,
      "tasks": ["*IAM*"]
    },
    {
      "level": 51,
      "tasks": []
    }
  ]
}
```

**Priority Levels:**
* Lower numbers = Higher priority
* Empty array [] applies to all tasks not specified elsewhere
* Supports wildcards (e.g., *IAM* matches all tasks with "IAM" in name)

### **Overridable and Not Overridable**

Control which parameters tasks can override. Both are flat lists of parameter names.

```json
{
  "overridable": ["table_prefix", "retry_count", "timeout"],
  "not_overridable": ["s3_bucket", "environment"]
}
```

**Rules:**
* Parameters in `not_overridable` cannot be changed by task configs or inline config — attempts are silently ignored (warning logged)
* Parameters in `overridable` are explicitly allowed to be overridden by later config layers
* If a parameter is in neither list, it CAN be overridden by later config layers (task_configs, inline config)
* If not specified, both default to empty lists `[]`

### **Complete Workflow Config Example**

```json
{
  "defaults": {
    "task": {
      "preAction": [...],
      "createAction": [...],
      "runningSLAAction": [...],
      "postAction": [...],
      "retry_count": 3,
      "retry_interval": 300,
      "timeout": 3600
    },
    "taskControlActions": [...],
    "uiActions": [...]
  },
  "parameters": {
    "s3_bucket": "s3://data-lake-prod",
    "database_name": "analytics",
    "environment": "production",
    "table_prefix": "dim_"
  },
  "partition": "daily_batch",
  "priority": [...],
  "overridable": ["table_prefix", "retry_count", "timeout"],
  "not_overridable": ["s3_bucket", "environment", "database_name"]
}
```

## **Task Config**

Tasks can override workflow config for parameters marked as overridable.

### **Structure**

```json
{
  "actions": {
    "preAction": [],
    "createAction": [],
    "runningSLAAction": [],
    "runningIntervalAction": [],
    "postAction": []
  },
  "config": {
    "retry_count": 0,
    "retry_interval": 0,
    "timeout": 0,
    "parameters": {}
  }
}
```

### **Override Example**

**Workflow Config:**
```json
{
  "defaults": {
    "task": {
      "retry_count": 3,
      "timeout": 3600
    }
  },
  "parameters": {
    "table_prefix": "dim_"
  },
  "overridable": ["table_prefix", "retry_count", "timeout"]
}
```

**Task Config (Override):**
```json
{
  "retry_count": 5,
  "timeout": 7200,
  "parameters": {
    "table_prefix": "fact_"
  }
}
```

**Result:** Task will use:
* retry_count: 5 (overridden)
* timeout: 7200 (overridden)
* table_prefix: "fact_" (overridden)

### **Adding Actions to Task**

Task-level actions **APPEND** to workflow defaults — they do not replace them. If the workflow default has `preAction: [A, B]` and the task specifies `preAction: [C]`, the resulting task runs `preAction: [A, B, C]`. If a task specifies the same action already in defaults, its `variables` are auto-filled from the default and the user can update or use config parameters to override them.

**Workflow Config:**
```json
{
  "defaults": {
    "task": {
      "preAction": [
        {
          "action": "LeastActionGitSync",
          "connection": "github-main",
          "variables": {}
        }
      ]
    }
  }
}
```

**Task Config (Additional Actions):**
```json
{
  "preAction": [
    {
      "action": "LeastActionGitSync",
      "connection": "github-main",
      "variables": {}
    },
    {
      "action": "LeastActionCheckS3FileExists",
      "connection": "s3-prod",
      "variables": {
        "s3_path": "s3://bucket/data.csv"
      }
    }
  ],
  "runningSLAAction": [
    {
      "action": "LeastActionSlackWebhook",
      "sla": 30,
      "connection": "slack-alerts",
      "variables": {
        "message": "Critical task taking too long"
      }
    }
  ]
}
```

## **Variables Available for Replacement**

Variable replacement is applied to **both the task payload and action variables** at execution time. The same variable context is available in `payload`, `preAction.variables`, `postAction.variables`, and all other action variable fields.

### **Resolution Order (highest priority wins)**

1. **Built-in variables** (`ds`, `ts`) — always win, cannot be overridden by config
2. **Config parameters** (`parameters` block from merged config) — override task schema fields
3. **Task schema fields** (all fields from `task.json`, except `description`, `actions`, `payload`, `config`) — lowest priority
4. **Undefined** — preserved as `{{variable_name}}`, not an error

---

### **1. Built-in System Variables**

Two built-in variables are always available. They reflect the **current wall-clock time at execution**, not the task's logical date:

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| `{{ds}}` | Execution date (YYYY-MM-DD) | `2026-03-06` |
| `{{ds_nodash}}` | Execution date without dashes (YYYYMMDD) | `20260306` |
| `{{ts}}` | Execution timestamp (ISO format) | `2026-03-06T14:30:00.123456` |
| `{{ts_nodash}}` | Execution timestamp without dashes (YYYYMMDDTHHmmSS) | `20260306T143000` |
| `{{ts_nodash_with_tz}}` | Execution timestamp without dashes with timezone offset | `20260306T143000+0000` |
| `{{current_date}}` | Current wall-clock date (YYYY-MM-DD) | `2026-03-06` |
| `{{current_timestamp}}` | Current wall-clock timestamp (ISO format) | `2026-03-06T14:30:00.123456` |

> **Note**: `{{ds}}` is the actual execution date, not the task's `logical_date`. Use `{{logical_date}}` when you need the scheduled slot date.

**Usage Example:**
```sql
SELECT * FROM sales.fact_daily_revenue WHERE date = '{{ds}}'
```

---

### **2. Config Parameters**

Any parameters defined in your config can be accessed by name:

**Config Definition:**
```json
{
  "parameters": {
    "user": "postgres",
    "host": "postgres-demo",
    "port": "5432",
    "database": "postgres_demo_db"
  }
}
```

**Usage in Payload:**
```json
{
  "server": "{{host}}:{{port}}",
  "database": "{{database}}"
}
```

**Usage in Action Variables:**
```json
{
  "action": "LeastActionSlackWebhook",
  "variables": {
    "message": "Task {{name}} completed on {{ds}} in {{database}}"
  }
}
```

**Note**: Parameters are accessed directly by name (e.g., `{{database}}`), NOT with a prefix like `{{parameters.database}}`.

---

### **3. Task Schema Fields**

All fields from `task.json` are injected automatically — **except** `description`, `actions`, `payload`, and `config` (these are excluded). Config parameters and built-in variables take priority over task schema fields if the same name is defined in both.

#### **Scheduling & Timing** (most commonly used)

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| `{{logical_date}}` | Scheduled slot datetime for this run | `2026-03-06T00:00:00` |
| `{{data_interval_start}}` | Current interval start (set at execution start) | `2026-03-06T00:00:00` |
| `{{data_interval_end}}` | Current interval end = logical_date + frequency (set at execution start) | `2026-03-07T00:00:00` |
| `{{prev_interval_start}}` | Previous run's interval start (set after previous run completes) | `2026-03-05T00:00:00` |
| `{{prev_interval_end}}` | Previous run's interval end (set after previous run completes) | `2026-03-06T00:00:00` |
| `{{last_run_date}}` | When the previous run ended | `2026-03-05T06:42:00` |
| `{{task_instance_start_date}}` | Actual start time of the current run | `2026-03-06T06:00:05` |
| `{{task_instance_end_date}}` | Actual end time of the current run (available in postAction) | `2026-03-06T06:07:22` |
| `{{start_date}}` | Task configured start date | `2026-01-01T00:00:00` |
| `{{end_date}}` | Task configured end date | `2026-12-31T23:59:59` |
| `{{frequency}}` | Cron expression or "ADHOC" | `0 6 * * *` |

#### **Execution State**

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| `{{state}}` | Current task state | `running` |
| `{{iteration}}` | Total number of times this task has run (lifetime counter) | `42` |
| `{{retry_number}}` | Current retry attempt (0 = first attempt, 1 = first retry) | `0` |
| `{{retry_interval}}` | Seconds between retries | `300` |
| `{{total_retries}}` | Max retries configured | `3` |
| `{{task_reschedule_count}}` | How many times the task has been rescheduled | `0` |
| `{{duration}}` | Duration of the last run in seconds | `427` |
| `{{priority}}` | Task priority level | `1` |

#### **Identity**

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| `{{name}}` | Task name | `daily_sales_load` |
| `{{partition}}` | Task partition | `ALL` |
| `{{project_laui}}` | Project identifier | `6997d6f277dcb18b47e47968` |
| `{{account_laui}}` | Account identifier | `6997d6f177dcb18b47e47966` |
| `{{operator_laui}}` | Operator identifier | `6aa7d6f277dcb18b47e47970` |
| `{{connection_laui}}` | Connection identifier | `6bb7d6f277dcb18b47e47971` |
| `{{payload_laui}}` | Payload item identifier (if payload stored as catalog item) | `6cc7d6f277dcb18b47e47972` |

#### **Session & Worker**

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| `{{executor}}` | Celery worker that ran this task | `task_worker@hostname` |
| `{{task_instance}}` | Instance name where the task ran | `instance-001` |
| `{{session_id}}` | Current session identifier | `a3f9b2c1d4e5f678` |
| `{{last_run_session_id}}` | Session ID of the previous run | `b4f8a3d2e1c5g789` |
| `{{project_instance}}` | EC2 IP used for routing (if set) | `10.0.1.42` |

#### **Not Available as Variables**

The following task fields are **excluded** from the variable context and cannot be used in templates:
- `description` — excluded
- `actions` — excluded (would create circular reference)
- `payload` — excluded (you are inside it)
- `config` — excluded (already merged into parameters)

**Usage Example — payload using task fields:**
```sql
INSERT INTO audit.task_runs (task_name, logical_dt, run_no, duration_s)
VALUES ('{{name}}', '{{logical_date}}', {{iteration}}, {{duration}})
```

**Usage Example — action variable using task fields:**
```json
{
  "action": "LeastActionSlackWebhook",
  "variables": {
    "message": "Task {{name}} (retry {{retry_number}}) completed. Logical date: {{logical_date}}. Duration: {{duration}}s"
  }
}
```

**Note:** Variables are resolved after config merging, immediately before execution. Undefined variables are preserved as `{{variable_name}}` — not an error.

## **Jinja Templating**

All JSON configs support Jinja templating for dynamic values.

### **Available Variables Summary**

```
# ── Built-in System Variables (highest priority) ──────────────────────────────
{{ds}}                          # Execution date (YYYY-MM-DD)
{{ds_nodash}}                   # Execution date without dashes (YYYYMMDD)
{{ts}}                          # Execution timestamp (ISO format)
{{ts_nodash}}                   # Execution timestamp without dashes (YYYYMMDDTHHmmSS)
{{ts_nodash_with_tz}}           # Execution timestamp without dashes with timezone offset
{{current_date}}                # Current wall-clock date (YYYY-MM-DD)
{{current_timestamp}}           # Current wall-clock timestamp (ISO format)

# ── Config Parameters (user-defined, override task fields) ────────────────────
{{any_parameter_you_define}}    # Direct access by name — e.g. {{database}}

# ── Task Schema Fields (lowest priority) ──────────────────────────────────────

# Scheduling & timing
{{logical_date}}                # Scheduled slot datetime for this run
{{data_interval_start}}         # Current interval start
{{data_interval_end}}           # Current interval end (logical_date + frequency)
{{prev_interval_start}}         # Previous interval start
{{prev_interval_end}}           # Previous interval end
{{last_run_date}}               # When the previous run ended
{{task_instance_start_date}}    # Actual start time of current run
{{task_instance_end_date}}      # Actual end time of current run
{{start_date}}                  # Task configured start date
{{end_date}}                    # Task configured end date
{{frequency}}                   # Cron expression or "ADHOC"

# Execution state
{{state}}                       # Task state enum (running, success, error, ...)
{{iteration}}                   # Total run count (lifetime)
{{retry_number}}                # Current retry attempt (0 = first)
{{retry_interval}}              # Seconds between retries
{{total_retries}}               # Max retries configured
{{duration}}                    # Last run duration in seconds
{{priority}}                    # Priority level

# Identity
{{name}}                        # Task name
{{partition}}                   # Task partition
{{project_laui}}                # Project identifier
{{account_laui}}                # Account identifier
{{operator_laui}}               # Operator identifier
{{connection_laui}}             # Connection identifier
{{payload_laui}}                # Payload item identifier

# Session & worker
{{executor}}                    # Celery worker name
{{task_instance}}               # Instance name
{{session_id}}                # Current session ID
{{last_run_session_id}}       # Previous session ID

# NOT available: description, actions, payload, config

# ── Notes ─────────────────────────────────────────────────────────────────────
# ds/ds_nodash/ts/ts_nodash/ts_nodash_with_tz — based on execution datetime
# current_date/current_timestamp — based on actual wall-clock time at execution
```

### **Comprehensive Usage Examples**

#### **Example 1: Date-Partitioned Data Processing**
```json
{
  "parameters": {
    "s3_input_path": "s3://data-lake/raw/{{ds}}/",
    "s3_output_path": "s3://data-lake/processed/{{ds}}/",
    "table_name": "events_{{ds | replace('-', '')}}",
    "partition_date": "{{ds}}"
  }
}
```

#### **Example 2: SQL Query with Multiple Variables**
```sql
-- Incremental data processing
SELECT 
    event_id,
    event_date,
    '{{name}}' as processed_by_task,
    {{iteration}} as task_iteration
FROM raw_events
WHERE event_date >= '{{data_interval_start}}'
  AND event_date < '{{data_interval_end}}'
  AND partition = '{{partition}}'
```

#### **Example 3: Database Connection with Config Parameters**
```json
{
  "connection_string": "postgresql://{{username}}:{{password}}@{{host}}:{{port}}/{{database}}",
  "query_timeout": {{query_timeout}},
  "execution_date": "{{ds}}"
}
```

#### **Example 4: Action Variables with Task Context**
```json
{
  "action": "LeastActionSlackWebhook",
  "variables": {
    "message": "Task '{{name}}' completed at {{ts}}",
    "details": "Iteration: {{iteration}}, Logical Date: {{logical_date}}",
    "status": "{{state}}"
  }
}
```

#### **Example 5: Incremental Processing Pattern**
```json
{
  "payload": {
    "source": {
      "path": "s3://bucket/data/",
      "start_date": "{{prev_interval_end}}",
      "end_date": "{{data_interval_end}}"
    },
    "destination": {
      "table": "incremental_{{partition}}",
      "partition_key": "{{ds}}"
    },
    "metadata": {
      "task_name": "{{name}}",
      "execution_number": {{iteration}},
      "retry_attempt": {{try_number}}
    }
  }
}
```

#### **Example 6: Conditional Processing Based on Task State**
```python
# In Python operator payload
config = {
    "task_name": "{{name}}",
    "logical_date": "{{logical_date}}",
    "state": "{{state}}",
    "data_range": {
        "start": "{{data_interval_start}}",
        "end": "{{data_interval_end}}"
    },
    "previous_range": {
        "start": "{{prev_interval_start}}",
        "end": "{{prev_interval_end}}"
    }
}
```

### **Undefined Variables**

If a variable is not defined in parameters, task fields, or built-in variables, it will be preserved in its original form:

**Before:**
```json
{
  "defined_param": "{{username}}",
  "undefined_param": "{{api_token}}",
  "system_var": "{{ds}}"
}
```

**After (with username="admin"):**
```json
{
  "defined_param": "admin",
  "undefined_param": "{{api_token}}",
  "system_var": "2026-01-08"
}
```

This allows you to safely use placeholders that may be replaced by downstream systems.

### **Variable Resolution Order**

Variables are resolved in the following priority order:
1. **Built-in System Variables** (ds, ts) - Highest priority
2. **Config Parameters** (user-defined in config.parameters)
3. **Task Schema Fields** (task properties)
4. **Undefined** - Preserved as-is if not found

## **Config Loading Order**

1. **System Config** - Loaded first, applies globally
2. **Workflow Config** - Loaded at workflow level
3. **Task Config** - Loaded at task level, overrides where allowed
4. **Jinja Resolution** - Template variables resolved before task execution

## **Best Practices**

### **Workflow Config**

1. **Descriptive Parameters**: Use clear parameter names
   * ✅ s3_bucket, database_name, table_prefix
   * ❌ bucket, db, prefix

2. **Sensible Defaults**: Set reasonable default values
   * retry_count: 3 (not 0 or 100)
   * timeout: 3600 (1 hour for most tasks)

3. **Parameter Organization**: Group related parameters
```json
{
  "parameters": {
    "s3_bucket": "...",
    "s3_prefix": "...",
    "s3_region": "..."
  }
}
```

4. **Override Control**: Be explicit about what can be overridden
   * Critical parameters (environment, production buckets): not_overridable
   * Task-specific values (table names, timeouts): overridable

5. **Action Configuration**: Configure actions at workflow level when possible
   * Common actions (GitSync, CheckParents): workflow level
   * Task-specific actions (custom sensors): task level

### **Task Config**

1. **Minimal Overrides**: Only override what's necessary
2. **Document Overrides**: Comment why overrides are needed
3. **Consistent Naming**: Use same parameter names as workflow config

### **Jinja Templating**

1. **Test Templates**: Validate Jinja templates before deployment
2. **Readable Templates**: Keep templates simple and readable
   * ✅ `{{ds}}`
   * ✅ `{{table_name}}`

## **Common Patterns**

### **Pattern 1: Environment-Specific Configs**

```json
{
  "parameters": {
    "environment": "production",
    "s3_bucket": "s3://data-lake-prod",
    "database": "analytics_prod"
  },
  "not_overridable": ["environment", "s3_bucket", "database"]
}
```

### **Pattern 2: Date-Partitioned Workflows**

```json
{
  "parameters": {
    "s3_path": "s3://bucket/data/{{ds}}/",
    "table_suffix": "_{{ds}}"
  }
}
```

**Granular date/time partitioning using string slicing on `ds` and `ts`:**

`ds` is `YYYY-MM-DD` and `ts` is an ISO timestamp (`YYYY-MM-DDTHH:MM:SS...`), so you can slice them to extract date/time parts:

```
source/yyyy={{ds[:4]}}/mm={{ds[5:7]}}/dd={{ds[8:10]}}/hh={{ts[11:13]}}/mm={{ts[14:16]}}/source_file.txt
source/date={{ds}} {{ts[11:16]}}/source_file.txt
```

> **Note:** `{{data_interval_start.year}}` style attribute access is **not supported** — use string slicing on `ds`/`ts` instead. Both `ds` and `ts` are derived from `logical_date`, not `data_interval_start`.

### **Pattern 3: Multi-Stage ETL**

```json
{
  "priority": [
    {
      "level": 0,
      "tasks": ["extract_*"]
    },
    {
      "level": 1,
      "tasks": ["transform_*"]
    },
    {
      "level": 2,
      "tasks": ["load_*"]
    }
  ]
}
```

### **Pattern 4: Critical Tasks with Enhanced Monitoring**

```json
{
  "defaults": {
    "task": {
      "runningSLAAction": [
        {
          "action": "LeastActionSlackWebhook",
          "sla": 30,
          "connection": "slack-critical",
          "variables": {
            "channel": "#critical-alerts",
            "severity": "high"
          }
        }
      ],
      "retry_count": 5,
      "retry_interval": 60
    }
  }
}
```

### **Pattern 5: Development vs Production**

**Production Workflow Config:**
```json
{
  "parameters": {
    "environment": "production",
    "s3_bucket": "s3://data-lake-prod",
    "database": "analytics_prod"
  },
  "defaults": {
    "task": {
      "retry_count": 3,
      "timeout": 3600,
      "runningSLAAction": [
        {
          "action": "LeastActionSlackWebhook",
          "sla": 60,
          "connection": "slack-alerts"
        }
      ]
    }
  }
}
```

**Development Workflow Config:**
```json
{
  "parameters": {
    "environment": "development",
    "s3_bucket": "s3://data-lake-dev",
    "database": "analytics_dev"
  },
  "defaults": {
    "task": {
      "retry_count": 1,
      "timeout": 1800,
      "runningSLAAction": []
    }
  }
}
```

## **Troubleshooting**

### **Config Not Loading**

**Symptoms**: Tasks not using expected config values

**Solutions**:
1. Verify config file exists at expected path
2. Check JSON is valid (use JSON validator)
3. Verify workflow-to-config relationship
4. Check task isn't specifying different config
5. Review LeastAction logs for config loading errors

### **Override Not Working**

**Symptoms**: Task config overrides being ignored

**Solutions**:
1. Check parameter is in workflow config's `overridable` list
2. Verify parameter name matches exactly (case-sensitive)
3. Ensure parameter not in `not_overridable` section
4. Check task config JSON is valid
5. Verify override rules in hierarchy

### **Jinja Template Errors**

**Symptoms**: Template variables not resolving or errors during execution

**Solutions**:
1. Test Jinja syntax in isolation
2. Verify variable exists in available context (ds, ts, or parameters)
3. Check for typos in variable names
4. Review LeastAction logs for template rendering errors

### **Parameter Not Found**

**Symptoms**: Tasks fail with "parameter not found" errors

**Solutions**:
1. Verify parameter defined in workflow config
2. Check spelling and case sensitivity
3. Check if parameter is being overridden incorrectly
4. Verify Jinja template syntax: `{{key}}`

### **Action Not Executing**

**Symptoms**: Configured actions not running

**Solutions**:
1. Verify action exists and is accessible
2. Check connection is valid and enabled
3. Ensure action variables are properly formatted
4. Review action execution logs
5. Verify action type matches lifecycle hook (preAction, postAction, etc.)

## **Config Conflicts**

1. **Missing**
   1. Missing cause of override
2. **Duplicates**
3. **Override**

## **Future Enhancements**

### **Config Versioning**
* Track config changes over time
* Rollback to previous versions
* View config history and diffs
* Tag config versions

### **Config Templates**
* Pre-built config templates for common patterns
* Import/export configs
* Config marketplace for sharing
* Template validation and linting

### **Dynamic Config Updates**
* Hot-reload configs without restart
* A/B testing different configs
* Gradual config rollouts
* Config feature flags

### **Enhanced Validation**
* Schema validation for all configs
* Dependency checking between parameters
* Jinja template validation
* Config impact analysis

### **Config Inheritance**
* Parent-child config relationships
* Config mixins and composition
* Override visualization
* Conflict resolution rules

### **Additional Jinja Macros (Planned)**

The following Jinja macros are planned for future implementation to provide more advanced date and string manipulation:

* `macros.ds_add(date, days)` - Add/subtract days from a date
  ```
  {{ macros.ds_add(ds, 7) }}  # Add 7 days to current date
  {{ macros.ds_add(ds, -1) }}  # Subtract 1 day (yesterday)
  ```

* `macros.ds_format(date, format)` - Format date strings with custom patterns
  ```
  {{ macros.ds_format(ds, '%Y%m%d') }}  # Convert to YYYYMMDD
  {{ macros.ds_format(logical_date, '%B %d, %Y') }}  # Full date format
  ```

* `macros.datetime.now(timezone)` - Get current datetime with timezone
  ```
  {{ macros.datetime.now('UTC') }}
  {{ macros.datetime.now('America/New_York') }}
  ```

* `macros.date_diff(date1, date2, unit)` - Calculate difference between dates
  ```
  {{ macros.date_diff(data_interval_end, data_interval_start, 'hours') }}
  {{ macros.date_diff(ds, prev_interval_start, 'days') }}
  ```

* `macros.json_encode(object)` - Safely encode objects as JSON strings
  ```
  {{ macros.json_encode(config_dict) }}
  ```

**Note:** While these macros are planned, you can currently use standard Jinja2 filters like `replace`, `upper`, `lower`, `default`, etc. on any variables.
