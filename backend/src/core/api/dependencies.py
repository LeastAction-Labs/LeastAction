from fastapi import Depends, HTTPException, Request

from src.common.context_vars.user_context import get_user_laui
from src.core.catalog.api_request import BaseCreateItemRequest
from src.core.ee.keto.access_reader import AccessReader, get_access_reader
from src.core.ee.keto.schema import Permission
from src.core.task.action.schema import Actions


async def validate_access_for_create_run(
    api_request: Request,
    request: BaseCreateItemRequest,
    access_reader: AccessReader = Depends(get_access_reader),
):

    task_api = True if api_request.url.path.startswith("/api/v1/task") else False

    keys = ["operator_laui", "connection_laui", "payload_laui"] if task_api else ["connection_laui"]
    keys.append("parent_laui")

    item_lauis_with_permissions = []
    item_laui_passed = False
    if hasattr(request, "item_laui"):
        item_laui_permission = Permission.EDIT if task_api else Permission.VIEW
        item_lauis_with_permissions.append((request.item_laui, item_laui_permission))
        item_laui_passed = True

    for key in keys:
        if hasattr(request, key):
            if not item_laui_passed and key == "parent_laui":
                item_lauis_with_permissions.append((getattr(request, key), Permission.EDIT))
            item_lauis_with_permissions.append((getattr(request, key), Permission.VIEW))

    if task_api and hasattr(request, "actions"):
        actions = (
            Actions(**request.actions) if isinstance(request.actions, dict) else request.actions
        )
        for action_list in [
            actions.pre_actions,
            actions.create_actions,
            actions.running_actions,
            actions.post_actions,
        ]:
            for action in action_list:
                item_lauis_with_permissions.append((action.laui, Permission.VIEW))

    item_access = await access_reader.batch_check_permissions_aliter(
        item_lauis_with_permissions=item_lauis_with_permissions,
        user_laui=get_user_laui(),
    )

    for (item_laui, _), access in zip(item_lauis_with_permissions, item_access):
        if not access:
            raise HTTPException(
                status_code=403, detail={"message": f"Unauthorized for item {item_laui}"}
            )

    return request
