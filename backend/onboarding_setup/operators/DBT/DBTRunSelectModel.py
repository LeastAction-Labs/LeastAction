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

codeblock = {"main.py": '''import json
import urllib.request
from src.common.logger.logger import log_info, log_error


def _get_server_url(connection):
    url = connection.get("dbt_server_url", "").strip().rstrip("/")
    if not url:
        raise ValueError("connection must contain 'dbt_server_url' (e.g. http://dbt-demo:8001)")
    return url


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        server_url = _get_server_url(connection)
        log_info("task", "initialize", "health_check", f"Checking dbt-server at {server_url}/health")
        req = urllib.request.Request(f"{server_url}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        log_info("task", "initialize", "health_ok", f"dbt-server responded: {body}")
        return {"base_url": server_url}
    except Exception as e:
        log_error("task", "initialize", "health_failed", f"Could not reach dbt-server: {str(e)}")
        raise


def run(least_action_task_object, client):
    try:
        raw = least_action_task_object.get("payload", "{}")
        if isinstance(raw, str):
            payload = json.loads(raw)
        else:
            payload = raw

        model = payload.get("model", "").strip()
        if not model:
            raise ValueError("payload must contain a non-empty 'model' field")

        log_info("task", "run", "running_model", f"Requesting dbt run for model: {model}")

        body = json.dumps({"model": model}).encode("utf-8")
        req = urllib.request.Request(
            f"{client['base_url']}/run-model",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())

        log_info("task", "run", "dbt_stdout", result.get("stdout", ""))

        if result.get("success"):
            log_info("task", "run", "run_success", f"Model '{model}' completed successfully")
            return {"status": "success", "execution_type": "sync", "model": model, "returncode": result.get("returncode"), "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}
        else:
            log_error("task", "run", "run_failed", f"Model '{model}' failed. stderr: {result.get('stderr', '')}")
            return {"status": "error", "execution_type": "sync", "model": model, "returncode": result.get("returncode"), "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}

    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Error: {str(e)}")
        raise


def check_completion(least_action_task_object, client, run_details):
    return {"status": "success", "message": "Synchronous operation completed", "output": run_details}


def finish(least_action_task_object, client, completion_details, run_details):
    log_info("task", "finish", "cleanup", "No resources to clean up for HTTP operator")
'''}

bashblock = {"main.sh": "# No additional dependencies required — uses Python stdlib only (urllib, json)"}

connection = {"dbt_server_url": "http://dbt-demo:8001"}

payload = '{"model": "stg_badge_events"}'

description = "Runs a single specific dbt model by name by calling a configurable dbt-server HTTP API. Server URL comes from connection."

prompt = "Runs a single specific dbt model by name by calling a configurable dbt-server HTTP API. Server URL comes from connection."

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Transformation",
    "tags": ["dbt", "model", "transformation", "elt", "dbt-server"],
    "airflow_equivalent": "DbtRunOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
