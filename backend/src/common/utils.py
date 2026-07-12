# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import secrets
import string


def generate_password(length=12):
    charset = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(charset) for _ in range(length))


def compare_common_keys(dict1: dict[str, any], dict2: dict[str, any], common_keys: list[str]):
    filtered_dict1 = {key: value for key, value in dict1.items() if key in common_keys}
    filtered_dict2 = {key: value for key, value in dict2.items() if key in common_keys}
    return filtered_dict1 == filtered_dict2


import base64
import json

from fastapi.encoders import jsonable_encoder


def encode_data(data: dict[str, any]) -> str:
    json_string = json.dumps(jsonable_encoder(data))
    bytes_to_encode = json_string.encode("utf-8")
    base64_bytes = base64.b64encode(bytes_to_encode)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string


def decode_data(code: str) -> dict[str, any]:
    base64_bytes = code.encode("utf-8")
    decoded_bytes = base64.b64decode(base64_bytes)
    json_string = decoded_bytes.decode("utf-8")
    data = json.loads(json_string)
    return data


from typing import Literal
from urllib.parse import urlencode, urlsplit, urlunsplit

import yaml
from fastapi import Response


def set_cookie(response: Response, key: str, value: str):
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        max_age=24 * 3600,
        path="/",
    )


def delete_cookie(response: Response, key: str):
    response.delete_cookie(key=key, path="/", httponly=True)


def check_differing_keys(new_dict: dict[str, any], old_dict: dict[str, any]) -> set[str]:
    differing_keys = set()
    for key in old_dict:
        if new_dict.get(key) and new_dict[key] != old_dict[key]:
            differing_keys.add(key)
    return differing_keys


def load_system_config():
    import os
    from pathlib import Path

    # Get the project root directory (assuming utils.py is in backend/src/common/)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    config_path = project_root / "config" / "system.yml"

    if not config_path.exists():
        raise FileNotFoundError(f"System configuration file not found at {config_path}")

    with open(config_path) as config_file:
        config = yaml.safe_load(config_file)

    app_public_url = os.environ.get("APP_PUBLIC_URL")
    if app_public_url:
        config["urls"]["core_backend_url"] = app_public_url
        config["urls"]["core_frontend_url"] = app_public_url

    marketplace_url = os.environ.get("MARKETPLACE_URL")
    if marketplace_url:
        config["urls"]["marketplace_url"] = marketplace_url

    # AWS=true implies email_otp; otherwise respect EMAIL_OTP env var (default false)
    aws = os.environ.get("AWS", "false").lower() == "true"
    if aws:
        config["totp_enabled"] = True
    else:
        email_otp_env = os.environ.get("EMAIL_OTP", "false").lower()
        config["totp_enabled"] = email_otp_env == "true"

    return config


def update_system_config(request_data: dict):
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    config_path = project_root / "config" / "system.yml"

    if not config_path.exists():
        raise FileNotFoundError(f"System configuration file not found at {config_path}")

    with open(config_path) as f:
        # Safe_load prevents arbitrary code execution from malicious YAML files
        config = yaml.safe_load(f) or {}

    # 2. Update existing attributes or add new ones
    for field, value in request_data.items():
        if value is not None:
            config[field] = value  # Dictionaries handle update/add natively

    # 3. Write the updated data back to the file
    with open(config_path, "w") as f:
        # sort_keys=False preserves the order you inserted them
        yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)


def assign_value_to_keys(source: dict[str, any], replace_with: any) -> dict[str, any]:
    result = {}
    for key, value in source.items():
        if isinstance(value, dict):
            result[key] = assign_value_to_keys(source=value, replace_with=replace_with)
        else:
            result[key] = replace_with
    return result


from pathlib import Path


def get_config_path(file_name: str = "system.yml") -> Path:

    root_dir = None
    current_path = Path(__file__).resolve()
    for file_path in [current_path] + list(current_path.parents):
        if file_path.name == "backend":
            root_dir = file_path.parent
            break

    if not root_dir:
        raise RuntimeError("Could not find the 'LeastAction' root directory in the file path.")

    config_path = root_dir / "config" / file_name

    return config_path


from typing import Any

from src.common.exceptions import InvalidArgumentError, NotFoundError
from src.common.logger.logger import log_error


def load_json(file_path: Path) -> Any:
    try:
        file_content = file_path.read_text(encoding="utf-8")
        return json.loads(file_content)
    except FileNotFoundError as e:
        error_msg = f"catalog.json file absent, desired file location: {file_path}"
        log_error("api", "load_json", "load_json", error_msg)
        log_error("api_traceback", "catalog_loader", "load_json", error_msg)
        raise NotFoundError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Error decoding JSON for file at {file_path} "
        log_error("api", "catalog_loader", "load_json", error_msg)
        log_error("api_traceback", "catalog_loader", "load_json", error_msg)
        raise InvalidArgumentError(error_msg) from e


from typing import Any

PYDANTIC_ERROR_KEYS = {"type", "loc", "msg"}


def _is_pydantic_error(obj: Any) -> bool:
    return isinstance(obj, dict) and PYDANTIC_ERROR_KEYS.issubset(obj.keys())


def _humanize_pydantic_error(error: dict) -> dict:
    result = {
        "field": ".".join(map(str, error.get("loc", []))),
        "error": error.get("msg"),
        "error_type": error.get("type"),
    }

    # Preserve all non-standard/custom fields
    for key, value in error.items():
        if key not in {"type", "loc", "msg", "input", "url"}:
            result[key] = value

    return result


def transform_validation_errors(data: Any) -> Any:
    """
    Recursively walk any object and transform pydantic errors
    while preserving custom fields and structure.
    """

    if _is_pydantic_error(data):
        return _humanize_pydantic_error(data)

    if isinstance(data, list):
        return [transform_validation_errors(item) for item in data]

    if isinstance(data, dict):
        return {key: transform_validation_errors(value) for key, value in data.items()}

    return data
