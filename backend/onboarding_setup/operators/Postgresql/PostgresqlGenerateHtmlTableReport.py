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

codeblock= {"main.py":''' 
"""
PostgreSQL HTML Report Generator Operator

Generates styled HTML reports from PostgreSQL database based on configuration.
Supports dynamic metric templating, implicit grouping detection, and per-metric styling.
"""

import psycopg2
import pandas as pd
from datetime import datetime
import json
import re
from pathlib import Path
import requests
import os
from src.common.logger.logger import log_info, log_error


def initialize(least_action_task_object):
    """
    Initialize PostgreSQL database connection.

    Args:
        least_action_task_object: Task object containing connection details

    Returns:
        psycopg2.connection: Database connection object
    """
    try:
        connection = least_action_task_object.get('connection', {})
        task_laui = least_action_task_object.get('laui')

        log_info("task", "initialize", "extracting_connection_details", "Extracting PostgreSQL connection details")

        # Extract connection parameters
        host = connection.get('host', 'localhost')
        port = connection.get('port', 5432)
        database = connection.get('database', 'postgres')
        user = connection.get('user', 'postgres')
        password = connection.get('password', '')

        log_info("task", "initialize", "creating_connection", "Creating PostgreSQL connection")

        # Create database connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

        log_info("task", "initialize", "connection_successful", "Successfully connected to PostgreSQL")

        return conn

    except psycopg2.OperationalError as e:
        log_error(
            "task",
            "initialize",
            "connection_error",
            f"PostgreSQL connection error: {str(e)}"
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


def load_data_from_database(conn, query_config):
    """
    Load data from database based on query configuration.

    Args:
        conn: PostgreSQL connection object
        query_config: Query configuration dictionary

    Returns:
        pd.DataFrame: Loaded data
    """
    try:
        table = query_config.get('table', 'fact_product_agg_daily')
        date_filter = query_config.get('date_filter', 'TRUE')
        limit = query_config.get('limit')

        log_info(
            "task",
            "run",
            "building_query",
            f"Building SQL query for table: {table}"
        )

        sql = f"""
            SELECT 
                date,
                dim_key,
                dim_key_grouping,
                dim_value,
                metric_key,
                metric_value,
                cube_level
            FROM {table}
            WHERE {date_filter}
        """

        if limit:
            sql += f" LIMIT {limit}"

        log_info(
            "task",
            "run",
            "executing_query",
            f"Executing query: SELECT FROM {table} WHERE {date_filter}"
        )

        df = pd.read_sql(sql, conn)

        log_info(
            "task",
            "run",
            "data_loaded",
            f"Successfully loaded {len(df)} rows from database"
        )

        log_info(
            "task",
            "run",
            "data_summary",
            f"Data shape: {df.shape[0]} rows, {df.shape[1]} columns | Unique groupings: {df['dim_key_grouping'].nunique()} | Unique metrics: {df['metric_key'].nunique()}"
        )

        return df

    except Exception as e:
        log_error(
            "task",
            "run",
            "query_execution_error",
            f"Error executing query: {str(e)}"
        )
        raise


def format_cell_value(value, format_string):
    """
    Format a cell value using a format string.

    Args:
        value: Value to format
        format_string: Format string template

    Returns:
        str: Formatted value
    """
    try:
        return format_string.format(value=value)
    except Exception:
        return str(value)


def pivot_kv_data_to_report(df, metric_template=None):
    """
    Pivot the key-value fact table data using dynamic template configuration.

    Args:
        df: Input DataFrame
        metric_template: List of metric template configurations

    Returns:
        tuple: (Pivoted DataFrame, Styling metadata dictionary)
    """
    try:
        log_info(
            "task",
            "run",
            "pivoting_data",
            "Starting data pivot operation"
        )

        df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        if metric_template is None:
            log_info(
                "task",
                "run",
                "no_template",
                "No metric template provided, using default pivot"
            )

            df['metric'] = df['dim_value'] + ' - ' + df['metric_key']
            pivot_table = df.pivot_table(
                index='metric',
                columns='date_str',
                values='metric_value',
                aggfunc='sum',
                fill_value=0
            )
            return pivot_table, {}

        filtered_data = []
        metric_order = []
        metric_styles = {}

        log_info(
            "task",
            "run",
            "processing_templates",
            f"Processing {len(metric_template)} metric templates"
        )

        for idx, template_item in enumerate(metric_template):
            display_name = template_item['display_name']
            dim_key_grouping_filter = template_item.get('dim_key_grouping')
            dim_value_filter = template_item.get('dim_value')
            metric_key_filter = template_item.get('metric_key')

            # Extract styling options
            cell_format = template_item.get('cell_format', '{value:,.2f}')
            cell_bg_color = template_item.get('cell_bg_color')
            cell_text_color = template_item.get('cell_text_color')
            text_bold = template_item.get('text_bold', False)
            text_italic = template_item.get('text_italic', False)
            text_size = template_item.get('text_size')

            log_info(
                "task",
                "run",
                "processing_template",
                f"Processing template {idx + 1}: {display_name}"
            )

            # DYNAMIC ROW DETECTION
            # '*' in the grouping key means "expand on this dimension" — one output row per distinct value
            show_details = False
            if dim_key_grouping_filter and '*' in dim_key_grouping_filter:
                show_details = True
                log_info(
                    "task",
                    "run",
                    "dynamic_row_detection",
                    f"Dynamic row expansion enabled for: {display_name}"
                )

            # Start with all data
            mask = pd.Series([True] * len(df))

            if metric_key_filter:
                mask &= (df['metric_key'] == metric_key_filter)

            if dim_key_grouping_filter is not None:
                if show_details:
                    # Convert pattern to regex:
                    #   '*'        → any non-placeholder value (not starting with 'dim_')
                    #   everything else → literal match
                    parts = dim_key_grouping_filter.split('::')
                    regex_parts = []
                    for part in parts:
                        if part == '*':
                            regex_parts.append(r'(?!dim_)[^:]+')
                        else:
                            regex_parts.append(re.escape(part))
                    pattern = '^' + '::'.join(regex_parts) + '$'
                    mask &= df['dim_key_grouping'].str.match(pattern)
                else:
                    mask &= (df['dim_key_grouping'] == dim_key_grouping_filter)

            if dim_value_filter is not None:
                mask &= (df['dim_value'] == dim_value_filter)
                show_details = False

            filtered_df = df[mask].copy()

            if len(filtered_df) > 0:
                if show_details and dim_value_filter is None:
                    # Detail rows
                    unique_dim_values = filtered_df['dim_value'].unique()

                    log_info(
                        "task",
                        "run",
                        "creating_detail_rows",
                        f"Creating {len(unique_dim_values)} detail rows for: {display_name}"
                    )

                    for dim_val in sorted(unique_dim_values):
                        detail_mask = filtered_df['dim_value'] == dim_val
                        detail_df = filtered_df[detail_mask].copy()
                        detail_grouped = detail_df.groupby('date_str')['metric_value'].sum().reset_index()
                        detail_metric_name = f"  {dim_val}"
                        detail_grouped['metric'] = detail_metric_name
                        filtered_data.append(detail_grouped)
                        metric_order.append(detail_metric_name)

                        metric_styles[detail_metric_name] = {
                            'cell_format': cell_format,
                            'cell_bg_color': cell_bg_color,
                            'cell_text_color': cell_text_color,
                            'text_bold': False,
                            'text_italic': text_italic,
                            'text_size': text_size
                        }

                    # Total row
                    total_grouped = filtered_df.groupby('date_str')['metric_value'].sum().reset_index()
                    total_metric_name = f"{display_name} (Total)"
                    total_grouped['metric'] = total_metric_name
                    filtered_data.append(total_grouped)
                    metric_order.append(total_metric_name)

                    metric_styles[total_metric_name] = {
                        'cell_format': cell_format,
                        'cell_bg_color': cell_bg_color,
                        'cell_text_color': cell_text_color,
                        'text_bold': True,
                        'text_italic': text_italic,
                        'text_size': text_size
                    }
                else:
                    # Single row
                    grouped = filtered_df.groupby('date_str')['metric_value'].sum().reset_index()
                    grouped['metric'] = display_name
                    filtered_data.append(grouped)
                    metric_order.append(display_name)

                    metric_styles[display_name] = {
                        'cell_format': cell_format,
                        'cell_bg_color': cell_bg_color,
                        'cell_text_color': cell_text_color,
                        'text_bold': text_bold,
                        'text_italic': text_italic,
                        'text_size': text_size
                    }
            else:
                log_info(
                    "task",
                    "run",
                    "no_data_for_template",
                    f"No data found for metric template: {display_name}"
                )

        if filtered_data:
            combined_df = pd.concat(filtered_data, ignore_index=True)
            pivot_table = combined_df.pivot_table(
                index='metric',
                columns='date_str',
                values='metric_value',
                aggfunc='sum',
                fill_value=0
            )
            existing_metrics = [m for m in metric_order if m in pivot_table.index]
            pivot_table = pivot_table.reindex(existing_metrics)

            log_info(
                "task",
                "run",
                "pivot_complete",
                f"Pivot table created: {pivot_table.shape[0]} metrics × {pivot_table.shape[1]} dates"
            )
        else:
            pivot_table = pd.DataFrame()
            log_info(
                "task",
                "run",
                "empty_pivot",
                "No metrics matched the template filters"
            )

        return pivot_table, metric_styles

    except Exception as e:
        log_error(
            "task",
            "run",
            "pivot_error",
            f"Error during pivot operation: {str(e)}"
        )
        raise


def generate_styled_html_table(pivot_table, metric_styles, report_style):
    """
    Generate HTML table with inline styling for each cell.

    Args:
        pivot_table: Pivoted DataFrame
        metric_styles: Styling metadata dictionary
        report_style: Report-level styling configuration

    Returns:
        str: HTML table string
    """
    try:
        if len(pivot_table) == 0:
            log_info(
                "task",
                "run",
                "empty_table",
                "No data to display in table"
            )
            return "<p>No data to display</p>"

        rs = report_style or {}
        border = rs.get('border_color', '#dddddd')
        even = rs.get('row_bg_color_even', '#f9f9f9')
        odd = rs.get('row_bg_color_odd', '#ffffff')

        # Emit ONE CSS class per distinct per-metric style (deduped) instead of
        # stamping a full inline style on every cell — a big table went from a
        # ~150-char <td style="…"> per cell to a ~10-char <td class="sN">, ~10x
        # smaller, which is what pushed the report over the catalog html cap.
        sig_to_class = {}
        metric_class = {}
        css_rules = []
        for m_name, st in (metric_styles or {}).items():
            props = []
            if st.get('cell_bg_color'):
                props.append(f"background-color:{st['cell_bg_color']}")
            if st.get('cell_text_color'):
                props.append(f"color:{st['cell_text_color']}")
            if st.get('text_bold'):
                props.append("font-weight:bold")
            if st.get('text_italic'):
                props.append("font-style:italic")
            if st.get('text_size'):
                props.append(f"font-size:{st['text_size']}")
            if not props:
                continue
            sig = ';'.join(props)
            cls = sig_to_class.get(sig)
            if cls is None:
                cls = f"s{len(sig_to_class)}"
                sig_to_class[sig] = cls
                css_rules.append(f".{cls}{{{sig}}}")
            metric_class[m_name] = cls

        style_block = (
            "<style>"
            f"td{{border:1px solid {border};padding:8px;text-align:right}}"
            "td.k{text-align:left;font-weight:bold}"
            f"tbody tr:nth-child(even){{background-color:{even}}}"
            f"tbody tr:nth-child(odd){{background-color:{odd}}}"
            + ''.join(css_rules)
            + "</style>"
        )

        parts = [style_block, '<table><thead><tr><th>Metric</th>']
        for col in pivot_table.columns:
            parts.append(f'<th>{col}</th>')
        parts.append('</tr></thead><tbody>')

        for metric_name, row in pivot_table.iterrows():
            fmt = (metric_styles or {}).get(metric_name, {}).get('cell_format', '{value:,.2f}')
            cls = metric_class.get(metric_name)
            cattr = f' class="{cls}"' if cls else ''
            parts.append('<tr>')
            parts.append(f'<td class="k">{metric_name}</td>')
            for value in row:
                parts.append(f'<td{cattr}>{format_cell_value(value, fmt)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')

        log_info("task", "run", "html_table_generated", "HTML table generated")

        return ''.join(parts)

    except Exception as e:
        log_error(
            "task",
            "run",
            "html_generation_error",
            f"Error generating HTML table: {str(e)}"
        )
        raise


def write_report_to_database(conn, pivot_table, metric_styles, output_table, report_title, report_style, output_parent_laui , least_action_task_object):
    """
    Write HTML report to database table and send to catalog API.

    Args:
        conn: PostgreSQL connection object
        pivot_table: Pivoted DataFrame
        metric_styles: Styling metadata dictionary
        output_table: Output table name
        report_title: Report title
        report_style: Report-level styling configuration
        least_action_task_object: Task object containing user_access_token

    Returns:
        str: Output table name
    """
    try:
        log_info(
            "task",
            "run",
            "generating_html_report",
            f"Generating HTML report to table: {output_table} - {report_title}"
        )

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_title}</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: {font_family};
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .report-container {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid {header_bg_color};
                    padding-bottom: 10px;
                }}
                .report-info {{
                    margin-bottom: 20px;
                    color: #666;
                    font-size: 14px;
                }}
                .config-note {{
                    background-color: #E3F2FD;
                    border-left: 4px solid #2196F3;
                    padding: 12px;
                    margin-bottom: 20px;
                    font-size: 13px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th {{
                    background-color: {header_bg_color};
                    color: {header_text_color};
                    padding: 12px;
                    text-align: right;
                    font-weight: bold;
                    border: 1px solid {border_color};
                }}
                th:first-child {{
                    text-align: left;
                }}
                tr:hover {{
                    background-color: {row_hover_color} !important;
                }}
                .footer {{
                    margin-top: 20px;
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <h1>{report_title}</h1>
                <div class="report-info">
                    <strong>Report Generated:</strong> {generation_time}<br>
                    <strong>Data Source:</strong> PostgreSQL Database (CUBE-transformed)<br>
                    <strong>Metrics Shown:</strong> {num_metrics} | <strong>Date Range:</strong> {num_dates} days
                </div>
                <div class="config-note">
                    <strong>💡 Dynamic Configuration:</strong> Report uses implicit grouping detection and per-metric styling.
                    No config updates needed when new dimension values are added!
                </div>
                {table_html}
                <div class="footer">
                    Generated by Dynamic Pivot Report System | Database-Driven Analytics
                </div>
            </div>
        </body>
        </html>
        """

        table_html = generate_styled_html_table(pivot_table, metric_styles, report_style)

        generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = html_template.format(
            report_title=report_title,
            generation_time=generation_time,
            num_metrics=len(pivot_table),
            num_dates=len(pivot_table.columns) if len(pivot_table) > 0 else 0,
            table_html=table_html,
            font_family=report_style.get('font_family', 'Arial, sans-serif'),
            header_bg_color=report_style.get('header_bg_color', '#4CAF50'),
            header_text_color=report_style.get('header_text_color', '#FFFFFF'),
            border_color=report_style.get('border_color', '#dddddd'),
            row_hover_color=report_style.get('row_hover_color', '#e8f5e9')
        )

        # Write to database table
        cursor = conn.cursor()

        # Serialize first-time table creation across concurrent report tasks.
        # `CREATE TABLE IF NOT EXISTS ... SERIAL` is NOT atomic: when several
        # reports target the same output_table and race on the initial create,
        # each session's IF NOT EXISTS check passes and each then tries to
        # create the implicit sequence, colliding on pg_class
        # ("duplicate key value violates unique constraint
        # pg_class_relname_nsp_index"). A transaction-level advisory lock keyed
        # on the table name lets only one creator run at a time; it is released
        # on commit/rollback below.
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (output_table,))

        # Create table if not exists
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {output_table} (
            id SERIAL PRIMARY KEY,
            report_title VARCHAR(500),
            html_content TEXT,
            generation_time TIMESTAMP,
            metrics_count INTEGER,
            date_range_count INTEGER
        )
        """
        cursor.execute(create_table_sql)
        
        # Insert report data
        insert_sql = f"""
        INSERT INTO {output_table} 
        (report_title, html_content, generation_time, metrics_count, date_range_count)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        generation_timestamp = datetime.now()
        metrics_count = len(pivot_table)
        date_range_count = len(pivot_table.columns) if len(pivot_table) > 0 else 0
        
        cursor.execute(insert_sql, (
            report_title,
            html_content,
            generation_timestamp,
            metrics_count,
            date_range_count
        ))
        
        conn.commit()
        cursor.close()

        log_info(
            "task",
            "run",
            "report_saved",
            f"HTML report saved to database table: {output_table}"
        )

        # Guard: the catalog `html_report.html` field is capped. Fail with guidance
        # rather than sending a doomed request that returns a raw 422.
        HTML_MAX = 5_000_000
        if len(html_content) > HTML_MAX:
            log_error("task", "run", "html_too_large",
                      f"Report HTML is {len(html_content)} chars (> {HTML_MAX}); narrow it with a metric_template or a tighter date_filter")
            raise ValueError(
                f"Report HTML {len(html_content)} chars exceeds {HTML_MAX}; narrow via metric_template or date_filter")

        # Send report to catalog API
        user_access_token = least_action_task_object.get('user_access_token')

        if not user_access_token:
            log_error("task", "run", "missing_token", "user_access_token not found in least_action_task_object")
            return output_table

        log_info("task", "run", "prepare_request", f"Preparing catalog create request for report: {report_title}")

        # Use backend-test for test environment, backend for production
        backend_host = os.getenv("BACKEND_HOST", "backend-test")
        api_url = f"http://backend:8000/api/v1/catalog/create"

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        # Generate a name for the report (use report_title with timestamp for uniqueness)
        report_name = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        payload = {
            "item_type": "html_report",
            "name": report_name,
            "description": report_title,
            "html": html_content,
            "parent_laui": output_parent_laui,
            "project_laui": str(least_action_task_object.get('project_laui')),
            "account_laui": str(least_action_task_object.get('account_laui')),
        }

        log_info("task", "run", "send_request", f"Sending POST request to {api_url}")

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200 or response.status_code == 201:
                log_info("task", "run", "api_success", f"Successfully sent report to catalog API: {report_name}")
            else:
                log_error("task", "run", "api_error", f"Catalog API returned status {response.status_code}: {response.text}")
                raise RuntimeError(f"Catalog create failed with status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            log_error("task", "run", "api_request_error", f"Error sending report to catalog API: {str(e)}")
            raise

        return output_table

    except Exception as e:
        log_error(
            "task",
            "run",
            "report_generation_error",
            f"Error generating HTML report: {str(e)}"
        )
        raise


def run(least_action_task_object, client):
    """
    Execute the report generation process.

    Args:
        least_action_task_object: Task object containing payload with report configuration
        client: PostgreSQL connection from initialize()

    Returns:
        dict: Result containing execution details and status
    """
    try:
        payload = least_action_task_object.get('payload', {})
        task_laui = least_action_task_object.get('laui')

        log_info("task", "run", "extracting_payload", "Extracting payload for task")

        # Check if payload itself is a string and parse it first
        if isinstance(payload, str):
            try:
                # If the string starts and ends with quotes, it's a JSON-encoded string
                # Remove outer quotes and unescape
                if payload.startswith('"') and payload.endswith('"'):
                    payload = payload[1:-1]  # Remove outer quotes
                    payload = payload.replace('\\"', '"')  # Unescape quotes
                
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                log_error(
                    "task",
                    "run",
                    "payload_parse_error",
                    f"Failed to parse payload as JSON: {str(e)}"
                )
                return {
                    'status': 'failed',
                    'execution_type': 'sync',
                    'result': None,
                    'error': f'Invalid payload format - payload is not valid JSON: {str(e)}'
                }

        # Extract payload data
        payload_data = payload.get('data', {})

        if isinstance(payload_data, str):
            try:
                payload_data = json.loads(payload_data)
            except json.JSONDecodeError:
                log_error(
                    "task",
                    "run",
                    "payload_data_parse_error",
                    "Failed to parse payload.data as JSON"
                )
                return {
                    'status': 'failed',
                    'execution_type': 'sync',
                    'result': None,
                    'error': 'Invalid payload.data format'
                }

        # Extract configuration from payload
        report_title = payload_data.get('report_title', 'Dynamic Report')
        output_table = payload_data.get('output_table', 'report_output')
        query_config = payload_data.get('query', {})
        metric_template = payload_data.get('metric_template')
        report_style = payload_data.get('report_style', {})
        output_parent_laui = payload_data.get('output_parent_laui')

        log_info(
            "task",
            "run",
            "configuration_loaded",
            f"Report title: {report_title}, Output table: {output_table}"
        )

        # Load data from database
        df = load_data_from_database(client, query_config)

        # Pivot data with styling
        pivot_table, metric_styles = pivot_kv_data_to_report(df, metric_template=metric_template)

        # Write HTML report to database and send to catalog API
        output_table_name = write_report_to_database(client, pivot_table, metric_styles, output_table, report_title, report_style, output_parent_laui , least_action_task_object)

        result = {
            'status': 'success',
            'execution_type': 'sync',
            'result': {
                'output_table': output_table_name,
                'report_title': report_title,
                'metrics_count': len(pivot_table),
                'date_range_count': len(pivot_table.columns) if len(pivot_table) > 0 else 0,
                'generation_time': datetime.now().isoformat()
            }
        }

        log_info(
            "task",
            "run",
            "operation_completed",
            f"Report generation completed successfully"
        )

        return result

    except Exception as e:
        log_error(
            "task",
            "run",
            "execution_error",
            f"Error during report generation: {str(e)}"
        )

        return {
            'status': 'failed',
            'execution_type': 'sync',
            'result': None,
            'error': str(e)
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Check completion status for synchronous operation.

    Args:
        least_action_task_object: Task object
        client: PostgreSQL connection
        run_details: Results from run() method

    Returns:
        dict: Completion status
    """
    try:
        log_info(
            "task",
            "check_completion",
            "checking_status",
            "Checking report generation status"
        )

        # This is a synchronous operation
        if run_details.get('status') == 'success':
            log_info(
                "task",
                "check_completion",
                "operation_successful",
                "Report generation completed successfully"
            )
            return {
                'status': 'success',
                'message': 'Report generation completed successfully',
                'output': run_details.get('result')
            }
        else:
            log_error(
                "task",
                "check_completion",
                "operation_failed",
                f"Report generation failed: {run_details.get('error')}"
            )
            return {
                'status': 'failed',
                'message': f"Report generation failed: {run_details.get('error')}",
                'output': None
            }

    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "status_check_error",
            f"Error checking completion status: {str(e)}"
        )

        return {
            'status': 'failed',
            'message': f"Status check error: {str(e)}",
            'output': None
        }


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Cleanup resources and close connections.

    Args:
        least_action_task_object: Task object
        client: PostgreSQL connection to cleanup
        completion_details: Final completion status
        run_details: Original run results
    """
    try:
        task_laui = least_action_task_object.get('laui')

        log_info("task", "finish", "starting_cleanup", "Starting cleanup for task")

        # Log final status
        final_status = completion_details.get('status', 'unknown')
        log_info(
            "task",
            "finish",
            "final_status",
            f"Task completed with status: {final_status}"
        )

        # Close database connection
        if client:
            try:
                client.close()
                log_info(
                    "task",
                    "finish",
                    "connection_closed",
                    "PostgreSQL connection closed successfully"
                )
            except Exception as e:
                log_error(
                    "task",
                    "finish",
                    "connection_close_error",
                    f"Error closing connection: {str(e)}"
                )

        # Log summary
        if final_status == 'success':
            output = completion_details.get('output', {})
            output_table = output.get('output_table', 'unknown')
            log_info("task", "finish", "operation_summary", "Report successfully generated")
        elif final_status == 'failed':
            log_error(
                "task",
                "finish",
                "operation_failed",
                f"Operation failed: {completion_details.get('message')}"
            )

        log_info("task", "finish", "cleanup_completed", "Cleanup completed for task")

    except Exception as e:
        log_error(
            "task",
            "finish",
            "cleanup_error",
            f"Error during finish/cleanup: {str(e)}"
        )

'''

}


bashblock={"main.sh":""}

payload = ""

connection = {
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "your_password_here"
}

prompt = (
    "Generate a styled HTML pivot table report from a PostgreSQL CUBE-transformed fact table and publish to the LeastAction catalog. "
    "Payload is a JSON config with: report_title, output_table, output_parent_laui, query (table + date_filter + limit), "
    "metric_template (list of row definitions with display_name, dim_key_grouping, dim_value, metric_key, cell_format, colors), "
    "report_style (header colors, fonts, border). "
    "Pivots the key-value fact table by date. Supports '*' wildcard in dim_key_grouping for dynamic row expansion. "
    "Writes report HTML to PostgreSQL output_table and publishes as html_report catalog item."
)

install_docs = """# PostgresqlGenerateHtmlTableReport — Install Guide

## Dependencies

    pip install psycopg2-binary
    pip install pandas
    pip install requests

## PostgreSQL Fact Table Structure

Expects a CUBE-transformed table with columns:
  date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level

## Catalog Publishing

Requires user_access_token in task object (injected by LeastAction executor).
Set output_parent_laui in payload to a valid catalog folder LAUI.
"""

guide_docs = """# PostgresqlGenerateHtmlTableReport — Operator Guide

## What it does

Reads from a CUBE-transformed PostgreSQL fact table, pivots data by date using metric_template
definitions, generates a styled inline HTML report, writes it to a database output table, and
optionally publishes it to the LeastAction catalog as an html_report item.

---

## Connection

Standard PostgreSQL connection:

    {"host": "localhost", "port": 5432, "database": "mydb", "user": "postgres", "password": "..."}

---

## Payload

JSON config with at minimum:

    {
      "report_title": "My Report",
      "output_table": "html_reports",
      "query": {"table": "fact_sales_daily"},
      "metric_template": [
        {
          "display_name": "Total Revenue",
          "dim_key_grouping": "revenue::total",
          "metric_key": "revenue",
          "cell_format": "${value:,.2f}"
        }
      ]
    }

Use '*' in dim_key_grouping to expand one row per distinct dim_value (e.g. "category::*").
Set output_parent_laui to publish to catalog.

---

## Output (on success)

    {
      "output_table": "html_reports",
      "report_title": "My Report",
      "metrics_count": 5,
      "date_range_count": 7,
      "generation_time": "..."
    }
"""

description = """
Generates a styled HTML pivot table report from a PostgreSQL CUBE-transformed fact table.
Supports dynamic row expansion with '*' wildcard in dim_key_grouping. Writes the HTML to
a PostgreSQL output table and optionally publishes to the LeastAction catalog as an html_report.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Reporting",
    "tags": ["postgresql", "html", "report", "pivot", "table", "catalog", "cube"],
    "airflow_equivalent": "PostgresOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
