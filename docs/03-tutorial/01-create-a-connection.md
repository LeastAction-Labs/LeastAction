# Tutorial 1 — Create a Connection

This tutorial builds a working PostgreSQL pipeline from scratch — one of the most common real-world setups. By the end you'll have a connection, an operator, a payload, a scheduled task, and a dependency chain.

> Prefer the fast path? See the [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart). New to the model? Read [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) first.

## What a connection is

A **connection** holds credentials and resource settings for an external system, plus concurrency controls. It's the **WHERE** of a task.

## Create it

1. Navigate to your project folder in the UI.
2. Click **Create Connection**.
3. Fill in the form:
   - **Name** — descriptive, e.g. `postgres-prod`
   - **Description** — optional
   - **Content** — JSON with credentials
   - **Max Parallelism** — max concurrent tasks using this connection (e.g. `10`)

**Example content:**

```json
{
  "host": "db.example.com",
  "port": 5432,
  "database": "analytics",
  "user": "pipeline_user",
  "password": "${AWS_SECRET_MANAGER:db-password}"
}
```

> **Security:** never store plain-text passwords — reference secrets with `${AWS_SECRET_MANAGER:secret-name}` or environment variables. See [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration).

Connections take **whatever fields your operator expects** — AWS connections use `region`, `aws_access_key_id`, etc.; a dbt connection uses `dbt_server_url`. The full field reference per system is in the [Connection concept](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection).

## Next

→ [Tutorial 2 — Choose or generate an operator](/path?laui=getting-started-03-tutorial-02-choose-or-generate-an-operator&itemtype=doc.file&itemname=Choose%20Or%20Generate%20An%20Operator)
