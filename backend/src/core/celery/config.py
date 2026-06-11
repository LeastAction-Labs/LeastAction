# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
from pathlib import Path
from typing import Any

from src.common.exceptions import NotFoundError
from src.common.utils import load_system_config


class CeleryConfig:
    def __init__(self):
        cfg = load_system_config()
        if "celery" not in cfg:
            raise NotFoundError("Missing 'celery' section in system.yml")

        self._celery = cfg["celery"]
        self._validate()

    def _require(self, key: str):
        data = self._celery
        for part in key.split("."):
            if part not in data:
                raise NotFoundError(f"Missing celery.{key} in system.yml")
            data = data[part]
        return data

    def _validate(self):
        self._require("broker_url")
        self._require("result_backend")
        self._require("operators_dir")
        self._require("actions_dir")
        self._require("task.soft_time_limit")
        self._require("task.hard_time_limit")
        self._require("action.soft_time_limit")
        self._require("action.hard_time_limit")
        self._require("queues.task_queue")
        self._require("queues.action_queue")

    # ---------------- Core ---------------- #

    @property
    def broker_url(self) -> str:
        url = self._celery["broker_url"]
        # Replace localhost with REDIS_HOST env var if set (for Docker)
        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            url = url.replace("localhost", redis_host)
        return url

    @property
    def result_backend(self) -> str:
        url = self._celery["result_backend"]
        # Replace localhost with REDIS_HOST env var if set (for Docker)
        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            url = url.replace("localhost", redis_host)
        return url

    # ----------------- Directories ---------------------#
    @property
    def actions_dir(self) -> Path:
        return self._celery["actions_dir"]

    @property
    def operators_dir(self) -> Path:
        return self._celery["operators_dir"]

    # ---------------- Time limits ---------------- #

    @property
    def task_soft_time_limit(self) -> int:
        return int(self._celery["task"]["soft_time_limit"])

    @property
    def task_hard_time_limit(self) -> int:
        return int(self._celery["task"]["hard_time_limit"])

    @property
    def action_soft_time_limit(self) -> int:
        return int(self._celery["action"]["soft_time_limit"])

    @property
    def action_hard_time_limit(self) -> int:
        return int(self._celery["action"]["hard_time_limit"])

    # ---------------- Queues ---------------- #

    @property
    def task_queue(self) -> str:
        return self._celery["queues"]["task_queue"]

    @property
    def cron_queue(self) -> str:
        return self._celery["queues"]["cron_queue"]

    @property
    def action_queue(self) -> str:
        return self._celery["queues"]["action_queue"]

    # ---------------- Worker ---------------- #

    @property
    def worker_config(self) -> dict[str, Any]:
        return self._celery["worker"]

    @property
    def api_client_base_url(self) -> str:
        """Get API client base URL from environment variable or config file"""
        # First check environment variable (takes precedence)
        env_url = os.getenv("API_CLIENT_BASE_URL")
        if env_url:
            return env_url
        # Fall back to config file
        return self._celery["api_client_base_url"]
