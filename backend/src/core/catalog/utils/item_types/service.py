# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from src.common.context_vars.catalog_context import (
    get_catalog_config,
    get_supported_item_tpyes_cache,
)
from src.core.catalog.item.schema import ItemProjection

from .schema import ItemCategory


class ItemTypesManager:
    def __init__(self):
        pass

    def _find_supported_item_types(self, item_type: str) -> list[str]:
        cache = get_supported_item_tpyes_cache()
        if cache.get(item_type):
            return cache[item_type]

        catalog_config = get_catalog_config()
        mapping = catalog_config.item_type_link_mapping

        if mapping.get(item_type):
            cache[item_type] = mapping[item_type].can_contain
            return mapping[item_type].can_contain

        cache[item_type] = []
        return []

    def get_supported_item_types(
        self, item_type: str, category: ItemCategory = ItemCategory.ALL
    ) -> list[str]:
        supported_item_types = []
        while item_type:
            supported_item_types = self._find_supported_item_types(item_type)
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

    def get_supported_parent_types(self, child_type: str) -> list[str]:
        catalog_config = get_catalog_config()
        mapping = catalog_config.item_type_link_mapping
        return [
            parent_type
            for parent_type in mapping.keys()
            if self.check_item_type_compatible(
                child_type, self.get_supported_item_types(parent_type, ItemCategory.ALL)
            )
        ]
