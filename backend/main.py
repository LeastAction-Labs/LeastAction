# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.common.config import Config
from src.common.env import ENV, get_env
from src.common.logger.logger import initialize_logger
from src.common.secrets import get_secret
from src.common.utils import transform_validation_errors
from src.core.admin.service import AdminService
from src.core.ai.service import AIService
from src.core.api.middleware.admin import admin_middleware
from src.core.api.middleware.auth import auth_middleware
from src.core.api.middleware.catalog import catalog_middleware
from src.core.api.middleware.celery_auth import celery_auth_middleware
from src.core.api.middleware.license import license_middleware
from src.core.api.middleware.session import SessionMiddleware
from src.core.api.middleware.transaction import transaction_context_middleware
from src.core.api.router import v1Router
from src.core.api.test import test_router
from src.core.api.utils import RedirectHandler
from src.core.catalog.item.repo import ItemRepository
from src.core.catalog.item_revision.repo import ItemRevisionRepository
from src.core.catalog.link.repo import LinkRepository
from src.core.catalog.orchestrator import ItemOrchestrator
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.cron.cron_manager import CronManager
from src.core.db.service import create_mongo_client
from src.core.db.transaction import (
    TransactionManager,
)
from src.core.ee.iam.auth.auth_code_dict import AuthCodeDict
from src.core.ee.iam.auth.service import AuthService
from src.core.ee.iam.group.repo import GroupRepository
from src.core.ee.iam.group.service import GroupService
from src.core.ee.iam.refresh_token.repo import RefreshTokenRepository
from src.core.ee.iam.refresh_token.service import RefreshTokenService
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.repo import UserRepository
from src.core.ee.iam.user.service import UserService
from src.core.ee.keto.access_reader import AccessReader
from src.core.ee.keto.service import KetoClient
from src.core.ee.license.repo import LicenseRepository
from src.core.ee.license.service import LicenseService
from src.core.email.service import EmailService
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.celery_orchestrator import CeleryOrchestrator
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.connection.connection_queue_repo import ConnectionQueueRepository
from src.core.task.task_manager import TaskManager
from src.core.task.task_validation_manager import TaskValidationManager
from src.core.validation.service import CodeblockValidator
from src.core.version_manager.service import VersionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config()
    initialize_logger(config)

    database_uri = get_secret("MONGO_URI")
    if get_env() == ENV.TEST:
        database_uri = get_secret("MONGO_TEST_URI")
    if not database_uri:
        raise ValueError("MONGO_URI is not set")
    public_key = SessionService.load_public_key()
    private_key = SessionService.load_private_key()
    app.state.session_service = SessionService(public_key, private_key)

    app.state.mongo_client = await create_mongo_client(database_uri)
    db_name = "LeastAction"
    if get_env() == ENV.TEST:
        db_name = "LeastActionTest"
    active_db = app.state.mongo_client.get_db(db_name)

    app.state.email_service = EmailService()
    app.state.auth_code_dict = AuthCodeDict()
    app.state.redirect_handler = RedirectHandler()
    app.state.user_repo = UserRepository(active_db)
    await app.state.user_repo.create_indexes()
    app.state.license_repo = LicenseRepository(active_db)
    app.state.license_service = LicenseService(app.state.license_repo)
    app.state.user_service = UserService(
        user_repo=app.state.user_repo, license_service=app.state.license_service
    )
    app.state.admin_service = AdminService(
        license_service=app.state.license_service, user_service=app.state.user_service
    )
    app.state.group_repo = GroupRepository(active_db)
    app.state.refresh_token_repo = RefreshTokenRepository(active_db)
    app.state.refresh_token_service = RefreshTokenService(
        refresh_token_repo=app.state.refresh_token_repo
    )
    app.state.auth_service = AuthService(
        user_service=app.state.user_service,
        session_service=app.state.session_service,
        refresh_token_service=app.state.refresh_token_service,
        auth_code_dict=app.state.auth_code_dict,
        admin_service=app.state.admin_service,
    )
    app.state.transaction_manager = TransactionManager(app.state.mongo_client)
    app.state.item_repo = ItemRepository(active_db)
    await app.state.item_repo.create_index()
    app.state.link_repo = LinkRepository(active_db)
    await app.state.link_repo.create_index()
    app.state.item_revision_repo = ItemRevisionRepository(active_db)

    app.state.keto_client = KetoClient()

    app.state.access_reader = AccessReader(
        keto_client=app.state.keto_client, link_repo=app.state.link_repo
    )

    app.state.group_service = GroupService(
        group_repo=app.state.group_repo,
        access_reader=app.state.access_reader,
        user_service=app.state.user_service,
    )
    app.state.connection_manager = ConnectionManager()
    app.state.config_manager = ConfigManager()
    app.state.item_types_manager = ItemTypesManager()
    app.state.catalog_manager = CatalogService(
        item_repo=app.state.item_repo,
        link_repo=app.state.link_repo,
        item_revision_repo=app.state.item_revision_repo,
        access_reader=app.state.access_reader,
        item_types_manager=app.state.item_types_manager,
    )
    app.state.task_validation_manager = TaskValidationManager(
        app.state.connection_manager,
        app.state.config_manager,
        app.state.catalog_manager,
        app.state.item_types_manager,
    )
    app.state.celery_orchestrator = CeleryOrchestrator(
        session_service=app.state.session_service, user_service=app.state.user_service
    )
    app.state.pre_action_manager = PreActionManager(
        app.state.celery_orchestrator, app.state.catalog_manager
    )

    app.state.connection_queue_repo = ConnectionQueueRepository(db=active_db)
    app.state.connection_queue_manager = ConnectionQueueManager(
        connection_queue_repo=app.state.connection_queue_repo
    )

    app.state.task_manager = TaskManager(
        app.state.task_validation_manager,
        app.state.pre_action_manager,
        app.state.celery_orchestrator,
        app.state.connection_queue_manager,
        app.state.catalog_manager,
        app.state.config_manager,
        connection_manager=app.state.connection_manager,
    )
    app.state.codeblock_validator = CodeblockValidator()
    app.state.cron_manager = CronManager(
        catalog_service=app.state.catalog_manager, celery_orchestrator=app.state.celery_orchestrator
    )
    app.state.version_manager = VersionManager()
    app.state.item_orchestrator = ItemOrchestrator(
        app.state.task_manager,
        app.state.catalog_manager,
        app.state.pre_action_manager,
        app.state.connection_queue_manager,
        app.state.codeblock_validator,
        app.state.version_manager,
    )

    from src.core.dataplane.mcp_proxy import McpProxyManager
    from src.core.mcp.server import create_mcp_server

    # Shared proxy manager for the awslabs/Azure MCP subprocesses — used by both the
    # MCP tools and the /query route (Data Inspector) so they reuse the same servers.
    app.state.mcp_proxy = McpProxyManager()
    app.state.mcp_server = create_mcp_server(app.state.item_orchestrator, app.state.mcp_proxy)
    mcp_http_app = app.state.mcp_server.http_app(stateless_http=True, path="/")
    app.mount("/mcp", mcp_http_app)

    async with mcp_http_app.lifespan(mcp_http_app):
        app.state.ai_service = AIService(
            app.state.catalog_manager,
            app.state.codeblock_validator,
            mcp_server=app.state.mcp_server,
        )

        yield

    await app.state.mcp_proxy.aclose()
    await app.state.mongo_client.close_connection()


# Limit traceback depth
sys.tracebacklimit = 0
# Initialize FastAPI app
app = FastAPI(
    title="Least Actions",
    description="Backend for Least Actions",
    version="1.0.0",
    lifespan=lifespan,
)


# MCP clients probe this before connecting; return OAuth error format so SDK falls back to Bearer
@app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
async def _mcp_oauth_discovery():
    return JSONResponse({"error": "not_supported"}, status_code=404)


# Configure CORS
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:80",
    "http://localhost",
]
_app_public_url = os.getenv("APP_PUBLIC_URL")
if _app_public_url:
    _cors_origins.append(_app_public_url.rstrip("/"))

app.middleware("http")(catalog_middleware)
app.middleware("http")(admin_middleware)
app.middleware("http")(license_middleware)
app.middleware("http")(auth_middleware)
app.middleware("http")(celery_auth_middleware)
app.middleware("http")(transaction_context_middleware)
app.add_middleware(SessionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=[
        "X-Session-ID"
    ],  # Must explicitly list headers when allow_credentials=True (wildcard * not allowed)
    max_age=1800,  # Preflight request caching ( minutes)
)


@app.get("/")
async def root():
    return {"message": "Welcome to Least Actions"}


app.include_router(test_router, prefix="/test")
app.include_router(v1Router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Invalid request parameters provided.",
            "detail": jsonable_encoder(transform_validation_errors(exc.errors())),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code, content=transform_validation_errors(exc.detail)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
