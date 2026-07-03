# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import traceback
from typing import Any, Optional

import httpx
from pydantic_mongo import PydanticObjectId

from src.common.logger.logger import log_error, log_info
from src.core.catalog.api_request import CreateItemResponse
from src.core.catalog.item.schema import Item
from src.core.task.schema import TaskUpdateData

_RETRYABLE_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.LocalProtocolError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteError,
)
_MAX_RETRIES = 3
_BACKOFF_DELAYS = (1, 2, 4, 7, 11)


class APIClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(90.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return await getattr(self._client, method)(url, **kwargs)

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_exc: Exception | None = None
        last_response: httpx.Response | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await getattr(self._client, method)(url, **kwargs)
                if response.status_code == 503 and attempt < _MAX_RETRIES - 1:
                    try:
                        is_write_conflict = response.json().get("detail") == "write_conflict"
                    except Exception:
                        is_write_conflict = False
                    if is_write_conflict:
                        wait = _BACKOFF_DELAYS[attempt]
                        log_info(
                            "api_client",
                            "APIClient",
                            "_request_with_retry",
                            f"{url} returned write_conflict — retry {attempt + 1}/{_MAX_RETRIES} in {wait}s",
                        )
                        last_response = response
                        await asyncio.sleep(wait)
                        continue
                return response
            except _RETRYABLE_ERRORS as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_DELAYS[attempt]
                    log_info(
                        "api_client",
                        "APIClient",
                        "_request_with_retry",
                        f"{url} failed ({type(exc).__name__}) — retry {attempt + 1}/{_MAX_RETRIES} in {wait}s",
                    )
                    await asyncio.sleep(wait)
        if last_exc:
            raise last_exc
        log_error(
            "api_client",
            "APIClient",
            "_request_with_retry",
            f"{url} write_conflict retries exhausted after {_MAX_RETRIES} attempts. Last response: {last_response.status_code} {last_response.text}",
        )
        return last_response

    def _build_headers(
        self,
        auth_token: str,
        additional_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Build headers with authentication token

        Args:
            auth_token: Required authentication token for the request
            additional_headers: Optional additional headers to include
        """
        headers = {}
        headers["Cookie"] = f"frontend_token={auth_token}"
        if additional_headers:
            headers.update(additional_headers)
        return headers

    async def update_item(
        self, auth_token: str, system_auth_token: str, task_laui: str, update_data: TaskUpdateData
    ) -> str:
        update_json_str = update_data.model_dump_json(exclude_none=True)
        update_dict = json.loads(update_json_str)
        response = await self._request_with_retry(
            "post",
            f"/task/update/{task_laui}",
            json=update_dict,
            headers=self._build_headers(auth_token, {"X-System-Auth-Token": system_auth_token}),
        )
        if response.status_code != 200:
            log_error(
                "celery",
                "APIClient",
                "update_item",
                f"Update failed with {response.status_code}: {response.text}",
            )
        response.raise_for_status()
        return str(task_laui)

    async def get_item(
        self, auth_token: str, item_laui: str, session_id: str | None = None
    ) -> Item:
        response = await self._request(
            "get",
            "/catalog/get",
            params={"item_laui": item_laui},
            headers=self._build_headers(auth_token),
        )
        response.raise_for_status()
        data = response.json()
        return Item(**data)

    async def finish_task(
        self, auth_token: str, system_auth_token: str, task_laui: str, session_id: str | None = None
    ):
        additional_headers = {"X-System-Auth-Token": system_auth_token}
        response = await self._request_with_retry(
            "post",
            f"/task/finish/{task_laui}",
            headers=self._build_headers(auth_token, additional_headers),
        )
        response.raise_for_status()

    async def get_tasks_ready_to_run(
        self, auth_token: str, project_laui: PydanticObjectId
    ) -> list[dict]:
        additional_headers = {"X-System-Auth-Token": auth_token}
        response = await self._request(
            "get",
            f"/catalog/get/tasks_ready_to_run/{project_laui}",
            headers=self._build_headers(auth_token, additional_headers),
        )
        response.raise_for_status()
        return response.json()

    async def run_multiple_tasks(self, auth_token: str, tasks: dict[str, Any]) -> dict[str, Any]:
        payload = {"task_lauis": tasks["task_lauis"]}
        response = await self._request(
            "post", "/task/multiple_tasks", json=payload, headers=self._build_headers(auth_token)
        )
        if response.status_code != 200:
            log_error(
                "celery",
                "APIClient",
                "run_multiple_tasks",
                f"Task execution failed with status {response.status_code}: {response.text}",
            )
        response.raise_for_status()
        return response.json()

    async def get_project(self, auth_token: str, item_laui: PydanticObjectId) -> dict[str, Any]:
        response = await self._request(
            "get",
            "/catalog/get",
            params={"item_laui": str(item_laui)},
            headers=self._build_headers(auth_token),
        )
        response.raise_for_status()
        return response.json()

    async def update_project_metadata(
        self,
        auth_token: str,
        item_laui: str,
        item_type: str,
        name: str,
        parent_laui: str | None,
        folder_metadata: dict,
        account_laui: str | None = None,
        project_laui: str | None = None,
    ) -> str:
        payload = {
            "item_laui": item_laui,
            "item_type": item_type,
            "name": name,
            "folder_metadata": folder_metadata,
        }
        if parent_laui:
            payload["parent_laui"] = parent_laui
        if account_laui:
            payload["account_laui"] = account_laui
        if project_laui:
            payload["project_laui"] = project_laui

        response = await self._request_with_retry(
            "post", "/catalog/create", json=payload, headers=self._build_headers(auth_token)
        )
        if response.status_code != 200:
            log_error(
                "celery",
                "APIClient",
                "update_project_metadata",
                f"Update failed with status {response.status_code}: {response.text}",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            log_error(
                "celery",
                "APIClient",
                "update_project_metadata",
                f"HTTPStatusError for item_laui={item_laui}: {e}\n{traceback.format_exc()}",
            )
            raise
        response_data = CreateItemResponse(**response.json())
        return response_data.item_laui

    async def get_running_tasks(
        self, auth_token: str, project_laui: PydanticObjectId
    ) -> list[dict]:
        response = await self._request(
            "get",
            "/catalog/get",
            params={
                "item_laui": str(project_laui),
                "item_type": "task",
                "filter_state": "running",
                "parent_or_child": "child",
                "per_page": 100,
            },
            headers=self._build_headers(auth_token),
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "items" in data:
            return [item.get("item", item) for item in data["items"]]
        if isinstance(data, list):
            return data
        return []
