# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import Request

from src.core.ee.iam.session.claims import AccessTokenClaims


class ApiService:
    def __init__(self, request: Request):
        self.request = request
        self.token_claims: AccessTokenClaims = request.state.token_claims
        pass

    def get_logged_in_user_laui(self):
        return self.token_claims.sub


def get_api_service(request: Request) -> ApiService:
    return ApiService(request)
