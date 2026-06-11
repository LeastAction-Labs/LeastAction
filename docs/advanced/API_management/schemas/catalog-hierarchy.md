# Catalog Hierarchy Reference

## Item Type Hierarchy

Items are organized in a parent-child hierarchy. The `catalog.json` configuration defines which item types can contain which other types.

**Maximum hierarchy depth**: 10 levels

## Hierarchy Tree

```
folder.account
├── folder.project
│   ├── folder.workflow
│   │   ├── folder.workflow (nested)
│   │   ├── task
│   │   ├── config
│   │   ├── connection
│   │   ├── payload
│   │   ├── operator
│   │   └── action
│   ├── folder.operator
│   │   ├── folder.operator (nested)
│   │   └── operator
│   ├── folder.action
│   │   ├── folder.action (nested)
│   │   └── action
│   ├── folder.payload
│   │   ├── folder.payload (nested)
│   │   └── payload
│   ├── folder.connection
│   │   ├── folder.connection (nested)
│   │   └── connection
│   ├── folder.config
│   │   ├── folder.config (nested)
│   │   └── config
│   ├── folder.asset
│   │   ├── folder.asset (nested)
│   │   ├── folder.report
│   │   │   ├── folder.report (nested)
│   │   │   ├── html_report
│   │   │   └── config
│   │   ├── folder.table
│   │   │   ├── folder.table (nested)
│   │   │   ├── table
│   │   │   └── config
│   │   ├── html_report
│   │   ├── table
│   │   └── config
│   ├── folder.ai
│   │   ├── folder.ai (nested)
│   │   ├── folder.chat
│   │   │   ├── folder.chat (nested)
│   │   │   └── chat
│   │   ├── folder.skill
│   │   │   ├── folder.skill (nested)
│   │   │   └── skill
│   │   └── skill
│   └── folder.bootstrap
├── folder.trash
│   ├── task
│   ├── connection
│   ├── config
│   ├── action
│   ├── operator
│   ├── payload
│   ├── html_report
│   └── table
└── folder.users
    └── folder.user
        └── chat_history
```

## Non-Folder Parent-Child Relationships

Some non-folder items can also contain children:

| Parent Type | Can Contain |
|-------------|-------------|
| `connection` | `connection_queue`, `task` |
| `operator` | `task` |
| `task` | `task` (subtasks) |
| `payload` | `task` |
| `config` | `task` |
| `table` | `column` |
| `database` | `schema` |
| `schema` | `table` |

## Link Types

Items are connected through links with two types:

| Link Property | Description |
|---------------|-------------|
| `true_parent` = `true` | The item's primary parent (ownership relationship) |
| `true_parent` = `false` | A secondary/reference relationship |

For example, a **task** has:
- **true_parent** link to its workflow folder
- **false_parent** links to its operator, connection, payload, and config items

## Connection-Operator Mapping

Connections and operators must be compatible. The mapping is defined in `config/system.yml`:

| Connection Type | Compatible Operators |
|----------------|---------------------|
| `connection.AWSIAMRole` | `operator.AWSIAMRole` |
| `connection.python` | `operator.python`, `operator.spark` |
| `connection.docker` | `operator.docker` |
| `connection.kubernetes` | `operator.kubernetes` |
| `connection.spark` | `operator.spark` |
| `connection.databricks` | `operator.spark`, `operator.python` |
| `connection.anthropic` | `operator.anthropic` |
| `connection.slack` | `operator.slack` |
| `connection.postgresql` | `operator.postgresql` |
| `connection.AWS` | `operator.AWS` |
| `connection.leastaction` | `operator.leastaction` |

When creating or executing a task, the system validates that the operator type is allowed for the specified connection type. If the mapping is invalid, a `422 Unprocessable Entity` error is returned with the list of valid operators for that connection.
