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
LeastAction Monitoring Operator

Reads PERFORMANCE, CRON heartbeat, and API_TRACEBACK logs via DuckDB,
computes detailed statistics (min/mean/median/max/p90/p95/p99, error rates),
generates a self-contained HTML report with Chart.js charts, and publishes
it as an html_report asset to the LeastAction catalog.

Payload fields:
  date        - Logical date YYYY-MM-DD (primary; sets a full-day 24h window)
  start_date  - ISO datetime fallback window start (used when date is not set)
  end_date    - ISO datetime fallback window end (used when date is not set)
  parent_laui - Catalog folder LAUI to publish the report under
  report_name - Display name for the catalog item (optional)
  email_to    - List of recipient email addresses (optional)
  email_from  - Sender address (must match smtp_user for Gmail)
"""

import email.mime.application
import email.mime.image
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
            cleaned = re.sub(r',\\s*([}\\]])', r'', payload)
            payload = json.loads(cleaned)
            log_info("task", "parse_payload", "parsed_string", f"Parsed JSON from string: {str(payload)[:500]}")
        except Exception as e:
            log_error("task", "parse_payload", "json_parse_error", f"Failed to parse payload string: {e}")
            payload = {}

    payload_data = payload.get("data", payload)
    log_info("task", "parse_payload", "payload_data", f"Extracted payload_data: {str(payload_data)[:500]}")

    if isinstance(payload_data, str):
        try:
            cleaned = re.sub(r',\\s*([}\\]])', r'', payload_data)
            payload_data = json.loads(cleaned)
            log_info("task", "parse_payload", "parsed_data_string", f"Parsed JSON from data string: {str(payload_data)[:500]}")
        except Exception as e:
            log_error("task", "parse_payload", "data_parse_error", f"Failed to parse payload_data string: {e}")
            payload_data = {}

    now = datetime.now(timezone.utc)
    date_single = payload_data.get("date", "")
    start_raw   = payload_data.get("start_date", "")
    end_raw     = payload_data.get("end_date", "")
    parent_laui = payload_data.get("parent_laui", "")
    report_name = payload_data.get("report_name", "")
    email_to    = payload_data.get("email_to", [])
    email_from  = payload_data.get("email_from", "")

    log_info("task", "parse_payload", "extracted_values",
             f"parent_laui='{parent_laui}', email_to={email_to}, email_from='{email_from}', report_name='{report_name}'")

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
            day = datetime.strptime(date_single[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_dt = day
            end_dt   = day + timedelta(hours=24)
        except Exception:
            start_dt = _parse_dt(start_raw, now - timedelta(hours=24))
            end_dt   = _parse_dt(end_raw, now)
    else:
        start_dt = _parse_dt(start_raw, now - timedelta(hours=24))
        end_dt   = _parse_dt(end_raw, now)

    if isinstance(email_to, str):
        email_to = [e.strip() for e in email_to.split(",") if e.strip()]

    parsed_result = {
        "start_dt":    start_dt,
        "end_dt":      end_dt,
        "parent_laui": parent_laui,
        "report_name": report_name,
        "email_to":    email_to,
        "email_from":  email_from,
    }

    log_info("task", "parse_payload", "final_result",
             f"Parsed params - parent_laui: '{parsed_result['parent_laui']}', "
             f"email_to: {parsed_result['email_to']}, email_from: '{parsed_result['email_from']}'")

    return parsed_result


def _logs_base() -> Path:
    return Path(os.getenv("LOGS_DIR", "/logs"))


def _read_performance_logs(logs_base: Path, start_dt: datetime, end_dt: datetime):
    """Read PERFORMANCE logs and return a DataFrame."""
    import pandas as pd

    perf_dir = logs_base / "category=PERFORMANCE"
    if not perf_dir.exists() or not list(perf_dir.rglob("*.log")):
        log_info("task", "run", "perf_logs_missing", f"No PERFORMANCE logs at {perf_dir}")
        return pd.DataFrame()

    import duckdb

    glob    = str(perf_dir / "yyyy=*/mm=*/dd=*/*.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    query = f"""
        SELECT
            timestamp,
            operation AS function_name,
            CASE
                WHEN message LIKE '{{%'
                THEN TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)
                ELSE TRY_CAST(message AS DOUBLE)
            END AS execution_time_seconds,
            CASE
                WHEN message LIKE '{{%'
                THEN json_extract_string(message, '$.error') IS NOT NULL
                ELSE FALSE
            END AS has_error,
            CASE
                WHEN message LIKE '{{%'
                THEN json_extract_string(message, '$.error')
                ELSE NULL
            END AS error_detail,
            COALESCE(session_id, '') AS session_id
        FROM read_json(
            '{glob}',
            format            = 'newline_delimited',
            hive_partitioning = true,
            ignore_errors     = true
        )
        WHERE timestamp >= '{start_s}' AND timestamp <= '{end_s}'
    """
    try:
        df = duckdb.execute(query).df()
        if df.empty:
            return pd.DataFrame()
        df["timestamp"]   = pd.to_datetime(df["timestamp"], format="ISO8601")
        df["duration_ms"] = df["execution_time_seconds"] * 1000
        return df
    except Exception as e:
        log_error("task", "run", "perf_duckdb_error", f"DuckDB PERFORMANCE read failed: {e}")
        return pd.DataFrame()


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
            TRY_CAST(json_extract_string(message, '$.cpu_percent_system')     AS DOUBLE) AS cpu_percent_system,
            TRY_CAST(json_extract_string(message, '$.cpu_percent_process')    AS DOUBLE) AS cpu_percent_process,
            TRY_CAST(json_extract_string(message, '$.memory_rss_mb')          AS DOUBLE) AS memory_rss_mb,
            TRY_CAST(json_extract_string(message, '$.memory_system_used_pct') AS DOUBLE) AS memory_system_used_pct,
            TRY_CAST(json_extract_string(message, '$.memory_system_available_mb') AS DOUBLE) AS memory_system_available_mb
        FROM read_json(
            '{glob}',
            format        = 'newline_delimited',
            ignore_errors = true
        )
        WHERE step = 'heartbeat_resources'
          AND timestamp >= '{start_s}' AND timestamp <= '{end_s}'
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


def _read_traceback_logs(logs_base: Path, start_dt: datetime, end_dt: datetime):
    """Read API_TRACEBACK error logs."""
    import pandas as pd

    nontask_dir = logs_base / "verbose=NON_TASK"
    if not nontask_dir.exists():
        return pd.DataFrame()
    matching = list(nontask_dir.rglob("*/category=API_TRACEBACK/*.log"))
    if not matching:
        return pd.DataFrame()

    import duckdb

    glob    = str(nontask_dir / "yyyy=*/mm=*/dd=*/session_id=*/category=API_TRACEBACK/*.log")
    start_s = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    query = f"""
        SELECT
            timestamp,
            level,
            message,
            COALESCE(operation, '')  AS operation,
            COALESCE(session_id, '') AS session_id
        FROM read_json(
            '{glob}',
            format        = 'newline_delimited',
            ignore_errors = true
        )
        WHERE level IN ('error', 'critical')
          AND timestamp >= '{start_s}' AND timestamp <= '{end_s}'
        ORDER BY timestamp DESC
        LIMIT 100
    """
    try:
        df = duckdb.execute(query).df()
        if df.empty:
            return pd.DataFrame()
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        return df
    except Exception as e:
        log_error("task", "run", "traceback_duckdb_error", f"DuckDB API_TRACEBACK read failed: {e}")
        return pd.DataFrame()


def _compute_stats(df):
    """Compute per-function and overall stats. Returns (overall_dict, func_stats_list)."""
    import pandas as pd

    if df.empty:
        return {}, []

    overall = {
        "total_calls":  len(df),
        "total_errors": int(df["has_error"].sum()) if "has_error" in df.columns else 0,
        "min_ms":    round(df["duration_ms"].min(), 2),
        "avg_ms":    round(df["duration_ms"].mean(), 2),
        "median_ms": round(df["duration_ms"].median(), 2),
        "max_ms":    round(df["duration_ms"].max(), 2),
        "p90_ms":    round(df["duration_ms"].quantile(0.90), 2),
        "p95_ms":    round(df["duration_ms"].quantile(0.95), 2),
        "p99_ms":    round(df["duration_ms"].quantile(0.99), 2),
    }
    overall["error_rate"] = round(
        (overall["total_errors"] / overall["total_calls"]) * 100, 2
    ) if overall["total_calls"] else 0.0

    func_stats = []
    for func_name, grp in df.groupby("function_name"):
        ms = grp["duration_ms"]
        ec = int(grp["has_error"].sum()) if "has_error" in grp.columns else 0
        func_stats.append({
            "function_name":  func_name,
            "count":          len(grp),
            "min_ms":         round(ms.min(), 2),
            "mean_ms":        round(ms.mean(), 2),
            "median_ms":      round(ms.median(), 2),
            "max_ms":         round(ms.max(), 2),
            "p90_ms":         round(ms.quantile(0.90), 2),
            "p95_ms":         round(ms.quantile(0.95), 2),
            "p99_ms":         round(ms.quantile(0.99), 2),
            "error_count":    ec,
            "error_rate_pct": round((ec / len(grp)) * 100, 2) if len(grp) else 0.0,
        })
    func_stats.sort(key=lambda x: x["max_ms"], reverse=True)
    return overall, func_stats


def _build_time_series(df):
    """Build 15-min time series and hourly aggregates."""
    empty = {
        "ts15_labels": [], "ts15_mean": [], "ts15_max": [],
        "hourly_labels": [], "hourly_counts": [], "hourly_avg_ms": [],
    }
    if df.empty:
        return empty

    COLORS = [
        "#667eea", "#e05c5c", "#36b37e", "#f59e0b", "#8b5cf6",
        "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
        "#a78bfa", "#fb923c", "#34d399", "#60a5fa", "#f472b6",
    ]

    df = df.copy()
    df["time_bucket"] = df["timestamp"].dt.floor("15min")
    df["hour"]        = df["timestamp"].dt.hour

    bucketed = (
        df.groupby(["time_bucket", "function_name"])["duration_ms"]
        .agg(["mean", "max"])
        .round(2)
        .reset_index()
    )
    all_buckets   = sorted(bucketed["time_bucket"].unique())
    all_functions = sorted(bucketed["function_name"].unique())
    bucket_labels = [b.strftime("%Y-%m-%d %H:%M") for b in all_buckets]

    def _series(col):
        out = []
        for i, fn in enumerate(all_functions):
            fd   = bucketed[bucketed["function_name"] == fn].set_index("time_bucket")[col]
            vals = [float(fd[b]) if b in fd.index else None for b in all_buckets]
            out.append({"label": fn, "data": vals, "color": COLORS[i % len(COLORS)]})
        return out

    hourly_calls = df.groupby("hour").size().reset_index(name="count")
    hourly_avg   = (
        df.groupby("hour")["duration_ms"]
        .mean().round(2).reset_index()
        .rename(columns={"duration_ms": "avg_ms"})
    )
    hourly = hourly_calls.merge(hourly_avg, on="hour", how="left").sort_values("hour")

    return {
        "ts15_labels":   bucket_labels,
        "ts15_mean":     _series("mean"),
        "ts15_max":      _series("max"),
        "hourly_labels": hourly["hour"].tolist(),
        "hourly_counts": hourly["count"].tolist(),
        "hourly_avg_ms": hourly["avg_ms"].tolist(),
    }


def _build_cron_series(cron_df):
    """Build CPU/memory series from CRON heartbeat data, or None if empty."""
    if cron_df is None or cron_df.empty:
        return None
    return {
        "labels":            [t.strftime("%Y-%m-%d %H:%M:%S") for t in cron_df["timestamp"]],
        "cpu_system":        cron_df["cpu_percent_system"].fillna(0).round(2).tolist(),
        "cpu_process":       cron_df["cpu_percent_process"].fillna(0).round(2).tolist(),
        "memory_rss_mb":     cron_df["memory_rss_mb"].fillna(0).round(2).tolist(),
        "memory_system_pct": cron_df["memory_system_used_pct"].fillna(0).round(2).tolist(),
        "memory_avail_mb":   cron_df["memory_system_available_mb"].fillna(0).round(2).tolist(),
    }


# ---------------------------------------------------------------------------
# SVG chart helpers  (browser/catalog HTML version only)
# ---------------------------------------------------------------------------

def _svg_line(labels, datasets, y_label="", y_max=None, height=260):
    """Pure SVG line chart — no JavaScript required."""
    W, H = 860, height
    PL, PR, PT, PB = 58, 20, 28, 52
    iw, ih = W - PL - PR, H - PT - PB
    n = len(labels)
    if n == 0:
        return '<p style="color:#aaa;font-style:italic;padding:12px">No data</p>'
    all_vals = [v for ds in datasets for v in (ds.get("data") or []) if v is not None]
    if not all_vals:
        return '<p style="color:#aaa;font-style:italic;padding:12px">No data</p>'
    ymx = (y_max or max(all_vals) * 1.1) or 1.0

    def xp(i): return PL + (i / max(n - 1, 1)) * iw
    def yp(v): return (PT + ih - (v / ymx) * ih) if v is not None else None

    COLORS = ["#667eea", "#e05c5c", "#36b37e", "#f59e0b", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"]
    o = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">']
    for k in range(5):
        gy = round(PT + (k / 4) * ih)
        gv = ymx * (1 - k / 4)
        o.append(f'<line x1="{PL}" y1="{gy}" x2="{PL+iw}" y2="{gy}" stroke="#f0f0f0" stroke-width="1"/>')
        o.append(f'<text x="{PL-4}" y="{gy+4}" text-anchor="end" font-size="10" fill="#bbb">{gv:.1f}</text>')
    o.append(f'<line x1="{PL}" y1="{PT}" x2="{PL}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>')
    o.append(f'<line x1="{PL}" y1="{PT+ih}" x2="{PL+iw}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>')
    step = max(1, n // 12)
    for i in range(0, n, step):
        x   = round(xp(i))
        lbl = str(labels[i])[-16:]
        o.append(f'<text x="{x}" y="{PT+ih+14}" text-anchor="end" font-size="9" fill="#bbb" transform="rotate(-35,{x},{PT+ih+14})">{lbl}</text>')
    cy = H // 2
    o.append(f'<text x="11" y="{cy}" text-anchor="middle" font-size="10" fill="#bbb" transform="rotate(-90,11,{cy})">{y_label}</text>')
    lx = PL
    for di, ds in enumerate(datasets):
        color = ds.get("color", COLORS[di % len(COLORS)])
        pts   = [(round(xp(i)), round(yp(v))) for i, v in enumerate(ds.get("data") or []) if v is not None]
        if pts:
            poly = " ".join(f"{x},{y}" for x, y in pts)
            area = f"{PL},{PT+ih} {poly} {pts[-1][0]},{PT+ih}"
            o.append(f'<polygon points="{area}" fill="{color}" opacity="0.07"/>')
            o.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>')
        label_txt = ds.get("label", "")[:28]
        o.append(f'<rect x="{lx}" y="8" width="10" height="10" fill="{color}" rx="2"/>')
        o.append(f'<text x="{lx+14}" y="17" font-size="10" fill="#666">{label_txt}</text>')
        lx += max(len(label_txt) * 7 + 20, 130)
        if lx > W - 80:
            break
    o.append('</svg>')
    return "".join(o)


def _svg_hbar(labels, values, color="#667eea", bar_h=24, gap=6):
    """Pure SVG horizontal bar chart."""
    if not labels:
        return '<p style="color:#aaa;font-style:italic;padding:12px">No data</p>'
    W  = 860
    PL, PR, PT, PB = 210, 70, 10, 10
    iw = W - PL - PR
    mx = max(values) if values else 1
    H  = PT + PB + len(labels) * (bar_h + gap)
    o  = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">']
    for i, (lbl, val) in enumerate(zip(labels, values)):
        y  = PT + i * (bar_h + gap)
        bw = round((val / mx) * iw) if mx else 0
        o.append(f'<text x="{PL-6}" y="{y+bar_h-6}" text-anchor="end" font-size="11" fill="#555">{str(lbl)[:32]}</text>')
        o.append(f'<rect x="{PL}" y="{y}" width="{bw}" height="{bar_h}" fill="{color}" rx="3" opacity="0.8"/>')
        o.append(f'<text x="{PL+bw+5}" y="{y+bar_h-6}" font-size="11" fill="#888">{val:,}</text>')
    o.append('</svg>')
    return "".join(o)


def _svg_vbar(labels, values, color="#667eea", height=220):
    """Pure SVG vertical bar chart.
    FIX: bar width capped at 60 px — prevents a single time-bucket from
    rendering as a solid colour block filling the entire chart.
    """
    if not labels:
        return '<p style="color:#aaa;font-style:italic;padding:12px">No data</p>'
    W, H = 860, height
    PL, PR, PT, PB = 40, 20, 20, 38
    iw, ih = W - PL - PR, H - PT - PB
    n  = len(labels)
    mx = max(values) if values else 1
    # FIX: cap at 60 px so a single bar never fills the whole chart
    bw = max(4, min(60, int(iw / n) - 4))
    o  = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">']
    o.append(f'<line x1="{PL}" y1="{PT}" x2="{PL}" y2="{PT+ih}" stroke="#ddd"/>')
    o.append(f'<line x1="{PL}" y1="{PT+ih}" x2="{PL+iw}" y2="{PT+ih}" stroke="#ddd"/>')
    for i, (lbl, val) in enumerate(zip(labels, values)):
        x  = round(PL + i * (iw / n) + (iw / n - bw) / 2)
        bh = round((val / mx) * ih) if mx else 0
        y  = PT + ih - bh
        cx = round(x + bw / 2)
        o.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{color}" rx="2" opacity="0.78"/>')
        o.append(f'<text x="{cx}" y="{PT+ih+14}" text-anchor="middle" font-size="10" fill="#bbb">{lbl}</text>')
    o.append('</svg>')
    return "".join(o)


# ---------------------------------------------------------------------------
# Matplotlib chart helpers  (email PNG embedding)
# ---------------------------------------------------------------------------

def _matplotlib_chart_png_bytes(labels, datasets, y_label="", y_max=None, height_in=3.2):
    """Render a line chart with matplotlib and return raw PNG bytes. Returns None on failure."""
    try:
        from io import BytesIO
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        all_vals = [v for ds in datasets for v in (ds.get("data") or []) if v is not None]
        if not all_vals or not labels:
            return None

        COLORS = ["#667eea", "#e05c5c", "#36b37e", "#f59e0b", "#8b5cf6",
                  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6"]

        fig, ax = plt.subplots(figsize=(9.5, height_in), dpi=110)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        x = list(range(len(labels)))
        for di, ds in enumerate(datasets):
            color = ds.get("color", COLORS[di % len(COLORS)])
            data  = [v if v is not None else 0 for v in (ds.get("data") or [])]
            ax.plot(x, data, color=color, linewidth=1.6,
                    label=ds.get("label", ""), solid_capstyle="round")
            ax.fill_between(x, data, alpha=0.07, color=color)

        n     = len(labels)
        step  = max(1, n // 10)
        ticks = list(range(0, n, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels(
            [str(labels[i])[-16:] for i in ticks],
            rotation=35, ha="right", fontsize=7, color="#888"
        )
        ax.tick_params(axis="y", labelsize=8, colors="#aaa")
        ax.set_ylabel(y_label, fontsize=9, color="#aaa")
        if y_max:
            ax.set_ylim(0, y_max)
        else:
            ax.set_ylim(bottom=0)

        ax.grid(axis="y", color="#f0f0f0", linewidth=0.8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#ddd")

        if any(ds.get("label") for ds in datasets):
            ax.legend(fontsize=8, loc="upper right", framealpha=0.6,
                      edgecolor="#ddd", facecolor="#fff")

        plt.tight_layout(pad=0.6)
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log_error("task", "run", "matplotlib_chart_error",
                  f"Failed to generate matplotlib chart: {e}")
        return None


def _matplotlib_hbar_png_bytes(labels, values, color="#667eea"):
    """Render a horizontal bar chart with matplotlib and return raw PNG bytes.

    FIX: used in email mode instead of _svg_hbar because most email clients
    (Gmail, Outlook, Apple Mail) strip or ignore inline SVG, causing all the
    function-name / count text to be rendered as a single concatenated string.
    Matplotlib renders to a proper PNG that embeds cleanly via CID attachment.
    """
    try:
        from io import BytesIO
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if not labels or not values:
            return None

        n      = len(labels)
        fig_h  = max(2.5, n * 0.38)
        fig, ax = plt.subplots(figsize=(9.5, fig_h), dpi=110)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        y_pos = list(range(n))
        ax.barh(y_pos, values, color=color, alpha=0.78, height=0.65)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9, color="#555")
        ax.invert_yaxis()
        ax.tick_params(axis="x", labelsize=8, colors="#aaa")
        ax.set_xlabel("Call count", fontsize=9, color="#aaa")
        ax.grid(axis="x", color="#f0f0f0", linewidth=0.8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#ddd")

        mx = max(values) if values else 1
        for i, v in enumerate(values):
            ax.text(v + mx * 0.01, i, f"{v:,}", va="center", fontsize=8, color="#888")

        plt.tight_layout(pad=0.6)
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log_error("task", "run", "matplotlib_hbar_error",
                  f"Failed to generate hbar chart: {e}")
        return None


def _build_email_png_bytes(time_series, cron_series, func_stats=None):
    """Render all charts as PNG bytes for CID email embedding.

    FIX: accepts func_stats so the most-called horizontal bar is rendered as
    a proper PNG (via _matplotlib_hbar_png_bytes) instead of SVG, which is
    not displayed by email clients.
    """
    pngs = {}

    # Most-called horizontal bar — must be PNG for email
    if func_stats:
        most_called = sorted(func_stats, key=lambda x: x["count"], reverse=True)[:15]
        if most_called:
            pngs["hbar"] = _matplotlib_hbar_png_bytes(
                [f["function_name"] for f in most_called],
                [f["count"]         for f in most_called],
            )

    if time_series.get("ts15_labels"):
        pngs["ts_mean"] = _matplotlib_chart_png_bytes(
            time_series["ts15_labels"], time_series["ts15_mean"], y_label="ms")
        pngs["ts_max"] = _matplotlib_chart_png_bytes(
            time_series["ts15_labels"], time_series["ts15_max"], y_label="ms")

    if time_series.get("hourly_labels"):
        pngs["hourly"] = _matplotlib_chart_png_bytes(
            time_series["hourly_labels"],
            [{"label": "Calls", "data": time_series["hourly_counts"], "color": "#667eea"}],
            y_label="calls")

    if cron_series:
        pngs["cpu"] = _matplotlib_chart_png_bytes(
            cron_series["labels"],
            [
                {"label": "System CPU %",  "data": cron_series["cpu_system"],  "color": "#667eea"},
                {"label": "Process CPU %", "data": cron_series["cpu_process"], "color": "#e05c5c"},
            ],
            y_label="%", y_max=100)
        pngs["mem"] = _matplotlib_chart_png_bytes(
            cron_series["labels"],
            [
                {"label": "Process RSS (MB)", "data": cron_series["memory_rss_mb"],     "color": "#36b37e"},
                {"label": "System Memory %",  "data": cron_series["memory_system_pct"], "color": "#f59e0b"},
            ],
            y_label="")

    return pngs


def _generate_html(overall, func_stats, time_series, cron_series, traceback_df, start_dt, end_dt,
                   for_email=False, png_bytes=None):
    """Render the full HTML monitoring report.
    for_email=False -> SVG charts embedded inline (for browser/catalog).
    for_email=True  -> CID <img> tags referencing PNG bytes (for email clients).
    """
    from jinja2 import Template

    NO_DATA = '<p style="color:#aaa;font-style:italic;padding:12px">No data</p>'

    traceback_rows = []
    if traceback_df is not None and not traceback_df.empty:
        for _, row in traceback_df.head(50).iterrows():
            traceback_rows.append({
                "timestamp":  str(row.get("timestamp", ""))[:19],
                "operation":  str(row.get("operation", ""))[:80],
                "session_id": str(row.get("session_id", ""))[:36],
                "message":    str(row.get("message", ""))[:300],
            })

    most_called = sorted(func_stats, key=lambda x: x["count"], reverse=True)[:15]

    if for_email:
        png_bytes = png_bytes or {}

        def _cid(key):
            return (
                f'<img src="cid:chart_{key}@lamonitoring" '
                f'style="width:100%;max-width:860px;height:auto;display:block" alt="{key} chart">'
                if png_bytes.get(key) else NO_DATA
            )

        # FIX: use PNG CID reference — email clients do not render inline SVG
        svg_most_called = _cid("hbar") if most_called else ""
        svg_hourly      = _cid("hourly")
        svg_ts_mean     = _cid("ts_mean")
        svg_ts_max      = _cid("ts_max")
        svg_cpu         = _cid("cpu")
        svg_mem         = _cid("mem")

    else:
        svg_most_called = _svg_hbar(
            [f["function_name"] for f in most_called],
            [f["count"] for f in most_called],
        ) if most_called else ""

        svg_hourly = _svg_vbar(
            time_series.get("hourly_labels", []),
            time_series.get("hourly_counts", []),
        ) if time_series.get("hourly_labels") else ""

        svg_ts_mean = _svg_line(
            time_series.get("ts15_labels", []),
            time_series.get("ts15_mean", []),
            y_label="ms",
        ) if time_series.get("ts15_labels") else ""

        svg_ts_max = _svg_line(
            time_series.get("ts15_labels", []),
            time_series.get("ts15_max", []),
            y_label="ms",
        ) if time_series.get("ts15_labels") else ""

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
                {"label": "Process RSS (MB)", "data": cron_series["memory_rss_mb"],     "color": "#36b37e"},
                {"label": "System Memory %",  "data": cron_series["memory_system_pct"], "color": "#f59e0b"},
            ],
        ) if cron_series else ""

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>LeastAction Monitoring Report</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#333;line-height:1.5}
    .container{max-width:1400px;margin:0 auto;padding:20px}
    header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:28px 32px;border-radius:10px;margin-bottom:22px;box-shadow:0 4px 12px rgba(0,0,0,.12)}
    header h1{font-size:1.9rem;margin-bottom:6px}
    .meta{opacity:.85;font-size:.9em;margin-top:3px}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px}
    .stat-card{background:#fff;padding:18px 20px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.07)}
    .stat-label{color:#777;font-size:.75em;text-transform:uppercase;letter-spacing:.6px;margin-bottom:7px}
    .stat-value{font-size:1.75em;font-weight:700;color:#667eea}
    .stat-unit{font-size:.52em;color:#aaa;margin-left:3px}
    .stat-value.red{color:#dc3545}
    .section{background:#fff;padding:26px 28px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.07);margin-bottom:22px}
    h2{color:#667eea;font-size:1.25em;border-bottom:2px solid #e8eaf6;padding-bottom:8px;margin-bottom:16px}
    .alert{padding:13px 16px;border-radius:6px;margin-bottom:14px;font-size:.93em}
    .alert-red{background:#f8d7da;border-left:4px solid #dc3545}
    .alert-yellow{background:#fff3cd;border-left:4px solid #ffc107}
    .alert-green{background:#d4edda;border-left:4px solid #28a745}
    table{width:100%;border-collapse:collapse;font-size:.88em}
    th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
    th{background:#f8f9fa;font-weight:600;color:#555;font-size:.82em;text-transform:uppercase;letter-spacing:.4px}
    tr:hover{background:#fafbff}
    td.num{text-align:right;font-variant-numeric:tabular-nums}
    .badge-err{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.82em;font-weight:600;background:#fde8ea;color:#9b1c1c}
    .chart-wrap{position:relative;height:360px;margin-top:14px}
    .chart-wrap-tall{position:relative;height:440px;margin-top:14px}
    .footer{text-align:center;color:#bbb;font-size:.8em;margin-top:28px;padding-bottom:20px}
    .no-data{color:#aaa;font-style:italic;font-size:.9em;text-align:center;padding:24px}
  </style>
</head>
<body>
<div class="container">

<header>
  <h1>LeastAction Monitoring Report</h1>
  <p class="meta">Generated: {{ generated_at }}</p>
  <p class="meta">Period: {{ period_start }} &rarr; {{ period_end }}</p>
</header>

{% if total_calls == 0 %}
<div class="section">
  <div class="alert alert-yellow"><strong>No performance data found</strong> for the selected time range ({{ period_start }} &rarr; {{ period_end }}).</div>
</div>
{% else %}

<div class="stats-grid">
  <div class="stat-card"><div class="stat-label">Total Calls</div><div class="stat-value">{{ total_calls }}</div></div>
  <div class="stat-card"><div class="stat-label">Min</div><div class="stat-value">{{ min_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">Mean</div><div class="stat-value">{{ avg_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">Median</div><div class="stat-value">{{ median_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">P90</div><div class="stat-value">{{ p90_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">P95</div><div class="stat-value">{{ p95_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">P99</div><div class="stat-value">{{ p99_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">Max</div><div class="stat-value">{{ max_ms }}<span class="stat-unit">ms</span></div></div>
  <div class="stat-card"><div class="stat-label">Total Errors</div><div class="stat-value red">{{ total_errors }}</div></div>
  <div class="stat-card"><div class="stat-label">Error Rate</div><div class="stat-value {% if error_rate > 5 %}red{% endif %}">{{ error_rate }}<span class="stat-unit">%</span></div></div>
</div>

{% if error_rate > 5 %}<div class="alert alert-red"><strong>High Error Rate:</strong> {{ error_rate }}% exceeds 5% threshold. Investigate immediately.</div>{% endif %}
{% if p95_ms > 5000 %}<div class="alert alert-yellow"><strong>Slow P95:</strong> {{ p95_ms }}ms exceeds 5s threshold.</div>{% endif %}
{% if error_rate <= 5 and p95_ms <= 5000 %}<div class="alert alert-green"><strong>System Healthy:</strong> Error rate and latency within normal bounds.</div>{% endif %}

<!-- Function Stats Table -->
<div class="section">
  <h2>Function Performance &mdash; sorted by Max</h2>
  <table>
    <thead><tr>
      <th>Function</th>
      <th class="num">Count</th><th class="num">Min (ms)</th><th class="num">Mean (ms)</th>
      <th class="num">Median (ms)</th><th class="num">Max (ms)</th>
      <th class="num">P90 (ms)</th><th class="num">P95 (ms)</th><th class="num">P99 (ms)</th>
      <th class="num">Errors</th><th class="num">Error %</th>
    </tr></thead>
    <tbody>
    {% for f in func_stats %}
    <tr>
      <td><strong>{{ f.function_name }}</strong></td>
      <td class="num">{{ f.count }}</td>
      <td class="num">{{ f.min_ms }}</td>
      <td class="num">{{ f.mean_ms }}</td>
      <td class="num">{{ f.median_ms }}</td>
      <td class="num">{{ f.max_ms }}</td>
      <td class="num">{{ f.p90_ms }}</td>
      <td class="num">{{ f.p95_ms }}</td>
      <td class="num">{{ f.p99_ms }}</td>
      <td class="num">{% if f.error_count > 0 %}<span class="badge-err">{{ f.error_count }}</span>{% else %}0{% endif %}</td>
      <td class="num">{{ f.error_rate_pct }}%</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>

{% if svg_most_called %}
<div class="section"><h2>Most Called Functions (Top 15)</h2>{{ svg_most_called | safe }}</div>
{% endif %}

{% if svg_hourly %}
<div class="section"><h2>Call Volume by Hour</h2>{{ svg_hourly | safe }}</div>
{% endif %}

{% if svg_ts_mean %}
<div class="section"><h2>Mean Duration per Function &mdash; 15-min intervals</h2>{{ svg_ts_mean | safe }}</div>
{% endif %}

{% if svg_ts_max %}
<div class="section"><h2>Max Duration per Function &mdash; 15-min intervals</h2>{{ svg_ts_max | safe }}</div>
{% endif %}

{% endif %}{# end total_calls > 0 #}

{% if svg_cpu %}
<div class="section"><h2>CPU Usage Over Time (Cron Heartbeat)</h2>{{ svg_cpu | safe }}</div>
{% endif %}

{% if svg_mem %}
<div class="section"><h2>Memory Usage Over Time (Cron Heartbeat)</h2>{{ svg_mem | safe }}</div>
{% endif %}

{% if traceback_rows %}
<div class="section">
  <h2>Recent API Errors &mdash; {{ traceback_rows|length }} records</h2>
  <table>
    <thead><tr><th>Timestamp</th><th>Operation</th><th>Session ID</th><th>Message</th></tr></thead>
    <tbody>
    {% for row in traceback_rows %}
    <tr>
      <td style="white-space:nowrap">{{ row.timestamp }}</td>
      <td>{{ row.operation }}</td>
      <td style="font-size:.8em;color:#888">{{ row.session_id }}</td>
      <td style="font-size:.85em;word-break:break-all;max-width:480px">{{ row.message }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<div class="footer">LeastAction Monitoring &mdash; {{ generated_at }}</div>
</div>
</body>
</html>"""

    t = Template(html_template)
    return t.render(
        generated_at    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        period_start    = start_dt.strftime("%Y-%m-%d %H:%M UTC"),
        period_end      = end_dt.strftime("%Y-%m-%d %H:%M UTC"),
        total_calls     = overall.get("total_calls", 0),
        total_errors    = overall.get("total_errors", 0),
        error_rate      = overall.get("error_rate", 0),
        min_ms          = overall.get("min_ms", 0),
        avg_ms          = overall.get("avg_ms", 0),
        median_ms       = overall.get("median_ms", 0),
        max_ms          = overall.get("max_ms", 0),
        p90_ms          = overall.get("p90_ms", 0),
        p95_ms          = overall.get("p95_ms", 0),
        p99_ms          = overall.get("p99_ms", 0),
        func_stats      = func_stats,
        traceback_rows  = traceback_rows,
        svg_most_called = svg_most_called,
        svg_hourly      = svg_hourly,
        svg_ts_mean     = svg_ts_mean,
        svg_ts_max      = svg_ts_max,
        svg_cpu         = svg_cpu,
        svg_mem         = svg_mem,
    )


def _send_smtp_email(html_content, email_to, email_from, subject, connection, png_bytes=None):
    """Send the HTML report via SMTP with CID-embedded PNG charts.
    png_bytes: dict of chart_key -> raw PNG bytes (from _build_email_png_bytes).
    """
    if not email_to or not email_from:
        log_info("task", "run", "email_skipped", "email_to or email_from not set — skipping email")
        return

    smtp_host = connection.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(connection.get("smtp_port", 587))
    smtp_user = connection.get("smtp_user", email_from)
    smtp_pass = connection.get("smtp_password", "")

    # MIME structure:
    #   multipart/mixed
    #     multipart/related       <- HTML body + inline chart PNGs
    #       multipart/alternative
    #         text/html
    #       image/png  (cid:chart_hbar@lamonitoring)
    #       image/png  (cid:chart_hourly@lamonitoring)
    #       ...
    #     application/octet-stream  <- HTML file attachment

    outer = email.mime.multipart.MIMEMultipart("mixed")
    outer["Subject"] = subject
    outer["From"]    = email_from
    outer["To"]      = ", ".join(email_to)

    related = email.mime.multipart.MIMEMultipart("related")

    alt = email.mime.multipart.MIMEMultipart("alternative")
    alt.attach(email.mime.text.MIMEText(html_content, "html", "utf-8"))
    related.attach(alt)

    for key, png_data in (png_bytes or {}).items():
        if not png_data:
            continue
        img_part = email.mime.image.MIMEImage(png_data, _subtype="png")
        img_part.add_header("Content-ID", f"<chart_{key}@lamonitoring>")
        img_part.add_header("Content-Disposition", "inline", filename=f"chart_{key}.png")
        related.attach(img_part)

    outer.attach(related)

    att = email.mime.application.MIMEApplication(
        html_content.encode("utf-8"), Name="la_monitoring_report.html"
    )
    att["Content-Disposition"] = 'attachment; filename="la_monitoring_report.html"'
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
    """No external connection needed — returns sentinel so executor proceeds."""
    log_info("task", "initialize", "start", "Start")
    connection = least_action_task_object.get("connection") or {}
    return {
        "smtp_host":     connection.get("smtp_host", "smtp.gmail.com"),
        "smtp_port":     int(connection.get("smtp_port", 587)),
        "smtp_user":     connection.get("smtp_user", ""),
        "smtp_password": connection.get("smtp_password", ""),
    }


def run(least_action_task_object, client):
    """Read logs, compute stats, generate HTML, publish to catalog.
    client = SMTP config dict returned by initialize().
    """
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "run", "start", "Start")

        params      = _parse_payload(least_action_task_object)
        start_dt    = params["start_dt"]
        end_dt      = params["end_dt"]
        parent_laui = params["parent_laui"]
        logs_base   = _logs_base()

        log_info("task", "run", "date_range", "Date range")

        # --- read logs ---
        log_info("task", "run", "reading_performance_logs", "Reading PERFORMANCE logs via DuckDB")
        perf_df = _read_performance_logs(logs_base, start_dt, end_dt)
        log_info("task", "run", "performance_loaded", f"Loaded {len(perf_df)} PERFORMANCE records")

        log_info("task", "run", "reading_cron_logs", "Reading CRON heartbeat logs via DuckDB")
        cron_df = _read_cron_heartbeat_logs(logs_base, start_dt, end_dt)
        log_info("task", "run", "cron_loaded", f"Loaded {len(cron_df)} CRON heartbeat records")

        log_info("task", "run", "reading_traceback_logs", "Reading API_TRACEBACK logs via DuckDB")
        traceback_df = _read_traceback_logs(logs_base, start_dt, end_dt)
        log_info("task", "run", "traceback_loaded", f"Loaded {len(traceback_df)} traceback error records")

        # --- compute ---
        overall, func_stats = _compute_stats(perf_df)
        time_series         = _build_time_series(perf_df)
        cron_series         = _build_cron_series(cron_df)
        log_info("task", "run", "stats_computed",
                 f"Functions: {len(func_stats)}, total calls: {overall.get('total_calls', 0)}, "
                 f"p95: {overall.get('p95_ms', 0)}ms, errors: {overall.get('total_errors', 0)}")

        # --- generate HTML (browser/catalog version with inline SVG) ---
        log_info("task", "run", "generating_html", "Generating HTML report")
        html_content = _generate_html(
            overall, func_stats, time_series, cron_series, traceback_df, start_dt, end_dt
        )
        log_info("task", "run", "html_generated", f"HTML size: {len(html_content):,} bytes")

        # --- pre-render PNG charts for email (matplotlib) ---
        # FIX: pass func_stats so hbar is also rendered as PNG for email
        email_png_bytes = {}
        if params.get("email_to"):
            log_info("task", "run", "rendering_png_charts", "Rendering PNG charts for email")
            email_png_bytes = _build_email_png_bytes(time_series, cron_series, func_stats)
            charts_ok = sum(1 for v in email_png_bytes.values() if v)
            log_info("task", "run", "png_charts_ready", f"PNG charts rendered: {charts_ok}")

        # --- publish to catalog ---
        catalog_result = None
        if parent_laui:
            user_access_token = least_action_task_object.get("user_access_token")
            if user_access_token:
                report_name = params.get("report_name") or f"Monitoring Report {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                api_url = "http://backend:8000/api/v1/catalog/create"
                headers = {
                    "Cookie": f"frontend_token={user_access_token}",
                    "Content-Type": "application/json",
                }
                body = {
                    "item_type":   "html_report",
                    "name":        report_name,
                    "description": "LeastAction Monitoring Report",
                    "html":        html_content,
                    "parent_laui": parent_laui,
                }
                log_info("task", "run", "posting_to_catalog",
                         f"Posting '{report_name}' under parent: {parent_laui}")
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
            log_info("task", "run", "no_parent_laui",
                     "No parent_laui provided — catalog publish skipped")

        # --- send email ---
        if params.get("email_to"):
            log_info("task", "run", "sending_email",
                     f"Sending report via SMTP to {params['email_to']}")
            try:
                subject = (
                    f"LeastAction Monitoring Report — "
                    f"{start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')} UTC"
                )
                # FIX: email version uses CID PNG references for all charts incl. hbar
                email_html = _generate_html(
                    overall, func_stats, time_series, cron_series, traceback_df, start_dt, end_dt,
                    for_email=True, png_bytes=email_png_bytes,
                )
                _send_smtp_email(
                    email_html,
                    params["email_to"],
                    params["email_from"],
                    subject,
                    client,
                    png_bytes=email_png_bytes,
                )
            except Exception as ee:
                log_error("task", "run", "email_error", f"Email sending failed: {ee}")
        else:
            log_info("task", "run", "email_skipped", "No email_to in payload — email skipped")

        return {
            "status":         "success",
            "execution_type": "sync",
            "result": {
                "performance_records":    len(perf_df),
                "cron_heartbeat_records": len(cron_df),
                "traceback_errors":       len(traceback_df),
                "total_calls":            overall.get("total_calls", 0),
                "error_rate":             overall.get("error_rate", 0),
                "p95_ms":                 overall.get("p95_ms", 0),
                "catalog_result":         catalog_result,
                "emailed_to":             params.get("email_to", []),
            },
        }

    except Exception as e:
        log_error("task", "run", "unexpected_error",
                  f"Monitoring operator failed: {e}\\n{_traceback.format_exc()}")
        return {
            "status":         "failed",
            "execution_type": "sync",
            "result":         None,
            "error":          str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """Synchronous operation — report status from run()."""
    try:
        status = run_details.get("status", "unknown")
        if status == "success":
            log_info("task", "check_completion", "success",
                     "Monitoring report completed successfully")
            return {
                "status":  "success",
                "message": "Monitoring report generated and published",
                "output":  run_details.get("result"),
            }
        else:
            err = run_details.get("error", "Unknown error")
            log_error("task", "check_completion", "failed", f"Report failed: {err}")
            return {"status": "failed", "message": err, "output": None}
    except Exception as e:
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    """Nothing to close — log final status."""
    try:
        log_info(
            "task", "finish", "cleanup",
            f"Task finished with status: {completion_details.get('status', 'unknown')}"
        )
    except Exception:
        pass
'''}


bashblock = {"main.sh": """#!/bin/bash
pip install duckdb pandas jinja2 matplotlib
echo "LeastActionMonitoring dependencies installed"
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
        "parent_laui": "",
        "email_to":    [],
        "email_from":  ""
    }
}
prompt = (
    "Read PERFORMANCE, CRON heartbeat, and API_TRACEBACK logs via DuckDB, "
    "compute detailed statistics (min/mean/median/max/p90/p95/p99, error rates), "
    "generate a self-contained HTML report with inline SVG charts, and publish "
    "it as an html_report asset to the LeastAction catalog. "
    "Optionally send the report via SMTP email with CID-embedded PNG charts rendered by matplotlib. "
    "Payload fields: date (YYYY-MM-DD logical date, sets a full-day 24h window — primary field), "
    "start_date and end_date (ISO datetime, fallback if date is not set, default 24h window), "
    "parent_laui (catalog folder to publish under), report_name (optional), "
    "email_to (list of recipients), email_from (must match smtp_user for Gmail). "
    "Empty regions and log categories are skipped silently. "
    "Auth: SMTP credentials from connection; catalog publish uses user_access_token from task object."
)

install_docs = """# LeastActionMonitoring — Install Guide

## Dependencies

    pip install duckdb
    pip install pandas
    pip install jinja2
    pip install matplotlib

## Log Directory Structure Required

    /logs/category=PERFORMANCE/yyyy=*/mm=*/dd=*/*.log
    /logs/category=CRON/project=*/yyyy=*/mm=*/dd=*/cron.log
    /logs/verbose=NON_TASK/yyyy=*/mm=*/dd=*/session_id=*/category=API_TRACEBACK/*.log

Override the default log path via the LOGS_DIR environment variable.

## SMTP Setup (Gmail)

    1. Enable 2FA on the Gmail account
    2. Generate an App Password (Google Account → Security → App Passwords)
    3. Use the app password as smtp_password in connection
    4. smtp_user and email_from must match the Gmail address

## Catalog Publish

    parent_laui must be set to a valid catalog folder LAUI.
    The task object must carry a user_access_token — this is injected automatically
    by the LeastAction executor when the operator runs in the platform.
"""

guide_docs = """# LeastActionMonitoring — Operator Guide

## What it does

Reads three log categories via DuckDB over a configurable time window:
- PERFORMANCE logs: per-function call durations and errors
- CRON heartbeat logs: system and process CPU/memory snapshots
- API_TRACEBACK logs: recent error and critical level API exceptions

Computes overall and per-function statistics (min, mean, median, max, p90, p95, p99,
error count, error rate). Builds 15-minute interval and hourly time series. Generates a
self-contained HTML report with inline SVG charts for browser and catalog viewing. When
email_to is set, re-renders charts as matplotlib PNGs and sends a CID-embedded HTML email
with the report attached as an .html file. Publishes the report to the LeastAction catalog
when parent_laui is provided.

---

## Auth

Catalog publish: user_access_token injected by the LeastAction executor — no config needed.
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
        "parent_laui": "",
        "email_to":    [],
        "email_from":  ""
      }
    }

| Field        | Required | Default          | Description                                                        |
|--------------|----------|------------------|--------------------------------------------------------------------|
| date         | No*      | —                | Logical date YYYY-MM-DD; sets a full-day window (midnight +24h)   |
| start_date   | No       | 24 hours ago     | ISO datetime fallback window start (used when date is not set)     |
| end_date     | No       | now              | ISO datetime fallback window end (used when date is not set)       |
| parent_laui  | No       | —                | Catalog folder LAUI to publish the HTML report under               |
| report_name  | No       | Auto-generated   | Display name for the catalog report item                           |
| email_to     | No       | []               | List of recipient email addresses (or comma-separated)             |
| email_from   | No       | —                | Sender address — must match smtp_user for Gmail                    |

*`date` is the recommended primary field when running on a schedule via `{{logical_date}}`.

---

## Output (on success)

    {
      "performance_records":    1420,
      "cron_heartbeat_records": 288,
      "traceback_errors":       3,
      "total_calls":            1420,
      "error_rate":             0.42,
      "p95_ms":                 312.5,
      "catalog_result":         { ... },
      "emailed_to":             ["you@example.com"]
    }

---

## Scenarios and Edge Cases

No PERFORMANCE logs in range:
  Report renders with a "No performance data found" notice. CRON and traceback
  sections still render if data is available.

No parent_laui set:
  Catalog publish is skipped with a log info entry — not an error.

No email_to set:
  Email step is skipped silently. PNG chart rendering is also skipped (no overhead).

matplotlib unavailable:
  PNG chart rendering fails gracefully per chart — logged as an error, email still sends
  with missing chart placeholders. Install matplotlib to fix.

user_access_token missing:
  Catalog publish is skipped with a log error. All other steps (stats, email) still run.

LOGS_DIR override:
  Set the LOGS_DIR environment variable to change the default /logs base path.
"""

description = (
    "Reads PERFORMANCE, CRON heartbeat, and API_TRACEBACK logs via DuckDB over a configurable "
    "time window and produces a full monitoring report. Computes per-function and overall statistics "
    "including min, mean, median, max, p90, p95, p99, error count, and error rate. Builds 15-minute "
    "and hourly time series from performance data. Generates a self-contained HTML report with inline "
    "SVG charts suitable for browser and catalog viewing. When email_to is provided, re-renders all "
    "charts as matplotlib PNGs and sends a CID-embedded HTML email with the report attached. "
    "Publishes the report as an html_report catalog item when parent_laui is set. "
    "Auth: catalog publish uses user_access_token from the task object; email uses SMTP credentials "
    "from connection. All log categories and chart types degrade gracefully when data is absent."
)

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Monitoring",
    "tags": ["monitoring", "logs", "performance", "duckdb", "html", "report",
             "email", "smtp", "catalog", "cpu", "memory", "latency", "errors"],
    "airflow_equivalent": "BashOperator"
}

version_details = {"version": "0.0.0", "core": ["0.*"]}
