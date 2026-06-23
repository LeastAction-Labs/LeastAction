# Query API

> **Experimental Preview** — The SQL Query Editor and this API are in beta. Connection types: `connection.postgresql`, `connection.mysql`, `connection.AWS` (Athena / Redshift / S3), `connection.gcp` (BigQuery / GCS), `connection.azure` (Blob Storage). Behaviour may change before general availability.

## Overview

`POST /api/v1/query/execute`

Runs a read-only SQL SELECT against any connection item in the catalog. The primary intent is **data inspection at every stage of a pipeline** — before building it (understand the source schema), after running it (verify data landed), and during debugging (sample what's actually in the table).

---

## Authentication

Requires a valid session. The request must include either the session cookie or a bearer token in the `Authorization` header (same as all private API routes).

---

## Request

```http
POST /api/v1/query/execute
Content-Type: application/json
```

```json
{
  "connection_laui": "<ObjectId of a connection catalog item>",
  "sql": "SELECT COUNT(*) FROM orders WHERE created_date = '2026-05-25'"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `connection_laui` | string | LAUI (ObjectId) of a catalog item whose `item_type` starts with `connection.` |
| `sql` | string | SQL query to execute — must be a `SELECT`, `WITH`, or `EXPLAIN` statement |

---

## Response

```json
{
  "columns": ["count"],
  "rows": [[4821]],
  "row_count": 1,
  "truncated": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `columns` | string[] | Column names from the query result |
| `rows` | any[][] | Result rows — each row is a list of values matching `columns` |
| `row_count` | int | Number of rows returned (after truncation) |
| `truncated` | bool | `true` if the result was capped at 10,000 rows |

---

## Limits

- **Max rows**: 10,000 — `truncated: true` in the response when the result is cut
- **Timeout**: 2 minutes — returns `504` if the query does not finish in time
- **DuckDB memory cap**: 512 MB per query — prevents large S3/GCS/Azure scans from OOMing the server
- **DuckDB threads**: 2 — prevents CPU starvation on shared infrastructure

---

## Error Responses

| Status | Condition |
|--------|-----------|
| `400` | SQL is not a SELECT/WITH/EXPLAIN, or contains blocked keywords (INSERT, UPDATE, DELETE, DROP, etc.) |
| `400` | Connection item is missing required fields |
| `400` | SQL syntax or runtime query error |
| `404` | Connection item not found or access denied |
| `502` | Cannot connect to the target database (bad credentials, host unreachable, timeout) |
| `504` | Query timed out after 2 minutes |

---

## Security

- Only `SELECT`, `WITH`, and `EXPLAIN` statements are accepted
- Blocked keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`
- PostgreSQL sessions are opened with `readonly=True, autocommit=True` — writes are impossible at the driver level
- Connection timeout: 10 seconds

---

## Connection Field Auto-Detection

Connection items store credentials as free-form JSON in their `content` field. The API auto-maps common synonyms (first match wins). If required fields can't be resolved, the API returns a `400` with the list of keys that were found.

### PostgreSQL (`connection.postgresql`)

| Parameter | Accepted field names |
|-----------|---------------------|
| `host` | `host`, `hostname`, `server`, `db_host`, `pg_host` |
| `port` | `port`, `db_port`, `pg_port` |
| `database` | `database`, `dbname`, `db`, `db_name`, `schema` |
| `user` | `user`, `username`, `usr`, `login`, `db_user` |
| `password` | `password`, `pass`, `passwd`, `pwd`, `secret` |

### MySQL (`connection.mysql`)

Same as PostgreSQL plus `charset` → `charset`, `encoding`, `character_set`.

### AWS Athena / Redshift (`connection.AWS`)

| Parameter | Accepted field names |
|-----------|---------------------|
| `region` | `region`, `aws_region`, `region_name` |
| `access_key` | `aws_access_key_id`, `access_key`, `access_key_id`, `key_id` |
| `secret_key` | `aws_secret_access_key`, `secret_key`, `secret_access_key`, `secret` |
| `session_token` | `aws_session_token`, `session_token`, `token` |
| `role_arn` | `assume_iam_role`, `role_arn`, `iam_role`, `role` |
| `output_location` (Athena) | `output_location`, `s3_output`, `s3_path`, `result_location` |
| `workgroup` (Athena) | `workgroup`, `work_group`, `athena_workgroup` |
| `database` (Athena) | `database`, `db`, `db_name`, `athena_database` |
| `cluster_identifier` (Redshift) | `cluster_identifier`, `cluster_id`, `redshift_cluster` |
| `workgroup_name` (Redshift Serverless) | `workgroup_name`, `serverless_workgroup`, `rs_workgroup` |

Athena is detected when `output_location` is present. Redshift when `cluster_identifier` or `workgroup_name` is present.

### GCP — BigQuery or GCS (`connection.gcp`)

Detection: if `project` is present → BigQuery. Otherwise → GCS via DuckDB + httpfs.

**BigQuery fields:**

| Parameter | Accepted field names |
|-----------|---------------------|
| `project` | `project`, `project_id`, `gcp_project`, `bq_project` |
| `credentials` | `credentials_json`, `service_account`, `service_account_key`, `credentials`, `gcp_credentials` |
| `dataset` | `dataset`, `dataset_id`, `bq_dataset`, `default_dataset` |
| `location` | `location`, `region`, `bq_location` |

`credentials` should be the full service account JSON (string or dict). Omit to use Application Default Credentials.

**GCS fields (HMAC keys for S3-compatible API):**

| Parameter | Accepted field names |
|-----------|---------------------|
| `access_key` | `hmac_access_key`, `access_key`, `gcs_access_key` |
| `secret_key` | `hmac_secret`, `secret_key`, `gcs_secret` |
| `endpoint` | `endpoint`, `gcs_endpoint` (default: `storage.googleapis.com`) |

### AWS — Athena, Redshift, or S3 (`connection.AWS`)

Detection: `output_location` → Athena. `cluster_identifier` or `workgroup_name` → Redshift. Neither → S3 via DuckDB.

S3 uses the same AWS synonym map (`access_key`, `secret_key`, `session_token`, `role_arn`, `region`). Omit credentials to fall back to the instance credential chain.

### Azure Blob (`connection.azure`)

Uses DuckDB + azure extension.

| Parameter | Accepted field names |
|-----------|---------------------|
| `connection_string` | `connection_string`, `azure_connection_string`, `storage_connection_string` |
| `account_name` | `account_name`, `storage_account`, `azure_account` |
| `account_key` | `account_key`, `storage_key`, `azure_key` |

---

## MCP Usage

The `inspect_data` MCP tool wraps this endpoint. It supports all connection types listed above — S3/GCS/Azure connections use DuckDB, so SQL can call `read_parquet('s3://...')`, `read_csv('gs://...')`, etc.

```
inspect_data(connection_laui="<id>", sql="SELECT ...")
```

Find the right connection with:
```
search_catalog(item_type="connection", name="<name>")
```

### Typical Workflows

**Pre-task — understand source schema before building the pipeline:**
```
inspect_data(connection_laui=<src>, sql="SELECT * FROM source_table LIMIT 10")
inspect_data(connection_laui=<src>, sql="SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'source_table'")
# → understand schema → generate operator → create task
```

**Post-task — verify data landed:**
```
run_task(task_laui=<id>)
get_task_logs(task_laui=<id>, session_id=<id>)
inspect_data(connection_laui=<conn_id>, sql="SELECT COUNT(*) FROM <target_table> WHERE date_col = '<logical_date>'")
```

---

## Per-System Query Examples

### PostgreSQL / MySQL

```sql
-- Row count
SELECT COUNT(*) FROM orders;

-- Sample latest rows
SELECT * FROM orders ORDER BY created_at DESC LIMIT 20;

-- Check this run's partition
SELECT COUNT(*) FROM orders WHERE date_col = '2026-05-26';

-- Inspect schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'orders'
ORDER BY ordinal_position;

-- Find duplicates
SELECT order_id, COUNT(*) FROM orders GROUP BY order_id HAVING COUNT(*) > 1;

-- Check for unexpected nulls
SELECT COUNT(*) - COUNT(customer_id) AS null_count FROM orders;

-- Compare pre/post row counts (after a load)
SELECT COUNT(*) FROM orders WHERE created_at > '2026-05-26 10:00:00';
```

**Connection item content example:**
```json
{
  "host": "db.internal",
  "port": 5432,
  "database": "analytics",
  "user": "readonly_user",
  "password": "..."
}
```

---

### AWS Athena

Athena queries S3-backed tables defined in the Glue Data Catalog. Partition filters are critical for performance — always filter on partition columns.

```sql
-- Count rows in a partition
SELECT COUNT(*) FROM my_db.orders WHERE dt = '2026-05-26';

-- Sample latest partition
SELECT * FROM my_db.orders WHERE dt = '2026-05-26' LIMIT 20;

-- List available partitions
SHOW PARTITIONS my_db.orders;

-- Inspect schema
DESCRIBE my_db.orders;

-- Find duplicates within a partition
SELECT order_id, COUNT(*)
FROM my_db.orders
WHERE dt = '2026-05-26'
GROUP BY order_id HAVING COUNT(*) > 1;

-- Check for nulls in a specific column
SELECT COUNT(*) - COUNT(customer_id) AS null_count
FROM my_db.orders
WHERE dt = '2026-05-26';
```

**Connection item content example:**
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "output_location": "s3://my-athena-results/",
  "database": "my_db",
  "workgroup": "primary"
}
```

---

### AWS Redshift

```sql
-- Row count
SELECT COUNT(*) FROM public.orders;

-- Sample latest rows
SELECT * FROM public.orders ORDER BY created_at DESC LIMIT 20;

-- Inspect table schema
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'orders' AND table_schema = 'public'
ORDER BY ordinal_position;

-- Check distribution key skew
SELECT COUNT(*), customer_id FROM public.orders GROUP BY customer_id ORDER BY COUNT(*) DESC LIMIT 10;

-- Find duplicates
SELECT order_id, COUNT(*) FROM public.orders GROUP BY order_id HAVING COUNT(*) > 1;
```

**Connection item content — Provisioned cluster:**
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "cluster_identifier": "my-redshift-cluster",
  "database": "analytics"
}
```

**Connection item content — Serverless:**
```json
{
  "region": "us-east-1",
  "role_arn": "arn:aws:iam::123456789:role/RedshiftRole",
  "workgroup_name": "my-workgroup",
  "database": "analytics"
}
```

---

### BigQuery

BigQuery bills by bytes scanned — always use partition filters and column projections in inspection queries.

```sql
-- Row count (use partition filter to avoid full scan)
SELECT COUNT(*) FROM `my_project.my_dataset.orders`
WHERE DATE(_PARTITIONTIME) = '2026-05-26';

-- Sample latest rows
SELECT * FROM `my_project.my_dataset.orders`
WHERE DATE(_PARTITIONTIME) = '2026-05-26'
LIMIT 20;

-- Inspect schema via INFORMATION_SCHEMA
SELECT column_name, data_type, is_nullable
FROM `my_project.my_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'orders';

-- Find duplicates
SELECT order_id, COUNT(*)
FROM `my_project.my_dataset.orders`
WHERE DATE(_PARTITIONTIME) = '2026-05-26'
GROUP BY order_id HAVING COUNT(*) > 1;

-- Check for nulls
SELECT COUNTIF(customer_id IS NULL) AS null_count
FROM `my_project.my_dataset.orders`
WHERE DATE(_PARTITIONTIME) = '2026-05-26';
```

**Connection item content example:**
```json
{
  "project_id": "my-gcp-project",
  "bq_dataset": "my_dataset",
  "credentials_json": { "type": "service_account", "project_id": "...", "private_key": "...", ... }
}
```

---

### S3 — DuckDB (`connection.AWS` with no Athena/Redshift fields)

DuckDB reads directly from S3 without Athena or Glue. Use `read_parquet`, `read_csv`, `read_json`. Glob patterns work.

```sql
-- Sample a single parquet file
SELECT * FROM read_parquet('s3://my-bucket/data/orders/2026-05-26.parquet') LIMIT 50;

-- Sample across a prefix (glob)
SELECT * FROM read_parquet('s3://my-bucket/data/orders/*.parquet') LIMIT 50;

-- Inspect schema (column names and types)
DESCRIBE SELECT * FROM read_parquet('s3://my-bucket/data/orders/2026-05-26.parquet');

-- Count rows in a partition
SELECT COUNT(*) FROM read_parquet('s3://my-bucket/data/orders/dt=2026-05-26/*.parquet');

-- Detect type mismatches
SELECT typeof(order_id), typeof(amount), COUNT(*)
FROM read_parquet('s3://my-bucket/data/orders/2026-05-26.parquet')
GROUP BY 1, 2;

-- Check for nulls across columns
SELECT
  COUNT(*) - COUNT(order_id)     AS null_order_id,
  COUNT(*) - COUNT(customer_id)  AS null_customer_id
FROM read_parquet('s3://my-bucket/data/orders/2026-05-26.parquet');

-- List files in a prefix with row counts
SELECT filename, COUNT(*) AS row_count
FROM read_parquet('s3://my-bucket/data/orders/**/*.parquet', filename=true)
GROUP BY filename;
```

**CSV on S3:**

```sql
-- Auto-detect delimiter, header, and types (simplest)
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true) LIMIT 20;

-- Explicit header + delimiter
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv', header=true, delim=',') LIMIT 20;

-- Tab-separated
SELECT * FROM read_csv('s3://my-bucket/raw/orders.tsv', header=true, delim='\t') LIMIT 20;

-- Override inferred column types
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv',
  header=true,
  columns={'order_id': 'VARCHAR', 'amount': 'DOUBLE', 'created_at': 'TIMESTAMP'}
) LIMIT 20;

-- Inspect schema before querying
DESCRIBE SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true);

-- Count rows
SELECT COUNT(*) FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true);

-- Glob across multiple CSV files in a prefix
SELECT * FROM read_csv('s3://my-bucket/raw/orders_*.csv', auto_detect=true) LIMIT 50;

-- Skip bad rows (ignore parse errors)
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv',
  header=true,
  ignore_errors=true
) LIMIT 20;

-- Check for nulls after load
SELECT
  COUNT(*) - COUNT(order_id)  AS null_order_id,
  COUNT(*) - COUNT(amount)    AS null_amount
FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true);

-- Find duplicates
SELECT order_id, COUNT(*)
FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true)
GROUP BY order_id HAVING COUNT(*) > 1;
```

**Connection item content example:**
```json
{
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "region": "us-east-1"
}
```

For IAM role-based auth, use `role_arn` instead and omit the keys. For EC2/ECS instance profile auth, omit all credential fields.

---

### GCS — DuckDB (`connection.gcp` with no `project` field)

GCS is accessed via the S3-compatible API using HMAC keys. SQL uses `gs://` paths.

```sql
-- Sample a parquet file
SELECT * FROM read_parquet('gs://my-bucket/data/orders/2026-05-26.parquet') LIMIT 50;

-- Count rows
SELECT COUNT(*) FROM read_parquet('gs://my-bucket/data/orders/*.parquet');

-- Inspect schema
DESCRIBE SELECT * FROM read_parquet('gs://my-bucket/data/orders/2026-05-26.parquet');

-- Sample CSV
SELECT * FROM read_csv('gs://my-bucket/raw/orders.csv', header=true) LIMIT 20;
```

**Connection item content example:**
```json
{
  "hmac_access_key": "GOOG...",
  "hmac_secret": "...",
  "gcs_endpoint": "storage.googleapis.com"
}
```

Generate HMAC keys in GCP Console → Cloud Storage → Settings → Interoperability.

---

### Azure Blob — DuckDB (`connection.azure`)


```sql
-- Sample a parquet file
SELECT * FROM read_parquet('azure://my-container/data/orders/2026-05-26.parquet') LIMIT 50;

-- Count rows across a prefix
SELECT COUNT(*) FROM read_parquet('azure://my-container/data/orders/*.parquet');

-- Inspect schema
DESCRIBE SELECT * FROM read_parquet('azure://my-container/data/orders/2026-05-26.parquet');

-- Sample CSV
SELECT * FROM read_csv('azure://my-container/raw/orders.csv', header=true) LIMIT 20;
```

**Connection item content — connection string:**
```json
{
  "connection_string": "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
}
```

**Connection item content — account name + key:**
```json
{
  "account_name": "mystorageaccount",
  "account_key": "..."
}
```

---

## UI Access

The Query API also powers the **SQL Query Editor** in the web UI:

- **Developer mode**: left sidebar terminal icon → `/query`
- **Business user mode**: top nav terminal icon → `/query`

The editor supports any connection item, Monaco SQL editor with syntax highlighting, and displays results as a table. Results are capped at 10,000 rows with a truncation indicator.
