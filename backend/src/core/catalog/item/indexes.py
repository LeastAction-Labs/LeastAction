# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, model_validator
from pymongo import ASCENDING, TEXT, IndexModel

from src.common.logger.logger import log_warning


class IndexSortType(Enum):
    ASC = "asc"
    TEXT = "text"


class IndexField(BaseModel):
    fields: list[str]
    sort: IndexSortType = IndexSortType.ASC
    filter: dict[str, Any] | None = None

    @model_validator(mode="after")
    def cleanup(self):

        if self.filter:
            for key, value in self.filter.items():
                if isinstance(value, list):
                    self.filter[key] = {"$in": value}

        self.fields = sorted(list(set(self.fields)))

        return self


class IndexFile(BaseModel):
    indexes: list[IndexField]


def get_index_model(index: IndexField, item_type: str | None) -> IndexModel:

    sort_field = TEXT if index.sort == IndexSortType.TEXT else ASCENDING
    index_model_fields = [(field, sort_field) for field in index.fields]

    index_model_partial_filter = index.filter if index.filter else {}
    if item_type:
        index_model_partial_filter["item_type"] = item_type

    options = {}
    if index_model_partial_filter:
        options["partialFilterExpression"] = index_model_partial_filter

    field_names = "_".join(f"{f}_1" for f in index.fields)
    if item_type:
        options["name"] = f"{field_names}_{item_type}"

    return IndexModel(index_model_fields, **options)


def get_index_models(file_path: Path) -> list[IndexModel]:
    indexes = []
    file_name = file_path.name
    file_content = IndexFile(**json.loads(file_path.read_text(encoding="utf-8")))
    file_indexes = file_content.indexes
    text_type_included = False
    item_type = None if file_name == "leastaction.json" else file_name.removesuffix(".json")
    for index in file_indexes:
        if not index.fields:
            msg = f"Ignoring the index: '{index}', the fields list is empty"
            log_warning("START", "indexes", "get_index_models", msg)
            continue
        if index.sort == IndexSortType.TEXT:
            if text_type_included:
                msg = f"Ignoring the index: '{index}', there can be only one index of type TEXT on a collection"
                log_warning("START", "indexes", "get_index_models", msg)
                continue
            else:
                text_type_included = True
        indexes.append(get_index_model(index, item_type))
    return indexes


def get_indexes() -> list[IndexModel]:
    indexes: list[IndexModel] = []
    root_dir = Path.cwd().parent
    schema_folder = root_dir / "config/schema"
    schema_folder.mkdir(parents=True, exist_ok=True)
    for file in schema_folder.iterdir():
        if file.is_file:
            try:
                indexes.extend(get_index_models(file))
            except Exception as e:
                msg = f"Got the error: '{e}' when processing indexes for file:{file.name}"
                log_warning("START", "indexes", "get_indexes", msg)
                continue

    index_names = []
    for index in indexes:
        index_doc = index.document
        if index_doc["name"] not in index_names:
            index_names.append(index_doc["name"])
        else:
            msg = f"Ignoring the index:{index}, as one with same fields is already other and this leads to index creation errors"
            log_warning("START", "indexes", "get_indexes", msg)
            indexes.remove(index)

    return indexes
