# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

bashblock = {"install_dependencies.sh": "pip install requests"}

codeblock = {
    "main.py": '''
import json
import os
import smtplib
import ssl
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.common.logger.logger import log_error, log_info

BANNER = "=" * 60


def _fetch_item(laui, auth_token, backend_host):
    try:
        resp = requests.get(
            f"http://{backend_host}:8000/api/v1/catalog/get?item_laui={laui}",
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log_error("action", "_fetch_item", "error", f"Failed to fetch {laui}: {str(e)}")
        return None


def _fetch_workflow_tasks(wf_laui, auth_token, backend_host):
    try:
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/search",
            json={
                "item_filter": {"item_type": "task", "parent_laui": wf_laui},
                "pagination": {"per_page": 50},
                "projection": {"include": ["name", "laui", "payload", "state", "operator_laui"]},
            },
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as e:
        log_error("action", "_fetch_workflow_tasks", "error", f"Failed to fetch workflow {wf_laui}: {str(e)}")
        return []


def _search_skill(name, auth_token, backend_host, project_laui=None, account_laui=None):
    try:
        item_filter = {"item_type": "skill", "name": name}
        if project_laui:
            item_filter["project_laui"] = project_laui
        if account_laui:
            item_filter["account_laui"] = account_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/search",
            json={"item_filter": item_filter, "pagination": {}, "projection": {"include": ["name", "laui", "content", "description"]}},
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0] if items else None
    except Exception as e:
        log_error("action", "_search_skill", "error", f"Skill search failed for '{name}': {str(e)}")
        return None


def _validate_connection(conn_laui, auth_token, backend_host):
    """Returns (ok, error_message). Checks that the connection exists and has an API key set."""
    conn = _fetch_item(conn_laui, auth_token, backend_host)
    if not conn:
        return False, f"AI connection {conn_laui} not found. Please check the connection LAUI in your action variables."
    api_key = (conn.get("content") or {}).get("api_key", "")
    if not api_key or not api_key.strip():
        name = conn.get("name", conn_laui)
        return False, (
            f"AI connection '{name}' has no API key configured. "
            "Please open the connection in the UI (Connections → {name}) and add your Anthropic API key."
        )
    return True, None


def _call_agent(prompt, skill_content, conn_laui, chat_laui, auth_token, backend_host, enable_tools=False):
    try:
        payload = {"prompt": prompt, "chat_laui": chat_laui, "skill_content": skill_content, "enable_tools": enable_tools}
        if conn_laui:
            payload["connection_laui"] = conn_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/ai/agent",
            json=payload,
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json().get("message", "")
    except Exception as e:
        log_error("action", "_call_agent", "error", f"Agent call failed: {str(e)}")
        return None


def _write_asset(parent_laui, report_text, label, session_id, auth_token, backend_host, project_laui=None, account_laui=None):
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe = label.replace("/", "_").replace(" ", "_")[:60]
        item_name = f"debug_{safe}_{session_id[:8]}_{ts}"
        html_body = "<pre style='font-family:monospace;white-space:pre-wrap;padding:16px'>{}</pre>".format(
            report_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        payload = {
            "item_type": "html_report", "name": item_name, "parent_laui": parent_laui,
            "description": f"Schema check report - session {session_id[:8]}", "html": html_body,
        }
        if project_laui:
            payload["project_laui"] = project_laui
        if account_laui:
            payload["account_laui"] = account_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/create",
            json=payload,
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        log_info("action", "_write_asset", "created", f"Report {resp.json().get('item_laui','?')} created under {parent_laui}")
        return True
    except Exception as e:
        log_error("action", "_write_asset", "error", f"Failed to create report asset: {str(e)}")
        return False


def _send_email(to, subject, body, smtp_host, smtp_port, smtp_user, smtp_password, from_addr):
    if not smtp_host or not from_addr:
        return False
    server = None
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        server = smtplib.SMTP(smtp_host, int(smtp_port) if smtp_port else 587, timeout=30)
        server.starttls(context=ssl.create_default_context())
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception as e:
        log_error("action", "_send_email", "error", f"Email send failed: {str(e)}")
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def _send_slack(webhook_url, label, report_text):
    try:
        summary = report_text[:2800] + ("\\n...(truncated)" if len(report_text) > 2800 else "")
        resp = requests.post(
            webhook_url,
            json={"text": f":rotating_light: *Schema check: {label}*",
                  "blocks": [{"type": "header", "text": {"type": "plain_text", "text": f"Schema check: {label}"}},
                             {"type": "section", "text": {"type": "mrkdwn", "text": summary}}]},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log_error("action", "_send_slack", "error", f"Slack send failed: {str(e)}")
        return False


def _dump(obj):
    if obj is None:
        return "(not found)"
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return str(obj)


def run(
    least_action_action_object,
    skill_names=None,
    chat_laui=None,
    notify=None,
    wf_laui=None,
    ai_connection=None,
    prompt=None,
    include_task_context=True,
    enable_tools=False,
    source_connection_laui=None,
    source_table=None,
    **kwargs,
):
    try:
        auth_token = least_action_action_object.get("user_access_token")
        if not auth_token:
            log_error("action", "run", "missing_auth_token", "user_access_token not found")
            return False

        backend_host = os.getenv("BACKEND_HOST", "backend")
        session_id = least_action_action_object.get("session_id", "unknown")
        current_task = least_action_action_object.get("task", {})
        task_name = current_task.get("name", "")
        task_state = current_task.get("state", "")
        project_laui = (current_task.get("project_laui") or least_action_action_object.get("project_laui")) or None
        account_laui = (current_task.get("account_laui") or least_action_action_object.get("account_laui")) or None
        notify = notify or {}

        # NOTE: unlike the reactive version, this does NOT skip on task success —
        # a schema/contract check via live inspect_data is meant to run every time,
        # since drift (e.g. a precision change) doesn't make the load itself fail.

        # Connection: injected by backend (post_action mode) or passed as ai_connection (standalone/workflow)
        conn_laui = least_action_action_object.get("connection_laui") or ai_connection

        mode = "workflow_audit" if wf_laui else ("post_action" if task_name else "standalone")
        label = task_name if task_name else (f"wf:{wf_laui[:8]}" if wf_laui else "audit")

        log_info("action", "run", "start",
            f"LeastActionAgentDebug | mode={mode} | label={label} | state={task_state} | conn={conn_laui} | enable_tools={enable_tools}"
        )

        # Collect task context (payload/state) as before
        task_context = ""
        if include_task_context and task_name and current_task:
            task_laui_val = current_task.get("laui")
            if task_laui_val:
                fetched = _fetch_item(str(task_laui_val), auth_token, backend_host)
                task_context = _dump(fetched or current_task)
            else:
                task_context = _dump(current_task)
            log_info("action", "run", "task_context", f"Task context collected for {task_name}")

        # Workflow audit: fetch all task payloads
        workflow_tasks_context = ""
        if wf_laui:
            wf_tasks = _fetch_workflow_tasks(wf_laui, auth_token, backend_host)
            if wf_tasks:
                summaries = []
                for t in wf_tasks:
                    item = t.get("item", t)
                    n = item.get("name", "?")
                    p = item.get("payload", "")
                    s = item.get("state", "?")
                    if isinstance(p, str) and len(p) > 1500:
                        p = p[:1500] + "\\n...(truncated)"
                    summaries.append(f"### {n} (state: {s})\\n\\n```\\n{p}\\n```")
                workflow_tasks_context = "\\n\\n".join(summaries)
                log_info("action", "run", "workflow_tasks", f"Fetched {len(wf_tasks)} tasks from {wf_laui}")

        # Collect skill documents
        skill_sections = []
        if skill_names:
            for skill_name in skill_names:
                skill_item = _search_skill(skill_name, auth_token, backend_host, project_laui, account_laui)
                if skill_item:
                    skill_sections.append(f"## Skill: {skill_name}\\n\\n{skill_item.get('content', '')}")
                else:
                    skill_sections.append(f"## Skill: {skill_name}\\n\\n(not found in catalog)")
        combined_skill_content = "\\n\\n".join(skill_sections)

        # Build agent prompt
        if prompt:
            parts = [prompt]
            if workflow_tasks_context:
                parts.append(f"## Pipeline Tasks\\n\\n{workflow_tasks_context}")
            if task_context:
                parts.append(f"## Task State\\n\\n```json\\n{task_context}\\n```")
            agent_prompt = "\\n\\n".join(parts)
        elif mode == "post_action" and enable_tools and source_connection_laui and source_table:
            parts = [
                f"You are a data contract auditor. Task `{task_name}` just finished (state: {task_state}) loading data "
                f"into `{source_table}`.\\n\\n"
                f"Using the inspect_data tool, query the live schema of `{source_table}` on connection_laui "
                f"`{source_connection_laui}` (via information_schema.columns) and compare it against the contract/skill "
                "reference below. Flag ANY drift versus what the contract specifies — renamed or missing columns, "
                "type changes, and precision/scale changes (numeric_precision, numeric_scale) even if the column name "
                "and base type are unchanged. For a precision/scale change specifically: state whether it is a "
                "widening (contract violation, no data loss) or a narrowing (contract violation AND a correctness "
                "risk — existing values may be rounded or truncated on write, silently corrupting downstream metrics). "
                "Be concise: 3-6 sentences. State exactly what you found via the tool call, not what you'd expect.",
            ]
            if task_context:
                parts.append(f"## Task State\\n\\n```json\\n{task_context}\\n```")
            agent_prompt = "\\n\\n".join(parts)
        elif mode == "post_action" and task_context:
            agent_prompt = "\\n\\n".join([
                f"Task `{task_name}` finished (state: {task_state}). "
                "Analyse the task payload and last run output to identify anything worth flagging. "
                "Be concise - 3-5 sentences.",
                f"## Task State\\n\\n```json\\n{task_context}\\n```",
            ])
        elif mode == "workflow_audit" and workflow_tasks_context:
            agent_prompt = "\\n\\n".join([
                "You are a data pipeline analyst. Perform a schema drift and consistency audit.\\n\\n"
                "Compare each task payload against the skill reference. Identify schema drift, broken references, "
                "contract mismatches, and cascade impact.\\n\\n"
                "For each issue: task name, exact drift, severity (critical/warning), recommended fix.",
                f"## Pipeline Tasks\\n\\n{workflow_tasks_context}",
            ])
        else:
            parts = [f"Task `{task_name}` finished. Produce a structured report."]
            if task_context:
                parts.append(f"## Task State\\n\\n```json\\n{task_context}\\n```")
            agent_prompt = "\\n\\n".join(parts)

        # Call agent
        analysis = "(No agent configured)"
        if conn_laui and chat_laui:
            ok, conn_err = _validate_connection(conn_laui, auth_token, backend_host)
            if not ok:
                log_error("action", "run", "connection_not_ready", conn_err)
                raise ValueError(conn_err)
            log_info("action", "run", "calling_agent", f"Calling AI agent (enable_tools={enable_tools})")
            result = _call_agent(agent_prompt, combined_skill_content or None, conn_laui, chat_laui, auth_token, backend_host, enable_tools=enable_tools)
            if result:
                analysis = result
                log_info("action", "run", "agent_response", f"Agent analysis received ({len(analysis)} chars)")
            else:
                analysis = "(Agent call failed - see logs)"
                log_error("action", "run", "agent_failed", "Agent returned no response")
        else:
            log_info("action", "run", "no_agent", f"Skipping agent: conn={conn_laui} chat={chat_laui}")

        # Build report
        ts = datetime.now(timezone.utc).isoformat()
        report_lines = [
            "# LeastAction Schema Check Report" if mode == "post_action" else "# LeastAction Audit Report",
            f"**Mode:** {mode}  ",
            f"**Task:** {label}  ",
            f"**State:** {task_state}  " if task_state else "",
            f"**Session:** {session_id}  ",
            f"**Generated:** {ts}  ",
            "", "---", "", "## Analysis", "", analysis,
        ]
        report_text = "\\n".join(report_lines)
        log_info("action", "run", "report_built", f"Report built ({len(report_text)} chars)")

        # Route output: asset always; slack/email only if configured
        dispatched = False
        if notify.get("asset_laui"):
            ap = notify.get("asset_project_laui") or project_laui
            aa = notify.get("asset_account_laui") or account_laui
            if _write_asset(notify["asset_laui"], report_text, label, session_id, auth_token, backend_host, ap, aa):
                log_info("action", "run", "asset_saved", f"Report saved under {notify['asset_laui']}")
                dispatched = True
            else:
                log_error("action", "run", "asset_failed", f"Failed to save under {notify['asset_laui']}")
        if notify.get("email"):
            smtp_cfg = notify.get("smtp", {})
            if _send_email(notify["email"], f"[LeastAction] {label} ({task_state})", report_text, smtp_cfg.get("host", ""), smtp_cfg.get("port", 587), smtp_cfg.get("user", ""), smtp_cfg.get("password", ""), smtp_cfg.get("from_addr", smtp_cfg.get("user", ""))):
                log_info("action", "run", "email_sent", f"Report emailed to {notify['email']}")
                dispatched = True
        if notify.get("slack_url"):
            if _send_slack(notify["slack_url"], label, report_text):
                log_info("action", "run", "slack_sent", "Report posted to Slack")
                dispatched = True
        if not dispatched:
            log_info("action", "run", "report_logged", f"\\n{BANNER}\\n{report_text}\\n{BANNER}")
        log_info("action", "run", "done", "LeastActionAgentDebug complete")
        return True
    except ValueError as e:
        log_error("action", "run", "error", str(e))
        return False
    except Exception as e:
        import traceback
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}\\n{traceback.format_exc()}")
        return False
'''
}

action_variables = {
    "skill_names": [
        "DBT_Postgresql_Sales_Pipelines_Skill.md",
        "DBT_Postgresql_Sales_Data_Contract.md",
    ],
    "chat_laui": "6a4b9eb10c4230f658a985eb",       # AnthropicAgentV2
    "ai_connection": "6a4b9dfb0a091f56877109b0",    # ClaudeApiDebug connection
    "wf_laui": "6a469b4dd878a3d63dca2542",           # dbt_sales_reporting workflow (standalone/audit mode)
    "prompt": "",                                     # custom audit instructions; leave empty for defaults
    "enable_tools": False,                            # set True + source_connection_laui/source_table for live inspect_data checks
    "notify": {
        "asset_laui": "6a4b8e85d5b78ff7c7d136ea",   # DebugReports folder
        "asset_project_laui": "6a469b2dd878a3d63dca2508",
        "asset_account_laui": "6a469b2c617f146531c8bffa",
        # "email": "user@example.com",               # optional — add smtp block if set
        # "slack_url": "https://hooks.slack.com/...", # optional
    },
}

connection = {}

description = (
    "AI-powered post-load schema/contract check. On post_action mode: after every source-load "
    "run, uses inspect_data (via tool-calling) to query information_schema and the live table "
    "itself, comparing against the named skill/contract, and flags drift (renames, precision/scale "
    "changes, etc.) whether or not the load itself succeeded. In standalone mode: full workflow "
    "audit with schema drift, contract mismatch, cascade impact analysis."
)

guide_docs = """# LeastActionAgentDebug — Action Guide

## Modes

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| `post_action` | Attached to a task | Fires on every completion, success or failure. With `enable_tools=True` + `source_connection_laui` + `source_table`, calls `inspect_data` live against the source table and reasons about drift versus the named skill/contract. Without tool-calling, reasons from task state + skill content only |
| `workflow_audit` | Run standalone with `wf_laui` | Fetches all tasks in the workflow, full schema drift + contract audit |
| `standalone` | Run standalone without `wf_laui` | Generic audit with whatever context is available |

## action_variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ai_connection` | yes | LAUI of the Claude connection |
| `chat_laui` | yes | LAUI of the agent chat item |
| `wf_laui` | no | Workflow LAUI — triggers workflow_audit mode when set |
| `skill_names` | no | Skills to pass as reference to the AI. Lookup is an EXACT name match — must include the file's `.md` suffix, e.g. `DBT_Postgresql_Sales_Data_Contract.md` |
| `enable_tools` | no | When `True` in `post_action` mode with `source_connection_laui` + `source_table` set, calls `inspect_data` live against the source table before reasoning |
| `source_connection_laui` | no | Connection LAUI for the live `inspect_data` lookup (only used when `enable_tools=True`) |
| `source_table` | no | Table name for the live `inspect_data` lookup (only used when `enable_tools=True`) |
| `prompt` | no | Custom audit instructions; overrides built-in prompts |
| `notify.asset_laui` | no | Folder to save the HTML report (always written if set) |
| `notify.email` | no | Email address — only sent if key is present |
| `notify.slack_url` | no | Slack webhook — only sent if key is present |

## Post-action behaviour

- Fires on **every** completion, success or failure — this does not skip on success, because
  drift (e.g. a precision change) doesn't make the load itself fail.
- With `enable_tools=True`: calls `inspect_data` against `source_table` live, compares the
  actual schema to the named skill/contract, and distinguishes a non-lossy widening (contract
  violation, no data loss) from a lossy narrowing (contract violation AND a correctness risk).
- Without `enable_tools`: reasons from the task's payload/last-run-output and the skill content
  alone, no live query.
- Report is always written to `notify.asset_laui` if set; email/Slack are additional, optional
  channels — set the corresponding key to also dispatch there.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Debug",
    "tags": ["debug", "agent", "ai", "pipeline", "triage", "audit", "post_action", "inspect_data", "data-contract"],
}

version_details = {
    "version": "3.0.0",
    "core": ["0.*"],
}
