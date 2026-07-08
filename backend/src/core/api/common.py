# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from typing import Optional

from pydantic import BaseModel, model_validator


class PaginationRequest(BaseModel):
    page: int = 1
    per_page: int = 10
    offset: int = 0
    limit: int = 0
    page_token: Optional[str] = None

    @model_validator(mode="after")
    def add_offset_and_limit(self):
        self.offset = (self.page - 1) * self.per_page
        self.limit = self.per_page
        return self


class PaginationResponse(BaseModel):
    current_page: Optional[int] = None
    per_page: Optional[int] = None
    has_next: bool
    next_page_token: Optional[str] = None
