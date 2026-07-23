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


def load_data_from_database(conn, query_config, needed_keys=None, window_weeks=12, grouping_patterns=None):
    """
    Load data from database based on query configuration.

    Pulls a trailing window (default 12 weeks ending at MAX(date)) restricted to
    the metric_keys the templates actually need, so the pivot stays bounded while
    still carrying enough history for the trend sparkline and rolling stats.

    Args:
        conn: PostgreSQL connection object
        query_config: Query configuration dictionary
        needed_keys: iterable of metric_key values to keep (None = all)
        window_weeks: trailing window size when no explicit date_filter is given

    Returns:
        pd.DataFrame: Loaded data
    """
    try:
        table = query_config.get('table', 'fact_product_agg_daily')
        date_filter = query_config.get('date_filter')
        limit = query_config.get('limit')

        if not date_filter:
            days = int(window_weeks) * 7
            date_filter = f"date >= (SELECT MAX(date) FROM {table}) - INTERVAL '{days} days'"

        key_clause = ""
        if needed_keys:
            safe = sorted({re.sub(r'[^A-Za-z0-9_]', '', str(k)) for k in needed_keys if k})
            if safe:
                key_list = ", ".join("'" + k + "'" for k in safe)
                key_clause = f"AND metric_key IN ({key_list})"

        # Restrict the pull to only the grouping SHAPES the templates render. Without
        # this the query returns every grouping in the cube over the whole window,
        # which for a wide report blows the worker's memory (OOM -> SIGKILL). We turn
        # each template's dim_key_grouping into a POSIX regex ('*' -> one non-colon
        # segment) and OR them; the finer '(?!dim_)' distinction is still applied in
        # pandas, so this is a coarse-but-safe pre-filter.
        group_clause = ""
        if grouping_patterns:
            regexes = []
            for g in sorted({p for p in grouping_patterns if p}):
                parts = g.split('::')
                rx = '^' + '::'.join('[^:]+' if p == '*' else re.escape(p) for p in parts) + '$'
                regexes.append(rx)
            if regexes:
                ors = " OR ".join("dim_key_grouping ~ '" + rx + "'" for rx in regexes)
                group_clause = f"AND ({ors})"

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
            {key_clause}
            {group_clause}
        """

        if limit:
            sql += f" LIMIT {limit}"

        log_info(
            "task",
            "run",
            "executing_query",
            f"Executing report query on {table} WHERE {date_filter} {key_clause}"
        )

        df = pd.read_sql(sql, conn)

        log_info(
            "task",
            "run",
            "data_loaded",
            f"Successfully loaded {len(df)} rows from database"
        )

        if len(df) > 0:
            log_info(
                "task",
                "run",
                "data_summary",
                f"Data shape: {df.shape[0]} rows | Unique groupings: {df['dim_key_grouping'].nunique()} | Unique metrics: {df['metric_key'].nunique()}"
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


# Variance sub-rows / summary columns are derived from cube metrics that already
# exist (stage2/final emits <base>_dod / _wow / _yoy / _pct_of_total). "lwsd"
# (last-week-same-day) reuses the 7-day lag captured by _wow.
VAR_SUFFIX = {"dod": "_dod", "lwsd": "_wow", "yoy": "_yoy"}
VAR_LABELS = {"dod": "DoD", "lwsd": "LWSD", "yoy": "YoY"}
SUMMARY_LABELS = {
    "trend": "12-Wk Trend",
    "std": "Std 12w",
    "dod": "DoD",
    "wow": "WoW",
    "yoy": "YoY",
    "lwsd": "LWSD",
    "share": "Share %",
}


def _pct_change(value, delta):
    """Percent change given a value and its absolute delta (value - prev)."""
    try:
        if value is None or delta is None:
            return None
        prev = value - delta
        if not prev:
            return None
        return delta / prev * 100.0
    except Exception:
        return None


def _sparkline_svg(values, color="#1565C0"):
    """Inline SVG polyline sparkline from a numeric series (self-contained, no deps)."""
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    w, h = 84.0, 20.0
    n = len(pts)
    coords = " ".join(
        f"{(i / (n - 1)) * w:.1f},{h - ((v - lo) / span) * h:.1f}"
        for i, v in enumerate(pts)
    )
    return (
        f'<svg width="{int(w)}" height="{int(h)}" viewBox="0 0 {int(w)} {int(h)}" '
        f'preserveAspectRatio="none"><polyline fill="none" stroke="{color}" '
        f'stroke-width="1.5" points="{coords}"/></svg>'
    )


def _summary_cell(key, g, v, base, cell_format, latest, val, full_series, grand):
    """Compute one right-hand analytic column for an item row."""
    if latest is None:
        return ""
    if key == "trend":
        return _sparkline_svg(full_series(g, v, base))
    if key == "std":
        vals = [x for x in full_series(g, v, base) if x is not None]
        if len(vals) < 2:
            return ""
        try:
            import statistics
            return format_cell_value(statistics.pstdev(vals), cell_format)
        except Exception:
            return ""
    if key == "share":
        # Share of the grand total for this metric/date. The cube's _pct_of_total is
        # self-referential per grouping (always 100% for a detail row), so we divide
        # by the grand-total row (dim_value='') value instead.
        row_v = val(g, v, base, latest)
        total = grand.get((base, latest))
        if row_v is None or not total:
            return ""
        return f"{row_v / total * 100.0:.1f}%"
    if key == "dod":
        p = _pct_change(val(g, v, base, latest), val(g, v, base + "_dod", latest))
        return "" if p is None else f"{p:+.1f}%"
    if key == "wow":
        # true week-over-week: trailing 7-day total vs the prior 7-day total
        ser = [x for x in full_series(g, v, base) if x is not None]
        if len(ser) < 14:
            return ""
        last7, prev7 = sum(ser[-7:]), sum(ser[-14:-7])
        if not prev7:
            return ""
        return f"{(last7 - prev7) / prev7 * 100.0:+.1f}%"
    if key in ("yoy", "lwsd"):
        suffix = "_yoy" if key == "yoy" else "_wow"
        p = _pct_change(val(g, v, base, latest), val(g, v, base + suffix, latest))
        return "" if p is None else f"{p:+.1f}%"
    return ""


def build_report_rows(df, metric_template, report_opts):
    """
    Build a hierarchical, multi-column report from the CUBE key-value fact table.

    Each metric_template item emits a block: an optional section header, one item
    row per expanded '*' dimension value (or a single row for a fixed grouping such
    as a grand total), and optional indented %-variance sub-rows (DoD / LWSD / YoY).
    Right-hand summary columns (12-week trend sparkline, Std, WoW, YoY, LWSD,
    Share %) are computed per item row from metrics already in the cube.

    Returns:
        tuple: (rows, date_cols, summary_cols)
          rows        -> list of {label, indent, kind, cells, summary, style}
          date_cols   -> list of date strings rendered as columns
          summary_cols-> list of {key, label}
    """
    try:
        if df is None or len(df) == 0:
            log_info("task", "run", "empty_pivot", "No rows returned for the report window")
            return [], [], []

        df = df.copy()
        df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        all_dates = sorted(df['date_str'].unique())
        n_date_cols = int(report_opts.get('date_columns', 4))
        date_cols = all_dates[-n_date_cols:] if n_date_cols > 0 else list(all_dates)
        latest = date_cols[-1] if date_cols else (all_dates[-1] if all_dates else None)

        summary_keys = list(report_opts.get('summary_columns', []) or [])
        summary_cols = [{"key": k, "label": SUMMARY_LABELS.get(k, k)} for k in summary_keys]

        # Fast lookup: (grouping, dim_value, metric_key) -> {date_str: value}
        series = {}
        for r in df.itertuples(index=False):
            series.setdefault((r.dim_key_grouping, r.dim_value, r.metric_key), {})[r.date_str] = r.metric_value

        # Grand total per (metric_key, date) for Share %: the fully-grouped row
        # (every dimension rolled up, dim_value='').
        grand = {}
        for (gg, vv, mk), dd in series.items():
            if vv == '' and all(p.startswith('dim_') for p in gg.split('::')):
                for d, x in dd.items():
                    grand[(mk, d)] = x

        def val(g, v, mk, d):
            return series.get((g, v, mk), {}).get(d)

        def full_series(g, v, mk):
            s = series.get((g, v, mk), {})
            return [s.get(d) for d in all_dates]

        rows = []
        for template_item in (metric_template or []):
            base = template_item.get('metric_key')
            grouping_filter = template_item.get('dim_key_grouping')
            dim_value_filter = template_item.get('dim_value')
            cell_format = template_item.get('cell_format', '{value:,.2f}')
            indent = int(template_item.get('indent', 0))
            show_header = bool(template_item.get('show_display_name', False))
            sort_order = template_item.get('sort_order', 'key')
            variance_rows = template_item.get('variance_rows', []) or []
            top_n = template_item.get('limit')
            display_name = template_item.get('display_name', base)

            item_style = {
                'bg': template_item.get('cell_bg_color'),
                'color': template_item.get('cell_text_color'),
                'bold': bool(template_item.get('text_bold', False)),
                'italic': bool(template_item.get('text_italic', False)),
            }

            expand = bool(grouping_filter and '*' in grouping_filter)

            # Which (grouping, dim_value) pairs make up this block's item rows
            base_mask = (df['metric_key'] == base)
            if grouping_filter is not None:
                if expand:
                    parts = grouping_filter.split('::')
                    pattern = '^' + '::'.join(
                        ('(?!dim_)[^:]+' if p == '*' else re.escape(p)) for p in parts
                    ) + '$'
                    base_mask &= df['dim_key_grouping'].str.match(pattern)
                else:
                    base_mask &= (df['dim_key_grouping'] == grouping_filter)
            if dim_value_filter is not None:
                base_mask &= (df['dim_value'] == dim_value_filter)

            bdf = df[base_mask]
            if len(bdf) == 0:
                log_info("task", "run", "no_data_for_template", f"No data for: {display_name}")
                continue

            pairs = list(
                bdf[['dim_key_grouping', 'dim_value']].drop_duplicates().itertuples(index=False, name=None)
            )
            if sort_order == 'value':
                pairs.sort(key=lambda gv: (val(gv[0], gv[1], base, latest) or 0), reverse=True)
            else:
                pairs.sort(key=lambda gv: str(gv[1]))
            if top_n:
                pairs = pairs[:int(top_n)]

            if show_header:
                rows.append({
                    'label': display_name, 'indent': indent, 'kind': 'section',
                    'cells': ['' for _ in date_cols], 'summary': ['' for _ in summary_cols],
                    'style': {'bold': True},
                })
                item_indent = indent + 1
            else:
                item_indent = indent

            for (g, v) in pairs:
                label = (str(v) if (expand and v not in (None, '')) else display_name)
                cells = []
                for d in date_cols:
                    x = val(g, v, base, d)
                    cells.append(format_cell_value(x, cell_format) if x is not None else '')
                summary = [
                    _summary_cell(sc['key'], g, v, base, cell_format, latest, val, full_series, grand)
                    for sc in summary_cols
                ]
                rows.append({
                    'label': label, 'indent': item_indent, 'kind': 'item',
                    'cells': cells, 'summary': summary, 'style': item_style,
                })

                for vr in variance_rows:
                    suffix = VAR_SUFFIX.get(vr)
                    if not suffix:
                        continue
                    vcells = []
                    for d in date_cols:
                        p = _pct_change(val(g, v, base, d), val(g, v, base + suffix, d))
                        vcells.append('' if p is None else f"{p:+.1f}%")
                    rows.append({
                        'label': VAR_LABELS.get(vr, vr.upper()), 'indent': item_indent + 1,
                        'kind': 'variance', 'cells': vcells,
                        'summary': ['' for _ in summary_cols],
                        'style': {'italic': True, 'color': '#777'},
                    })

        log_info("task", "run", "pivot_complete",
                 f"Report built: {len(rows)} rows x {len(date_cols)} date cols + {len(summary_cols)} summary cols")
        return rows, date_cols, summary_cols

    except Exception as e:
        log_error(
            "task",
            "run",
            "pivot_error",
            f"Error building report rows: {str(e)}"
        )
        raise


def generate_styled_html_table(rows, date_cols, summary_cols, report_style):
    """
    Render the hierarchical report rows into an HTML table.

    Rows carry an indent level (rendered as left padding), the date-column cells,
    and the right-hand summary cells. Per-row styles are de-duplicated into a small
    set of CSS classes (sN) to keep the HTML well under the catalog size cap.

    Returns:
        str: HTML table string
    """
    try:
        if not rows:
            log_info("task", "run", "empty_table", "No data to display in table")
            return "<p>No data to display</p>"

        rs = report_style or {}
        border = rs.get('border_color', '#dddddd')
        even = rs.get('row_bg_color_even', '#f9f9f9')
        odd = rs.get('row_bg_color_odd', '#ffffff')

        sig_to_class = {}
        css_rules = []

        def class_for(style):
            props = []
            if style.get('bg'):
                props.append(f"background-color:{style['bg']}")
            if style.get('color'):
                props.append(f"color:{style['color']}")
            if style.get('bold'):
                props.append("font-weight:bold")
            if style.get('italic'):
                props.append("font-style:italic")
            if not props:
                return ''
            sig = ';'.join(props)
            cls = sig_to_class.get(sig)
            if cls is None:
                cls = f"s{len(sig_to_class)}"
                sig_to_class[sig] = cls
                css_rules.append(f".{cls}{{{sig}}}")
            return cls

        row_classes = [class_for(r.get('style', {})) for r in rows]

        style_block = (
            "<style>"
            f"td,th{{border:1px solid {border};padding:6px 8px;text-align:right;white-space:nowrap}}"
            "td.k{text-align:left}"
            f"tbody tr:nth-child(even){{background-color:{even}}}"
            f"tbody tr:nth-child(odd){{background-color:{odd}}}"
            + ''.join(css_rules)
            + "</style>"
        )

        parts = [style_block, '<table><thead><tr><th>Metric</th>']
        for col in date_cols:
            parts.append(f'<th>{col}</th>')
        for sc in summary_cols:
            parts.append(f'<th>{sc["label"]}</th>')
        parts.append('</tr></thead><tbody>')

        for r, cls in zip(rows, row_classes):
            cattr = f' class="{cls}"' if cls else ''
            kcls = ('k ' + cls).strip()
            pad = 8 + int(r.get('indent', 0)) * 18
            parts.append('<tr>')
            parts.append(f'<td class="{kcls}" style="padding-left:{pad}px">{r["label"]}</td>')
            for c in r.get('cells', []):
                parts.append(f'<td{cattr}>{c}</td>')
            for s in r.get('summary', []):
                parts.append(f'<td{cattr}>{s}</td>')
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


def write_report_to_database(conn, rows, date_cols, summary_cols, output_table, report_title, report_style, output_parent_laui , least_action_task_object):
    """
    Write HTML report to database table and send to catalog API.

    Args:
        conn: PostgreSQL connection object
        rows: hierarchical report rows from build_report_rows
        date_cols: date-column labels
        summary_cols: right-hand analytic column definitions
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

        table_html = generate_styled_html_table(rows, date_cols, summary_cols, report_style)

        generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = html_template.format(
            report_title=report_title,
            generation_time=generation_time,
            num_metrics=sum(1 for r in rows if r.get('kind') == 'item'),
            num_dates=len(date_cols),
            table_html=table_html,
            font_family=report_style.get('font_family', 'Arial, sans-serif'),
            header_bg_color=report_style.get('header_bg_color', '#4CAF50'),
            header_text_color=report_style.get('header_text_color', '#FFFFFF'),
            border_color=report_style.get('border_color', '#dddddd'),
            row_hover_color=report_style.get('row_hover_color', '#e8f5e9')
        )

        # Write to database table
        cursor = conn.cursor()
        
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
        metrics_count = sum(1 for r in rows if r.get('kind') == 'item')
        date_range_count = len(date_cols)
        
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
        metric_template = payload_data.get('metric_template') or []
        report_style = payload_data.get('report_style', {})
        output_parent_laui = payload_data.get('output_parent_laui')

        # Report-level layout: how many recent date columns + which right-hand
        # analytic columns to render, and how far back to pull for trend/stats.
        report_opts = {
            'date_columns': payload_data.get('date_columns', 4),
            'summary_columns': payload_data.get('summary_columns', []),
        }
        trend_weeks = int(payload_data.get('trend_weeks', 12))

        # Pull only the metric_keys the templates need: each base metric plus the
        # derived suffixes required by its variance rows / the summary columns.
        summary_keys = set(report_opts.get('summary_columns') or [])
        needed_keys = set()
        for t in metric_template:
            base = t.get('metric_key')
            if not base:
                continue
            needed_keys.add(base)
            wanted_suffixes = set()
            for vr in (t.get('variance_rows') or []):
                suf = VAR_SUFFIX.get(vr)
                if suf:
                    wanted_suffixes.add(suf)
            if 'dod' in summary_keys:
                wanted_suffixes.add('_dod')
            if 'yoy' in summary_keys:
                wanted_suffixes.add('_yoy')
            if 'lwsd' in summary_keys:
                wanted_suffixes.add('_wow')
            for suf in wanted_suffixes:
                needed_keys.add(base + suf)

        # Grouping shapes to restrict the SQL pull to only what the report renders
        # (memory guard against pulling the whole cube).
        grouping_patterns = [t.get('dim_key_grouping') for t in metric_template if t.get('dim_key_grouping')]

        log_info(
            "task",
            "run",
            "configuration_loaded",
            f"Report title: {report_title}, Output table: {output_table}"
        )

        # Load data from database (trailing window, only the needed metric_keys)
        df = load_data_from_database(client, query_config, needed_keys=needed_keys, window_weeks=trend_weeks, grouping_patterns=grouping_patterns)

        # Build the hierarchical, multi-column report
        rows, date_cols, summary_cols = build_report_rows(df, metric_template, report_opts)

        # Write HTML report to database and send to catalog API
        output_table_name = write_report_to_database(client, rows, date_cols, summary_cols, output_table, report_title, report_style, output_parent_laui , least_action_task_object)

        result = {
            'status': 'success',
            'execution_type': 'sync',
            'result': {
                'output_table': output_table_name,
                'report_title': report_title,
                'metrics_count': sum(1 for r in rows if r.get('kind') == 'item'),
                'date_range_count': len(date_cols),
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
    "Generate an analyst-grade, hierarchical HTML report from a PostgreSQL CUBE-transformed fact table and publish to the LeastAction catalog. "
    "Payload is a JSON config with: report_title, output_table, output_parent_laui, query (table + optional date_filter + limit), "
    "date_columns (how many recent dates to show), trend_weeks (trailing window pulled for trend/stats), "
    "summary_columns (right-hand analytic columns, any of trend/std/wow/yoy/lwsd/share), "
    "metric_template (list of blocks: display_name, show_display_name, dim_key_grouping, dim_value, metric_key, cell_format, colors, "
    "indent, sort_order key|value, limit, variance_rows any of dod/lwsd/yoy), and report_style. "
    "Each block renders a section header + one row per '*'-expanded dimension value (or a single row for a fixed grouping) plus indented "
    "%-variance sub-rows. Analytic columns and variances derive from cube metrics already present (<base>_dod/_wow/_yoy/_pct_of_total). "
    "Writes report HTML to PostgreSQL output_table and publishes as an html_report catalog item."
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
