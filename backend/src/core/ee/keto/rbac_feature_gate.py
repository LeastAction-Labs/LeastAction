# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# feature gating code , we are not using it currently , might use it later.
"""
import importlib
from typing import Protocol , Optional
from src.core.ee.license.service import LicenseService
from fastapi import Request
from src.core.ee.keto.schema import (
    Permission, Relation,
    SharedItemsResponse,
    RelationTupleWithPermission,
    GroupsResponse
)
from contextvars import ContextVar

class RBACInterface(Protocol):

    async def check_item_edit_access(
        self,
        item_laui:str ,
        user_laui:str
    ) -> None:
        ...

    async def check_item_view_access(
        self,
        item_laui:str ,
        user_laui:str
    ) -> None:
        ...

    async def check_item_own_access(
        self,
        item_laui:str ,
        user_laui:str
    ) -> None:
        ...


    async def check_item_delete_access(
        self,
        item_laui:str ,
        user_laui:str
    ) -> None:
        ...


    async def check_group_own_access(
        self,
        group_laui:str ,
        user_laui:str
    ) -> None:
        ...

    async def check_group_edit_access(
        self,
        group_laui:str ,
        user_laui:str
    ) -> None:
        ...


    async def check_group_view_access(
        self,
        group_laui:str ,
        user_laui:str
    ) -> None:
        ...


    async def get_shared_items(
       self,
       user_laui:str ,
       page_size: int ,
       page_token: Optional[str] = None
    ) -> SharedItemsResponse:
        ...

    async def get_permission(
        self,
        item_laui:str,
        user_laui:Optional[str]=None,
        group_laui:Optional[str]=None,
        true_parent_permission:Optional[Permission] = None
    ) -> Permission:
        ...

    async def get_user_group_relation(
        self,user_laui:str,group_laui:str
    ) -> Relation :
        ...

    async def get_all_access_relations(
        self,
        user_laui: str
    ) -> list[RelationTupleWithPermission]:
        ...

    async def get_user_groups(
        self,
        user_laui:str,
        relation: Relation
    ) -> GroupsResponse:
        ...

rbac_context: ContextVar[Optional[RBACInterface]] = ContextVar(
    "rbac_context", default=None
)

async def set_rbac_service(request:Request) -> RBACInterface:
    license_service : LicenseService = request.app.state.license_service
    rbac_included = await license_service.is_rbac_included()
    if rbac_included:
        module = importlib.import_module("src.core.ee.keto.access_reader_ee")
        rbac_service = module.AccessReader(keto_client=request.app.state.keto_client)
        rbac_context.set(rbac_service)
        request.app.state.rbac_service = rbac_service
    else:
        module = importlib.import_module("src.core.ee.keto.access_reader")
        rbac_service = module.AccessReader()
        rbac_context.set(rbac_service)
        request.app.state.rbac_service = rbac_service

def get_rbac_service_from_context() -> RBACInterface:
    return rbac_context.get()

def get_rbac_service(request:Request) -> RBACInterface:
    return request.app.state.rbac_service


from src.core.ee.keto.schema import (
    Permission , Relation ,
    SharedItemsResponse , RelationTupleWithPermission ,
    GroupsResponse
)
from typing import Optional

class AccessReader:

    async def check_item_edit_access(
        self,
        item_laui:str,
        user_laui:str
    ):
        return

    async def check_item_view_access(
        self,
        item_laui:str ,
        user_laui:str
    ):
        return

    async def check_item_own_access(
        self,
        item_laui:str ,
        user_laui:str
    ):
        return

    async def check_item_delete_access(
        self,
        item_laui:str ,
        user_laui:str
    ):
        return

    async def check_group_own_access(
        self,
        group_laui:str ,
        user_laui:str
    ):
        return

    async def check_group_edit_access(
        self,
        group_laui:str ,
        user_laui:str
    ):
        return

    async def check_group_view_access(
        self,
        group_laui:str ,
        user_laui:str
    ) -> None :
        return

    async def get_shared_items(
       self,
       user_laui:str ,
       page_size: int ,
       page_token: Optional[str] = None
    ) -> SharedItemsResponse :
        return SharedItemsResponse(
            item_nodes = [],
            next_page_token = "",
            flag=False
        )

    async def get_permission(
        self,
        item_laui:str,
        user_laui:Optional[str]=None,
        group_laui:Optional[str]=None,
        true_parent_permission:Optional[Permission] = None
    ) -> Permission :
        return Permission.OWN

    async def get_user_group_relation(
        self,
        user_laui:str,
        group_laui:str
    ) -> Relation :
        return Relation.OWNERS

    async def get_all_access_relations(
        self,
        user_laui: str
    ) -> list[RelationTupleWithPermission]:
        return []

    async def get_user_groups(
        self,
        user_laui:str,
        relation: Relation
    ) -> GroupsResponse:
        return GroupsResponse(
            groups = [],
            next_page_token = ""
        )
"""
