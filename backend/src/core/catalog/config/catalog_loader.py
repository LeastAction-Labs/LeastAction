# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from pathlib import Path

from pydantic import ValidationError

from src.common.exceptions import InvalidArgumentError, NotFoundError, UnprocessableEntityError
from src.common.logger.logger import log_error
from src.core.catalog.config.catalog_schema import CatalogConfig


def load_catalog_config() -> CatalogConfig:
    root_dir = Path.cwd().parent
    config_file_path = root_dir / "config/catalog.json"

    try:
        config_json = config_file_path.read_text(encoding="utf-8")
        config_dict = json.loads(config_json)
        config = CatalogConfig(**config_dict)
        return config

    except FileNotFoundError:
        message = "Catalog file missing"
        detail = f"The catalog configuration file was not found. Please make sure it exists at: '{config_file_path}'."

        log_error("api", "catalog_loader", "load_json", detail)
        log_error("api_traceback", "catalog_loader", "load_json", detail)
        raise NotFoundError(message=message, detail=detail)

    except json.JSONDecodeError as e:
        message = "Invalid JSON format"
        detail = f"Could not parse the file at '{config_file_path}' because the JSON is broken. Syntax error: {str(e)}."

        log_error("api", "catalog_loader", "load_json", detail)
        log_error("api_traceback", "catalog_loader", "load_json", detail)
        raise InvalidArgumentError(message=message, detail=detail)

    except TypeError as e:
        sample_catalog_config = {
            "item_type_link_mapping": {
                "item_type": {"can_contain": ["item_type", "..."]},
            },
            "hierarchy_items_limit": "int",
        }
        message = "Invalid configuration format"
        detail = (
            f"The data inside '{config_file_path}' must be a dictionary that matches this format: {sample_catalog_config}. "
            f"Internal error: {str(e)}."
        )

        log_error("api", "catalog_loader", "load_json", "catalog config not a dict")
        log_error("api_traceback", "catalog_loader", "load_json", "catalog config not a dict")
        raise UnprocessableEntityError(message=message, detail=detail)

    except ValidationError as e:
        raise UnprocessableEntityError(message="Config validation failed", detail=e.errors())
