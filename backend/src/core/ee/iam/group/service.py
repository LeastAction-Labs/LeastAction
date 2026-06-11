# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import NotFoundError
from src.core.ee.iam.user.service import UserService
from src.core.ee.keto.access_reader import AccessReader
from src.core.ee.keto.schema import GroupResponse, GroupsResponse, Relation

from .api_request import (
    GetGroupResponse,
    PaginationResponse,
    SearchGroupsRequest,
    SearchGroupsResponse,
)
from .repo import GroupRepository
from .schema import CreateGroup, UpdateGroup


class GroupService:
    def __init__(
        self, group_repo: GroupRepository, access_reader: AccessReader, user_service: UserService
    ):
        self.group_repo = group_repo
        self.access_reader = access_reader
        self.user_service = user_service

    async def create_group(self, group: CreateGroup) -> str:
        try:
            existing_group = await self.group_repo.find_group_by_name(group.name)
            if group.access_patch.add.owners or group.access_patch.remove.owners:
                await self.access_reader.check_group_own_access(
                    group_laui=existing_group.laui, user_laui=get_user_laui()
                )
            else:
                await self.access_reader.check_group_edit_access(
                    group_laui=existing_group.laui, user_laui=get_user_laui()
                )
            await self.group_repo.update_group(
                group=UpdateGroup(**group.model_dump(), laui=existing_group.laui)
            )
            return existing_group.laui
        except NotFoundError:
            user_laui = get_user_laui()
            group.access_patch.add.owners = {f"U{user_laui}": ""}
            return await self.group_repo.create_group(group)

    async def get_groups(self, relation: Relation) -> GroupsResponse:
        raw = await self.access_reader.get_user_groups(user_laui=get_user_laui(), relation=relation)
        groups_with_names = []
        for group_id in raw.groups:
            try:
                group = await self.group_repo.find_group(PydanticObjectId(group_id))
                groups_with_names.append(GroupResponse(id=group_id, name=group.name))
            except Exception:
                groups_with_names.append(GroupResponse(id=group_id, name=group_id))
        return GroupsResponse(groups=groups_with_names, next_page_token=raw.next_page_token)

    async def get_group(self, group_laui: PydanticObjectId) -> GetGroupResponse:
        await self.access_reader.check_group_view_access(
            group_laui=str(group_laui), user_laui=get_user_laui()
        )
        group = await self.group_repo.find_group(group_laui)
        return GetGroupResponse(
            name=group.name,
            description=group.description,
            members=group.access.viewers.keys(),
            admins=group.access.editors.keys(),
            owners=group.access.owners.keys(),
        )

    async def delete_group(self, group_laui: PydanticObjectId) -> str:
        await self.access_reader.check_group_own_access(
            group_laui=str(group_laui), user_laui=get_user_laui()
        )
        await self.group_repo.delete_group(group_laui)

    async def search_groups(self, request: SearchGroupsRequest) -> SearchGroupsResponse:
        groups = await self.group_repo.find_groups(
            filter=request.get_filters,
            projections=["name"],
            offset=request.offset,
            limit=request.limit,
        )
        has_next = await self.group_repo.check_next_page_exists(
            filter=request.get_filters, offset=request.offset, limit=request.limit
        )
        return SearchGroupsResponse(
            groups=groups,
            pagination=PaginationResponse(
                current_page=request.page, per_page=request.per_page, has_next=has_next
            ),
        )


def get_group_service(request: Request) -> GroupService:
    return request.app.state.group_service
