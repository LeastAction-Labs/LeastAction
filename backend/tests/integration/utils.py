# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
import time

import dotenv
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase, MongoDocument
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.schema import UserType
from src.core.ee.license.repo import LicenseRepository
from src.core.ee.license.service import LicenseService
from tests.integration.schema import TestRequest

dotenv.load_dotenv()


def get_session_service():
    return SessionService(
        private_key=SessionService.load_private_key(), public_key=SessionService.load_public_key()
    )


async def get_test_database() -> MongoDatabase:
    test_db_uri = os.getenv("MONGO_TEST_URI")
    if not test_db_uri:
        raise ValueError("MONGO_TEST_URI is not set")
    test_client: AsyncMongoClient[MongoDocument] = AsyncMongoClient(test_db_uri)
    try:
        await test_client.admin.command("ping")
    except Exception as e:
        print(f"Failed to connect to the mongodb: {e}")
        raise e
    print("Got test database client")
    db = test_client["LeastActionTest"]
    db.client_ref = test_client
    return db


async def get_system_access_token() -> str:
    """Get or create the system user's access token from the database"""
    from bson import ObjectId

    from src.core.ee.iam.user.repo import UserRepository
    from src.core.ee.iam.user.schema import CreateUser

    test_db = await get_test_database()

    # Check if system user already exists
    system_user = await test_db["users"].find_one({"email": "system@leastactionlabs.com"})

    if system_user and "system_access_token" in system_user:
        if system_user.get("user_type") != "system":
            await test_db["users"].update_one(
                {"_id": system_user["_id"]}, {"$set": {"user_type": "system"}}
            )
        return system_user["system_access_token"]

    # Create system user if it doesn't exist

    license_repo = LicenseRepository(test_db)
    license_service = LicenseService(license_repo)
    user_service = UserService(user_repo=UserRepository(test_db), license_service=license_service)
    session_service = get_session_service()

    if not system_user:
        # Create new system user
        system_user_data = CreateUser(
            email="system@leastactionlabs.com",
            username="System",
            password="test123",
            user_type=UserType.SYSTEM,
        )

        await user_service.create_user(system_user_data)
        created_user = await user_service.get_user_by_email(email="system@leastactionlabs.com")

        # Generate long-lived access token (10 years)
        long_lived_token = session_service.generate_access_token(
            user=created_user,
            expires_in_hours=87600,  # 10 years
        )

        # Store the token in the user document
        await test_db["users"].update_one(
            {"_id": ObjectId(created_user.laui)},
            {"$set": {"system_access_token": long_lived_token}},
        )

        return long_lived_token
    else:
        # System user exists but doesn't have system_access_token, add it
        existing_user = await user_service.get_user_by_email(email="system@leastactionlabs.com")

        long_lived_token = session_service.generate_access_token(
            user=existing_user,
            expires_in_hours=87600,  # 10 years
        )

        await test_db["users"].update_one(
            {"_id": ObjectId(existing_user.laui)},
            {"$set": {"system_access_token": long_lived_token, "user_type": "system"}},
        )

        return long_lived_token


async def get_user_laui():
    access_token = await get_system_access_token()
    session_service = get_session_service()
    user_laui = session_service.verify_jwt_token(token=access_token).sub
    return user_laui


async def get_auth_header():
    access_token = await get_system_access_token()
    return f"frontend_token={access_token}"


def execute_request(client: TestClient, request: TestRequest):

    if (
        request.url == "/api/v1/catalog/create"
        and request.json
        and request.json.get("item_type", None) == "task"
    ) or (request.url == "/api/v1/task/multiple_tasks"):
        # these apis call get multiple items by laui which uses keto
        # if it doesnt work as expected then they dont send 403 but rather send 422 or 200
        time.sleep(1)

    response = client.request(**request.model_dump(exclude_none=True))
    print("FIXTURE RESPONSE BODY:", response.json())

    if response.status_code == 403:
        # Retry once to handle Keto auth propagation delay
        time.sleep(0.5)
        response = client.request(**request.model_dump(exclude_none=True))
        print("FIXTURE RESPONSE BODY:", response.json())

    return response


from src.common.context_vars.catalog_context import catalog_context
from src.common.context_vars.user_context import set_user_laui
from src.core.catalog.config.catalog_loader import load_catalog_config
from src.core.catalog.item.repo import ItemRepository
from src.core.catalog.item_revision.repo import ItemRevisionRepository
from src.core.catalog.link.repo import LinkRepository
from src.core.catalog.orchestrator import ItemOrchestrator
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.db.transaction import (
    TransactionManager,
    transaction_manager_context,
)
from src.core.ee.iam.user.repo import UserRepository
from src.core.ee.iam.user.service import UserService
from src.core.ee.keto.access_reader import AccessReader
from src.core.ee.keto.service import KetoClient
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.celery_orchestrator import CeleryOrchestrator
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.connection.connection_queue_repo import ConnectionQueueRepository
from src.core.task.task_manager import TaskManager
from src.core.task.task_validation_manager import TaskValidationManager
from src.core.version_manager.service import VersionManager


async def get_item_orchestrator(test_database: MongoDatabase):
    user_laui = await get_user_laui()
    set_user_laui(user_laui)
    transaction_manager = TransactionManager(client=test_database)
    transaction_manager_context.set(transaction_manager)
    item_repo = ItemRepository(test_database)
    await item_repo.create_index()
    link_repo = LinkRepository(test_database)
    await link_repo.create_index()
    item_revision_repo = ItemRevisionRepository(test_database)
    keto_client = KetoClient()
    access_reader = AccessReader(keto_client=keto_client, link_repo=link_repo)
    connection_manager = ConnectionManager()
    config_manager = ConfigManager()
    item_types_manager = ItemTypesManager()
    catalog_manager = CatalogService(
        item_repo=item_repo,
        link_repo=link_repo,
        item_revision_repo=item_revision_repo,
        access_reader=access_reader,
        item_types_manager=item_types_manager,
    )
    task_validation_manager = TaskValidationManager(
        connection_manager, config_manager, catalog_manager, item_types_manager
    )

    # Initialize session and user services for token generation
    session_service = get_session_service()
    license_repo = LicenseRepository(test_database)
    license_service = LicenseService(license_repo)
    user_service = UserService(
        user_repo=UserRepository(test_database), license_service=license_service
    )

    celery_orchestrator = CeleryOrchestrator(
        session_service=session_service, user_service=user_service
    )
    action_manager = PreActionManager(celery_orchestrator, catalog_manager)
    connection_queue_repo = ConnectionQueueRepository(test_database)
    connection_queue_manager = ConnectionQueueManager(connection_queue_repo=connection_queue_repo)

    task_manager = TaskManager(
        task_validation_manager,
        action_manager,
        celery_orchestrator,
        connection_queue_manager,
        catalog_manager,
        config_manager,
        connection_manager,
    )
    version_manager = VersionManager()

    from src.core.validation.service import CodeblockValidator

    codeblock_validator = CodeblockValidator()

    catalog_config = load_catalog_config()
    with catalog_context(config=catalog_config):
        yield ItemOrchestrator(
            task_manager,
            catalog_manager,
            action_manager,
            connection_queue_manager,
            codeblock_validator,
            version_manager,
        )


from tests.integration.schema import BaseFolders


def create_base_folders(client: TestClient) -> BaseFolders:

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.account", "name": "account_folder", "is_root": True},
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    account_folder_laui = response.item_laui

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.project",
                "name": "project_folder",
                "parent_laui": account_folder_laui,
                "account_laui": account_folder_laui,
            },
        ),
    )
    if response.status_code != 200:
        print(f"ERROR creating project folder: {response.json()}")
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    project_folder_laui = response.item_laui

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.trash",
                "name": "trash",
                "parent_laui": account_folder_laui,
                "account_laui": account_folder_laui,
                "project_laui": project_folder_laui,
            },
        ),
    )
    if response.status_code != 200:
        print(f"ERROR creating trash folder: {response.json()}")
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    trash_folder_laui = response.item_laui

    return BaseFolders(
        account_folder_laui=account_folder_laui,
        project_folder_laui=project_folder_laui,
        trash_folder_laui=trash_folder_laui,
    )
