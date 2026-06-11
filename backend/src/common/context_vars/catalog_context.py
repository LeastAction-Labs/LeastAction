# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from contextlib import contextmanager
from contextvars import ContextVar

from src.core.catalog.config.catalog_schema import CatalogConfig
from src.core.catalog.config.schema.schema_manager import SchemaManager

catalog_config_var: ContextVar[CatalogConfig] = ContextVar("catalog_config", default=None)


def get_catalog_config() -> CatalogConfig:
    return catalog_config_var.get()


supported_item_types_cache_var: ContextVar[dict[str, list[str]]] = ContextVar(
    "supported_item_types_cache", default=None
)


def get_supported_item_tpyes_cache() -> dict[str, list[str]]:
    return supported_item_types_cache_var.get()


item_type_schema_manager_mapping_var: ContextVar[dict[str, SchemaManager]] = ContextVar(
    "schema_manager_mapping", default=None
)


def get_schema_manager(item_type: str) -> SchemaManager:
    mapping = item_type_schema_manager_mapping_var.get()
    if mapping.get(item_type):
        return mapping[item_type]
    schema_manager = SchemaManager(item_type)
    mapping[item_type] = schema_manager
    return schema_manager


@contextmanager
def catalog_context(config: CatalogConfig):
    config_token = catalog_config_var.set(config)
    cache_token = supported_item_types_cache_var.set({})
    item_type_schema_manager_mapping_token = item_type_schema_manager_mapping_var.set({})
    try:
        yield
    finally:
        item_type_schema_manager_mapping_var.reset(item_type_schema_manager_mapping_token)
        supported_item_types_cache_var.reset(cache_token)
        catalog_config_var.reset(config_token)
