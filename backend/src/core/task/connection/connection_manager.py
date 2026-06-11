# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pathlib import Path

import yaml

from src.common.exceptions import UnprocessableEntityError
from src.common.logger.logger import log_error
from src.common.utils import get_config_path
from src.core.catalog.item.schema import ItemProjection


class ConnectionManager:
    def __init__(self, config_path: str = None):
        if config_path:
            self._config_file_path = Path(config_path)
        else:
            self._config_file_path = get_config_path()

    def validate_connection_operator_mapping(
        self, connection: ItemProjection, operator: ItemProjection
    ) -> bool:
        connection_type = connection.item_type
        operator_type = operator.item_type
        #    TODO load connection and operator mapping only when the config file is changed
        enforce_connection_operator_mapping, valid_mappings = (
            self._load_connection_operator_mapping()
        )
        if not enforce_connection_operator_mapping:
            return True
        try:
            # Extract subtypes - handle both "connection.python" and potentially just "python"
            if "." in connection_type:
                connection_sub_type = connection_type.split("connection.")[1]
            else:
                connection_sub_type = connection_type

            if "." in operator_type:
                operator_sub_type = operator_type.split("operator.")[1]
            else:
                operator_sub_type = operator_type
        except Exception as e:
            log_error(
                "API",
                "connectionManager",
                "validate_connection_operator_mapping",
                f"Invalid subtype format: {e}",
            )
            raise UnprocessableEntityError("Invalid connection or operator subtype format")

        # Look for the mapping with full type name first, then just subtype
        allowed_operator_types = valid_mappings.get(f"connection.{connection_sub_type}")

        if not allowed_operator_types:
            # Try without the prefix
            allowed_operator_types = valid_mappings.get(connection_sub_type)

        if not allowed_operator_types:
            raise UnprocessableEntityError(
                f"No mapping defined for connection type '{connection_sub_type}'. "
                f"Available mappings: {list(valid_mappings.keys())}"
            )

        # Check if the full operator type is in allowed types
        if operator_type not in allowed_operator_types:
            raise UnprocessableEntityError(
                f"Invalid connection-operator mapping: {connection_sub_type} does not support {operator_sub_type}. "
                f"Allowed: {', '.join(allowed_operator_types)}"
            )

        return True

    def _load_connection_operator_mapping(self) -> tuple[bool, dict[str, list[str]]]:
        try:
            with open(self._config_file_path, encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if not config or "connection_operator_mapping" not in config:
                raise UnprocessableEntityError(
                    f"'connection_operator_mapping' key missing in {self._config_file_path}"
                )

            mappings = config["connection_operator_mapping"]
            enforce_mapping = config.get("enforce_connection_operator_mapping", False)  # ✅ Fixed

            if not isinstance(mappings, dict):
                raise UnprocessableEntityError(
                    "Invalid format: connection_operator_mapping must be a dict"
                )

            return enforce_mapping, mappings

        except FileNotFoundError as e:
            raise UnprocessableEntityError(
                f"system.yml file not found at {self._config_file_path}: {e}"
            )
        except yaml.YAMLError as e:
            raise UnprocessableEntityError(f"Error parsing YAML file {self._config_file_path}: {e}")
        except Exception as e:
            raise UnprocessableEntityError(
                f"Unexpected error while loading connection-operator mapping: {e}"
            )
