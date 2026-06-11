# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os

import httpx

from src.common.context_vars.user_context import get_current_token

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


async def mcp_api(method: str, path: str, headers: dict | None = None, **kwargs) -> dict:
    token = get_current_token()
    request_headers = {"Cookie": f"frontend_token={token}"}
    if headers:
        request_headers.update(headers)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method,
            f"{BACKEND_URL}/api/v1/{path}",
            headers=request_headers,
            **kwargs,
        )
    if not resp.is_success:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"error": detail}
    return resp.json()
