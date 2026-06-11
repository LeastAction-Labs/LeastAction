# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock ={"main.py": '''"""
PostgreSQL Connection Checker

This module provides functionality to test PostgreSQL database connections.
"""

import psycopg2
from psycopg2 import Error
from typing import Dict, Any, Optional
from src.common.logger.logger import log_info, log_error


def run(
    least_action_action_object: Dict[str, Any],
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    **kwargs
) -> bool:
    """
    Checks if a successful connection can be established to a PostgreSQL instance.
    
    Parameters:
        least_action_action_object (dict): Action object containing metadata
        host (str): PostgreSQL server hostname or IP address
        port (int): PostgreSQL server port
        database (str): Database name to connect to
        user (str): PostgreSQL username
        password (str): PostgreSQL password
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    connection: Optional[psycopg2.extensions.connection] = None
    
    try:
        log_info("action", "run", "start", "Starting PostgreSQL connection check")
        
        # Validate parameters
        log_info(
            "action",
            "run",
            "validate_parameters",
            f"Validating connection parameters for host: {host}, "
            f"port: {port}, database: {database}"
        )
        
        if not all([host, port, database, user, password]):
            log_error(
                "action",
                "run",
                "validate_parameters",
                "Missing required connection parameters"
            )
            return False
        
        # Establish connection
        log_info(
            "action",
            "run",
            "establish_connection",
            f"Attempting to connect to PostgreSQL at {host}:{port}/{database}"
        )
        
        connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )
        
        log_info(
            "action",
            "run",
            "connection_established",
            "Successfully established connection to PostgreSQL"
        )
        
        # Test query
        log_info(
            "action",
            "run",
            "test_query",
            "Executing test query to verify connection functionality"
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        
        version_info = db_version[0] if db_version else "Unknown"
        log_info(
            "action",
            "run",
            "test_query",
            f"Test query successful. Database version: {version_info}"
        )
        
        log_info(
            "action",
            "run",
            "connection_verified",
            "PostgreSQL connection verified and ready for command execution"
        )
        
        # Print success status
        _print_connection_status(
            success=True,
            host=host,
            port=port,
            database=database,
            user=user,
            version=version_info
        )
        
        return True
        
    except Error as e:
        log_error(
            "action",
            "run",
            "connection_error",
            f"PostgreSQL connection error: {str(e)}"
        )
        _print_connection_status(success=False, error=str(e))
        return False
        
    except Exception as e:
        log_error(
            "action",
            "run",
            "unexpected_error",
            f"Unexpected error during connection check: {str(e)}"
        )
        _print_connection_status(success=False, error=f"Unexpected Error: {str(e)}")
        return False
        
    finally:
        if connection is not None:
            log_info("action", "run", "cleanup", "Closing PostgreSQL connection")
            connection.close()


def _print_connection_status(
    success: bool,
    host: str = "",
    port: int = 0,
    database: str = "",
    user: str = "",
    version: str = "",
    error: str = ""
) -> None:
    """
    Print formatted connection status information.
    
    Parameters:
        success (bool): Whether the connection was successful
        host (str): PostgreSQL server hostname
        port (int): PostgreSQL server port
        database (str): Database name
        user (str): PostgreSQL username
        version (str): Database version string
        error (str): Error message if connection failed
    """
    separator = "=" * 80
    status = "SUCCESS" if success else "FAILED"
    
    print(f"\\n{separator}")
    print(f"PostgreSQL Connection Status: {status}")
    print(separator)
    
    if success:
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Database: {database}")
        print(f"User: {user}")
        if version:
            print(f"Database Version: {version}")
    else:
        if error:
            print(f"Error: {error}")
    
    print(f"{separator}\\n")
'''
}
bashblock = {"shell.sh":''' 
pip install psycopg2-binary==2.9.9
 '''
}
action_variables= {
  "host": "localhost",
  "port": 5432,
  "database": "postgres",
  "user": "postgres",
  "password": ""
}
connection = {}

prompt = (
    "Test a PostgreSQL database connection by attempting to connect and retrieve the server version. "
    "Action variables: host, port, database, user, password. "
    "Returns True if the connection succeeds, False otherwise. Prints server version on success. "
    "Use as a pre-flight check before running database operators."
)

install_docs = """# PostgresqlTestConnection — Install Guide

## Dependencies

    pip install psycopg2-binary==2.9.9
"""

guide_docs = """# PostgresqlTestConnection — Action Guide

## What it does

Tests a PostgreSQL connection by connecting with the provided credentials and executing
SELECT version(). Prints the server version on success. Returns True/False.

---

## Action Variables

    {
      "host": "localhost",
      "port": 5432,
      "database": "postgres",
      "user": "postgres",
      "password": "your_password"
    }

---

## Returns

True if connection succeeds. False on any error.
"""

description = """
Tests a PostgreSQL connection by connecting with provided credentials and fetching the
server version. Returns True on success, False on any error. Use as a workflow gate
to validate database connectivity before running data operations.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Database",
    "tags": ["postgresql", "connection", "test", "health-check", "database"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
