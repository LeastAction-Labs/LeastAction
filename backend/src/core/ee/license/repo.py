# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.core.db.transaction import session_context
from src.core.db.types import MongoDatabase

from .schema import CreateLicense, CreateLicenseInDB, License, LicenseProjection, UpdateLicense


class LicenseRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "licenses"

    async def create_license(self, license: CreateLicense) -> PydanticObjectId:
        try:
            session = session_context.get()
            create_license_in_db = CreateLicenseInDB(
                **license.model_dump(), created_at=datetime.now(UTC)
            )
            db_license = await self.db[self.collection_name].insert_one(
                create_license_in_db.model_dump(), session=session
            )
            return db_license.inserted_id
        except Exception as e:
            log_error("api", "license_repository", "create_license", str(e))
            log_error("api_traceback", "license_repository", "create_license", str(e))
            raise e

    async def delete_license(self) -> None:
        try:
            session = session_context.get()
            await self.db[self.collection_name].delete_many({}, session=session)
        except Exception as e:
            log_error("api", "license_repository", "create_license", str(e))
            log_error("api_traceback", "license_repository", "delete_license", str(e))
            raise e

    async def get_license(self, license_laui: PydanticObjectId) -> License:
        try:
            session = session_context.get()
            license = await self.db[self.collection_name].find_one(
                {"_id": license_laui}, session=session
            )
            if not license:
                raise NotFoundError("license not found")
            return License(**license)
        except Exception as e:
            log_error("api", "license_repository", "get_license", str(e))
            log_error("api_traceback", "license_repository", "get_license", str(e))
            raise e

    async def get_license_by_filter(self, filter: dict[str, Any]) -> License:
        try:
            session = session_context.get()
            license = await self.db[self.collection_name].find_one(filter, session=session)
            if not license:
                raise NotFoundError("license not found")
            return License(**license)
        except Exception as e:
            log_error("api", "license_repository", "get_license", str(e))
            log_error("api_traceback", "license_repository", "get_license", str(e))
            raise e

    async def find_licenses(
        self,
        filter: dict[str, Any] = {},
        offset: int = 0,
        limit: int = 0,
        projections: dict[str, int] | None = {"status": 1, "tier": 1, "license_id": 1},
    ) -> list[License]:
        try:
            session = session_context.get()
            licenses = (
                await self.db[self.collection_name]
                .find(filter, projections, skip=offset, limit=limit, session=session)
                .sort("created_at", 1)
                .to_list(length=None)
            )
            return [LicenseProjection(**license) for license in licenses]
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "license_repository",
                "find_licenses",
                f"Failed to find licenses, {error_string}",
            )
            log_error(
                "api_traceback",
                "license_repository",
                "find_licenses",
                f"Failed to find licenses, {error_string}",
            )
            raise e

    async def update_license(self, license: UpdateLicense):
        try:
            session = session_context.get()

            update_dict = {
                "$set": {
                    **license.model_dump(exclude=["user_list_patch", "laui"], exclude_unset=True),
                    "updated_at": datetime.now(UTC),
                }
            }

            if license.user_list_patch.add:
                update_dict["$push"] = {"user_list": {"$each": license.user_list_patch.add}}

            if license.user_list_patch.remove:
                update_dict["$pullAll"] = {"user_list": license.user_list_patch.remove}

            await self.db[self.collection_name].update_one(
                {"_id": license.laui}, update_dict, session=session
            )

        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "license_repository",
                "update_license",
                f"Failed to update license, {error_string}",
            )
            log_error(
                "api_traceback",
                "license_repository",
                "update_license",
                f"Failed to update license, {error_string}",
            )
            raise e


def get_license_repository(request: Request):
    return request.app.state.license_repo
