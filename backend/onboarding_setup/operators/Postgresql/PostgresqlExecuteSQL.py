# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
operator_type = "postgresql"
codeblock = {"main.py":'''
"""PostgreSQL SQL Executor Operator

This operator connects to PostgreSQL and executes SQL commands (excluding SELECT).
Supports INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, and other DML/DDL operations.
"""
import time

import psycopg2
import psycopg2.extras
import sqlparse
from psycopg2 import Error as PostgreSQLError

from src.common.logger.logger import log_info, log_error


def initialize(least_action_task_object):
    """
    Initialize PostgreSQL connection with credentials from connection.
    """
    try:
        connection_config = least_action_task_object.get('connection', {})

        log_info("task", "initialize", "extracting_connection_details", "Extracting connection details for task")

        host = connection_config.get('host', 'localhost')
        port = connection_config.get('port', 5432)
        database = connection_config.get('database')
        user = connection_config.get('user')
        password = connection_config.get('password')

        if not database:
            raise ValueError("Database name is required in connection configuration")
        if not user:
            raise ValueError("User is required in connection configuration")

        log_info("task", "initialize", "creating_connection", "Creating PostgreSQL connection")

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10,
        )

        log_info("task", "initialize", "connection_established", "PostgreSQL connection established")

        log_info(
            "task",
            "initialize",
            "verifying_connection",
            "Verifying PostgreSQL connection",
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()

        log_info(
            "task",
            "initialize",
            "connection_verified",
            f"PostgreSQL connection verified. Version: {version.split(',')[0]}",
        )

        return conn

    except ValueError as e:
        log_error("task", "initialize", "validation_error", str(e))
        raise
    except PostgreSQLError as e:
        log_error("task", "initialize", "postgresql_error", str(e))
        raise
    except Exception as e:
        log_error("task", "initialize", "initialization_failed", str(e))
        raise


def _validate_sql_statement(sql_command):
    """
    Validate SQL command.

    - Reject top-level SELECT
    - Allow SELECT inside CTE or subqueries
    - Allow only specific DML/DDL
    """
    try:
        parsed = sqlparse.parse(sql_command)

        if not parsed:
            return True, "Empty or invalid SQL statement"

        log_info("task", "validate_sql", "statement_count", "Validating SQL statement(s)")

        allowed_types = {
            'INSERT',
            'UPDATE',
            'DELETE',
            'CREATE',
            'ALTER',
            'DROP',
            'TRUNCATE',
            'GRANT',
            'REVOKE',
            'COMMENT',
        }

        for idx, statement in enumerate(parsed, 1):
            if not statement.tokens:
                continue

            stmt_type = statement.get_type()

            log_info(
                "task",
                "validate_sql",
                "statement_type_detected",
                f"Statement {idx}: {stmt_type}",
            )

            if stmt_type == 'SELECT':
                error_msg = f"Direct SELECT statement detected at position {idx}"
                log_error("task", "validate_sql", "select_detected", error_msg)
                return True, error_msg

            if stmt_type == 'UNKNOWN':
                error_msg = f"Unsupported or invalid SQL at position {idx}"
                log_error("task", "validate_sql", "unknown_statement", error_msg)
                return True, error_msg

            if stmt_type in {'BEGIN', 'COMMIT', 'ROLLBACK'}:
                error_msg = f"Transaction control statements not allowed at position {idx}"
                log_error("task", "validate_sql", "transaction_not_allowed", error_msg)
                return True, error_msg

            if stmt_type not in allowed_types:
                error_msg = f"Statement type '{stmt_type}' not allowed at position {idx}"
                log_error("task", "validate_sql", "statement_not_allowed", error_msg)
                return True, error_msg

        log_info(
            "task",
            "validate_sql",
            "validation_passed",
            "All statements validated successfully",
        )

        return False, ""

    except Exception as e:
        log_error(
            "task",
            "validate_sql",
            "validation_error",
            f"Error during SQL validation: {str(e)}",
        )
        return True, "SQL validation failed due to parsing error"


def run(least_action_task_object, conn):
    """
    Execute SQL command on PostgreSQL database.
    """
    cursor = None
    try:
        payload_str = least_action_task_object.get('payload', '')

        log_info("task", "run", "extracting_payload", "Extracting SQL command from payload")

        if not payload_str or not isinstance(payload_str, str):
            raise ValueError("Payload must contain a non-empty SQL command string")

        sql_command = payload_str.strip()

        if not sql_command:
            raise ValueError("SQL command cannot be empty")

        log_info("task", "run", "validating_sql_command", "Validating SQL command")

        has_error, validation_error_msg = _validate_sql_statement(sql_command)

        if has_error:
            raise ValueError(f"SQL validation failed: {validation_error_msg}")

        log_info("task", "run", "validation_passed", "SQL validation passed")
        log_info("task", "run", "executing_sql_command", "Executing SQL command")

        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(sql_command)
        execution_time = time.time() - start_time

        affected_rows = cursor.rowcount
        conn.commit()

        return {
            'execution_type': 'sync',
            'result': {
                'sql_command': sql_command[:500],
                'affected_rows': affected_rows,
                'execution_time_seconds': round(execution_time, 4),
                'status': 'executed',
                'message': f'SQL command executed successfully. {affected_rows} row(s) affected.',
            },
            'status': 'success',
            'timestamp': time.time(),
        }

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

        log_error("task", "run", "executing_sql_command", f"error executing sql cmd :- {e}")

        return {
            'execution_type': 'sync',
            'result': {
                'sql_command': '',
                'affected_rows': 0,
                'execution_time_seconds': 0,
                'status': 'failed',
                'message': str(e),
            },
            'status': 'failed',
            'timestamp': time.time(),
        }

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass


def check_completion(least_action_task_object, conn, run_details):
    """
    Check the completion status of a previously executed SQL task.
    """
    try:
        execution_type = run_details.get('execution_type')

        if execution_type == 'sync':
            result = run_details.get('result', {})
            status = run_details.get('status', 'unknown')

            return {
                'status': status,
                'message': result.get('message', ''),
                'output': {
                    'affected_rows': result.get('affected_rows', 0),
                    'execution_time_seconds': result.get('execution_time_seconds', 0),
                    'sql_command': result.get('sql_command', ''),
                    'execution_type': 'sync',
                },
            }

        return {'status': 'failed', 'message': 'Unexpected execution type', 'output': {}}

    except Exception as e:
        return {'status': 'failed', 'message': str(e), 'output': {}}


def finish(least_action_task_object, conn, completion_details, run_details):
    """
    Close the PostgreSQL connection and clean up resources.
    """
    try:
        if conn:
            conn.close()
    except Exception:
        pass
'''
}
bashblock = {"main.sh":"""
#!/bin/bash

# Install required dependencies for PostgreSQL Operator
pip install psycopg2-binary==2.9.* sqlparse==0.4.*

# Verify installation
python3 -c "import psycopg2; print(f'psycopg2 version: {psycopg2.__version__}')"
python3 -c "import sqlparse; print(f'sqlparse version: {sqlparse.__version__}')"

echo "Dependencies installed successfully"

"""

}

connection = {
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "your_password_here"
}
payload="""
INSERT INTO people (name, age) VALUES ('Alice', 28), ('Bob', 34), ('Charlie', 22);
"""

prompt = (
    "Execute a SQL DML/DDL command (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE) against PostgreSQL. "
    "Payload is a raw SQL string — no SELECT statements allowed at the top level. "
    "Validates the SQL statement type before execution. Commits on success, rolls back on failure. "
    "Connection fields: host, port, database, user, password. "
    "Returns affected_rows and execution_time_seconds on success."
)

install_docs = """# PostgresqlExecuteSQL — Install Guide

## Dependencies

    pip install psycopg2-binary==2.9.*
    pip install sqlparse==0.4.*

## PostgreSQL Setup

The operator connects with the credentials in connection. Ensure the user has permissions
for the SQL operations being executed (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP etc).
"""

guide_docs = """# PostgresqlExecuteSQL — Operator Guide

## What it does

Connects to PostgreSQL and executes a single SQL DML or DDL command. Validates that the
statement is not a top-level SELECT (CTEs and subqueries are allowed). Commits on success,
rolls back automatically on any failure.

---

## Connection

    {
      "host": "localhost",
      "port": 5432,
      "database": "mydb",
      "user": "postgres",
      "password": "..."
    }

---

## Payload

A raw SQL string:

    INSERT INTO people (name, age) VALUES ('Alice', 28);

Or a multi-statement DDL:

    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    );

Allowed statement types: INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, COMMENT.

---

## Output (on success)

    {
      "sql_command": "INSERT INTO...",
      "affected_rows": 3,
      "execution_time_seconds": 0.0012,
      "status": "executed",
      "message": "SQL command executed successfully. 3 row(s) affected."
    }
"""

description = """
Executes a SQL DML or DDL command against PostgreSQL. Validates the statement type to reject
top-level SELECTs. Commits on success, rolls back on failure. Supports INSERT, UPDATE, DELETE,
CREATE, ALTER, DROP, TRUNCATE and other non-query statements. Returns affected row count and
execution time.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Database",
    "tags": ["postgresql", "sql", "execute", "insert", "update", "delete", "ddl", "dml"],
    "airflow_equivalent": "PostgresOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
