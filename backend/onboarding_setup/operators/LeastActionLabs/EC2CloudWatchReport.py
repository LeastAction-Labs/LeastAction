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
EC2 CloudWatch Report Operator

Fetches free-tier EC2 CloudWatch metrics (CPU, Network, Disk, Status Checks),
generates a self-contained HTML report with SVG charts, publishes it to
the LeastAction catalog, and emails it via SMTP with CID-embedded PNG charts.

Uses IAM role — no explicit credentials required.

Payload fields:
  instance_id  - EC2 instance ID (leave empty to auto-detect via metadata)
  region       - AWS region (default: us-east-1)
  hours        - Lookback window in hours (default: 24)
  parent_laui  - Catalog folder LAUI to publish the report under
  email_to     - List of recipient email addresses
  email_from   - SES-verified sender address
  report_title - Report title (optional)
"""

import email.mime.application
import email.mime.image
import email.mime.multipart
import email.mime.text
import json
import smtplib
import traceback as _traceback
import urllib.request
from datetime import datetime, timezone, timedelta

import boto3
import requests

from src.common.logger.logger import log_info, log_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_payload(least_action_task_object):
    payload = least_action_task_object.get("payload", {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            # Previously swallowed silently — now it will surface in logs
            log_error("task", "_parse_payload", "json_decode_error",
                      f"Payload JSON is invalid: {e}. Raw payload: {payload[:300]}")
            raise ValueError(f"Payload JSON parse failed: {e}") from e

    payload_data = payload.get("data", payload)
    if isinstance(payload_data, str):
        try:
            payload_data = json.loads(payload_data)
        except json.JSONDecodeError as e:
            log_error("task", "_parse_payload", "json_decode_error",
                      f"payload.data JSON is invalid: {e}")
            raise ValueError(f"payload.data JSON parse failed: {e}") from e
    ...

    hours = int(payload_data.get("hours", 24))
    now   = datetime.now(timezone.utc)
    return {
        "instance_id":   payload_data.get("instance_id", "").strip(),
        "region":        payload_data.get("region", "us-east-1"),
        "hours":         hours,
        "start_time":    now - timedelta(hours=hours),
        "end_time":      now,
        "parent_laui":   payload_data.get("parent_laui", ""),
        "email_to":      _normalise_emails(payload_data.get("email_to", [])),
        "email_from":    payload_data.get("email_from", ""),
        "report_title":  payload_data.get("report_title", "EC2 CloudWatch Report"),
    }


def _normalise_emails(val):
    if isinstance(val, str):
        return [v.strip() for v in val.split(",") if v.strip()]
    return [v.strip() for v in val if v.strip()] if val else []


def _get_instance_id():
    """Auto-detect instance ID via IMDSv2 (works on EC2 only)."""
    try:
        token_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
        )
        token = urllib.request.urlopen(token_req, timeout=2).read().decode()
        meta_req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
        )
        return urllib.request.urlopen(meta_req, timeout=2).read().decode()
    except Exception as e:
        log_error("task", "run", "imds_error", f"Could not auto-detect instance ID: {e}")
        return ""


def _fetch_metrics(cw_client, instance_id, start_time, end_time):
    """Fetch all free-tier EC2 metrics. Returns dict: metric_id -> [(timestamp, value)]."""
    queries = [
        ("cpu",          "CPUUtilization",             "Average"),
        ("net_in",       "NetworkIn",                  "Sum"),
        ("net_out",      "NetworkOut",                 "Sum"),
        ("net_pkts_in",  "NetworkPacketsIn",            "Sum"),
        ("net_pkts_out", "NetworkPacketsOut",           "Sum"),
        ("disk_rb",      "DiskReadBytes",               "Sum"),
        ("disk_wb",      "DiskWriteBytes",              "Sum"),
        ("disk_ro",      "DiskReadOps",                 "Sum"),
        ("disk_wo",      "DiskWriteOps",                "Sum"),
        ("status_all",   "StatusCheckFailed",           "Maximum"),
        ("status_inst",  "StatusCheckFailed_Instance",  "Maximum"),
        ("status_sys",   "StatusCheckFailed_System",    "Maximum"),
    ]
    mq = [
        {
            "Id": qid,
            "MetricStat": {
                "Metric": {
                    "Namespace":  "AWS/EC2",
                    "MetricName": metric,
                    "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                },
                "Period": 300,
                "Stat":   stat,
            },
        }
        for qid, metric, stat in queries
    ]
    results = {}
    try:
        paginator = cw_client.get_paginator("get_metric_data")
        for page in paginator.paginate(
            MetricDataQueries=mq,
            StartTime=start_time,
            EndTime=end_time,
            ScanBy="TimestampAscending",
        ):
            for r in page.get("MetricDataResults", []):
                rid   = r["Id"]
                pairs = sorted(zip(r["Timestamps"], r["Values"]), key=lambda x: x[0])
                results.setdefault(rid, []).extend(pairs)
    except Exception as e:
        log_error("task", "run", "cloudwatch_fetch_error", f"Error fetching metrics: {e}")
    return results


def _get_instance_info(ec2_client, instance_id):
    """Fetch basic instance metadata."""
    try:
        resp = ec2_client.describe_instances(InstanceIds=[instance_id])
        inst = resp["Reservations"][0]["Instances"][0]
        name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), "")
        return {
            "name":        name,
            "type":        inst.get("InstanceType", ""),
            "state":       inst.get("State", {}).get("Name", ""),
            "az":          inst.get("Placement", {}).get("AvailabilityZone", ""),
            "launch_time": str(inst.get("LaunchTime", ""))[:19],
        }
    except Exception as e:
        log_error("task", "run", "describe_instance_error", f"Could not describe instance: {e}")
        return {}


def _compute_summary(metrics):
    def _avg(p):   return round(sum(v for _, v in p) / len(p), 2) if p else 0.0
    def _total(p): return round(sum(v for _, v in p), 2)
    def _max(p):   return round(max((v for _, v in p), default=0.0), 2)
    cpu = metrics.get("cpu", [])
    return {
        "cpu_avg":       _avg(cpu),
        "cpu_max":       _max(cpu),
        "cpu_latest":    round(cpu[-1][1], 2) if cpu else 0.0,
        "net_in_mb":     round(_total(metrics.get("net_in",  [])) / 1_048_576, 2),
        "net_out_mb":    round(_total(metrics.get("net_out", [])) / 1_048_576, 2),
        "disk_rb_mb":    round(_total(metrics.get("disk_rb", [])) / 1_048_576, 2),
        "disk_wb_mb":    round(_total(metrics.get("disk_wb", [])) / 1_048_576, 2),
        "disk_ro_total": int(_total(metrics.get("disk_ro", []))),
        "disk_wo_total": int(_total(metrics.get("disk_wo", []))),
        "status_failed": int(_total(metrics.get("status_all", []))),
    }


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

def _svg_line(labels, datasets, y_label="", y_max=None, height=260):
    """Pure SVG line chart — for browser HTML report."""
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
    COLORS = ["#1a73e8","#e05c5c","#36b37e","#f59e0b","#8b5cf6","#06b6d4","#ec4899","#84cc16"]
    o = [f\'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">\']
    for k in range(5):
        gy = round(PT + (k / 4) * ih)
        gv = ymx * (1 - k / 4)
        o.append(f\'<line x1="{PL}" y1="{gy}" x2="{PL+iw}" y2="{gy}" stroke="#f0f0f0" stroke-width="1"/>\')
        o.append(f\'<text x="{PL-4}" y="{gy+4}" text-anchor="end" font-size="10" fill="#bbb">{gv:.2f}</text>\')
    o.append(f\'<line x1="{PL}" y1="{PT}" x2="{PL}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>\')
    o.append(f\'<line x1="{PL}" y1="{PT+ih}" x2="{PL+iw}" y2="{PT+ih}" stroke="#ddd" stroke-width="1"/>\')
    step = max(1, n // 12)
    for i in range(0, n, step):
        x   = round(xp(i))
        lbl = str(labels[i])[-16:]
        o.append(f\'<text x="{x}" y="{PT+ih+14}" text-anchor="end" font-size="9" fill="#bbb" transform="rotate(-35,{x},{PT+ih+14})">{lbl}</text>\')
    cy = H // 2
    o.append(f\'<text x="11" y="{cy}" text-anchor="middle" font-size="10" fill="#bbb" transform="rotate(-90,11,{cy})">{y_label}</text>\')
    lx = PL
    for di, ds in enumerate(datasets):
        color     = ds.get("color", COLORS[di % len(COLORS)])
        pts       = [(round(xp(i)), round(yp(v))) for i, v in enumerate(ds.get("data") or []) if v is not None]
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


def _matplotlib_chart_png_bytes(labels, datasets, y_label="", y_max=None, height_in=3.2):
    """
    Render a chart with matplotlib and return raw PNG bytes.
    Returns None on failure.
    """
    try:
        from io import BytesIO
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        all_vals = [v for ds in datasets for v in (ds.get("data") or []) if v is not None]
        if not all_vals or not labels:
            return None

        COLORS = ["#1a73e8","#e05c5c","#36b37e","#f59e0b","#8b5cf6","#06b6d4","#ec4899","#84cc16"]

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

        n    = len(labels)
        step = max(1, n // 10)
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


# ---------------------------------------------------------------------------
# Chart data preparation
# ---------------------------------------------------------------------------

def _build_chart_vars(metrics):
    """Pre-compute (labels, datasets) for each chart panel."""
    def _j(pairs, scale=1.0):
        labels = [ts.strftime("%Y-%m-%d %H:%M") for ts, _ in pairs]
        values = [round(v * scale, 4) for _, v in pairs]
        return labels, values

    cpu_l,  cpu_v  = _j(metrics.get("cpu", []))
    ni_l,   ni_v   = _j(metrics.get("net_in",  []), 1/1_048_576)
    no_l,   no_v   = _j(metrics.get("net_out", []), 1/1_048_576)
    drb_l,  drb_v  = _j(metrics.get("disk_rb", []), 1/1_048_576)
    dwb_l,  dwb_v  = _j(metrics.get("disk_wb", []), 1/1_048_576)
    dro_l,  dro_v  = _j(metrics.get("disk_ro", []))
    dwo_l,  dwo_v  = _j(metrics.get("disk_wo", []))
    sc_l,   sc_v   = _j(metrics.get("status_all",  []))
    sc_il,  sc_iv  = _j(metrics.get("status_inst", []))
    sc_sl,  sc_sv  = _j(metrics.get("status_sys",  []))

    return {
        "cpu":    (cpu_l,          [{"label": "CPU %",            "data": cpu_v,  "color": "#1a73e8"}]),
        "net":    (ni_l or no_l,   [{"label": "Network In (MB)",  "data": ni_v,   "color": "#36b37e"},
                                     {"label": "Network Out (MB)", "data": no_v,   "color": "#f59e0b"}]),
        "disk_b": (drb_l or dwb_l, [{"label": "Read (MB)",        "data": drb_v,  "color": "#8b5cf6"},
                                     {"label": "Write (MB)",       "data": dwb_v,  "color": "#ec4899"}]),
        "disk_o": (dro_l or dwo_l, [{"label": "Read Ops",         "data": dro_v,  "color": "#06b6d4"},
                                     {"label": "Write Ops",        "data": dwo_v,  "color": "#f97316"}]),
        "status": (sc_l or sc_il,  [{"label": "All Checks Failed","data": sc_v,   "color": "#dc3545"},
                                     {"label": "Instance Check",   "data": sc_iv,  "color": "#fd7e14"},
                                     {"label": "System Check",     "data": sc_sv,  "color": "#6f42c1"}]),
    }


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_charts_svg(chart_vars):
    """Returns dict of key -> SVG HTML string (for browser report)."""
    NO_DATA = \'<p style="color:#aaa;font-style:italic;padding:12px">No data available.</p>\'
    def _c(key, y_label, y_max=None, height=260):
        labels, datasets = chart_vars[key]
        return _svg_line(labels, datasets, y_label=y_label, y_max=y_max, height=height) if labels else NO_DATA
    return {
        "cpu":    _c("cpu",    "%",      y_max=100),
        "net":    _c("net",    "MB"),
        "disk_b": _c("disk_b", "MB"),
        "disk_o": _c("disk_o", "Ops"),
        "status": _c("status", "Failed", y_max=1.5, height=200),
    }


def _render_charts_png_bytes(chart_vars):
    """Returns dict of key -> PNG bytes (or None). Used for CID email attachments."""
    def _c(key, y_label, y_max=None, height_in=3.2):
        labels, datasets = chart_vars[key]
        if not labels:
            return None
        return _matplotlib_chart_png_bytes(labels, datasets,
                                           y_label=y_label, y_max=y_max,
                                           height_in=height_in)
    return {
        "cpu":    _c("cpu",    "%",      y_max=100),
        "net":    _c("net",    "MB"),
        "disk_b": _c("disk_b", "MB"),
        "disk_o": _c("disk_o", "Ops"),
        "status": _c("status", "Failed", y_max=1.5, height_in=2.4),
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{{ report_title }}</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;background:#f5f7fa;color:#333;line-height:1.5}
    .container{max-width:1300px;margin:0 auto;padding:20px}
    header{background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);color:#fff;padding:28px 32px;border-radius:10px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,.15)}
    header h1{font-size:1.8rem;margin-bottom:6px}
    .meta{opacity:.85;font-size:.88em;margin-top:3px}
    .info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:20px}
    .info-card{background:#fff;padding:14px 18px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.07);border-left:4px solid #1a73e8}
    .info-label{color:#777;font-size:.75em;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
    .info-value{font-size:1.05em;font-weight:600;color:#222}
    .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin-bottom:20px}
    .stat-card{background:#fff;padding:18px 20px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.07)}
    .stat-label{color:#777;font-size:.75em;text-transform:uppercase;letter-spacing:.5px;margin-bottom:7px}
    .stat-value{font-size:1.7em;font-weight:700;color:#1a73e8}
    .stat-unit{font-size:.52em;color:#aaa;margin-left:3px}
    .stat-value.red{color:#dc3545}
    .stat-value.green{color:#28a745}
    .section{background:#fff;padding:24px 28px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.07);margin-bottom:20px}
    h2{color:#1a73e8;font-size:1.2em;border-bottom:2px solid #e8f0fe;padding-bottom:8px;margin-bottom:14px}
    .alert{padding:12px 16px;border-radius:6px;margin-bottom:14px;font-size:.93em}
    .alert-red{background:#f8d7da;border-left:4px solid #dc3545}
    .alert-green{background:#d4edda;border-left:4px solid #28a745}
    .chart-row{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:20px}
    .chart-row .section{margin-bottom:0}
    .footer{text-align:center;color:#bbb;font-size:.8em;margin-top:24px;padding-bottom:20px}
    .note{font-size:.82em;color:#888;margin-top:10px;font-style:italic}
    img.chart{width:100%;max-width:860px;height:auto;display:block}
    @media(max-width:800px){.chart-row{grid-template-columns:1fr}}
  </style>
</head>
<body>
<div class="container">

<header>
  <h1>{{ report_title }}</h1>
  <p class="meta">Instance: {{ instance_id }}{% if instance_name %} &nbsp;|&nbsp; {{ instance_name }}{% endif %}</p>
  <p class="meta">Region: {{ region }} &nbsp;|&nbsp; Period: {{ period_start }} &rarr; {{ period_end }} ({{ hours }}h)</p>
  <p class="meta">Generated: {{ generated_at }}</p>
</header>

{% if status_failed > 0 %}
<div class="alert alert-red"><strong>Status Check Failures Detected:</strong> {{ status_failed }} failure(s) in the selected period.</div>
{% else %}
<div class="alert alert-green"><strong>All Status Checks Passed</strong> during the selected period.</div>
{% endif %}

{% if instance_info %}
<div class="info-grid">
  <div class="info-card"><div class="info-label">Instance Type</div><div class="info-value">{{ instance_info.type }}</div></div>
  <div class="info-card"><div class="info-label">State</div><div class="info-value">{{ instance_info.state }}</div></div>
  <div class="info-card"><div class="info-label">Availability Zone</div><div class="info-value">{{ instance_info.az }}</div></div>
  <div class="info-card"><div class="info-label">Launch Time</div><div class="info-value">{{ instance_info.launch_time }}</div></div>
</div>
{% endif %}

<div class="stats-grid">
  <div class="stat-card"><div class="stat-label">CPU Avg</div><div class="stat-value">{{ cpu_avg }}<span class="stat-unit">%</span></div></div>
  <div class="stat-card"><div class="stat-label">CPU Max</div><div class="stat-value {% if cpu_max > 80 %}red{% endif %}">{{ cpu_max }}<span class="stat-unit">%</span></div></div>
  <div class="stat-card"><div class="stat-label">Network In</div><div class="stat-value">{{ net_in_mb }}<span class="stat-unit">MB</span></div></div>
  <div class="stat-card"><div class="stat-label">Network Out</div><div class="stat-value">{{ net_out_mb }}<span class="stat-unit">MB</span></div></div>
  <div class="stat-card"><div class="stat-label">Disk Read</div><div class="stat-value">{{ disk_rb_mb }}<span class="stat-unit">MB</span></div></div>
  <div class="stat-card"><div class="stat-label">Disk Write</div><div class="stat-value">{{ disk_wb_mb }}<span class="stat-unit">MB</span></div></div>
  <div class="stat-card"><div class="stat-label">Disk Read Ops</div><div class="stat-value">{{ disk_ro_total }}</div></div>
  <div class="stat-card"><div class="stat-label">Disk Write Ops</div><div class="stat-value">{{ disk_wo_total }}</div></div>
  <div class="stat-card"><div class="stat-label">Status Failures</div><div class="stat-value {% if status_failed > 0 %}red{% else %}green{% endif %}">{{ status_failed }}</div></div>
</div>

<div class="section">
  <h2>CPU Utilization (%)</h2>
  {{ chart_cpu | safe }}
</div>

<div class="section">
  <h2>Network I/O (MB per 5-min interval)</h2>
  {{ chart_net | safe }}
</div>

<div class="chart-row">
  <div class="section">
    <h2>Disk Throughput (MB per 5-min)</h2>
    {{ chart_disk_b | safe }}
    <p class="note">Note: Disk metrics reflect instance-store volumes. EBS volumes report under AWS/EBS namespace.</p>
  </div>
  <div class="section">
    <h2>Disk Operations (per 5-min)</h2>
    {{ chart_disk_o | safe }}
  </div>
</div>

<div class="section">
  <h2>Status Checks (1 = Failed)</h2>
  {{ chart_status | safe }}
</div>

<div class="footer">{{ report_title }} &mdash; {{ instance_id }} &mdash; {{ generated_at }}</div>
</div>
</body>
</html>"""


def _render_html(instance_id, instance_info, summary, start_time, end_time,
                 report_title, charts):
    """Fill Jinja2 template with data and pre-rendered chart snippets."""
    from jinja2 import Template
    t = Template(_HTML_TEMPLATE)
    return t.render(
        report_title  = report_title,
        instance_id   = instance_id,
        instance_name = instance_info.get("name", ""),
        instance_info = instance_info,
        region        = instance_info.get("az", "")[:-1] if instance_info.get("az") else "",
        period_start  = start_time.strftime("%Y-%m-%d %H:%M UTC"),
        period_end    = end_time.strftime("%Y-%m-%d %H:%M UTC"),
        hours         = int((end_time - start_time).total_seconds() / 3600),
        generated_at  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        status_failed = summary["status_failed"],
        cpu_avg       = summary["cpu_avg"],
        cpu_max       = summary["cpu_max"],
        net_in_mb     = summary["net_in_mb"],
        net_out_mb    = summary["net_out_mb"],
        disk_rb_mb    = summary["disk_rb_mb"],
        disk_wb_mb    = summary["disk_wb_mb"],
        disk_ro_total = summary["disk_ro_total"],
        disk_wo_total = summary["disk_wo_total"],
        chart_cpu     = charts["cpu"],
        chart_net     = charts["net"],
        chart_disk_b  = charts["disk_b"],
        chart_disk_o  = charts["disk_o"],
        chart_status  = charts["status"],
    )


def _generate_html(instance_id, instance_info, summary, metrics,
                   start_time, end_time, report_title, for_email=False):
    """
    Generate the full HTML report.
      for_email=False  -> SVG charts; returns html_str
      for_email=True   -> CID <img> placeholders; returns (html_str, png_bytes_dict)
    """
    chart_vars = _build_chart_vars(metrics)

    if for_email:
        png_bytes = _render_charts_png_bytes(chart_vars)
        NO_DATA   = \'<p style="color:#aaa;font-style:italic;padding:8px 0">No data available.</p>\'
        # Reference each chart by its CID — the actual PNG bytes travel as MIME parts
        charts = {
            key: (
                f\'<img class="chart" src="cid:chart_{key}@ec2report" alt="{key} chart">\' 
                if png_bytes.get(key) else NO_DATA
            )
            for key in ("cpu", "net", "disk_b", "disk_o", "status")
        }
        html = _render_html(instance_id, instance_info, summary,
                            start_time, end_time, report_title, charts)
        return html, png_bytes

    charts = _render_charts_svg(chart_vars)
    return _render_html(instance_id, instance_info, summary,
                        start_time, end_time, report_title, charts)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _send_smtp_email(html_content, png_bytes, email_to, email_from, subject, connection):
    """
    Send an HTML email with chart PNGs embedded as CID (Content-ID) MIME image parts.
    This is the correct standard for inline images in HTML email — supported by all
    major clients (Gmail, Outlook, Apple Mail, Thunderbird, etc.).

    png_bytes: dict of chart_key -> raw PNG bytes (from _render_charts_png_bytes).
    """
    if not email_to or not email_from:
        log_info("task", "run", "email_skipped",
                 "email_to or email_from not set — skipping email")
        return

    smtp_host = connection.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(connection.get("smtp_port", 587))
    smtp_user = connection.get("smtp_user", email_from)
    smtp_pass = connection.get("smtp_password", "")

    # MIME structure:
    #   multipart/mixed
    #     multipart/related          <- HTML body + its inline images
    #       multipart/alternative
    #         text/html
    #       image/png  (Content-ID: chart_cpu@ec2report)
    #       image/png  (Content-ID: chart_net@ec2report)
    #       ...
    #     application/octet-stream   <- HTML file attachment

    outer = email.mime.multipart.MIMEMultipart("mixed")
    outer["Subject"] = subject
    outer["From"]    = email_from
    outer["To"]      = ", ".join(email_to)

    related = email.mime.multipart.MIMEMultipart("related")

    alt = email.mime.multipart.MIMEMultipart("alternative")
    alt.attach(email.mime.text.MIMEText(html_content, "html", "utf-8"))
    related.attach(alt)

    # Attach each chart PNG as an inline CID part
    for key, png_data in (png_bytes or {}).items():
        if not png_data:
            continue
        img_part = email.mime.image.MIMEImage(png_data, _subtype="png")
        img_part.add_header("Content-ID",          f"<chart_{key}@ec2report>")
        img_part.add_header("Content-Disposition", "inline",
                            filename=f"chart_{key}.png")
        related.attach(img_part)

    outer.attach(related)

    # Attach the full browser-quality HTML as a downloadable file
    att = email.mime.application.MIMEApplication(
        html_content.encode("utf-8"), Name="ec2_report.html"
    )
    att["Content-Disposition"] = \'attachment; filename="ec2_report.html"\'
    outer.attach(att)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(email_from, email_to, outer.as_string())

    log_info("task", "run", "email_sent",
             f"Report emailed to {email_to} via {smtp_host}")


def _post_to_catalog(html_content, parent_laui, report_name, user_access_token):
    """POST HTML report to LeastAction catalog."""
    resp = requests.post(
        "http://backend:8000/api/v1/catalog/create",
        json={
            "item_type":   "html_report",
            "name":        report_name,
            "description": "EC2 CloudWatch Monitoring Report",
            "html":        html_content,
            "parent_laui": parent_laui,
        },
        headers={
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type":  "application/json",
        },
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        log_error("task", "run", "catalog_http_error",
                  f"Catalog API returned {resp.status_code}: {resp.text[:200]}")
        return None
    return resp.json()


# ---------------------------------------------------------------------------
# 4 Required Operator Methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """Create CloudWatch and EC2 boto3 clients."""
    try:
        log_info("task", "initialize", "start", "Initializing EC2CloudWatchReport")
        conn   = least_action_task_object.get("connection", {})
        region = conn.get("region", "us-east-1")
        session_kwargs = {"region_name": region}
        if conn.get("aws_access_key_id"):
            session_kwargs["aws_access_key_id"]     = conn["aws_access_key_id"]
            session_kwargs["aws_secret_access_key"] = conn.get("aws_secret_access_key", "")
            if conn.get("aws_session_token"):
                session_kwargs["aws_session_token"] = conn["aws_session_token"]
            log_info("task", "initialize", "credentials", "Using explicit credentials from connection")
        else:
            log_info("task", "initialize", "credentials", "Using IAM role / default credential chain")
        session = boto3.Session(**session_kwargs)
        clients = {
            "cloudwatch": session.client("cloudwatch"),
            "ec2":        session.client("ec2"),
            "region":     region,
            "smtp":       conn,
        }
        clients["cloudwatch"].list_metrics(Namespace="AWS/EC2", MetricName="CPUUtilization")
        log_info("task", "initialize", "clients_ready", "CloudWatch and EC2 clients initialized")
        return clients
    except Exception as e:
        log_error("task", "initialize", "init_error", f"Initialization failed: {e}")
        raise


def run(least_action_task_object, client):
    """Fetch CloudWatch metrics, generate HTML report, publish and email."""
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "run", "start", "Starting EC2CloudWatchReport")

        params = _parse_payload(least_action_task_object)

        instance_id = params["instance_id"]
        if not instance_id:
            log_info("task", "run", "auto_detect_instance",
                     "No instance_id in payload — auto-detecting via IMDS")
            instance_id = _get_instance_id()
        if not instance_id:
            raise ValueError("instance_id not provided and could not be auto-detected")

        start_time = params["start_time"]
        end_time   = params["end_time"]
        log_info("task", "run", "params",
                 f"instance={instance_id}, region={params[\'region\']}, "
                 f"{start_time.strftime(\'%Y-%m-%d %H:%M\')} -> {end_time.strftime(\'%Y-%m-%d %H:%M\')}")

        instance_info = _get_instance_info(client["ec2"], instance_id)
        log_info("task", "run", "instance_info",
                 f"Type={instance_info.get(\'type\')}, State={instance_info.get(\'state\')}")

        metrics     = _fetch_metrics(client["cloudwatch"], instance_id, start_time, end_time)
        data_points = sum(len(v) for v in metrics.values())
        log_info("task", "run", "metrics_fetched", f"Total data points: {data_points}")

        summary = _compute_summary(metrics)
        log_info("task", "run", "summary",
                 f"CPU avg={summary[\'cpu_avg\']}%, max={summary[\'cpu_max\']}%, "
                 f"status_failures={summary[\'status_failed\']}")

        # Browser / catalog report — SVG charts
        html_content = _generate_html(
            instance_id, instance_info, summary, metrics,
            start_time, end_time, params["report_title"], for_email=False
        )
        log_info("task", "run", "html_generated", f"HTML size: {len(html_content):,} bytes")

        # Catalog
        catalog_result = None
        if params["parent_laui"]:
            token = least_action_task_object.get("user_access_token")
            if token:
                report_name = (
                    f"{params[\'report_title\']} {datetime.now().strftime(\'%Y-%m-%d %H:%M\')}"
                )
                log_info("task", "run", "posting_catalog",
                         f"Publishing \'{report_name}\' under {params[\'parent_laui\']}")
                try:
                    catalog_result = _post_to_catalog(
                        html_content, params["parent_laui"], report_name, token
                    )
                    log_info("task", "run", "catalog_published", "Report published to catalog")
                except Exception as ce:
                    log_error("task", "run", "catalog_error", f"Catalog publish failed: {ce}")
            else:
                log_error("task", "run", "missing_token",
                          "user_access_token missing — catalog publish skipped")

        # Email — CID-embedded PNG charts
        if params["email_to"]:
            log_info("task", "run", "sending_email",
                     f"Sending email to {params[\'email_to\']} (CID PNG charts)")
            try:
                email_html, png_bytes = _generate_html(
                    instance_id, instance_info, summary, metrics,
                    start_time, end_time, params["report_title"], for_email=True
                )
                charts_ok = sum(1 for v in png_bytes.values() if v)
                log_info("task", "run", "email_charts_ready",
                         f"Charts rendered: {charts_ok}/5, HTML: {len(email_html):,} bytes")
                _send_smtp_email(
                    email_html,
                    png_bytes,
                    params["email_to"],
                    params["email_from"],
                    f"{params[\'report_title\']} — {instance_id} — "
                    f"{datetime.now().strftime(\'%Y-%m-%d %H:%M UTC\')}",
                    client.get("smtp", {}),
                )
            except Exception as ee:
                log_error("task", "run", "email_error", f"Email sending failed: {ee}")
        else:
            log_info("task", "run", "email_skipped", "No email_to addresses — email skipped")

        return {
            "status":         "success",
            "execution_type": "sync",
            "result": {
                "instance_id":    instance_id,
                "data_points":    data_points,
                "cpu_avg":        summary["cpu_avg"],
                "cpu_max":        summary["cpu_max"],
                "status_failed":  summary["status_failed"],
                "catalog_result": catalog_result,
                "emailed_to":     params["email_to"],
            },
        }

    except Exception as e:
        log_error("task", "run", "unexpected_error",
                  f"EC2CloudWatchReport failed: {e}\\n{_traceback.format_exc()}")
        return {
            "status":         "failed",
            "execution_type": "sync",
            "result":         None,
            "error":          str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get("status") == "success":
            log_info("task", "check_completion", "success", "EC2 report completed")
            return {"status": "success", "message": "EC2 CloudWatch report generated",
                    "output": run_details.get("result")}
        err = run_details.get("error", "Unknown error")
        log_error("task", "check_completion", "failed", err)
        return {"status": "failed", "message": err, "output": None}
    except Exception as e:
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        log_info("task", "finish", "cleanup",
                 f"Task finished with status: {completion_details.get(\'status\', \'unknown\')}")
    except Exception:
        pass
'''}


bashblock = {"main.sh": """#!/bin/bash
pip install boto3 botocore jinja2 matplotlib
echo "EC2CloudWatchReport dependencies installed"
"""}

connection = {
    "region":                "us-east-1",   # optional, only for temporary STS credentials
    "smtp_host":             "smtp.gmail.com",
    "smtp_port":             587,
    "smtp_user":             "you@gmail.com",
    "smtp_password":         "xxxx xxxx xxxx xxxx"
}

payload = {
    "data": {
        "instance_id":  "",
        "region":       "us-east-1",
        "hours":        24,
        "parent_laui":  "",
        "email_to":     ["you@example.com"],
        "email_from":   "you@gmail.com",
        "report_title": "EC2 CloudWatch Report"
    }
}
prompt = (
    "Fetch free-tier EC2 CloudWatch metrics (CPU, Network, Disk, Status Checks) for a given "
    "instance over a configurable lookback window, generate a self-contained HTML report with "
    "inline SVG charts, publish it to the LeastAction catalog, and email it via SMTP with "
    "CID-embedded PNG charts rendered by matplotlib. "
    "If instance_id is not provided in the payload, auto-detects it via IMDSv2 metadata service. "
    "Payload fields: instance_id (leave empty to auto-detect), region, hours (lookback window, "
    "default 24), parent_laui (catalog folder LAUI), email_to (list of recipients), "
    "email_from (must match smtp_user for Gmail), report_title (optional). "
    "Auth: IAM role via default credential chain first, fallback to explicit keys from connection."
)

install_docs = """# EC2CloudWatchReport — Install Guide

## Dependencies

    pip install boto3
    pip install botocore
    pip install jinja2
    pip install matplotlib

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |

## SMTP Setup (Gmail)

    1. Enable 2FA on the Gmail account
    2. Generate an App Password (Google Account → Security → App Passwords)
    3. Use the app password as smtp_password in connection
    4. smtp_user and email_from must match the Gmail address

## Catalog Publish

    parent_laui must be set to a valid catalog folder LAUI.
    The task object must carry a user_access_token — this is injected automatically
    by the LeastAction executor when the operator runs in the platform.

## Instance Auto-Detection

    When instance_id is left empty, the operator queries the EC2 IMDSv2 metadata
    endpoint (169.254.169.254). This only works when running on an EC2 instance.
    For local or off-instance runs, always provide instance_id explicitly.
"""

guide_docs = """# EC2CloudWatchReport — Operator Guide

## What it does

Fetches all free-tier EC2 CloudWatch metrics for a single instance over a configurable
lookback window (default 24 hours) at 5-minute resolution. Metrics collected:

- CPU: CPUUtilization (Average)
- Network: NetworkIn, NetworkOut, NetworkPacketsIn, NetworkPacketsOut (Sum)
- Disk: DiskReadBytes, DiskWriteBytes, DiskReadOps, DiskWriteOps (Sum)
- Status: StatusCheckFailed, StatusCheckFailed_Instance, StatusCheckFailed_System (Maximum)

Computes a summary (averages, totals, max). Generates a self-contained HTML report with
inline SVG charts for browser and catalog viewing. When email_to is provided, re-renders
all charts as matplotlib PNGs and sends a CID-embedded HTML email with the report attached
as an .html file. Publishes the report to the LeastAction catalog when parent_laui is set.

---

## Auth

1. IAM role — tried first via the default boto3 credential chain. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region":                "us-east-1",
      "aws_access_key_id":     "", //optional - leave empty to use IAM role
      "aws_secret_access_key": "", //optional - leave empty to use IAM role
      "aws_session_token":     "", // optional - only needed if using IAM role
      "smtp_host":             "smtp.gmail.com",
      "smtp_port":             587,
      "smtp_user":             "you@gmail.com",
      "smtp_password":         "xxxx xxxx xxxx xxxx"
    }

Leave aws_access_key_id empty on EC2 — the IAM role is used automatically.

---

## Payload

    {
      "data": {
        "instance_id":  "",
        "region":       "us-east-1",
        "hours":        24,
        "parent_laui":  "",
        "email_to":     ["you@example.com"],
        "email_from":   "you@gmail.com",
        "report_title": "EC2 CloudWatch Report"
      }
    }

| Field        | Required      | Default                  | Description                                            |
|--------------|---------------|--------------------------|--------------------------------------------------------|
| instance_id  | No            | Auto-detected via IMDSv2 | EC2 instance ID to report on                           |
| region       | No            | us-east-1                | AWS region of the instance                             |
| hours        | No            | 24                       | Lookback window in hours                               |
| parent_laui  | No            | —                        | Catalog folder LAUI to publish the HTML report under   |
| email_to     | No            | []                       | List of recipient email addresses (or comma-separated) |
| email_from   | No            | —                        | Sender address — must match smtp_user for Gmail        |
| report_title | No            | EC2 CloudWatch Report    | Display title shown in the report header               |

---

## Output (on success)

    {
      "instance_id":    "i-0abc123def456789",
      "data_points":    864,
      "cpu_avg":        12.4,
      "cpu_max":        87.3,
      "status_failed":  0,
      "catalog_result": { ... },
      "emailed_to":     ["you@example.com"]
    }

---

## Scenarios and Edge Cases

instance_id empty and not on EC2:
  IMDSv2 call times out — operator raises ValueError immediately with a clear message.
  Always provide instance_id explicitly for local or off-instance runs.

No metrics returned:
  All chart panels render with a "No data available" placeholder. Summary values are 0.
  This is expected for stopped instances or very short lookback windows.

status_failed > 0:
  A red alert banner is shown at the top of the HTML report.

No parent_laui set:
  Catalog publish is skipped with a log info entry — not an error.

No email_to set:
  Email step and PNG chart rendering are both skipped silently.

matplotlib unavailable:
  PNG chart rendering fails gracefully per chart — logged as an error, email still sends
  with missing chart placeholders. Install matplotlib to fix.

Disk metrics are zero on EBS-only instances:
  CloudWatch DiskReadBytes/DiskWriteBytes apply to instance-store volumes only.
  EBS metrics are under the AWS/EBS namespace and are not included in free-tier EC2 metrics.
"""

description = (
    "Fetches all free-tier EC2 CloudWatch metrics (CPU, Network, Disk, Status Checks) for a "
    "single instance at 5-minute resolution over a configurable lookback window. Auto-detects "
    "the instance ID via IMDSv2 if not provided. Computes a summary of averages, totals, and "
    "maximums. Generates a self-contained HTML report with inline SVG charts for browser and "
    "catalog viewing. When email_to is provided, re-renders charts as matplotlib PNGs and sends "
    "a CID-embedded HTML email with the report attached. Publishes the report as an html_report "
    "catalog item when parent_laui is set. "
    "Auth: IAM role via default boto3 credential chain first, fallback to explicit access keys "
    "in connection. SMTP credentials for email are taken from connection."
)

publisher = "LeastAction"

metadata = {
    "service": "EC2, CloudWatch",
    "category": "Monitoring",
    "tags": ["ec2", "cloudwatch", "metrics", "cpu", "network", "disk", "status",
             "report", "html", "email", "smtp", "catalog", "monitoring", "aws"],
    "airflow_equivalent": "BashOperator"
}

version_details = {"version": "0.0.0", "core": ["0.*"]}