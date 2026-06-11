# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import APIRouter

from src.core.api.routes.ai import ai_router
from src.core.api.routes.catalog import catalog_router
from src.core.api.routes.cron import cron_router

test_router = APIRouter()

test_router.include_router(catalog_router, prefix="/catalog")
test_router.include_router(ai_router, prefix="/ai")
test_router.include_router(cron_router, prefix="/cron", tags=["test-cron"])
