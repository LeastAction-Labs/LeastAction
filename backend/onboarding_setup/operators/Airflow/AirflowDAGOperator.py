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
operator_type = "airflow"
codeblock = {"main.py":'''
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional

from src.common.logger.logger import log_info, log_error


def initialize(least_action_task_object: Dict[str, Any]) -> requests.Session:
    """
    Initialize Airflow connection and authenticate with JWT token.
    Airflow 3.x: JWT token endpoint is at /auth/token (not /api/v2/auth/token)
    """
    try:
        connection = least_action_task_object.get('connection', {})
        base_url = connection.get('base_url', '').rstrip('/')
        username = connection.get('username')
        password = connection.get('password')

        if not all([base_url, username, password]):
            raise ValueError('Missing required connection fields: base_url, username, password')

        log_info("task", "initialize", "initializing_connection", "Initializing Airflow connection to {base_url}")

        # Authenticate with Airflow 3 JWT - use /auth/token endpoint
        auth_url = f"{base_url}/auth/token"
        auth_payload = {"username": username, "password": password}
        
        log_info("task", "initialize", "authenticating", "Authenticating with JWT via /auth/token")
        auth_response = requests.post(auth_url, json=auth_payload, timeout=10)
        
        # Check for 201 Created or 200 OK
        if auth_response.status_code not in [200, 201]:
            log_error("task", "initialize", "jwt_auth_failed", "JWT auth failed")
            raise ValueError(f'JWT authentication failed: {auth_response.status_code}')
        
        token = auth_response.json().get('access_token')
        
        if not token:
            raise ValueError('Failed to obtain access token from Airflow')
        
        log_info("task", "initialize", "jwt_token_obtained", "Successfully obtained JWT token")
        
        # Create authenticated session
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {token}'})
        
        # Verify connectivity with /api/v2/dags
        log_info("task", "initialize", "verifying_connectivity", "Verifying Airflow API connectivity")
        test_url = f"{base_url}/api/v2/dags"
        test_response = session.get(test_url, timeout=10)
        
        if test_response.status_code >= 400:
            log_error("task", "initialize", "api_verification_failed", f"API verification failed: {test_response.status_code}")
            raise RuntimeError(f'Failed to verify API connectivity: {test_response.status_code}')
        
        log_info("task", "initialize", "connection_established", "Successfully connected to Airflow")
        return session
        
    except requests.exceptions.RequestException as e:
        log_error("task", "initialize", "connection_failed", f"Airflow connection failed: {str(e)}")
        raise RuntimeError(f'Airflow connection failed: {str(e)}')
    except Exception as e:
        log_error("task", "initialize", "initialization_failed", f"Unexpected error during initialization: {str(e)}")
        raise


def run(least_action_task_object: Dict[str, Any], client: requests.Session) -> Dict[str, Any]:
    """
    Trigger Airflow DAG run. Handles both reference and with-code modes.
    """
    try:
        connection = least_action_task_object.get('connection', {})
        base_url = connection.get('base_url', '').rstrip('/')
        payload = least_action_task_object.get('payload', '')
        config = least_action_task_object.get('config', {})
        logical_date = least_action_task_object.get('logical_date')
        task_name = least_action_task_object.get('name', 'unknown_task')

        log_info("task", "run", "starting_execution", f"Starting DAG execution for task: {task_name}")

        # Determine mode: with_code (Python string) or reference (JSON/dict)
        is_with_code = isinstance(payload, str) and ('def ' in payload or 'import ' in payload)
        log_info("task", "run", "execution_mode_detected", f"Execution mode: {'with_code' if is_with_code else 'reference'}")
        
        if is_with_code:
            dag_id = config.get('parameters', {}).get('dag_id')
            if not dag_id:
                raise ValueError('dag_id required in config.parameters for with-code mode')
            dag_code = payload
            log_info("task", "run", "with_code_mode", f"With-code mode: dag_id={dag_id}")
        else:
            # Reference mode: payload is JSON or dict with dag_id
            if isinstance(payload, str):
                payload_dict = json.loads(payload)
            else:
                payload_dict = payload
            dag_id = payload_dict.get('dag_id')
            if not dag_id:
                raise ValueError('dag_id required in payload for reference mode')
            log_info("task", "run", "reference_mode", f"Reference mode: dag_id={dag_id}")

        # If with-code mode: upload DAG code
        if is_with_code:
            log_info("task", "run", "uploading_dag_code", f"Uploading DAG code for {dag_id}")
            try:
                files_url = f"{base_url}/api/v2/files"
                dag_filename = f"dags/{dag_id}.py"
                
                files_payload = {
                    'path': dag_filename,
                    'content': dag_code
                }
                
                log_info("task", "run", "uploading_dag_file", f"Uploading to {dag_filename}")
                upload_response = client.post(files_url, json=files_payload, timeout=30)
                
                if upload_response.status_code not in [200, 201]:
                    log_info("task", "run", "dag_upload_warning", f"File upload returned {upload_response.status_code}, proceeding anyway")
                else:
                    log_info("task", "run", "dag_code_uploaded", "DAG code uploaded successfully")
                
                # Wait for Airflow to parse the DAG
                log_info("task", "run", "waiting_for_dag_parse", "Waiting for Airflow to parse DAG")
                max_retries = 30
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        dag_response = client.get(f"{base_url}/api/v2/dags/{dag_id}", timeout=10)
                        if dag_response.status_code == 200:
                            dag_data = dag_response.json()
                            if dag_data.get('is_paused'):
                                log_info("task", "run", "unpausing_dag", f"Unpausing DAG {dag_id}")
                                unpause_response = client.patch(
                                    f"{base_url}/api/v2/dags/{dag_id}",
                                    json={'is_paused': False},
                                    timeout=10
                                )
                                if unpause_response.status_code not in [200, 204]:
                                    log_info("task", "run", "unpause_warning", f"Unpause returned {unpause_response.status_code}")
                            log_info("task", "run", "dag_ready", f"DAG {dag_id} ready")
                            break
                    except requests.exceptions.RequestException:
                        pass
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(1)
                
                if retry_count >= max_retries:
                    log_info("task", "run", "dag_parse_timeout", f"DAG {dag_id} parsing timeout, proceeding with trigger")
                    
            except Exception as e:
                log_error("task", "run", "dag_upload_failed", f"Failed to upload DAG code: {str(e)}")
                raise RuntimeError(f'Failed to upload DAG code: {str(e)}')

        # Build trigger payload - Airflow 3.x requires specific format
        # Use current UTC time as logical_date if not provided
        if not logical_date:
            logical_date = datetime.utcnow().isoformat() + 'Z'
            log_info("task", "run", "logical_date_set", f"No logical_date provided, using current time: {logical_date}")
        elif not isinstance(logical_date, str):
            logical_date = logical_date.isoformat() if hasattr(logical_date, 'isoformat') else str(logical_date)
        
        # Ensure logical_date is in ISO format with Z suffix for UTC
        if logical_date and not logical_date.endswith('Z') and '+' not in logical_date:
            logical_date = logical_date + 'Z'
        
        # Build the minimal required trigger payload
        trigger_payload = {
            'logical_date': logical_date
        }
        
        log_info("task", "run", "logical_date", f"Logical date: {logical_date}")
        
        # Add DAG config from LeastAction config.parameters
        dag_conf = config.get('parameters', {})
        if dag_conf:
            dag_conf_filtered = {k: v for k, v in dag_conf.items() if k != 'dag_id'}
            if dag_conf_filtered:
                trigger_payload['conf'] = dag_conf_filtered
                log_info("task", "run", "dag_config", f"DAG config: {dag_conf_filtered}")

        # Trigger DAG run
        trigger_url = f"{base_url}/api/v2/dags/{dag_id}/dagRuns"
        log_info("task", "run", "triggering_dag", f"Triggering DAG: POST {trigger_url}")
        log_info("task", "run", "trigger_payload", f"Payload: {json.dumps(trigger_payload)}")
        
        try:
            trigger_response = client.post(trigger_url, json=trigger_payload, timeout=30)
            
            if trigger_response.status_code >= 400:
                log_error("task", "run", "trigger_failed", f"Trigger failed ({trigger_response.status_code}): {trigger_response.text}")
                trigger_response.raise_for_status()
            
            run_data = trigger_response.json()
            
            dag_run_id = run_data.get('dag_run_id')
            state = run_data.get('state', 'queued')
            
            log_info("task", "run", "dag_triggered", f"DAG triggered successfully: run_id={dag_run_id}, state={state}")
            
            return {
                'dag_run_id': str(dag_run_id),
                'dag_id': str(dag_id),
                'execution_type': 'async',
                'status': 'pending',
                'result': {
                    'state': str(state),
                    'triggered_at': datetime.utcnow().isoformat()
                }
            }
            
        except requests.exceptions.RequestException as e:
            log_error("task", "run", "dag_trigger_failed", f"Failed to trigger DAG {dag_id}: {str(e)}")
            return {
                'status': 'error',
                'execution_type': 'async',
                'error': str(e),
                'debug_payload': trigger_payload
            }

    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {
            'status': 'failed',
            'execution_type': 'async',
            'error': str(e)
        }


def check_completion(least_action_task_object: Dict[str, Any], client: requests.Session, run_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check DAG run completion status.
    """
    try:
        connection = least_action_task_object.get('connection', {})
        base_url = connection.get('base_url', '').rstrip('/')
        
        dag_id = run_details.get('dag_id')
        dag_run_id = run_details.get('dag_run_id')

        if not dag_id or not dag_run_id:
            log_error("task", "check_completion", "missing_run_details", "Missing dag_id or dag_run_id in run_details")
            return {'status': 'error', 'message': 'Missing dag_id or dag_run_id in run_details'}

        log_info("task", "check_completion", "checking_status", f"Checking status for DAG run: {dag_id}/{dag_run_id}")
        
        try:
            status_url = f"{base_url}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}"
            status_response = client.get(status_url, timeout=10)
            status_response.raise_for_status()
            
            run_data = status_response.json()
            airflow_state = run_data.get('state', 'unknown')
            
            log_info("task", "check_completion", "airflow_state", f"Airflow state: {airflow_state}")
            
            # Map Airflow states to LeastAction states
            if airflow_state == 'success':
                la_status = 'success'
            elif airflow_state in ['failed', 'upstream_failed']:
                la_status = 'failed'
            elif airflow_state in ['running', 'queued', 'scheduled']:
                la_status = 'pending'
            else:
                la_status = 'unknown'
            
            output = {
                'airflow_state': str(airflow_state),
                'start_date': run_data.get('start_date'),
                'end_date': run_data.get('end_date')
            }
            
            log_info("task", "check_completion", "mapped_status", f"Mapped status: {la_status}")
            
            return {
                'status': la_status,
                'message': f'DAG run {dag_run_id} is {la_status}',
                'output': output
            }
            
        except requests.exceptions.RequestException as e:
            log_error("task", "check_completion", "status_check_failed", f"Failed to check DAG run status: {str(e)}")
            return {'status': 'error', 'message': f'Failed to check status: {str(e)}'}

    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", f"Unexpected error during check_completion: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def finish(least_action_task_object: Dict[str, Any], client: requests.Session, completion_details: Dict[str, Any], run_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finalize operator execution. Close session and log results.
    """
    try:
        dag_id = run_details.get('dag_id')
        dag_run_id = run_details.get('dag_run_id')
        status = completion_details.get('status')
        
        log_info("task", "finish", "finishing_run", f"Finishing DAG run {dag_run_id} ({dag_id}) with status: {status}")
        
        # Close the session
        client.close()
        log_info("task", "finish", "session_closed", "Airflow session closed")

    except Exception as e:
        log_error("task", "finish", "finish_error", f"Error in finish: {str(e)}")
'''
}
bashblock = {"main.sh":"""
"""

}

connection = {
  "base_url": "http://host.docker.internal:8080",
  "username": "admin",
  "password": "something"
}
payload={
  "dag_id": "daily_hello"
}

prompt = (
    "Trigger an Airflow DAG run via the Airflow 3.x REST API. "
    "Authenticates with JWT via /auth/token, verifies connectivity with /api/v2/dags. "
    "Two modes: reference mode (payload contains dag_id + optional conf dict) and "
    "with-code mode (payload is a Python DAG string — uploads to Airflow files API and waits for parse). "
    "Async: trigger returns dag_run_id, check_completion polls /api/v2/dags/{dag_id}/dagRuns/{dag_run_id} "
    "until state is success/failed. "
    "Connection fields: base_url (Airflow server), username, password. "
    "Returns dag_run_id, dag_id, airflow_state, start_date, end_date on completion."
)

install_docs = """# AirflowDAGOperator — Install Guide

## Dependencies

No external Python packages required beyond the standard library (uses requests, which is
installed by default in LeastAction). The empty main.sh is intentional.

## Airflow Setup

- Airflow 3.x must be accessible at base_url from the execution environment
- The Airflow user (username/password) must have DAG trigger permissions
- For with-code mode, the user must have file upload permissions via /api/v2/files

## Connection Fields

| Field    | Required | Description                          |
|----------|----------|--------------------------------------|
| base_url | Yes      | Airflow server URL, e.g. http://host:8080 |
| username | Yes      | Airflow login username               |
| password | Yes      | Airflow login password               |
"""

guide_docs = """# AirflowDAGOperator — Operator Guide

## What it does

Triggers an Apache Airflow DAG run via the Airflow 3.x REST API. Supports two modes:

**Reference mode**: payload is a JSON dict with dag_id. Triggers an existing DAG.

**With-code mode**: payload is a Python DAG string. Uploads the code to Airflow's files API,
waits for Airflow to parse it, then triggers the run.

Execution is async: run() returns immediately after triggering. check_completion() polls
the DAG run status until it reaches success, failed, or upstream_failed.

---

## Connection

    {
      "base_url": "http://host.docker.internal:8080",
      "username": "admin",
      "password": "your_password"
    }

---

## Payload (reference mode)

    {"dag_id": "daily_etl"}

## Payload (with-code mode)

    from airflow import DAG
    from airflow.operators.python import PythonOperator
    ...

Set dag_id in config.parameters when using with-code mode.

---

## Output (on success)

    {
      "airflow_state": "success",
      "start_date": "2026-01-01T00:00:00+00:00",
      "end_date": "2026-01-01T00:05:12+00:00"
    }
"""

description = """
Triggers an Airflow DAG run via the Airflow 3.x REST API using JWT authentication.
Supports reference mode (trigger by dag_id) and with-code mode (upload Python DAG then trigger).
Async execution: submits the trigger in run(), polls DAG run state in check_completion().
"""

publisher = "LeastAction"

metadata = {
    "service": "Airflow",
    "category": "Orchestration",
    "tags": ["airflow", "dag", "trigger", "workflow", "orchestration"],
    "airflow_equivalent": "TriggerDagRunOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
