# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import (
    ConflictError,
    InvalidArgumentError,
    NotFoundError,
)
from src.common.logger.logger import log_error, log_info
from src.common.utils import load_system_config
from src.core.catalog.item.schema import CreateItem, Item
from src.core.catalog.service import CatalogService
from src.core.cron.schema import CronStatus
from src.core.task.celery_orchestrator import CeleryOrchestrator


class CronManager:
    def __init__(
        self,
        catalog_service: CatalogService,
        celery_orchestrator: CeleryOrchestrator,
        config_path: str | None = None,
    ) -> None:
        self.catalog_service = catalog_service
        self.config_path = config_path
        self.cron_config = load_system_config()
        self.celery_orchestrator = celery_orchestrator
        self.cron_interval = self.cron_config.get("project_scheduler_interval")

    def _get_cron_interval_for_project(self, project_name: str) -> int:
        """Get the cron interval for a specific project."""
        project_interval_key = f"{project_name}_cron_interval"
        interval = self.cron_config.get(project_interval_key, self.cron_interval)
        return interval

    async def _update_project_metadata(
        self, project: Item, folder_metadata: dict[str, Any]
    ) -> None:
        # Only send the fields we're updating
        update_item = CreateItem(
            item_laui=project.laui,
            item_type=project.item_type,
            name=project.name,
            parent_laui=project.parent_laui,
            folder_metadata=folder_metadata,
            account_laui=getattr(project, "account_laui", None),
            project_laui=getattr(project, "project_laui", None),
        )
        await self.catalog_service.update_existing_item(existing_item=project, new_item=update_item)

    async def _cron_exists(self, project_laui: PydanticObjectId) -> bool:
        """Check if a cron job is actively running for the project."""
        try:
            project = await self.catalog_service.find_item(
                item_laui=project_laui, include_deleted=False
            )

            folder_metadata = getattr(project, "folder_metadata", {}) or {}
            cron_status = folder_metadata.get("cron_status")

            if cron_status not in [CronStatus.STARTED, CronStatus.RUNNING]:
                error_msg = f"Cron not running (status={cron_status})"
                if cron_status == CronStatus.ERROR:
                    error_msg += f" - error: {folder_metadata.get('error', 'Unknown error')}"
                log_info("cron", "cron_manager", "_cron_exists", error_msg)
                return False

            # Check if heartbeat is stale (delayed over 3 times the interval)
            latest_heartbeat = folder_metadata.get("latest_heartbeat")
            if isinstance(latest_heartbeat, str):
                latest_heartbeat = datetime.fromisoformat(latest_heartbeat)
            if latest_heartbeat:
                # Ensure latest_heartbeat is timezone-aware
                if latest_heartbeat.tzinfo is None:
                    latest_heartbeat = latest_heartbeat.replace(tzinfo=UTC)

                interval = self._get_cron_interval_for_project(project.name)
                max_delay = timedelta(seconds=interval * 3)
                time_since_heartbeat = datetime.now(UTC) - latest_heartbeat

                if time_since_heartbeat > max_delay:
                    log_info(
                        "cron",
                        "cron_manager",
                        "_cron_exists",
                        f"Heartbeat is stale (delay={time_since_heartbeat.total_seconds()}s > {max_delay.total_seconds()}s)",
                    )
                    return False

            return True

        except NotFoundError:
            log_error(
                "cron",
                "cron_manager",
                "_cron_exists",
                f"Project not found: {project_laui}",
            )
            raise
        except Exception as e:
            log_error(
                "cron",
                "cron_manager",
                "_cron_exists",
                f"Error checking cron existence: {e}",
            )
            raise

    async def start_cron(self, project_laui: PydanticObjectId) -> bool:
        # TODO: Add cron_started_by parameter to track who started the cron
        try:
            log_info(
                "cron",
                "cron_manager",
                "start_cron",
                f"Starting cron for project_laui={project_laui}",
            )

            if await self._cron_exists(project_laui):
                log_error(
                    "cron",
                    "cron_manager",
                    "start_cron",
                    f"Cron already running for project_laui={project_laui}",
                )
                raise ConflictError(
                    message="Cron is already running for this project",
                    detail={"project_laui": str(project_laui)},
                )

            project = await self.catalog_service.find_item(
                item_laui=project_laui, include_deleted=False
            )
            print(project_laui)
            print(project)

            if project.item_type != "folder.project":
                raise InvalidArgumentError(
                    message="Item is not a project",
                    detail={"item_type": project.item_type},
                )

            interval = self._get_cron_interval_for_project(project.name)

            # Update project status to STARTED and clear any previous errors
            folder_metadata = getattr(project, "folder_metadata", {}) or {}
            folder_metadata["cron_status"] = CronStatus.STARTED
            folder_metadata["latest_heartbeat"] = datetime.now(UTC).isoformat()
            folder_metadata["start_date"] = datetime.now(UTC).isoformat()
            folder_metadata["stop_date"] = None
            folder_metadata["error"] = None

            await self._update_project_metadata(project, folder_metadata)

            celery_response = await self.celery_orchestrator.run_cron(
                project_laui=project_laui, interval=interval
            )
            log_info(
                "cron",
                "cron_manager",
                "start_cron",
                f"Cron started for project_laui={project_laui}, celery_id={celery_response}",
            )

            return True

        except (ConflictError, InvalidArgumentError, NotFoundError):
            raise
        except Exception as e:
            log_error(
                "cron",
                "cron_manager",
                "start_cron",
                f"Failed to start cron: {e}",
            )
            raise

    async def stop_cron(self, project_laui: PydanticObjectId) -> bool:
        # TODO: Add stopped_by parameter to track who stopped the cron
        try:
            log_info(
                "cron",
                "cron_manager",
                "stop_cron",
                f"Stopping cron for project_laui={project_laui}",
            )

            if not await self._cron_exists(project_laui):
                log_error(
                    "cron",
                    "cron_manager",
                    "stop_cron",
                    f"Cron not running for project_laui={project_laui}",
                )
                raise NotFoundError(
                    message="Cron is not running for this project",
                    detail={"project_laui": str(project_laui)},
                )
            project = await self.catalog_service.find_item(
                item_laui=project_laui, include_deleted=False
            )

            # Update project status to STOP (executor will change to STOPPED)
            folder_metadata = getattr(project, "folder_metadata", {}) or {}
            folder_metadata["cron_status"] = CronStatus.STOP
            folder_metadata["latest_heartbeat"] = datetime.now(UTC).isoformat()
            folder_metadata["stop_date"] = datetime.now(UTC).isoformat()
            # TODO: Handle retry for update fail due to transaction

            await self._update_project_metadata(project, folder_metadata)
            log_info(
                "cron",
                "cron_manager",
                "stop_cron",
                f"Cron stop requested for project_laui={project_laui}",
            )

            return True

        except NotFoundError:
            raise
        except Exception as e:
            log_error("cron", "cron_manager", "stop_cron", f"Failed to stop cron: {e}")
            raise


def get_cron_manager(request: Request) -> CronManager:
    return request.app.state.cron_manager
