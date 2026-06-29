# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_mongo import PydanticObjectId

from src.core.ee.keto.types import KetoString


class Relation(str, Enum):
    OWNERS = "owners"
    VIEWERS = "viewers"
    EDITORS = "editors"
    FALSE_PARENTS = "false_parents"
    TRUE_PARENT = "true_parent"
    NONE = ""
    ALL = "all"


class Permission(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    OWN = "own"
    TRUE_PARENT_EDIT = "true_parent_edit"
    DELETE = "delete"
    IS_TRUE_PARENT = "is_true_parent"
    NONE = ""


class Namespace(str, Enum):
    ITEM = "Item"
    GROUP = "Group"
    USER = "User"


class Action(str, Enum):
    INSERT = "insert"
    DELETE = "delete"


class SubjectSet(BaseModel):
    namespace: Namespace
    object: KetoString
    relation: str


class RelationTuple(BaseModel):
    namespace: Namespace
    object: KetoString | None = None
    relation: Relation | Permission | None = None
    subject_id: KetoString | None = None
    subject_set: SubjectSet | None = None


class RelationTupleParams(BaseModel):
    namespace: Namespace
    object: KetoString | None = None
    relation: Relation | Permission | None = None
    subject_id: KetoString | None = None
    subject_namespace: Namespace | None = Field(
        serialization_alias="subject_set.namespace", default=None
    )
    subject_object: KetoString | None = Field(
        serialization_alias="subject_set.object", default=None
    )
    subject_relation: Relation | Permission | None = Field(
        serialization_alias="subject_set.relation", default=None
    )
    page_size: int | None = 1000
    page_token: str | None = None


class RelationTupleWithAction(BaseModel):
    relation_tuple: RelationTuple
    action: Action


class GetRelationTuplesResponse(BaseModel):
    relation_tuples: list[RelationTuple]
    next_page_token: str


class SharedItemsResponse(BaseModel):
    item_nodes: list[tuple[PydanticObjectId, Permission]]
    next_page_token: str


class RelationTupleWithPermission(BaseModel):
    relation_tuple: RelationTuple
    permission: Permission


class AccessRelation(BaseModel):
    item_laui: str
    subject_laui: str
    subject_type: Literal["user", "group"]
    subject_permission: Permission


class GroupResponse(BaseModel):
    id: str
    name: str


class GroupsRawResponse(BaseModel):
    groups: list[str]
    next_page_token: str


class GroupsResponse(BaseModel):
    groups: list[GroupResponse]
    next_page_token: str
