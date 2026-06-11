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
operator_type = "python"

codeblock = {"main.py": '''
import psycopg2
import requests
import os
import json
import re
from src.common.logger.logger import log_info, log_error


def _strip_code_fences(text):
    text = text.strip()
    for prefix in ['```sql', '```html', '```']:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
            break
    return text


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get('connection', {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        db_host = connection.get('host')
        db_port = connection.get('port', 5432)
        db_name = connection.get('database')
        db_user = connection.get('user')
        db_password = connection.get('password')
        log_info('task', 'initialize', 'connecting', f'host={db_host} port={db_port} db={db_name} user={db_user}')
        conn = psycopg2.connect(host=db_host, port=int(db_port), database=db_name, user=db_user, password=db_password)
        log_info('task', 'initialize', 'connected', 'PostgreSQL connection established')
        return conn
    except psycopg2.OperationalError as e:
        log_error('task', 'initialize', 'connection_failed', f'OperationalError: {str(e)}')
        raise
    except Exception as e:
        log_error('task', 'initialize', 'init_failed', f'Error: {str(e)}')
        raise


def run(least_action_task_object, client):
    try:
        connection = least_action_task_object.get('connection', {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        raw_payload = least_action_task_object.get('payload', '{}')
        if isinstance(raw_payload, str):
            payload = json.loads(raw_payload)
        else:
            payload = raw_payload

        source_table_name = payload.get('source_table_name', '')
        chat_prompt = payload.get('chat_prompt', '')
        parent_laui = payload.get('parent_laui', '')
        user_access_token = least_action_task_object.get('user_access_token', '') or payload.get('user_access_token', '')

        claude_api_key = connection.get('claude_api_key', '')
        claude_model = connection.get('claude_model', 'claude-haiku-4-5-20251001')
        claude_token_limit = int(connection.get('claude_token_limit', 4096))

        if not source_table_name:
            log_error('task', 'run', 'missing_table', 'source_table_name is required in payload')
            return {'status': 'failed', 'execution_type': 'sync', 'result': 'source_table_name is required'}

        if not claude_api_key:
            log_error('task', 'run', 'missing_key', 'claude_api_key is required in connection')
            return {'status': 'failed', 'execution_type': 'sync', 'result': 'claude_api_key is required'}

        log_info('task', 'run', 'params', f'table={source_table_name} prompt={chat_prompt[:60]}')

        cursor = client.cursor()

        if '.' in source_table_name:
            schema_name, table_only = source_table_name.split('.', 1)
        else:
            schema_name = 'public'
            table_only = source_table_name

        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position
        """, (schema_name, table_only))
        schema_rows = cursor.fetchall()

        if not schema_rows:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s ORDER BY ordinal_position
            """, (table_only,))
            schema_rows = cursor.fetchall()

        if not schema_rows:
            log_error('task', 'run', 'table_not_found', f'Table {source_table_name} not found')
            cursor.close()
            return {'status': 'failed', 'execution_type': 'sync', 'result': f'Table {source_table_name} not found'}

        log_info('task', 'run', 'schema_ok', f'{len(schema_rows)} columns found')
        table_definition = [f"{r[0]} {r[1]} {'NULL' if r[2]=='YES' else 'NOT NULL'}" for r in schema_rows]

        cursor.execute(f'SELECT * FROM {source_table_name} LIMIT 5')
        sample_rows = cursor.fetchall()
        col_names = [d[0] for d in cursor.description]
        sample_data = [dict(zip(col_names, [str(v) if v is not None else None for v in row])) for row in sample_rows]

        claude_headers = {'x-api-key': claude_api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'}
        system_prompt = 'You are an expert SQL and data analyst. Return only raw SQL or raw HTML as instructed. No markdown, no code fences, no explanation.'

        sql_prompt = f"""Generate a PostgreSQL SQL query for the request below. Return ONLY the raw SQL — no markdown, no code fences, no comments, no explanation.

REQUEST: {chat_prompt}
TABLE: {source_table_name}
SCHEMA:
{chr(10).join(table_definition)}
SAMPLE:
{json.dumps(sample_data, indent=2)}"""

        log_info('task', 'run', 'claude_sql_call', 'Calling Claude for SQL')
        r = requests.post('https://api.anthropic.com/v1/messages', headers=claude_headers,
                          json={'model': claude_model, 'max_tokens': claude_token_limit, 'system': system_prompt,
                                'messages': [{'role': 'user', 'content': sql_prompt}]}, timeout=60)

        if r.status_code != 200:
            log_error('task', 'run', 'claude_sql_error', f'HTTP {r.status_code}: {r.text}')
            cursor.close()
            return {'status': 'failed', 'execution_type': 'sync', 'result': f'Claude SQL error {r.status_code}'}

        generated_sql = _strip_code_fences(r.json().get('content', [{}])[0].get('text', ''))
        log_info('task', 'run', 'generated_sql', f'SQL={generated_sql}')

        if not generated_sql:
            log_error('task', 'run', 'no_sql', 'Empty SQL returned by Claude')
            cursor.close()
            return {'status': 'failed', 'execution_type': 'sync', 'result': 'No SQL generated'}

        cursor.execute(generated_sql)
        report_rows = cursor.fetchall()
        report_cols = [d[0] for d in cursor.description]
        report_data = [dict(zip(report_cols, [str(v) if v is not None else None for v in row])) for row in report_rows]
        log_info('task', 'run', 'query_done', f'{len(report_data)} rows returned')
        cursor.close()

        html_prompt = f"""Generate a professional standalone HTML report. Return ONLY the raw HTML starting with <!DOCTYPE html> — no markdown, no code fences, no explanation.

USER REQUEST: {chat_prompt}
TABLE: {source_table_name}
SQL USED: {generated_sql}
COLUMNS: {json.dumps(report_cols)}
DATA ({len(report_data)} rows): {json.dumps(report_data[:50], indent=2)}

Requirements:
- Start with <!DOCTYPE html> immediately — first character
- Use ONLY HTML and CSS — absolutely NO JavaScript, NO <script> tags, NO event handlers
- Modern styling with <style> block: clean fonts, alternating row colors via CSS tr:nth-child(even), color header
- Show all data in a well-formatted <table>
- Include title, row count, and generation timestamp in footer"""

        log_info('task', 'run', 'claude_html_call', 'Calling Claude for HTML')
        r2 = requests.post('https://api.anthropic.com/v1/messages', headers=claude_headers,
                           json={'model': claude_model, 'max_tokens': claude_token_limit * 2, 'system': system_prompt,
                                 'messages': [{'role': 'user', 'content': html_prompt}]}, timeout=60)

        if r2.status_code != 200:
            log_error('task', 'run', 'claude_html_error', f'HTTP {r2.status_code}: {r2.text}')
            return {'status': 'failed', 'execution_type': 'sync', 'result': f'Claude HTML error {r2.status_code}'}

        html_content = _strip_code_fences(r2.json().get('content', [{}])[0].get('text', ''))
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r"\\s+on\\w+=['\\\"][^'\\\"]*['\\\"]", '', html_content)

        log_info('task', 'run', 'html_ok', f'HTML length={len(html_content)} doctype={html_content[:15]!r}')

        if not html_content.upper().startswith('<!DOCTYPE'):
            log_error('task', 'run', 'bad_html', f'Does not start with DOCTYPE: {html_content[:200]}')
            return {'status': 'failed', 'execution_type': 'sync', 'result': 'Invalid HTML generated'}

        backend_host = os.getenv('BACKEND_HOST', 'backend')
        api_url = f'http://{backend_host}:8000/api/v1/catalog/create'
        headers = {'Cookie': f'frontend_token={user_access_token}', 'Content-Type': 'application/json'}
        catalog_payload = {'item_type': 'html_report', 'name': chat_prompt[:100],
                           'description': chat_prompt[:100], 'html': html_content, 'parent_laui': parent_laui}

        log_info('task', 'run', 'catalog_create', f'Creating html_report: {chat_prompt[:60]}')
        resp = requests.post(api_url, json=catalog_payload, headers=headers, timeout=30)
        log_info('task', 'run', 'catalog_response', f'Status={resp.status_code} body={resp.text[:200]}')

        if resp.status_code in [200, 201]:
            log_info('task', 'run', 'success', 'HTML report created successfully')
            return {'status': 'success', 'execution_type': 'sync', 'result': 'Report created'}
        else:
            log_error('task', 'run', 'catalog_failed', f'{resp.status_code} {resp.text}')
            return {'status': 'failed', 'execution_type': 'sync', 'result': f'Catalog create failed {resp.status_code}'}

    except psycopg2.Error as e:
        log_error('task', 'run', 'db_error', f'PostgreSQL error: {str(e)}')
        return {'status': 'failed', 'execution_type': 'sync', 'result': f'DB error: {str(e)}'}
    except Exception as e:
        log_error('task', 'run', 'unexpected_error', f'Error: {str(e)}')
        return {'status': 'failed', 'execution_type': 'sync', 'result': f'Error: {str(e)}'}


def check_completion(least_action_task_object, client, run_details):
    return {'status': 'success', 'message': 'Synchronous operation completed', 'output': run_details}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        if client:
            client.close()
            log_info('task', 'finish', 'closed', 'PostgreSQL connection closed')
    except Exception as e:
        log_error('task', 'finish', 'close_error', f'Error closing connection: {str(e)}')
'''}

bashblock = {"main.sh": """
#!/bin/bash
pip install psycopg2-binary requests
"""}

connection = {
    "host": "host.docker.internal",
    "port": 5432,
    "database": "dbtdb",
    "user": "postgres",
    "password": "your_password_here",
    "claude_api_key": "sk-ant-...",
    "claude_model": "claude-haiku-4-5-20251001",
    "claude_token_limit": 4096
}

payload = """
{
  "source_table_name": "mart_attendance_summary",
  "chat_prompt": "Generate a comprehensive daily attendance summary report for the latest date. Show present vs absent counts by department, flag badges still on campus, early exits, and those with 3+ consecutive absence streaks. Include an overall attendance percentage.",
  "parent_laui": "<folder.report laui>"
}
"""

prompt = (
    "Queries a PostgreSQL table, uses Claude AI to generate a SQL query from a natural language prompt, "
    "executes the query, then uses Claude to generate a styled HTML report. "
    "Strips all JavaScript before saving the report as an html_report asset in the LeastAction catalog. "
    "Connection fields: host, port, database, user, password, claude_api_key, claude_model, claude_token_limit. "
    "Payload fields: source_table_name, chat_prompt, parent_laui."
)

install_docs = """# PostgresClaudeReportDebug — Install Guide

## Dependencies

    pip install psycopg2-binary
    pip install requests

## Connection Setup

| Field | Description |
|---|---|
| `host` | PostgreSQL host (use `host.docker.internal` if LeastAction runs in Docker) |
| `port` | PostgreSQL port (default 5432) |
| `database` | Database name |
| `user` | Database user |
| `password` | Database password |
| `claude_api_key` | Anthropic Claude API key (`sk-ant-...`) |
| `claude_model` | Claude model ID (default: `claude-haiku-4-5-20251001`) |
| `claude_token_limit` | Max tokens per Claude call (default: 4096) |
"""

guide_docs = """# PostgresClaudeReportDebug — Operator Guide

## What it does

1. Connects to PostgreSQL and reads the schema of `source_table_name`
2. Sends schema + sample rows to Claude with `chat_prompt` to generate a SQL query
3. Executes the generated SQL and fetches results
4. Sends results back to Claude to generate a styled standalone HTML report
5. Strips any `<script>` tags or inline event handlers from the HTML
6. Saves the HTML as an `html_report` catalog item under `parent_laui`

---

## Connection

    {
      "host": "host.docker.internal",
      "port": 5432,
      "database": "dbtdb",
      "user": "postgres",
      "password": "...",
      "claude_api_key": "sk-ant-...",
      "claude_model": "claude-haiku-4-5-20251001",
      "claude_token_limit": 4096
    }

---

## Payload

    {
      "source_table_name": "mart_attendance_summary",
      "chat_prompt": "Generate a comprehensive daily attendance summary...",
      "parent_laui": "<folder.report laui>"
    }

---

## Notes

- `user_access_token` is injected automatically by the LeastAction framework
- `parent_laui` must point to a `folder.report` item — not a workflow folder
- Supports schema-qualified table names (`schema.table`)
- HTML reports with `<script>` tags are blocked by LeastAction — this operator strips them automatically
"""

description = """
Connects to PostgreSQL, uses Claude AI to generate a SQL query from a natural language prompt,
executes the query, then uses Claude to generate a styled HTML report from the results.
Strips all JavaScript and saves the report as an html_report asset in the LeastAction catalog.
Designed for flat/wide tables (e.g. badge attendance marts). Use PostgresqlGenerateHtmlTableReport
for key-value metric tables (e.g. fact_product_agg_daily).
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Reporting",
    "tags": ["postgresql", "claude", "html", "report", "ai", "attendance", "analytics"],
    "airflow_equivalent": "BashOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
