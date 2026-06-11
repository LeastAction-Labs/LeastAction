# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from src.common.config import Config
from src.common.exceptions import UnprocessableEntityError
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.schema import TaskCreationValidationModel
from src.core.task.task_manager import TaskManager
from src.core.task.task_validation_manager import TaskValidationManager


class TestTaskManager:
    """Unit tests for TaskManager"""

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
        service.find_item = AsyncMock(return_value=None)
        service.find_multiple_items_by_laui = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_connection_manager(self):
        manager = MagicMock(spec=ConnectionManager)
        manager.validate_connection_operator_mapping = MagicMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_connection_queue_manager(self):
        service = AsyncMock(spec=ConnectionQueueManager)
        service.load_balance_tasks = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def config_manager(self):
        """Mock ConfigManager fixture"""
        manager = AsyncMock(spec=ConfigManager)
        # Mock the replace_placeholders method to return the input as-is
        manager.replace_placeholders = MagicMock(side_effect=lambda x, y: x)
        # Mock merge_configs to return the correct format
        manager.merge_configs = MagicMock(
            side_effect=lambda config, configs_data: {
                "merged_config": {},
                "merged_value_sources": {},
            }
        )
        return manager

    @pytest.fixture
    def mock_supported_item_types_manager(self):
        manager = MagicMock(spec=ItemTypesManager)
        manager.get_supported_item_types = MagicMock(return_value=["task"])
        return manager

    @pytest.fixture
    def task_validation_manager(
        self,
        mock_connection_manager,
        mock_supported_item_types_manager,
        config_manager,
        mock_catalog_service,
    ):
        return TaskValidationManager(
            mock_connection_manager,
            config_manager,
            mock_catalog_service,
            mock_supported_item_types_manager,
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

    @pytest.fixture
    def valid_task_data(self):
        return {
            "item_type": "task",
            "name": "test_task",
            "project_name": "test_project",
            "account_name": "test_account",
            "project_laui": ObjectId(),
            "account_laui": ObjectId(),
            "parent_laui": ObjectId(),
            "operator_laui": ObjectId(),
            "connection_laui": ObjectId(),
            "state": "scheduled",
            "frequency": "ADHOC",
        }

    # ---------------------- Helpers ----------------------

    def _create_mock_item(self, item_type: str, item_id: ObjectId = None, **kwargs):
        item = MagicMock(spec=ItemProjection)
        item.item_type = item_type
        item.id = item_id or ObjectId()
        item.laui = item.id  # Set laui to be the same as id
        item.model_dump.return_value = {
            "item_type": item_type,
            "id": str(item.id),
        }
        # Set any additional attributes from kwargs
        for key, value in kwargs.items():
            setattr(item, key, value)
        return item

    def _setup_valid_items_batch(self, mock_catalog_service, task_data):
        """Setup mock for batch fetch using find_multiple_items_by_laui"""
        operator = self._create_mock_item("operator.python", task_data["operator_laui"])
        operator.laui = task_data["operator_laui"]  # Set laui attribute
        workflow = self._create_mock_item("folder", task_data["parent_laui"])
        workflow.laui = task_data["parent_laui"]
        workflow.attached_config_lauis = []  # Add attached_config_lauis attribute
        connection = self._create_mock_item("connection.python", task_data["connection_laui"])
        connection.laui = task_data["connection_laui"]

        async def get_multiple_items_side_effect(
            item_lauis=None, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == task_data["operator_laui"]:
                    items.append(operator)
                elif item_laui == task_data["parent_laui"]:
                    items.append(workflow)
                elif item_laui == task_data["connection_laui"]:
                    items.append(connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui = AsyncMock(
            side_effect=get_multiple_items_side_effect
        )

        # Replace find_item completely with AsyncMock with custom return_value based on call
        async def async_find_item(item_id=None, *args, **kwargs):
            # Convert to string for comparison to handle ObjectId vs PydanticObjectId
            if str(item_id) == str(task_data["parent_laui"]):
                return workflow
            return None

        mock_catalog_service.find_item = AsyncMock(side_effect=async_find_item)

    # ---------------------- Tests ----------------------

    @pytest.mark.asyncio
    async def test_validate_task_success(self, task_manager, mock_catalog_service, valid_task_data):
        self._setup_valid_items_batch(mock_catalog_service, valid_task_data)
        task_model = TaskCreationValidationModel(**valid_task_data)
        result = await task_manager.validate_task_creation(task_model)
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_task_operator_not_found(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        # Return empty list (operator not found)
        mock_catalog_service.find_multiple_items_by_laui.return_value = []

        # Setup find_item to return None when called
        def find_item_side_effect(*args, **kwargs):
            # Return an awaitable that returns None
            async def async_return_none():
                return None

            return async_return_none()

        mock_catalog_service.find_item.side_effect = find_item_side_effect
        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert str(valid_task_data["operator_laui"]) in str(exc.value.detail)
        assert "not found" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_workflow_not_found(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        from src.common.exceptions import NotFoundError

        operator = self._create_mock_item("operator.python", valid_task_data["operator_laui"])
        connection = self._create_mock_item("connection.python", valid_task_data["connection_laui"])

        # Only return operator and connection, not workflow
        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == valid_task_data["operator_laui"]:
                    items.append(operator)
                elif item_laui == valid_task_data["connection_laui"]:
                    items.append(connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )

        # Make find_item raise NotFoundError for workflow
        def find_item_side_effect(*args, **kwargs):
            # Return an awaitable that raises NotFoundError
            async def async_raise():
                raise NotFoundError("item not found")

            return async_raise()

        mock_catalog_service.find_item.side_effect = find_item_side_effect

        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert str(valid_task_data["parent_laui"]) in str(exc.value.detail)
        assert "not found" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_connection_not_found(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        operator = self._create_mock_item("operator.python", valid_task_data["operator_laui"])
        workflow = self._create_mock_item("folder", valid_task_data["parent_laui"])
        workflow.attached_config_lauis = []  # Add attached_config_lauis attribute

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == valid_task_data["operator_laui"]:
                    items.append(operator)
                elif item_laui == valid_task_data["parent_laui"]:
                    items.append(workflow)
            return items

        # Setup find_item to return the workflow
        def find_item_side_effect(*args, **kwargs):
            item_id = kwargs.get("item_id")
            if item_id == valid_task_data["parent_laui"]:
                # Return an awaitable that returns the workflow
                async def async_return():
                    return workflow

                return async_return()

            # Return an awaitable that returns None
            async def async_return_none():
                return None

            return async_return_none()

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        mock_catalog_service.find_item.side_effect = find_item_side_effect
        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert str(valid_task_data["connection_laui"]) in str(exc.value.detail)
        assert "not found" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_invalid_cron_expression(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["frequency"] = "0 0 * * * *"  # invalid (6 parts)
        self._setup_valid_items_batch(mock_catalog_service, data)
        task_model = TaskCreationValidationModel(**data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "cron" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_scheduled_missing_dates(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["frequency"] = "0 2 * * *"
        self._setup_valid_items_batch(mock_catalog_service, data)
        task_model = TaskCreationValidationModel(**data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "start_date is required" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_end_date_before_start_date(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["frequency"] = "0 2 * * *"
        data["start_date"] = datetime(2025, 12, 31, tzinfo=UTC)
        data["end_date"] = datetime(2025, 1, 1, tzinfo=UTC)
        self._setup_valid_items_batch(mock_catalog_service, data)
        task_model = TaskCreationValidationModel(**data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert (
            "end_date must be greater than or equal to start_date" in str(exc.value.detail).lower()
        )

    @pytest.mark.asyncio
    async def test_validate_task_with_payload_string(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["payload"] = '{"key": "value"}'
        self._setup_valid_items_batch(mock_catalog_service, data)
        task_model = TaskCreationValidationModel(**data)

        result = await task_manager.validate_task_creation(task_model)
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_task_with_payload_laui(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["payload_laui"] = ObjectId()

        operator = self._create_mock_item("operator.python", data["operator_laui"])
        workflow = self._create_mock_item("folder", data["parent_laui"])
        workflow.attached_config_lauis = []
        connection = self._create_mock_item("connection.python", data["connection_laui"])
        payload = self._create_mock_item("payload", data["payload_laui"])
        payload.content = '{"key": "value"}'  # Add content attribute

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == data["operator_laui"]:
                    items.append(operator)
                elif item_laui == data["parent_laui"]:
                    items.append(workflow)
                elif item_laui == data["connection_laui"]:
                    items.append(connection)
                elif item_laui == data["payload_laui"]:
                    items.append(payload)
            return items

        # Setup find_item to return workflow
        async def async_find_item(item_id=None, *args, **kwargs):
            if str(item_id) == str(data["parent_laui"]):
                return workflow
            return None

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        mock_catalog_service.find_item = AsyncMock(side_effect=async_find_item)
        task_model = TaskCreationValidationModel(**data)

        result = await task_manager.validate_task_creation(task_model)
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_task_invalid_payload_laui(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        data = valid_task_data.copy()
        data["payload_laui"] = ObjectId()

        operator = self._create_mock_item("operator.python", data["operator_laui"])
        workflow = self._create_mock_item("folder", data["parent_laui"])
        connection = self._create_mock_item("connection.python", data["connection_laui"])

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == data["operator_laui"]:
                    items.append(operator)
                elif item_laui == data["parent_laui"]:
                    items.append(workflow)
                elif item_laui == data["connection_laui"]:
                    items.append(connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        task_model = TaskCreationValidationModel(**data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert str(data["payload_laui"]) in str(exc.value.detail)
        assert "not found" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_wrong_operator_type(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        wrong_operator = self._create_mock_item("config", valid_task_data["operator_laui"])
        workflow = self._create_mock_item("folder", valid_task_data["parent_laui"])
        connection = self._create_mock_item("connection.python", valid_task_data["connection_laui"])

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == valid_task_data["operator_laui"]:
                    items.append(wrong_operator)
                elif item_laui == valid_task_data["parent_laui"]:
                    items.append(workflow)
                elif item_laui == valid_task_data["connection_laui"]:
                    items.append(connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "not of type operator" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_wrong_workflow_type(
        self,
        task_manager,
        mock_catalog_service,
        mock_supported_item_types_manager,
        valid_task_data,
    ):
        operator = self._create_mock_item("operator.python", valid_task_data["operator_laui"])
        wrong_workflow = self._create_mock_item("operator", valid_task_data["parent_laui"])
        connection = self._create_mock_item("connection.python", valid_task_data["connection_laui"])

        # Mock supported types to not include "task"
        mock_supported_item_types_manager.get_supported_item_types.return_value = ["config"]

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == valid_task_data["operator_laui"]:
                    items.append(operator)
                elif item_laui == valid_task_data["parent_laui"]:
                    items.append(wrong_workflow)
                elif item_laui == valid_task_data["connection_laui"]:
                    items.append(connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "invalid item_type task for workflow" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_wrong_connection_type(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        operator = self._create_mock_item("operator.python", valid_task_data["operator_laui"])
        workflow = self._create_mock_item("folder", valid_task_data["parent_laui"])
        wrong_connection = self._create_mock_item("payload", valid_task_data["connection_laui"])

        async def get_multiple_items_side_effect(
            item_lauis, projections=None, include_deleted=False
        ):
            items = []
            for item_laui in item_lauis:
                if item_laui == valid_task_data["operator_laui"]:
                    items.append(operator)
                elif item_laui == valid_task_data["parent_laui"]:
                    items.append(workflow)
                elif item_laui == valid_task_data["connection_laui"]:
                    items.append(wrong_connection)
            return items

        mock_catalog_service.find_multiple_items_by_laui.side_effect = (
            get_multiple_items_side_effect
        )
        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "not of type connection" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_connection_operator_mapping_fails(
        self,
        task_manager,
        mock_catalog_service,
        mock_connection_manager,
        valid_task_data,
    ):
        self._setup_valid_items_batch(mock_catalog_service, valid_task_data)

        # Simulate connection manager validation failure by raising exception
        mock_connection_manager.validate_connection_operator_mapping.side_effect = Exception(
            "connection type 'python' is not compatible with operator type 'spark'"
        )

        task_model = TaskCreationValidationModel(**valid_task_data)

        with pytest.raises(UnprocessableEntityError) as exc:
            await task_manager.validate_task_creation(task_model)
        assert "not compatible" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_task_valid_cron_expressions(
        self, task_manager, mock_catalog_service, valid_task_data
    ):
        """Test various valid cron expressions"""
        valid_crons = [
            "0 0 * * *",  # Daily at midnight
            "*/5 * * * *",  # Every 5 minutes
            "0 9-17 * * 1-5",  # Weekdays 9am-5pm
            "30 2 * * 0",  # Sundays at 2:30am
        ]

        for cron in valid_crons:
            data = valid_task_data.copy()
            data["frequency"] = cron
            data["start_date"] = datetime(2025, 1, 1, tzinfo=UTC)
            data["end_date"] = datetime(2025, 12, 31, tzinfo=UTC)
            self._setup_valid_items_batch(mock_catalog_service, data)

            task_model = TaskCreationValidationModel(**data)
            result = await task_manager.validate_task_creation(task_model)
            assert result is not None

    @pytest.mark.asyncio
    async def test_validate_task_with_config_field(
        self, task_manager, mock_catalog_service, valid_task_data, config_manager
    ):
        """Test that task config field is passed to config manager"""
        data = valid_task_data.copy()
        data["config"] = {
            "parameters": {"env": "production", "timeout": 300},
            "defaults": {"task": {"retry_count": 5}},
        }
        self._setup_valid_items_batch(mock_catalog_service, data)
        task_model = TaskCreationValidationModel(**data)

        result = await task_manager.validate_task_creation(task_model)
        assert result is not None

        # Verify that merge_configs was called with the task config
        config_manager.merge_configs.assert_called()
        call_args = config_manager.merge_configs.call_args
        # First argument should be the task config
        assert call_args[0][0] == data["config"]
