# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from pathlib import Path
from typing import Any

from src.common.exceptions import InvalidArgumentError, NotFoundError
from src.common.logger.logger import log_error


def load_json(item_type: str) -> dict[str, Any]:
    root_dir = Path.cwd().parent
    config_file_path = root_dir / f"config/schema/{item_type}.json"

    try:
        config_json = config_file_path.read_text(encoding="utf-8")
        config_dict = json.loads(config_json)
        return config_dict

    except FileNotFoundError as e:
        message = "File not found: schema configuration missing"
        detail = f"The requested item type schema definition '{item_type}.json' is absent. Target location: '{config_file_path}'."

        log_error(
            "api",
            "schema_loader",
            "load_json",
            f"FileNotFoundError — {detail}",
        )
        log_error(
            "api_traceback",
            "schema_loader",
            "load_json",
            f"FileNotFoundError — {detail}",
        )
        raise NotFoundError(message=message, detail=detail) from e

    except json.JSONDecodeError as e:
        message = "Invalid argument: malformed schema JSON syntax"
        detail = f"Failed to decode valid JSON contents inside schema file for item_type '{item_type}' at path '{config_file_path}'. Parser error: {str(e)}."

        log_error(
            "api",
            "schema_loader",
            "load_json",
            f"JSONDecodeError — {detail}",
        )
        log_error(
            "api_traceback",
            "schema_loader",
            "load_json",
            f"JSONDecodeError — {detail}",
        )
        raise InvalidArgumentError(message=message, detail=detail) from e
