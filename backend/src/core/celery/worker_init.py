# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
from pathlib import Path

from celery import signals

from src.common.config import Config
from src.common.logger.logger import initialize_logger
from src.core.celery.app import get_celery_config
from src.core.celery.client import APIClient
from src.core.celery.executors.action_executor import ActionExecutionService
from src.core.celery.executors.task_executor import TaskExecutionService
from src.core.task.action.action_manager import ActionManager

initialize_logger(Config())

api_client: APIClient | None = None
task_execution_service: TaskExecutionService | None = None
action_execution_service: ActionExecutionService | None = None
_worker_loop: asyncio.AbstractEventLoop | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop:
    if _worker_loop is None:
        raise RuntimeError(
            "Worker event loop not initialized — this code must run inside a Celery worker process."
        )
    return _worker_loop


def get_api_client() -> APIClient:
    if api_client is None:
        raise RuntimeError(
            "API client not initialized — this code must run inside a Celery worker process."
        )
    return api_client


def get_task_execution_service() -> TaskExecutionService:
    if task_execution_service is None:
        raise RuntimeError(
            "Task execution service not initialized — this code must run inside a Celery worker process."
        )
    return task_execution_service


def get_action_execution_service() -> ActionExecutionService:
    if action_execution_service is None:
        raise RuntimeError(
            "Action execution service not initialized — this code must run inside a Celery worker process."
        )
    return action_execution_service


@signals.worker_process_init.connect
def init_worker(**_kwargs):
    global _worker_loop, api_client, task_execution_service, action_execution_service
    config = Config()
    initialize_logger(config)
    _worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_worker_loop)
    celery_cfg = get_celery_config()
    from src.core.celery.registry.actions import execute_action

    api_client = APIClient(base_url=celery_cfg.api_client_base_url)
    action_manager = ActionManager(api_client=api_client, action_task=execute_action)
    task_execution_service = TaskExecutionService(
        api_client=api_client,
        operators_dir=Path(celery_cfg.operators_dir),
        action_manager=action_manager,
    )
    action_execution_service = ActionExecutionService(
        api_client=api_client,
        action_dir=Path(celery_cfg.actions_dir),
    )


@signals.worker_process_shutdown.connect
def shutdown_worker(**_kwargs):
    global _worker_loop, api_client, task_execution_service, action_execution_service
    if _worker_loop is not None and api_client is not None:
        _worker_loop.run_until_complete(api_client.close())
        _worker_loop.close()
        _worker_loop = None
        api_client = None
        task_execution_service = None
        action_execution_service = None
