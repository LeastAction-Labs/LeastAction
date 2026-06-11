# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.common.config import Config
from src.common.exceptions import UnprocessableEntityError
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.catalog.item.schema import ItemProjection
from src.core.task.connection.connection_manager import ConnectionManager

MOCK_YAML_CONFIG = """
enforce_connection_operator_mapping: true
connection_operator_mapping:
  connection.AWSIAMRole:
    - operator.AWSIAMRole
  connection.python:
    - operator.python
  connection.databricks:
    - operator.python
    - operator.databricks
"""


class TestconnectionManager:
    """Unit tests for connectionManager"""

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
    def connection_manager(self):
        return ConnectionManager()

    @pytest.fixture
    def mock_connection_iam(self):
        connection = MagicMock(spec=ItemProjection)
        connection.item_type = "connection.AWSIAMRole"
        return connection

    @pytest.fixture
    def mock_connection_python(self):
        connection = MagicMock(spec=ItemProjection)
        connection.item_type = "connection.python"
        return connection

    @pytest.fixture
    def mock_connection_databricks(self):
        connection = MagicMock(spec=ItemProjection)
        connection.item_type = "connection.databricks"
        return connection

    @pytest.fixture
    def mock_operator_iam(self):
        operator = MagicMock(spec=ItemProjection)
        operator.item_type = "operator.AWSIAMRole"
        return operator

    @pytest.fixture
    def mock_operator_python(self):
        operator = MagicMock(spec=ItemProjection)
        operator.item_type = "operator.python"
        return operator

    # @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    # def test_load_connection_operator_mapping(self, mock_file, connection_manager):
    #     # _load_connection_operator_mapping now returns (enforce: bool, mappings: dict)
    #     mapping = connection_manager._load_connection_operator_mapping()
    #     assert isinstance(mapping, dict)
    #     assert "connection.AWSIAMRole" in mapping
    #     assert "operator.AWSIAMRole" in mapping["connection.AWSIAMRole"]

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_valid_iam_connection_iam_operator(
        self,
        mock_file,
        connection_manager,
        mock_connection_iam,
        mock_operator_iam,
    ):
        result = connection_manager.validate_connection_operator_mapping(
            mock_connection_iam, mock_operator_iam
        )
        assert result is True

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_valid_python_connection_python_operator(
        self,
        mock_file,
        connection_manager,
        mock_connection_python,
        mock_operator_python,
    ):
        result = connection_manager.validate_connection_operator_mapping(
            mock_connection_python, mock_operator_python
        )
        assert result is True

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_invalid_iam_connection_python_operator(
        self,
        mock_file,
        connection_manager,
        mock_connection_iam,
        mock_operator_python,
    ):
        with pytest.raises(UnprocessableEntityError) as exc:
            connection_manager.validate_connection_operator_mapping(
                mock_connection_iam, mock_operator_python
            )
        assert "does not support" in str(exc.value)
        assert "AWSIAMRole" in str(exc.value)
        assert "python" in str(exc.value)

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_invalid_python_connection_iam_operator(
        self,
        mock_file,
        connection_manager,
        mock_connection_python,
        mock_operator_iam,
    ):
        with pytest.raises(UnprocessableEntityError) as exc:
            connection_manager.validate_connection_operator_mapping(
                mock_connection_python, mock_operator_iam
            )
        assert "does not support" in str(exc.value)

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_unknown_connection_type(self, mock_file, connection_manager, mock_operator_python):
        unknown_connection = MagicMock(spec=ItemProjection)
        unknown_connection.item_type = "connection.unknown_type"
        with pytest.raises(UnprocessableEntityError) as exc:
            connection_manager.validate_connection_operator_mapping(
                unknown_connection, mock_operator_python
            )
        assert "No mapping defined" in str(exc.value) or "does not support" in str(exc.value)

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_databricks_connection_python_operator(
        self,
        mock_file,
        connection_manager,
        mock_connection_databricks,
        mock_operator_python,
    ):
        result = connection_manager.validate_connection_operator_mapping(
            mock_connection_databricks, mock_operator_python
        )
        assert result is True

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_YAML_CONFIG)
    def test_error_message_format(
        self,
        mock_file,
        connection_manager,
        mock_connection_iam,
        mock_operator_python,
    ):
        with pytest.raises(UnprocessableEntityError) as exc:
            connection_manager.validate_connection_operator_mapping(
                mock_connection_iam, mock_operator_python
            )
        error_msg = str(exc.value)
        assert "Invalid connection-operator mapping" in error_msg
        assert "AWSIAMRole" in error_msg
        assert "python" in error_msg
