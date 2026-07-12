# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pydantic import BaseModel


class _BaseClaims(BaseModel):
    sub: str
    exp: int
    iat: int
    iss: str


class AccessTokenClaims(_BaseClaims):
    type: str = "access"
