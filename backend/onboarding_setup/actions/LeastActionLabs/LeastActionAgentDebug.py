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
        log_error("action", "_fetch_item", "error", f"Failed to fetch item {laui}: {str(e)}")
        return None


def _search_skill(name, auth_token, backend_host, project_laui=None, account_laui=None):
    try:
        item_filter = {"item_type": "skill", "name": name}
        if project_laui:
            item_filter["project_laui"] = project_laui
        if account_laui:
            item_filter["account_laui"] = account_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/search",
            json={"item_filter": item_filter, "pagination": {}, "projection": {"include": ["name", "laui", "content", "prompt", "description"]}},
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0] if items else None
    except Exception as e:
        log_error("action", "_search_skill", "error", f"Failed to search for skill \'{name}\': {str(e)}")
        return None


def _call_agent(prompt, skill_content, connection_laui, chat_laui, auth_token, backend_host):
    try:
        payload = {
            "prompt": prompt,
            "chat_laui": chat_laui,
            "skill_content": skill_content,
            "enable_tools": False,
        }
        if connection_laui:
            payload["connection_laui"] = connection_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/ai/agent",
            json=payload,
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", "")
    except Exception as e:
        log_error("action", "_call_agent", "error", f"Agent call failed: {str(e)}")
        return None


def _write_local_report(report_text, task_name, session_id):
    try:
        report_dir = "/tmp/la/debug_reports"
        os.makedirs(report_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = (task_name or "unknown").replace("/", "_").replace(" ", "_")
        path = f"{report_dir}/{safe_name}_{session_id[:8]}_{ts}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_text)
        log_info("action", "_write_local_report", "written", f"Report written to {path}")
        return path
    except Exception as e:
        log_error("action", "_write_local_report", "error", f"Failed to write local report: {str(e)}")
        return None


def _send_email(to, subject, body, smtp_host, smtp_port, smtp_user, smtp_password, from_addr):
    if not smtp_host or not from_addr:
        log_error("action", "_send_email", "missing_config", "smtp_host and from_addr are required for email notify")
        return False
    server = None
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        port = int(smtp_port) if smtp_port else 587
        server = smtplib.SMTP(smtp_host, port, timeout=30)
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


def _write_asset(parent_laui, report_text, task_name, session_id, auth_token, backend_host, project_laui=None, account_laui=None):
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = (task_name or "unknown").replace("/", "_").replace(" ", "_")
        item_name = f"debug_{safe_name}_{session_id[:8]}_{ts}"
        html_body = "<pre style='font-family:monospace;white-space:pre-wrap;padding:16px'>{}</pre>".format(
            report_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        payload = {
            "item_type": "html_report",
            "name": item_name,
            "parent_laui": parent_laui,
            "description": f"Debug report for task {task_name} — session {session_id[:8]}",
            "html": html_body,
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
        new_laui = resp.json().get("item_laui", "?")
        log_info("action", "_write_asset", "created", f"Report created as catalog skill {new_laui} under parent {parent_laui}")
        return True
    except Exception as e:
        log_error("action", "_write_asset", "error", f"Failed to create catalog asset: {str(e)}")
        return False


def _send_slack(webhook_url, task_name, report_text):
    try:
        # Slack message cap is 3000 chars per block — send summary + truncated report
        summary = report_text[:2800] + ("\n...(truncated)" if len(report_text) > 2800 else "")
        payload = {
            "text": f":rotating_light: *LeastAction Debug Report — `{task_name}` failed*",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"Debug Report: {task_name}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": summary}
                },
            ],
        }
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        log_error("action", "_send_slack", "error", f"Slack send failed: {str(e)}")
        return False


def _fetch_workflow_tasks(workflow_laui, auth_token, backend_host):
    try:
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/search",
            json={
                "item_filter": {"item_type": "task", "parent_laui": workflow_laui},
                "pagination": {"per_page": 50},
                "projection": {"include": ["name", "laui", "payload", "state", "operator_laui", "connection_laui", "actions"]},
            },
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as e:
        log_error("action", "_fetch_workflow_tasks", "error", f"Failed to fetch tasks for workflow {workflow_laui}: {str(e)}")
        return []


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
    include_task_context=True,
    workflow_laui=None,
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
        task_name = current_task.get("name", "unknown_task")
        project_laui = (current_task.get("project_laui") or least_action_action_object.get("project_laui")) or None
        account_laui = (current_task.get("account_laui") or least_action_action_object.get("account_laui")) or None
        notify = notify or {}

        # connection_laui is set on the action item itself — backend injects it here automatically
        connection_laui = least_action_action_object.get("connection_laui")

        log_info("action", "run", "start",
            f"LeastActionAgentDebug started | task={task_name} | "
            f"skill_names={skill_names} | connection_laui={connection_laui} | "
            f"chat_laui={chat_laui} | notify={list(notify.keys())}"
        )

        # ── 1. Collect task context ──────────────────────────────────────────
        task_context = ""
        if include_task_context:
            task_laui = current_task.get("laui")
            if task_laui:
                fetched = _fetch_item(str(task_laui), auth_token, backend_host)
                task_context = _dump(fetched or current_task)
            else:
                task_context = _dump(current_task)
            log_info("action", "run", "task_context", "Task context collected")

        # ── 1b. Collect all tasks in the workflow for schema drift analysis ──
        workflow_tasks_context = ""
        if workflow_laui:
            wf_tasks = _fetch_workflow_tasks(workflow_laui, auth_token, backend_host)
            if wf_tasks:
                task_summaries = []
                for t in wf_tasks:
                    item = t.get("item", t)
                    name = item.get("name", "?")
                    payload = item.get("payload", "")
                    state = item.get("state", "?")
                    # Truncate large payloads (seed SQL can be 3k+ chars)
                    if isinstance(payload, str) and len(payload) > 1500:
                        payload = payload[:1500] + "\\n...(truncated)"
                    task_summaries.append(f"### {name} (state: {state})\\n\\n```\\n{payload}\\n```")
                workflow_tasks_context = "\\n\\n".join(task_summaries)
                log_info("action", "run", "workflow_tasks", f"Fetched {len(wf_tasks)} tasks from workflow {workflow_laui}")
            else:
                log_info("action", "run", "workflow_tasks", f"No tasks found in workflow {workflow_laui}")

        # ── 2. Collect skill documents ───────────────────────────────────────
        skill_sections = []
        combined_skill_content = ""
        if skill_names:
            for skill_name in skill_names:
                skill_item = _search_skill(skill_name, auth_token, backend_host, project_laui, account_laui)
                if skill_item:
                    content = skill_item.get("content", "")
                    prompt_text = skill_item.get("prompt", "")
                    skill_sections.append(f"## Skill: {skill_name}\\n\\n{content}")
                    if prompt_text:
                        skill_sections.append(f"### Prompt: {skill_name}\\n\\n{prompt_text}")
                    log_info("action", "run", "skill_found", f"Skill \'{skill_name}\' fetched")
                else:
                    skill_sections.append(f"## Skill: {skill_name}\\n\\n(not found in catalog)")
                    log_info("action", "run", "skill_missing", f"Skill \'{skill_name}\' not found")
            combined_skill_content = "\\n\\n".join(skill_sections)

        # ── 3. Build agent prompt ────────────────────────────────────────────
        if workflow_laui and workflow_tasks_context:
            agent_prompt_parts = [
                "You are a data pipeline analyst. Perform a schema drift and consistency audit on the "
                "following pipeline tasks. Compare each task's payload (SQL DDL, dbt model names, contract "
                "checks, etc.) against the documented skill reference below.\\n\\n"
                "Identify:\\n"
                "1. **Schema drift** — columns added, renamed, or dropped vs. the data contract\\n"
                "2. **Broken references** — dbt model names or column names that no longer match\\n"
                "3. **Contract mismatches** — contract checks that reference columns that no longer exist\\n"
                "4. **Cascade impact** — which downstream tasks will fail as a result\\n\\n"
                "For each issue: state the task name, the exact drift, the severity (critical/warning), "
                "and the recommended fix."
            ]
            agent_prompt_parts.append(f"## Pipeline Tasks (current payloads)\\n\\n{workflow_tasks_context}")
        else:
            agent_prompt_parts = [
                f"A task named `{task_name}` has failed. Analyze the failure and produce a structured debug report.",
            ]
            if task_context:
                agent_prompt_parts.append(f"## Current Task State\\n\\n```json\\n{task_context}\\n```")
            if not skill_names or not combined_skill_content:
                agent_prompt_parts.append(
                    "No skill documents were provided. Analyze the task state above and identify "
                    "the most likely root cause. Suggest specific remediation steps."
                )

        agent_prompt = "\\n\\n".join(agent_prompt_parts)

        # ── 4. Call agent ────────────────────────────────────────────────────
        analysis = None
        if connection_laui and chat_laui:
            log_info("action", "run", "calling_agent", "Calling AI agent for analysis")
            analysis = _call_agent(
                prompt=agent_prompt,
                skill_content=combined_skill_content or None,
                connection_laui=connection_laui,
                chat_laui=chat_laui,
                auth_token=auth_token,
                backend_host=backend_host,
            )
            if analysis:
                log_info("action", "run", "agent_response", f"Agent analysis received ({len(analysis)} chars)")
            else:
                log_error("action", "run", "agent_failed", "Agent returned no response")
                analysis = "(Agent call failed — see logs above)"
        else:
            log_info("action", "run", "no_agent", "No connection_laui/chat_laui provided — skipping agent call")
            analysis = "(No agent configured — raw context only)"

        # ── 5. Build report ──────────────────────────────────────────────────
        ts = datetime.now(timezone.utc).isoformat()
        report_lines = [
            f"# LeastActionAgentDebug Report",
            f"**Task:** {task_name}  ",
            f"**Session:** {session_id}  ",
            f"**Generated:** {ts}  ",
            "",
            "---",
            "",
            "## Agent Analysis",
            "",
            analysis,
        ]
        if task_context:
            report_lines += ["", "---", "", "## Task State", "", f"```json", task_context, "```"]
        if combined_skill_content:
            report_lines += ["", "---", "", "## Skill Reference", "", combined_skill_content]
        report_text = "\\n".join(report_lines)

        log_info("action", "run", "report_built", f"Report built ({len(report_text)} chars)")

        # ── 6. Route output ──────────────────────────────────────────────────
        dispatched = False

        # Local file — only write when explicitly configured
        local_path = notify.get("local_path")
        if local_path:
            path = _write_local_report(report_text, task_name, session_id)
            if path:
                log_info("action", "run", "local_report", f"Report saved: {path}")
                dispatched = True

        # Email
        if notify.get("email"):
            smtp_cfg = notify.get("smtp", {})
            sent = _send_email(
                to=notify["email"],
                subject=f"[LeastAction Debug] {task_name} failed",
                body=report_text,
                smtp_host=smtp_cfg.get("host", ""),
                smtp_port=smtp_cfg.get("port", 587),
                smtp_user=smtp_cfg.get("user", ""),
                smtp_password=smtp_cfg.get("password", ""),
                from_addr=smtp_cfg.get("from_addr", smtp_cfg.get("user", "")),
            )
            if sent:
                log_info("action", "run", "email_sent", f"Report emailed to {notify['email']}")
                dispatched = True
            else:
                log_error("action", "run", "email_failed", f"Failed to email report to {notify['email']}")

        if notify.get("slack_url"):
            sent = _send_slack(notify["slack_url"], task_name, report_text)
            if sent:
                log_info("action", "run", "slack_sent", "Report posted to Slack")
                dispatched = True
            else:
                log_error("action", "run", "slack_failed", "Failed to post report to Slack")

        if notify.get("asset_laui"):
            # Use explicit project/account from notify if provided (needed when running standalone)
            asset_project_laui = notify.get("asset_project_laui") or project_laui
            asset_account_laui = notify.get("asset_account_laui") or account_laui
            saved = _write_asset(
                notify["asset_laui"], report_text, task_name, session_id,
                auth_token, backend_host, asset_project_laui, asset_account_laui,
            )
            if saved:
                log_info("action", "run", "asset_saved", f"Report saved to catalog asset {notify['asset_laui']}")
                dispatched = True
            else:
                log_error("action", "run", "asset_failed", f"Failed to save report to catalog asset {notify['asset_laui']}")

        if not dispatched:
            log_info("action", "run", "report_logged", f"\\n{BANNER}\\n  AGENT DEBUG REPORT\\n{BANNER}\\n{report_text}\\n{BANNER}")

        log_info("action", "run", "done", "LeastActionAgentDebug complete")
        return True

    except Exception as e:
        import traceback
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}\\n{traceback.format_exc()}")
        return False
'''
}

connection_laui = "6a4b9dfb0a091f56877109b0"  # ClaudeApiDebug — set on action item, not in code

action_variables = {
    "skill_names": [
        "DBT_Postgresql_Sales_Pipelines_Skill",
        "DBT_Postgresql_Sales_Data_Contract",
    ],
    "chat_laui": "6a4b9eb10c4230f658a985eb",  # AnthropicAgentV2
    "include_task_context": True,
    "workflow_laui": "6a469b4dd878a3d63dca2542",  # dbt_sales_reporting workflow
    "notify": {
        "local_path": "/tmp/la/debug_reports",
        "email": "ananyabs66@gmail.com",
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "user": "",
            "password": "",
            "from_addr": "",
        },
        "slack_url": None,  # e.g. "https://hooks.slack.com/services/xxx/yyy/zzz"
        "asset_laui": "6a4b8e85d5b78ff7c7d136ea",  # DebugReports folder.asset under project assets
        "asset_project_laui": "6a469b2dd878a3d63dca2508",
        "asset_account_laui": "6a469b2c617f146531c8bffa",
    },
}

connection = {}

prompt = (
    "Debug a failing pipeline task using AI analysis: collect the current task state and named skill "
    "documents from the catalog, call an AI agent to produce a structured root-cause analysis, then "
    "route the report to a local file, email, or Slack based on the notify action_variables. "
    "action_variables: skill_names (skills to fetch), connection_laui (Claude connection), "
    "chat_laui (agent chat item), notify.local_path / notify.email / notify.slack_url (output routing). "
    "Always returns True — never gates the pipeline."
)

description = (
    "AI-powered debug action for failing pipeline tasks. Fetches skill documents and task state, "
    "calls an AI agent for root-cause analysis, and routes the report to a local file, email, or Slack. "
    "Attach as a post_action on any failing task. Always returns True."
)

install_docs = """# LeastActionAgentDebug — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionAgentDebug — Action Guide

## What it does

1. Collects the failing task's state from the catalog
2. Fetches named skill documents (pipeline reference, data contract, etc.)
3. Calls an AI agent (`/api/v1/ai/agent`) with the combined context
4. Writes the analysis report based on `notify`:
   - `notify.local_path` → writes a Markdown file to that path on the server
   - `notify.email` → (future) sends via SMTP
   - `notify.slack_url` → (future) POSTs to Slack webhook

---

## action_variables

```json
{
  "skill_names": ["DBT_Postgresql_Sales_Pipelines_Skill", "DBT_Postgresql_Sales_Data_Contract"],
  "connection_laui": "<claude-connection-laui>",
  "chat_laui": "<agent-chat-item-laui>",
  "include_task_context": true,
  "notify": {
    "local_path": "/tmp/la/debug_reports",
    "email": null,
    "slack_url": null
  }
}
```

| Variable | Required | Description |
|----------|----------|-------------|
| `skill_names` | no | Names of skills to fetch and pass to the agent |
| `connection_laui` | yes (for AI) | LAUI of the Claude connection (ClaudeApi) |
| `chat_laui` | yes (for AI) | LAUI of the agent chat item |
| `include_task_context` | no | Log and pass the current task state (default true) |
| `notify.local_path` | no | Directory to write the Markdown report (default `/tmp/la/debug_reports`) |
| `notify.email` | no | Email address to send the report (future) |
| `notify.slack_url` | no | Slack webhook URL (future) |

---

## Returns

Always `True` — debug-only, never gates the pipeline.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Debug",
    "tags": ["debug", "agent", "ai", "pipeline", "analysis", "report", "post_action"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
