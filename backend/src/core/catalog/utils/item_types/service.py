# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from typing import Optional

from src.common.context_vars.catalog_context import (
    get_catalog_config,
    get_supported_item_types_cache,
)
from src.core.catalog.config.catalog_schema import ItemTypeMapping
from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.utils.item_types.schema import ChildType, ItemCategory


class ItemTypesManager:
    def __init__(self):
        pass

    def _find_supported_item_types(
        self, item_type: str, child_type: Optional[ChildType] = None
    ) -> list[str]:
        cache = get_supported_item_types_cache()
        item_type_map = cache.get(item_type)

        if not item_type_map:
            catalog_config = get_catalog_config()
            mapping = catalog_config.item_type_link_mapping
            print(mapping)
            item_type_map = mapping.get(item_type, ItemTypeMapping())
            print("XXXXX")
            print(item_type_map)
            cache[item_type] = item_type_map

        if child_type == ChildType.HARD:
            return item_type_map.hard_children

        if child_type == ChildType.SOFT:
            return item_type_map.soft_children

        return list(set(item_type_map.hard_children + item_type_map.soft_children))

    def get_supported_item_types(
        self,
        item_type: str,
        category: ItemCategory = ItemCategory.ALL,
        child_type: Optional[ChildType] = None,
    ) -> list[str]:
        supported_item_types = []
        while item_type:
            supported_item_types = self._find_supported_item_types(item_type, child_type)
            if supported_item_types or "." not in item_type:
                break
            item_type = item_type.rsplit(".")[0]
        if category == ItemCategory.NON_FOLDER:
            return [
                item_type
                for item_type in supported_item_types
                if not item_type.startswith("folder.")
            ]
        if category == ItemCategory.FOLDER:
            return [
                item_type for item_type in supported_item_types if item_type.startswith("folder.")
            ]
        return supported_item_types

    def attach_supported_item_types(self, items: list[ItemProjection]):
        for item in items:
            item.supported_types = self._find_supported_item_types(item.item_type)

    def check_item_type_compatible(self, item_type: str, supported_item_types: list[str]) -> bool:
        for supported_item_type in supported_item_types:
            if item_type == supported_item_type or item_type.startswith(supported_item_type + "."):
                return True
        return False

    def get_supported_parent_types(
        self, item_type: str, child_type: Optional[ChildType] = None
    ) -> list[str]:
        catalog_config = get_catalog_config()
        mapping = catalog_config.item_type_link_mapping
        return [
            parent_type
            for parent_type in mapping.keys()
            if self.check_item_type_compatible(
                item_type, self.get_supported_item_types(parent_type, ItemCategory.ALL, child_type)
            )
        ]
