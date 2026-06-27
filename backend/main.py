# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

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
from src.core.api.middleware.license import license_middleware
from src.core.api.middleware.session import SessionMiddleware
from src.core.api.middleware.transaction import transaction_context_middleware
from src.core.api.router import v1Router
from src.core.api.test import test_router
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
    app.state.user_repo = UserRepository(active_db)
    await app.state.user_repo.create_indexes()
    app.state.user_service = UserService(user_repo=app.state.user_repo)
    app.state.license_repo = LicenseRepository(active_db)
    app.state.license_service = LicenseService(app.state.license_repo)
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


# app.include_router(items_router, prefix="/items")
# app.include_router(links_router, prefix="/links")
# app.include_router(ai_router, prefix="/ai")
# app.include_router(auth_router, prefix="/auth")
app.include_router(test_router, prefix="/test")
app.include_router(v1Router, prefix="/api/v1")
# Endpoint for logging
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "logs" / "app.log"
LOGS_DIR = BASE_DIR / "logs"


@app.get("/logs")
async def get_logs():
    """Return the full contents of the log file"""
    try:
        with open(LOG_FILE) as f:
            content = f.read()
        return {"logs": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


@app.get("/logs/listItems")
async def list_log_items():
    """Return list of all files and folders in the logs directory"""
    try:
        if not LOGS_DIR.exists():
            raise HTTPException(status_code=404, detail="Logs directory not found")

        items = []
        for item in LOGS_DIR.iterdir():
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime,
                "path": str(item.relative_to(LOGS_DIR)),
            }
            items.append(item_info)

        items.sort(key=lambda x: x["name"], reverse=True)

        return {
            "directory": str(LOGS_DIR),
            "items": items,
            "total_count": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing directory: {str(e)}")


@app.get("/logs/listItems/{folder_path:path}")
async def list_folder_items(folder_path: str):
    """Return list of files and folders in a specific subfolder"""
    try:
        target_path = LOGS_DIR / folder_path

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Folder not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        items = []
        for item in target_path.iterdir():
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime,
                "path": str(item.relative_to(LOGS_DIR)),
            }
            items.append(item_info)

        return {
            "directory": str(target_path),
            "items": items,
            "total_count": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing directory: {str(e)}")


@app.get("/logs/file/{file_path:path}")
async def get_file_details(file_path: str):
    """Get detailed information about a specific file including content for supported formats"""
    try:
        target_file = LOGS_DIR / file_path
        if not target_file.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if not target_file.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        file_stats = target_file.stat()

        # Base response with file metadata
        response = {
            "name": target_file.name,
            "path": str(target_file.relative_to(LOGS_DIR)),
            "full_path": str(target_file),
            "size": file_stats.st_size,
            "modified": file_stats.st_mtime,
            "created": file_stats.st_ctime,
            "extension": target_file.suffix,
            "is_readable": target_file.is_file() and target_file.stat().st_size > 0,
        }

        # Add content for supported file types
        supported_extensions = {".log", ".txt", ".json"}
        if target_file.suffix.lower() in supported_extensions:
            try:
                # Read file content with UTF-8 encoding
                with open(target_file, encoding="utf-8") as f:
                    content = f.read()

                response["content"] = content
                response["content_type"] = "text/plain"

                # Special handling for JSON files
                if target_file.suffix.lower() == ".json":
                    try:
                        import json

                        # Validate JSON and format it
                        json_data = json.loads(content)
                        response["content_type"] = "application/json"
                        response["json_valid"] = True
                        response["formatted_content"] = json.dumps(json_data, indent=2)
                    except json.JSONDecodeError as je:
                        response["json_valid"] = False
                        response["json_error"] = str(je)

            except UnicodeDecodeError:
                # Handle files that aren't UTF-8 encoded
                response["content"] = None
                response["content_error"] = (
                    "File contains non-UTF-8 characters and cannot be displayed as text"
                )
            except Exception as read_error:
                response["content"] = None
                response["content_error"] = f"Error reading file content: {str(read_error)}"
        else:
            response["content"] = None
            response["content_reason"] = (
                f"Content not included - unsupported file type: {target_file.suffix}"
            )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting file details: {str(e)}")


#
# @app.get("/logs/listItems")
# async def list_log_items():
#     """Return list of all files and folders in the logs directory"""
#     try:
#         if not LOGS_DIR.exists():
#             raise HTTPException(status_code=404, detail="Logs directory not found")
#
#         items = []
#         for item in LOGS_DIR.iterdir():
#             item_info = {
#                 "name": item.name,
#                 "type": "directory" if item.is_dir() else "file",
#                 "size": item.stat().st_size if item.is_file() else None,
#                 "modified": item.stat().st_mtime
#             }
#             items.append(item_info)
#
#         return {
#             "directory": str(LOGS_DIR),
#             "items": items,
#             "total_count": len(items)
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error listing directory: {str(e)}")


@app.get("/logs/stream")
async def stream_logs():
    async def event_generator():
        last_position = 0

        # First, Initial content is sent
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE) as f:
                    content = f.read()
                    last_position = len(content)
                    yield f"data: {json.dumps({'content': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Then, we watch for changes
        while True:
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE) as f:
                        f.seek(last_position)
                        new_content = f.read()
                        if new_content:
                            last_position = f.tell()
                            yield f"data: {json.dumps({'content': new_content})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            # the 1 here indicates the duration after which we should
            # check for updates.
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",  # Critical for SSE!
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Invalid request parameters provided.",
            "detail": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(HTTPException)
async def validation_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
