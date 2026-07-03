# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import AuthorizationError
from src.core.catalog.item.schema import CreateItem, Item
from src.core.ee.keto.access_reader import AccessReader
from src.core.ee.keto.schema import Permission
from src.core.task.action.schema import Actions


class PermissionManager:
    def __init__(self, access_reader: AccessReader):
        self.access_reader = access_reader

    async def check_permission_for_update_item(self, new_item: CreateItem, existing_item: Item):
        if new_item.access_patch.add.owners or new_item.access_patch.remove.owners:
            await self.access_reader.check_item_own_access(
                item_laui=str(existing_item.laui), user_laui=get_user_laui()
            )
            return
        await self.access_reader.check_item_edit_access(
            item_laui=str(existing_item.laui), user_laui=get_user_laui()
        )

    async def check_permission_for_create_item(self, item: CreateItem):

        item_lauis_with_permissions = [("parent_laui", Permission.EDIT)]
        if item.item_type == "task":
            item_lauis_with_permissions.extend(
                [
                    (item.operator_laui, Permission.EDIT),
                    (item.connection_laui, Permission.EDIT),
                ]
            )
            if getattr(item, "payload_laui", None):
                item_lauis_with_permissions.append((item.payload_laui, Permission.VIEW))

            if hasattr(item, "actions"):
                actions = (
                    Actions(**item.actions) if isinstance(item.actions, dict) else item.actions
                )
                for action_list in [
                    actions.pre_actions,
                    actions.create_actions,
                    actions.running_actions,
                    actions.post_actions,
                ]:
                    for action in action_list:
                        item_lauis_with_permissions.append((action.laui, Permission.VIEW))

        if item.item_type == "action":
            item_lauis_with_permissions.append((item.connection_laui, Permission.EDIT))

        item_access = await self.access_reader.batch_check_permissions_aliter(
            item_lauis_with_permissions, get_user_laui()
        )
        for (item_laui, _), access in zip(item_lauis_with_permissions, item_access):
            if not access:
                raise AuthorizationError(f"Unauthorized for item {item_laui}")

    async def build_permission_map(
        self, links: list, parent_or_child: str, inherited_item_permission: Permission
    ) -> dict[PydanticObjectId, Permission]:
        item_lauis_with_true_parent_permission = []
        for link in links:
            if parent_or_child == "child":
                true_parent_permission = inherited_item_permission if link.true_parent else None
                item_lauis_with_true_parent_permission.append(
                    (link.child_laui, true_parent_permission)
                )
            else:
                if not link.parent_laui:
                    continue
                item_lauis_with_true_parent_permission.append((link.parent_laui, Permission.NONE))
        permission_map = await self.access_reader.get_permissions_map(
            item_lauis_with_true_parent_permission=item_lauis_with_true_parent_permission,
            user_laui=get_user_laui(),
        )
        return permission_map
