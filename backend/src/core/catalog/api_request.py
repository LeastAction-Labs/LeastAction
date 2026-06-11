# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import InvalidArgumentError, UnprocessableEntityError
from src.core.api.common import PaginationRequest, PaginationResponse
from src.core.catalog.config.schema.schema_manager import SchemaManager
from src.core.catalog.item.repo import ItemProjection
from src.core.catalog.item_directory import ItemDirectoryItemNode
from src.core.catalog.item_revision.schema import ItemRevision, ItemRevisionProjection
from src.core.catalog.link.repo import Link
from src.core.ee.keto.schema import Permission
from src.core.task.schema import TaskUpdateData

from .pagination_constants import pagination_constants


class BaseCreateItemRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    item_type: str


class CreateItemResponse(BaseModel):
    item_laui: str


class TaskUpdateRequest(TaskUpdateData):
    pass


class MultipleTaskRequest(BaseModel):
    task_lauis: list[PydanticObjectId]
    model_config = ConfigDict(extra="allow")


class MultipleTaskResponse(BaseModel):
    task_results: list[dict[str, Any]]


class CreateLinkResponse(BaseModel):
    link_laui: str


class CreateLinkRequest(BaseModel):
    parent_laui: PydanticObjectId
    child_laui: PydanticObjectId


class FilterType(Enum):
    ITEM = "item"
    LINK = "link"


class FilterSchema:
    @staticmethod
    def create(
        filter_type: FilterType,
        filter_statement: str,
        transformer: Callable[[Any], Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "filter_type": filter_type,
            "filter_statement": filter_statement,
            "transformer": transformer,
        }


SORTABLE_TASK_FIELDS = {
    "partition",
    "logical_date",
    "state",
    "last_run_date",
    "duration",
    "priority",
}


class GetItemsFilter(BaseModel):
    item_laui: PydanticObjectId | None = Field(
        default=None, json_schema_extra={"deciding_factor": True}
    )
    is_root: bool | None = Field(default=None, json_schema_extra={"deciding_factor": True})
    parent_or_child: Literal["parent", "child"] | None = Field(
        default=None, json_schema_extra={"deciding_factor": True}
    )
    item_type: str | None = None
    depth: int | None = 1
    per_page: int = 10
    page: int = 1
    is_deleted: bool = True
    page_token: str | None = None
    item_permission: Permission | None = None
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] | None = "asc"
    filter_state: str | None = None

    @property
    def only_item_laui_passed(self) -> bool:
        if not self.item_laui:
            return False
        for field_name, field_info in self.model_fields.items():
            extra = field_info.json_schema_extra or {}
            if (
                extra.get("deciding_factor")
                and field_name != "item_laui"
                and getattr(self, field_name, None)
            ):
                return False
        return True

    @model_validator(mode="after")
    def validate_filters(self):
        if self.is_root:
            non_root_item_fields_passed = []
            fields_disallowed_for_root = []
            for field_name, field_info in self.model_fields.items():
                extra = field_info.json_schema_extra or {}
                if extra.get("deciding_factor") and field_name != "is_root":
                    fields_disallowed_for_root.append(field_name)
                    if getattr(self, field_name, None):
                        non_root_item_fields_passed.append(field_name)

            if non_root_item_fields_passed:
                raise InvalidArgumentError(
                    message="Invalid argument: filter conflict",
                    detail={
                        "error_type": "Invalid Field Combination",
                        "message": "Invalid fields passed when 'is_root' is set to True.",
                        "invalid_fields_passed": non_root_item_fields_passed,
                        "fields_disallowed_for_root": fields_disallowed_for_root,
                    },
                )

        if not self.item_laui and not self.is_root:
            raise InvalidArgumentError(
                message="Invalid argument: missing filter criteria",
                detail="You must provide either 'item_laui' or 'is_root' to run this query.",
            )

        if (
            self.per_page < pagination_constants["per_page"]["min"]
            or self.per_page > pagination_constants["per_page"]["max"]
            or self.page < pagination_constants["page"]["min"]
        ):
            raise InvalidArgumentError(
                message="Invalid argument: pagination parameters out of bounds",
                detail=f"The pagination values (page: {self.page}, per_page: {self.per_page}) are outside the allowed system boundaries: {pagination_constants}.",
            )

        return self


class SearchItemsFilter(BaseModel):
    model_config = ConfigDict(extra="allow")
    item_laui: PydanticObjectId | None = Field(default=None, serialization_alias="_id")
    is_root: bool | None = None
    item_type: str | None = None
    item_types: list[str] | None = None
    name: str | None = None
    parent_laui: PydanticObjectId | None = None
    item_lauis: list[PydanticObjectId] | None = None
    project_laui: PydanticObjectId | None = None
    get_by_pk: bool | None = False

    @model_validator(mode="after")
    def coerce_fields(self):
        for key, value in self.model_dump(exclude_none=True).items():
            if key.endswith("_laui") and getattr(self, key, None):
                setattr(self, key, PydanticObjectId(value))
            if (key.endswith("_at") or key.endswith("_date")) and getattr(self, key, None):
                setattr(self, key, datetime.fromisoformat(value))
        return self

    @property
    def get_item_filters(self) -> dict[str, Any]:
        if self.get_by_pk and not self.item_type:
            raise UnprocessableEntityError(
                message="Unprocessable entity: missing item_type",
                detail="When 'get_by_pk' is True, you must specify an 'item_type' parameter.",
            )
        if self.get_by_pk:
            schema_manager = SchemaManager(item_type=self.item_type)
            primary_keys = sorted(schema_manager.primary_keys)
            missing_keys = []
            pk_values_array = []
            for key in primary_keys:
                if not getattr(self, key, None):
                    missing_keys.append(key)
                pk_values_array.append(str(getattr(self, key, None)))
            if missing_keys:
                raise UnprocessableEntityError(
                    message="Unprocessable entity: missing primary keys",
                    detail=f"Cannot look up item_type '{self.item_type}' because required primary key fields are missing: {missing_keys}.",
                )
            pk_value = "-".join(pk_values_array)
            return {"pk": pk_value}
        if self.item_lauis:
            return {"_id": {"$in": self.item_lauis}}

        item_filters = self.model_dump(exclude={"get_by_pk", "item_types"}, exclude_unset=True)
        if self.item_types:
            patterns = "|".join(re.escape(t) for t in self.item_types)
            item_filters["item_type"] = {"$regex": f"^({patterns})(\\.|$)"}
        elif self.item_type:
            item_filters["item_type"] = {"$regex": f"^{re.escape(self.item_type)}(\\.|$)"}
        if self.name:
            tokens = [re.escape(t) for t in self.name.split() if t]
            if tokens:
                pattern = "".join(f"(?=.*{t})" for t in tokens)
                or_clauses = [{"name": {"$regex": pattern, "$options": "i"}}]
                try:
                    or_clauses.append({"_id": PydanticObjectId(self.name.strip())})
                except Exception:
                    pass
                item_filters.pop("name", None)
                item_filters["$or"] = or_clauses
        item_filters["deleted_at"] = None
        return item_filters


class SearchLinksFilter(BaseModel):
    parent_laui: PydanticObjectId | None = None
    child_laui: PydanticObjectId | None = None
    true_parent: bool | None = None
    parent_type: str | None = None
    child_type: str | None = None

    @property
    def get_link_filters(self):
        return self.model_dump(exclude_none=True)


class SearchItemsResponse(BaseModel):
    items: list[ItemProjection]
    pagination: PaginationResponse


class SearchLinksResponse(BaseModel):
    links: list[Link]
    pagination: PaginationResponse


class SearchRequest(BaseModel):
    item_filter: SearchItemsFilter | None = None
    link_filter: SearchLinksFilter | None = None
    pagination: PaginationRequest = PaginationRequest()
    projection: SearchItemsProjection | None = None

    @model_validator(mode="after")
    def validate_filters(self):
        if self.link_filter and self.item_filter:
            raise UnprocessableEntityError(
                message="Unprocessable entity: filter conflict",
                detail="You cannot pass both an 'item_filter' and a 'link_filter' in the same search request. Choose one.",
            )
        if not self.link_filter and not self.item_filter:
            raise UnprocessableEntityError(
                message="Unprocessable entity: missing search targets",
                detail="Your search request is empty. You must provide either an 'item_filter' or a 'link_filter'.",
            )
        return self

    @property
    def projections_dict(self) -> dict[str, int]:
        projections_dict = {"item_type": 1, "pk": 1}
        if not self.projection:
            return projections_dict
        if self.projection.include:
            for field in self.projection.include:
                projections_dict[field] = 1
        if self.projection.exclude:
            for field in self.projection.exclude:
                projections_dict[field] = 0
        projections_dict["item_type"] = 1
        return projections_dict


class SearchItemsProjection(BaseModel):
    include: list[str] | None = None
    exclude: list[str] | None = None


class GetItemsRequest(BaseModel):
    filter: GetItemsFilter


class GetItemRevisionsRequest(BaseModel):
    item_laui: PydanticObjectId
    version: int | None = None


class GetItemsResponse(BaseModel):
    items: list[ItemDirectoryItemNode]
    pagination: PaginationResponse | None = None


class GetItemRevisionsResponse(BaseModel):
    item_revisions: list[ItemRevisionProjection] | None = None
    item_revision: ItemRevision | None = None


class DeleteItemRequest(BaseModel):
    item_laui: PydanticObjectId
    parent_laui: PydanticObjectId | None
    hard_delete: bool = False


# Account -> Project ->Operators[Folder] -> Operator1, Operator2
# Account -> Project -> Config[Folder] -> Config1, Config2
# Account -> ProGetItemsFilterject -> Path[Folder] -> Path -> Task, Config1=

# is_root -> True
# item_laui , is_root , item_type , parent_or_child , depth

# item_laui , is_root , item_type

# is_root

# item_type , item_laui

"""
class SearchItemsFilter(BaseModel):

    item_laui: Optional[str] = Field(
        default=None,
        json_schema_extra=FilterSchema.create(
            FilterType.ITEM, "_laui", lambda x: ObjectId(x)
        ),
    )
    is_root : Optional[bool] = Field(
        default= None ,
        json_schema_extra= FilterSchema.create(FilterType.ITEM , "is_root")
    )
    item_type: Optional[str] = Field(
        default=None,
        json_schema_extra=FilterSchema.create(FilterType.ITEM, "item_type"),
    )
    name: Optional[str] = Field(
        default=None, json_schema_extra=FilterSchema.create(FilterType.ITEM, "name")
    )
    parent_laui: Optional[str] = Field(
        default=None,
        json_schema_extra=FilterSchema.create(
            FilterType.LINK, "parent_laui", lambda x: ObjectId(x)
        ),
    )
    child_laui :  Optional[str] = Field(
        default=None,
        json_schema_extra=FilterSchema.create(
            FilterType.LINK, "child_laui", lambda x: ObjectId(x)
        ),
    )
    trueparent_only: Optional[bool] = Field(
        default=None,
        json_schema_extra=FilterSchema.create(FilterType.LINK, "true_parent"),
    )
    parent_or_child : Optional[Literal["parent","child"]] = None
    depth: Optional[int] = 1
    has_children: Optional[bool] = None
    @model_validator(mode="after")
    def validate_filters(self) -> Any:
        # return error if no filters are provided by looping through the field
        no_filters = True
        for field_name, field_info in self.model_fields.items():
            field_value = getattr(self, field_name)
            field_schema = getattr(field_info,"json_schema_extra" , None )
            if field_value is not None:
                if field_schema is not None :
                    if no_filters :
                        no_filters = False
                        break

        if no_filters:
            raise InvalidArgumentError("No filters provided")

        # If trueparent_only is provided, parent_laui should be provided
        if self.trueparent_only and not self.parent_laui:
            raise InvalidArgumentError("Parent ID is required for trueparent_only")
        return self


    def get_filters_by_type(self, target_filter_type: FilterType) -> Dict[str, Any]:
        filters = {}

        for field_name, field_info in self.model_fields.items():

            field_value = getattr(self, field_name)

            if field_value is None:
                continue

            field_schema: Optional[Dict[str, Any]] = (
                getattr(field_info, "json_schema_extra", None) or {}
            )
            if not field_schema:
                continue
            filter_type = field_schema.get("filter_type")
            filter_statement = field_schema.get("filter_statement")
            transformer: Optional[Callable[[Any], Any]] = field_schema.get(
                "transformer"
            )
            if filter_type == target_filter_type:
                filters[filter_statement] = transformer(field_value) if transformer else field_value

        return filters

    def get_item_filters(self) -> Dict[str, Any]:
        filters = self.get_filters_by_type(FilterType.ITEM)
        return filters

    def get_link_filters(self) -> Dict[str, Any]:
        return self.get_filters_by_type(FilterType.LINK)
"""
