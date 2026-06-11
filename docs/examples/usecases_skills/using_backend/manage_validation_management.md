<operator/action/doc pending>

import json
import yaml
from datetime import datetime
from html import escape
import psycopg2
import sys
import requests
import os

def initialize(task):
    """Initialize database connection."""
    conn_config = task.get('connection', {})
    return psycopg2.connect(
        host=conn_config.get('host'),
        port=conn_config.get('port'),
        database=conn_config.get('database'),
        user=conn_config.get('user'),
        password=conn_config.get('password')
    )

def run(task, conn):
    """Execute validation checks."""
    return main(task.get('payload', ''), conn, task)

def check_completion(task, conn, run_details):
    """Check completion."""
    return {'status': 'success'}

def finish(task, conn, completion, run_details):
    """Cleanup."""
    if conn:
        conn.close()

def main(payload, connection, task_object):
    """
    SQL Validation Reports Operator
    Reads validation config, runs SQL checks, renders HTML report, saves to DB and catalog.
    """
    try:
        # Parse config from payload
        if isinstance(payload, str):
            try:
                config = yaml.safe_load(payload)
                if config is None:
                    config = {}
            except yaml.YAMLError as ye:
                raise ValueError(f"YAML parsing failed: {str(ye)}")
        else:
            config = payload
        
        cursor = connection.cursor()
        
        logical_date = datetime.now().strftime('%Y-%m-%d')
        partition = 'default'
        
        # Get output table name and parent laui
        output_table = config.get('output_table', 'validation_reports')
        output_parent_laui = config.get('output_parent_laui')
        
        # Create output table
        try:
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {output_table} (
                id SERIAL PRIMARY KEY,
                report_date DATE,
                partition VARCHAR(255),
                checks_total INTEGER,
                checks_passed INTEGER,
                checks_failed INTEGER,
                html_content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
            cursor.execute(create_table_sql)
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise ValueError(f"Failed to create output table: {str(e)}")
        
        # Run validation checks
        queries = config.get('queries', [])
        results = []
        checks_passed = 0
        checks_failed = 0
        
        for i, query_config in enumerate(queries):
            check_name = query_config.get('name', f'Check {i+1}')
            sql = query_config.get('sql', '')
            severity = query_config.get('severity', 'info')
            pass_condition = query_config.get('pass_condition', 'true')
            display = query_config.get('display', 'scalar')
            description = query_config.get('description', '')
            
            try:
                # Create fresh cursor for each query to avoid transaction issues
                query_cursor = connection.cursor()
                query_cursor.execute(sql)
                rows = query_cursor.fetchall()
                cols = [desc[0] for desc in query_cursor.description] if query_cursor.description else []
                query_cursor.close()
                connection.commit()  # Commit after each successful query
                
                condition_context = {'row_count': len(rows)}
                if len(rows) == 1 and len(cols) == 1:
                    condition_context[cols[0]] = rows[0][0]
                
                passed = eval(pass_condition, {"__builtins__": {}}, condition_context)
                
                if severity in ['critical', 'warning']:
                    if passed:
                        checks_passed += 1
                    else:
                        checks_failed += 1
                
                results.append({
                    'name': check_name,
                    'description': description,
                    'severity': severity,
                    'passed': passed,
                    'display': display,
                    'row_count': len(rows)
                })
                
            except Exception as e:
                # Rollback failed query and continue
                try:
                    connection.rollback()
                except:
                    pass
                
                results.append({
                    'name': check_name,
                    'description': description,
                    'severity': severity,
                    'passed': False,
                    'display': display,
                    'error': str(e)
                })
                if severity in ['critical', 'warning']:
                    checks_failed += 1
        
        checks_total = len(queries)
        
        # Generate HTML report
        report_title = config.get('report_title', 'Validation Report')
        html_report = generate_html_report(
            report_title, logical_date, checks_passed, checks_failed, checks_total, results
        )
        
        # Write to database
        try:
            insert_cursor = connection.cursor()
            insert_sql = f"""
            INSERT INTO {output_table} (report_date, partition, checks_total, checks_passed, checks_failed, html_content)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            insert_cursor.execute(insert_sql, (logical_date, partition, checks_total, checks_passed, checks_failed, html_report))
            connection.commit()
            insert_cursor.close()
        except Exception as e:
            connection.rollback()
            raise ValueError(f"Failed to insert report: {str(e)}")
        
        # Send HTML report to catalog API if parent_laui is provided
        if output_parent_laui:
            send_report_to_catalog(html_report, report_title, output_parent_laui, task_object)
        
        cursor.close()
        
        return {
            'status': 'success',
            'execution_type': 'sync',
            'result': {
                'report_title': report_title,
                'checks_total': checks_total,
                'checks_passed': checks_passed,
                'checks_failed': checks_failed,
                'output_table': output_table,
                'catalog_saved': bool(output_parent_laui)
            }
        }
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)} | {traceback.format_exc()}"
        return {
            'status': 'failed',
            'execution_type': 'sync',
            'result': None,
            'error': error_msg
        }

def send_report_to_catalog(html_content, report_title, output_parent_laui, task_object):
    """
    Send HTML report to catalog API as html_report item.
    
    Args:
        html_content: HTML report content
        report_title: Report title
        output_parent_laui: Parent laui for the report
        task_object: Task object containing user_access_token
    """
    try:
        user_access_token = task_object.get('user_access_token')
        
        if not user_access_token:
            print(f"Warning: user_access_token not found, skipping catalog upload")
            return
        
        api_url = f"http://backend:8000/api/v1/catalog/create"
        
        headers = {
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        }
        
        # Generate unique report name with timestamp
        report_name = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        payload = {
            "item_type": "html_report",
            "name": report_name,
            "description": report_title,
            "html": html_content,
            "parent_laui": output_parent_laui
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print(f"Successfully sent report to catalog: {report_name}")
        else:
            print(f"Catalog API error {response.status_code}: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error sending report to catalog API: {str(e)}")
    except Exception as e:
        print(f"Unexpected error sending report to catalog: {str(e)}")

def generate_html_report(title, date, passed, failed, total, results):
    """Generate a styled HTML report of validation results."""
    overall_status = 'pass' if failed == 0 else 'fail'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{escape(title)}</title>
    <style>
        body {{ font-family: sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ margin: 0 0 10px 0; }}
        .badge {{ padding: 8px 16px; border-radius: 20px; color: white; font-weight: bold; }}
        .pass {{ background: #28a745; }}
        .fail {{ background: #dc3545; }}
        .check-item {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid; }}
        .critical {{ border-color: #dc3545; }}
        .warning {{ border-color: #fd7e14; }}
        .info {{ border-color: #0dcaf0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{escape(title)}</h1>
        <p>Generated {escape(date)}</p>
        <div class="badge {overall_status}">{passed} of {total} checks passed</div>"""
    
    for result in results:
        severity = result.get('severity', 'info')
        passed_txt = 'PASS' if result.get('passed') else 'FAIL'
        html += f"""\n        <div class="check-item {severity}">
            <strong>{escape(result.get('name', 'Check'))}</strong> [{severity.upper()}]: {passed_txt}"""
        if result.get('description'):
            html += f"<br/><small>{escape(result.get('description'))}</small>"
        if 'error' in result:
            html += f"<br/><small style='color: red'>Error: {escape(result.get('error'))}</small>"
        html += "\n        </div>"
    
    html += f"""\n        <p style='font-size: 12px; color: #999;'>Generated at {datetime.now().isoformat()}</p>
    </div>
</body>
</html>"""
    return html


----

report_title: 'Daily Sales Validation'
output_table: 'validation_reports'
output_parent_laui: '69b8a2f9ea73365bc5ffabe9'

queries:
  - name: 'Row count check'
    description: 'Ensures fact_sales_daily has data'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Null check — sale_amount'
    description: 'Finds rows where sale_amount is null'
    sql: "SELECT COUNT(*) AS null_count FROM fact_sales_daily WHERE sale_amount IS NULL"
    severity: critical
    pass_condition: 'null_count == 0'
    display: scalar

  - name: 'Negative amount check'
    description: 'Finds rows with negative sale amounts (data quality issue)'
    sql: "SELECT COUNT(*) AS negative_count FROM fact_sales_daily WHERE sale_amount < 0"
    severity: warning
    pass_condition: 'negative_count == 0'
    display: scalar

  - name: 'Column count audit'
    description: 'Verifies expected columns exist'
    sql: "SELECT column_name FROM information_schema.columns WHERE table_name = 'fact_sales_daily' ORDER BY column_name"
    severity: info
    pass_condition: 'row_count > 0'
    display: count
