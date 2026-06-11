# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

from src.common.exceptions import LAException
from src.common.logger.logger import log_warning
from src.common.models import AccessPatch
from src.common.types import LAUI, AccessPatchType
from src.core.catalog.config.constants_mappers import types_mapper
from src.core.catalog.config.schema.model_creator import create_item_model
from src.core.catalog.config.schema.schema_model import SchemaModel


def _load_task_schema() -> dict[str, Any]:
    """Load task schema from JSON file."""
    try:
        root_dir = Path.cwd().parent
        config_file_path = root_dir / "config/schema/task.json"

        if not config_file_path.exists():
            raise LAException(f"Task schema file not found at: {config_file_path}")

        with open(config_file_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise LAException(f"Invalid JSON in task schema file: {e}")
    except Exception as e:
        raise LAException(f"Failed to load task schema: {e}")


def _create_task_state_enum(schema_dict: dict[str, Any]) -> Enum:
    """Create TaskState enum dynamically from schema."""
    state_column = next(
        (col for col in schema_dict.get("columns", []) if col.get("name") == "state"), None
    )

    if not state_column:
        raise LAException("Task schema missing 'state' column definition")

    enum_values = state_column.get("enum_values")
    if not enum_values:
        raise LAException("Task schema 'state' column missing 'enum_values'")

    # Convert "queued_for_connection" -> QUEUED_FOR_CONNECTION
    state_enum_values = {value.upper().replace("-", "_"): value for value in enum_values}

    TaskState = Enum("TaskState", state_enum_values, type=str)
    return TaskState


def _create_task_state_map(task_state_enum: Enum) -> dict[str, Enum]:
    task_state_map = {}
    # Add direct mappings for all enum values (state -> itself)
    for state in task_state_enum:
        task_state_map[state.value] = state

    return task_state_map


def _create_task_update_model(
    schema_dict: dict[str, Any], task_state_enum: Enum
) -> type[BaseModel]:
    system_update_fields = schema_dict.get("system_update_fields", [])
    if not system_update_fields:
        raise LAException("Task schema missing 'system_update_fields' definition")
    columns_map = {col.get("name"): col for col in schema_dict.get("columns", [])}
    update_fields = {}
    for field_name in system_update_fields:
        column = columns_map.get(field_name)
        if not column:
            raise LAException(
                f"Field '{field_name}' in system_update_fields not found in columns definition"
            )

        # Handle enum types (specifically for state and user_set_state)
        if column.get("datatype") == "enum":
            enum_values = column.get("enum_values", [])
            if field_name == "state":
                # Use the TaskState enum we already created
                data_field_type = task_state_enum
            else:
                # For other enums, use Literal
                data_field_type = Literal[tuple(enum_values)]
        else:
            # Handle regular types
            data_field_type = types_mapper.get(column.get("datatype"))
            if not data_field_type:
                raise LAException(
                    f"Unknown datatype '{column.get('datatype')}' for field '{field_name}'"
                )

        # All update fields are optional
        update_fields[field_name] = (Optional[data_field_type], None)

    @field_validator("duration", mode="before")
    @classmethod
    def convert_duration_to_int(cls, v):
        if v is None:
            return v
        return int(v)

    class SafeSetAttrBase(BaseModel):
        """BaseModel that logs a warning and skips unknown fields on setattr instead of raising."""

        def __setattr__(self, name: str, value: Any) -> None:
            if name not in self.model_fields:
                log_warning(
                    "task",
                    "TaskUpdateData",
                    "__setattr__",
                    f"Ignoring unknown field '{name}' "
                    f"(not in system_update_fields). Value: {value}",
                )
                return
            super().__setattr__(name, value)

    # Create the model dynamically
    TaskUpdateDataModel = create_model(
        "TaskUpdateData",
        __base__=SafeSetAttrBase,
        __validators__={"convert_duration_to_int": convert_duration_to_int},
        **update_fields,
    )

    return TaskUpdateDataModel


# Load task schema and create models dynamically
_task_schema_dict = _load_task_schema()

# Create TaskState enum from schema
TaskState = _create_task_state_enum(_task_schema_dict)

# Create BaseTaskModel from schema
_task_schema_model = SchemaModel(**_task_schema_dict)
BaseTaskModel = create_item_model(_task_schema_model)

# Create task_state_map from enum values using convention-based mappings
task_state_map = _create_task_state_map(TaskState)

# Create TaskUpdateData model from system_update_fields
TaskUpdateData = _create_task_update_model(_task_schema_dict, TaskState)


class TaskCreationValidationModel(BaseTaskModel):
    model_config = ConfigDict(extra="allow")
    access_patch: AccessPatchType = Field(default=AccessPatch())
    pass


class TaskValidationModel(BaseTaskModel):
    """
    Model used for validation context in TaskManager.
    Adding other fields needed for validation context, which TaskManager might use.
    """

    item_type: str = "task"
    laui: LAUI
    connection: dict[str, Any] | None = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class Task(TaskValidationModel):
    pass
