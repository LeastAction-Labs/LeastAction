# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest
from fastapi.testclient import TestClient
from pydantic_mongo import PydanticObjectId

from src.core.db.types import MongoDatabase
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.repo import UserRepository
from src.core.ee.iam.user.schema import CreateUser, UserType
from src.core.ee.iam.user.service import UserService
from src.core.ee.license.schema import LicenseClaims, LicenseTier, LicenseUploadRequest
from tests.integration.schema import TestRequest
from tests.integration.utils import execute_request

pytestmark = pytest.mark.anyio


async def test_create_user(client: TestClient, test_database: MongoDatabase):

    # create account item
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.account", "name": "a", "is_root": True},
        ),
    )
    assert response.status_code == 200

    user_service = UserService(user_repo=UserRepository(test_database))

    # create root user
    root_user_email = "root_user@gmail.com"
    root_user_username = "root_user"
    root_user_password = "password"
    root_user = None
    try:
        root_user = await user_service.get_user_by_email(root_user_email)
    except Exception:
        await user_service.create_user(
            user=CreateUser(
                username=root_user_username,
                email=root_user_email,
                password=root_user_password,
                user_type=UserType.ROOT,
            )
        )
        root_user = await user_service.get_user_by_email(root_user_email)

    license_claims = LicenseClaims(
        permanent_seats=100,
        trial_seats=0,
        tier=LicenseTier.BUSINESS,
        user_laui=PydanticObjectId(root_user.laui),
    )
    import jwt

    license_id = jwt.encode(
        license_claims.model_dump(mode="json"), SessionService.load_private_key(), algorithm="RS256"
    )
    license_upload_body = LicenseUploadRequest(
        license_id=license_id, public_key=SessionService.load_public_key()
    )

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/license/upload", method="post", json=license_upload_body.model_dump()
        ),
    )

    test_user_username = "test_user"
    test_user_email = "test_user@gmail.com"

    try:
        await user_service.get_user_by_email(test_user_email)
    except Exception:
        response = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/admin/user/create",
                method="post",
                json={"username": test_user_username, "email": test_user_email},
            ),
        )
        assert response.status_code == 200

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/user/create",
            method="post",
            json={"username": test_user_username, "email": test_user_email},
        ),
    )
    assert response.status_code == 409
    assert response.json()["message"] == f"user with username: {test_user_username} already exists"

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/user/create",
            method="post",
            json={"username": test_user_username, "email": "a" + test_user_email},
        ),
    )
    assert response.status_code == 409
    assert response.json()["message"] == f"user with username: {test_user_username} already exists"

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/user/create",
            method="post",
            json={"username": "a" + test_user_username, "email": test_user_email + ""},
        ),
    )
    assert response.status_code == 409
    assert response.json()["message"] == f"user with email: {test_user_email} already exists"
