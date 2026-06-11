# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from src.common.config import Config
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.catalog.item.repo import ItemRepository
from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.item_revision.repo import ItemRevisionRepository
from src.core.catalog.link.repo import LinkRepository
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.ee.keto.access_reader import AccessReader


class TestCatalogServiceFindMultipleItemsByLaui:
    """Unit tests for CatalogService.find_multiple_items_by_laui"""

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
    def mock_item_repo(self):
        repo = AsyncMock(spec=ItemRepository)
        repo.get_multiple_items_by_laui = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_link_repo(self):
        return AsyncMock(spec=LinkRepository)

    @pytest.fixture
    def mock_item_revision_repo(self):
        return AsyncMock(spec=ItemRevisionRepository)

    @pytest.fixture
    def mock_access_reader(self):
        mock = AsyncMock(spec=AccessReader)

        async def mock_permissions(**kwargs):
            item_lauis = kwargs["item_lauis"]
            return [True] * len(item_lauis)

        mock.batch_check_permissions.side_effect = mock_permissions
        return mock

    @pytest.fixture
    def mock_item_types_manager(self):
        return AsyncMock(spec=ItemTypesManager)

    @pytest.fixture
    def catalog_service(
        self,
        mock_item_repo,
        mock_link_repo,
        mock_item_revision_repo,
        mock_access_reader,
        mock_item_types_manager,
    ):
        return CatalogService(
            item_repo=mock_item_repo,
            link_repo=mock_link_repo,
            access_reader=mock_access_reader,
            item_revision_repo=mock_item_revision_repo,
            item_types_manager=mock_item_types_manager,
        )

    def _create_mock_item(self, item_type: str, item_laui: ObjectId = None, **extra_fields):
        """Helper to create a mock ItemProjection"""
        item_data = {
            "laui": item_laui or ObjectId(),
            "item_type": item_type,
            **extra_fields,
        }
        return ItemProjection(**item_data)

    # ---------------------- Tests ----------------------

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_success(self, catalog_service, mock_item_repo):
        """Test successful retrieval of multiple items"""
        item_laui1 = ObjectId()
        item_laui2 = ObjectId()
        item_laui3 = ObjectId()

        item1 = self._create_mock_item("operator.python", item_laui1)
        item2 = self._create_mock_item("connection.python", item_laui2)
        item3 = self._create_mock_item("folder", item_laui3)

        mock_item_repo.get_multiple_items_by_laui.return_value = [
            item1,
            item2,
            item3,
        ]

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui1, item_laui2, item_laui3],
            projections={},
        )

        assert len(result) == 3
        assert result[0].laui == str(item_laui1)
        assert result[1].laui == str(item_laui2)
        assert result[2].laui == str(item_laui3)
        assert result[0].item_type == "operator.python"
        assert result[1].item_type == "connection.python"
        assert result[2].item_type == "folder"

        mock_item_repo.get_multiple_items_by_laui.assert_called_once_with(
            item_lauis=[item_laui1, item_laui2, item_laui3],
            projections={},
            include_deleted=False,
        )

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_with_projections(
        self, catalog_service, mock_item_repo
    ):
        """Test retrieval with specific field projections"""
        item_laui1 = ObjectId()
        item_laui2 = ObjectId()

        item1 = self._create_mock_item("task", item_laui1)
        item2 = self._create_mock_item("config", item_laui2)

        mock_item_repo.get_multiple_items_by_laui.return_value = [item1, item2]

        projections = {"name": 1, "item_type": 1}

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui1, item_laui2],
            projections=projections,
        )

        assert len(result) == 2

        mock_item_repo.get_multiple_items_by_laui.assert_called_once_with(
            item_lauis=[item_laui1, item_laui2],
            projections=projections,
            include_deleted=False,
        )

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_include_deleted(
        self, catalog_service, mock_item_repo
    ):
        """Test retrieval including soft-deleted items"""
        item_laui1 = ObjectId()
        item_laui2 = ObjectId()

        item1 = self._create_mock_item("task", item_laui1)
        item2 = self._create_mock_item(
            "operator",
            item_laui2,
            deleted_at="2025-01-01",
        )

        mock_item_repo.get_multiple_items_by_laui.return_value = [item1, item2]

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui1, item_laui2],
            projections={},
            include_deleted=True,
        )

        assert len(result) == 2

        mock_item_repo.get_multiple_items_by_laui.assert_called_once_with(
            item_lauis=[item_laui1, item_laui2],
            projections={},
            include_deleted=True,
        )

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_empty_list(self, catalog_service, mock_item_repo):
        """Test with empty item_lauis list"""
        mock_item_repo.get_multiple_items_by_laui.return_value = []

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[],
            projections={},
        )

        assert len(result) == 0

        mock_item_repo.get_multiple_items_by_laui.assert_called_once_with(
            item_lauis=[],
            projections={},
            include_deleted=False,
        )

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_single_item(self, catalog_service, mock_item_repo):
        """Test retrieval of a single item"""
        item_laui = ObjectId()

        item = self._create_mock_item("payload", item_laui)

        mock_item_repo.get_multiple_items_by_laui.return_value = [item]

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui],
            projections={},
        )

        assert len(result) == 1
        assert result[0].laui == str(item_laui)
        assert result[0].item_type == "payload"

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_partial_results(
        self, catalog_service, mock_item_repo
    ):
        """Test when some items exist and some don't"""
        item_laui1 = ObjectId()
        item_laui2 = ObjectId()
        item_laui3 = ObjectId()

        item1 = self._create_mock_item("operator.python", item_laui1)
        item2 = self._create_mock_item("connection.python", item_laui2)

        mock_item_repo.get_multiple_items_by_laui.return_value = [item1, item2]

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui1, item_laui2, item_laui3],
            projections={},
        )

        assert len(result) == 2
        assert result[0].laui == str(item_laui1)
        assert result[1].laui == str(item_laui2)

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_no_results(self, catalog_service, mock_item_repo):
        """Test when none of the requested items exist"""
        item_laui1 = ObjectId()
        item_laui2 = ObjectId()

        mock_item_repo.get_multiple_items_by_laui.return_value = []

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=[item_laui1, item_laui2],
            projections={},
        )

        assert len(result) == 0

        mock_item_repo.get_multiple_items_by_laui.assert_called_once_with(
            item_lauis=[item_laui1, item_laui2],
            projections={},
            include_deleted=False,
        )

    @pytest.mark.asyncio
    async def test_find_multiple_items_by_laui_various_item_types(
        self, catalog_service, mock_item_repo
    ):
        """Test retrieval of items with various item types"""
        item_lauis = [ObjectId() for _ in range(6)]

        items = [
            self._create_mock_item("operator.python", item_lauis[0]),
            self._create_mock_item("connection.spark", item_lauis[1]),
            self._create_mock_item("folder.workspace", item_lauis[2]),
            self._create_mock_item("task", item_lauis[3]),
            self._create_mock_item("config", item_lauis[4]),
            self._create_mock_item("payload", item_lauis[5]),
        ]

        mock_item_repo.get_multiple_items_by_laui.return_value = items

        result = await catalog_service.find_multiple_items_by_laui(
            item_lauis=item_lauis,
            projections={},
        )

        assert len(result) == 6
        assert result[0].item_type == "operator.python"
        assert result[1].item_type == "connection.spark"
        assert result[2].item_type == "folder.workspace"
        assert result[3].item_type == "task"
        assert result[4].item_type == "config"
        assert result[5].item_type == "payload"
