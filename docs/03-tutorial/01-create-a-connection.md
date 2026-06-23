# Tutorial 1 — Create a Connection

This tutorial builds a working PostgreSQL pipeline from scratch — one of the most common real-world setups. By the end you'll have a connection, an operator, a payload, a scheduled task, and a dependency chain.

> Prefer the fast path? See the [Quickstart](/path?laui=getting-started-01-getting-started-02-quickstart&itemtype=doc.file&itemname=Quickstart). New to the model? Read [Core concepts](/path?laui=getting-started-01-getting-started-03-core-concepts&itemtype=doc.file&itemname=Core%20Concepts) first.

## What a connection is

A **connection** holds credentials and resource settings for an external system, plus concurrency controls. It's the **WHERE** of a task.

## Create it

1. Navigate to your project folder in the UI.
2. Click **Create Connection**.
3. Fill in the form:
   - **Name** — descriptive, e.g. `postgresql` (the name of the bundled demo connection)
   - **Description** — optional
   - **Content** — JSON with credentials
   - **Max Parallelism** — max concurrent tasks using this connection (e.g. `10`)

**Example content:**

```json
{
  "host": "postgres-demo",
  "port": 5432,
  "database": "postgres_demo_db",
  "user": "postgres",
  "password": "postgres"
}
```

> These are the bundled demo values (the `postgres-demo` database that ships with the docker stack). Point `host` / `database` / `user` / `password` at your own PostgreSQL instance when you're ready.

> **Security:** connection values are passed to the operator **exactly as stored** — LeastAction does **not** expand `${...}` placeholders. `PostgresqlExecuteSQL` reads `password` literally, so put the real value here and protect the connection with catalog permissions. For credential-free auth use IAM roles / managed identities, or an operator that takes a native secret reference (e.g. `secret_arn`). See [How secrets work](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection) and [Configuration](/path?laui=getting-started-02-installation-02-configuration&itemtype=doc.file&itemname=Configuration).

Connections take **whatever fields your operator expects** — AWS connections use `region`, `aws_access_key_id`, etc.; a dbt connection uses `dbt_server_url`. The full field reference per system is in the [Connection concept](/path?laui=getting-started-04-concepts-02-connection&itemtype=doc.file&itemname=Connection).

## Or create it with the AI

Anything you can do in the UI you can also do through the AI. There's no `AI > Connection` wizard, so create connections by asking the assistant (Service AI chat) or any MCP-connected client:

> "create a postgres connection named `postgresql` pointing at `postgres-demo:5432`, database `postgres_demo_db`, user `postgres`."

The agent calls `create_catalog_item` with `item_type: connection` and reports the new item's laui. See [MCP](/path?laui=getting-started-06-ai-05-mcp&itemtype=doc.file&itemname=Mcp).

## Next

→ [Tutorial 2 — Choose or generate an operator](/path?laui=getting-started-03-tutorial-02-choose-or-generate-an-operator&itemtype=doc.file&itemname=Choose%20Or%20Generate%20An%20Operator)
