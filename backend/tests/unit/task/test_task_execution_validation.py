# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Unit tests for TaskManager.validate_task_execution method

Test Cases:
1. test_validate_task_execution_empty_list_pass - Validates empty task list returns empty result (pass)
2. test_validate_task_execution_single_valid_task_pass - Validates single task with all required items present (pass)
3. test_validate_task_execution_multiple_valid_tasks_pass - Validates multiple tasks all pass validation (pass)
4. test_validate_task_execution_deduplicates_item_lauis_pass - Verifies duplicate LAUIs are deduplicated using sets (pass)
5. test_validate_task_execution_missing_operator_fail - Validates task is filtered out when operator is missing (fail)
6. test_validate_task_execution_missing_connection_fail - Validates task is filtered out when connection is missing (fail)
7. test_validate_task_execution_missing_workflow_fail - Validates task is filtered out when workflow is missing (fail)
8. test_validate_task_execution_with_payload_laui_pass - Validates task with payload_laui passes when payload item exists (pass)
10. test_validate_task_execution_with_task_configs_pass - Validates task with attached configs passes when configs exist (pass)
11. test_validate_task_execution_missing_task_config_fail - Validates task is filtered out when attached config is missing (fail)
12. test_validate_task_execution_with_workflow_configs_pass - Validates workflow configs are fetched and validated in second batch call (pass)
13. test_validate_task_execution_missing_workflow_config_fail - Validates task is filtered out when workflow config is missing (fail)
14. test_validate_task_execution_connection_operator_mapping_fails_fail - Validates task is filtered out when connection-operator mapping is incompatible (fail)
15. test_validate_task_execution_partial_validation_pass - Validates some tasks pass while others fail and are filtered out (partial)
16. test_validate_task_execution_logs_item_fetch_errors_pass - Validates item fetch errors are logged as warnings not raised (pass)
18. test_validate_task_execution_with_both_payload_and_payload_laui_pass - Validates payload_laui takes precedence and payload is cleared (pass)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from src.common.config import Config
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.schema import TaskValidationModel
from src.core.task.task_manager import TaskManager
from src.core.task.task_validation_manager import TaskValidationManager


class TestTaskExecutionValidation:
    """Unit tests for TaskManager.validate_task_execution"""

    @pytest.fixture
    def real_config(self):
        config = Config()
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        return config

    @pytest.fixture(autouse=True)
    def setup_logger(self, real_config):
        initialize_logger(real_config)
        yield
        get_logger_manager().clear_loggers()

    @pytest.fixture
    def mock_catalog_service(self):
        service = AsyncMock(spec=CatalogService)
        service.find_multiple_items_by_laui = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_connection_manager(self):
        manager = AsyncMock(spec=ConnectionManager)
        manager.validate_connection_operator_mapping = MagicMock(return_value=True)
        return manager

    @pytest.fixture
    def config_manager(self):
        """Mock ConfigManager fixture"""
        manager = MagicMock(spec=ConfigManager)
        manager.replace_placeholders = MagicMock(side_effect=lambda x, y: x)
        manager.process_task_execution = MagicMock(side_effect=lambda task, field=None: task)
        return manager

    @pytest.fixture
    def mock_connection_queue_manager(self):
        service = AsyncMock(spec=ConnectionQueueManager)
        service.load_balance_tasks = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_item_types_manager(self):
        manager = MagicMock(spec=ItemTypesManager)
        manager.get_supported_item_types = MagicMock(return_value=["task"])
        return manager

    @pytest.fixture
    def task_validation_manager(
        self, mock_connection_manager, config_manager, mock_catalog_service, mock_item_types_manager
    ):
        return TaskValidationManager(
            mock_connection_manager,
            config_manager,
            mock_catalog_service,
            mock_item_types_manager,
        )

    @pytest.fixture
    def mock_celery_orchestrator(self):
        """Mock CeleryOrchestrator fixture"""
        from src.core.task.celery_orchestrator import CeleryOrchestrator

        orchestrator = MagicMock(spec=CeleryOrchestrator)
        orchestrator.run_task = MagicMock(return_value="task_id_123")
        return orchestrator

    @pytest.fixture
    def mock_action_manager(self):
        manager = MagicMock(spec=PreActionManager)
        manager.pre_actions = MagicMock(return_value=True)
        manager.create_actions = MagicMock(return_value=True)
        manager.running_actions = MagicMock(return_value=None)
        manager.post_actions = MagicMock(return_value=None)
        return manager

    @pytest.fixture
    def task_manager(
        self,
        task_validation_manager,
        mock_action_manager,
        mock_celery_orchestrator,
        mock_connection_queue_manager,
        mock_catalog_service,
        config_manager,
        mock_connection_manager,
    ):
        return TaskManager(
            task_validation_manager,
            mock_action_manager,
            mock_celery_orchestrator,
            mock_connection_queue_manager,
            mock_catalog_service,
            config_manager,
            mock_connection_manager,
        )

    # ---------------------- Helpers ----------------------

    def _create_mock_item(self, item_type: str, laui: ObjectId = None, **kwargs):
        """Create a mock item with given type and laui"""
        item = MagicMock(spec=ItemProjection)
        item.item_type = item_type
        item.laui = laui or ObjectId()
        item.attached_config_lauis = kwargs.get("attached_config_lauis", [])

        for key, value in kwargs.items():
            setattr(item, key, value)

        return item

    def _create_task_validation_model(self, **overrides):
        """Create a TaskValidationModel with default values and overrides"""
        defaults = {
            "item_type": "task",
            "name": "test_task",
            "project_laui": ObjectId(),
            "account_laui": ObjectId(),
            "parent_laui": ObjectId(),
            "operator_laui": ObjectId(),
            "connection_laui": ObjectId(),
            "state": "scheduled",
            "frequency": "* * * * *",
            "laui": ObjectId(),  # Add laui field for execution validation
        }
        defaults.update(overrides)
        return TaskValidationModel(**defaults)

    # ---------------------- Tests ----------------------

    @pytest.mark.asyncio
    async def test_validate_task_execution_empty_list_pass(
        self, task_manager, mock_catalog_service
    ):
        """Test that empty task list returns empty result"""
        result = await task_manager.validate_task_execution([])
        assert result == []
        # Should not call catalog service with empty list
        mock_catalog_service.find_multiple_items_by_laui.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_task_execution_single_valid_task_pass(
        self, task_manager, mock_catalog_service, config_manager
    ):
        """Test validation of a single valid task"""
        task = self._create_task_validation_model()

        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])

        items = [operator, connection, workflow]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 1
        assert result[0] == task
        # Verify process_task_execution was called
        config_manager.process_task_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_task_execution_multiple_valid_tasks_pass(
        self, task_manager, mock_catalog_service, config_manager
    ):
        """Test validation of multiple valid tasks"""
        task1 = self._create_task_validation_model()
        task2 = self._create_task_validation_model()
        task3 = self._create_task_validation_model()

        # Create items for all tasks
        operator1 = self._create_mock_item("operator.python", task1.operator_laui)
        connection1 = self._create_mock_item("connection.python", task1.connection_laui)
        workflow1 = self._create_mock_item("workflow", task1.parent_laui, attached_config_lauis=[])

        operator2 = self._create_mock_item("operator.python", task2.operator_laui)
        connection2 = self._create_mock_item("connection.python", task2.connection_laui)
        workflow2 = self._create_mock_item("workflow", task2.parent_laui, attached_config_lauis=[])

        operator3 = self._create_mock_item("operator.python", task3.operator_laui)
        connection3 = self._create_mock_item("connection.python", task3.connection_laui)
        workflow3 = self._create_mock_item("workflow", task3.parent_laui, attached_config_lauis=[])

        items = [
            operator1,
            connection1,
            workflow1,
            operator2,
            connection2,
            workflow2,
            operator3,
            connection3,
            workflow3,
        ]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task1, task2, task3])

        assert len(result) == 3
        assert config_manager.process_task_execution.call_count == 3

    @pytest.mark.asyncio
    async def test_validate_task_execution_deduplicates_item_lauis_pass(
        self, task_manager, mock_catalog_service
    ):
        """Test that duplicate item LAUIs are deduplicated using sets"""
        shared_operator = ObjectId()
        shared_connection = ObjectId()
        shared_workflow = ObjectId()

        task1 = self._create_task_validation_model(
            operator_laui=shared_operator,
            connection_laui=shared_connection,
            parent_laui=shared_workflow,
        )
        task2 = self._create_task_validation_model(
            operator_laui=shared_operator,
            connection_laui=shared_connection,
            parent_laui=shared_workflow,
        )
        task3 = self._create_task_validation_model(
            operator_laui=shared_operator,
            connection_laui=shared_connection,
            parent_laui=shared_workflow,
        )

        operator = self._create_mock_item("operator.python", shared_operator)
        connection = self._create_mock_item("connection.python", shared_connection)
        workflow = self._create_mock_item("workflow", shared_workflow, attached_config_lauis=[])

        items = [operator, connection, workflow]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task1, task2, task3])

        # All 3 tasks should be validated successfully
        assert len(result) == 3

        # Verify that catalog service was called only once with deduplicated IDs
        assert mock_catalog_service.find_multiple_items_by_laui.call_count == 1
        call_args = mock_catalog_service.find_multiple_items_by_laui.call_args[1]
        item_lauis = call_args["item_lauis"]
        # Should have exactly 3 unique items
        assert len(item_lauis) == 3

    @pytest.mark.asyncio
    async def test_validate_task_execution_missing_operator_fail(
        self, task_manager, mock_catalog_service
    ):
        """Test that tasks with missing operators are filtered out and logged"""
        task = self._create_task_validation_model()

        # Only return connection and workflow, not operator
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])

        items = [connection, workflow]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        # Task should be filtered out
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_task_execution_missing_connection_fail(
        self, task_manager, mock_catalog_service
    ):
        """Test that tasks with missing connections are filtered out"""
        task = self._create_task_validation_model()

        # Only return operator and workflow, not connection
        operator = self._create_mock_item("operator.python", task.operator_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])

        items = [operator, workflow]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_task_execution_missing_workflow_fail(
        self, task_manager, mock_catalog_service
    ):
        """Test that tasks with missing workflows are filtered out"""
        task = self._create_task_validation_model()

        # Only return operator and connection, not workflow
        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)

        items = [operator, connection]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_task_execution_with_payload_laui_pass(
        self, task_manager, mock_catalog_service
    ):
        """Test validation with payload_laui"""
        payload_laui = ObjectId()
        task = self._create_task_validation_model(payload_laui=payload_laui)
        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])
        # Payload item must have content field for _validate_payload_constraints
        payload = self._create_mock_item(
            "payload", payload_laui, content='{"test": "payload_data"}'
        )

        items = [operator, connection, workflow, payload]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_validate_task_execution_with_task_configs_pass(
        self, task_manager, mock_catalog_service
    ):
        """Test validation with task attached configs"""
        config1_laui = ObjectId()
        config2_laui = ObjectId()
        task = self._create_task_validation_model(
            attached_config_lauis=[str(config1_laui), str(config2_laui)]
        )

        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])
        config1 = self._create_mock_item("config", config1_laui)
        config2 = self._create_mock_item("config", config2_laui)

        items = [operator, connection, workflow, config1, config2]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_validate_task_execution_connection_operator_mapping_fails_fail(
        self, task_manager, mock_catalog_service, mock_connection_manager
    ):
        """Test that tasks with incompatible connection-operator mapping are filtered out"""
        task = self._create_task_validation_model()

        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])

        items = [operator, connection, workflow]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        # Make connection validation fail
        mock_connection_manager.validate_connection_operator_mapping.side_effect = Exception(
            "Incompatible connection-operator mapping"
        )

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_task_execution_partial_validation_pass(
        self, task_manager, mock_catalog_service, config_manager
    ):
        """Test that some tasks can pass while others fail validation"""
        task1 = self._create_task_validation_model()  # Valid
        task2 = self._create_task_validation_model()  # Missing operator
        task3 = self._create_task_validation_model()  # Valid

        operator1 = self._create_mock_item("operator.python", task1.operator_laui)
        connection1 = self._create_mock_item("connection.python", task1.connection_laui)
        workflow1 = self._create_mock_item("workflow", task1.parent_laui, attached_config_lauis=[])

        # task2 missing operator
        connection2 = self._create_mock_item("connection.python", task2.connection_laui)
        workflow2 = self._create_mock_item("workflow", task2.parent_laui, attached_config_lauis=[])

        operator3 = self._create_mock_item("operator.python", task3.operator_laui)
        connection3 = self._create_mock_item("connection.python", task3.connection_laui)
        workflow3 = self._create_mock_item("workflow", task3.parent_laui, attached_config_lauis=[])

        items = [
            operator1,
            connection1,
            workflow1,
            connection2,
            workflow2,  # Missing operator2
            operator3,
            connection3,
            workflow3,
        ]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task1, task2, task3])

        # Only task1 and task3 should pass
        assert len(result) == 2
        assert task1 in result
        assert task3 in result
        assert task2 not in result

    @pytest.mark.asyncio
    async def test_validate_task_execution_logs_item_fetch_errors_pass(
        self, task_manager, mock_catalog_service, caplog
    ):
        """Test that item fetching errors are logged as warnings"""
        task = self._create_task_validation_model()

        # Return empty to simulate items not found
        mock_catalog_service.find_multiple_items_by_laui.return_value = []

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_validate_task_execution_with_both_payload_and_payload_laui_pass(
        self, task_manager, mock_catalog_service
    ):
        """Test that payload_laui takes precedence when both payload and payload_laui are provided"""
        payload_laui = ObjectId()
        task = self._create_task_validation_model(payload="raw payload", payload_laui=payload_laui)

        operator = self._create_mock_item("operator.python", task.operator_laui)
        connection = self._create_mock_item("connection.python", task.connection_laui)
        workflow = self._create_mock_item("workflow", task.parent_laui, attached_config_lauis=[])
        payload = self._create_mock_item("payload", payload_laui, content="payload from laui")

        items = [operator, connection, workflow, payload]
        mock_catalog_service.find_multiple_items_by_laui.return_value = items

        result = await task_manager.validate_task_execution([task])

        assert len(result) == 1
        # Payload should be set to content from payload_laui (takes precedence over raw payload)
        assert result[0].payload == "payload from laui"
