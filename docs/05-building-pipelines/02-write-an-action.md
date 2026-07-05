# LeastAction Action Development Guide

## Table of Contents
1. [Overview](#overview)
2. [Action Structure](#action-structure)
3. [The Run Method](#the-run-method)
4. [Understanding least_action_action_object](#understanding-least_action_action_object)
5. [Connection Object](#connection-object)
6. [Action Variables](#action-variables)
7. [Return Values](#return-values)
8. [Logging Requirements](#logging-requirements)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)
11. [Complete Example](#complete-example)
12. [Development Workflow](#development-workflow)

---

## Overview

**Actions** are the fundamental building blocks of LeastAction workflows. An action is a self-contained Python function that performs a specific task, such as sending a notification, interacting with cloud services, processing data, or executing business logic.

### Key Characteristics:
- **Single Responsibility**: Each action should perform one specific task
- **Reusable**: Actions can be invoked in multiple workflows
- **Configurable**: Actions accept parameters through action_variables
- **Observable**: Comprehensive logging for debugging and monitoring
- **Reliable**: Robust error handling and clear success/failure indication

---

## Action Structure

Every action must follow this structure:

```json
{
  "bashblock": {
    "main.sh": "pip install package1 package2",
  },
  "codeblock": {
    "main.py": "Python code with run method",
  },
  "action_variables": {
    "param1": "value1",
    "param2": "value2",
  },
  "connection": {
    "credential_field": "value",
  },
}
```

### Components:

1. **bashblock**: Shell commands for installing dependencies
2. **codeblock**: Python code containing the `run` method
3. **action_variables**: User-configurable parameters for the action
4. **connection**: Credentials and connection configuration

---

## The Run Method

The `run` method is the entry point for every action. It is invoked by the LeastAction platform.

### Signature:

```python
def run(least_action_action_object, param1, param2, ...):
    """
    Execute the action with the provided parameters.

    Parameters:
        least_action_action_object (dict): Action context object containing metadata and credentials
        param1, param2, ... : User-defined parameters from action_variables

    Returns:
        bool: True if action succeeds, False if action fails
    """
    # Implementation here
```

### Important Rules:

1. **First Parameter**: Must always be `least_action_action_object`
2. **Additional Parameters**: User-defined, extracted from action_variables
3. **Parameter Types**: Can be any type (str, int, bool, dict, list, etc.)
4. **Optional Parameters**: Use default values (e.g., `channel=None`)
5. **Return Value**: Must return `True` (success) or `False` (failure)
6. **Do NOT Call**: The platform calls this method - do not invoke it yourself

### Example:

```python
def run(least_action_action_object, webhook_url, message, channel=None, username=None):
    # Access context
    action_id = least_action_action_object.get('laui')
    connection = least_action_action_object.get('connection', {})

    # Implementation
    # ...

    return True  # or False
```

---

## Understanding least_action_action_object

The `least_action_action_object` is a dictionary containing all context and metadata for the action execution.

### Structure:

```python
least_action_action_object = {
    "laui": "action-unique-identifier",           # Action identifier (string)
    "session_id": "session-unique-identifier",    # Session identifier (string)
    "connection": {                               # Connection credentials (dict)
        "credential_field": "value",
        "region": "us-east-1",
        # ... other connection fields
    },
    "action_variables": {                         # User-provided variables (dict)
        "param1": "value1",
        "param2": "value2",
        # ... other action variables
    },
    "sla": {                                      # SLA configuration (dict)
        "timeout": 300,
        "retry_count": 3,
        # ... other SLA settings
    },
    "task_result": None,                          # Previous task result (any type)
    "connection_laui": "connection-identifier"    # Connection identifier (string)
}
```

### Fields Explained:

| Field | Type | Description |
|-------|------|-------------|
| `laui` | string | Unique identifier for this action instance |
| `session_id` | string | Identifier for the current workflow session |
| `connection` | dict | Contains credentials and connection configuration |
| `action_variables` | dict | User-provided parameters for this execution |
| `sla` | dict | Service Level Agreement settings (timeout, retries, etc.) |
| `task_result` | any | Result from the previous task in the workflow (if any) |
| `connection_laui` | string | Identifier for the connection configuration |

### Accessing Fields:

Always use `.get()` method for safe access:

```python
# Safe access with default fallback
action_id = least_action_action_object.get('laui')
session_id = least_action_action_object.get('session_id')
connection = least_action_action_object.get('connection', {})
action_vars = least_action_action_object.get('action_variables', {})
sla = least_action_action_object.get('sla', {})
previous_result = least_action_action_object.get('task_result')

# Accessing nested fields
region = connection.get('region', 'us-east-1')
timeout = sla.get('timeout', 300)
```

### Common Use Cases:

1. **Accessing Credentials**:
```python
connection = least_action_action_object.get('connection', {})
api_key = connection.get('api_key')
api_secret = connection.get('api_secret')
```

2. **Logging with Context**:
```python
action_id = least_action_action_object.get('laui')
session_id = least_action_action_object.get('session_id')
log_info("action", "run", "start", f"Action {action_id} started in session {session_id}")
```

3. **Using Previous Task Results**:
```python
previous_result = least_action_action_object.get('task_result')
if previous_result:
    # Process result from previous task
    data = previous_result.get('data')
```

4. **Accessing Action Variables**:
```python
action_vars = least_action_action_object.get('action_variables', {})
custom_param = action_vars.get('custom_param', 'default_value')
```

---

## Connection Object

The connection object contains credentials and configuration needed to connect to external services.

### Purpose:
- Store sensitive credentials (API keys, passwords, tokens)
- Provide connection configuration (region, endpoint, timeout)
- Enable credential reuse across multiple actions

### Structure Examples:

**1. API-Based Service (Slack, REST APIs)**:
```json
{
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "base_url": "https://api.example.com",
  "timeout": 30,
  "completed": true
}
```

**2. Cloud Provider (AWS)**:
```json
{
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "aws_session_token": "",
  "region": "us-east-1",
  "completed": true
}
```

**3. Database**:
```json
{
  "host": "postgres-demo",
  "port": 5432,
  "database": "postgres_demo_db",
  "user": "postgres",
  "password": "postgres",
  "completed": true
}
```

**4. No Connection Required**:
```json
{
  "completed": true
}
```

### Accessing Connection in Code:

```python
def run(least_action_action_object, param1):
    # Get connection object
    connection = least_action_action_object.get('connection', {})

    # Extract credentials
    api_key = connection.get('api_key')
    api_secret = connection.get('api_secret')
    region = connection.get('region', 'us-east-1')

    # Use for authentication
    client = SomeAPIClient(
        api_key=api_key,
        api_secret=api_secret,
        region=region
    )
```

### Connection vs Action Variables:

| Connection | Action Variables |
|------------|------------------|
| Credentials (API keys, passwords) | Business logic parameters |
| Connection config (region, endpoint) | Action-specific settings |
| Reusable across actions | Specific to each execution |
| Usually sensitive | Usually not sensitive |

### Authentication Patterns:

**1. Explicit Credentials**:
```python
connection = least_action_action_object.get('connection', {})
if connection.get('api_key'):
    client = APIClient(api_key=connection.get('api_key'))
```

**2. IAM Role (Cloud Environment)**:
```python
connection = least_action_action_object.get('connection', {})
aws_access_key = connection.get('aws_access_key_id')

if aws_access_key:
    # Use explicit credentials
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=connection.get('aws_secret_access_key')
    )
else:
    # Use IAM role or environment credentials
    session = boto3.Session()
```

**3. Environment Variables**:
```python
import os
connection = least_action_action_object.get('connection', {})
api_key = connection.get('api_key') or os.environ.get('API_KEY')
```

---

## Action Variables

Action variables are user-provided parameters that control the behavior of the action.

### Purpose:
- Configure action behavior for each execution
- Provide input data for processing
- Allow customization without code changes

### Example:

```json
{
  "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
  "message": "Task execution completed successfully",
  "channel": "#notifications",
  "username": "LeastAction Bot",
  "icon_emoji": ":robot_face:",
  "completed": true
}
```

### Parameter Types:

**1. Required Parameters** (no default value):
```python
def run(least_action_action_object, webhook_url, message):
    # webhook_url and message must be provided
```

**2. Optional Parameters** (with default value):
```python
def run(least_action_action_object, message, channel=None, priority="normal"):
    # channel and priority are optional
    if channel:
        # Use provided channel
    else:
        # Use default channel
```

**3. Complex Parameters**:
```python
def run(least_action_action_object, config):
    # config can be a dict
    """
    config = {
        "retries": 3,
        "timeout": 30,
        "options": ["opt1", "opt2"]
    }
    """
```

### Naming Conventions:

- Use lowercase with underscores: `webhook_url`, `max_retries`
- Be descriptive: `message` not `msg`, `channel` not `ch`
- Avoid abbreviations unless very common: `api_key` is OK, `wh_url` is not
- Use plural for lists: `instance_ids`, `file_paths`

### Documentation in action_variables:

Provide example values that demonstrate the expected format:

```json
{
  "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
  "message": "Task execution notification",
  "priority": "high",
  "tags": ["production", "critical"],
  "metadata": {
    "source": "workflow-123",
    "environment": "prod"
  },
  "completed": true
}
```

---

## Return Values

The `run` method must return a boolean indicating success or failure.

### Return Types:

| Return Value | Meaning | When to Use |
|--------------|---------|-------------|
| `True` | Action completed successfully | Expected outcome achieved |
| `False` | Action failed | Error occurred, unable to complete |

### Examples:

**Success Case**:
```python
def run(least_action_action_object, param):
    try:
        # Perform operation
        result = perform_operation()

        if result.status_code == 200:
            log_info("action", "run", "success", "Operation completed")
            return True
    except Exception as e:
        log_error("action", "run", "error", f"Failed: {str(e)}")
        return False
```

**Multiple Success Conditions**:
```python
def run(least_action_action_object, operation_type):
    try:
        if operation_type == "create":
            success = create_resource()
        elif operation_type == "update":
            success = update_resource()
        else:
            log_error("action", "run", "invalid_type", f"Unknown operation: {operation_type}")
            return False

        if success:
            log_info("action", "run", "success", f"Operation {operation_type} completed")
            return True
        else:
            log_error("action", "run", "failed", f"Operation {operation_type} failed")
            return False
    except Exception as e:
        log_error("action", "run", "error", f"Exception: {str(e)}")
        return False
```

### Important Notes:

1. **Always Return**: Every code path must return True or False
2. **Log Before Return**: Log the outcome before returning
3. **Clear Meaning**: True = definite success, False = definite failure
4. **No Other Values**: Never return None, strings, or other types

---

## Logging Requirements

Comprehensive logging is **mandatory** for all actions. Use the LeastAction logging framework.

### Import Statement:

```python
from src.common.logger.logger import log_info, log_error
```

### Logging Functions:

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
| `type` | `"action"` | Always "action" for action logging |
| `function` | `"run"` | Name of the function (usually "run") |
| `step` | step name | Descriptive step identifier (lowercase, underscored) |
| `description` | message | Detailed message about what's happening |

### Step Naming Convention:

Use lowercase, descriptive names with underscores:

✅ Good:
- `"start"`
- `"initialize_client"`
- `"send_request"`
- `"parse_response"`
- `"validate_input"`
- `"complete"`
- `"success"`

❌ Bad:
- `"Step1"` (not descriptive)
- `"SendRequest"` (camelCase)
- `"INIT"` (uppercase)
- `"s1"` (abbreviated)

### Required Log Points:

1. **Action Start**:
```python
log_info("action", "run", "start", "Starting [action name]")
```

2. **Major Steps**:
```python
log_info("action", "run", "initialize_client", f"Initializing client for region: {region}")
log_info("action", "run", "prepare_payload", f"Prepared payload with {len(items)} items")
log_info("action", "run", "send_request", f"Sending request to {endpoint}")
```

3. **Success**:
```python
log_info("action", "run", "success", "Operation completed successfully")
```

4. **Errors**:
```python
log_error("action", "run", "connection_error", f"Failed to connect: {str(e)}")
log_error("action", "run", "validation_error", f"Invalid parameter: {param}")
log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
```

### Complete Logging Example:

```python
def run(least_action_action_object, webhook_url, message):
    action_id = least_action_action_object.get('laui')

    try:
        log_info("action", "run", "start", "Starting Slack webhook message send")

        # Prepare payload
        payload = {"text": message}
        log_info("action", "run", "prepare_payload", f"Prepared payload for message: {message[:50]}")

        # Send request
        log_info("action", "run", "send_request", f"Sending request to webhook")
        response = requests.post(webhook_url, json=payload, timeout=30)

        # Check response
        if response.status_code == 200:
            log_info("action", "run", "success", "Message sent successfully to Slack")
            return True
        else:
            log_error("action", "run", "failed", f"Failed with status {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
```

### Logging Best Practices:

1. **Log Early and Often**: Log at every major step
2. **Include Context**: Add relevant variable values in messages
3. **Be Specific**: "Failed to connect to API" not "Error"
4. **Avoid Secrets**: Never log credentials, API keys, passwords
5. **Use f-strings**: For dynamic messages with variables
6. **Log Errors with Details**: Include error messages and types
7. **Consistent Format**: Follow the step naming convention

---

## Error Handling

Robust error handling is essential for reliable actions.

### Try-Except Structure:

```python
def run(least_action_action_object, param):
    try:
        log_info("action", "run", "start", "Starting action")

        # Main logic here
        result = perform_operation()

        log_info("action", "run", "success", "Action completed")
        return True

    except SpecificException as e:
        log_error("action", "run", "specific_error", f"Specific error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
```

### Exception Hierarchy:

Handle specific exceptions before general ones:

```python
try:
    response = requests.post(url, json=payload, timeout=30)

except requests.exceptions.Timeout:
    log_error("action", "run", "timeout", "Request timed out")
    return False
except requests.exceptions.ConnectionError as e:
    log_error("action", "run", "connection_error", f"Connection failed: {str(e)}")
    return False
except requests.exceptions.RequestException as e:
    log_error("action", "run", "request_error", f"Request error: {str(e)}")
    return False
except Exception as e:
    log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
    return False
```

### Common Error Patterns:

**1. Credential Errors**:
```python
try:
    connection = least_action_action_object.get('connection', {})
    api_key = connection.get('api_key')

    if not api_key:
        log_error("action", "run", "missing_credentials", "API key not provided")
        return False

    # Use api_key...

except botocore.exceptions.NoCredentialsError:
    log_error("action", "run", "credentials_error", "AWS credentials not found")
    return False
```

**2. Validation Errors**:
```python
def run(least_action_action_object, email, message):
    try:
        log_info("action", "run", "start", "Starting email send")

        # Validate inputs
        if not email or '@' not in email:
            log_error("action", "run", "validation_error", f"Invalid email: {email}")
            return False

        if not message:
            log_error("action", "run", "validation_error", "Message cannot be empty")
            return False

        # Proceed with sending...
```

**3. API Response Errors**:
```python
try:
    response = api_client.call_endpoint()

    if response.status_code == 200:
        log_info("action", "run", "success", "API call successful")
        return True
    elif response.status_code == 400:
        log_error("action", "run", "bad_request", f"Bad request: {response.text}")
        return False
    elif response.status_code == 401:
        log_error("action", "run", "unauthorized", "Authentication failed")
        return False
    elif response.status_code == 429:
        log_error("action", "run", "rate_limited", "Rate limit exceeded")
        return False
    else:
        log_error("action", "run", "api_error", f"API error {response.status_code}: {response.text}")
        return False
```

**4. Resource Not Found**:
```python
try:
    resource = get_resource_by_id(resource_id)

    if not resource:
        log_error("action", "run", "not_found", f"Resource {resource_id} not found")
        return False

    # Process resource...
```

### Error Handling Best Practices:

1. **Catch Specific Exceptions**: Don't just use `except Exception`
2. **Log All Errors**: Every exception should be logged
3. **Provide Context**: Include relevant variable values in error messages
4. **Fail Gracefully**: Always return False on error
5. **Don't Re-raise**: Handle errors and return False instead
6. **Validate Early**: Check inputs before processing
7. **Timeout Operations**: Use timeouts for network calls
8. **Clean Up Resources**: Use try-finally if needed for cleanup

---

## Best Practices

### 1. Code Organization

```python
import requests
import json
from src.common.logger.logger import log_info, log_error

def run(least_action_action_object, param1, param2):
    """
    Brief description of what this action does.

    Parameters:
        least_action_action_object (dict): Action context
        param1 (type): Description of param1
        param2 (type): Description of param2

    Returns:
        bool: True if successful, False otherwise
    """
    # Extract context
    action_id = least_action_action_object.get('laui')
    connection = least_action_action_object.get('connection', {})

    try:
        log_info("action", "run", "start", "Starting action")

        # Main logic
        # ...

        log_info("action", "run", "success", "Action completed")
        return True

    except Exception as e:
        log_error("action", "run", "error", f"Error: {str(e)}")
        return False
```

### 2. Use Constants

```python
# Good
TIMEOUT = 30
MAX_RETRIES = 3
DEFAULT_REGION = "us-east-1"

def run(least_action_action_object, param):
    response = requests.post(url, json=payload, timeout=TIMEOUT)
```

### 3. Validate Inputs

```python
def run(least_action_action_object, email, count):
    try:
        log_info("action", "run", "start", "Starting action")

        # Validate inputs
        if not email or '@' not in email:
            log_error("action", "run", "validation_error", f"Invalid email: {email}")
            return False

        if not isinstance(count, int) or count <= 0:
            log_error("action", "run", "validation_error", f"Invalid count: {count}")
            return False

        # Proceed...
```

### 4. Use Helper Functions

```python
def _validate_credentials(connection):
    """Validate required credentials are present."""
    required_fields = ['api_key', 'api_secret']
    for field in required_fields:
        if not connection.get(field):
            return False, f"Missing {field}"
    return True, None

def run(least_action_action_object, param):
    try:
        connection = least_action_action_object.get('connection', {})

        valid, error = _validate_credentials(connection)
        if not valid:
            log_error("action", "run", "validation_error", error)
            return False

        # Proceed...
```

### 5. Configuration Over Hardcoding

```python
# Bad
def run(least_action_action_object):
    url = "https://api.example.com/v1/endpoint"  # Hardcoded

# Good
def run(least_action_action_object):
    connection = least_action_action_object.get('connection', {})
    base_url = connection.get('base_url', 'https://api.example.com')
    version = connection.get('api_version', 'v1')
    url = f"{base_url}/{version}/endpoint"
```

### 6. Security Considerations

```python
# Never log credentials
api_key = connection.get('api_key')
log_info("action", "run", "auth", f"Using API key: {api_key}")  # ❌ BAD

# Log safely
log_info("action", "run", "auth", "Authenticating with API key")  # ✅ GOOD

# Validate SSL certificates
response = requests.post(url, json=payload, verify=True)  # ✅ GOOD
```

### 7. Use Type Hints (Optional but Recommended)

```python
from typing import Dict, Any, Optional

def run(
    least_action_action_object: Dict[str, Any],
    message: str,
    priority: Optional[str] = "normal"
) -> bool:
    # Implementation
```

### 8. Avoid Magic Numbers

```python
# Bad
if response.status_code == 200:  # What does 200 mean?

# Good
HTTP_OK = 200
if response.status_code == HTTP_OK:
```

### 9. Keep Functions Focused

```python
# Each helper does one thing
def _build_payload(message, metadata):
    """Build request payload."""
    return {"message": message, "metadata": metadata}

def _send_request(url, payload, timeout):
    """Send HTTP request."""
    return requests.post(url, json=payload, timeout=timeout)

def run(least_action_action_object, message, metadata):
    try:
        payload = _build_payload(message, metadata)
        response = _send_request(url, payload, 30)
        # ...
```

### 10. Document Complex Logic

```python
# For complex operations, add comments
def run(least_action_action_object, config):
    try:
        # Parse configuration
        # Format: {"retries": 3, "backoff": "exponential", "max_wait": 60}
        retries = config.get('retries', 3)
        backoff_strategy = config.get('backoff', 'exponential')

        # Implement retry logic with exponential backoff
        # Wait times: 1s, 2s, 4s, 8s, ...
        for attempt in range(retries):
            wait_time = 2 ** attempt
            # ...
```

---

## Complete Example

Here's a complete, production-ready action that sends Slack notifications via webhook:

### JSON Structure:

```json
{
  "bashblock": {
    "main.sh": "pip install requests",
    "completed": true
  },
  "codeblock": {
    "main.py": "[See Python code below]",
    "completed": true
  },
  "action_variables": {
    "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
    "message": "Task execution notification",
    "channel": "#general",
    "username": "LeastAction Bot",
    "icon_emoji": ":robot_face:",
    "completed": true
  },
  "connection": {
    "completed": true
  },
  "item_type": "action"
}
```

### Python Code (main.py):

```python
import requests
import json
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, webhook_url, message, channel=None, username=None, icon_emoji=None):
    """
    Send a message to Slack using an incoming webhook.

    This action sends a notification to a Slack channel using Slack's incoming
    webhook integration. It supports customizing the channel, username, and icon.

    Parameters:
        least_action_action_object (dict): Action context containing laui, session_id, connection
        webhook_url (str): Slack incoming webhook URL (required)
        message (str): Message text to send (required)
        channel (str): Override default channel, e.g., "#general" (optional)
        username (str): Override default username (optional)
        icon_emoji (str): Override default icon, e.g., ":robot_face:" (optional)

    Returns:
        bool: True if message sent successfully, False otherwise

    Example:
        run(
            least_action_action_object,
            webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
            message="Workflow completed successfully!",
            channel="#notifications",
            username="LeastAction Bot",
            icon_emoji=":white_check_mark:"
        )
    """
    # Extract action context
    action_id = least_action_action_object.get('laui')

    try:
        log_info("action", "run", "start", "Starting Slack webhook message send")

        # Build payload with required fields
        payload = {
            "text": message
        }

        # Add optional fields if provided
        if channel:
            payload["channel"] = channel
        if username:
            payload["username"] = username
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji

        log_info("action", "run", "prepare_payload", f"Prepared payload for channel: {channel or 'default'}")

        # Send request to Slack webhook
        log_info("action", "run", "send_request", "Sending message to Slack webhook")
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        # Check response status
        if response.status_code == 200:
            log_info("action", "run", "success", "Message sent successfully to Slack")
            return True
        else:
            log_error(
                "action",
                "run",
                "failed",
                f"Failed to send message. Status: {response.status_code}, Response: {response.text}"
            )
            return False

    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out while sending Slack message")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
```

### Key Features of This Example:

1. ✅ Complete docstring explaining purpose, parameters, and usage
2. ✅ Required parameters (webhook_url, message) and optional parameters (channel, username, icon_emoji)
3. ✅ Comprehensive logging at every step
4. ✅ Specific exception handling (Timeout, RequestException, general Exception)
5. ✅ Input validation through optional parameters with defaults
6. ✅ Clear return values (True/False)
7. ✅ Timeout on network request (30 seconds)
8. ✅ Proper HTTP headers and JSON encoding
9. ✅ Error logging with detailed context
10. ✅ Follows all LeastAction conventions

---

## Development Workflow

Follow this step-by-step process to develop a new action:

### Step 1: Understand Requirements

**Questions to Answer:**
- What is the action supposed to do?
- What external service/API does it interact with?
- What inputs does it need?
- What credentials are required?
- What constitutes success vs failure?

**Example:**
- Action: Send email via SendGrid
- Service: SendGrid API
- Inputs: recipient_email, subject, body, from_email
- Credentials: SendGrid API key
- Success: Email sent (200 response)

### Step 2: Design the Action

**Define:**

1. **Action Variables** (user inputs):
```json
{
  "recipient_email": "user@example.com",
  "subject": "Workflow Notification",
  "body": "Your workflow has completed",
  "from_email": "noreply@example.com"
}
```

2. **Connection** (credentials):
```json
{
  "sendgrid_api_key": "SG.xxxxxxxxxxxxx"
}
```

3. **Dependencies**:
```bash
pip install sendgrid
```

### Step 3: Write the Run Method

**Template:**

```python
import sendgrid
from sendgrid.helpers.mail import Mail
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, recipient_email, subject, body, from_email):
    """
    [Docstring describing the action]
    """
    # 1. Extract context
    action_id = least_action_action_object.get('laui')
    connection = least_action_action_object.get('connection', {})

    try:
        # 2. Log start
        log_info("action", "run", "start", "Starting SendGrid email send")

        # 3. Validate inputs
        if not recipient_email or '@' not in recipient_email:
            log_error("action", "run", "validation_error", f"Invalid recipient: {recipient_email}")
            return False

        # 4. Get credentials
        api_key = connection.get('sendgrid_api_key')
        if not api_key:
            log_error("action", "run", "missing_credentials", "SendGrid API key not provided")
            return False

        # 5. Initialize client
        log_info("action", "run", "initialize_client", "Initializing SendGrid client")
        sg = sendgrid.SendGridAPIClient(api_key=api_key)

        # 6. Prepare message
        message = Mail(
            from_email=from_email,
            to_emails=recipient_email,
            subject=subject,
            html_content=body
        )
        log_info("action", "run", "prepare_message", f"Prepared email to {recipient_email}")

        # 7. Send message
        log_info("action", "run", "send_email", "Sending email via SendGrid")
        response = sg.send(message)

        # 8. Check response
        if response.status_code in [200, 202]:
            log_info("action", "run", "success", f"Email sent successfully (status: {response.status_code})")
            return True
        else:
            log_error("action", "run", "failed", f"Failed to send email (status: {response.status_code})")
            return False

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Error sending email: {str(e)}")
        return False
```

### Step 4: Add Error Handling

Wrap operations in try-except blocks:

```python
try:
    # Main logic
    pass
except SpecificException as e:
    log_error("action", "run", "specific_error", f"Specific error: {str(e)}")
    return False
except Exception as e:
    log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
    return False
```

### Step 5: Test the Action

**Create Test Script:**

```python
# test_action.py
from main import run

# Mock least_action_action_object
test_object = {
    "laui": "test-action-123",
    "session_id": "test-session-456",
    "connection": {
        "sendgrid_api_key": "SG.test_key"
    },
    "action_variables": {
        "recipient_email": "test@example.com",
        "subject": "Test Email",
        "body": "This is a test",
        "from_email": "noreply@example.com"
    }
}

# Test the action
result = run(
    test_object,
    recipient_email="test@example.com",
    subject="Test Email",
    body="This is a test",
    from_email="noreply@example.com"
)

print(f"Action result: {result}")
```

**Run Tests:**
```bash
python test_action.py
```

### Step 6: Create JSON Structure

Assemble the complete action JSON:

```json
{
  "bashblock": {
    "install_dependencies.sh": "pip install sendgrid==6.9.7",
    "completed": true
  },
  "codeblock": {
    "sendgrid_email.py": "[Complete Python code]",
    "completed": true
  },
  "action_variables": {
    "recipient_email": "user@example.com",
    "subject": "Workflow Notification",
    "body": "Your workflow has completed successfully",
    "from_email": "noreply@example.com",
    "completed": true
  },
  "connection": {
    "sendgrid_api_key": "SG.xxxxxxxxxxxxx",
    "completed": true
  },
  "item_type": "action"
}
```

### Step 7: Document (if requested)

If user requests documentation, create a guide:

```json
{
  "guide": {
    "guide.txt": "[Comprehensive guide content]",
    "completed": true
  }
}
```

### Step 8: Review Checklist

Before finalizing, verify:

- [ ] Action has a `run` method with `least_action_action_object` as first parameter
- [ ] All required parameters are documented in action_variables
- [ ] Connection object contains all necessary credentials
- [ ] Dependencies are listed in bashblock
- [ ] Comprehensive logging at all major steps (start, success, errors)
- [ ] Try-except blocks around all operations
- [ ] Returns True on success, False on failure
- [ ] No credentials logged
- [ ] Timeout on network operations
- [ ] Input validation for critical parameters
- [ ] Clear error messages
- [ ] Docstring explains purpose and parameters
- [ ] "completed": true in all JSON sections
- [ ] "item_type": "action" in root JSON

---

## Quick Reference Card

### Action Template

```python
import [libraries]
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, param1, param2=None):
    """
    Brief description.

    Parameters:
        least_action_action_object (dict): Action context
        param1 (type): Description
        param2 (type): Description (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    # Extract context
    action_id = least_action_action_object.get('laui')
    connection = least_action_action_object.get('connection', {})

    try:
        log_info("action", "run", "start", "Starting [action name]")

        # Main logic
        # ...

        log_info("action", "run", "success", "Action completed")
        return True

    except SpecificException as e:
        log_error("action", "run", "specific_error", f"Error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Error: {str(e)}")
        return False
```

### JSON Template

```json
{
  "bashblock": {
    "main.sh": "pip install package",
    "completed": true
  },
  "codeblock": {
    "main.py": "[Python code]",
    "completed": true
  },
  "action_variables": {
    "param1": "value1",
    "completed": true
  },
  "connection": {
    "credential_field": "value",
    "completed": true
  },
  "item_type": "action"
}
```

### Common Patterns

**Access Connection:**
```python
connection = least_action_action_object.get('connection', {})
api_key = connection.get('api_key')
```

**Log Steps:**
```python
log_info("action", "run", "step_name", f"Description: {details}")
log_error("action", "run", "error_type", f"Error: {str(e)}")
```

**Return Values:**
```python
return True   # Success
return False  # Failure
```

**Validate Input:**
```python
if not param or invalid_condition:
    log_error("action", "run", "validation_error", f"Invalid {param}")
    return False
```

---

## Additional Resources

### LeastAction Documentation
- **Logging Framework**: `src.common.logger.logger`
- **Example Actions**: `bootstrap/actions/` directory

### External References
- **Python Best Practices**: [PEP 8 Style Guide](https://pep8.org/)
- **Error Handling**: [Python Exception Handling](https://docs.python.org/3/tutorial/errors.html)
- **Type Hints**: [Python typing module](https://docs.python.org/3/library/typing.html)

### Getting Help
- Review existing actions in `bootstrap/actions/` for patterns
- Check action.txt prompt for AI generation guidelines
- Test thoroughly with mock data before production use

---

## Appendix: Action vs Operator

LeastAction has two types of executable components:

| Feature | Action | Operator |
|---------|--------|----------|
| **Purpose** | Simple, synchronous operations | Complex, async operations |
| **Methods** | `run()` only | `initialize()`, `run()`, `check_completion()`, `finish()` |
| **Execution** | Immediate | Async with status checking |
| **Use Cases** | Notifications, simple API calls | Long-running jobs, batch processing |
| **Complexity** | Lower | Higher |
| **Return** | Boolean (True/False) | Status dict with "pending", "success", "failed" |

**When to use Action:**
- Send notification (email, Slack, SMS)
- Simple API call with immediate response
- Data transformation/validation
- File operations (read, write, move)

**When to use Operator:**
- Start AWS EC2 instances (takes time)
- Run batch data processing job
- Deploy application (multi-step process)
- Poll for completion of external task

---

This guide provides everything you need to develop production-ready actions for LeastAction. Follow the structure, conventions, and best practices outlined here to create reliable, maintainable, and well-documented actions.

Happy coding!
