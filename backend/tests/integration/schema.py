# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any, Literal

from pydantic import BaseModel


class TestRequest(BaseModel):
    url: str
    method: Literal["get", "post", "delete", "patch", "put"]
    params: dict[str, Any] | None = None
    json: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    follow_redirects: bool | None = None


class BaseFolders(BaseModel):
    account_folder_laui: str
    project_folder_laui: str
    trash_folder_laui: str
