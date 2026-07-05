# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import re
from typing import Any

from bson import ObjectId
from fastapi import Request
from pydantic import ValidationError
from pydantic_core import PydanticUndefined
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.catalog_context import get_schema_manager
from src.common.context_vars.user_context import get_user_laui, is_root_user
from src.common.exceptions import (
    ConflictError,
    InvalidArgumentError,
    LAException,
    NotFoundError,
    UnprocessableEntityError,
)
from src.common.utils import check_differing_keys
from src.core.api.common import PaginationResponse
from src.core.catalog.api_request import (
    BaseCreateItemRequest,
    CreateLinkRequest,
    DeleteItemRequest,
    GetItemRevisionsRequest,
    GetItemRevisionsResponse,
    GetItemsFilter,
    GetItemsResponse,
    ItemDirectoryItemNode,
    SearchItemsResponse,
    SearchLinksResponse,
    SearchRequest,
)
from src.core.catalog.config.constants_mappers import immutable_system_fields, mutable_system_fields
from src.core.catalog.config.schema.schema_manager import SchemaManager
from src.core.catalog.item.repo import ItemRepository
from src.core.catalog.item.schema import CreateItem, Item, ItemProjection, UpdateItem
from src.core.catalog.item_directory import ItemDirectory, ItemDirectoryItemNode
from src.core.catalog.item_revision.repo import ItemRevisionRepository
from src.core.catalog.item_revision.schema import CreateItemRevision
from src.core.catalog.link.repo import LinkRepository
from src.core.catalog.link.schema import CreateLink, Link, LinkWithPermission
from src.core.catalog.utils.item_types.schema import ItemCategory
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.catalog.utils.permissions import PermissionManager
from src.core.db.transaction import transactional
from src.core.ee.keto.access_reader import AccessReader
from src.core.ee.keto.schema import Permission
from src.core.task.schema import Task


class CatalogService:
    def __init__(
        self,
        item_repo: ItemRepository,
        link_repo: LinkRepository,
        item_revision_repo: ItemRevisionRepository,
        access_reader: AccessReader,
        item_types_manager: ItemTypesManager,
    ):
        self.item_repo = item_repo
        self.link_repo = link_repo
        self.item_revision_repo = item_revision_repo
        self.item_types_manager = item_types_manager
        self.access_reader = access_reader
        self.permission_manager: PermissionManager = PermissionManager(access_reader=access_reader)

    async def find_existing_item_by_pk(self, item: BaseCreateItemRequest) -> Item | None:
        schema_manager = self._get_schema_manager(item.item_type)
        pk = self._build_pk(item, schema_manager)
        try:
            return await self.item_repo.get_item_by_pk(item_pk=pk)
        except NotFoundError:
            return None

    def _get_schema_manager(self, item_type: str):
        item_type_for_schema = item_type.split(".")[0]
        return get_schema_manager(item_type_for_schema)

    def _build_pk(self, item: Any, schema_manager: SchemaManager) -> str:
        item_type_for_schema = item.item_type.split(".")[0]
        pk_values = []
        for key in sorted(schema_manager.primary_keys):
            if key == "item_type":
                pk_values.append(item_type_for_schema)
            elif hasattr(item, key):
                pk_values.append(getattr(item, key))
            else:
                field_info = schema_manager.CreateItemRequest_model.model_fields.get(key)
                if field_info is None:
                    pk_values.append(None)
                elif field_info.default_factory is not None:
                    pk_values.append(field_info.default_factory())
                elif field_info.default is not PydanticUndefined:
                    pk_values.append(field_info.default)
                else:
                    pk_values.append(None)
        return "-".join(str(value) for value in pk_values)

    def validate_item_schema(
        self, item_request: BaseCreateItemRequest, exclude_unset: bool = False
    ) -> CreateItem:
        schema_manager = self._get_schema_manager(item_request.item_type)
        try:
            item = item_request.model_dump()
            CreateItemRequest = schema_manager.CreateItemRequest_model
            CreateItemRequest.model_validate(item)
            if exclude_unset:
                return CreateItem(**(CreateItemRequest(**item).model_dump(exclude_unset=True)))
            return CreateItem(**(CreateItemRequest(**item).model_dump()))
        except ValidationError as e:
            errors = schema_manager.get_validation_error_message(validation_error=e)
            raise UnprocessableEntityError(
                message="The request body contains invalid or missing fields", detail=errors
            )

    def _get_projection_fields(self, item_type: str | None = None):
        if not item_type:
            return {
                "name": 1,
                "item_type": 1,
                "description": 1,
                "project_laui": 1,
                "parent_laui": 1,
            }
        schema_manager = self._get_schema_manager(item_type)
        return dict.fromkeys(list(schema_manager.projection_fields), 1)

    @transactional
    async def create_item(self, item: CreateItem) -> PydanticObjectId:
        item.pk = self._build_pk(
            item=item, schema_manager=self._get_schema_manager(item_type=item.item_type)
        )
        await self.permission_manager.check_permission_for_create_item(item)
        if item.is_root:
            return await self._create_root_item(item=item)
        return await self._create_linkable_item(item=item)

    async def _create_root_item(self, item: CreateItem) -> PydanticObjectId:
        if item.item_type != "folder.account" or (await self.item_repo.get_account_laui()):
            raise UnprocessableEntityError(
                message="Invalid root item",
                detail="Only 'folder.account' can be a root item, and you can only have one root item total.",
            )
        item.access_patch.add.owners = {f"U{get_user_laui()}": ""}
        item_laui = await self.item_repo.create_item(item)
        link = CreateLink(child_laui=item_laui, child_type=item.item_type, true_parent=True)
        await self.link_repo.create_link(link)
        return item_laui

    async def _create_linkable_item(self, item: CreateItem) -> PydanticObjectId:
        item_laui = await self.item_repo.create_item(item)
        parent_item_projection: ItemProjection = await self.item_repo.get_item_projection(
            item_laui=item.parent_laui
        )
        parent_item_type = parent_item_projection.item_type
        await self._ensure_parent_supports_item_type(
            item_type=item.item_type, parent_item_type=parent_item_type
        )
        link = CreateLink(
            child_laui=item_laui,
            parent_laui=item.parent_laui,
            child_type=item.item_type,
            parent_type=parent_item_type,
            true_parent=True,
        )
        await self.link_repo.create_link(link)
        if item.item_type == "task":
            await self._link_task_and_its_paramaters(item=item, item_laui=item_laui)
        return item_laui

    async def _ensure_parent_supports_item_type(self, item_type: str, parent_item_type: str):

        allowed_item_types = self.item_types_manager.get_supported_item_types(parent_item_type)
        for supported_item_type in allowed_item_types:
            if item_type == supported_item_type or item_type.startswith(supported_item_type + "."):
                return

        error = {
            "message": "invalid item_type for the passed parent_laui",
            "item_type_passed": item_type,
            "allowed_item_types": allowed_item_types,
        }

        raise UnprocessableEntityError(message="Invalid item type for parent", detail=error)

    @transactional
    async def update_existing_item(
        self, existing_item: Item, new_item: CreateItem
    ) -> PydanticObjectId:

        if existing_item.deleted_at:
            raise ConflictError(
                message="Item is in the trash",
                detail="An item with the same primary keys already exists in the trash. Please rename your new item or restore the existing one.",
            )

        schema_manager = self._get_schema_manager(existing_item.item_type)

        await self.permission_manager.check_permission_for_update_item(
            new_item=new_item, existing_item=existing_item
        )

        item_revision_created = await self._create_item_revision(
            version_fields=schema_manager.version_fields,
            new_item=new_item,
            existing_item=existing_item,
        )

        update_item_dict = await self._get_update_item_dict(
            new_item=new_item, existing_item=existing_item, schema_manager=schema_manager
        )
        update_item = UpdateItem(**update_item_dict)
        await self.item_repo.update_item(update_item, versioning_required=item_revision_created)

        return existing_item.laui

    async def _create_item_revision(
        self, version_fields: set[str], new_item: CreateItem, existing_item: Item
    ):
        versioning_required = False
        if not version_fields:
            versioning_required = True
        else:
            differing_keys = check_differing_keys(new_item.model_dump(), existing_item.model_dump())
            if differing_keys & version_fields:
                versioning_required = True

        if versioning_required:
            item_revision = CreateItemRevision(
                **existing_item.model_dump(
                    exclude={"created_at", "updated_at", "laui", "deleted_at", "item_laui"}
                ),
                item_laui=existing_item.laui,
            )
            await self.item_revision_repo.create_item_revision(item_revision)

        return versioning_required

    async def _get_update_item_dict(
        self, new_item: CreateItem, existing_item: Item, schema_manager: SchemaManager
    ):

        system_update_fields = schema_manager.system_update_fields
        user_update_fields = schema_manager.user_update_fields

        system_only_fields = system_update_fields - user_update_fields
        fields_to_exclude = (
            set(immutable_system_fields) | system_only_fields | schema_manager.primary_keys
        )
        new_item_dict = new_item.model_dump(exclude_unset=True, exclude=fields_to_exclude)

        existing_item_dict = existing_item.model_dump()

        changed_fields = {}
        for field, new_value in new_item_dict.items():
            existing_value = existing_item_dict.get(field)
            if new_value != existing_value:
                changed_fields[field] = new_value

        if user_update_fields:
            user_update_fields.update(mutable_system_fields)
            forbidden_fields = set(changed_fields.keys()) - user_update_fields
            if forbidden_fields:
                raise UnprocessableEntityError(
                    message="Cannot update protected fields",
                    detail=f"You are trying to update fields that are locked: {', '.join(forbidden_fields)}. Only these fields can be changed: {', '.join(sorted(user_update_fields))}.",
                )

        update_dict = existing_item.model_dump()
        update_dict.update(changed_fields)

        update_dict["updated_by"] = PydanticObjectId(get_user_laui())

        return update_dict

    async def find_item(self, item_laui: PydanticObjectId, include_deleted: bool = False) -> Item:
        item = await self.item_repo.get_item(item_laui=item_laui, include_deleted=include_deleted)
        item.supported_types = self.item_types_manager.get_supported_item_types(item.item_type)
        item.permission = await self.access_reader.get_permission(
            item_laui=str(item_laui), user_laui=get_user_laui()
        )
        return item

    async def safe_find_item(
        self, item_laui: PydanticObjectId, include_deleted: bool = False
    ) -> tuple[Item | None, Exception | None]:
        try:
            item = await self.find_item(item_laui=item_laui, include_deleted=include_deleted)
            return item, None
        except LAException as e:
            return None, e
        except Exception as e:
            return None, e

    @transactional
    async def find_items(self, request: GetItemsFilter) -> GetItemsResponse:
        offset = (request.page - 1) * request.per_page
        limit = request.per_page

        if (request.sort_by or request.filter_state) and not request.is_root:
            return await self._find_items_with_sort_or_filter(
                request=request,
                offset=offset,
                limit=limit,
            )

        return await self._find_items_paginated(
            request=request,
            offset=offset,
            limit=limit,
        )

    async def _find_items_with_sort_or_filter(
        self,
        request: GetItemsFilter,
        offset: int,
        limit: int,
    ) -> GetItemsResponse:
        permission = await self.access_reader.get_permission(
            item_laui=str(request.item_laui), user_laui=get_user_laui()
        )

        item_filter = {
            "parent_laui": request.item_laui,
            "deleted_at": None,
            "item_type": request.item_type,
        }
        if request.filter_state:
            item_filter["state"] = request.filter_state

        sorted_items = await self.item_repo.find_items(
            filter=item_filter,
            projections=self._get_projection_fields(request.item_type),
            offset=offset,
            limit=limit,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
        has_next = await self.item_repo.check_next_page_exists(
            filter=item_filter, offset=offset, limit=limit
        )

        self.item_types_manager.attach_supported_item_types(sorted_items)

        for item in sorted_items:
            item.permission = permission

        return GetItemsResponse(
            items=[ItemDirectoryItemNode(item=item) for item in sorted_items],
            pagination=PaginationResponse(
                current_page=request.page,
                per_page=request.per_page,
                has_next=has_next,
            ),
        )

    async def _find_items_paginated(
        self,
        request: GetItemsFilter,
        offset: int,
        limit: int,
    ) -> GetItemsResponse:
        """
        Paginate at the link level (cheap) — only one page of links is fetched at a time.
        """
        next_page_token = None
        has_next = False

        if request.is_root:
            request.parent_or_child = "child"
            if is_root_user():
                filtered_nodes = [
                    (PydanticObjectId(await self.item_repo.get_account_laui()), Permission.OWN)
                ]
            else:
                response = await self.access_reader.get_shared_items(
                    user_laui=get_user_laui(),
                    page_token=request.page_token,
                    page_size=limit,
                )
                next_page_token = response.next_page_token
                has_next = bool(next_page_token)
                filtered_nodes = response.item_nodes
        else:
            link_filters = self._get_link_filters(
                item_type=request.item_type,
                parent_or_child=request.parent_or_child,
                item_laui=request.item_laui,
            )
            filtered_links = await self.link_repo.find_links(
                filter=link_filters, offset=offset, limit=limit
            )
            permission_map = await self.permission_manager.build_permission_map(
                links=filtered_links,
                inherited_item_permission=request.item_permission,
                parent_or_child=request.parent_or_child,
            )
            filtered_nodes = [
                (item_laui, permission) for item_laui, permission in permission_map.items()
            ]
            has_next = await self.link_repo.check_next_page_exists(
                filter=link_filters, offset=offset, limit=limit
            )

        if not filtered_nodes:
            return self._empty_response()

        filtered_items = await self._find_heirarchy_items(filtered_nodes, request=request)

        return GetItemsResponse(
            items=filtered_items,
            pagination=PaginationResponse(
                current_page=request.page,
                per_page=request.per_page,
                has_next=has_next,
                next_page_token=next_page_token,
            ),
        )

    def _get_link_filters(self, parent_or_child: str, item_laui: str, item_type: str | None = None):
        link_filters = {}
        if parent_or_child == "parent":
            link_filters["child_laui"] = item_laui
            link_filters["true_parent"] = True
        else:
            link_filters["parent_laui"] = item_laui
            if item_type:
                link_filters["child_type"] = {"$regex": f"^{re.escape(item_type)}(\\.|$)"}
        return link_filters

    async def _find_heirarchy_items(
        self, item_nodes: list[tuple[PydanticObjectId, Permission]], request: GetItemsFilter
    ) -> list[ItemDirectoryItemNode]:
        item_directory = ItemDirectory(root_nodes=item_nodes)

        for i in range(request.depth):
            links_with_permission: list[LinkWithPermission] = []

            for item_laui, item_permission in item_nodes:
                link_filters = self._get_link_filters(
                    parent_or_child=request.parent_or_child,
                    item_laui=item_laui,
                    item_type=request.item_type,
                )

                links = await self.link_repo.find_links(filter=link_filters)

                permission_map = await self.permission_manager.build_permission_map(
                    links=links,
                    parent_or_child=request.parent_or_child,
                    inherited_item_permission=item_permission,
                )

                for link, (_, permission) in zip(links, permission_map.items()):
                    links_with_permission.append(
                        LinkWithPermission(**link.model_dump(), permission=permission)
                    )

            if request.parent_or_child == "parent":
                item_directory.add_parent_level(links_with_permission)
                item_nodes = [(link.parent_laui, link.permission) for link in links_with_permission]
            else:
                item_directory.add_child_level(links_with_permission)
                item_nodes = [(link.child_laui, link.permission) for link in links_with_permission]

        flattened_item_lauis = item_directory.get_flattened_lauis()
        heirarchy_items_list = await self.item_repo.find_items(
            filter={"_id": {"$in": list(flattened_item_lauis)}},
            projections=self._get_projection_fields(request.item_type),
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
        self.item_types_manager.attach_supported_item_types(heirarchy_items_list)
        items = []
        try:
            items = item_directory.fill_items(
                {PydanticObjectId(item.laui): item for item in heirarchy_items_list}
            )
        except Exception:
            pass
        return items

    async def find_multiple_items_by_laui(
        self,
        item_lauis: list[PydanticObjectId],
        projections: dict[str, int],
        include_deleted: bool = False,
    ) -> list[ItemProjection]:

        return await self.item_repo.get_multiple_items_by_laui(
            item_lauis=item_lauis, projections=projections, include_deleted=include_deleted
        )

    async def search(self, request: SearchRequest):
        offset = (request.pagination.page - 1) * request.pagination.per_page
        limit = request.pagination.per_page

        if request.item_filter:
            filter = request.item_filter.get_item_filters

            items = await self.item_repo.find_items(
                filter=filter, projections=request.projections_dict, offset=offset, limit=limit
            )

            has_next = await self.item_repo.check_next_page_exists(
                filter=filter, offset=offset, limit=limit
            )

            return SearchItemsResponse(
                items=items,
                pagination=PaginationResponse(
                    current_page=request.pagination.page,
                    per_page=request.pagination.per_page,
                    has_next=has_next,
                ),
            )
        else:
            filter = request.link_filter.get_link_filters
            links = await self.link_repo.find_links(filter=filter, offset=offset, limit=limit)
            has_next = await self.link_repo.check_next_page_exists(
                filter=filter, offset=offset, limit=limit
            )
            return SearchLinksResponse(
                links=links,
                pagination=PaginationResponse(
                    current_page=request.pagination.page,
                    per_page=request.pagination.per_page,
                    has_next=has_next,
                ),
            )

    async def get_item_revisions(
        self, request: GetItemRevisionsRequest
    ) -> GetItemRevisionsResponse:
        if request.version:
            item_revision = await self.item_revision_repo.get_item_revision(
                item_laui=request.item_laui, version=request.version
            )
            return GetItemRevisionsResponse(item_revision=item_revision)
        item_projection: ItemProjection = await self.item_repo.get_item_projection(
            item_laui=request.item_laui
        )
        item_type = item_projection.item_type
        schema_manager = self._get_schema_manager(item_type)
        item_revisions = await self.item_revision_repo.get_item_revisons(
            item_laui=request.item_laui, projection_fields=schema_manager.projection_fields
        )
        return GetItemRevisionsResponse(item_revisions=item_revisions)

    @transactional
    async def delete_item(self, request: DeleteItemRequest):
        item_laui = request.item_laui
        parent_laui = request.parent_laui
        trash_folder_laui = await self.item_repo.get_trash_folder_laui()
        if item_laui == trash_folder_laui:
            raise ConflictError(
                message="Action not allowed", detail="You cannot delete the system trash folder."
            )
        link = await self.link_repo.get_link_by_pk(parent_laui=parent_laui, child_laui=item_laui)

        if parent_laui == trash_folder_laui or request.hard_delete:
            children_links = await self.link_repo.children_links_lookup(
                link_laui=ObjectId(link.laui)
            )

            soft_children_links: list[Link] = []
            hard_children_links: list[Link] = []
            for link in children_links:
                if link.true_parent:
                    hard_children_links.append(link)
                else:
                    soft_children_links.append(link)

            hard_children_item_lauis = [link.child_laui for link in hard_children_links]

            parent_links = await self.link_repo.find_links({"child_laui": item_laui})
            hard_children_links += await self.link_repo.find_links(
                {"child_laui": {"$in": hard_children_item_lauis}, "true_parent": False}
            )
            hard_children_links = list(set(hard_children_links))
            links_to_be_deleted = hard_children_links + soft_children_links + parent_links
            await self.link_repo.delete_links(
                link_lauis=[ObjectId(link.laui) for link in links_to_be_deleted]
            )
            items_lauis_to_delete = hard_children_item_lauis + [item_laui]
            await self.item_repo.hard_delete_items(items_lauis=items_lauis_to_delete)
            return
        if link.true_parent:
            hard_links = await self.link_repo.children_links_lookup(
                link_laui=ObjectId(link.laui), true_parent=True
            )
            items_to_be_soft_deleted = [link.child_laui for link in hard_links]
            items_to_be_soft_deleted.append(item_laui)
            links_to_be_deleted = await self.link_repo.find_links(
                {"child_laui": {"$in": items_to_be_soft_deleted}, "true_parent": False}
            )
            links_to_be_deleted.append(link)
            await self.item_repo.soft_delete_items(item_lauis=items_to_be_soft_deleted)
            await self.link_repo.delete_links(
                link_lauis=[ObjectId(link.laui) for link in links_to_be_deleted]
            )
            await self.link_repo.create_link(
                CreateLink(
                    parent_laui=trash_folder_laui,
                    child_laui=item_laui,
                    true_parent=True,
                    child_type=link.child_type,
                    parent_type="folder.trash",
                )
            )
            return
        await self.link_repo.delete_links(link_lauis=[ObjectId(link.laui)])

    @transactional
    async def restore_item(self, item_laui: PydanticObjectId):
        trash_folder_laui = await self.item_repo.get_trash_folder_laui()

        link = await self.link_repo.get_link_by_pk(
            parent_laui=trash_folder_laui, child_laui=item_laui
        )
        item = await self.item_repo.get_item(item_laui, include_deleted=True)
        parent_item = await self.item_repo.get_item(item.parent_laui)
        hard_links = await self.link_repo.children_links_lookup(
            link_laui=ObjectId(link.laui), true_parent=True
        )
        items_to_be_restored = [link.child_laui for link in hard_links]
        items_to_be_restored.append(item_laui)
        await self.item_repo.restore_items(item_lauis=items_to_be_restored)
        await self.link_repo.delete_links(link_lauis=[ObjectId(link.laui)])
        await self.link_repo.create_link(
            CreateLink(
                parent_laui=item.parent_laui,
                child_laui=item_laui,
                true_parent=True,
                child_type=item.item_type,
                parent_type=parent_item.item_type,
            )
        )

    @transactional
    async def update_task_item(
        self, task_laui: PydanticObjectId, update_fields: dict
    ) -> PydanticObjectId:
        # Ensure task_laui is ObjectId
        task_laui = ObjectId(task_laui) if not isinstance(task_laui, ObjectId) else task_laui

        existing_task = await self.find_item(task_laui)
        if existing_task.item_type != "task":
            raise UnprocessableEntityError(
                message="Invalid type",
                detail=f"Expected an item type of 'task', but received '{existing_task.item_type}' instead.",
            )

        # Initialize schema manager for task
        schema_manager = self._get_schema_manager("task")

        # Validate against system_update_fields if defined
        system_update_fields = schema_manager.system_update_fields
        if system_update_fields is not None:
            forbidden_fields = set(update_fields.keys()) - system_update_fields
            if forbidden_fields:
                raise UnprocessableEntityError(
                    message="Cannot update fields via task API",
                    detail=f"The following fields are locked for updates: {', '.join(forbidden_fields)}. You can only update: {', '.join(sorted(system_update_fields))}.",
                )

        # If user requests cancel and task is not in an active state, immediately mark as cancelled
        if update_fields.get("user_set_state") == "cancel":
            current_state = existing_task.model_dump().get("state")
            active_states = {"queued_for_connection", "queued_in_redis", "running"}
            if current_state not in active_states:
                update_fields["state"] = "cancelled"

        # Build update dictionary
        update_dict = existing_task.model_dump()
        update_dict.update(update_fields)

        # Set required fields for UpdateItem
        update_dict["laui"] = existing_task.laui
        update_dict["version"] = existing_task.version
        update_dict["updated_by"] = PydanticObjectId(get_user_laui())

        # Remove fields that shouldn't be in UpdateItem
        for field in ["created_at", "updated_at", "deleted_at", "access"]:
            update_dict.pop(field, None)

        # Handle access_patch
        if "access_patch" in update_dict and update_dict["access_patch"] is None:
            del update_dict["access_patch"]

        # Create UpdateItem and call repo directly
        update_item = UpdateItem(**update_dict)
        await self.item_repo.update_item(update_item, versioning_required=False)

        return existing_task.laui

    @transactional
    async def batch_update_task_items(
        self, task_lauis: list[PydanticObjectId], update_fields: dict
    ) -> int:
        if not task_lauis:
            return 0

        # Ensure all task_lauis are ObjectId
        normalized_lauis = [
            ObjectId(laui) if not isinstance(laui, ObjectId) else laui for laui in task_lauis
        ]
        modified_count = await self.item_repo.batch_update_tasks(
            task_lauis=normalized_lauis, update_fields=update_fields
        )

        return modified_count

    async def create_link(self, link: CreateLinkRequest):
        parent_laui = link.parent_laui
        child_laui = link.child_laui

        trash_folder_laui = await self.item_repo.get_trash_folder_laui()
        if parent_laui == trash_folder_laui:
            raise InvalidArgumentError(
                message="Invalid parent folder",
                detail=f"The parent_laui '{parent_laui}' is the trash folder. You are not allowed to link directly inside the trash folder.",
            )

        parent_item_projection: ItemProjection = await self.item_repo.get_item_projection(
            parent_laui
        )
        parent_type = parent_item_projection.item_type
        child_item_projection: ItemProjection = await self.item_repo.get_item_projection(child_laui)
        child_type = child_item_projection.item_type

        try:
            parent_item_supported_types = self.item_types_manager.get_supported_item_types(
                item_type=parent_type, category=ItemCategory.NON_FOLDER
            )

            if not self.item_types_manager.check_item_type_compatible(
                item_type=child_type, supported_item_types=parent_item_supported_types
            ):
                raise InvalidArgumentError(
                    message="Item type compatibility mismatch",
                    detail=f"The child type '{child_type}' (LAUI: '{child_laui}') cannot fit under parent type '{parent_type}' (LAUI: '{parent_laui}'). Allowed types are: {parent_item_supported_types}.",
                )

            exisiting_link = await self.link_repo.get_link_by_pk(
                parent_laui=parent_laui, child_laui=child_laui
            )

            if exisiting_link.true_parent:
                raise InvalidArgumentError(
                    message="Link relationship conflict",
                    detail=f"A hard link already exists between parent_laui '{parent_laui}' and child_laui '{child_laui}'.",
                )
            else:
                raise InvalidArgumentError(
                    message="Link relationship conflict",
                    detail=f"A soft link already exists between parent_laui '{parent_laui}' and child_laui '{child_laui}'.",
                )

        except NotFoundError:
            link_laui = await self.link_repo.create_link(
                CreateLink(
                    parent_laui=parent_laui,
                    child_laui=child_laui,
                    parent_type=parent_type,
                    child_type=child_type,
                    true_parent=False,
                )
            )
            return link_laui

    async def find_tasks_ready_to_run(self, project_laui: PydanticObjectId) -> list[Task]:
        tasks = await self.item_repo.get_tasks_ready_to_run(project_laui)
        return tasks

    async def _link_task_and_its_paramaters(self, item_laui: ObjectId, item: CreateItem):
        # Link assiciated items
        if item.operator_laui:
            link_operator_laui = await self.create_link(
                CreateLinkRequest(parent_laui=item.operator_laui, child_laui=item_laui)
            )
            item.link_operator_laui = link_operator_laui
        if item.connection_laui:
            link_connection_laui = await self.create_link(
                CreateLinkRequest(parent_laui=item.connection_laui, child_laui=item_laui)
            )
            item.link_connection_laui = link_connection_laui
        if item.payload_laui:
            link_payload_laui = await self.create_link(
                CreateLinkRequest(parent_laui=item.payload_laui, child_laui=item_laui)
            )
            item.link_payload_laui = link_payload_laui
        if item.attached_config_lauis:
            if not hasattr(item, "link_config_lauis"):
                item.link_config_lauis = []
            for config_laui in item.attached_config_lauis:
                link_config_laui = await self.create_link(
                    CreateLinkRequest(parent_laui=config_laui, child_laui=item_laui)
                )
                item.link_config_lauis.append(link_config_laui)

    async def link_tasks(self, parent_task_laui: str, child_task_laui: str):
        await self.link_repo.create_link(
            CreateLink(
                parent_laui=parent_task_laui,
                child_laui=child_task_laui,
                child_type="task",
                parent_type="task",
                true_parent=False,
            )
        )

    def get_supported_children_types(self, item_type: str) -> list[str]:
        return self.item_types_manager.get_supported_item_types(item_type)

    def get_supported_parent_types(self, item_type: str) -> list[str]:
        return self.item_types_manager.get_supported_parent_types(item_type)

    @staticmethod
    def _empty_response() -> GetItemsResponse:
        return GetItemsResponse(
            items=[],
            pagination=PaginationResponse(current_page=1, per_page=0, has_next=False),
        )


def get_catalog_manager(request: Request):
    return request.app.state.catalog_manager
