# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pydantic import BaseModel


class Access(BaseModel):
    owners: dict[str, str] = {}
    editors: dict[str, str] = {}
    viewers: dict[str, str] = {}

    @property
    def is_empty(self):
        return not any(self.model_dump().values())


class AccessPatch(BaseModel):
    add: Access = Access()
    remove: Access = Access()

    @property
    def has_changes(self) -> bool:
        return not (self.add.is_empty and self.remove.is_empty)
