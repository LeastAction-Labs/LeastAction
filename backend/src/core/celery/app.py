# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from celery import Celery

from src.core.celery.config import CeleryConfig

celery_cfg = CeleryConfig()


def get_celery_config() -> CeleryConfig:
    return celery_cfg


# Initialize Celery application
app = Celery(
    "least_action_celery",
    broker=celery_cfg.broker_url,
    backend=celery_cfg.result_backend,
)

# Configure worker behavior
app.conf.update(
    worker_prefetch_multiplier=celery_cfg.worker_config.get("prefetch_multiplier", 1),
    task_acks_late=celery_cfg.worker_config.get("acks_late", True),
    task_track_started=celery_cfg.worker_config.get("track_started", True),
    task_reject_on_worker_lost=celery_cfg.worker_config.get("reject_on_worker_lost", True),
    task_acks_on_failure_or_timeout=celery_cfg.worker_config.get(
        "acks_on_failure_or_timeout", False
    ),
    worker_max_tasks_per_child=celery_cfg.worker_config.get("max_tasks_per_child", 100),
    worker_max_memory_per_child=celery_cfg.worker_config.get("max_memory_per_child", 524288),
    worker_cancel_long_running_tasks_on_connection_loss=celery_cfg.worker_config.get(
        "cancel_long_running_tasks_on_connection_loss", True
    ),
    worker_send_task_events=celery_cfg.worker_config.get("send_task_events", True),
    task_send_sent_event=celery_cfg.worker_config.get("send_sent_event", True),
)

# Import worker initialization (registers signal handlers)
import src.core.celery.worker_init  # noqa

# Import task definitions
import src.core.celery.registry  # noqa
