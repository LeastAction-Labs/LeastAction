# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import APIRouter

from src.core.api.routes.action import action_router
from src.core.api.routes.admin import admin_router
from src.core.api.routes.ai import ai_router
from src.core.api.routes.auth import auth_router
from src.core.api.routes.catalog import catalog_router
from src.core.api.routes.cron import cron_router
from src.core.api.routes.docs import docs_router
from src.core.api.routes.embed import embed_router
from src.core.api.routes.group import group_router
from src.core.api.routes.logs import logs_router
from src.core.api.routes.dataplane import query_router
from src.core.api.routes.task import task_router
from src.core.api.routes.user import user_router
from src.core.ee.routes.access import access_router

v1Router = APIRouter()

v1Router.include_router(auth_router)
v1Router.include_router(catalog_router, prefix="/catalog", tags=["catalog"])
v1Router.include_router(ai_router, prefix="/ai", tags=["ai"])
v1Router.include_router(task_router, prefix="/task", tags=["task"])
v1Router.include_router(action_router, prefix="/action", tags=["action"])
v1Router.include_router(cron_router, prefix="/cron", tags=["cron"])
v1Router.include_router(logs_router, prefix="/logs", tags=["logs"])
v1Router.include_router(access_router, prefix="/access")
v1Router.include_router(group_router, prefix="/group")
v1Router.include_router(user_router, prefix="/user")
v1Router.include_router(admin_router, prefix="/admin")
v1Router.include_router(docs_router, prefix="/docs", tags=["docs"])
v1Router.include_router(query_router, prefix="/query", tags=["query"])
v1Router.include_router(embed_router, prefix="/embed", tags=["embed"])


# authenticated sample route
@v1Router.get("/check")
def check():
    return


@v1Router.get("/health")
def check_health():
    return


@v1Router.get("/system/info")
def get_system_info():
    from src.common.utils import load_system_config

    config = load_system_config()
    bv = config.get("explore_view", {})
    return {
        "core_version": config.get("core_version", "0.0.0"),
        "explore_view": {
            "name": bv.get("name", "Report Explorer"),
            "logo_url": bv.get("logo_url", ""),
            "logo_width": str(bv.get("logo_width", "auto")),
            "logo_height": str(bv.get("logo_height", "24")),
        },
    }
