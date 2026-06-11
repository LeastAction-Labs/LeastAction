# Config Manager

The Config Manager is a core component responsible for managing task configurations in the LeastAction system. It handles configuration merging, parameter resolution, and placeholder replacement for task execution.

## Overview

The `ConfigManager` class provides a robust configuration management system that:
- Merges configurations from 3 sources during task creation (workflow configs, attached task configs, and inline task config)
- Enforces parameter override policies
- Replaces placeholders in task payloads with actual values during task execution
- Provides built-in system variables for dynamic configuration

**Important:** Config merging only occurs during task creation. The merged result is persisted to the database. During task execution, only placeholder replacement is performed using the already-merged config.

## Configuration Hierarchy

Configurations are merged in the following order (later sources override earlier ones):

1. **Workflow Configs** - Configs auto-discovered as children of the parent workflow (queried by `parent_laui`)
2. **Attached Task Configs** - Task-specific configs referenced via `attached_config_lauis`
3. **Inline Task Config** - The `config` field provided directly on the task at creation time

## Key Features

### 1. Configuration Merging

The `merge_configs()` method intelligently merges multiple configuration sources while respecting override rules.

**Input:**
- `task_config`: The runtime task configuration dictionary
- `configs_data`: Dictionary containing `task_configs` and `workflow_configs` arrays

**Output:**
- Dictionary with `merged_config` and `merged_value_sources` (tracking the origin of each value)

**Override Rules:**
- Parameters can be marked as `overridable` or `not_overridable`
- Once a parameter is set, subsequent attempts to override it are logged and ignored (unless marked as overridable)
- Non-overridable parameters cannot be changed by later configurations

### 2. Parameter Management

Three lists track parameter override behavior:
- `overridable_params`: Parameters that can be overridden by subsequent configs
- `not_overridable_params`: Parameters that are locked after first definition
- `overridden_params`: Tracks which parameters have been set

### 3. Placeholder Replacement

The `replace_placeholders()` method supports dynamic value substitution using Jinja2 template syntax.

**Supported Types:**
- Strings (plain text and JSON strings)
- Dictionaries (recursive replacement)
- Lists (recursive replacement)
- Nested structures

**Placeholder Format:**
```
{{ parameter_name }}
```

**Behavior:**
- Undefined placeholders are preserved in the output
- JSON strings are parsed, replaced, and serialized back
- Supports nested structures

### 4. Built-in System Variables

The `get_builtin_variables()` method provides system-level variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `ds` | Current date | `2026-01-08` |
| `ts` | Current timestamp (ISO format) | `2026-01-08T14:30:00.000000` |

Additional system variables can be added by extending this method.

## Core Methods

### `merge_configs(task_config, configs_data)`

Merges configurations from multiple sources.

```python
result = config_manager.merge_configs(
    task_config={"parameters": {"env": "prod"}},
    configs_data={
        "workflow_configs": [...],
        "task_configs": [...]
    }
)

merged_config = result["merged_config"]
value_sources = result["merged_value_sources"]
```

### `replace_placeholders(payload_content, parameters)`

Replaces template placeholders with actual values.

```python
payload = {
    "url": "https://api.example.com/data/{{ ds }}",
    "environment": "{{ env }}"
}

parameters = {
    "ds": "2026-01-08",
    "env": "production"
}

result = config_manager.replace_placeholders(payload, parameters)
# Result: {"url": "https://api.example.com/data/2026-01-08", "environment": "production"}
```

### `process_task_execution(task)`

Main entry point for task preparation. Combines built-in variables with config parameters and replaces all placeholders in the task payload.

```python
prepared_task = config_manager.process_task_execution(task)
```

This method:
1. Retrieves built-in system variables (ds, ts, etc.)
2. Extracts parameters from task.config
3. Combines all parameters (built-in variables take precedence)
4. Replaces placeholders in task.payload

### `cleanup()`

Resets internal state (override tracking lists).

## How Config Sources Are Resolved

### Workflow Configs
Workflow configs are **automatically discovered** by querying all `config` items that are children of the task's parent workflow (`parent_laui`). This is done via `_get_all_attached_configs()` in `TaskValidationManager`, which calls `find_items()` with the workflow LAUI and `item_type="config"`, `parent_or_child="child"`.

### Attached Task Configs
Attached task configs are **explicitly specified** via the `attached_config_lauis` field on the task. These are fetched individually with full projections to include the `content` field.

### Inline Task Config
The `config` field provided directly on the task creation request.

## Usage Example

```python
from src.core.task.config.config_manager import ConfigManager

# Initialize
config_manager = ConfigManager()

# Merge configurations (called during task creation, NOT execution)
result = config_manager.merge_configs(
    task_config={
        "parameters": {
            "database": "analytics_db",
            "table": "events_{{ ds }}"
        },
        "not_overridable": ["database"]
    },
    configs_data={
        "workflow_configs": [{
            "laui": "workflow-001",
            "content": {
                "parameters": {
                    "environment": "production"
                }
            }
        }],
        "task_configs": [{
            "laui": "task-config-001",
            "content": {
                "parameters": {
                    "batch_size": 1000
                }
            }
        }]
    }
)

merged_config = result["merged_config"]
# Contains merged parameters from all 3 sources
# This merged config is saved to the database with the task

# During task execution, only placeholder replacement occurs:
prepared_task = config_manager.process_task_execution(task)
# Task payload now has all placeholders replaced with actual values
```

## Configuration Structure

### Config Object Format

Configs from the database include metadata:
```json
{
  "laui": "config-identifier",
  "content": {
    "parameters": {
      "key": "value"
    },
    "overridable": ["param1", "param2"],
    "not_overridable": ["param3"]
  }
}
```

Inline task configs (the `config` field on the task) are used directly without the wrapper:
```json
{
  "parameters": {
    "key": "value"
  }
}
```

## Implementation Details

### Special Undefined Handler

The `KeepUndefined` class ensures that undefined placeholders are preserved in the output rather than being removed or throwing errors:

```python
# If 'unknown_var' is not provided
"Value: {{ unknown_var }}"  # Remains as "Value: {{ unknown_var }}"
```

### Merge Algorithm

The merge process uses recursive merging with override tracking:
- Dictionary values are merged recursively
- Non-dictionary values replace previous values
- `parameters` key at root level gets special handling via `_merge_parameters()`
- All other keys follow standard merge rules via `_merge_content()`

### Value Source Tracking

The `merged_value_sources` dictionary mirrors the structure of `merged_config` and records which configuration (identified by LAUI) provided each value. This enables debugging and audit trails.

## Error Handling

- Undefined placeholders are preserved rather than causing errors
- Invalid JSON in string replacement is handled gracefully
- Parameter override violations are logged as warnings
- All operations are logged for debugging

## Best Practices

1. **Config merging is creation-time only**: The merged config is saved to the database at task creation. Execution only replaces placeholders
2. **Workflow configs are auto-discovered**: Any config item that is a child of the parent workflow will be merged. Be mindful of what configs are placed under a workflow
3. **Define override policies early**: Set `overridable` and `not_overridable` lists in workflow configs
4. **Use system variables**: Leverage built-in variables like `ds` and `ts` for dynamic values
5. **Track value sources**: Use `merged_value_sources` for debugging configuration issues
6. **Clean parameter names**: Avoid special characters in parameter names
7. **Test placeholder syntax**: Ensure `{{ param }}` format with spaces inside braces

## Logging

The ConfigManager logs all operations at various levels:
- **INFO**: Normal operations (merges, replacements)
- **WARNING**: Override violations, ignored parameters
- **ERROR**: Placeholder rendering failures

All logs include context (API, ConfigManager, method name) for easy filtering.
