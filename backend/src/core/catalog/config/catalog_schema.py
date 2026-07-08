# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from pydantic import AliasChoices, BaseModel, Field


class ItemTypeMapping(BaseModel):
    hard_children: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("children", "hard_children")
    )
    soft_children: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("children", "soft_children")
    )


class CatalogConfig(BaseModel):
    item_type_link_mapping: dict[str, ItemTypeMapping]
    hierarchy_items_limit: int
