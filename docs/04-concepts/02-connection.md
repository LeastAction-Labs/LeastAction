# LeastAction Connection - User Guide

## Overview

A **Connection** in LeastAction is a reusable configuration that manages computational resources, credentials, and execution limits. Connections provide a secure, centralized way to manage access to external systems and control task execution concurrency.

**Key Concepts:**

- **Secure Credential Storage**: Connections store credentials and configuration for external systems
- **Resource Management**: Control concurrent task execution via `max_parallelism`
- **Task Queuing**: Built-in queue management with priority and sort ordering
- **Reusability**: One connection can be used by multiple tasks and operators

---

## Connection Structure

```json
{
"item_type": "connection.{subtype}",
"name": "my-connection",
"parent_laui": "folder-connection-laui",
"content": {
    // The content field can contain any fields that the operator supports
    // Structure is operator-specific (flat structure recommended)
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/LeastActionRole"
    },
"max_parallelism": 10,
"current_parallelism": 0,
"in_queue": 0,
"sort_order": {
    "priority": "descending",
    "start_date": "ascending"
    }
}
```

### Core Fields


| Field                 | Type    | Required | Description                                                                                                                       |
| --------------------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `item_type`           | string  | Yes      | Format is `connection.{subtype}` (e.g., `connection.AWSIAMRole`). Subtype is optional — use `connection` if no subtype is needed. |
| `name`                | string  | Yes      | Connection identifier                                                                                                             |
| `parent_laui`         | string  | Yes      | Parent folder (must be `folder.connection` type)                                                                                  |
| `content`             | object  | Yes      | Credentials and configuration (operator-specific, can contain any fields the operator supports)                                   |
| `max_parallelism`     | integer | Yes      | Maximum concurrent tasks allowed                                                                                                  |
| `current_parallelism` | integer | Auto     | Currently running tasks (system-managed)                                                                                          |
| `in_queue`            | integer | Auto     | Tasks waiting in queue (system-managed)                                                                                           |
| `sort_order`          | object  | Optional | Task queue sorting rules                                                                                                          |


### Sort Order Configuration

The `sort_order` field controls how tasks are selected from the queue:

```json
{
"sort_order": {
    "priority": "descending", // Higher priority tasks first
    "start_date": "ascending" // Older tasks first (within same priority)
    }
}
```

**Available Sort Fields:**

- `priority`: Task priority level
- `start_date`: Task scheduled start time
- `name`: Task name (alphabetical)
**Sort Directions:**
- `descending` / `DESC`: Highest to lowest
- `ascending` / `ASC`: Lowest to highest

---

## Connection Types

LeastAction supports connections for major cloud providers and services. All connection types follow the same core structure but have different `content` schemas.
**Important:** When creating a new operator using AI, a connection sample is automatically generated. It's **strongly recommended** to use this AI-generated sample as your starting template and customize it for your environment.

### AWS IAM Role Connection

**Type:** `connection.AWSIAMRole`
**Use Cases:**

- AWS Lambda functions
- S3 operations
- EC2 instance management
- Athena queries
**Access Pattern in Operators:**

```python
def initialize(least_action_task_object, least_action_parameters):
connection = least_action_task_object.get('connection', {})
# Direct access to connection fields
region = connection.get('region', 'us-east-1')
role_arn = connection.get('role_arn')
# Credentials can be direct or via IAM role
if connection.get('aws_access_key_id'):
client = boto3.client(
'lambda',
region_name=region,
aws_access_key_id=connection['aws_access_key_id'],
aws_secret_access_key=connection['aws_secret_access_key']
)
else:
# Use IAM role attached to EC2 instance
client = boto3.client('lambda', region_name=region)
return client
```

**Recommended Setup (IAM Role - Most Secure):**

```json
{
"item_type": "connection.AWSIAMRole",
"name": "aws-production",
"parent_laui": "folder-connection-laui",
"content": {
    "role_arn": "arn:aws:iam::123456789012:role/LeastActionRole",
    "region": "us-east-1"
    },
"max_parallelism": 50,
"sort_order": {
    "priority": "descending",
    "start_date": "ascending"
    }
}
```

**Alternative Setup (With Static Access Keys):**

```json
{
"item_type": "connection.AWSIAMRole",
"name": "aws-production-with-keys",
"parent_laui": "folder-connection-laui",
"content": {
    "region": "us-east-1",
    "aws_access_key_id": "<your-access-key-id>",
    "aws_secret_access_key": "<your-secret-access-key>"
    },
"max_parallelism": 50,
"sort_order": {
    "priority": "descending"
    }
}
```

> These values are stored and passed to the operator as-is — LeastAction does not resolve `${...}`
> placeholders. Prefer IAM roles (below) so no keys live in the connection. See
> [How secrets actually work](#2-how-secrets-actually-work).

**Best Practice:**

1. Use IAM roles attached to LeastAction's EC2 instances instead of storing credentials
2. If keys are unavoidable, scope them to least privilege and protect the connection with catalog permissions
3. Always use the AI-generated connection sample when creating a new operator
  **Operators Compatible:**

- Any operator with type `operator.AWSIAMRole` (e.g., `AWSLambdaInvokeFunction`, `AWSS3MoveData`, `AWSEC2StartInstance`, `AWSAthenaExecuteSQL`)

**Note on Operator-Connection Mapping:** Subtype matching between connection and operator is optional. When `enforce_connection_operator_mapping: true` is set in `system.yml`, the system validates that the connection subtype is compatible with the operator subtype (e.g., `connection.AWSIAMRole` with `operator.AWSIAMRole`). With enforcement off, any connection can be used with any operator.
  **AI-Generated Sample:** When creating an AWS Lambda operator via AI, the system generates a connection sample like this:

```json
{
"name": "AWS Lambda Production",
"type": "connection.AWSIAMRole",
"content": {
    "role_arn": "arn:aws:iam::123456789012:role/LambdaRole",
    "region": "us-east-1"
    }
}
```

## **Important:** The `content` field structure is determined by what the operator expects. Always use the AI-generated connection sample as your starting point, as it contains the exact fields the operator needs.

### GCP Service Account Connection

**Type:** `connection.GCPServiceAccount`
**Use Cases:**

- Cloud Functions
- BigQuery operations
- GCS storage
- Compute Engine management
**Access Pattern in Operators:**

```python
def initialize(least_action_task_object, least_action_parameters):
connection = least_action_task_object.get('connection', {})
# Direct access to connection fields
project_id = connection.get('project_id')
service_account_email = connection.get('service_account_email')
region = connection.get('region', 'us-central1')
# Use Workload Identity or service account key
if connection.get('service_account_key_path'):
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = connection['service_account_key_path']
client = bigquery.Client(project=project_id)
return client
```

**Recommended Setup (Workload Identity - Most Secure):**

```json
{
"item_type": "connection.GCPServiceAccount",
"name": "gcp-production",
"parent_laui": "folder-connection-laui",
"content": {
    "project_id": "my-project-id",
    "service_account_email": "leastaction@my-project.iam.gserviceaccount.com",
    "region": "us-central1"
    },
"max_parallelism": 30,
"sort_order": {
    "priority": "descending"
    }
}
```

**Alternative Setup (With Service Account Key):**

```json
{
"item_type": "connection.GCPServiceAccount",
"name": "gcp-with-key",
"parent_laui": "folder-connection-laui",
"content": {
    "project_id": "my-project-id",
    "service_account_email": "leastaction@my-project.iam.gserviceaccount.com",
    "service_account_key_path": "/secrets/gcp/sa-key.json",
    "region": "us-central1"
    },
"max_parallelism": 30,
"sort_order": {
    "priority": "descending"
    }
}
```

**Best Practice:**

1. Use Workload Identity so no key lives in the connection
2. If a key file is needed, mount it on the LeastAction host and reference its path (as above)
3. Protect the connection with catalog permissions and a least-privilege service account
4. Always start with AI-generated connection sample
  **AI-Generated Sample:** When creating a GCP BigQuery operator via AI:

```json
{
"name": "GCP BigQuery Production",
"type": "connection.GCPServiceAccount",
"content": {
    "project_id": "my-project-id",
    "region": "us-central1"
    }
}
```

---

### Azure Managed Identity Connection

**Type:** `connection.AzureManagedIdentity`
**Use Cases:**

- Azure Functions
- Blob Storage operations
- Azure SQL Database
- VM management
**Access Pattern in Operators:**

```python
def initialize(least_action_task_object, least_action_parameters):
connection = least_action_task_object.get('connection', {})
# Direct access to connection fields
tenant_id = connection.get('tenant_id')
subscription_id = connection.get('subscription_id')
managed_identity_client_id = connection.get('managed_identity_client_id')
# Use Managed Identity
credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
client = BlobServiceClient(
account_url=f"https://{connection['storage_account_name']}.blob.core.windows.net",
credential=credential
)
return client
```

**Recommended Setup (Managed Identity - Most Secure):**

```json
{
"item_type": "connection.AzureManagedIdentity",
"name": "azure-production",
"parent_laui": "folder-connection-laui",
"content": {
    "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "managed_identity_client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "region": "eastus"
    },
"max_parallelism": 40,
    "sort_order": {
    "priority": "descending"
    }
}
```

**Best Practice:**

1. Use Azure Managed Identity assigned to LeastAction's VM/Container instance — no secret in the connection
2. If credentials are unavoidable, store the real value and protect the connection with catalog permissions
3. Scope the identity/service principal to least privilege
4. Start with AI-generated connection sample
  **AI-Generated Sample:** When creating an Azure Blob Storage operator:

```json
{
"name": "Azure Blob Production",
"type": "connection.AzureManagedIdentity",
"content": {
    "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "region": "eastus"
    }
}
```

---

### PostgreSQL Connection

**Type:** `connection.postgresql`
**Use Cases:**

- SQL query execution
- Data extraction
- Database migrations
**Access Pattern in Operators:**

```python
def initialize(least_action_task_object):
connection = least_action_task_object.get('connection', {})
# Direct access to connection fields (flat structure)
conn = psycopg2.connect(
host=connection.get('host'),
port=connection.get('port', 5432),
database=connection.get('database'),
user=connection.get('user'),
password=connection.get('password'),
)
return conn
```

**Recommended Setup:**

```json
{
"item_type": "connection.postgresql",
"name": "postgresql",
"parent_laui": "folder-connection-laui",
"content": {
    "host": "postgres-demo",
    "port": 5432,
    "database": "postgres_demo_db",
    "user": "postgres",
    "password": "postgres"
    },
"max_parallelism": 20,
"sort_order": {
    "priority": "descending"
    }
}
```

> This is the **bundled demo connection** (`postgresql`), which points at the internal `postgres-demo` database that ships with the docker stack. Edit `host` / `port` / `database` / `user` / `password` to point at your own PostgreSQL instance.

**Best Practice:**

1. `PostgresqlExecuteSQL` reads `user` / `password` literally — store the real values and protect the connection with catalog permissions
2. Use read-only database users when possible
3. Always start with AI-generated connection sample
  **AI-Generated Sample:** When creating a PostgreSQL operator:

```json
{
"name": "postgresql",
"type": "connection.postgresql",
"content": {
    "host": "postgres-demo",
    "port": 5432,
    "database": "postgres_demo_db",
    "user": "postgres"
    }
}
```

---

## Creating Connections

### Step 1: Create Connection Folder

All connections must be stored in a `folder.connection` type folder:

```bash
POST /api/v1/catalog/create
```

```json
{
"item_type": "folder.connection",
"name": "production-connections",
"is_root": true
}
```

**Response:**

```json
{
"item_laui": "conn-folder-123456",
"status": "success"
}
```

---

### Step 2: Use AI to Generate Operator and Connection Sample

The recommended workflow is to use AI to generate both operator and connection:

1. Navigate to **AI > Operator** in LeastAction UI
2. Describe what you want: "Create an operator to invoke AWS Lambda functions"
3. AI generates:

- Complete operator code
- Sample connection JSON
- Sample payload JSON
**AI Output Example:**

```json
{
"operator": {
    "name": "AWSLambdaInvokeFunction",
    "type": "operator.AWSLambda",
    "codeblock": {
        "main.py": "# Complete operator code..."
        },
    "bashblock": {
        "main.sh": "pip install boto3"
        }
    },
"connection_sample": {
    "name": "AWS Lambda Production",
    "type": "connection.AWSIAMRole",
    "content": {
        "region": "us-east-1",
        "role_arn": "arn:aws:iam::123456789012:role/LambdaRole"
        }
},
"payload_sample": {
    "function_name": "my-lambda",
    "invoke_payload": {}
    }
}
```

---

### Step 3: Create Connection Using UI Form

LeastAction provides a **form-based interface** for creating connections. Take the AI-generated `connection_sample` and use it to fill the form:

**UI Form Steps:**

1. Navigate to **Connections** section
2. Click **Create Connection** button
3. Fill in the form fields:
  - **Subtype**: Optional. Select from dropdown (e.g., `connection.AWSIAMRole`) or leave blank. When `enforce_connection_operator_mapping: true` in `system.yml`, only compatible operator subtypes will be selectable when creating a task.
  - **Parent Folder**: Browse and select connection folder or use current folder
  - **Name**: Enter connection name (e.g., "lambda-production")
  - **Description**: Optional description
  - **Content**: JSON editor - paste and customize AI-generated content:
    ```json
    {
      "role_arn": "arn:aws:iam::123456789012:role/LeastActionProdRole",
      "region": "us-east-1"
    }
    ```
  - **Max Parallelism**: Enter number (e.g., 50)
  - **Sort Order**: JSON editor - define queue sorting:
    ```json
    {
      "priority": "descending",
      "start_date": "ascending"
    }
    ```
4. Click **Save**

**Alternative: API Creation**

You can also create connections programmatically via API:

```bash
POST /api/v1/catalog/create
```

```json
{
"item_type": "connection.AWSIAMRole",
"name": "lambda-production",
"parent_laui": "conn-folder-123456",
"content": {
    "role_arn": "arn:aws:iam::123456789012:role/LeastActionProdRole",
    "region": "us-east-1"
    },
"max_parallelism": 50,
"sort_order": {
    "priority": "descending",
    "start_date": "ascending"
    }
}
```

**Response:**

```json
{
"item_laui": "conn-lambda-prod-789",
"status": "success"
}
```

## **💡 Understanding Subtypes**: Subtypes (e.g., `connection.AWSIAMRole`) are optional labels that indicate which operators a connection is intended for. Subtype compatibility is only enforced when `enforce_connection_operator_mapping: true` in `system.yml`. With enforcement enabled, the UI filters compatible connections when creating a task. With enforcement disabled, any connection can pair with any operator regardless of subtype.

### Step 4: Use Connection in Task

Reference the connection by its `laui` when creating a task:

```json
{
"task_id": "process-daily-events",
"workflow": "event-pipeline",
"operator": "operator.AWSLambda",
"connection": "conn-lambda-prod-789",
"payload": {
    "function_name": "process-events",
    "invoke_payload": {
        "date": "2024-01-15"
        }
    }
}
```

---

## Task Queue Management

### How Task Queuing Works

1. **Task Submission**: When a task is scheduled, it enters the connection's queue
2. **Queue Position**: Tasks are sorted according to `sort_order` configuration
3. **Execution Selection**: System picks top `max_parallelism` tasks from sorted queue
4. **Concurrency Control**: `current_parallelism` tracks running tasks
5. **Queue Monitoring**: `in_queue` shows waiting tasks
  **Workflow:**

```
Task Created → Queue Entry → Sort by Rules → Check max_parallelism → Execute or Wait
```

---

### Priority-Based Task Picking

**Scenario:** High-priority tasks should run first
**Connection Configuration:**

```json
{
"max_parallelism": 5,
"sort_order": {
    "priority": "descending" // Higher priority first
    }
}
```

**Task Queue:**

```
Priority 5 (runs first)
Priority 4
Priority 3
Priority 2
Priority 1 (runs last)
```

## **Result:** Top 5 priority tasks execute concurrently.

### Time-Based Task Picking

**Scenario:** Process tasks in order received
**Connection Configuration:**

```json
{
"max_parallelism": 10,
"sort_order": {
    "start_date": "ascending" // Oldest first
    }
}
```

**Task Queue:**

```
2024-01-15 08:00 (runs first)
2024-01-15 09:00
2024-01-15 10:00
...
```

## **Result:** First 10 oldest tasks execute.

### Combined Sorting

**Scenario:** High-priority tasks first, then by time
**Connection Configuration:**

```json
{
"max_parallelism": 8,
"sort_order": {
    "priority": "descending",
    "start_date": "ascending"
    }
}
```

**Task Queue Logic:**

1. Sort by priority (highest first)
2. Within same priority, sort by start_date (oldest first)
  **Example Queue:**

```
Priority 5, 08:00 (runs first)
Priority 5, 09:00
Priority 4, 07:00
Priority 4, 10:00
Priority 3, 06:00
...
```

---

## Advanced Features

### 🔜 Coming Soon: Connection Groups

**Feature:** Group multiple connections for load balancing

```json
{
"item_type": "connection.group",
"name": "lambda-cluster",
"connections": [
    "conn-lambda-prod-1",
    "conn-lambda-prod-2",
    "conn-lambda-prod-3"
    ],
"load_balance_strategy": "round_robin"
}
```

**Benefits:**

- Distribute tasks across multiple resource pools
- Increase total parallelism
- Implement failover strategies

---

### 🔜 Coming Soon: Connection Utilization

**Feature:** Dynamic parallelism based on resource utilization

```json
{
"max_parallelism": 50,
"max_utilization": 80, // Percentage
"utilization_metric": "cpu_percent"
}
```

**Behavior:**

- Monitor connection resource utilization (CPU, memory, etc.)
- Update via `runningIntervalAction`
- Prevent task execution if `utilization >= max_utilization`
- Resume when utilization drops below threshold
**Example Action:**

```json
{
"runningIntervalAction": [
{
"action": "LeastActionUpdateConnectionUtilization",
"interval": 300,
"connection": "conn-ec2-prod",
"variables": {
    "metric": "cpu_utilization"
    }
}
]
}
```

---

## Security Best Practices

### 1. Always Start with AI-Generated Connection Sample

✅ **Best Practice:**

1. Use AI to generate operator
2. Review the generated `connection_sample`
3. Customize the sample for your environment
4. Never create connection from scratch
  **Why:** AI ensures correct structure and compatible fields for the operator.

---

### 2. How secrets actually work

**There is no platform-wide secret substitution.** Connection field values are passed to the
operator **exactly as stored** — LeastAction does **not** expand `${...}` placeholders in connection
content. A string like `"${AWS_SECRET_MANAGER:db-password}"` is handed to the operator verbatim, and
most operators (e.g. `PostgresqlExecuteSQL`, which reads `connection['password']` directly) would try
to use that literal string as the credential. So you have three real options:

1. **Operator-native secret references.** An operator can accept a cloud-native secret handle and let
   the SDK resolve it. The bundled example is `AWSRedshiftDataExecuteSQL`, which takes an optional
   `secret_arn` (a Secrets Manager ARN) and passes it to the Redshift Data API — AWS fetches the
   credentials, not LeastAction. Only operators that explicitly implement this support it.
2. **IAM roles / managed identities** (see §3 below) — the preferred cloud pattern: no credentials in
   the connection at all; the SDK picks them up from the instance profile / workload identity.
3. **Platform-level env secrets** — for *platform* secrets (root password, the Claude/LLM API key, DB
   URL), `backend/src/common/secrets.py:get_secret()` resolves from environment, and from AWS Secrets
   Manager when `USE_AWS_SECRETS=true`. This applies to deployment config (`deploy/.env`), **not** to
   per-connection fields.

For operators without secret support, the connection stores the actual value. Protect it with
catalog permissions and a least-privilege DB/cloud user, and prefer option 1 or 2 above.

```json
// AWSRedshiftDataExecuteSQL — operator-native secret reference (resolved by AWS, not LeastAction)
{
"content": {
    "secret_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/redshift-AbCdEf"
    }
}
```

---

### 3. Use IAM Roles and Managed Identities

**AWS:**

- Attach IAM role to LeastAction EC2 instance
- Grant role permissions to access resources
- Reference role ARN in connection (optional)
- boto3 automatically uses instance profile
**GCP:**
- Use Workload Identity
- Assign service account to LeastAction GKE pod
- Reference service account email (optional)
- gcloud SDK automatically uses Workload Identity
**Azure:**
- Enable Managed Identity on VM/Container
- Grant identity permissions to resources
- Reference managed identity client ID
- Azure SDK automatically uses Managed Identity

---

### 4. Least Privilege Principle

Grant connections **only** the permissions they need:
**Example AWS IAM Policy:**

```json
{
"Version": "2012-10-17",
"Statement": [
{
"Effect": "Allow",
"Action": [
"lambda:InvokeFunction"
],
"Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-events"
}
]
}
```

---

### 5. Separate Connections by Environment

Create separate connections for each environment:

```
production-connections/
├── aws-lambda
├── postgresql
└── gcp-bigquery
staging-connections/
├── aws-lambda
├── postgresql
└── gcp-bigquery
```

---

## Monitoring and Troubleshooting

### View Connection Status

```bash
GET /api/v1/catalog/item/{connection_laui}
```

**Response:**

```json
{
"name": "lambda-production",
"max_parallelism": 50,
"current_parallelism": 23,
"in_queue": 12,
"sort_order": {
    "priority": "descending"
    },
"content": {
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789012:role/LeastActionRole"
    }
}
```

**Metrics:**

- `current_parallelism`: Tasks currently executing
- `in_queue`: Tasks waiting to execute
- Available capacity: `max_parallelism - current_parallelism`

---

### Common Issues

#### Issue: Tasks Not Starting

**Symptoms:**

- `in_queue` increasing
- `current_parallelism` at max
**Solutions:**

1. Increase `max_parallelism`
2. Check if tasks are hanging (not completing)
3. Review task execution logs
4. Check connection resource limits

---

#### Issue: Wrong Task Execution Order

**Symptoms:**

- Low-priority tasks run before high-priority
- Newer tasks run before older tasks
**Solutions:**

1. Verify `sort_order` configuration
2. Check task priority values
3. Confirm `start_date` is set correctly

---

#### Issue: Connection Authentication Failures

**Symptoms:**

- Tasks fail with authentication errors
- "Access Denied" or "Unauthorized" errors
**Solutions:**

1. Verify credentials in secrets manager
2. Check IAM role/service account permissions
3. Confirm connection `content` has correct field names (use AI-generated sample)
4. Validate region/endpoint configuration
5. Check operator code for correct field access pattern

---

#### Issue: Connection Structure Mismatch

**Symptoms:**

- KeyError in operator logs
- "Field not found" errors
- Tasks fail immediately
**Solutions:**

1. **Always use AI-generated connection sample**
2. Compare your connection with AI sample
3. Check operator code for expected field names
4. Verify connection `content` uses flat structure (not nested)
  **Example Fix:**
   ❌ **Wrong (nested structure):**

```json
{
"content": {
"aws": {
    "region": "us-east-1",
    "role_arn": "arn:..."
    }
}
}
```

✅ **Correct (flat structure):**

```json
{
"content": {
    "region": "us-east-1",
    "role_arn": "arn:..."
    }
}
```

---

## Example Configurations

### High-Throughput Lambda Connection

```json
{
"item_type": "connection.AWSIAMRole",
"name": "lambda-high-throughput",
"parent_laui": "conn-folder-123",
"content": {
    "role_arn": "arn:aws:iam::123456789012:role/LeastActionHighThroughput",
    "region": "us-east-1"
    },
"max_parallelism": 100,
"sort_order": {
    "priority": "descending",
    "start_date": "ascending"
    }
}
```

## **Use Case:** High-volume event processing with priority queuing

### Time-Critical Database Connection

The same `postgresql` connection, tuned for in-order processing (lower parallelism, oldest-first):

```json
{
"item_type": "connection.postgresql",
"name": "postgresql",
"parent_laui": "conn-folder-123",
"content": {
    "host": "postgres-demo",
    "port": 5432,
    "database": "postgres_demo_db",
    "user": "postgres",
    "password": "postgres"
    },
"max_parallelism": 10,
"sort_order": {
    "start_date": "ascending" // Process in order received
    }
}
```

## **Use Case:** Sequential processing of time-sensitive database operations

### Balanced GCP Connection

```json
{
"item_type": "connection.GCPServiceAccount",
"name": "gcp-balanced",
"parent_laui": "conn-folder-123",
"content": {
    "project_id": "my-project",
    "service_account_email": "leastaction@my-project.iam.gserviceaccount.com",
    "region": "us-central1"
    },
"max_parallelism": 30,
"sort_order": {
    "priority": "descending",
    "name": "ascending"
    }
}
```

## **Use Case:** Balanced workload with priority and alphabetical fallback

## Quick Start Workflow

### 1. Generate Operator with AI

```
1. Go to AI > Operator
2. Enter: "Create operator to invoke AWS Lambda functions"
3. AI generates operator code + connection sample + payload sample
```

### 2. Save Operator

```
1. Review generated code
2. Click "Save" to catalog
3. Note the operator_laui
```

### 3. Create Connection from AI Sample

```
1. Copy the connection_sample from AI output
2. Customize with your credentials
3. POST /api/v1/catalog/create with connection JSON
4. Note the connection_laui
```

### 4. Create Task

```json
{
"task_id": "my-first-task",
"workflow": "my-workflow",
"operator": "<operator_laui>",
"connection": "<connection_laui>",
"payload": {
// Use AI-generated payload_sample
}
}
```

### 5. Monitor Execution

```
1. Check connection metrics (current_parallelism, in_queue)
2. Review task logs
3. Adjust max_parallelism if needed
```

---

## API Reference

### Create Connection

```bash
POST /api/v1/catalog/create
Content-Type: application/json
```

**Request:**

```json
{
"item_type": "connection.{subtype}",
"name": "connection-name",
"parent_laui": "folder-laui",
"content": {
// Flat structure with operator-specific fields
},
"max_parallelism": 10,
"sort_order": {}
}
```

---

### Update Connection

```bash
PUT /api/v1/catalog/update/{connection_laui}
Content-Type: application/json
```

**Request:**

```json
{
"max_parallelism": 20,
"sort_order": {
"priority": "ascending"
}
}
```

---

### Get Connection Details

```bash
GET /api/v1/catalog/item/{connection_laui}
```

---

### List Connections

```bash
GET /api/v1/catalog/list?parent_laui={folder_laui}&item_type=connection
```

---

## Next Steps

1. **[Learn About Operators](/path?laui=getting-started-04-concepts-03-operator&itemtype=doc.file&itemname=Operator)** - Understand operator-connection compatibility
2. **[Explore Actions](/path?laui=getting-started-04-concepts-06-action&itemtype=doc.file&itemname=Action%20Aka%20Hook)** - Use actions to enhance connections
3. **[Config Guide](/path?laui=getting-started-04-concepts-05-config&itemtype=doc.file&itemname=Config)** - Set workflow defaults and parameters
4. **[CI/CD Guide](/path?laui=getting-started-08-cicd-01-git-to-task&itemtype=doc.file&itemname=Cicd)** - Deploy tasks from Git

---

## Key Takeaways

## ✅ **Always use AI-generated connection samples** - They have the correct structure for the operator
✅ **Connection content uses flat structure** - Not nested under `content.aws` or similar
✅ **Connection values pass to the operator as-is** - LeastAction does not resolve `${...}` placeholders; secret handling is operator-specific (e.g. `secret_arn`)
✅ **Use IAM roles and managed identities** - Most secure approach for cloud providers; no credentials in the connection
✅ **Test connection with AI sample first** - Then customize for your environment

## Support

- **Issues**: [https://github.com/LeastAction-Labs/LeastAction-samples](https://github.com/LeastAction-Labs/LeastAction-samples)

