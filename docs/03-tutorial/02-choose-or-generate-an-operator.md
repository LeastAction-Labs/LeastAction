# Tutorial 2 — Choose or Generate an Operator

An **operator** contains the execution logic — the **HOW**. LeastAction ships operators for PostgreSQL, AWS, Airflow, dbt, and more, and you can generate new ones with AI in seconds.

## Option A — Use an existing operator

Browse the operators folder and select one, e.g. `PostgresqlExecuteSQL`.

## Option B — Generate with AI

1. Go to **AI > Operator** in the UI.
2. Describe what you need in plain English.
3. The AI generates the operator code, a sample connection, and a sample payload.
4. Review, test, and save.

## The operator contract

Every operator's `main.py` defines exactly four methods, called in order:

```python
def initialize(least_action_task_object):            # build the client/connection
def run(least_action_task_object, client):            # do the work; return status + result
def check_completion(least_action_task_object, client, run_details):  # poll async / pass through sync
def finish(least_action_task_object, client, completion_details, run_details):  # cleanup
```

When saving, you also provide a **bashblock** (dependencies, e.g. `pip install psycopg2-binary`) and sample connection/payload JSON.

> Full contract, rules, logging, and validation: the [Operator concept](/path?laui=getting-started-04-concepts-03-operator&itemtype=doc.file&itemname=Operator) and the [Write an Operator guide](/path?laui=getting-started-05-building-pipelines-01-write-an-operator&itemtype=doc.file&itemname=Write%20An%20Operator). For AI generation specifics see [Service AI](/path?laui=getting-started-06-ai-02-service-ai&itemtype=doc.file&itemname=Service%20Ai).

## Next

→ [Tutorial 3 — Write a payload](/path?laui=getting-started-03-tutorial-03-write-a-payload&itemtype=doc.file&itemname=Write%20A%20Payload)
