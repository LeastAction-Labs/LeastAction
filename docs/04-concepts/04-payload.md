# **LeastAction Payload - Feature Guide**

## **Overview**

A **payload** is the "what" of a task — the operator-specific data, query, script, or configuration that the operator executes. While the operator defines *how* to run something and the connection defines *where* to run it, the payload defines *what* to run.

Payloads are entirely operator-defined: a SQL operator expects a SQL query, a Lambda operator expects a JSON invocation payload, a Python operator expects a script, and so on. LeastAction does not interpret the payload — it passes it directly to the operator.

---

## **How Payloads Are Added to a Task**

There are two ways to attach a payload to a task:

### **1. Via laui (Catalog Item)**

A payload can be stored as a reusable catalog item with its own laui (LeastAction unique identifier). You reference it by laui when creating a task.

Use this when:
- The same payload is shared across multiple tasks
- You want to manage payloads independently of tasks (update once, applies everywhere)
- You manage payload versions in the catalog

### **2. Inline / Direct**

The payload content is embedded directly in the task definition. Use this when:
- The payload is unique to a single task
- You are creating tasks from Git files using `LeastActionGitToTask` — the payload body is the file content below the metadata comment block
- You want the payload and task definition to live together in version control

---

## **Payload Formats by Operator Type**

The format of a payload is determined entirely by the operator. Common examples:

| Operator type | Expected payload format |
|--------------|------------------------|
| SQL (Athena, BigQuery, Snowflake, Redshift) | SQL query string |
| AWS Lambda | JSON object — function invocation event |
| Python script | Python source code |
| API / HTTP | JSON body or YAML config |
| Spark / Databricks | Spark SQL or job config |
| Shell / Bash | Shell script |
| S3 / file move | YAML or JSON config with source/destination |

Check the operator's documentation or the catalog entry for its expected payload format.

---

## **Jinja Templating in Payloads**

Payloads support Jinja-style variable replacement: `{{variable_name}}`. Variables are resolved at execution time, so your payload can reference dynamic values like the execution date, task metadata, or config parameters.

**Built-in variables:**

| Variable | Value |
|----------|-------|
| `{{ds}}` | Logical date as `YYYY-MM-DD` (derived from `logical_date`, not wall-clock) |
| `{{ts}}` | Logical date as ISO timestamp (derived from `logical_date`) |

**Config parameters** — any `parameters` key defined in an attached config:

```sql
SELECT * FROM sales WHERE date = '{{ds}}' AND region = '{{region}}'
```

**Task schema fields** — most task fields are available, including `{{task_name}}`, `{{frequency}}`, `{{session_id}}`, `{{retry_number}}`, `{{logical_date}}`, and others.

See the [Config guide](/path?laui=getting-started-04-concepts-05-config&itemtype=doc.file&itemname=Config) for the full variable reference and resolution order.

---

## **The Git-First Approach**

The recommended pattern is to store all payloads in a Git repository and use LeastAction purely for orchestration. This approach gives you:

- **Version control** — every change to a payload is tracked, reviewable, and reversible
- **Code review** — payloads go through PR review before deployment
- **Environment parity** — the same repo drives dev, staging, and production
- **Fast onboarding** — launch a new service by pointing LeastAction at an existing Git repo; tasks and their payloads deploy automatically
- **Separation of concerns** — your data team owns the SQL/Python/YAML files; LeastAction owns scheduling and orchestration

### **How It Works**

Each file in your Git repo is both the task definition and its payload. The metadata block at the top describes how to create the task; everything after it is the payload:

**SQL example:**
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
WHERE date = '{{ds}}'
GROUP BY date
```

**Python example:**
```python
/*
{
  "name": "run_pipeline",
  "operator_name": "AWSLambdaInvokeFunction",
  "connection_name": "aws-prod",
  "frequency": "0 6 * * *"
}
*/

{
  "pipeline": "daily_etl",
  "date": "{{ds}}",
  "env": "{{environment}}"
}
```

When `LeastActionGitToTask` runs, it clones the repo, reads each file, extracts the metadata to create the task, and stores the remaining content as the task's payload. No manual form filling required.

### **Deploying from Git**

Use the `LeastActionGitToTask` action to sync your Git repo into LeastAction:

- **Manual**: Click the action button on a workflow folder to deploy on demand
- **Automatic**: Attach it as a `preAction` on the root task to deploy before every workflow run

See the [CI/CD guide](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Cicd) for the full setup.

### **Starting a New Service**

If all your payloads are in Git, getting a new data pipeline or service live is straightforward:

1. Create a Git repository with your task files (SQL queries, Python scripts, etc.)
2. Add a Git connection in LeastAction with your credentials
3. Create a workflow folder and attach your config
4. Run `LeastActionGitToTask` — all tasks deploy immediately
5. The workflow runs on schedule from that point forward

No manual task creation, no copy-pasting SQL into forms. The Git repo is the source of truth.

---

## **Payload as a Catalog Item**

For shared or reusable payloads, you can store them in the LeastAction catalog as standalone items. This is useful when:

- Multiple tasks run the same query or script with different configs
- You want to update a payload without touching each task individually
- You manage a library of standard templates

To use a catalog payload, reference its laui in the task's `payload_laui` field instead of providing inline content.

---

## **Best Practices**

**Store payloads in Git.** Inline payloads in the UI work, but Git-stored task files give you version history, review, and fast redeploy. Import them with the **`LeastActionGitToTask`** action (or ask the AI), which creates/updates the catalog tasks from a repo folder — this is also the easiest way to run A/B or parallel-parameter variants side by side and to recover a workflow exactly. See [Git to Task](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Git%20To%20Task).

**Use config parameters for environment differences.** Instead of separate payloads for dev and prod, use a single parameterized payload with `{{environment}}`, `{{s3_bucket}}`, etc., resolved from config at runtime.

**Keep payloads focused.** A payload should do one thing. Use task dependencies in the workflow to chain payloads rather than building monolithic scripts.

**Use `{{ds}}` for date-based processing.** Most batch pipelines need the execution date — `{{ds}}` provides it without hardcoding.

**Test payload templates locally.** Since payloads are just files, you can render them locally with your own Jinja tooling before deploying.
