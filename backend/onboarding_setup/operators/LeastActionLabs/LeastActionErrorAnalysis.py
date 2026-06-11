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
operator_type = "leastaction"

codeblock = {"main.py": '''
"""
LeastAction Error Analysis Operator

Reads PERFORMANCE and verbose API logs via DuckDB, performs deep-dive error
analysis per operation (error distribution, failing PKs, per-minute timeline,
verbose session samples), generates a self-contained HTML report, and publishes
it as an html_report asset to the LeastAction catalog.

Payload fields:
  date        - Logical date YYYY-MM-DD (primary; sets a full-day 24h window)
  start_date  - ISO datetime fallback window start (used when date is not set)
  end_date    - ISO datetime fallback window end (used when date is not set)
  operations  - List of operations to deep-dive (empty = all ops with errors)
  parent_laui - Catalog folder LAUI to publish the report under
  report_name - Display name for the catalog item (optional)
  email_to    - List of recipient email addresses (optional)
  email_from  - Sender address (must match smtp_user for Gmail)
"""

import email.mime.application
import email.mime.multipart
import email.mime.text
import json
import os
import re
import smtplib
import traceback as _traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from src.common.logger.logger import log_info, log_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_payload(least_action_task_object):
    payload = least_action_task_object.get("payload", {})
    log_info("task", "parse_payload", "raw_payload", f"Raw payload type: {type(payload)}, value: {str(payload)[:500]}")

    if isinstance(payload, str):
        try:
            cleaned = re.sub(r\',\\s*([}\\]])\', r\'\', payload)
            payload = json.loads(cleaned)
        except Exception as e:
            log_error("task", "parse_payload", "json_parse_error", f"Failed to parse payload string: {e}")
            payload = {}

    payload_data = payload.get("data", payload)

    if isinstance(payload_data, str):
        try:
            cleaned = re.sub(r\',\\s*([}\\]])\', r\'\', payload_data)
            payload_data = json.loads(cleaned)
        except Exception as e:
            log_error("task", "parse_payload", "data_parse_error", f"Failed to parse payload_data string: {e}")
            payload_data = {}

    now = datetime.now(timezone.utc)

    date_single = payload_data.get("date", "")
    start_raw   = payload_data.get("start_date", "")
    end_raw     = payload_data.get("end_date", "")
    parent_laui = payload_data.get("parent_laui", "")
    report_name = payload_data.get("report_name", "")
    operations  = payload_data.get("operations", [])
    email_to    = payload_data.get("email_to", [])
    email_from  = payload_data.get("email_from", "")

    def _parse_dt(s, fallback):
        if not s:
            return fallback
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except Exception:
            return fallback

    if date_single:
        try:
            d = datetime.strptime(date_single, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_dt = d
            end_dt   = d.replace(hour=23, minute=59, second=59)
        except Exception:
            start_dt = now - timedelta(hours=24)
            end_dt   = now
    else:
        start_dt = _parse_dt(start_raw, now - timedelta(hours=24))
        end_dt   = _parse_dt(end_raw, now)

    if isinstance(operations, str):
        operations = [o.strip() for o in operations.split(",") if o.strip()]
    if isinstance(email_to, str):
        email_to = [e.strip() for e in email_to.split(",") if e.strip()]

    log_info("task", "parse_payload", "final_result",
             f"start_dt={start_dt}, end_dt={end_dt}, operations={operations}, parent_laui=\'{parent_laui}\'")

    return {
        "start_dt":    start_dt,
        "end_dt":      end_dt,
        "operations":  operations,
        "parent_laui": parent_laui,
        "report_name": report_name,
        "email_to":    email_to,
        "email_from":  email_from,
    }


def _logs_base() -> Path:
    return Path(os.getenv("LOGS_DIR", "/logs"))


# ---------------------------------------------------------------------------
# DuckDB queries
# ---------------------------------------------------------------------------

def _read_cron_heartbeat_logs(logs_base: Path, start_dt: datetime, end_dt: datetime):
    """Read CRON heartbeat_resources entries."""
    import pandas as pd

    cron_dir = logs_base / "category=CRON"
    if not cron_dir.exists() or not list(cron_dir.rglob("*.log")):
        log_info("task", "run", "cron_logs_missing", f"No CRON logs at {cron_dir}")
        return pd.DataFrame()

    import duckdb

    glob    = str(cron_dir / "project=*/yyyy=*/mm=*/dd=*/cron.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    query = f"""
        SELECT
            timestamp,
            TRY_CAST(json_extract_string(message, \'$.cpu_percent_system\')        AS DOUBLE) AS cpu_percent_system,
            TRY_CAST(json_extract_string(message, \'$.cpu_percent_process\')       AS DOUBLE) AS cpu_percent_process,
            TRY_CAST(json_extract_string(message, \'$.memory_rss_mb\')             AS DOUBLE) AS memory_rss_mb,
            TRY_CAST(json_extract_string(message, \'$.memory_system_used_pct\')    AS DOUBLE) AS memory_system_used_pct,
            TRY_CAST(json_extract_string(message, \'$.memory_system_available_mb\') AS DOUBLE) AS memory_system_available_mb
        FROM read_json(\'{glob}\', format=\'newline_delimited\', ignore_errors=true)
        WHERE step = \'heartbeat_resources\'
          AND timestamp >= \'{start_s}\' AND timestamp <= \'{end_s}\'
        ORDER BY timestamp
    """
    try:
        df = duckdb.execute(query).df()
        if df.empty:
            return pd.DataFrame()
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        return df
    except Exception as e:
        log_error("task", "run", "cron_duckdb_error", f"DuckDB CRON read failed: {e}")
        return pd.DataFrame()


def _build_cron_series(cron_df):
    if cron_df is None or cron_df.empty:
        return None
    return {
        "labels":            [t.strftime("%Y-%m-%d %H:%M:%S") for t in cron_df["timestamp"]],
        "cpu_system":        cron_df["cpu_percent_system"].fillna(0).round(2).tolist(),
        "cpu_process":       cron_df["cpu_percent_process"].fillna(0).round(2).tolist(),
        "memory_rss_mb":     cron_df["memory_rss_mb"].fillna(0).round(2).tolist(),
        "memory_system_pct": cron_df["memory_system_used_pct"].fillna(0).round(2).tolist(),
    }

def _overall_summary(logs_base: Path, start_dt: datetime, end_dt: datetime) -> list:
    """Per-operation error/latency summary over the time window."""
    import pandas as pd

    perf_dir = logs_base / "category=PERFORMANCE"
    if not perf_dir.exists() or not list(perf_dir.rglob("*.log")):
        return []

    import duckdb

    glob    = str(perf_dir / "yyyy=*/mm=*/dd=*/*.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    q = f"""
        SELECT
            operation,
            COUNT(*) AS total,
            SUM(CASE WHEN message LIKE \'{{%\'
                      AND json_extract_string(message, \'$.error\') IS NOT NULL
                      THEN 1 ELSE 0 END) AS errors,
            ROUND(AVG(
                CASE WHEN message LIKE \'{{%\'
                     THEN TRY_CAST(json_extract_string(message, \'$.execution_time\') AS DOUBLE) * 1000
                     ELSE TRY_CAST(message AS DOUBLE) * 1000 END
            ), 2) AS avg_ms,
            ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY
                CASE WHEN message LIKE \'{{%\'
                     THEN TRY_CAST(json_extract_string(message, \'$.execution_time\') AS DOUBLE) * 1000
                     ELSE TRY_CAST(message AS DOUBLE) * 1000 END
            ), 2) AS p95_ms,
            ROUND(MAX(
                CASE WHEN message LIKE \'{{%\'
                     THEN TRY_CAST(json_extract_string(message, \'$.execution_time\') AS DOUBLE) * 1000
                     ELSE TRY_CAST(message AS DOUBLE) * 1000 END
            ), 2) AS max_ms
        FROM read_json(
            \'{glob}\',
            format            = \'newline_delimited\',
            hive_partitioning = true,
            ignore_errors     = true
        )
        WHERE timestamp >= \'{start_s}\' AND timestamp <= \'{end_s}\'
        GROUP BY operation
        ORDER BY errors DESC, total DESC
    """
    try:
        df = duckdb.execute(q).df()
        return df.to_dict("records")
    except Exception as e:
        log_error("task", "run", "summary_duckdb_error", f"Overall summary query failed: {e}")
        return []


def _get_error_sessions(logs_base: Path, start_dt: datetime, end_dt: datetime, operations: list) -> "pd.DataFrame":
    """Pull error records from PERFORMANCE logs for the given operations."""
    import pandas as pd

    perf_dir = logs_base / "category=PERFORMANCE"
    if not perf_dir.exists() or not list(perf_dir.rglob("*.log")):
        return pd.DataFrame()

    import duckdb

    glob    = str(perf_dir / "yyyy=*/mm=*/dd=*/*.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    ops_filter = ""
    if operations:
        ops_list   = ", ".join(f"\'{o}\'" for o in operations)
        ops_filter = f"AND operation IN ({ops_list})"

    q = f"""
        SELECT
            timestamp,
            operation,
            session_id,
            CASE
                WHEN message LIKE \'{{%\'
                THEN json_extract_string(message, \'$.error\')
                ELSE NULL
            END AS error_msg,
            CASE
                WHEN message LIKE \'{{%\'
                THEN TRY_CAST(json_extract_string(message, \'$.execution_time\') AS DOUBLE) * 1000
                ELSE TRY_CAST(message AS DOUBLE) * 1000
            END AS duration_ms
        FROM read_json(
            \'{glob}\',
            format            = \'newline_delimited\',
            hive_partitioning = true,
            ignore_errors     = true
        )
        WHERE timestamp >= \'{start_s}\' AND timestamp <= \'{end_s}\'
          {ops_filter}
          AND message LIKE \'{{%\'
          AND json_extract_string(message, \'$.error\') IS NOT NULL
        ORDER BY timestamp
    """
    try:
        df = duckdb.execute(q).df()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        return df
    except Exception as e:
        log_error("task", "run", "error_sessions_duckdb_error", f"Error sessions query failed: {e}")
        return pd.DataFrame()


def _get_verbose_for_sessions(logs_base: Path, start_dt: datetime, end_dt: datetime,
                               session_ids: list) -> "pd.DataFrame":
    """Pull verbose API logs for a set of session_ids."""
    import pandas as pd

    verbose_dir = logs_base / "verbose=NON_TASK"
    if not verbose_dir.exists():
        return pd.DataFrame()
    if not list(verbose_dir.rglob("*.log")):
        return pd.DataFrame()

    import duckdb

    glob    = str(verbose_dir / "yyyy=*/mm=*/dd=*/session_id=*/category=API/*.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
    ids_list = ", ".join(f"\'{s}\'" for s in session_ids)

    q = f"""
        SELECT timestamp, level, step, operation, session_id, message
        FROM read_json(\'{glob}\', format=\'newline_delimited\', ignore_errors=true)
        WHERE session_id IN ({ids_list})
          AND timestamp >= \'{start_s}\' AND timestamp <= \'{end_s}\'
        ORDER BY session_id, timestamp
    """
    try:
        df = duckdb.execute(q).df()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        return df
    except Exception as e:
        log_error("task", "run", "verbose_duckdb_error", f"Verbose sessions query failed: {e}")
        return pd.DataFrame()


def _get_perf_context_for_sessions(logs_base: Path, start_dt: datetime, end_dt: datetime,
                                    session_ids: list) -> "pd.DataFrame":
    """Pull all PERF events for the given session_ids (cross-reference context)."""
    import pandas as pd

    perf_dir = logs_base / "category=PERFORMANCE"
    if not perf_dir.exists():
        return pd.DataFrame()

    import duckdb

    glob     = str(perf_dir / "yyyy=*/mm=*/dd=*/*.log")
    start_s  = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s    = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
    ids_list = ", ".join(f"\'{s}\'" for s in session_ids)

    q = f"""
        SELECT
            timestamp, operation, session_id,
            CASE WHEN message LIKE \'{{%\'
                 THEN json_extract_string(message, \'$.error\')
                 ELSE NULL END AS error_msg,
            CASE WHEN message LIKE \'{{%\'
                 THEN TRY_CAST(json_extract_string(message, \'$.execution_time\') AS DOUBLE) * 1000
                 ELSE TRY_CAST(message AS DOUBLE) * 1000 END AS duration_ms
        FROM read_json(
            \'{glob}\',
            format            = \'newline_delimited\',
            hive_partitioning = true,
            ignore_errors     = true
        )
        WHERE session_id IN ({ids_list})
          AND timestamp >= \'{start_s}\' AND timestamp <= \'{end_s}\'
        ORDER BY session_id, timestamp
    """
    try:
        df = duckdb.execute(q).df()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        return df
    except Exception as e:
        log_error("task", "run", "perf_context_duckdb_error", f"PERF context query failed: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Analysis builder
# ---------------------------------------------------------------------------

def _analyse_operation(op_name: str, err_df: "pd.DataFrame",
                        logs_base: Path, start_dt: datetime, end_dt: datetime) -> dict:
    """
    Build a structured analysis dict for one operation.
    Returns everything needed to render the HTML section.
    """
    import pandas as pd

    op_errors = err_df[err_df["operation"] == op_name].copy()
    if op_errors.empty:
        return {"operation": op_name, "total_errors": 0, "unique_sessions": 0}

    # Error distribution (top 10)
    error_dist = (
        op_errors["error_msg"]
        .fillna("(no message)")
        .value_counts()
        .head(10)
        .reset_index()
    )
    error_dist.columns = ["error_msg", "count"]

    # PK extraction (best-effort for get_item_by_pk style errors)
    op_errors["pk"] = op_errors["error_msg"].str.extract(r"\'pk\':\\s*\'([^\']+)\'")
    pk_counts = (
        op_errors["pk"]
        .dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )
    pk_counts.columns = ["pk", "count"]

    # task_laui extraction (for dequeue_task style errors)
    op_errors["task_laui"] = op_errors["error_msg"].str.extract(r"task_laui:(\\S+)")

    # Errors by minute — top 10 busiest
    op_errors["minute"] = op_errors["timestamp"].dt.floor("1min")
    by_minute = (
        op_errors.groupby("minute")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
        .sort_values("minute")
    )

    # Verbose context for sample sessions
    sample_sessions = op_errors["session_id"].dropna().unique()[:3].tolist()
    verbose_samples = []
    perf_context    = []

    if sample_sessions:
        verbose_df = _get_verbose_for_sessions(logs_base, start_dt, end_dt, sample_sessions)
        if not verbose_df.empty:
            for sid in sample_sessions:
                rows = verbose_df[verbose_df["session_id"] == sid]
                entries = []
                for _, row in rows.iterrows():
                    entries.append({
                        "level":     str(row.get("level", ""))[:10],
                        "step":      str(row.get("step", ""))[:50],
                        "message":   str(row.get("message", ""))[:300],
                    })
                if entries:
                    verbose_samples.append({"session_id": sid, "entries": entries})

        ctx_df = _get_perf_context_for_sessions(logs_base, start_dt, end_dt, sample_sessions)
        if not ctx_df.empty:
            for sid in sample_sessions:
                rows = ctx_df[ctx_df["session_id"] == sid]
                entries = []
                for _, r in rows.iterrows():
                    entries.append({
                        "operation":  str(r.get("operation", ""))[:50],
                        "duration_ms": round(r.get("duration_ms") or 0, 1),
                        "error_msg":  str(r.get("error_msg", "") or "")[:120],
                    })
                if entries:
                    perf_context.append({"session_id": sid, "entries": entries})

    return {
        "operation":       op_name,
        "total_errors":    len(op_errors),
        "unique_sessions": int(op_errors["session_id"].nunique()),
        "error_dist":      error_dist.to_dict("records"),
        "pk_counts":       pk_counts.to_dict("records"),
        "task_lauis":      op_errors[["timestamp", "task_laui", "error_msg"]].dropna(
                               subset=["task_laui"]).head(10).assign(
                               timestamp=lambda df: df["timestamp"].astype(str).str[:19]
                           ).to_dict("records"),
        "by_minute":       by_minute.assign(
                               minute=lambda df: df["minute"].astype(str).str[:16]
                           ).to_dict("records"),
        "verbose_samples": verbose_samples,
        "perf_context":    perf_context,
    }


# ---------------------------------------------------------------------------
# SVG chart helpers
# ---------------------------------------------------------------------------

def _svg_line(labels, datasets, y_label="", y_max=None, height=220):
    W, H = 860, height
    PL, PR, PT, PB = 58, 20, 28, 52
    iw, ih = W - PL - PR, H - PT - PB
    n = len(labels)
    if n == 0:
        return \'<p style="color:#aaa;font-style:italic;padding:12px">No data</p>\'
    all_vals = [v for ds in datasets for v in (ds.get("data") or []) if v is not None]
    if not all_vals:
        return \'<p style="color:#aaa;font-style:italic;padding:12px">No data</p>\'
    ymx = (y_max or max(all_vals) * 1.1) or 1.0

    def xp(i): return PL + (i / max(n - 1, 1)) * iw
    def yp(v): return (PT + ih - (v / ymx) * ih) if v is not None else None

    COLORS = ["#667eea", "#e05c5c", "#36b37e", "#f59e0b", "#8b5cf6", "#06b6d4"]
    o = [f\'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">\']
    for k in range(5):
        gy = round(PT + (k / 4) * ih)
        gv = ymx * (1 - k / 4)
        o.append(f\'<line x1="{PL}" y1="{gy}" x2="{PL+iw}" y2="{gy}" stroke="#f0f0f0" stroke-width="1"/>\')
        o.append(f\'<text x="{PL-4}" y="{gy+4}" text-anchor="end" font-size="10" fill="#bbb">{gv:.1f}</text>\')
    o.append(f\'<line x1="{PL}" y1="{PT}" x2="{PL}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>\')
    o.append(f\'<line x1="{PL}" y1="{PT+ih}" x2="{PL+iw}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>\')
    step = max(1, n // 12)
    for i in range(0, n, step):
        x   = round(xp(i))
        lbl = str(labels[i])[-16:]
        o.append(f\'<text x="{x}" y="{PT+ih+14}" text-anchor="end" font-size="9" fill="#bbb" transform="rotate(-35,{x},{PT+ih+14})">{lbl}</text>\')
    lx = PL
    for di, ds in enumerate(datasets):
        color = ds.get("color", COLORS[di % len(COLORS)])
        pts   = [(round(xp(i)), round(yp(v))) for i, v in enumerate(ds.get("data") or []) if v is not None]
        if pts:
            poly = " ".join(f"{x},{y}" for x, y in pts)
            area = f"{PL},{PT+ih} {poly} {pts[-1][0]},{PT+ih}"
            o.append(f\'<polygon points="{area}" fill="{color}" opacity="0.07"/>\')
            o.append(f\'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>\')
        label_txt = ds.get("label", "")[:28]
        o.append(f\'<rect x="{lx}" y="8" width="10" height="10" fill="{color}" rx="2"/>\')
        o.append(f\'<text x="{lx+14}" y="17" font-size="10" fill="#666">{label_txt}</text>\')
        lx += max(len(label_txt) * 7 + 20, 130)
        if lx > W - 80:
            break
    o.append(\'</svg>\')
    return "".join(o)


def _svg_hbar(labels, values, color="#e05c5c", bar_h=22, gap=5):
    if not labels:
        return \'<p style="color:#aaa;font-style:italic;padding:12px">No data</p>\'
    W  = 860
    PL, PR, PT, PB = 220, 70, 8, 8
    iw = W - PL - PR
    mx = max(values) if values else 1
    H  = PT + PB + len(labels) * (bar_h + gap)
    o  = [f\'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">\']
    for i, (lbl, val) in enumerate(zip(labels, values)):
        y  = PT + i * (bar_h + gap)
        bw = round((val / mx) * iw) if mx else 0
        o.append(f\'<text x="{PL-6}" y="{y+bar_h-5}" text-anchor="end" font-size="11" fill="#555">{str(lbl)[:36]}</text>\')
        o.append(f\'<rect x="{PL}" y="{y}" width="{bw}" height="{bar_h}" fill="{color}" rx="3" opacity="0.8"/>\')
        o.append(f\'<text x="{PL+bw+5}" y="{y+bar_h-5}" font-size="11" fill="#888">{val:,}</text>\')
    o.append(\'</svg>\')
    return "".join(o)


def _svg_vbar(labels, values, color="#e05c5c", height=200):
    if not labels:
        return \'<p style="color:#aaa;font-style:italic;padding:12px">No data</p>\'
    W, H = 860, height
    PL, PR, PT, PB = 40, 20, 20, 38
    iw, ih = W - PL - PR, H - PT - PB
    n  = len(labels)
    mx = max(values) if values else 1
    bw = max(4, min(60, int(iw / n) - 4))
    o  = [f\'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">\']
    o.append(f\'<line x1="{PL}" y1="{PT}" x2="{PL}" y2="{PT+ih}" stroke="#ddd"/>\')
    o.append(f\'<line x1="{PL}" y1="{PT+ih}" x2="{PL+iw}" y2="{PT+ih}" stroke="#ddd"/>\')
    for i, (lbl, val) in enumerate(zip(labels, values)):
        x  = round(PL + i * (iw / n) + (iw / n - bw) / 2)
        bh = round((val / mx) * ih) if mx else 0
        y  = PT + ih - bh
        cx = round(x + bw / 2)
        o.append(f\'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{color}" rx="2" opacity="0.78"/>\')
        o.append(f\'<text x="{cx}" y="{PT+ih+14}" text-anchor="middle" font-size="9" fill="#bbb">{str(lbl)[-16:]}</text>\')
    o.append(\'</svg>\')
    return "".join(o)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _generate_html(summary_rows: list, operation_analyses: list,
                   start_dt: datetime, end_dt: datetime,
                   cron_series: dict = None) -> str:
    from jinja2 import Template

    svg_cpu = _svg_line(
        cron_series["labels"],
        [
            {"label": "System CPU %",  "data": cron_series["cpu_system"],  "color": "#667eea"},
            {"label": "Process CPU %", "data": cron_series["cpu_process"], "color": "#e05c5c"},
        ],
        y_label="%", y_max=100,
    ) if cron_series else ""

    svg_mem = _svg_line(
        cron_series["labels"],
        [
            {"label": "Process RSS (MB)",    "data": cron_series["memory_rss_mb"],     "color": "#36b37e"},
            {"label": "System Memory Used %", "data": cron_series["memory_system_pct"], "color": "#f59e0b"},
        ],
    ) if cron_series else ""

    for a in operation_analyses:
        if a.get("error_dist"):
            a["svg_error_dist"] = _svg_hbar(
                [r["error_msg"][:60] for r in a["error_dist"]],
                [r["count"]          for r in a["error_dist"]],
            )
        else:
            a["svg_error_dist"] = ""

        if a.get("pk_counts"):
            a["svg_pk"] = _svg_hbar(
                [r["pk"]    for r in a["pk_counts"]],
                [r["count"] for r in a["pk_counts"]],
                color="#8b5cf6",
            )
        else:
            a["svg_pk"] = ""

        if a.get("by_minute"):
            a["svg_timeline"] = _svg_vbar(
                [r["minute"] for r in a["by_minute"]],
                [r["count"]  for r in a["by_minute"]],
            )
        else:
            a["svg_timeline"] = ""

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>LeastAction Error Analysis</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;background:#f5f7fa;color:#333;line-height:1.5}
    .container{max-width:1400px;margin:0 auto;padding:20px}
    header{background:linear-gradient(135deg,#e05c5c 0%,#9b1c1c 100%);color:#fff;padding:28px 32px;border-radius:10px;margin-bottom:22px;box-shadow:0 4px 12px rgba(0,0,0,.12)}
    header h1{font-size:1.9rem;margin-bottom:6px}
    .meta{opacity:.85;font-size:.9em;margin-top:3px}
    .section{background:#fff;padding:26px 28px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.07);margin-bottom:22px}
    h2{color:#e05c5c;font-size:1.25em;border-bottom:2px solid #fde8ea;padding-bottom:8px;margin-bottom:16px}
    h3{color:#555;font-size:1em;margin:16px 0 8px}
    table{width:100%;border-collapse:collapse;font-size:.88em}
    th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
    th{background:#f8f9fa;font-weight:600;color:#555;font-size:.82em;text-transform:uppercase;letter-spacing:.4px}
    tr:hover{background:#fafbff}
    td.num{text-align:right;font-variant-numeric:tabular-nums}
    .badge-err{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.82em;font-weight:600;background:#fde8ea;color:#9b1c1c}
    .op-header{display:flex;align-items:center;gap:14px;margin-bottom:10px}
    .op-title{font-size:1.1em;font-weight:700;color:#9b1c1c}
    .op-meta{font-size:.88em;color:#888}
    .stat-pills{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}
    .pill{background:#fde8ea;color:#9b1c1c;border-radius:20px;padding:4px 14px;font-size:.85em;font-weight:600}
    .pill.purple{background:#ede9fe;color:#5b21b6}
    .session-block{background:#f8f9fa;border-radius:6px;padding:12px 16px;margin-top:8px;font-size:.83em}
    .session-id{font-weight:700;color:#555;margin-bottom:6px;font-family:monospace}
    .log-row{display:flex;gap:10px;padding:3px 0;border-bottom:1px solid #f0f0f0}
    .log-level{min-width:50px;font-weight:600;color:#e05c5c;font-family:monospace}
    .log-step{min-width:200px;color:#888;font-family:monospace}
    .log-msg{color:#333;word-break:break-all}
    .perf-row{display:flex;gap:10px;padding:3px 0;border-bottom:1px solid #f0f0f0;font-size:.85em;font-family:monospace}
    .perf-op{min-width:240px;color:#555}
    .perf-ms{min-width:80px;text-align:right;color:#888}
    .perf-err{color:#e05c5c;word-break:break-all}
    .alert-yellow{background:#fff3cd;border-left:4px solid #ffc107;padding:13px 16px;border-radius:6px;margin-bottom:14px;font-size:.93em}
    .footer{text-align:center;color:#bbb;font-size:.8em;margin-top:28px;padding-bottom:20px}
  </style>
</head>
<body>
<div class="container">

<header>
  <h1>LeastAction Error Analysis</h1>
  <p class="meta">Generated: {{ generated_at }}</p>
  <p class="meta">Period: {{ period_start }} &rarr; {{ period_end }}</p>
</header>

{% if not summary_rows %}
<div class="section">
  <div class="alert-yellow"><strong>No performance data found</strong> for the selected time range.</div>
</div>
{% else %}

<!-- Overall summary -->
<div class="section">
  <h2>Performance Summary &mdash; All Operations</h2>
  <table>
    <thead><tr>
      <th>Operation</th>
      <th class="num">Total</th>
      <th class="num">Errors</th>
      <th class="num">Error %</th>
      <th class="num">Avg (ms)</th>
      <th class="num">P95 (ms)</th>
      <th class="num">Max (ms)</th>
    </tr></thead>
    <tbody>
    {% for r in summary_rows %}
    <tr>
      <td><strong>{{ r.operation }}</strong></td>
      <td class="num">{{ r.total }}</td>
      <td class="num">{% if r.errors > 0 %}<span class="badge-err">{{ r.errors }}</span>{% else %}0{% endif %}</td>
      <td class="num">{% if r.total > 0 %}{{ "%.1f"|format(r.errors / r.total * 100) }}%{% else %}—{% endif %}</td>
      <td class="num">{{ r.avg_ms }}</td>
      <td class="num">{{ r.p95_ms }}</td>
      <td class="num">{{ r.max_ms }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>

{% endif %}

<!-- Per-operation deep dives -->
{% for a in operation_analyses %}
{% if a.total_errors == 0 %}
<div class="section">
  <div class="op-header">
    <span class="op-title">{{ a.operation }}</span>
    <span class="op-meta">No errors found in range</span>
  </div>
</div>
{% else %}
<div class="section">
  <h2>{{ a.operation }}</h2>
  <div class="stat-pills">
    <span class="pill">{{ a.total_errors }} errors</span>
    <span class="pill">{{ a.unique_sessions }} sessions</span>
  </div>

  {% if a.svg_error_dist %}
  <h3>Error Distribution (top 20)</h3>
  {{ a.svg_error_dist | safe }}
  {% endif %}

  {% if a.svg_pk %}
  <h3>Failing PKs (top 30)</h3>
  {{ a.svg_pk | safe }}
  {% endif %}

  {% if a.task_lauis %}
  <h3>Stuck task_lauis</h3>
  <table>
    <thead><tr><th>Timestamp</th><th>task_laui</th><th>Error</th></tr></thead>
    <tbody>
    {% for row in a.task_lauis %}
    <tr>
      <td style="white-space:nowrap">{{ row.timestamp }}</td>
      <td style="font-family:monospace;font-size:.85em">{{ row.task_laui }}</td>
      <td style="font-size:.83em;word-break:break-all;max-width:420px">{{ row.error_msg }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if a.svg_timeline %}
  <h3>Errors by Minute</h3>
  {{ a.svg_timeline | safe }}
  {% endif %}

  {% if a.verbose_samples %}
  <h3>Verbose Context &mdash; {{ a.verbose_samples|length }} sample session(s)</h3>
  {% for sample in a.verbose_samples %}
  <div class="session-block">
    <div class="session-id">{{ sample.session_id }}</div>
    {% for entry in sample.entries %}
    <div class="log-row">
      <span class="log-level">{{ entry.level }}</span>
      <span class="log-step">{{ entry.step }}</span>
      <span class="log-msg">{{ entry.message }}</span>
    </div>
    {% endfor %}
  </div>
  {% endfor %}
  {% endif %}

  {% if a.perf_context %}
  <h3>PERF Context for Same Sessions</h3>
  {% for ctx in a.perf_context %}
  <div class="session-block">
    <div class="session-id">{{ ctx.session_id }}</div>
    {% for entry in ctx.entries %}
    <div class="perf-row">
      <span class="perf-op">{{ entry.operation }}</span>
      <span class="perf-ms">{{ entry.duration_ms }} ms</span>
      {% if entry.error_msg %}<span class="perf-err">{{ entry.error_msg }}</span>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endfor %}
  {% endif %}

</div>
{% endif %}
{% endfor %}

{% if svg_cpu %}
<div class="section"><h2>CPU Usage Over Time (Cron Heartbeat)</h2>{{ svg_cpu | safe }}</div>
{% endif %}

{% if svg_mem %}
<div class="section"><h2>Memory Usage Over Time (Cron Heartbeat)</h2>{{ svg_mem | safe }}</div>
{% endif %}

<div class="footer">LeastAction Error Analysis &mdash; {{ generated_at }}</div>
</div>
</body>
</html>"""

    t = Template(html_template)
    return t.render(
        generated_at       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        period_start       = start_dt.strftime("%Y-%m-%d %H:%M UTC"),
        period_end         = end_dt.strftime("%Y-%m-%d %H:%M UTC"),
        summary_rows       = summary_rows,
        operation_analyses = operation_analyses,
        svg_cpu            = svg_cpu,
        svg_mem            = svg_mem,
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _send_smtp_email(html_content, email_to, email_from, subject, connection):
    if not email_to or not email_from:
        log_info("task", "run", "email_skipped", "email_to or email_from not set — skipping email")
        return

    smtp_host = connection.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(connection.get("smtp_port", 587))
    smtp_user = connection.get("smtp_user", email_from)
    smtp_pass = connection.get("smtp_password", "")

    outer = email.mime.multipart.MIMEMultipart("mixed")
    outer["Subject"] = subject
    outer["From"]    = email_from
    outer["To"]      = ", ".join(email_to)

    alt = email.mime.multipart.MIMEMultipart("alternative")
    alt.attach(email.mime.text.MIMEText(html_content, "html", "utf-8"))
    outer.attach(alt)

    att = email.mime.application.MIMEApplication(
        html_content.encode("utf-8"), Name="la_error_analysis.html"
    )
    att["Content-Disposition"] = \'attachment; filename="la_error_analysis.html"\'
    outer.attach(att)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(email_from, email_to, outer.as_string())

    log_info("task", "run", "email_sent", f"Report emailed to {email_to} via {smtp_host}")


# ---------------------------------------------------------------------------
# 4 Required Operator Methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    log_info("task", "initialize", "start", "Start")
    connection = least_action_task_object.get("connection") or {}
    return {
        "smtp_host":     connection.get("smtp_host", "smtp.gmail.com"),
        "smtp_port":     int(connection.get("smtp_port", 587)),
        "smtp_user":     connection.get("smtp_user", ""),
        "smtp_password": connection.get("smtp_password", ""),
    }


def run(least_action_task_object, client):
    try:
        log_info("task", "run", "start", "Start")

        params      = _parse_payload(least_action_task_object)
        start_dt    = params["start_dt"]
        end_dt      = params["end_dt"]
        operations  = params["operations"]
        parent_laui = params["parent_laui"]
        logs_base   = _logs_base()

        # --- overall summary ---
        log_info("task", "run", "reading_summary", "Computing overall operation summary")
        summary_rows = _overall_summary(logs_base, start_dt, end_dt)
        log_info("task", "run", "summary_done", f"Summary covers {len(summary_rows)} operations")

        # --- determine which operations to deep-dive ---
        if not operations:
            # default: all operations that actually have errors
            operations = [r["operation"] for r in summary_rows if r.get("errors", 0) > 0]
        log_info("task", "run", "operations", f"Deep-diving {len(operations)} operation(s): {operations}")

        # --- read CRON heartbeat ---
        log_info("task", "run", "reading_cron_logs", "Reading CRON heartbeat logs via DuckDB")
        cron_df = _read_cron_heartbeat_logs(logs_base, start_dt, end_dt)
        log_info("task", "run", "cron_loaded", f"Loaded {len(cron_df)} CRON heartbeat records")
        cron_series = _build_cron_series(cron_df)

        # --- fetch all error sessions in one pass ---
        err_df = _get_error_sessions(logs_base, start_dt, end_dt, operations)
        log_info("task", "run", "error_sessions_loaded",
                 f"Loaded {len(err_df)} error records across {err_df[\'operation\'].nunique() if not err_df.empty else 0} operations")

        # --- per-operation analysis ---
        operation_analyses = []
        for op in operations:
            log_info("task", "run", "analysing_op", f"Analysing {op}")
            analysis = _analyse_operation(op, err_df, logs_base, start_dt, end_dt)
            operation_analyses.append(analysis)
            log_info("task", "run", "op_done",
                     f"{op}: {analysis[\'total_errors\']} errors, {analysis[\'unique_sessions\']} sessions")

        # --- generate HTML ---
        log_info("task", "run", "generating_html", "Generating HTML report")
        html_content = _generate_html(summary_rows, operation_analyses, start_dt, end_dt, cron_series)
        log_info("task", "run", "html_generated", f"HTML size: {len(html_content):,} bytes")

        # --- publish to catalog ---
        catalog_result = None
        if parent_laui:
            user_access_token = least_action_task_object.get("user_access_token")
            if user_access_token:
                report_name = params.get("report_name") or f"Error Analysis {datetime.now().strftime(\'%Y-%m-%d %H:%M\')}"
                api_url = "http://backend:8000/api/v1/catalog/create"
                headers = {
                    "Cookie":       f"frontend_token={user_access_token}",
                    "Content-Type": "application/json",
                }
                body = {
                    "item_type":   "html_report",
                    "name":        report_name,
                    "description": "LeastAction Error Analysis Report",
                    "html":        html_content,
                    "parent_laui": parent_laui,
                }
                log_info("task", "run", "posting_to_catalog",
                         f"Posting \'{report_name}\' under parent: {parent_laui}")
                try:
                    resp = requests.post(api_url, json=body, headers=headers, timeout=60)
                    if resp.status_code in (200, 201):
                        catalog_result = resp.json()
                        log_info("task", "run", "catalog_posted", f"Report published: {report_name}")
                    else:
                        log_error("task", "run", "catalog_http_error",
                                  f"Catalog API returned {resp.status_code}: {resp.text[:200]}")
                except Exception as ce:
                    log_error("task", "run", "catalog_post_error", f"Failed to post to catalog: {ce}")
            else:
                log_error("task", "run", "missing_token",
                          "user_access_token not found — catalog publish skipped")
        else:
            log_info("task", "run", "no_parent_laui", "No parent_laui provided — catalog publish skipped")

        # --- send email ---
        if params.get("email_to"):
            log_info("task", "run", "sending_email", f"Sending report via SMTP to {params[\'email_to\']}")
            try:
                subject = (
                    f"LeastAction Error Analysis — "
                    f"{start_dt.strftime(\'%Y-%m-%d %H:%M\')} → {end_dt.strftime(\'%Y-%m-%d %H:%M\')} UTC"
                )
                _send_smtp_email(html_content, params["email_to"], params["email_from"], subject, client)
            except Exception as ee:
                log_error("task", "run", "email_error", f"Email sending failed: {ee}")
        else:
            log_info("task", "run", "email_skipped", "No email_to in payload — email skipped")

        total_errors = sum(a.get("total_errors", 0) for a in operation_analyses)

        return {
            "status":         "success",
            "execution_type": "sync",
            "result": {
                "operations_analysed":    len(operation_analyses),
                "total_errors":           total_errors,
                "summary_operations":     len(summary_rows),
                "cron_heartbeat_records": len(cron_df),
                "catalog_result":         catalog_result,
                "emailed_to":             params.get("email_to", []),
            },
        }

    except Exception as e:
        log_error("task", "run", "unexpected_error",
                  f"Error analysis operator failed: {e}\\n{_traceback.format_exc()}")
        return {
            "status":         "failed",
            "execution_type": "sync",
            "result":         None,
            "error":          str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    try:
        status = run_details.get("status", "unknown")
        if status == "success":
            log_info("task", "check_completion", "success", "Error analysis completed successfully")
            return {
                "status":  "success",
                "message": "Error analysis report generated and published",
                "output":  run_details.get("result"),
            }
        else:
            err = run_details.get("error", "Unknown error")
            log_error("task", "check_completion", "failed", f"Report failed: {err}")
            return {"status": "failed", "message": err, "output": None}
    except Exception as e:
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        log_info(
            "task", "finish", "cleanup",
            f"Task finished with status: {completion_details.get(\'status\', \'unknown\')}"
        )
    except Exception:
        pass
'''}


bashblock = {"main.sh": """#!/bin/bash
pip install duckdb pandas jinja2
echo "LeastActionErrorAnalysis dependencies installed"
"""}

connection = {
    "smtp_host":     "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     "you@gmail.com",
    "smtp_password": "xxxx xxxx xxxx xxxx"
}

payload = {
    "data": {
        "date":        "{{logical_date}}",
        "operations":  [],
        "parent_laui": "",
        "email_to":    [],
        "email_from":  ""
    }
}

prompt = (
    "Read PERFORMANCE and verbose API logs via DuckDB over a configurable time window. "
    "Compute an overall per-operation error/latency summary (total calls, errors, avg/p95/max ms). "
    "For each specified operation perform a deep-dive: error message distribution, failing PK extraction, "
    "stuck task_laui identification, errors-by-minute timeline, verbose session context, and PERF "
    "cross-reference for sample sessions. Generate a self-contained HTML report with inline SVG charts "
    "and publish it as an html_report asset to the LeastAction catalog. "
    "Optionally send the report via SMTP email as an HTML attachment. "
    "Payload fields: date (YYYY-MM-DD logical date — primary field, sets a full-day 24h window), "
    "start_date and end_date (ISO datetime fallback when date is not set, default 24h window), "
    "operations (list of operation names to deep-dive, empty means all operations with errors), "
    "parent_laui (catalog folder), email_to, email_from."
)

install_docs = """# LeastActionErrorAnalysis — Install Guide

## Dependencies

    pip install duckdb
    pip install pandas
    pip install jinja2

## Log Directory Structure Required

    /logs/category=PERFORMANCE/yyyy=*/mm=*/dd=*/*.log
    /logs/verbose=NON_TASK/yyyy=*/mm=*/dd=*/session_id=*/category=API/*.log

Override the default log path via the LOGS_DIR environment variable.

## SMTP Setup (Gmail)

    1. Enable 2FA on the Gmail account
    2. Generate an App Password (Google Account → Security → App Passwords)
    3. Use the app password as smtp_password in connection
    4. smtp_user and email_from must match the Gmail address

## Catalog Publish

    parent_laui must be set to a valid catalog folder LAUI.
    The task object must carry a user_access_token — injected automatically
    by the LeastAction executor when the operator runs in the platform.
"""

guide_docs = """# LeastActionErrorAnalysis — Operator Guide

## What it does

Reads two log categories via DuckDB over a configurable time window:
- PERFORMANCE logs: per-operation call durations and structured error messages
- Verbose API logs: full request context logs keyed by session_id

Computes an overall operation summary (total calls, errors, avg/p95/max latency).
For each operation in the `operations` list performs a deep-dive:
  - Error message frequency distribution
  - Failing PK extraction (for get_item_by_pk-style errors)
  - Stuck task_laui extraction (for dequeue_task-style errors)
  - Errors-by-minute timeline
  - Verbose session context for up to 3 sample sessions
  - PERF event cross-reference for the same sessions

Generates a self-contained HTML report with inline SVG charts. Publishes to the
LeastAction catalog when parent_laui is set. Sends an HTML email attachment when
email_to is provided.

---

## Auth

Catalog publish: user_access_token injected by the LeastAction executor.
Email: smtp_host, smtp_port, smtp_user, smtp_password from connection.

---

## Connection

    {
      "smtp_host":     "smtp.gmail.com",
      "smtp_port":     587,
      "smtp_user":     "you@gmail.com",
      "smtp_password": "xxxx xxxx xxxx xxxx"
    }

---

## Payload

    {
      "data": {
        "date":        "{{logical_date}}",
        "operations":  [],
        "parent_laui": "",
        "email_to":    [],
        "email_from":  ""
      }
    }

| Field        | Required | Default              | Description                                                         |
|--------------|----------|----------------------|---------------------------------------------------------------------|
| date         | No*      | —                    | Logical date YYYY-MM-DD; sets a full-day window (midnight +24h)    |
| start_date   | No       | 24 hours ago         | ISO datetime fallback window start (used when date is not set)      |
| end_date     | No       | now                  | ISO datetime fallback window end (used when date is not set)        |
| operations   | No       | all ops with errors  | List of operation names to deep-dive; empty = all ops with errors   |
| parent_laui  | No       | —                    | Catalog folder LAUI to publish the HTML report under                |
| email_to     | No       | []                   | List of recipient email addresses (or comma-separated string)       |
| email_from   | No       | —                    | Sender address — must match smtp_user for Gmail                     |

*`date` is the recommended primary field when running on a schedule via `{{logical_date}}`.

---

## Output (on success)

    {
      "operations_analysed": 2,
      "total_errors":        47,
      "summary_operations":  12,
      "catalog_result":      { ... },
      "emailed_to":          ["you@example.com"]
    }

---

## Scenarios and Edge Cases

No PERFORMANCE logs in range:
  Report renders with a "No data found" notice. No error is raised.

operations list is empty:
  Automatically deep-dives every operation that has at least one error in the window.

No verbose logs for a session:
  Verbose context section is omitted for that session — not an error.

No parent_laui set:
  Catalog publish is skipped with a log info entry.

No email_to set:
  Email step is skipped silently.

user_access_token missing:
  Catalog publish is skipped with a log error. Email still runs if configured.

LOGS_DIR override:
  Set the LOGS_DIR environment variable to change the default /logs base path.
"""

description = (
    "Reads PERFORMANCE and verbose API logs via DuckDB over a configurable time window and produces "
    "a detailed error analysis report. Computes an overall per-operation summary (total calls, errors, "
    "avg/p95/max latency). For each operation performs a deep-dive: error message distribution, "
    "failing PK extraction, stuck task_laui identification, errors-by-minute timeline, verbose session "
    "context for sample sessions, and PERF cross-reference. Generates a self-contained HTML report "
    "with inline SVG charts. Publishes to the LeastAction catalog when parent_laui is set. "
    "Sends an HTML email attachment via SMTP when email_to is provided. "
    "Auth: catalog uses user_access_token from the task object; email uses SMTP credentials from connection."
)

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Monitoring",
    "tags": ["monitoring", "errors", "debugging", "logs", "duckdb", "html", "report",
             "email", "smtp", "catalog", "traceback", "analysis"],
    "airflow_equivalent": "BashOperator"
}

version_details = {"version": "0.0.0", "core": ["0.*"]}
