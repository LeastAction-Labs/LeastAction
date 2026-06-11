# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock ={"main.py": '''
import psycopg2
import requests
import os
import json
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, parent_laui, source_table_name, chat_prompt, **kwargs):
    """
    Dynamically generates reporting queries and HTML reports using Claude AI.

    This action:
    1. Connects to PostgreSQL and retrieves table definition
    2. Queries sample data from the specified table
    3. Sends table schema and sample data to Claude AI with the chat prompt
    4. Claude generates an appropriate reporting SQL query
    5. Executes the generated query
    6. Sends query results back to Claude to generate professional HTML report
    7. Creates html_report asset in catalog

    Parameters:
        least_action_action_object (dict): Action object containing connection and metadata
        parent_laui (str): Parent LAUI for the html_report item
        source_table_name (str): PostgreSQL table name to analyze and report on
        chat_prompt (str): Natural language prompt describing the desired report

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info("action", "run", "start",
                 f"Starting dynamic PostgreSQL to HTML report with Claude AI for table: {source_table_name}")

        user_access_token = least_action_action_object.get('user_access_token')
        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in least_action_action_object")
            return False

        log_info("action", "run", "validate_inputs", f"Parent LAUI: {parent_laui}, Table: {source_table_name}")

        connection = least_action_action_object.get('connection', {})

        db_host = connection.get('host')
        db_port = connection.get('port', 5432)
        db_name = connection.get('database')
        db_user = connection.get('user')
        db_password = connection.get('password')
        claude_api_key = connection.get('claude_api_key')
        claude_model = connection.get('claude_model', 'claude-3-5-sonnet-20241022')
        claude_token_limit = connection.get('claude_token_limit', 4096)

        if not all([db_host, db_name, db_user, db_password]):
            log_error("action", "run", "missing_connection", "Missing required PostgreSQL connection details")
            return False

        if not claude_api_key:
            log_error("action", "run", "missing_claude_key", "Claude API key not found in connection")
            return False

        log_info("action", "run", "connect_postgresql", "Connect postgresql")

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        cursor = conn.cursor()
        log_info("action", "run", "connected", "Successfully connected to PostgreSQL")

        log_info("action", "run", "get_table_definition", f"Retrieving table definition for {source_table_name}")

        schema_query = """
                       SELECT column_name, \
                              data_type, \
                              character_maximum_length, \
                              is_nullable, \
                              column_default
                       FROM information_schema.columns
                       WHERE table_name = %s
                       ORDER BY ordinal_position \
                       """

        cursor.execute(schema_query, (source_table_name,))
        schema_rows = cursor.fetchall()

        if not schema_rows:
            log_error("action", "run", "table_not_found", f"Table {source_table_name} not found or has no columns")
            cursor.close()
            conn.close()
            return False

        table_definition = []
        for row in schema_rows:
            col_name, data_type, max_length, nullable, default = row
            col_def = f"{col_name} {data_type}"
            if max_length:
                col_def += f"({max_length})"
            col_def += f" {'NULL' if nullable == 'YES' else 'NOT NULL'}"
            if default:
                col_def += f" DEFAULT {default}"
            table_definition.append(col_def)

        log_info("action", "run", "table_definition_retrieved", f"Retrieved {len(table_definition)} columns")

        log_info("action", "run", "get_sample_data", f"Retrieving sample data from {source_table_name}")

        sample_query = f"SELECT * FROM {source_table_name} LIMIT 5"
        cursor.execute(sample_query)
        sample_rows = cursor.fetchall()

        column_names = [desc[0] for desc in cursor.description]

        sample_data = []
        for row in sample_rows:
            sample_data.append(dict(zip(column_names, [str(val) if val is not None else None for val in row])))

        log_info("action", "run", "sample_data_retrieved", f"Retrieved {len(sample_data)} sample rows")

        log_info("action", "run", "prepare_claude_prompt", "Preparing prompt for Claude AI to generate SQL query")

        system_prompt = """You are Least Action AI, an expert AI assistant and exceptional distinguished software developer with vast knowledge across Python and its libraries, frameworks, cloud services, data orchestration, and best practices. You generate actions for LeastAction, an innovative AI-powered data management platform designed to streamline workflows and enhance team productivity - the most efficient way to manage orchestration of any number of jobs on any system, without needing provider updates."""

        sql_prompt = f"""Given the following PostgreSQL table definition and sample data, generate a SQL query that fulfills this reporting requirement:

USER REQUEST: {chat_prompt}

TABLE NAME: {source_table_name}

TABLE DEFINITION:
{chr(10).join(table_definition)}

SAMPLE DATA (first 5 rows):
{json.dumps(sample_data, indent=2)}

Return ONLY a valid PostgreSQL SQL query that addresses the user's request. Do not include any explanation, markdown formatting, or code blocks - just the raw SQL query.

IMPORTANT:
- Only query the table: {source_table_name}
- Ensure the query is valid PostgreSQL syntax
- Use appropriate aggregations, filters, and ordering based on the request
- Keep the query efficient and focused on the reporting requirement
"""

        log_info("action", "run", "call_claude_api", "Sending request to Claude AI for SQL generation")

        claude_headers = {
            "x-api-key": claude_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        claude_payload = {
            "model": claude_model,
            "max_tokens": claude_token_limit,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": sql_prompt
                }
            ]
        }

        claude_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=claude_headers,
            json=claude_payload,
            timeout=60
        )

        if claude_response.status_code != 200:
            log_error("action", "run", "claude_api_error", f"Claude API returned status {claude_response.status_code}: {claude_response.text}")
            cursor.close()
            conn.close()
            return False

        log_info("action", "run", "claude_response_received", "Successfully received SQL query from Claude AI")

        claude_result = claude_response.json()
        generated_sql = claude_result.get("content", [{}])[0].get("text", "").strip()

        if not generated_sql:
            log_error("action", "run", "no_sql_generated", "Claude did not generate a SQL query")
            cursor.close()
            conn.close()
            return False

        log_info("action", "run", "execute_generated_query", "Execute generated query")

        cursor.execute(generated_sql)
        report_rows = cursor.fetchall()
        report_columns = [desc[0] for desc in cursor.description]

        log_info("action", "run", "query_executed", "Query executed")

        cursor.close()
        conn.close()

        report_data = []
        for row in report_rows:
            report_data.append(dict(zip(report_columns, [str(val) if val is not None else None for val in row])))

        log_info("action", "run", "request_html_from_claude", "Requesting HTML report generation from Claude AI")

        html_prompt = f"""Generate a professional, visually appealing HTML report based on the following data:

USER REQUEST: {chat_prompt}

SOURCE TABLE: {source_table_name}

SQL QUERY EXECUTED:
{generated_sql}

COLUMN NAMES:
{json.dumps(report_columns)}

QUERY RESULTS ({len(report_data)} rows):
{json.dumps(report_data, indent=2)}

Please create a complete, standalone HTML document that:
1. Has a clear, descriptive title based on the user's request
2. Includes professional, modern styling (use beautiful CSS, good color schemes, responsive design)
3. Displays the data in an appropriate format (table, or other visualization as appropriate)
4. Shows metadata like the source table, row count, and generation timestamp
5. Optionally shows the SQL query that was executed in a formatted code block
6. Is visually appealing, easy to read, and professionally formatted
7. Uses modern web design principles

Return ONLY the complete HTML document, starting with <!DOCTYPE html> and ending with </html>. Do not include any markdown code blocks or explanations - just the raw HTML.
"""

        html_payload = {
            "model": claude_model,
            "max_tokens": claude_token_limit * 2,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": html_prompt
                }
            ]
        }

        html_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=claude_headers,
            json=html_payload,
            timeout=60
        )

        if html_response.status_code != 200:
            log_error("action", "run", "claude_html_error", "Claude html error",f"Claude API returned status {html_response.status_code}: {html_response.text}")
            return False

        html_result = html_response.json()
        html_content = html_result.get("content", [{}])[0].get("text", "").strip()
        
        if not html_content:
            log_error("action", "run", "invalid_html", "Claude returned empty HTML content")
            return False
        
        log_info("action", "run", "html_content_preview", "Html content preview")
        
        if html_content.startswith("```html"):
            html_content = html_content[7:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            html_content = html_content.strip()
            log_info("action", "run", "cleaned_markdown", "Removed markdown code block wrapper from HTML")
        elif html_content.startswith("```"):
            html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            html_content = html_content.strip()
            log_info("action", "run", "cleaned_markdown", "Removed markdown code block wrapper from HTML")
        
        if not html_content.upper().startswith("<!DOCTYPE"):
            log_error("action", "run", "invalid_html", "Invalid html")
            return False

        log_info("action", "run", "html_generated", f"Successfully generated HTML report from Claude AI")

        report_description = chat_prompt[:100]

        backend_host = os.getenv("BACKEND_HOST", "backend")
        api_url = f"http://{backend_host}:8000/api/v1/catalog/create"

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "item_type": "html_report",
            "name": report_description,
            "description": report_description,
            "html": html_content,
            "parent_laui": parent_laui
        }

        log_info("action", "run", "create_html_report", f"Creating html_report asset: {report_description}")

        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code in [200, 201]:
            log_info("action", "run", "success", f"Successfully created html_report asset")
            return True
        else:
            log_error("action", "run", "create_failed", "Create failed",f"Failed to create html_report. Status: {response.status_code}, Response: {response.text}")
            return False

    except psycopg2.OperationalError as e:
        log_error("action", "run", "connection_error", f"PostgreSQL connection error: {str(e)}")
        return False
    except psycopg2.ProgrammingError as e:
        log_error("action", "run", "query_error", f"PostgreSQL query error: {str(e)}")
        return False
    except psycopg2.Error as e:
        log_error("action", "run", "database_error", f"PostgreSQL error: {str(e)}")
        return False
    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timeout")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
'''
}
bashblock = {}
action_variables= {

        "parent_laui": "699b9c2b30bf86a5a20cb16b",
        "source_table_name": "fact_sales_daily",
        "chat_prompt": "Show me top 10 customers by revenue for the past 10 days"
}
connection = {}

prompt = (
    "Query a PostgreSQL table, send the data to Claude via the LeastAction chat API with a natural language prompt, "
    "render the response as an HTML report, and publish the report as a catalog asset. "
    "Action variables: parent_laui (catalog folder), source_table_name (PostgreSQL table to query), "
    "chat_prompt (natural language question about the data). "
    "Connection: PostgreSQL credentials (host, port, database, user, password) plus claude_api_key and claude_model. "
    "Returns True on successful report creation."
)

install_docs = """# PostgresqlToClaudeChatToHtmlReportToAsset — Install Guide

## Dependencies

    pip install psycopg2-binary
    pip install requests
    pip install anthropic   (or uses LeastAction chat API)

## Connection Requirements

Requires both PostgreSQL credentials AND Claude API settings:

    {
      "host": "localhost", "port": 5432,
      "database": "mydb", "user": "postgres", "password": "...",
      "claude_api_key": "...",
      "claude_model": "claude-haiku-4-5-20251001"
    }
"""

guide_docs = """# PostgresqlToClaudeChatToHtmlReportToAsset — Action Guide

## What it does

End-to-end pipeline: queries a PostgreSQL table, sends the result with a natural language
prompt to Claude, renders the AI response as an HTML report, and publishes it to the
LeastAction catalog under parent_laui.

---

## Action Variables

    {
      "parent_laui": "catalog_folder_laui",
      "source_table_name": "fact_sales_daily",
      "chat_prompt": "Show top 10 customers by revenue for the past 10 days"
    }

---

## Returns

True if the report was created and published. False on any error.
"""

description = """
Queries a PostgreSQL table and sends the results with a natural language prompt to Claude.
Renders the AI response as an HTML report and publishes it to the LeastAction catalog.
Combines database query, AI analysis, and catalog publishing in a single action.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL, Anthropic",
    "category": "AI Reporting",
    "tags": ["postgresql", "claude", "ai", "html", "report", "catalog", "chat", "analysis"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
