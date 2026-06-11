# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest
from fastapi.testclient import TestClient

from tests.integration.schema import TestRequest
from tests.integration.utils import execute_request

pytestmark = pytest.mark.anyio


async def test_validate_codeblock_syntax_error(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/validate",
            method="post",
            json={
                "codeblock": {"main.py": "def foo(\n"},
                "item_type": "operator",
            },
        ),
    )
    assert response.status_code == 200
    parsed = response.json()
    assert parsed["valid"] is False
    error_codes = [e["code"] for e in parsed["errors"]]
    assert "SYNTAX_ERROR" in error_codes


async def test_validate_codeblock_missing_main_py(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/validate",
            method="post",
            json={
                "codeblock": {"helper.py": "x = 1"},
                "item_type": "operator",
            },
        ),
    )
    assert response.status_code == 200
    parsed = response.json()
    assert parsed["valid"] is False
    assert len(parsed["errors"]) == 1
    assert parsed["errors"][0]["code"] == "NO_MAIN_FILE"
    assert parsed["errors"][0]["message"] == "Main file must be named 'main.py'"


async def test_validate_codeblock_denied_import(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/validate",
            method="post",
            json={
                "codeblock": {
                    "main.py": "import ctypes\ndef initialize(self):\n    pass\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "item_type": "operator",
            },
        ),
    )
    assert response.status_code == 200
    parsed = response.json()
    assert parsed["valid"] is False
    error_codes = [e["code"] for e in parsed["errors"]]
    assert "DENIED_IMPORT" in error_codes
    denied_errors = [e for e in parsed["errors"] if e["code"] == "DENIED_IMPORT"]
    assert any("ctypes" in e["message"] for e in denied_errors)


async def test_validate_codeblock_multiple_violations(client: TestClient):
    main_code = (
        "import threading\n"
        "import logging\n"
        "import helper\n"
        "async def initialize(self):\n"
        "    obj = self.__class__\n"
        "    logging.basicConfig()\n"
        "    return {}\n"
        "def run(self, ctx):\n"
        "    return 'not_a_dict'\n"
        "def check_completion(self, ctx, state):\n"
        "    return {'status': 'done'}\n"
        "def finish(self, ctx, state, result):\n"
        "    return None\n"
    )
    helper_code = "import main\nx = 1\n"
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/validate",
            method="post",
            json={
                "codeblock": {"main.py": main_code, "helper.py": helper_code},
                "item_type": "operator",
            },
        ),
    )
    assert response.status_code == 200
    parsed = response.json()
    assert parsed["valid"] is False
    error_codes = {e["code"] for e in parsed["errors"]}
    assert "DENIED_IMPORT" in error_codes
    assert "INVALID_LOGGER_IMPORT" in error_codes
    assert "ASYNC_FUNC" in error_codes
    assert "DUNDER_ACCESS" in error_codes
    assert "ROOT_LOGGER_CONFIG" in error_codes
    assert "INVALID_RETURN" in error_codes
    assert "CYCLIC_IMPORT" in error_codes
    assert len(parsed["errors"]) >= 7
