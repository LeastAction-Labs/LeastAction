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

codeblock = {'main.py': '"""\n'
            'LeastAction Dummy Operator\n'
            '\n'
            'A simple dummy operator for testing and demonstration purposes.\n'
            'This operator simulates basic task execution with configurable behavior.\n'
            '"""\n'
            '\n'
            'import time\n'
            'import json\n'
            'from src.common.logger.logger import log_info, log_error\n'
            '\n'
            '\n'
            'def initialize(least_action_task_object):\n'
            '    try:\n'
            "        connection = least_action_task_object.get('connection', {})\n"
            "        task_laui = least_action_task_object.get('laui')\n"
            '        \n'
            '        log_info("task", "initialize", "extracting_connection_details", "Initializing dummy operator")\n'
            '        \n'
            "        host = connection.get('host', 'localhost')\n"
            "        port = connection.get('port', 8080)\n"
            "        timeout = connection.get('timeout', 30)\n"
            '        \n'
            '        log_info("task", "initialize", "creating_client", "Creating dummy client")\n'
            '        \n'
            '        client = {\n'
            "            'host': host,\n"
            "            'port': port,\n"
            "            'timeout': timeout,\n"
            "            'connected': True,\n"
            "            'client_type': 'dummy'\n"
            '        }\n'
            '        \n'
            '        log_info("task", "initialize", "connection_successful",\n'
            '                 "Dummy client initialized successfully")\n'
            '        return client\n'
            '        \n'
            '    except Exception as e:\n'
            '        log_error("task", "initialize", "initialization_error",\n'
            '                  f"Error during initialization: {str(e)}")\n'
            '        raise\n'
            '\n'
            '\n'
            'def run(least_action_task_object, client):\n'
            '    try:\n'
            "        payload = least_action_task_object.get('payload', {})\n"
            "        task_laui = least_action_task_object.get('laui')\n"
            '        \n'
            '        log_info("task", "run", "extracting_payload", "Extracting payload")\n'
            '        \n'
            "        # payload is a flat dict - read fields directly (not nested under 'data')\n"
            '        if isinstance(payload, str):\n'
            '            try:\n'
            '                payload = json.loads(payload)\n'
            '            except json.JSONDecodeError:\n'
            '                log_error("task", "run", "payload_parse_error",\n'
            '                          "Failed to parse payload as JSON")\n'
            '                return {\n'
            "                    'status': 'failed',\n"
            "                    'execution_type': 'sync',\n"
            "                    'result': None,\n"
            "                    'error': 'Invalid payload format'\n"
            '                }\n'
            '        \n'
            '        if not isinstance(payload, dict):\n'
            '            payload = {}\n'
            '\n'
            "        message = payload.get('message', 'No message provided')\n"
            "        operation = payload.get('operation', 'default')\n"
            "        delay_seconds = payload.get('delay_seconds', 0)\n"
            "        async_mode = payload.get('async_mode', False)\n"
            '        \n'
            '        log_info("task", "run", "operation_start", "Starting operation")\n'
            '        \n'
            '        if delay_seconds > 0:\n'
            '            log_info("task", "run", "simulating_delay", "Simulating operation delay")\n'
            '            time.sleep(delay_seconds)\n'
            '        \n'
            '        result_data = {\n'
            "            'message': message,\n"
            "            'operation': operation,\n"
            "            'execution_time_seconds': delay_seconds,\n"
            "            'timestamp': str(time.time()),\n"
            "            'client_info': {\n"
            "                'host': client.get('host'),\n"
            "                'port': client.get('port'),\n"
            "                'connected': client.get('connected')\n"
            '            }\n'
            '        }\n'
            '        \n'
            '        log_info("task", "run", "operation_completed",\n'
            '                 f"Operation {operation} completed successfully")\n'
            '        \n'
            "        execution_type = 'async' if async_mode else 'sync'\n"
            '        \n'
            '        return {\n'
            "            'status': 'success',\n"
            "            'execution_type': execution_type,\n"
            "            'result': result_data,\n"
            '            \'operation_id\': f"{task_laui}-{int(time.time())}"\n'
            '        }\n'
            '        \n'
            '    except Exception as e:\n'
            '        log_error("task", "run", "execution_error",\n'
            '                  f"Error during execution: {str(e)}")\n'
            '        return {\n'
            "            'status': 'failed',\n"
            "            'execution_type': 'sync',\n"
            "            'result': None,\n"
            "            'error': str(e)\n"
            '        }\n'
            '\n'
            '\n'
            'def check_completion(least_action_task_object, client, run_details):\n'
            '    try:\n'
            "        if run_details.get('execution_type') == 'sync':\n"
            '            log_info("task", "check_completion", "sync_operation",\n'
            '                     "Synchronous operation - no status check needed")\n'
            '            return {\n'
            "                'status': 'success',\n"
            "                'message': 'Synchronous operation completed',\n"
            "                'output': run_details.get('result')\n"
            '            }\n'
            '        \n'
            "        if run_details.get('status') == 'failed':\n"
            '            log_error("task", "check_completion", "run_failed",\n'
            '                      f"Run operation failed: {run_details.get(\'error\')}")\n'
            '            return {\n'
            "                'status': 'failed',\n"
            '                \'message\': f"Run operation failed: {run_details.get(\'error\')}",\n'
            "                'output': None\n"
            '            }\n'
            '        \n'
            "        operation_id = run_details.get('operation_id')\n"
            '        log_info("task", "check_completion", "checking_async_status",\n'
            '                 f"Checking status for operation: {operation_id}")\n'
            '        \n'
            '        completion_data = {\n'
            "            'operation_id': operation_id,\n"
            "            'status_message': 'Async operation completed successfully',\n"
            "            'result': run_details.get('result'),\n"
            "            'completion_time': str(time.time())\n"
            '        }\n'
            '        \n'
            '        log_info("task", "check_completion", "async_operation_complete",\n'
            '                 f"Async operation {operation_id} completed")\n'
            '        \n'
            '        return {\n'
            "            'status': 'success',\n"
            "            'message': 'Async operation completed successfully',\n"
            "            'output': completion_data\n"
            '        }\n'
            '        \n'
            '    except Exception as e:\n'
            '        log_error("task", "check_completion", "status_check_error",\n'
            '                  f"Error during status check: {str(e)}")\n'
            '        return {\n'
            "            'status': 'failed',\n"
            '            \'message\': f"Status check error: {str(e)}",\n'
            "            'output': None\n"
            '        }\n'
            '\n'
            '\n'
            'def finish(least_action_task_object, client, completion_details, run_details):\n'
            '    try:\n'
            "        task_laui = least_action_task_object.get('laui')\n"
            '        \n'
            '        log_info("task", "finish", "starting_cleanup", "Starting cleanup")\n'
            '        \n'
            "        final_status = completion_details.get('status', 'unknown') if "
            "completion_details else 'unknown'\n"
            '        log_info("task", "finish", "final_status",\n'
            '                 f"Task completed with status: {final_status}")\n'
            '        \n'
            '        if client:\n'
            '            try:\n'
            '                log_info("task", "finish", "client_cleanup",\n'
            '                         f"Cleaning up dummy client - host: {client.get(\'host\')}, '
            'port: {client.get(\'port\')}")\n'
            "                client['connected'] = False\n"
            '            except Exception as e:\n'
            '                log_error("task", "finish", "client_cleanup_error",\n'
            '                          f"Error during client cleanup: {str(e)}")\n'
            '        \n'
            "        if final_status == 'success':\n"
            "            output = completion_details.get('output', {}) if completion_details else "
            '{}\n'
            '            log_info("task", "finish", "operation_summary",\n'
            '                     f"Operation completed successfully - output: {json.dumps(output, '
            'default=str)}")\n'
            "        elif final_status == 'failed':\n"
            "            msg = completion_details.get('message') if completion_details else "
            "'unknown'\n"
            '            log_error("task", "finish", "operation_failed",\n'
            '                      f"Operation failed: {msg}")\n'
            '        \n'
            '        log_info("task", "finish", "cleanup_completed", "Cleanup completed")\n'
            '        \n'
            '    except Exception as e:\n'
            '        log_error("task", "finish", "cleanup_error",\n'
            '                  f"Error during finish/cleanup: {str(e)}")\n'}

bashblock = {'main.sh': '#!/bin/bash\n'
            '\n'
            '# No external dependencies required for dummy operator\n'
            'echo "LeastActionDummy operator - no external dependencies needed"\n'
            '\n'
            'echo "Dependencies check completed successfully"'}

connection = {'host': 'localhost', 'port': 8080, 'timeout': 30}

payload = {'delay_seconds': 0, 'message': 'Hello from LeastActionDummy', 'operation': 'test'}

prompt = (
    "A no-op test operator for validating the LeastAction execution pipeline. "
    "Payload fields: message (string), operation (string label), delay_seconds (sleep duration), "
    "async_mode (bool — returns async execution_type if True). "
    "initialize() creates a dummy client dict. run() sleeps delay_seconds then returns result. "
    "check_completion() handles both sync and async modes. No external dependencies required. "
    "Use this to test connections, scheduler behaviour, and workflow wiring without side effects."
)

install_docs = """# LeastActionDummy — Install Guide

## Dependencies

No external dependencies. The empty bash block is intentional — nothing to install.

## Usage

Add this operator to any workflow to:
- Validate that the LeastAction executor is working correctly
- Test scheduler and dependency logic without executing real operations
- Simulate async workflows using async_mode=true in payload
"""

guide_docs = """# LeastActionDummy — Operator Guide

## What it does

A no-op operator that simulates task execution without performing any real operations.
Useful for testing pipelines, validating scheduler behaviour, and debugging workflow wiring.

---

## Connection

    {"host": "localhost", "port": 8080, "timeout": 30}

All fields are optional — not used in any real operation.

---

## Payload

    {
      "message": "Hello from LeastActionDummy",
      "operation": "test",
      "delay_seconds": 0,
      "async_mode": false
    }

| Field         | Required | Default | Description                                      |
|---------------|----------|---------|--------------------------------------------------|
| message       | No       | ""      | A message string included in the result          |
| operation     | No       | default | Label for the operation (cosmetic only)          |
| delay_seconds | No       | 0       | Sleep duration to simulate long-running tasks    |
| async_mode    | No       | false   | If true, returns execution_type=async            |

---

## Output (on success)

    {
      "message": "Hello from LeastActionDummy",
      "operation": "test",
      "execution_time_seconds": 0,
      "timestamp": "...",
      "client_info": {"host": "localhost", "port": 8080, "connected": true}
    }
"""

description = """
No-op test operator that validates the LeastAction execution pipeline without side effects.
Accepts configurable delay and message fields. Supports both sync and async execution modes.
Use for testing scheduler behaviour, workflow wiring, and pipeline connectivity.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Testing",
    "tags": ["dummy", "test", "noop", "debug", "pipeline"],
    "airflow_equivalent": "EmptyOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

