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

Generates styled HTML reports from a PostgreSQL database. Automatically picks the
report layout based on the shape of the query result and payload:

  - Pivot mode : payload.data.metric_template is provided -> pivot key-value data
                 by date using the template rows (existing behaviour).
  - Cube mode  : no metric_template, and the result has multiple distinct
                 cube_level values -> render one section per cube level with
                 subtotal rows.
  - Table mode : no metric_template and a single (or no) cube_level -> render
                 the raw query result as a flat HTML table (one row per record,
                 one column per field).
"""

import psycopg2
import pandas as pd
from datetime import datetime
import json
import re
import requests
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

        log_info("task", "initialize", "extracting_connection_details", "Extracting PostgreSQL connection details")

        host = connection.get('host', 'localhost')
        port = connection.get('port', 5432)
        database = connection.get('database', 'postgres')
        user = connection.get('user', 'postgres')
        password = connection.get('password', '')

        log_info("task", "initialize", "creating_connection", "Creating PostgreSQL connection")

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
        log_error("task", "initialize", "connection_error", f"PostgreSQL connection error: {str(e)}")
        raise
    except Exception as e:
        log_error("task", "initialize", "unexpected_error", f"Unexpected error during initialization: {str(e)}")
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
        columns = query_config.get('columns')

        log_info("task", "run", "building_query", "Building query")

        if columns:
            select_clause = ", ".join(columns)
        else:
            select_clause = "*"

        sql = f"""
            SELECT
                {select_clause}
            FROM {table}
            WHERE {date_filter}
        """

        if limit:
            sql += f" LIMIT {limit}"

        log_info("task", "run", "executing_query", "Executing query")

        df = pd.read_sql(sql, conn)

        log_info("task", "run", "data_loaded", "Data loaded")

        return df

    except Exception as e:
        log_error("task", "run", "query_execution_error", f"Error executing query: {str(e)}")
        raise


def detect_report_mode(df, metric_template):
    """
    Determine which report layout to generate based on payload and result shape.

    Args:
        df: Loaded DataFrame
        metric_template: metric_template list from payload, or None

    Returns:
        str: 'pivot', 'cube', or 'table'
    """
    if metric_template is not None:
        return 'pivot'

    if 'cube_level' in df.columns and df['cube_level'].nunique() > 1:
        return 'cube'

    return 'table'


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


def pivot_kv_data_to_report(df, metric_template):
    """
    Pivot the key-value fact table data using dynamic template configuration.

    Args:
        df: Input DataFrame
        metric_template: List of metric template configurations

    Returns:
        tuple: (Pivoted DataFrame, Styling metadata dictionary)
    """
    try:
        log_info("task", "run", "pivoting_data", "Starting data pivot operation")

        df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        filtered_data = []
        metric_order = []
        metric_styles = {}

        log_info("task", "run", "processing_templates", "Processing templates")

        for idx, template_item in enumerate(metric_template):
            display_name = template_item['display_name']
            dim_key_grouping_filter = template_item.get('dim_key_grouping')
            dim_value_filter = template_item.get('dim_value')
            metric_key_filter = template_item.get('metric_key')

            cell_format = template_item.get('cell_format', '{value:,.2f}')
            cell_bg_color = template_item.get('cell_bg_color')
            cell_text_color = template_item.get('cell_text_color')
            text_bold = template_item.get('text_bold', False)
            text_italic = template_item.get('text_italic', False)
            text_size = template_item.get('text_size')

            log_info("task", "run", "processing_template", "Processing template")

            show_details = False
            if dim_key_grouping_filter and '*' in dim_key_grouping_filter:
                show_details = True
                log_info("task", "run", "dynamic_row_detection", "Dynamic row detection")

            mask = pd.Series([True] * len(df))

            if metric_key_filter:
                mask &= (df['metric_key'] == metric_key_filter)

            if dim_key_grouping_filter is not None:
                if show_details:
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
                    unique_dim_values = filtered_df['dim_value'].unique()

                    log_info("task", "run", "creating_detail_rows", "Creating detail rows")

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
                log_info("task", "run", "no_data_for_template", "No data for template")

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

            log_info("task", "run", "pivot_complete", "Pivot complete")
        else:
            pivot_table = pd.DataFrame()
            log_info("task", "run", "empty_pivot", "No metrics matched the template filters")

        return pivot_table, metric_styles

    except Exception as e:
        log_error("task", "run", "pivot_error", f"Error during pivot operation: {str(e)}")
        raise


def generate_pivot_table_html(pivot_table, metric_styles, report_style):
    """
    Generate HTML table with inline styling for each cell (pivot mode).

    Args:
        pivot_table: Pivoted DataFrame
        metric_styles: Styling metadata dictionary
        report_style: Report-level styling configuration

    Returns:
        str: HTML table string
    """
    try:
        if len(pivot_table) == 0:
            log_info("task", "run", "empty_table", "No data to display in table")
            return "<p>No data to display</p>"

        html_parts = ['<table>']

        html_parts.append('<thead><tr>')
        html_parts.append('<th style="text-align: left;">Metric</th>')
        for col in pivot_table.columns:
            html_parts.append(f'<th>{col}</th>')
        html_parts.append('</tr></thead>')

        html_parts.append('<tbody>')
        for idx, (metric_name, row) in enumerate(pivot_table.iterrows()):
            row_style = metric_styles.get(metric_name, {})

            is_even = idx % 2 == 0
            default_bg = report_style.get('row_bg_color_even' if is_even else 'row_bg_color_odd', '#ffffff')

            html_parts.append('<tr>')
            html_parts.append(f'<td style="text-align: left; font-weight: bold;">{metric_name}</td>')

            for value in row:
                cell_format = row_style.get('cell_format', '{value:,.2f}')
                formatted_value = format_cell_value(value, cell_format)

                cell_style_parts = []

                bg_color = row_style.get('cell_bg_color', default_bg)
                if bg_color:
                    cell_style_parts.append(f'background-color: {bg_color}')

                text_color = row_style.get('cell_text_color')
                if text_color:
                    cell_style_parts.append(f'color: {text_color}')

                if row_style.get('text_bold'):
                    cell_style_parts.append('font-weight: bold')

                if row_style.get('text_italic'):
                    cell_style_parts.append('font-style: italic')

                text_size = row_style.get('text_size')
                if text_size:
                    cell_style_parts.append(f'font-size: {text_size}')

                cell_style_parts.append('text-align: right')
                cell_style_parts.append('padding: 10px')
                cell_style_parts.append(f'border: 1px solid {report_style.get("border_color", "#ddd")}')

                cell_style_str = '; '.join(cell_style_parts)
                html_parts.append(f'<td style="{cell_style_str}">{formatted_value}</td>')

            html_parts.append('</tr>')
        html_parts.append('</tbody>')
        html_parts.append('</table>')

        log_info("task", "run", "html_table_generated", "Pivot HTML table generated")

        return ''.join(html_parts)

    except Exception as e:
        log_error("task", "run", "html_generation_error", f"Error generating pivot HTML table: {str(e)}")
        raise


def generate_flat_table_html(df, report_style):
    """
    Generate a plain HTML table directly from a query result DataFrame (table mode).

    Args:
        df: Query result DataFrame
        report_style: Report-level styling configuration

    Returns:
        str: HTML table string
    """
    try:
        if len(df) == 0:
            log_info("task", "run", "empty_table", "No data to display in table")
            return "<p>No data to display</p>"

        border_color = report_style.get('border_color', '#ddd')

        html_parts = ['<table>']

        html_parts.append('<thead><tr>')
        for col in df.columns:
            html_parts.append(f'<th>{col}</th>')
        html_parts.append('</tr></thead>')

        html_parts.append('<tbody>')
        for idx, (_, row) in enumerate(df.iterrows()):
            is_even = idx % 2 == 0
            row_bg = report_style.get('row_bg_color_even' if is_even else 'row_bg_color_odd', '#ffffff')

            html_parts.append('<tr>')
            for value in row:
                cell_style = (
                    f'background-color: {row_bg}; text-align: right; '
                    f'padding: 10px; border: 1px solid {border_color}'
                )
                html_parts.append(f'<td style="{cell_style}">{value}</td>')
            html_parts.append('</tr>')
        html_parts.append('</tbody>')
        html_parts.append('</table>')

        log_info("task", "run", "html_table_generated", "Flat HTML table generated")

        return ''.join(html_parts)

    except Exception as e:
        log_error("task", "run", "html_generation_error", f"Error generating flat HTML table: {str(e)}")
        raise


def generate_cube_report_html(df, report_style):
    """
    Generate an HTML report with one section per cube_level (cube mode).

    Each cube_level gets its own table showing the dim/metric breakdown for that
    rollup level.

    Args:
        df: Query result DataFrame containing a cube_level column
        report_style: Report-level styling configuration

    Returns:
        str: HTML string containing one table per cube level
    """
    try:
        if len(df) == 0:
            log_info("task", "run", "empty_table", "No data to display in table")
            return "<p>No data to display</p>"

        border_color = report_style.get('border_color', '#ddd')
        header_bg_color = report_style.get('header_bg_color', '#4CAF50')

        display_columns = [col for col in df.columns if col != 'cube_level']

        html_parts = []

        for cube_level in sorted(df['cube_level'].dropna().unique()):
            level_df = df[df['cube_level'] == cube_level]

            html_parts.append(
                f'<h3 style="border-bottom: 2px solid {header_bg_color}; padding-bottom: 5px;">'
                f'Cube Level: {cube_level}</h3>'
            )
            html_parts.append('<table>')

            html_parts.append('<thead><tr>')
            for col in display_columns:
                html_parts.append(f'<th>{col}</th>')
            html_parts.append('</tr></thead>')

            html_parts.append('<tbody>')
            for idx, (_, row) in enumerate(level_df[display_columns].iterrows()):
                is_even = idx % 2 == 0
                row_bg = report_style.get('row_bg_color_even' if is_even else 'row_bg_color_odd', '#ffffff')

                html_parts.append('<tr>')
                for value in row:
                    cell_style = (
                        f'background-color: {row_bg}; text-align: right; '
                        f'padding: 10px; border: 1px solid {border_color}'
                    )
                    html_parts.append(f'<td style="{cell_style}">{value}</td>')
                html_parts.append('</tr>')
            html_parts.append('</tbody>')
            html_parts.append('</table>')

        log_info("task", "run", "html_table_generated", "Cube html report generated")

        return ''.join(html_parts)

    except Exception as e:
        log_error("task", "run", "html_generation_error", f"Error generating cube HTML report: {str(e)}")
        raise


def write_report_to_database(conn, table_html, metrics_count, date_range_count, output_table, report_title, report_style, output_parent_laui, least_action_task_object):
    """
    Write HTML report to database table and send to catalog API.

    Args:
        conn: PostgreSQL connection object
        table_html: Pre-rendered HTML table/report body
        metrics_count: Number of metric rows in the report
        date_range_count: Number of date columns (0 if not applicable)
        output_table: Output table name
        report_title: Report title
        report_style: Report-level styling configuration
        output_parent_laui: Catalog folder LAUI to publish the report under
        least_action_task_object: Task object containing user_access_token

    Returns:
        str: Output table name
    """
    try:
        log_info("task", "run", "generating_html_report", "Generating html report")

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
                    <strong>Data Source:</strong> PostgreSQL Database<br>
                    <strong>Metrics Shown:</strong> {num_metrics} | <strong>Date Range:</strong> {num_dates} days
                </div>
                {table_html}
                <div class="footer">
                    Generated by Dynamic Report System | Database-Driven Analytics
                </div>
            </div>
        </body>
        </html>
        """

        generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = html_template.format(
            report_title=report_title,
            generation_time=generation_time,
            num_metrics=metrics_count,
            num_dates=date_range_count,
            table_html=table_html,
            font_family=report_style.get('font_family', 'Arial, sans-serif'),
            header_bg_color=report_style.get('header_bg_color', '#4CAF50'),
            header_text_color=report_style.get('header_text_color', '#FFFFFF'),
            border_color=report_style.get('border_color', '#dddddd'),
            row_hover_color=report_style.get('row_hover_color', '#e8f5e9')
        )

        cursor = conn.cursor()

        # Serialize first-time table creation across concurrent report tasks.
        # This check-then-CREATE is not atomic: when several reports target the
        # same output_table and race on the initial create, each session sees
        # table_exists=False and each then tries to create the table and its
        # implicit sequence, colliding on pg_class ("duplicate key value
        # violates unique constraint pg_class_relname_nsp_index"). A
        # transaction-level advisory lock keyed on the table name lets only one
        # creator run at a time; it is released on commit/rollback.
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (output_table,))

        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
            (output_table,)
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            create_table_sql = f"""
            CREATE TABLE {output_table} (
                id SERIAL PRIMARY KEY,
                report_title VARCHAR(500),
                html_content TEXT,
                generation_time TIMESTAMP,
                metrics_count INTEGER,
                date_range_count INTEGER
            )
            """
            cursor.execute(create_table_sql)

        insert_sql = f"""
        INSERT INTO {output_table}
        (report_title, html_content, generation_time, metrics_count, date_range_count)
        VALUES (%s, %s, %s, %s, %s)
        """

        generation_timestamp = datetime.now()

        cursor.execute(insert_sql, (
            report_title,
            html_content,
            generation_timestamp,
            metrics_count,
            date_range_count
        ))

        conn.commit()
        cursor.close()

        log_info("task", "run", "report_saved", "Report saved")

        user_access_token = least_action_task_object.get('user_access_token')

        if not user_access_token:
            log_error("task", "run", "missing_token", "user_access_token not found in least_action_task_object")
            return output_table

        log_info("task", "run", "prepare_request", "Prepare request")

        api_url = "http://backend:8000/api/v1/catalog/create"

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        report_name = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        payload = {
            "item_type": "html_report",
            "name": report_name,
            "description": report_title,
            "html": html_content,
            "parent_laui": output_parent_laui,
            "project_laui": str(least_action_task_object.get('project_laui')),
            "account_laui": str(least_action_task_object.get('account_laui'))
        }

        log_info("task", "run", "send_request", f"Sending POST request to {api_url}")

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code in (200, 201):
                log_info("task", "run", "api_success", "Api success")
            else:
                log_error("task", "run", "api_error", f"Api error: status={response.status_code}, body={response.text}")

        except requests.exceptions.RequestException as e:
            log_error("task", "run", "api_request_error", f"Error sending report to catalog API: {str(e)}")

        return output_table

    except Exception as e:
        log_error("task", "run", "report_generation_error", f"Error generating HTML report: {str(e)}")
        raise


def run(least_action_task_object, client):
    """
    Execute the report generation process.

    Selects pivot, cube, or flat table layout based on payload.data.metric_template
    and the cube_level distribution of the query result.

    Args:
        least_action_task_object: Task object containing payload with report configuration
        client: PostgreSQL connection from initialize()

    Returns:
        dict: Result containing execution details and status
    """
    try:
        payload = least_action_task_object.get('payload', {})

        log_info("task", "run", "extracting_payload", "Extracting payload for task")

        if isinstance(payload, str):
            try:
                if payload.startswith('"') and payload.endswith('"'):
                    payload = payload[1:-1]
                    payload = payload.replace('\\\\"', '"')

                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                log_error("task", "run", "payload_parse_error", f"Failed to parse payload as JSON: {str(e)}")
                return {
                    'status': 'failed',
                    'execution_type': 'sync',
                    'result': None,
                    'error': f'Invalid payload format - payload is not valid JSON: {str(e)}'
                }

        payload_data = payload.get('data', {})

        if isinstance(payload_data, str):
            try:
                payload_data = json.loads(payload_data)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_data_parse_error", "Failed to parse payload.data as JSON")
                return {
                    'status': 'failed',
                    'execution_type': 'sync',
                    'result': None,
                    'error': 'Invalid payload.data format'
                }

        report_title = payload_data.get('report_title', 'Dynamic Report')
        output_table = payload_data.get('output_table', 'report_output')
        query_config = payload_data.get('query', {})
        metric_template = payload_data.get('metric_template')
        report_style = payload_data.get('report_style', {})
        output_parent_laui = payload_data.get('output_parent_laui')

        log_info("task", "run", "configuration_loaded", "Configuration loaded")

        df = load_data_from_database(client, query_config)

        report_mode = detect_report_mode(df, metric_template)
        log_info("task", "run", "report_mode_detected", "Report mode detected")

        if report_mode == 'pivot':
            pivot_table, metric_styles = pivot_kv_data_to_report(df, metric_template)
            table_html = generate_pivot_table_html(pivot_table, metric_styles, report_style)
            metrics_count = len(pivot_table)
            date_range_count = len(pivot_table.columns) if len(pivot_table) > 0 else 0

        elif report_mode == 'cube':
            table_html = generate_cube_report_html(df, report_style)
            metrics_count = len(df)
            date_range_count = df['cube_level'].nunique()

        else:
            table_html = generate_flat_table_html(df, report_style)
            metrics_count = len(df)
            date_range_count = len(df.columns)

        output_table_name = write_report_to_database(
            client, table_html, metrics_count, date_range_count,
            output_table, report_title, report_style, output_parent_laui,
            least_action_task_object
        )

        result = {
            'status': 'success',
            'execution_type': 'sync',
            'result': {
                'output_table': output_table_name,
                'report_title': report_title,
                'report_mode': report_mode,
                'metrics_count': metrics_count,
                'date_range_count': date_range_count,
                'generation_time': datetime.now().isoformat()
            }
        }

        log_info("task", "run", "operation_completed", "Report generation completed successfully")

        return result

    except Exception as e:
        log_error("task", "run", "execution_error", f"Error during report generation: {str(e)}")

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
        log_info("task", "check_completion", "checking_status", "Checking report generation status")

        if run_details.get('status') == 'success':
            log_info("task", "check_completion", "operation_successful", "Report generation completed successfully")
            return {
                'status': 'success',
                'message': 'Report generation completed successfully',
                'output': run_details.get('result')
            }
        else:
            log_error("task", "check_completion", "operation_failed", f"Report generation failed: {run_details.get('error')}")
            return {
                'status': 'failed',
                'message': f"Report generation failed: {run_details.get('error')}",
                'output': None
            }

    except Exception as e:
        log_error("task", "check_completion", "status_check_error", f"Error checking completion status: {str(e)}")

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
        log_info("task", "finish", "starting_cleanup", "Starting cleanup for task")

        final_status = completion_details.get('status', 'unknown')
        log_info("task", "finish", "final_status", "Final status")

        if client:
            try:
                client.close()
                log_info("task", "finish", "connection_closed", "PostgreSQL connection closed successfully")
            except Exception as e:
                log_error("task", "finish", "connection_close_error", f"Error closing connection: {str(e)}")

        if final_status == 'success':
            log_info("task", "finish", "operation_summary", "Report successfully generated")
        elif final_status == 'failed':
            log_error("task", "finish", "operation_failed", f"Operation failed: {completion_details.get('message')}")

        log_info("task", "finish", "cleanup_completed", "Cleanup completed for task")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")

'''

}


bashblock={"main.sh":"pip install psycopg2-binary pandas requests"}

payload = ""

connection = {
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "your_password_here"
}

prompt = (
    "Generate a styled HTML report from a PostgreSQL database and publish it to the LeastAction catalog. "
    "The operator auto-detects the report layout from the payload and query result: "
    "(1) Pivot mode - if payload.data.metric_template is provided, pivots key-value fact data by date using the "
    "template rows, supports '*' wildcard in dim_key_grouping for dynamic row expansion; "
    "(2) Cube mode - if no metric_template and the query result has multiple distinct cube_level values, renders "
    "one table per cube level; "
    "(3) Table mode - otherwise, renders the raw query result as a flat HTML table (one row per record, one "
    "column per field). "
    "Payload fields (under data): report_title, output_table, output_parent_laui, query (table, date_filter, "
    "limit, optional columns list), metric_template (optional, list of row configs), report_style "
    "(header_bg_color, border_color, etc)."
)

install_docs = """# PostgresqlGenerateHtml — Install Guide

## Dependencies

    pip install psycopg2-binary
    pip install pandas
    pip install requests

## PostgreSQL Fact Table Structure

For pivot/cube modes, expects a CUBE-transformed table with columns:
  date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value, cube_level

For table mode, any query result shape is supported via query.columns.

## Catalog Publishing

Requires user_access_token in task object (injected by LeastAction executor).
Set output_parent_laui in payload to a valid catalog folder LAUI.
"""

guide_docs = """# PostgresqlGenerateHtml — Operator Guide

## What it does

Runs a query against PostgreSQL and renders a styled HTML report, automatically choosing
the layout based on the payload and result shape:

  - Pivot mode : payload.data.metric_template is provided -> pivot key-value data by date
                 using the template rows. Supports '*' wildcard in dim_key_grouping for
                 dynamic row expansion.
  - Cube mode  : no metric_template, and the result has multiple distinct cube_level values
                 -> render one section per cube level with subtotal rows.
  - Table mode : no metric_template and a single (or no) cube_level -> render the raw query
                 result as a flat HTML table (one row per record, one column per field).

The HTML is written to a PostgreSQL output table and optionally published to the
LeastAction catalog as an html_report item.

---

## Connection

Standard PostgreSQL connection:

    {"host": "localhost", "port": 5432, "database": "mydb", "user": "postgres", "password": "..."}

---

## Payload

JSON config under "data":

    {
      "report_title": "My Report",
      "output_table": "html_reports",
      "output_parent_laui": "<catalog folder laui>",
      "query": {
        "table": "fact_product_agg_daily_stage1",
        "date_filter": "cube_level = 1",
        "limit": 50,
        "columns": null
      },
      "metric_template": [
        {
          "display_name": "Total Revenue",
          "dim_key_grouping": "*::dim_category::dim_region::dim_subregion::dim_store",
          "metric_key": "revenue",
          "cell_format": "{value:,.2f}",
          "text_bold": true
        }
      ],
      "report_style": {
        "header_bg_color": "#4CAF50",
        "header_text_color": "#FFFFFF",
        "border_color": "#dddddd",
        "row_bg_color_even": "#ffffff",
        "row_bg_color_odd": "#f9f9f9",
        "row_hover_color": "#e8f5e9",
        "font_family": "Arial, sans-serif"
      }
    }

- Omit metric_template and use a date_filter that yields a single cube_level for table mode.
- Omit metric_template and use a date_filter that yields multiple cube_level values for cube mode.
- Provide metric_template for pivot mode. Use '*' in dim_key_grouping to expand one row per
  distinct dim_value.
- Set output_parent_laui to publish to catalog.

---

## Output (on success)

    {
      "output_table": "html_reports",
      "report_title": "My Report",
      "report_mode": "pivot",
      "metrics_count": 5,
      "date_range_count": 7,
      "generation_time": "..."
    }
"""

description = """
Generates a styled HTML report (table, pivot, or cube layout) from a PostgreSQL fact table.
Auto-detects the layout: pivot when metric_template is given, cube when multiple cube_level
values are present, otherwise a flat SQL table. Writes the HTML to a PostgreSQL output table
and publishes it to the LeastAction catalog.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Reporting",
    "tags": ["postgresql", "html", "report", "pivot", "cube", "table", "catalog"],
    "airflow_equivalent": "PostgresOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
