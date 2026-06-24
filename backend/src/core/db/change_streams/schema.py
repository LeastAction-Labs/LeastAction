# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, AliasPath, BaseModel, Field
from pydantic_mongo import PydanticObjectId


class FieldPatch(BaseModel):
    add: list[str] = []
    remove: list[str] = []

    @property
    def is_empty(self):
        if not self.add and not self.remove:
            return True
        return False


class AccessPatch(BaseModel):
    owners: FieldPatch = FieldPatch()
    editors: FieldPatch = FieldPatch()
    viewers: FieldPatch = FieldPatch()

    @property
    def is_empty(self):
        if self.owners.is_empty and self.editors.is_empty and self.viewers.is_empty:
            return True
        return False


class AccessState(BaseModel):
    owners: dict[str, str] = {}
    editors: dict[str, str] = {}
    viewers: dict[str, str] = {}


class AccessUpdate(BaseModel):
    access: AccessState | None = None
    access_editors: dict[str, str] | None = Field(alias="access.editors", default=None)
    access_viewers: dict[str, str] | None = Field(alias="access.viewers", default=None)
    access_owners: dict[str, str] | None = Field(alias="access.owners", default=None)


class AccessCreate(BaseModel):
    access: AccessState


class PayloadType(str, Enum):
    LINK = "link"
    ITEM = "item"
    GROUP = "group"
    USER = "user"


class Action(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DROP = "drop"


class ItemPayload(BaseModel):
    item_laui: str | None = None
    access_patch: AccessPatch | None = None
    action: Action
    payload_type: PayloadType = PayloadType.ITEM
    session_id: str | None = None


class LinkPayload(BaseModel):
    item_laui: str
    parent_laui: str
    true_parent: bool
    action: Action
    payload_type: PayloadType = PayloadType.LINK


class GroupPayload(BaseModel):
    group_laui: str | None = None
    access_patch: AccessPatch | None = None
    action: Action
    payload_type: PayloadType = PayloadType.GROUP
    session_id: str | None = None


class UserPayload(BaseModel):
    user_laui: str
    action: Action
    payload_type: PayloadType = PayloadType.USER


class Link(BaseModel):
    parent_laui: PydanticObjectId | None = None
    child_laui: PydanticObjectId
    true_parent: bool


class UpdateDescription(BaseModel):
    updatedFields: dict[str, Any]
    removedFields: list[str]


class ChangeStream(BaseModel):
    collection: str
    document_laui: PydanticObjectId | None
    operationType: Literal["replace", "insert", "delete", "update", "drop"]
    updateDescription: UpdateDescription | None = None
    fullDocument: dict[str, Any] | None = None
    fullDocumentBeforeChange: dict[str, Any] | None = None
    session_id: str | None = Field(
        validation_alias=AliasChoices(
            AliasPath("updateDescription", "updatedFields", "last_session_id"),
            AliasPath("fullDocument", "last_session_id"),
        ),
        default=None,
    )
