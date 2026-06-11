# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock = {"main.py": '''
import os
import re
import json
import requests
from collections import defaultdict, deque
from src.common.logger.logger import log_info, log_error

DBT_RUN_MODEL_OPERATOR_LAUI = '69fb52cb198163a36cc6d619'
DBT_RUN_SELECT_MODEL_OPERATOR_LAUI = '69fc84903639a116d9db8936'
LEAST_ACTION_CHECK_PARENTS_LAUI = '69d52cd543cc13c4e56a5cd3'


def natural_sort_key(s):
    parts = re.split(r'(\\d+)', s)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def topological_sort(files, deps):
    in_degree = {f: 0 for f in files}
    for f in files:
        for dep in deps.get(f, []):
            if dep in in_degree:
                in_degree[f] += 1
    queue = deque([f for f in files if in_degree[f] == 0])
    result = []
    while queue:
        current = queue.popleft()
        result.append(current)
        for f in files:
            if current in deps.get(f, []) and f in in_degree:
                in_degree[f] -= 1
                if in_degree[f] == 0:
                    queue.append(f)
    if len(result) != len(files):
        remaining = [f for f in files if f not in result]
        log_error('action', 'topological_sort', 'circular_dependency', f'Circular dependency detected: {remaining}')
        result.extend(remaining)
    return result


def parse_refs(sql_content):
    pattern = r"\\{\\{\\s*ref\\s*\\(\\s*['\\\"]([^'\\\"]+)['\\\"]\\s*[^)]*\\)\\s*\\}\\}"
    return set(re.findall(pattern, sql_content, re.IGNORECASE))


def task_exists_in_folder(task_name, workflow_folder_laui, project_laui, account_laui, partition, user_access_token):
    backend_host = os.getenv('BACKEND_HOST', 'backend')
    api_url = f'http://{backend_host}:8000/api/v1/catalog/search'
    headers = {'Cookie': f'frontend_token={user_access_token}', 'Content-Type': 'application/json'}
    body = {
        'item_filter': {
            'item_type': 'task',
            'name': task_name,
            'project_laui': project_laui,
            'account_laui': account_laui,
            'partition': partition,
            'get_by_pk': True,
        },
        'pagination': {},
        'projection': {'include': ['name', 'laui', 'parent_laui']},
    }
    try:
        response = requests.post(api_url, json=body, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            for item in response.json().get('items', []):
                if item.get('parent_laui') == workflow_folder_laui:
                    return item['laui']
    except Exception as e:
        log_error('action', 'task_exists_in_folder', 'check_failed', f"Could not check task '{task_name}': {str(e)}")
    return None


def create_task(task_body, user_access_token):
    backend_host = os.getenv('BACKEND_HOST', 'backend')
    api_url = f'http://{backend_host}:8000/api/v1/catalog/create'
    headers = {'Cookie': f'frontend_token={user_access_token}', 'Content-Type': 'application/json'}

    log_info('action', 'create_task', 'request_details',
        f"[CREATE_TASK REQUEST] "
        f"url={api_url} | "
        f"access_token={user_access_token} | "
        f"headers={json.dumps(headers)} | "
        f"body={json.dumps(task_body, indent=2)}"
    )

    try:
        response = requests.post(api_url, json=task_body, headers=headers, timeout=30)

        log_info('action', 'create_task', 'response_details',
            f"[CREATE_TASK RESPONSE] "
            f"url={api_url} | "
            f"status_code={response.status_code} | "
            f"response_headers={dict(response.headers)} | "
            f"response_body={response.text}"
        )

        if response.status_code in (200, 201):
            data = response.json()
            item_laui = data.get('item_laui') or data.get('laui')
            log_info('action', 'create_task', 'success',
                f"[CREATE_TASK SUCCESS] task_name={task_body.get('name')} | laui={item_laui} | full_response={json.dumps(data, indent=2)}"
            )
            return True, item_laui

        log_error('action', 'create_task', 'bad_status',
            f"[CREATE_TASK FAILED] task_name={task_body.get('name')} | "
            f"status_code={response.status_code} | "
            f"response_body={response.text} | "
            f"request_url={api_url} | "
            f"request_body={json.dumps(task_body, indent=2)} | "
            f"access_token={user_access_token}"
        )
        return False, f"{response.status_code}: {response.text}"

    except Exception as e:
        import traceback
        log_error('action', 'create_task', 'exception',
            f"[CREATE_TASK EXCEPTION] task_name={task_body.get('name')} | "
            f"error={str(e)} | "
            f"traceback={traceback.format_exc()} | "
            f"request_url={api_url} | "
            f"request_body={json.dumps(task_body, indent=2)} | "
            f"access_token={user_access_token}"
        )
        return False, str(e)


def get_models_from_server(dbt_server_url):
    url = f"{dbt_server_url.rstrip('/')}/list-models"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise Exception(f'Failed to list models: {response.status_code} {response.text}')
    return response.json().get('models', [])


def get_model_details_from_server(dbt_server_url):
    url = f"{dbt_server_url.rstrip('/')}/list-models-detail"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json().get('models', [])
    except Exception:
        pass
    return None


def run(
    least_action_action_object,
    import_mode,
    workflow_folder_laui,
    project_laui,
    account_laui,
    connection_name,
    partition=None,
    model_name=None,
):
    tasks_created = 0
    tasks_skipped = 0
    failed = []

    try:
        log_info('action', 'run', 'start', f'DBTImportModel started. mode={import_mode}')

        resolved_partition = partition if partition else 'ALL'
        log_info('action', 'run', 'partition', f'Using partition={resolved_partition}')

        user_access_token = least_action_action_object.get('user_access_token')
        if not user_access_token:
            log_error('action', 'run', 'missing_token', 'Missing user_access_token')
            return False

        connection_laui = least_action_action_object.get('connection_laui')
        if not connection_laui:
            log_error('action', 'run', 'missing_connection_laui', 'connection_laui not found in action object')
            return False
        log_info('action', 'run', 'connection_resolved', f'connection_laui={connection_laui}')

        connection_obj = least_action_action_object.get('connection', {})
        if isinstance(connection_obj, str):
            connection_obj = json.loads(connection_obj)
        dbt_server_url = connection_obj.get('dbt_server_url', '').strip()
        if not dbt_server_url:
            log_error('action', 'run', 'missing_dbt_server_url', 'connection must have dbt_server_url')
            return False
        log_info('action', 'run', 'dbt_server_url', f'Using dbt-server at {dbt_server_url}')

        # SINGLE MODE
        if import_mode == 'single':
            if not model_name or not model_name.strip():
                log_error('action', 'run', 'missing_model_name', "model_name required for import_mode='single'")
                return False

            model_name = re.sub(r'[^\\w]', '_', model_name.strip())
            log_info('action', 'run', 'operator', f'single mode using DBTRunSelectModel={DBT_RUN_SELECT_MODEL_OPERATOR_LAUI}')

            model_details = get_model_details_from_server(dbt_server_url)
            model_sql = ''
            if model_details:
                for m in model_details:
                    if m.get('name') == model_name:
                        model_sql = m.get('sql', '')
                        break

            try:
                available = get_models_from_server(dbt_server_url)
                if model_name not in available:
                    log_error('action', 'run', 'model_not_found', f"Model '{model_name}' not found. Available: {available}")
                    return False
            except Exception as e:
                log_error('action', 'run', 'list_models_failed', str(e))
                return False

            task_name = f'dbt_{model_name}_task'
            existing = task_exists_in_folder(task_name, workflow_folder_laui, project_laui, account_laui, resolved_partition, user_access_token)
            if existing:
                log_info('action', 'run', 'task_exists', f"Task '{task_name}' already exists in this workflow - skipping")
                return True

            task_body = {
                'item_type': 'task',
                'name': task_name,
                'parent_laui': workflow_folder_laui,
                'project_laui': project_laui,
                'account_laui': account_laui,
                'operator_laui': DBT_RUN_SELECT_MODEL_OPERATOR_LAUI,
                'connection_laui': connection_laui,
                'frequency': 'ADHOC',
                'partition': resolved_partition,
                'payload': json.dumps({'model': model_name, 'sql': model_sql}),
                'state': 'scheduled',
            }

            log_info('action', 'run', 'pre_create_task',
                f"[SINGLE MODE] About to call create_task | "
                f"task_name={task_name} | "
                f"partition={resolved_partition} | "
                f"workflow_folder_laui={workflow_folder_laui} | "
                f"project_laui={project_laui} | "
                f"account_laui={account_laui} | "
                f"operator_laui={DBT_RUN_SELECT_MODEL_OPERATOR_LAUI} | "
                f"connection_laui={connection_laui} | "
                f"model_name={model_name} | "
                f"access_token={user_access_token} | "
                f"full_task_body={json.dumps(task_body, indent=2)}"
            )

            success, result = create_task(task_body, user_access_token)
            if success:
                log_info('action', 'run', 'task_created', f"Created task '{task_name}' laui={result}")
                tasks_created += 1
            else:
                log_error('action', 'run', 'task_create_failed',
                    f"Failed to create '{task_name}' | "
                    f"reason={result} | "
                    f"partition={resolved_partition} | "
                    f"workflow_folder_laui={workflow_folder_laui} | "
                    f"project_laui={project_laui} | "
                    f"account_laui={account_laui} | "
                    f"connection_laui={connection_laui} | "
                    f"access_token={user_access_token} | "
                    f"full_task_body={json.dumps(task_body, indent=2)}"
                )
                failed.append({'name': task_name, 'reason': result})

            log_info('action', 'run', 'summary', f'Done. created={tasks_created} failed={len(failed)}')
            return len(failed) == 0

        # FULL MODE
        elif import_mode == 'full':
            log_info('action', 'run', 'operator', f'full mode using DBTRunModel={DBT_RUN_MODEL_OPERATOR_LAUI}')

            try:
                all_models = get_models_from_server(dbt_server_url)
                log_info('action', 'run', 'models_listed', f'Found {len(all_models)} models: {all_models}')
            except Exception as e:
                log_error('action', 'run', 'list_models_failed', str(e))
                return False

            if not all_models:
                log_error('action', 'run', 'no_models', 'dbt-server returned no models')
                return False

            model_details = get_model_details_from_server(dbt_server_url)
            if model_details is None:
                log_info('action', 'run', 'detail_fallback', '/list-models-detail not available - using flat list')
                model_details = [{'name': m, 'folder': '', 'sql': ''} for m in all_models]

            sql_map = {m['name']: m.get('sql', '') for m in model_details}

            folder_map = defaultdict(list)
            for m in model_details:
                folder_map[m.get('folder', '')].append(m)
            sorted_folders = sorted(folder_map.keys(), key=lambda p: natural_sort_key(os.path.basename(p) if p else ''))
            log_info('action', 'run', 'folder_order', f'Processing folders: {sorted_folders}')

            for folder in sorted_folders:
                models_in_folder = folder_map[folder]
                model_names_in_folder = {m['name'] for m in models_in_folder}
                log_info('action', 'run', 'folder_start', f'Folder {folder!r}: {sorted([m["name"] for m in models_in_folder])}')

                dependencies = defaultdict(list)
                for m in models_in_folder:
                    refs = parse_refs(m.get('sql', ''))
                    for ref in refs:
                        if ref in model_names_in_folder:
                            dependencies[m['name']].append(ref)
                        else:
                            log_info('action', 'run', 'cross_folder_ref',
                                     f"'{m['name']}' refs '{ref}' outside folder - ignored for ordering")
                    log_info('action', 'run', 'model_deps', f"'{m['name']}' depends on: {dependencies[m['name']]}")

                sorted_models = topological_sort([m['name'] for m in models_in_folder], dependencies)
                log_info('action', 'run', 'processing_order', f'Order for {folder!r}: {sorted_models}')

                newly_created_in_folder = {}

                for model in sorted_models:
                    task_name = f'dbt_{model}_task'

                    existing = task_exists_in_folder(task_name, workflow_folder_laui, project_laui, account_laui, resolved_partition, user_access_token)
                    if existing:
                        log_info('action', 'run', 'task_exists', f"'{task_name}' already exists in this workflow - skipping")
                        newly_created_in_folder[model] = existing
                        tasks_skipped += 1
                        continue

                    pre_actions = []
                    parent_descriptors = [
                        {
                            'task_name': f'dbt_{dep}_task',
                            'project_laui': project_laui,
                            'account_laui': account_laui,
                            'partition': resolved_partition,
                        }
                        for dep in dependencies.get(model, [])
                        if dep in newly_created_in_folder
                    ]
                    if parent_descriptors:
                        pre_actions = [{
                            'laui': LEAST_ACTION_CHECK_PARENTS_LAUI,
                            'action_variables': {'parents': parent_descriptors}
                        }]
                        log_info('action', 'run', 'pre_actions_added',
                                 f"'{task_name}' waits for: {[p['task_name'] for p in parent_descriptors]}")

                    task_body = {
                        'item_type': 'task',
                        'name': task_name,
                        'parent_laui': workflow_folder_laui,
                        'project_laui': project_laui,
                        'account_laui': account_laui,
                        'operator_laui': DBT_RUN_MODEL_OPERATOR_LAUI,
                        'connection_laui': connection_laui,
                        'frequency': 'ADHOC',
                        'partition': resolved_partition,
                        'payload': json.dumps({'model': model, 'sql': sql_map.get(model, '')}),
                        'state': 'scheduled',
                    }
                    if pre_actions:
                        task_body['actions'] = {
                            'create_actions': [],
                            'pre_actions': pre_actions,
                            'running_actions': [],
                            'post_actions': [],
                        }

                    log_info('action', 'run', 'pre_create_task',
                        f"[FULL MODE] About to call create_task | "
                        f"task_name={task_name} | "
                        f"partition={resolved_partition} | "
                        f"folder={folder!r} | "
                        f"workflow_folder_laui={workflow_folder_laui} | "
                        f"project_laui={project_laui} | "
                        f"account_laui={account_laui} | "
                        f"operator_laui={DBT_RUN_MODEL_OPERATOR_LAUI} | "
                        f"connection_laui={connection_laui} | "
                        f"model={model} | "
                        f"has_pre_actions={bool(pre_actions)} | "
                        f"access_token={user_access_token} | "
                        f"full_task_body={json.dumps(task_body, indent=2)}"
                    )

                    success, result = create_task(task_body, user_access_token)
                    if success:
                        log_info('action', 'run', 'task_created', f"Created '{task_name}' laui={result}")
                        newly_created_in_folder[model] = result
                        tasks_created += 1
                    else:
                        log_error('action', 'run', 'task_create_failed',
                            f"Failed to create '{task_name}' | "
                            f"reason={result} | "
                            f"partition={resolved_partition} | "
                            f"folder={folder!r} | "
                            f"workflow_folder_laui={workflow_folder_laui} | "
                            f"project_laui={project_laui} | "
                            f"account_laui={account_laui} | "
                            f"connection_laui={connection_laui} | "
                            f"access_token={user_access_token} | "
                            f"full_task_body={json.dumps(task_body, indent=2)}"
                        )
                        failed.append({'name': task_name, 'reason': result})

            log_info('action', 'run', 'summary',
                     f'Done. total={len(all_models)} created={tasks_created} skipped={tasks_skipped} failed={len(failed)}')
            return len(failed) == 0

        else:
            log_error('action', 'run', 'invalid_mode', f"Unknown import_mode '{import_mode}'. Use 'full' or 'single'")
            return False

    except Exception as e:
        import traceback
        log_error('action', 'run', 'unexpected_error', f'Unexpected error: {str(e)}\\n{traceback.format_exc()}')
        return False
'''}

bashblock = {"script.sh": ""}

action_variables = {
    "import_mode": "full",
    "model_name": "",
    "workflow_folder_laui": "",
    "project_laui": "",
    "account_laui": "",
    "partition": "",
    "connection_name": "dbt_server_connection"
}

connection = {
    "dbt_server_url": "http://host.docker.internal:8001"
}

prompt = (
    "Import dbt models. full: one task per model using DBTRunModel with pre-action dependencies. "
    "single: one task for selected model using DBTRunSelectModel."
)

description = (
    "Imports dbt models and creates LA tasks. full mode: one task per model using DBTRunModel with pre-action dependencies. "
    "single mode: one task for selected model using DBTRunSelectModel."
)

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Transformation",
    "tags": ["dbt", "import", "model", "task", "pipeline"],
    "airflow_equivalent": "DbtRunOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
