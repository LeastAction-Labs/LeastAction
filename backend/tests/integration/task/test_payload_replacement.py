# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# """
# Integration tests for task payload placeholder replacement functionality.
#
# These tests verify that:
# 1. Payload strings with placeholders ({{param_name}}) are replaced with values from config
# 2. Payload_laui content is fetched and placeholders are replaced
# 3. Config merge priority is respected (workflow > attached > task config field)
# 4. Payloads without placeholders remain unchanged
# 5. Placeholders without matching config parameters remain unchanged
#
# NOTE: These tests verify the expected behavior. If tests fail, ensure:
# - The replaced payload from TaskManager.validate_task_creation() is persisted to the database
# - The catalog create endpoint uses the validated task_data.payload value
# """
#
# import pytest
# from datetime import datetime
# from fastapi.testclient import TestClient
# from src.core.catalog.api_request import CreateItemResponse
#
# from src.core.db.types import MongoDatabase
#
# from tests.integration.utils import execute_request
# from tests.integration.schema import TestRequest, BaseFolders, create_base_folders
#
# pytestmark = pytest.mark.anyio
# @pytest.fixture(autouse=True)
# async def database_cleanup(test_database: MongoDatabase, client: TestClient):
#     await test_database.items.drop()
#     await test_database.links.delete_many({})
#     yield  # Test runs here
#     await test_database.items.drop()
#     await test_database.links.drop()
#
#
#
# # ============================================================================
# # FIXTURES
# # ============================================================================
#
#
# @pytest.fixture(autouse=True)
# def base_folders_setup(client:TestClient,database_cleanup):
#    base_folders = create_base_folders(client)
#    yield base_folders
#
# @pytest.fixture
# async def account_laui(base_folders_setup:BaseFolders) -> str:
#     return base_folders_setup.account_folder_laui
#
# @pytest.fixture
# async def project_laui(base_folders_setup: BaseFolders) -> str:
#     return base_folders_setup.project_folder_laui
#
# @pytest.fixture
# async def workflow_laui(client: TestClient, project_laui: str) -> str:
#     """Create a workflow folder under the project"""
#     wf_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "folder.workflow",
#             "name": f"workflow_payload_{datetime.now().timestamp()}",
#             "parent_laui": project_laui,
#         }))
#     assert wf_resp.status_code == 200
#     return CreateItemResponse(**wf_resp.json()).item_laui
#
#
# @pytest.fixture
# async def python_operator_laui(client: TestClient, workflow_laui: str) -> str:
#     """Create a Python operator"""
#     op_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "operator.python",
#             "name": f"python_operator_{datetime.now().timestamp()}",
#             "parent_laui": workflow_laui,
#             "codeblock": { "main.py" : "print('test')"  } ,
#             "bashblock": { "main.sh" : "echo 'test'"  } ,
#         }))
#     assert op_resp.status_code == 200
#     return CreateItemResponse(**op_resp.json()).item_laui
#
#
# @pytest.fixture
# async def python_connection_laui(client: TestClient, workflow_laui: str) -> str:
#     """Create a Python connection environment"""
#     connection_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "connection.python",
#             "name": f"python_connection_{datetime.now().timestamp()}",
#             "parent_laui": workflow_laui,
#             "content": {"type": "docker"},
#         }))
#     assert connection_resp.status_code == 200
#     return CreateItemResponse(**connection_resp.json()).item_laui
#
#
# @pytest.fixture
# async def config_with_parameters(client: TestClient, workflow_laui: str) -> str:
#     """Create a config with parameters for placeholder replacement"""
#     config_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "config.json",
#             "name": f"config_params_{datetime.now().timestamp()}",
#             "parent_laui": workflow_laui,
#             "config_type": "task",
#             "content": {
#                 "parameters": {
#                     "username": "admin",
#                     "password": "secret123",
#                     "host": "localhost",
#                     "port": "5432",
#                     "database": "mydb",
#                 }
#             },
#         }))
#     assert config_resp.status_code == 200
#     return CreateItemResponse(**config_resp.json()).item_laui
#
#
# @pytest.fixture
# async def payload_with_placeholders(client: TestClient, workflow_laui: str) -> str:
#     """Create a payload item with placeholders"""
#     payload_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "payload.json",
#             "name": f"payload_placeholders_{datetime.now().timestamp()}",
#             "parent_laui": workflow_laui,
#             "content": '{"user": "{{username}}", "pass": "{{password}}", "db": "{{database}}"}',
#         }))
#     assert payload_resp.status_code == 200
#     return CreateItemResponse(**payload_resp.json()).item_laui
#
#
# @pytest.fixture
# async def payload_without_placeholders(client: TestClient, workflow_laui: str) -> str:
#     """Create a payload item without placeholders"""
#     payload_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "payload.json",
#             "name": f"payload_no_placeholders_{datetime.now().timestamp()}",
#             "parent_laui": workflow_laui,
#             "content": '{"static": "value", "number": 42}',
#         }))
#     assert payload_resp.status_code == 200
#     return CreateItemResponse(**payload_resp.json()).item_laui
#
#
# # ============================================================================
# # TEST CASES - PAYLOAD STRING
# # ============================================================================
#
#
# async def test_payload_without_placeholders_no_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str):
#     """
#     Case 1: Payload without placeholders and no config - stays as is
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_no_placeholder_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload": '{"static": "data", "value": 100}',
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload unchanged
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     assert task_data["payload"] == '{"static": "data", "value": 100}'
#
#
# async def test_payload_without_placeholders_with_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     config_with_parameters: str):
#     """
#     Case 2: Payload without placeholders with config - stays as is
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_no_placeholder_config_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload": '{"static": "data", "value": 100}',
#             "attached_config_lauis": [config_with_parameters],
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload unchanged
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     assert task_data["payload"] == '{"static": "data", "value": 100}'
#
#
# async def test_payload_with_placeholders_and_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     config_with_parameters: str):
#     """
#     Case 3: Payload with placeholders and parameters in config - gets replaced
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_replacement_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload": '{"user": "{{username}}", "pass": "{{password}}", "server": "{{host}}:{{port}}"}',
#             "attached_config_lauis": [config_with_parameters],
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload replaced
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     # Placeholders should be replaced with config values
#     assert '"user": "admin"' in task_data["payload"]
#     assert '"pass": "secret123"' in task_data["payload"]
#     assert '"server": "localhost:5432"' in task_data["payload"]
#
#
# async def test_payload_with_placeholders_no_matching_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     config_with_parameters: str):
#     """
#     Case 4: Payload with placeholders but parameters not in config - stays as is
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_no_match_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload": '{"api_key": "{{ api_token }}", "endpoint": "{{ api_url }}"}',
#             "attached_config_lauis": [config_with_parameters],
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify placeholders unchanged (no matching params)
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     # Placeholders should remain as they don't match config parameters - DebugUnasync defined adds spaces
#     assert "{{ api_token }}" in task_data["payload"]
#     assert "{{ api_url }}" in task_data["payload"]
#
#
# async def test_payload_partial_replacement_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     config_with_parameters: str):
#     """
#     Payload with some placeholders matching config and some not
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_partial_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload": '{"user": "{{username}}", "unknown": "{{not_in_config}}", "db": "{{database}}"}',
#             "attached_config_lauis": [config_with_parameters],
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify partial replacement
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     # Matching placeholders replaced, unknown ones kept with spaces
#     assert '"user": "admin"' in task_data["payload"]
#     assert "{{ not_in_config }}" in task_data["payload"]
#     assert '"db": "mydb"' in task_data["payload"]
#
#
# async def test_payload_laui_without_placeholders_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     payload_without_placeholders: str):
#     """
#     Case 5: payload_laui without placeholders - content fetched and stays as is
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_laui_no_placeholder_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload_laui": payload_without_placeholders,
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload content fetched and unchanged
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     assert task_data["payload"] == '{"static": "value", "number": 42}'
#
#
# async def test_payload_laui_with_placeholders_and_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     payload_with_placeholders: str,
#     config_with_parameters: str):
#     """
#     Case 6: payload_laui with placeholders and parameters in config - content fetched and replaced
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_laui_replacement_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload_laui": payload_with_placeholders,
#             "attached_config_lauis": [config_with_parameters],
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload fetched and replaced
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     # Placeholders from payload_laui content should be replaced
#     assert '"user": "admin"' in task_data["payload"]
#     assert '"pass": "secret123"' in task_data["payload"]
#     assert '"db": "mydb"' in task_data["payload"]
#
#
# async def test_payload_laui_with_placeholders_no_config_pass(
#     client: TestClient,
#     python_operator_laui: str,
#     python_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str,
#     payload_with_placeholders: str):
#     """
#     Case 7: payload_laui with placeholders but no config - content fetched, stays as is
#     """
#     task_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_payload_laui_no_config_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": python_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#             "payload_laui": payload_with_placeholders,
#         }))
#
#     assert task_resp.status_code == 200
#     task_laui = CreateItemResponse(**task_resp.json()).item_laui
#
#     # Get the task and verify payload fetched but placeholders unchanged
#     get_resp = execute_request(
#         client=client,
#         request=TestRequest(url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}))
#     assert get_resp.status_code == 200
#     task_data = get_resp.json()
#     # Placeholders should remain unchanged (no config) - DebugUnasync defined adds spaces
#     assert "{{ username }}" in task_data["payload"]
#     assert "{{ password }}" in task_data["payload"]
#     assert "{{ database }}" in task_data["payload"]
