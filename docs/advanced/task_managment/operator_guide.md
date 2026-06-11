# LeastAction Operator Development Guide

## Table of Contents
1. [Overview](#overview)
2. [Operator vs Action](#operator-vs-action)
3. [Operator Structure](#operator-structure)
4. [The Four Methods](#the-four-methods)
5. [Understanding least_action_task_object](#understanding-least_action_task_object)
6. [Connection Object](#connection-object)
7. [Payload Structure](#payload-structure)
8. [Logging Requirements](#logging-requirements)
9. [Error Handling](#error-handling)
10. [Execution Patterns](#execution-patterns)
11. [Best Practices](#best-practices)
12. [Complete Example](#complete-example)
13. [Development Workflow](#development-workflow)

---

## Overview

**Operators** are advanced, multi-phase execution components in LeastAction designed for complex, asynchronous, or long-running operations. Unlike actions (which execute synchronously and return immediately), operators support asynchronous execution with status polling and completion checking.

### Key Characteristics:
- **Multi-Phase Execution**: Initialize, run, check completion, and cleanup
- **Asynchronous Support**: Can handle long-running operations with status polling
- **State Management**: Maintains execution state across phases
- **Resource Lifecycle**: Proper initialization and cleanup of resources
- **Status Tracking**: Monitors operation progress with pending/success/failed states

### Common Use Cases:
- Starting/stopping cloud resources (EC2 instances, databases)
- Running batch jobs or data processing pipelines
- Executing remote commands on servers
- Deploying applications with multiple steps
- Long-running computations or transformations
- Operations that require polling for completion

---

## Operator vs Action

Understanding when to use operators vs actions is crucial for proper implementation.

| Feature | Action | Operator |
|---------|--------|----------|
| **Execution Model** | Synchronous, immediate | Asynchronous with polling |
| **Methods** | `run()` only | `initialize()`, `run()`, `check_completion()`, `finish()` |
| **Return Type** | Boolean (True/False) | Dict with status/message/output |
| **Complexity** | Simple, single-step | Complex, multi-step |
| **Duration** | Quick (seconds) | Long-running (minutes to hours) |
| **State Management** | Stateless | Stateful across phases |
| **Use Cases** | Notifications, API calls | Resource management, batch jobs |

### When to Use an Operator:

✅ **Use Operator for:**
- Starting EC2 instances (takes time to boot)
- Running shell commands on remote servers
- Executing database migrations
- Processing large datasets
- Deploying applications
- Operations with unpredictable completion time
- Tasks requiring status polling

❌ **Use Action instead for:**
- Sending Slack/email notifications
- Simple API calls with immediate response
- Data validation/transformation
- File read/write operations
- Synchronous operations

---

## Operator Structure

Every operator must follow this structure:

```json
{
  "bashblock": {
    "main.sh": "pip install package1 package2"
  },
  "codeblock": {
    "main.py": "Python code with initialize, run, check_completion, finish methods"
  },
  "payload": {
    "field1": "value1",
    "field2": "value2"
  },
  "connection": {
    "credential_field": "value"
  },
  "item_type": "operator.AWSIAMRole"
}
```

### Components:

1. **bashblock**: Shell commands for installing dependencies
2. **codeblock**: Python code containing all 4 operator methods
3. **payload**: Operation-specific parameters and data
4. **connection**: Credentials and connection configuration
5. **item_type**: Must be "operator.{AuthType}" (e.g., "operator.AWSIAMRole")

### Key Differences from Actions:

- Uses **payload** instead of action_variables
- Has **4 methods** instead of 1
- **item_type** starts with "operator."
- Returns **dicts** instead of booleans

---

## The Four Methods

Operators implement four methods that execute in sequence:

```
┌─────────────┐     ┌─────────┐     ┌──────────────────┐     ┌────────┐
│ initialize  │ --> │   run   │ --> │ check_completion │ --> │ finish │
│             │     │         │     │  (polled until   │     │        │
│ Setup client│     │ Start   │     │   done)          │     │ Cleanup│
└─────────────┘     └─────────┘     └──────────────────┘     └────────┘
```

### 1. initialize()

**Purpose**: Set up connections, authenticate, and return a client object

```python
def initialize(least_action_task_object, least_action_parameters):
    """
    Initialize connections and return a client object.

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters

    Returns:
        any: Client/connection object (boto3 client, API client, etc.)
    """
```

**Responsibilities:**
- Extract credentials from connection
- Create and configure client/connection objects
- Verify connectivity (optional but recommended)
- Handle authentication errors
- Return initialized client for use in other methods

**Example:**
```python
def initialize(least_action_task_object, least_action_parameters):
    connection = least_action_task_object.get('connection', {})

    try:
        log_info(
            "task",
            "initialize",
            "creating_client",
            "Setting up AWS EC2 client"
        )

        if connection.get('aws_access_key_id'):
            client = boto3.client(
                'ec2',
                region_name=connection.get('region', 'us-east-1'),
                aws_access_key_id=connection['aws_access_key_id'],
                aws_secret_access_key=connection['aws_secret_access_key']
            )
        else:
            client = boto3.client('ec2',
                region_name=connection.get('region', 'us-east-1'))

        # Test connection
        client.describe_instances(MaxResults=5)
        log_info(
            "task",
            "initialize",
            "connection_verified",
            "Successfully connected to AWS EC2"
        )

        return client

    except Exception as e:
        log_error(
            "task",
            "initialize",
            "error",
            f"Failed to initialize: {str(e)}"
        )
        raise
```

---

### 2. run()

**Purpose**: Start the operation and return execution details

```python
def run(least_action_task_object, least_action_parameters, client):
    """
    Execute the operation and return details.

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters
        client (any): Client object returned from initialize()

    Returns:
        dict: Must contain 'execution_type' and operation details
            {
                'execution_type': 'async' or 'sync',
                'operation_id': 'unique-operation-identifier',
                # ... other operation-specific fields
            }
    """
```

**Responsibilities:**
- Parse payload from least_action_task_object
- Validate input parameters
- Start the operation using the client
- Return execution details needed by checkCompletion()

**Required Return Fields:**
- `execution_type`: **REQUIRED** - Must be 'async' or 'sync'
- Additional fields: Operation identifiers, resource IDs, etc.

**Example:**
```python
def run(least_action_task_object, least_action_parameters, client):
    payload = least_action_task_object.get('payload', '{}')

    try:
        log_info(
            "task",
            "run",
            "parsing_payload",
            "Parsing payload for instance details"
        )

        # Parse payload
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        instance_ids = payload_data.get('instance_ids', [])

        log_info(
            "task",
            "run",
            "starting_instances",
            f"Starting instances: {instance_ids}"
        )

        # Start the operation
        response = client.start_instances(InstanceIds=instance_ids)

        log_info(
            "task",
            "run",
            "instances_started",
            f"Start command sent for {len(instance_ids)} instances"
        )

        return {
            'execution_type': 'async',
            'instance_ids': instance_ids,
            'response': response
        }

    except Exception as e:
        log_error(
            "task",
            "run",
            "error",
            f"Error during execution: {str(e)}"
        )
        raise
```

---

### 3. check_completion()

**Purpose**: Check if the operation has completed and return status

```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    """
    Check operation completion status.

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters
        client (any): Client object from initialize()
        run_details (dict): Dict returned from run() method

    Returns:
        dict: MUST contain 'status', 'message', and 'output'
            {
                'status': 'success' | 'failed' | 'pending',
                'message': 'Human-readable status message',
                'output': {
                    # Result data or error details
                }
            }
    """
```

**Responsibilities:**
- Query operation status using run_details
- Determine if operation is complete, failed, or still pending
- Return structured status information

**Required Return Fields:**
- `status`: **REQUIRED** - Must be 'success', 'failed', or 'pending'
- `message`: **REQUIRED** - Human-readable description
- `output`: **REQUIRED** - Dict with result data or error details

**Status Values:**
- `'success'`: Operation completed successfully
- `'failed'`: Operation failed (will not retry)
- `'pending'`: Operation still in progress (will poll again)

**Example:**
```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    try:
        instance_ids = run_details.get('instance_ids', [])

        log_info(
            "task",
            "check_completion",
            "checking_status",
            f"Checking status of instances: {instance_ids}"
        )

        # Query current state
        response = client.describe_instances(InstanceIds=instance_ids)

        instance_states = {}
        all_running = True
        any_failed = False

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                instance_states[instance_id] = state

                if state != 'running':
                    all_running = False
                if state in ['terminated', 'stopping', 'stopped']:
                    any_failed = True

        log_info(
            "task",
            "check_completion",
            "status_checked",
            f"Instance states: {instance_states}"
        )

        if any_failed:
            return {
                'status': 'failed',
                'message': f'One or more instances failed to start',
                'output': {'instance_states': instance_states}
            }
        elif all_running:
            return {
                'status': 'success',
                'message': f'All instances are now running',
                'output': {'instance_states': instance_states}
            }
        else:
            return {
                'status': 'pending',
                'message': f'Instances still starting',
                'output': {'instance_states': instance_states}
            }

    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "error",
            f"Error checking completion: {str(e)}"
        )
        return {
            'status': 'failed',
            'message': f'Error checking completion: {str(e)}',
            'output': {}
        }
```

---

### 4. finish()

**Purpose**: Clean up resources and close connections

```python
def finish(least_action_task_object, client, completion_details, run_details):
    """
    Clean up resources after operation completes.

    Parameters:
        least_action_task_object (dict): Task context object
        client (any): Client object from initialize()
        completion_details (dict): Final dict from checkCompletion()
        run_details (dict): Dict from run() method

    Returns:
        None
    """
```

**Responsibilities:**
- Close connections
- Release resources
- Log final status
- Handle cleanup errors gracefully

**Note**: The finish method receives the final result from `check_completion()` as the `completion_details` parameter.

**Example:**
```python
def finish(least_action_task_object, client, completion_details, run_details):
    try:
        log_info(
            "task",
            "finish",
            "cleaning_up",
            "Cleaning up AWS EC2 client resources"
        )

        if completion_details.get('status') == 'success':
            log_info(
                "task",
                "finish",
                "task_completed",
                "EC2 instance start operation completed successfully"
            )
        else:
            log_info(
                "task",
                "finish",
                "task_failed",
                f"EC2 instance start operation failed: {completion_details.get('message')}"
            )

        # Cleanup resources if needed
        # For boto3 clients, no explicit cleanup needed

        log_info(
            "task",
            "finish",
            "cleanup_complete",
            "Resource cleanup completed"
        )

    except Exception as e:
        log_error(
            "task",
            "finish",
            "cleanup_error",
            f"Error during cleanup: {str(e)}"
        )
```

---

## Understanding least_action_task_object

The `least_action_task_object` is a dictionary containing all context and metadata for the operator execution.

### Structure:

```python
least_action_task_object = {
    "laui": "task-unique-identifier",             # Same as _id (string)
    "session_id": "session-unique-identifier",    # Session ID (string)
    "connection": {                               # Connection credentials (dict)
        "region": "us-east-1",
        "aws_access_key_id": "...",
        # ... other connection fields
    },
    "payload": {                                  # Task payload data (dict or JSON string)
        "instance_ids": ["i-123", "i-456"],
        "operation": "start",
        # ... operation-specific fields
    },
    "connection_laui": "connection-identifier"    # Connection identifier (string)
}
```

### Fields Explained:

| Field | Type | Description |
|-------|------|-------------|
| `laui` | string | Unique identifier for this task instance |
| `session_id` | string | Identifier for the current workflow session |
| `connection` | dict | Contains credentials and connection configuration |
| `payload` | dict/string | Operation-specific parameters (may be JSON string) |
| `connection_laui` | string | Identifier for the connection configuration |

### Accessing Fields:

Always use `.get()` method for safe access:

```python
# Safe access with default fallback
task_id = least_action_task_object.get('laui')
session_id = least_action_task_object.get('session_id')
connection = least_action_task_object.get('connection', {})
payload = least_action_task_object.get('payload', '{}')

# Parse payload (it can be string or dict)
import json
if isinstance(payload, str):
    payload_data = json.loads(payload)
else:
    payload_data = payload

# Access payload fields
instance_ids = payload_data.get('instance_ids', [])
```

### Key Differences from Actions:

| Actions | Operators |
|---------|-----------|
| `least_action_action_object` | `least_action_task_object` |
| `action_variables` field | `payload` field |
| `laui` for action ID | `laui` for task ID |
| Direct parameter passing | Payload parsing required |

---

## Connection Object

The connection object works the same way in operators as in actions.

### Structure Examples:

**AWS Services:**
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "aws_session_token": ""
}
```

**Database:**
```json
{
  "host": "db.example.com",
  "port": 5432,
  "database": "mydb",
  "username": "dbuser",
  "password": "dbpassword"
}
```

### Usage in initialize():

The connection object is extracted in the `initialize()` method to create the client.



```python
def initialize(least_action_task_object, least_action_parameters):
    connection = least_action_task_object.get('connection', {})

    # Get credentials
    region = connection.get('region', 'us-east-1')
    aws_access_key_id = connection.get('aws_access_key_id')
    aws_secret_access_key = connection.get('aws_secret_access_key')

    # Create client with credentials if provided
    if aws_access_key_id and aws_secret_access_key:
        client = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    else:
        # Use IAM role or environment credentials
        client = boto3.client('ec2', region_name=region)

    return client
```

---

## Payload Structure

The payload contains operation-specific parameters and data. It can be a JSON string or a dict.

### Common Payload Patterns:

**1. Resource Operations (EC2, RDS, etc.):**
```json
{
  "instance_ids": ["i-123456", "i-789012"],
  "operation": "start"
}
```

**2. Shell Commands:**
```json
{
  "instance_ids": ["i-123456"],
  "commands": [
    "#!/bin/bash",
    "echo 'Running system check'",
    "uptime",
    "df -h"
  ],
  "timeout_seconds": 600,
  "working_directory": "/tmp"
}
```

**3. Lambda Invocation:**
```json
{
  "function_name": "my-lambda-function",
  "invoke_payload": {
    "key1": "value1",
    "key2": "value2"
  },
  "invocation_type": "RequestResponse"
}
```

**4. Batch Operations:**
```json
{
  "resources": [
    {
      "id": "resource-1",
      "type": "instance",
      "action": "stop"
    },
    {
      "id": "resource-2",
      "type": "instance",
      "action": "stop"
    }
  ],
  "concurrent": true
}
```

### Parsing Payload:

Always parse payload in the `run()` method:

```python
def run(least_action_task_object, least_action_parameters, client):
    payload = least_action_task_object.get('payload', '{}')

    try:
        # Parse payload (can be string or dict)
        import json
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        # Extract fields with defaults
        instance_ids = payload_data.get('instance_ids', [])
        timeout = payload_data.get('timeout_seconds', 3600)

        # Validate required fields
        if not instance_ids:
            raise ValueError("No instance IDs provided in payload")

        # Use payload data...

    except json.JSONDecodeError as e:
        log_error("task", task_id, "run", "payload_parse_error",
                 f"Failed to parse payload: {str(e)}", session_id)
        raise
```

---

## Logging Requirements

Operators use a slightly different logging format than actions.

### Import Statement:

```python
from src.common.logger.logger import log_info, log_error

```

### Logging Functions:

> **⚠️ IMPORTANT**: The logging signature has only **4 parameters** - no task_id or session_id parameters!

**1. log_info** - For successful operations and progress:
```python
log_info(type, function, step, description)
```

**2. log_error** - For errors and exceptions:
```python
log_error(type, function, step, description)
```

### Parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `type` | `"task"` | Always "task" for operator logging |
| `function` | function name | "initialize", "run", "check_completion", "finish" |
| `step` | step name | Descriptive step identifier (lowercase, underscored) |
| `description` | message | Detailed message about what's happening (can include task/session IDs in the message string) |

**Example**:
```python
# Correct - 4 parameters
log_info(
    "task",
    "initialize",
    "creating_client",
    f"Setting up AWS EC2 client for task: {least_action_task_object.get('laui')}"
)

# Wrong - DO NOT pass task_id and session_id as separate parameters!
log_info("task", task_id, "initialize", "creating_client", "Setting up client", session_id)  # ❌
```

### Logging Pattern:

```python
def run(least_action_task_object, least_action_parameters, client):
    # Extract task ID for logging context (optional, can include in message)
    task_id = least_action_task_object.get('laui')

    try:
        log_info(
            "task",
            "run",
            "start",
            f"Starting operation for task: {task_id}"
        )

        log_info(
            "task",
            "run",
            "parsing_payload",
            "Parsing payload for operation"
        )

        # ... operation logic ...

        log_info(
            "task",
            "run",
            "operation_started",
            f"Operation started successfully for task: {task_id}"
        )

        return {...}

    except Exception as e:
        log_error(
            "task",
            "run",
            "error",
            f"Error during operation: {str(e)}"
        )
        raise
```

### Step Naming Convention:

Use lowercase, descriptive names with underscores:

✅ Good:
- `"creating_client"`
- `"parsing_payload"`
- `"starting_instances"`
- `"checking_status"`
- `"cleanup_complete"`

❌ Bad:
- `"Step1"` (not descriptive)
- `"StartingInstances"` (camelCase)
- `"INIT"` (uppercase)

### Required Log Points:

**initialize():**
```python
log_info("task", "initialize", "creating_client", "Setting up AWS EC2 client")
log_info("task", "initialize", "connection_verified", "Successfully connected to AWS EC2")
```

**run():**
```python
log_info("task", "run", "parsing_payload", "Parsing payload for instance details")
log_info("task", "run", "operation_started", f"Operation started for {len(instance_ids)} instances")
```

**check_completion():**
```python
log_info("task", "check_completion", "checking_status", f"Checking status of instances: {instance_ids}")
log_info("task", "check_completion", "status_checked", f"Instance states: {instance_states}")
```

**finish():**
```python
log_info("task", "finish", "cleaning_up", "Cleaning up AWS EC2 client resources")
log_info("task", "finish", "cleanup_complete", "Resource cleanup completed")
```

---

## Error Handling

Robust error handling is critical for operators due to their complexity.

### Exception Handling Strategy:

**initialize() - Raise exceptions:**
```python
def initialize(least_action_task_object, least_action_parameters):
    try:
        # Setup logic
        return client
    except ClientError as e:
        log_error(
            "task",
            "initialize",
            "aws_error",
            f"AWS error: {str(e)}"
        )
        raise  # Re-raise to fail fast
    except Exception as e:
        log_error(
            "task",
            "initialize",
            "error",
            f"Initialization failed: {str(e)}"
        )
        raise
```

**run() - Raise exceptions:**
```python
def run(least_action_task_object, least_action_parameters, client):
    try:
        # Operation logic
        return {...}
    except json.JSONDecodeError as e:
        log_error(
            "task",
            "run",
            "payload_parse_error",
            f"Invalid payload: {str(e)}"
        )
        raise
    except ClientError as e:
        log_error(
            "task",
            "run",
            "aws_error",
            f"AWS error: {str(e)}"
        )
        raise
    except Exception as e:
        log_error(
            "task",
            "run",
            "error",
            f"Execution failed: {str(e)}"
        )
        raise
```

**check_completion() - Return failed status:**
```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    try:
        # Check status logic
        return {'status': 'success', 'message': '...', 'output': {...}}
    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "error",
                 f"Error checking status: {str(e)}", session_id)
        # Don't raise - return failed status
        return {
            'status': 'failed',
            'message': f'Error checking completion: {str(e)}',
            'output': {}
        }
```

**finish() - Log but don't raise:**
```python
def finish(least_action_task_object, client, completion_details, run_details):
    try:
        # Cleanup logic
        pass
    except Exception as e:
        log_error(
            "task",
            "finish",
            "cleanup_error",
            f"Cleanup error: {str(e)}"
        )
        # Don't raise - log and continue
```

### Error Handling Rules:

| Method | On Error | Reason |
|--------|----------|--------|
| `initialize()` | **Raise** | Fail fast if can't connect |
| `run()` | **Raise** | Fail fast if can't start operation |
| `check_completion()` | **Return failed status** | Allow graceful failure reporting |
| `finish()` | **Log only** | Ensure cleanup always completes |

---

## Execution Patterns

### Synchronous Execution

For operations that complete immediately:

```python
def run(least_action_task_object, least_action_parameters, client):
    # Perform operation
    result = client.invoke_function(...)

    return {
        'execution_type': 'sync',  # Synchronous
        'result': result
    }

def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    # For sync operations, immediately return success
    if run_details.get('execution_type') == 'sync':
        return {
            'status': 'success',
            'message': 'Synchronous operation completed',
            'output': run_details.get('result', {})
        }
```

### Asynchronous Execution

For long-running operations:

```python
def run(least_action_task_object, least_action_parameters, client):
    # Start operation
    response = client.start_operation(...)
    operation_id = response['OperationId']

    return {
        'execution_type': 'async',  # Asynchronous
        'operation_id': operation_id
    }

def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    operation_id = run_details.get('operation_id')

    # Query status
    status = client.get_operation_status(operation_id)

    if status == 'COMPLETED':
        return {
            'status': 'success',
            'message': 'Operation completed',
            'output': {'operation_id': operation_id}
        }
    elif status == 'FAILED':
        return {
            'status': 'failed',
            'message': 'Operation failed',
            'output': {'operation_id': operation_id}
        }
    else:
        return {
            'status': 'pending',
            'message': f'Operation in progress: {status}',
            'output': {'operation_id': operation_id}
        }
```

### Batch Operations

For operations on multiple resources:

```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    instance_ids = run_details.get('instance_ids', [])

    # Check status of all instances
    statuses = {}
    for instance_id in instance_ids:
        status = client.get_instance_status(instance_id)
        statuses[instance_id] = status

    # Determine overall status
    all_complete = all(s == 'running' for s in statuses.values())
    any_failed = any(s == 'failed' for s in statuses.values())

    if any_failed:
        return {
            'status': 'failed',
            'message': 'One or more instances failed',
            'output': {'instance_statuses': statuses}
        }
    elif all_complete:
        return {
            'status': 'success',
            'message': 'All instances running',
            'output': {'instance_statuses': statuses}
        }
    else:
        return {
            'status': 'pending',
            'message': 'Some instances still starting',
            'output': {'instance_statuses': statuses}
        }
```

---

## Best Practices

### 1. Client Reuse

The client returned from `initialize()` is passed to all subsequent methods:

```python
def initialize(least_action_task_object, least_action_parameters):
    client = boto3.client('ec2', ...)
    return client  # This client is reused

def run(least_action_task_object, least_action_parameters, client):
    # Use the same client instance
    client.start_instances(...)

def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    # Use the same client instance
    client.describe_instances(...)
```

### 2. Validate Payload Early

```python
def run(least_action_task_object, least_action_parameters, client):
    payload = least_action_task_object.get('payload', '{}')

    if isinstance(payload, str):
        payload_data = json.loads(payload)
    else:
        payload_data = payload

    # Validate required fields
    instance_ids = payload_data.get('instance_ids')
    if not instance_ids:
        raise ValueError("instance_ids is required in payload")

    if not isinstance(instance_ids, list):
        raise ValueError("instance_ids must be a list")
```

### 3. Store Necessary Data in run_details

Return everything `check_completion()` needs:

```python
def run(least_action_task_object, least_action_parameters, client):
    response = client.send_command(...)

    return {
        'execution_type': 'async',
        'command_id': response['Command']['CommandId'],  # Needed for status check
        'instance_ids': instance_ids,                     # Needed for status check
        'document_name': response['Command']['DocumentName'],
        'requested_at': str(response['Command']['RequestedDateTime'])
    }

def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    # Use data from run_details
    command_id = run_details.get('command_id')
    instance_ids = run_details.get('instance_ids', [])

    # Check status using this data
    status = client.get_command_status(command_id, instance_ids)
    # ...
```

### 4. Handle Partial Failures

For batch operations, report partial success:

```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    instance_ids = run_details.get('instance_ids', [])

    success_count = 0
    failed_count = 0
    pending_count = 0

    for instance_id in instance_ids:
        status = get_status(instance_id)
        if status == 'success':
            success_count += 1
        elif status == 'failed':
            failed_count += 1
        else:
            pending_count += 1

    if pending_count > 0:
        return {
            'status': 'pending',
            'message': f'{success_count} succeeded, {failed_count} failed, {pending_count} pending',
            'output': {...}
        }
    elif failed_count > 0 and success_count > 0:
        # Partial success - decide whether to report success or failure
        return {
            'status': 'success',  # or 'failed' depending on requirements
            'message': f'{success_count} succeeded, {failed_count} failed',
            'output': {...}
        }
    elif failed_count > 0:
        return {
            'status': 'failed',
            'message': f'All {failed_count} instances failed',
            'output': {...}
        }
    else:
        return {
            'status': 'success',
            'message': f'All {success_count} instances succeeded',
            'output': {...}
        }
```

### 5. Test Connection in initialize()

```python
def initialize(least_action_task_object, least_action_parameters):
    client = boto3.client('ec2', ...)

    # Test connection with a minimal operation
    try:
        client.describe_instances(MaxResults=1)
        log_info("task", task_id, "initialize", "connection_verified",
                "Connection verified", session_id)
    except Exception as e:
        log_error("task", task_id, "initialize", "connection_failed",
                 f"Connection test failed: {str(e)}", session_id)
        raise

    return client
```

### 6. Provide Detailed Output

```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    # Gather detailed results
    outputs = []
    for invocation in invocations:
        outputs.append({
            'instance_id': invocation['InstanceId'],
            'status': invocation['Status'],
            'stdout': invocation.get('StandardOutputContent', ''),
            'stderr': invocation.get('StandardErrorContent', ''),
            'exit_code': invocation.get('ResponseCode', -1)
        })

    return {
        'status': 'success',
        'message': 'Commands executed successfully',
        'output': {
            'command_id': command_id,
            'execution_details': outputs
        }
    }
```

### 7. Use Type Conversion

```python
# Ensure lists
if isinstance(instance_ids, str):
    instance_ids = [instance_ids]

# Ensure strings
timeout = str(timeout_seconds)

# Parse JSON safely
try:
    if isinstance(payload, str):
        payload_data = json.loads(payload)
    else:
        payload_data = payload
except json.JSONDecodeError:
    payload_data = {}
```

### 8. Logging Consistency

```python
# Keep logging calls concise and consistent
log_info("task", "run", "step_name", "Clear description of what's happening")
log_error("task", "run", "error_type", f"Error message: {str(e)}")

# Include context in the message when needed
task_id = least_action_task_object.get('laui')
log_info("task", "run", "start", f"Starting operation for task: {task_id}")
```

---

## Complete Example

Here's a complete, production-ready operator for starting EC2 instances:

### JSON Structure:

```json
{
  "bashblock": {
    "main.sh": "pip install boto3"
  },
  "codeblock": {
    "main.py": "[See Python code below]"
  },
  "payload": {
    "instance_ids": ["i-123456789abcdef0"]
  },
  "connection": {
    "region": "us-east-1",
    "aws_access_key_id": "",
    "aws_secret_access_key": ""
  },
  "item_type": "operator.AWSIAMRole"
}
```

### Python Code (main.py):

```python
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError
from src.common.logger.logger import log_info, log_error


def initialize(least_action_task_object, least_action_parameters):
    """
    Initialize AWS EC2 client for instance operations.

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters

    Returns:
        boto3.client: EC2 client for instance operations
    """
    connection = least_action_task_object.get('connection', {})

    try:
        log_info(
            "task",
            "initialize",
            "creating_client",
            "Setting up AWS EC2 client"
        )

        # Check if credentials are provided in connection
        if connection.get('aws_access_key_id') and connection.get('aws_secret_access_key'):
            client = boto3.client(
                'ec2',
                region_name=connection.get('region', 'us-east-1'),
                aws_access_key_id=connection['aws_access_key_id'],
                aws_secret_access_key=connection['aws_secret_access_key']
            )
            log_info(
                "task",
                "initialize",
                "client_created",
                "EC2 client created with provided credentials"
            )
        else:
            # Use default credentials (IAM role, AWS CLI config, environment variables)
            client = boto3.client(
                'ec2',
                region_name=connection.get('region', 'us-east-1')
            )
            log_info(
                "task",
                "initialize",
                "client_created",
                "EC2 client created with default credentials"
            )

        # Test connection
        client.describe_instances(MaxResults=5)
        log_info(
            "task",
            "initialize",
            "connection_verified",
            "Successfully connected to AWS EC2"
        )

        return client

    except NoCredentialsError as e:
        log_error(
            "task",
            "initialize",
            "credentials_error",
            f"AWS credentials not found: {str(e)}"
        )
        raise
    except ClientError as e:
        log_error(
            "task",
            "initialize",
            "client_error",
            f"AWS client error: {str(e)}"
        )
        raise
    except Exception as e:
        log_error(
            "task",
            "initialize",
            "unexpected_error",
            f"Unexpected error during initialization: {str(e)}"
        )
        raise


def run(least_action_task_object, least_action_parameters, client):
    """
    Start EC2 instance(s).

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters
        client (boto3.client): EC2 client from initialize()

    Returns:
        dict: Execution details including instance IDs and response
    """
    payload = least_action_task_object.get('payload', '{}')

    try:
        log_info(
            "task",
            "run",
            "parsing_payload",
            "Parsing payload for instance details"
        )

        # Parse payload
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        instance_ids = payload_data.get('instance_ids', [])
        if not instance_ids:
            raise ValueError("No instance IDs provided in payload")

        log_info(
            "task",
            "run",
            "starting_instances",
            f"Starting instances: {instance_ids}"
        )

        # Start the instances
        response = client.start_instances(InstanceIds=instance_ids)

        starting_instances = response.get('StartingInstances', [])

        log_info(
            "task",
            "run",
            "instances_started",
            f"Start command sent for {len(starting_instances)} instances"
        )

        return {
            'execution_type': 'async',
            'instance_ids': instance_ids,
            'starting_instances': starting_instances,
            'response': response
        }

    except json.JSONDecodeError as e:
        log_error(
            "task",
            "run",
            "payload_parse_error",
            f"Failed to parse payload JSON: {str(e)}"
        )
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        log_error(
            "task",
            "run",
            "aws_error",
            f"AWS error ({error_code}): {str(e)}"
        )
        raise
    except Exception as e:
        log_error(
            "task",
            "run",
            "execution_error",
            f"Error during instance start: {str(e)}"
        )
        raise


def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    """
    Check if EC2 instances have successfully started.

    Parameters:
        least_action_task_object (dict): Task context object
        least_action_parameters (dict): Additional parameters
        client (boto3.client): EC2 client from initialize()
        run_details (dict): Details from run() method

    Returns:
        dict: Status information (status, message, output)
    """
    try:
        instance_ids = run_details.get('instance_ids', [])

        log_info(
            "task",
            "check_completion",
            "checking_status",
            f"Checking status of instances: {instance_ids}"
        )

        # Describe instances to get current state
        response = client.describe_instances(InstanceIds=instance_ids)

        instance_states = {}
        all_running = True
        any_failed = False

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                instance_states[instance_id] = state

                if state not in ['running']:
                    all_running = False
                if state in ['terminated', 'stopping', 'stopped']:
                    any_failed = True

        log_info(
            "task",
            "check_completion",
            "status_checked",
            f"Instance states: {instance_states}"
        )

        if any_failed:
            return {
                'status': 'failed',
                'message': f'One or more instances failed to start: {instance_states}',
                'output': {'instance_states': instance_states}
            }
        elif all_running:
            return {
                'status': 'success',
                'message': f'All instances are now running: {instance_states}',
                'output': {'instance_states': instance_states}
            }
        else:
            return {
                'status': 'pending',
                'message': f'Instances still starting: {instance_states}',
                'output': {'instance_states': instance_states}
            }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        log_error(
            "task",
            "check_completion",
            "aws_error",
            f"AWS error ({error_code}): {str(e)}"
        )
        return {
            'status': 'failed',
            'message': f'AWS error while checking completion: {str(e)}',
            'output': {}
        }
    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "check_error",
            f"Error checking completion: {str(e)}"
        )
        return {
            'status': 'failed',
            'message': f'Error checking completion: {str(e)}',
            'output': {}
        }


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Cleanup resources and close connections.

    Parameters:
        least_action_task_object (dict): Task context object
        client (boto3.client): EC2 client from initialize()
        completion_details (dict): Final status from check_completion()
        run_details (dict): Details from run() method

    Returns:
        None
    """
    try:
        log_info(
            "task",
            "finish",
            "cleaning_up",
            "Cleaning up AWS EC2 client resources"
        )

        # Boto3 clients don't need explicit cleanup, but we can log the completion
        if completion_details.get('status') == 'success':
            log_info(
                "task",
                "finish",
                "task_completed",
                "EC2 instance start operation completed successfully"
            )
        else:
            log_info(
                "task",
                "finish",
                "task_failed",
                f"EC2 instance start operation failed: {completion_details.get('message')}"
            )

        log_info(
            "task",
            "finish",
            "cleanup_complete",
            "Resource cleanup completed"
        )

    except Exception as e:
        log_error(
            "task",
            "finish",
            "cleanup_error",
            f"Error during cleanup: {str(e)}"
        )
```

---

## Development Workflow

Follow this process to develop a new operator:

### Step 1: Understand Requirements

**Questions to Answer:**
- What operation needs to be performed?
- Is it synchronous or asynchronous?
- What external service/API is involved?
- What inputs are needed in the payload?
- What credentials are required?
- How do we check completion status?

**Example:**
- Operator: Start EC2 instances
- Type: Asynchronous
- Service: AWS EC2
- Payload: instance_ids
- Credentials: AWS access key, secret key, region
- Completion: Check instance state until "running"

### Step 2: Design the Operator

**Define:**

1. **Payload** (operation parameters):
```json
{
  "instance_ids": ["i-123456789abcdef0"]
}
```

2. **Connection** (credentials):
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

3. **Dependencies**:
```bash
pip install boto3
```

### Step 3: Implement initialize()

Create and test the client connection:

```python
def initialize(least_action_task_object, least_action_parameters):
    task_id = least_action_task_object.get('laui')
    session_id = least_action_task_object.get('session_id')
    connection = least_action_task_object.get('connection', {})

    try:
        log_info("task", task_id, "initialize", "creating_client",
                "Setting up client", session_id)

        client = create_client(connection)

        # Test connection
        test_connection(client)

        log_info("task", task_id, "initialize", "connection_verified",
                "Connection verified", session_id)

        return client
    except Exception as e:
        log_error("task", task_id, "initialize", "error",
                 f"Initialization failed: {str(e)}", session_id)
        raise
```

### Step 4: Implement run()

Start the operation and return details:

```python
def run(least_action_task_object, least_action_parameters, client):
    task_id = least_action_task_object.get('laui')
    session_id = least_action_task_object.get('session_id')
    payload = least_action_task_object.get('payload', '{}')

    try:
        log_info("task", task_id, "run", "parsing_payload",
                "Parsing payload", session_id)

        # Parse payload
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        # Extract and validate parameters
        param = payload_data.get('param')
        if not param:
            raise ValueError("Missing required parameter")

        log_info("task", task_id, "run", "starting_operation",
                f"Starting operation with {param}", session_id)

        # Start operation
        response = client.start_operation(param)
        operation_id = response['OperationId']

        log_info("task", task_id, "run", "operation_started",
                f"Operation started: {operation_id}", session_id)

        return {
            'execution_type': 'async',  # or 'sync'
            'operation_id': operation_id,
            'param': param
        }
    except Exception as e:
        log_error("task", task_id, "run", "error",
                 f"Execution failed: {str(e)}", session_id)
        raise
```

### Step 5: Implement check_completion()

Check operation status and return structured result:

```python
def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    task_id = least_action_task_object.get('laui')
    session_id = least_action_task_object.get('session_id')

    try:
        operation_id = run_details.get('operation_id')

        log_info(
            "task",
            "check_completion",
            "checking_status",
                f"Checking status of operation {operation_id}", session_id)

        # Query status
        status = client.get_operation_status(operation_id)

        log_info(
            "task",
            "check_completion",
            "status_checked",
                f"Operation status: {status}", session_id)

        # Determine completion state
        if status == 'COMPLETED':
            return {
                'status': 'success',
                'message': 'Operation completed successfully',
                'output': {'operation_id': operation_id}
            }
        elif status == 'FAILED':
            return {
                'status': 'failed',
                'message': 'Operation failed',
                'output': {'operation_id': operation_id}
            }
        else:
            return {
                'status': 'pending',
                'message': f'Operation in progress: {status}',
                'output': {'operation_id': operation_id}
            }
    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "error",
                 f"Error checking completion: {str(e)}", session_id)
        return {
            'status': 'failed',
            'message': f'Error: {str(e)}',
            'output': {}
        }
```

### Step 6: Implement finish()

Clean up resources:

```python
def finish(least_action_task_object, client, completion_details, run_details):
    task_id = least_action_task_object.get('laui')
    session_id = least_action_task_object.get('session_id')

    try:
        log_info("task", task_id, "finish", "cleaning_up",
                "Cleaning up resources", session_id)

        # Close connections, release resources
        # For many clients, no explicit cleanup needed

        if completion_details.get('status') == 'success':
            log_info("task", task_id, "finish", "task_completed",
                    "Operation completed successfully", session_id)
        else:
            log_info("task", task_id, "finish", "task_failed",
                    f"Operation failed: {completion_details.get('message')}",
                    session_id)

        log_info("task", task_id, "finish", "cleanup_complete",
                "Cleanup completed", session_id)
    except Exception as e:
        log_error("task", task_id, "finish", "cleanup_error",
                 f"Cleanup error: {str(e)}", session_id)
```

### Step 7: Create JSON Structure

Assemble the complete operator JSON:

```json
{
  "bashblock": {
    "main.sh": "pip install boto3"
  },
  "codeblock": {
    "main.py": "[Complete Python code with all 4 methods]"
  },
  "payload": {
    "instance_ids": ["i-123456789abcdef0"]
  },
  "connection": {
    "region": "us-east-1",
    "aws_access_key_id": "",
    "aws_secret_access_key": ""
  },
  "item_type": "operator.AWSIAMRole"
}
```

### Step 8: Review Checklist

Before finalizing, verify:

- [ ] All 4 methods implemented: initialize, run, check_completion, finish
- [ ] initialize() returns a client object
- [ ] run() returns dict with 'execution_type'
- [ ] check_completion() returns dict with 'status', 'message', 'output'
- [ ] finish() performs cleanup (no return value)
- [ ] Payload is parsed correctly (handle string and dict)
- [ ] Connection object contains all necessary credentials
- [ ] Dependencies listed in bashblock
- [ ] Comprehensive logging in all methods (start, progress, completion, errors)
- [ ] Error handling: raise in initialize/run, return failed in check_completion, log in finish
- [ ] No credentials logged
- [ ] Timeout on network operations
- [ ] Status values are 'success', 'failed', or 'pending'
- [ ] item_type starts with "operator."

---

## Quick Reference Card

### Operator Template

```python
import [libraries]
import json
from src.common.logger.logger import log_info, log_error


def initialize(least_action_task_object, least_action_parameters):
    connection = least_action_task_object.get('connection', {})

    try:
        log_info("task", "initialize", "creating_client", "Setting up client")
        client = create_client(connection)
        log_info("task", "initialize", "connection_verified", "Successfully connected")
        return client
    except Exception as e:
        log_error("task", "initialize", "error", f"Initialization failed: {str(e)}")
        raise


def run(least_action_task_object, least_action_parameters, client):
    payload = least_action_task_object.get('payload', '{}')

    try:
        log_info("task", "run", "parsing_payload", "Parsing payload")

        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        # Start operation
        result = client.start_operation(...)

        log_info("task", "run", "operation_started", "Operation started successfully")

        return {
            'execution_type': 'async',  # or 'sync'
            # ... operation details
        }
    except Exception as e:
        log_error("task", "run", "error", f"Execution failed: {str(e)}")
        raise


def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    try:
        log_info("task", "check_completion", "checking_status", "Checking operation status")

        # Check status
        status = get_status(run_details)

        if status == 'completed':
            return {
                'status': 'success',
                'message': 'Operation completed',
                'output': {}
            }
        elif status == 'failed':
            return {
                'status': 'failed',
                'message': 'Operation failed',
                'output': {}
            }
        else:
            return {
                'status': 'pending',
                'message': 'Operation in progress',
                'output': {}
            }
    except Exception as e:
        log_error("task", "check_completion", "error", f"Error checking status: {str(e)}")
        return {
            'status': 'failed',
            'message': str(e),
            'output': {}
        }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        log_info("task", "finish", "cleaning_up", "Cleaning up resources")
        # Cleanup
        log_info("task", "finish", "cleanup_complete", "Cleanup completed successfully")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during cleanup: {str(e)}")
```

### JSON Template

```json
{
  "bashblock": {
    "main.sh": "pip install package"
  },
  "codeblock": {
    "main.py": "[Python code with 4 methods]"
  },
  "payload": {
    "param1": "value1"
  },
  "connection": {
    "credential_field": "value"
  },
  "item_type": "operator.AuthType"
}
```

### Common Patterns

**Parse Payload:**
```python
payload = least_action_task_object.get('payload', '{}')
if isinstance(payload, str):
    payload_data = json.loads(payload)
else:
    payload_data = payload
```

**Log Pattern:**
```python
log_info("task", "function_name", "step_name", "Clear description")
log_error("task", "function_name", "error_type", f"Error: {str(e)}")
```

**Return from check_completion:**
```python
return {
    'status': 'success' | 'failed' | 'pending',
    'message': 'Description',
    'output': {}
}
```

---

## Additional Resources

### LeastAction Documentation
- **Operator Examples**: `bootstrap/operators/` directory
- **Logging Framework**: `src.common.logger.logger`
- **Action vs Operator**: See ACTION_DEVELOPMENT_GUIDE.md

### External References
- **AWS Boto3**: [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- **Python Best Practices**: [PEP 8 Style Guide](https://pep8.org/)
- **Error Handling**: [Python Exception Handling](https://docs.python.org/3/tutorial/errors.html)

---

This guide provides everything you need to develop production-ready operators for LeastAction. Follow the structure, method signatures, and best practices to create reliable, maintainable operators that handle complex, asynchronous operations effectively.

Happy coding!
