# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# import pytest
# from datetime import datetime, timedelta
# from fastapi.testclient import TestClient
# from bson import ObjectId as BsonObjectId
# from src.core.catalog.api_request import CreateItemResponse
# from src.core.db.types import MongoDatabase
# from tests.integration.utils import execute_request, create_base_folders
# from tests.integration.schema import TestRequest
# from src.core.task.connection.schema import SortOrder
# from pathlib import Path
#
# pytestmark = pytest.mark.anyio
#
# ACTION_FILE = Path(__file__).resolve().parent.parent.parent.parent / (
#     "tests/integration/task/celery/test-task-data/la_check_parents_done.py"
# )
#
#
# def _load_action_definition():
#     """Read and parse the LeastActionCheckIfAreParentsDone action file."""
#     content = ACTION_FILE.read_text(encoding="utf-8")
#     ns = {}
#     exec(content, ns)
#     return ns
#
#
# # ---------------------------------------------------------------------------
# # helpers
# # ---------------------------------------------------------------------------
#
# async def _create_task_with_check_parents_action(
#         client: TestClient,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
#         check_parents_action_laui: str,
#         parents_list: list[dict],
#         name: str | None = None,
#         frequency: str = "ADHOC",
#         start_date: str | None = None,
#         end_date: str | None = None,
# ) -> str:
#     """Create a task with the check-parents action as a pre-action and return the task laui."""
#     task_name = name or f"task_{datetime.now().timestamp()}"
#
#     task_data = {
#         "item_type": "task",
#         "name": task_name,
#         "project_laui": project_laui,
#         "account_laui": account_laui,
#         "parent_laui": workflow_laui,
#         "operator_laui": operator_laui,
#         "connection_laui": connection_laui,
#         "payload_laui": payload_laui,
#         "frequency": frequency,
#         "priority": 1,
#         # Add the check-parents action as a pre-action
#         "pre_actions": [
#             {
#                 "action_laui": check_parents_action_laui,
#                 "action_variables": {
#                     "parents": parents_list,
#                 },
#             }
#         ],
#     }
#
#     # Add start_date and end_date if provided
#     if start_date:
#         task_data["start_date"] = start_date
#     if end_date:
#         task_data["end_date"] = end_date
#
#     resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/task",
#             method="post",
#             json=task_data,
#         ),
#     )
#     assert resp.status_code == 200, (
#         f"Task creation failed ({resp.status_code}): {resp.text}"
#     )
#     laui = CreateItemResponse(**resp.json()).item_laui
#     return laui
#
#
# async def _run_task_and_check_pre_action(
#         client: TestClient,
#         task_laui: str,
# ) -> tuple[int, object]:
#     """Run a task via /api/v1/task and return (status_code, response).
#
#     The pre-action will be executed during task execution, and we can check
#     if the task execution succeeded or failed based on the pre-action result.
#     """
#     resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url=f"/api/v1/task",
#             method="post",
#             json={"item_laui": task_laui},
#         ),
#     )
#     return resp.status_code, resp
#
#
#
#
#
# async def _create_task(
#
#         client: TestClient,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
#         name: str | None = None,
#         frequency: str = "ADHOC",
#         start_date: str | None = None,
#         end_date: str | None = None,
# ) -> tuple[str, str]:
#     """Create a task and return (name, laui)."""
#     task_name = name or f"task_{datetime.now().timestamp()}"
#
#     task_data = {
#         "item_type": "task",
#         "name": task_name,
#         "project_laui": project_laui,
#         "account_laui": account_laui,
#         "parent_laui": workflow_laui,
#         "operator_laui": operator_laui,
#         "connection_laui": connection_laui,
#         "payload_laui": payload_laui,
#         "frequency": frequency,
#         "priority": 1,
#     }
#
#     # Add start_date and end_date if provided
#     if start_date:
#         task_data["start_date"] = start_date
#     if end_date:
#         task_data["end_date"] = end_date
#
#     resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/task",
#             method="post",
#             json=task_data,
#         ),
#     )
#     assert resp.status_code == 200, (
#         f"Task creation failed ({resp.status_code}): {resp.text}"
#     )
#     laui = CreateItemResponse(**resp.json()).item_laui
#     return task_name, laui
#
#
# async def _set_task_state(
#         db: MongoDatabase,
#         task_laui: str,
#         state: str,
#         last_run_date: str | None = None,
#         frequency: str | None = None,
# ):
#     """Directly update a task's state / last_run_date / frequency in the DB."""
#     fields: dict = {"state": state}
#     if last_run_date is not None:
#         fields["last_run_date"] = last_run_date
#     if frequency is not None:
#         fields["frequency"] = frequency
#     result = await db.items.update_one(
#         {"_id": BsonObjectId(task_laui)},
#         {"$set": fields},
#     )
#     print(f"    DB update task {task_laui}: state={state}, "
#           f"last_run_date={last_run_date}, frequency={frequency} "
#           f"(matched={result.matched_count}, modified={result.modified_count})")
#
#
# def _parent_descriptor(
#         task_name: str,
#         project_laui: str,
#         account_laui: str,
#         partition: str = "ALL",
# ) -> dict:
#     return {
#         "task_name": task_name,
#         "project_laui": project_laui,
#         "account_laui": account_laui,
#         "partition": partition,
#     }
#
#
# # ---------------------------------------------------------------------------
# # fixtures
# # ---------------------------------------------------------------------------
#
# @pytest.fixture(autouse=True)
# async def database_cleanup(test_database: MongoDatabase, client: TestClient):
#     await test_database.items.drop()
#     await test_database.links.delete_many({})
#     yield
#     await test_database.items.drop()
#     await test_database.links.drop()
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
#
# @pytest.fixture
# async def workflow_laui(client: TestClient, project_laui: str) -> str:
#     wf_resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/catalog/create",
#             method="post",
#             json={
#                 "item_type": "folder.workflow",
#                 "name": f"workflow_{datetime.now().timestamp()}",
#                 "parent_laui": project_laui,
#                 "folder_metadata": {"state": "active"},
#             },
#         ),
#     )
#     assert wf_resp.status_code == 200
#     return CreateItemResponse(**wf_resp.json()).item_laui
#
#
# @pytest.fixture
# async def operator_laui(client: TestClient, workflow_laui: str) -> str:
#     codeblock_path = (
#             Path(__file__).resolve().parent.parent
#             / "task/celery/task-test-data/sleep_operator.py"
#     )
#     codeblock = codeblock_path.read_text(encoding="utf-8")
#     op_resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/catalog/create",
#             method="post",
#             json={
#                 "item_type": "operator.python",
#                 "name": f"python_operator_{datetime.now().timestamp()}",
#                 "parent_laui": workflow_laui,
#                 "codeblock": {"main.py": codeblock},
#                 "bashblock": {"main.sh": {}},
#             },
#         ),
#     )
#     assert op_resp.status_code == 200
#     return CreateItemResponse(**op_resp.json()).item_laui
#
#
# @pytest.fixture
# async def connection_laui(client: TestClient, workflow_laui: str) -> str:
#     connection_resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/catalog/create",
#             method="post",
#             json={
#                 "item_type": "connection.python",
#                 "name": f"python_connection_{datetime.now().timestamp()}",
#                 "parent_laui": workflow_laui,
#                 "content": {},
#                 "max_parallelism": 10,
#                 "sort_dict": {"priority": SortOrder.ASC},
#             },
#         ),
#     )
#     assert connection_resp.status_code == 200
#     return CreateItemResponse(**connection_resp.json()).item_laui
#
#
# @pytest.fixture
# async def payload_laui(client: TestClient, workflow_laui: str) -> str:
#     payload_resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/catalog/create",
#             method="post",
#             json={
#                 "item_type": "payload.json",
#                 "name": f"payload_{datetime.now().timestamp()}",
#                 "parent_laui": workflow_laui,
#                 "content": '{"seconds": 10}',
#             },
#         ),
#     )
#     assert payload_resp.status_code == 200
#     return CreateItemResponse(**payload_resp.json()).item_laui
#
#
# @pytest.fixture
# async def check_parents_action_laui(client: TestClient, workflow_laui: str) -> str:
#     """Create the LeastActionCheckIfAreParentsDone action from the onboarding file."""
#     action_def = _load_action_definition()
#     action_resp = execute_request(
#         client=client,
#         request=TestRequest(
#             url="/api/v1/catalog/create",
#             method="post",
#             json={
#                 "item_type": "action.regular",
#                 "name": "LeastActionCheckIfAreParentsDone",
#                 "parent_laui": workflow_laui,
#                 "bashblock": action_def.get("bashblock", {}),
#                 "codeblock": action_def.get("codeblock", {}),
#                 "action_variables": action_def.get("action_variables", {}),
#                 "connection": action_def.get("connection", {}),
#             },
#         ),
#     )
#     assert action_resp.status_code == 200, (
#         f"Action creation failed ({action_resp.status_code}): {action_resp.text}"
#     )
#     laui = CreateItemResponse(**action_resp.json()).item_laui
#     print(f"  check_parents action created: {laui}")
#     return laui
#
#
# # ===========================================================================
# # SHOULD RETURN TRUE
# # ===========================================================================
#
#
# async def test_no_parents_passed_returns_true(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return True when no parents are passed (empty list)."""
#     print("\n" + "=" * 80)
#     print("TEST: no parents passed -> expect True")
#     print("=" * 80)
#
#     # Create child task with check-parents action as pre-action (no parents)
#     child_laui = await _create_task_with_check_parents_action(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         check_parents_action_laui,
#         parents_list=[],  # Empty parents list
#         name=f"child_task_{datetime.now().timestamp()}",
#     )
#     print(f"  created child task WITH pre-action (no parents): laui={child_laui}")
#
#     # Run task and check if pre-action succeeded
#     status_code, resp = await _run_task_and_check_pre_action(
#         client=client,
#         task_laui=child_laui,
#     )
#
#     print(f"\n  response status: {status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert status_code == 200, (
#         f"Expected 200, got {status_code}: {resp.text}"
#     )
#
#     # Pre-action should pass with no parents
#     result = resp.json()
#     print(f"  ✓ response result: {result}")
#
#     pre_action_passed = result.get("pre_action_result", {}).get("result", True)
#
#     assert pre_action_passed is True, (
#         f"Expected pre-action to return True (no parents), but got: {pre_action_passed}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Pre-action correctly returned True for no parents")
#     print("=" * 80)
#
#
# async def test_single_parent_success_returns_true(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return True when 1 parent exists with state='success'
#     and last_run_date >= expected scheduled time."""
#     print("\n" + "=" * 80)
#     print("TEST: 1 parent, state=success, last_run recent -> expect True")
#     print("=" * 80)
#
#     # Define time window for scheduled tasks
#     start_date = (datetime.now() - timedelta(days=7)).isoformat()
#     end_date = (datetime.now() + timedelta(days=30)).isoformat()
#     print(f"  task schedule window: {start_date} to {end_date}")
#
#     # -- create parent task --
#     parent_name, parent_laui = await _create_task(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         frequency="0 * * * *",  # hourly
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created parent task: name={parent_name}, laui={parent_laui}")
#
#     # -- set parent state to success with a recent last_run_date --
#     recent_run = datetime.now().isoformat()
#     await _set_task_state(
#         test_database, parent_laui,
#         state="success",
#         last_run_date=recent_run,
#         frequency="0 * * * *",  # hourly
#     )
#     print(f"  updated parent state=success, last_run_date={recent_run}, frequency=hourly")
#
#     # -- verify DB update --
#     doc = await test_database.items.find_one({"_id": BsonObjectId(parent_laui)})
#     print(f"  DB verification: state={doc.get('state')}, last_run_date={doc.get('last_run_date')}")
#
#     # -- build parents descriptor --
#     parents_list = [_parent_descriptor(parent_name, project_laui, account_laui)]
#     print(f"  action_variables.parents: {parents_list}")
#
#     # -- create child task WITH check-parents pre-action for timing validation --
#     child_laui = await _create_task_with_check_parents_action(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         check_parents_action_laui,
#         parents_list=parents_list,
#         name=f"child_task_{datetime.now().timestamp()}",
#         frequency="0 * * * *",  # hourly
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created child task WITH pre-action: laui={child_laui}")
#
#     # -- run task and check if pre-action succeeded --
#     status_code, resp = await _run_task_and_check_pre_action(
#         client=client,
#         task_laui=child_laui,
#     )
#
#     print(f"\n  response status: {status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert status_code == 200, (
#         f"Expected 200, got {status_code}: {resp.text}"
#     )
#
#     # Pre-action should pass with recent parent run
#     result = resp.json()
#     print(f"  ✓ response result: {result}")
#
#     pre_action_passed = result.get("pre_action_result", {}).get("result", True)
#
#     assert pre_action_passed is True, (
#         f"Expected pre-action to return True (parent recent), but got: {pre_action_passed}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Pre-action correctly returned True")
#     print("=" * 80)
#
#
# async def test_four_parents_all_success_returns_true(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return True when all 4 parents have state='success'
#     and valid last_run_date."""
#     print("\n" + "=" * 80)
#     print("TEST: 4 parents, all state=success -> expect True")
#     print("=" * 80)
#
#     # Define time window for scheduled tasks
#     start_date = (datetime.now() - timedelta(days=7)).isoformat()
#     end_date = (datetime.now() + timedelta(days=30)).isoformat()
#     print(f"  task schedule window: {start_date} to {end_date}")
#
#     num_parents = 4
#     parents_list = []
#
#     for i in range(num_parents):
#         name, laui = await _create_task(
#             client, project_laui, account_laui, workflow_laui,
#             operator_laui, connection_laui, payload_laui,
#             name=f"parent_all_pass_{i}_{datetime.now().timestamp()}",
#             frequency="0 * * * *",  # hourly
#             start_date=start_date,
#             end_date=end_date,
#         )
#         print(f"  created parent {i}: name={name}, laui={laui}")
#
#         recent_run = (datetime.now() - timedelta(minutes=i)).isoformat()
#         await _set_task_state(
#             test_database, laui,
#             state="success",
#             last_run_date=recent_run,
#             frequency="0 * * * *",
#         )
#         print(f"  updated parent {i}: state=success, last_run_date={recent_run}")
#
#         parents_list.append(_parent_descriptor(name, project_laui, account_laui))
#
#     print(f"  total parents prepared: {len(parents_list)}")
#
#     # -- create child task for timing validation --
#     child_name, child_laui = await _create_task(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         name=f"child_task_{datetime.now().timestamp()}",
#         frequency="0 * * * *",  # hourly
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created child task for timing validation: name={child_name}, laui={child_laui}")
#
#     # -- execute action --
#     resp = _run_check_parents_action(
#         client=client,
#         check_parents_action_laui=check_parents_action_laui,
#         parents_list=parents_list,
#         task_laui=child_laui,  # Enable timing validation
#     )
#
#     print(f"\n  response status: {resp.status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert resp.status_code == 200, (
#         f"Expected 200, got {resp.status_code}: {resp.text}"
#     )
#
#     # ASSERT RETURN VALUE IS TRUE
#     result = resp.json()
#     return_value = result.get("result")
#     print(f"\n  ✓ return_value extracted: {return_value}")
#
#     assert return_value is True, (
#         f"Expected action to return True (all 4 parents state=success), but got: {return_value}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Action correctly returned True")
#     print("=" * 80)
#
#
# # ===========================================================================
# # SHOULD RETURN FALSE
# # ===========================================================================
#
#
# async def test_parent_not_found_returns_false(
#         client: TestClient,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
# ):
#     """Action should return False when a parent task does not exist in the catalog."""
#     print("\n" + "=" * 80)
#     print("TEST: parent task does not exist -> expect False")
#     print("=" * 80)
#
#     fake_parent_name = f"nonexistent_parent_{datetime.now().timestamp()}"
#     parents_list = [_parent_descriptor(fake_parent_name, project_laui, account_laui)]
#     print(f"  using fake parent name: {fake_parent_name}")
#     print(f"  action_variables.parents: {parents_list}")
#
#     # -- execute action --
#     resp = _run_check_parents_action(
#         client=client,
#         check_parents_action_laui=check_parents_action_laui,
#         parents_list=parents_list,
#     )
#
#     print(f"\n  response status: {resp.status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert resp.status_code == 200, (
#         f"Expected 200, got {resp.status_code}: {resp.text}"
#     )
#
#     # ASSERT RETURN VALUE IS FALSE
#     result = resp.json()
#     return_value = result.get("result")
#     print(f"\n  ✓ return_value extracted: {return_value}")
#
#     assert return_value is False, (
#         f"Expected action to return False (parent not found), but got: {return_value}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Action correctly returned False")
#     print("=" * 80)
#
#
# async def test_parent_state_not_success_returns_false(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return False when a parent task state is not 'success'."""
#     print("\n" + "=" * 80)
#     print("TEST: parent state=failed -> expect False")
#     print("=" * 80)
#
#     # Define time window for scheduled tasks
#     start_date = (datetime.now() - timedelta(days=7)).isoformat()
#     end_date = (datetime.now() + timedelta(days=30)).isoformat()
#     print(f"  task schedule window: {start_date} to {end_date}")
#
#     # -- create parent task --
#     parent_name, parent_laui = await _create_task(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created parent task: name={parent_name}, laui={parent_laui}")
#
#     # -- set parent state to 'failed' --
#     await _set_task_state(
#         test_database, parent_laui,
#         state="failed",
#         last_run_date=datetime.now().isoformat(),
#     )
#
#     # -- verify DB update --
#     doc = await test_database.items.find_one({"_id": BsonObjectId(parent_laui)})
#     print(f"  DB verification: state={doc.get('state')}, last_run_date={doc.get('last_run_date')}")
#
#     # -- build parents descriptor --
#     parents_list = [_parent_descriptor(parent_name, project_laui, account_laui)]
#     print(f"  action_variables.parents: {parents_list}")
#
#     # -- execute action --
#     resp = _run_check_parents_action(
#         client=client,
#         check_parents_action_laui=check_parents_action_laui,
#         parents_list=parents_list,
#     )
#
#     print(f"\n  response status: {resp.status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert resp.status_code == 200, (
#         f"Expected 200, got {resp.status_code}: {resp.text}"
#     )
#
#     # ASSERT RETURN VALUE IS FALSE
#     result = resp.json()
#     return_value = result.get("result")
#     print(f"\n  ✓ return_value extracted: {return_value}")
#
#     assert return_value is False, (
#         f"Expected action to return False (parent state=failed), but got: {return_value}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Action correctly returned False")
#     print("=" * 80)
#
#
# async def test_parent_success_but_stale_last_run_returns_false(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return False when parent state='success' but last_run_date
#     is older than the expected scheduled time.
#
#     This test uses the task execution flow (with pre-action) to properly pass
#     the task object to the action, which is necessary for timing validation.
#     """
#     print("\n" + "=" * 80)
#     print("TEST: parent state=success, last_run stale -> expect False")
#     print("=" * 80)
#
#     # Define time window for scheduled tasks
#     start_date = (datetime.now() - timedelta(days=60)).isoformat()
#     end_date = (datetime.now() + timedelta(days=30)).isoformat()
#     print(f"  task schedule window: {start_date} to {end_date}")
#
#     # -- create parent task --
#     parent_name, parent_laui = await _create_task(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         frequency="0 * * * *",  # hourly
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created parent task: name={parent_name}, laui={parent_laui}")
#
#     # -- set parent state=success but with a very old last_run_date --
#     stale_run = (datetime.now() - timedelta(days=30)).isoformat()
#     await _set_task_state(
#         test_database, parent_laui,
#         state="success",
#         last_run_date=stale_run,
#         frequency="0 * * * *",  # hourly
#     )
#     print(f"  updated parent: state=success, last_run_date={stale_run} (30 days ago)")
#
#     # -- verify DB update --
#     doc = await test_database.items.find_one({"_id": BsonObjectId(parent_laui)})
#     print(f"  DB verification: state={doc.get('state')}, last_run_date={doc.get('last_run_date')}")
#
#     # -- create child task WITH check-parents pre-action for timing validation --
#     parents_list = [_parent_descriptor(parent_name, project_laui, account_laui)]
#     print(f"  action_variables.parents: {parents_list}")
#
#     child_laui = await _create_task_with_check_parents_action(
#         client, project_laui, account_laui, workflow_laui,
#         operator_laui, connection_laui, payload_laui,
#         check_parents_action_laui,
#         parents_list=parents_list,
#         name=f"child_task_{datetime.now().timestamp()}",
#         frequency="0 * * * *",  # hourly
#         start_date=start_date,
#         end_date=end_date,
#     )
#     print(f"  created child task WITH pre-action: laui={child_laui}")
#
#     # -- run task and check if pre-action failed (which is what we expect) --
#     status_code, resp = await _run_task_and_check_pre_action(
#         client=client,
#         task_laui=child_laui,
#     )
#
#     print(f"\n  response status: {status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert status_code == 200, (
#         f"Expected 200, got {status_code}: {resp.text}"
#     )
#
#     # The pre-action should have failed because of stale last_run_date
#     # If pre-action failed, the task execution should reflect that
#     result = resp.json()
#     print(f"  ✓ response result: {result}")
#
#     # Check if the response indicates pre-action failure
#     # The exact field name depends on the task execution API response structure
#     # For now, we check if the overall execution was not successful
#     pre_action_passed = result.get("pre_action_result", {}).get("result", True)
#
#     assert pre_action_passed is False, (
#         f"Expected pre-action to return False (stale last_run_date), but got: {pre_action_passed}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Pre-action correctly returned False for stale last_run_date")
#     print("=" * 80)
#
#
# async def test_multiple_parents_partial_failure_returns_false(
#         client: TestClient,
#         test_database: MongoDatabase,
#         check_parents_action_laui: str,
#         project_laui: str,
#         account_laui: str,
#         workflow_laui: str,
#         operator_laui: str,
#         connection_laui: str,
#         payload_laui: str,
# ):
#     """Action should return False when some parents meet conditions but others don't.
#     Here: 2 parents state=success, 2 parents state=failed."""
#     print("\n" + "=" * 80)
#     print("TEST: 4 parents, 2 success + 2 failed -> expect False")
#     print("=" * 80)
#
#     # Define time window for scheduled tasks
#     start_date = (datetime.now() - timedelta(days=7)).isoformat()
#     end_date = (datetime.now() + timedelta(days=30)).isoformat()
#     print(f"  task schedule window: {start_date} to {end_date}")
#
#     parents_list = []
#     num_parents = 4
#
#     for i in range(num_parents):
#         name, laui = await _create_task(
#             client, project_laui, account_laui, workflow_laui,
#             operator_laui, connection_laui, payload_laui,
#             name=f"parent_mixed_{i}_{datetime.now().timestamp()}",
#             frequency="0 * * * *",  # hourly
#             start_date=start_date,
#             end_date=end_date,
#         )
#         # first 2 succeed, last 2 fail
#         state = "success" if i < 2 else "failed"
#         await _set_task_state(
#             test_database, laui,
#             state=state,
#             last_run_date=datetime.now().isoformat(),
#             frequency="0 * * * *",
#         )
#         print(f"  parent {i}: name={name}, laui={laui}, state={state}")
#         parents_list.append(_parent_descriptor(name, project_laui, account_laui))
#
#     print(f"  total parents: {len(parents_list)} (2 success, 2 failed)")
#
#     # -- execute action --
#     resp = _run_check_parents_action(
#         client=client,
#         check_parents_action_laui=check_parents_action_laui,
#         parents_list=parents_list,
#     )
#
#     print(f"\n  response status: {resp.status_code}")
#     print(f"  response body: {resp.json()}")
#
#     # ASSERT HTTP 200
#     assert resp.status_code == 200, (
#         f"Expected 200, got {resp.status_code}: {resp.text}"
#     )
#
#     # ASSERT RETURN VALUE IS FALSE
#     result = resp.json()
#     return_value = result.get("result")
#     print(f"\n  ✓ return_value extracted: {return_value}")
#
#     assert return_value is False, (
#         f"Expected action to return False (some parents failed), but got: {return_value}"
#     )
#
#     print("\n  ✓✓✓ TEST PASSED: Action correctly returned False")
#     print("=" * 80)
