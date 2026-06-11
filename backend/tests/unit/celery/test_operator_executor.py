# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Test 1: validate function with all methods present - pass
# Test 2: validate function with no methods present - fail
# Test 3: validate function when run is coroutine - fail
from datetime import UTC, datetime
from types import ModuleType

import pytest
from bson import ObjectId

from src.common.config import Config
from src.common.exceptions import InvalidOperatorError
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.celery.executors.operator_executor import OperatorExecutor
from src.core.celery.schema import TaskRequest


@pytest.fixture
def real_config():
    """Create a real config for logger initialization"""
    config = Config()
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture(autouse=True)
def setup_logger(real_config):
    """Initialize logger before each test and clean up after"""
    initialize_logger(real_config)
    yield
    get_logger_manager().clear_loggers()


@pytest.fixture
def mock_account_laui():
    """Mock account LAUI for testing"""
    return ObjectId()


@pytest.fixture
def mock_project_laui():
    """Mock project LAUI for testing"""
    return ObjectId()


@pytest.fixture
def mock_parent_laui():
    """Mock parent LAUI for testing"""
    return ObjectId()


@pytest.fixture
def mock_connection_laui():
    """Mock connection LAUI for testing"""
    return ObjectId()


@pytest.fixture
def mock_operator_laui():
    """Mock operator LAUI for testing"""
    return ObjectId()


@pytest.fixture
def mock_task(
    mock_account_laui, mock_project_laui, mock_parent_laui, mock_connection_laui, mock_operator_laui
):
    """Create a mock TaskRequest for testing"""
    return TaskRequest(
        name="test_task",
        item_type="task",
        laui="test_laui",
        account_laui=mock_account_laui,
        project_laui=mock_project_laui,
        parent_laui=mock_parent_laui,
        last_run_session_id="test_session",
        connection_laui=mock_connection_laui,
        connection={},
        payload="{}",
        operator_laui=mock_operator_laui,
        frequency="daily",
        logical_date=datetime.now(UTC),
        retry_number=0,
        user_access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdkZjQ4ZmU2NGI5MGI3ZTA0ODlkMzUiLCJleHAiOjIwODUyMjIyODgsImlhdCI6MTc2OTg2MjI4OCwiaXNzIjoiTGVhc3RBY3Rpb24tQVBJLU9yZzEiLCJ0eXBlIjoiYWNjZXNzIn0.gDZv5Ww5bwekjlJqWT579DPOQE831_AjKbNbuJV2bZTUGW9Hfsht8C70nXS3-Zj7LJ7sva_7FVY6lbu-_RzLNDypQ6m1Y5QpPb6lFQuKRTu3XdvDSpcrJKeDJjz6r1xkYHf3YZUGuJ1W4zj-M_xJZjYkakfUzBd3sIK7_z7o-QYADxwii_OWMVlk_i5QaTb2pcs_fVNqtF6Ov0_W7t7gFK5YXNFjIYfVISV11aU_0NS5ovRnHa1tAxM8z1HO3jhZl5JnZQeli2gkex69v8OmLHjEv9Xueppm3wcJ8wBQIbECzoOqeC98W1DkU1T6TfXehbZJJzgTLNDywa0MZ_jCEA",
    )


@pytest.fixture
def complete_operator_module():
    """Create a module with all required methods"""
    module = ModuleType("complete_operator")

    def initialize(task):
        return {"client": "initialized"}

    def run(task, client):
        return {"result": "success"}

    def check_completion(task, client, result):
        return {"status": "completed"}

    def finish(task, client, completion_details, result):
        pass

    module.initialize = initialize
    module.run = run
    module.check_completion = check_completion
    module.finish = finish

    return module


@pytest.fixture
def empty_operator_module():
    """Create a module with no methods"""
    return ModuleType("empty_operator")


@pytest.fixture
def async_run_operator_module():
    """Create a module with async run method"""
    module = ModuleType("async_operator")

    def initialize(task):
        return {"client": "initialized"}

    async def run(task, client):
        return {"result": "success"}

    def check_completion(task, client, result):
        return {"status": "completed"}

    def finish(task, client, completion_details, result):
        pass

    module.initialize = initialize
    module.run = run
    module.check_completion = check_completion
    module.finish = finish

    return module


def test_validate_with_all_methods_present_passes(complete_operator_module, mock_task):
    """Test validate function with all methods present - should pass"""
    executor = OperatorExecutor(complete_operator_module, mock_task)

    # Should not raise any exception
    executor.validate()


def test_validate_with_no_methods_present_fails(
    empty_operator_module, mock_task, mock_operator_laui
):
    """Test validate function with no methods present - should fail"""
    executor = OperatorExecutor(empty_operator_module, mock_task)

    with pytest.raises(InvalidOperatorError) as exc_info:
        executor.validate()

    assert exc_info.value.message == "Operator module is missing required methods"
    assert "missing_methods" in exc_info.value.detail
    assert set(exc_info.value.detail["missing_methods"]) == {
        "initialize",
        "run",
        "check_completion",
        "finish",
    }
    assert exc_info.value.detail["operator_laui"] == mock_operator_laui


def test_validate_when_run_is_coroutine_fails(
    async_run_operator_module, mock_task, mock_operator_laui
):
    """Test validate function when run is coroutine - should fail"""
    executor = OperatorExecutor(async_run_operator_module, mock_task)

    with pytest.raises(InvalidOperatorError) as exc_info:
        executor.validate()

    assert "run() must be synchronous" in exc_info.value.message
    assert str(mock_operator_laui) in exc_info.value.message
    assert exc_info.value.detail["operator_laui"] == mock_operator_laui
    assert exc_info.value.detail["reason"] == "Async run() is not allowed."


def test_validate_with_partial_methods_fails(mock_task, mock_operator_laui):
    """Test validate function with only some methods present - should fail"""
    module = ModuleType("partial_operator")

    def initialize(task):
        return {"client": "initialized"}

    def run(task, client):
        return {"result": "success"}

    module.initialize = initialize
    module.run = run

    executor = OperatorExecutor(module, mock_task)

    with pytest.raises(InvalidOperatorError) as exc_info:
        executor.validate()

    assert exc_info.value.message == "Operator module is missing required methods"
    assert "check_completion" in exc_info.value.detail["missing_methods"]
    assert "finish" in exc_info.value.detail["missing_methods"]
    assert exc_info.value.detail["operator_laui"] == mock_operator_laui


def test_validate_with_non_callable_method_fails(mock_task, mock_operator_laui):
    """Test validate function when a required method is not callable - should fail"""
    module = ModuleType("non_callable_operator")

    def initialize(task):
        return {"client": "initialized"}

    def check_completion(task, client, result):
        return {"status": "completed"}

    def finish(task, client, completion_details, result):
        pass

    module.initialize = initialize
    module.run = "not a function"  # Not callable
    module.check_completion = check_completion
    module.finish = finish

    executor = OperatorExecutor(module, mock_task)

    with pytest.raises(InvalidOperatorError) as exc_info:
        executor.validate()

    assert exc_info.value.message == "Operator module is missing required methods"
    assert "run (not callable)" in exc_info.value.detail["missing_methods"]
    assert exc_info.value.detail["operator_laui"] == mock_operator_laui
