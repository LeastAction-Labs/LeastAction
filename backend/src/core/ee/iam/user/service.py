# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import hashlib

from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import AuthenticationError
from src.common.utils import generate_password
from src.core.admin.api_request import (
    GetUsersRequest,
    GetUsersResponse,
    PaginationResponse,
    UpdateUserPayload,
)

from .api_request import CreateUserResponse, SearchUsersRequest, SearchUsersResponse
from .repo import UserRepository
from .schema import CreateUser, User


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_user(
        self, user: CreateUser, auto_generate: bool = False
    ) -> CreateUserResponse:

        if auto_generate:
            temp_password = generate_password()
            user.password = temp_password
            user.must_change_password = True
        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
        user.password = hashed_password

        user_laui = await self.user_repo.create_user(user)

        response = CreateUserResponse(user_laui=user_laui)
        if auto_generate:
            response.username = (user.username,)
            response.temp_password = temp_password
        return response

    async def change_password(
        self, laui: PydanticObjectId, current_password: str, new_password: str
    ) -> None:
        user = await self.user_repo.find_user(laui)
        if hashlib.sha256(current_password.encode()).hexdigest() != user.password:
            raise AuthenticationError(message="Current password is incorrect")
        new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
        await self.user_repo.update_user(
            laui, {"password": new_hashed, "must_change_password": False}
        )

    async def authenticate(self, username: str, password: str) -> User:
        user = await self.user_repo.get_user_by_username(username)
        if hashlib.sha256(password.encode()).hexdigest() != user.password:
            raise AuthenticationError(message="Invalid password")
        return user

    async def get_user_by_username(self, username: str) -> User:
        return await self.user_repo.get_user_by_username(username)

    async def get_user_by_email(self, email: str) -> User:
        return await self.user_repo.get_user_by_email(email)

    async def find_user(self, laui: PydanticObjectId):
        return await self.user_repo.find_user(laui=laui)

    async def get_users(self, request: GetUsersRequest) -> list[User]:
        users = await self.user_repo.find_users(
            filter={},
            projections=[
                "username",
                "email",
                "is_active",
                "created_at",
                "allowed_mcp_tools",
                "chat_agent_name",
                "chat_agent_laui",
            ],
            offset=request.offset,
            limit=request.limit,
        )
        has_next = await self.user_repo.check_next_page_exists(
            filter={}, offset=request.offset, limit=request.limit
        )
        return GetUsersResponse(
            users=users,
            pagination=PaginationResponse(
                current_page=request.page, per_page=request.per_page, has_next=has_next
            ),
        )

    async def delete_user(self, laui: PydanticObjectId) -> None:
        await self.user_repo.delete_user(laui)

    async def update_user(self, laui: PydanticObjectId, payload: UpdateUserPayload) -> None:
        await self.user_repo.update_user(laui, payload.model_dump(exclude_unset=True))

    async def update_users(self, lauis: list[PydanticObjectId], payload: UpdateUserPayload) -> None:
        await self.user_repo.update_users(
            lauis=lauis, update_data=payload.model_dump(exclude_unset=True)
        )

    async def search_users(self, request: SearchUsersRequest) -> SearchUsersResponse:
        users = await self.user_repo.find_users(
            filter=request.get_filters,
            projections=["username", "email"],
            offset=request.offset,
            limit=request.limit,
        )
        has_next = await self.user_repo.check_next_page_exists(
            filter=request.get_filters, offset=request.offset, limit=request.limit
        )
        return SearchUsersResponse(
            users=users,
            pagination=PaginationResponse(
                current_page=request.page, per_page=request.per_page, has_next=has_next
            ),
        )


def get_user_service(request: Request) -> UserService:
    return request.app.state.user_service
