# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio

from bson import ObjectId
from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_root_user_laui, is_root_user
from src.common.exceptions import AuthorizationError
from src.core.catalog.link.repo import LinkRepository

from .api_request import GetAccessRelationsRequest, GetAccessRelationsResponse
from .schema import (
    AccessRelation,
    GroupsRawResponse,
    Namespace,
    Permission,
    Relation,
    RelationTuple,
    RelationTupleParams,
    SharedItemsResponse,
    SubjectSet,
)
from .service import KetoClient
from .utils import permission_relation_map


class AccessReader:
    def __init__(self, keto_client: KetoClient, link_repo: LinkRepository):
        self.keto_client = keto_client
        self.link_repo = link_repo

    async def check_item_edit_access(self, item_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    object=item_laui,
                    relation=Permission.EDIT,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(
                message="Access denied", detail="You do not have permission to edit this item."
            )

    async def check_item_view_access(self, item_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.ITEM,
                    object=item_laui,
                    relation=Permission.VIEW,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(
                message="Access denied", detail="You do not have permission to view this item."
            )

    async def check_item_own_access(self, item_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.ITEM,
                    object=item_laui,
                    relation=Permission.OWN,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(message="Access denied", detail="You do not own this item.")

    async def check_item_delete_access(self, item_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.ITEM,
                    object=item_laui,
                    relation=Permission.DELETE,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(
                message="Access denied", detail="You do not have permission to delete this item."
            )

    async def check_group_own_access(self, group_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.GROUP,
                    object=group_laui,
                    relation=Relation.OWNERS,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(message="Access denied", detail="You do not own this group.")

    async def check_group_edit_access(self, group_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.GROUP,
                    object=group_laui,
                    relation=Permission.EDIT,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(
                message="Access denied", detail="You do not have permission to edit this group."
            )

    async def check_group_view_access(self, group_laui: str, user_laui: str):
        if is_root_user():
            return
        try:
            await self.keto_client.check_permission(
                relation_tuple=RelationTuple(
                    namespace=Namespace.GROUP,
                    object=group_laui,
                    relation=Permission.VIEW,
                    subject_id=user_laui,
                )
            )
        except AuthorizationError:
            raise AuthorizationError(
                message="Access denied", detail="You do not have permission to view this group."
            )

    async def get_shared_items(self, user_laui: str, page_size: int, page_token: str | None = None):
        user_groups = (await self.get_user_groups(user_laui=user_laui)).groups

        # Fetch direct item relations + all group-based item relations concurrently
        queries = [
            self.keto_client.get_relations(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    subject_id=user_laui,
                )
            )
        ] + [
            self.keto_client.get_relations(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    subject_namespace=Namespace.GROUP,
                    subject_relation=Relation.VIEWERS,
                    subject_object=group_laui,
                )
            )
            for group_laui in user_groups
        ]

        results = await asyncio.gather(*queries)
        relation_tuples = [rt for resp in results for rt in resp.relation_tuples]
        relation_tuples = await self._remove_children_relations(relation_tuples)

        return SharedItemsResponse(
            item_nodes=[
                (ObjectId(rt.object), permission_relation_map[rt.relation])
                for rt in relation_tuples
            ],
            next_page_token="",
        )

    async def _remove_children_relations(
        self, relation_tuples: list[RelationTuple]
    ) -> list[RelationTuple]:
        """
        when we get the relations from the ory keto db then we get all the present relations
        but i need only those which are at top level , i want to eliminate the children
        so this function takes a list of item_laui / objects and return only those which are non related with each other.
        only true parent is involved here
        """

        objects = [rt.object for rt in relation_tuples]
        n = len(objects)
        if n == 0:
            return relation_tuples

        relation_tuples_to_check: list[RelationTuple] = []

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                relation_tuples_to_check.append(
                    RelationTuple(
                        namespace=Namespace.ITEM,
                        object=objects[i],
                        relation=Permission.IS_TRUE_PARENT,
                        subject_set=SubjectSet(
                            namespace=Namespace.ITEM, object=objects[j], relation=Permission.NONE
                        ),
                    )
                )

        results = await self.keto_client.batch_check_permissions(
            relation_tuples=relation_tuples_to_check
        )

        child_objects = set()

        for is_child, index in enumerate(results):
            if is_child:
                child_objects.add(relation_tuples_to_check[index].object)

        return [rt for rt in relation_tuples if rt.object not in child_objects]

    async def get_permission(
        self,
        item_laui: str,
        user_laui: str | None = None,
        group_laui: str | None = None,
        true_parent_permission: Permission | None = None,
    ):
        """
        if true_parent_permission is passed then we dont need to recursively check the item's access
        we know item atleast has access that it's true parent has
        """
        # checking_own_access = not group_laui and (not user_laui or user_laui == get_user_laui())
        if user_laui == get_root_user_laui():
            return Permission.OWN

        def make_tuple(perm: Permission) -> RelationTuple:
            rt = RelationTuple(
                namespace=Namespace.ITEM,
                object=item_laui,
                relation=perm,
                subject_id=user_laui,
            )
            if group_laui:
                rt.subject_id = None
                rt.subject_set = SubjectSet(
                    namespace=Namespace.GROUP, relation=Relation.NONE, object=group_laui
                )
            return rt

        all_permissions = [Permission.OWN, Permission.EDIT, Permission.VIEW]

        if true_parent_permission:
            # Only check permissions higher than what parent already gives
            parent_index = all_permissions.index(true_parent_permission)
            permissions_to_check = all_permissions[:parent_index]
            if not permissions_to_check:
                return true_parent_permission
        else:
            permissions_to_check = all_permissions

        results = await self.keto_client.batch_check_permissions(
            relation_tuples=[make_tuple(p) for p in permissions_to_check]
        )

        for perm, result in zip(permissions_to_check, results, strict=False):
            if result:
                return perm

        return true_parent_permission if true_parent_permission else Permission.NONE

    async def batch_check_permissions_aliter(
        self, item_lauis_with_permissions: list[tuple[PydanticObjectId, Permission]], user_laui: str
    ) -> list[bool]:
        return await self.keto_client.batch_check_permissions(
            relation_tuples=[
                RelationTuple(
                    namespace=Namespace.ITEM,
                    object=str(item_laui),
                    relation=permission,
                    subject_id=user_laui,
                )
                for item_laui, permission in item_lauis_with_permissions
            ]
        )

    async def batch_check_permissions(
        self, permission_to_check: Permission, item_lauis: list[PydanticObjectId], user_laui: str
    ) -> list[bool]:
        return await self.keto_client.batch_check_permissions(
            relation_tuples=[
                RelationTuple(
                    namespace=Namespace.ITEM,
                    object=str(item_laui),
                    relation=permission_to_check,
                    subject_id=user_laui,
                )
                for item_laui in item_lauis
            ]
        )

    async def get_permissions_map(
        self,
        item_lauis_with_true_parent_permission: list[tuple[PydanticObjectId, Permission]],
        user_laui: str,
    ) -> dict[PydanticObjectId, Permission]:
        "Returns item_id and what permssion user_laui has for that item"

        permission_map = {
            item_laui: true_parent_permission
            for item_laui, true_parent_permission in item_lauis_with_true_parent_permission
        }

        permissions = [Permission.OWN, Permission.EDIT, Permission.VIEW]

        def _check_needed(true_parent_permission: Permission, current_permission: Permission):
            if not true_parent_permission:
                return True
            return permissions.index(true_parent_permission) > permissions.index(current_permission)

        for permission in permissions:
            item_lauis_included_for_check = []

            relation_tuples_included_for_check = []

            item_lauis_with_true_parent_permission = [
                (item_laui, true_parent_permission)
                for item_laui, true_parent_permission in item_lauis_with_true_parent_permission
                if true_parent_permission != permission
            ]

            for item_laui, true_parent_permission in item_lauis_with_true_parent_permission:
                if _check_needed(true_parent_permission, permission):
                    relation_tuples_included_for_check.append(
                        RelationTuple(
                            namespace=Namespace.ITEM,
                            object=str(item_laui),
                            subject_id=user_laui,
                            relation=permission,
                        )
                    )
                    item_lauis_included_for_check.append(item_laui)

            check_results = await self.keto_client.batch_check_permissions(
                relation_tuples=relation_tuples_included_for_check
            )

            item_lauis_check_done = []
            for is_allowed, item_laui in zip(check_results, item_lauis_included_for_check):
                if is_allowed:
                    permission_map[item_laui] = permission
                    item_lauis_check_done.append(item_laui)

            item_lauis_with_true_parent_permission = [
                (item_laui, true_parent_permission)
                for item_laui, true_parent_permission in item_lauis_with_true_parent_permission
                if item_laui not in item_lauis_check_done
            ]

        return permission_map

    async def get_user_group_relation(self, user_laui: str, group_laui: str) -> Relation:
        if is_root_user():
            return Relation.OWNERS

        relations = [Relation.OWNERS, Relation.EDITORS, Relation.VIEWERS]

        results = await self.keto_client.batch_check_permissions(
            relation_tuples=[
                RelationTuple(
                    namespace=Namespace.GROUP,
                    object=group_laui,
                    relation=rel,
                    subject_id=user_laui,
                )
                for rel in relations
            ]
        )

        for rel, result in zip(relations, results, strict=False):
            if result:
                return rel

        return Relation.NONE

    async def get_all_access_relations(
        self, user_laui: str, request: GetAccessRelationsRequest
    ) -> GetAccessRelationsResponse:

        if is_root_user():
            return await self._get_all_access_relations_root(request)

        user_groups = (await self.get_user_groups(user_laui=user_laui)).groups

        own_direct_resp, edit_direct_resp, *group_resps = await asyncio.gather(
            self.keto_client.get_relations(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    relation=Relation.OWNERS,
                    subject_id=user_laui,
                )
            ),
            self.keto_client.get_relations(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    relation=Relation.EDITORS,
                    subject_id=user_laui,
                )
            ),
            *[
                self.keto_client.get_relations(
                    relation_tuple=RelationTupleParams(
                        namespace=Namespace.ITEM,
                        relation=Relation.OWNERS,
                        subject_relation=Relation.OWNERS,
                        subject_namespace=Namespace.GROUP,
                        subject_object=group_laui,
                    )
                )
                for group_laui in user_groups
            ],
            *[
                self.keto_client.get_relations(
                    relation_tuple=RelationTupleParams(
                        namespace=Namespace.ITEM,
                        relation=Relation.EDITORS,
                        subject_relation=Relation.OWNERS,
                        subject_namespace=Namespace.GROUP,
                        subject_object=group_laui,
                    )
                )
                for group_laui in user_groups
            ],
        )
        own_root_rels = own_direct_resp.relation_tuples
        edit_root_rels = edit_direct_resp.relation_tuples
        n_groups = len(user_groups)
        for _i, resp in enumerate(group_resps[:n_groups]):
            own_root_rels.extend(resp.relation_tuples)
        for _i, resp in enumerate(group_resps[n_groups:]):
            edit_root_rels.extend(resp.relation_tuples)
        all_entry_points = own_root_rels + edit_root_rels
        top_level_entry_points = await self._remove_children_relations(all_entry_points)

        user_item_lauis = []
        for rt in top_level_entry_points:
            link = (
                await self.link_repo.find_links(
                    {"child_laui": PydanticObjectId(rt.object)}, limit=1
                )
            )[0]
            true_children_links = await self.link_repo.children_links_lookup(
                link_laui=PydanticObjectId(link.laui), true_parent=True
            )
            for link in true_children_links:
                user_item_lauis.append(str(link.child_laui))

        res = GetAccessRelationsResponse(
            access_relations=[],
            next_page_token=request.page_token,
            skip=request.skip,
        )
        relation = permission_relation_map[request.permission]

        while len(res.access_relations) <= request.per_page and res.next_page_token != "":
            relation_tuples_res = await self.keto_client.get_relations(
                relation_tuple=RelationTupleParams(
                    namespace=Namespace.ITEM,
                    relation=relation,
                    page_token=res.next_page_token,
                )
            )

            relation_tuples = relation_tuples_res.relation_tuples

            if res.skip > 0:
                relation_tuples = relation_tuples[res.skip :]

            for index, rt in enumerate(relation_tuples):
                if len(res.access_relations) == request.per_page:
                    res.skip = index
                    return res

                if rt.object in user_item_lauis:
                    new_relation = AccessRelation(
                        item_laui=rt.object,
                        subject_laui=(rt.subject_id if rt.subject_id else rt.subject_set.object),
                        subject_type="user" if rt.subject_id else "group",
                        subject_permission=permission_relation_map[rt.relation],
                    )
                    res.access_relations.append(new_relation)

            res.next_page_token = relation_tuples_res.next_page_token
            res.skip = 0

        return res

    async def _get_all_access_relations_root(
        self, request: GetAccessRelationsRequest
    ) -> GetAccessRelationsResponse:

        relation = permission_relation_map[request.permission]

        relation_tuples_resp = await self.keto_client.get_relations(
            RelationTupleParams(namespace=Namespace.ITEM, relation=relation)
        )

        relation_tuples = relation_tuples_resp.relation_tuples

        return GetAccessRelationsResponse(
            access_relations=[
                AccessRelation(
                    item_laui=rt.object,
                    subject_laui=(rt.subject_id if rt.subject_id else rt.subject_set.object),
                    subject_type="user" if rt.subject_id else "group",
                    subject_permission=permission_relation_map[rt.relation],
                    item_permission=Permission.OWN,
                )
                for rt in relation_tuples
            ],
            next_page_token=relation_tuples_resp.next_page_token,
            skip=0,
        )

    async def get_user_groups(
        self, user_laui: str, relation: Relation | None = None
    ) -> GroupsRawResponse:

        if is_root_user():
            if relation == Relation.OWNERS:
                resp = await self.keto_client.get_relations(
                    relation_tuple=RelationTupleParams(namespace=Namespace.GROUP)
                )
                return GroupsRawResponse(
                    groups=[rt.object for rt in resp.relation_tuples],
                    next_page_token=resp.next_page_token,
                )
            return GroupsRawResponse(groups=[], next_page_token="")

        resp = await self.keto_client.get_relations(
            relation_tuple=RelationTupleParams(
                namespace=Namespace.GROUP,
                relation=relation,
                subject_id=user_laui,
            )
        )
        return GroupsRawResponse(
            groups=[rt.object for rt in resp.relation_tuples],
            next_page_token=resp.next_page_token,
        )


def get_access_reader(request: Request) -> AccessReader:
    return request.app.state.access_reader
