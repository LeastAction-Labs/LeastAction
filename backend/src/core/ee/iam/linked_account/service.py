# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import Request

from src.common.exceptions import NotFoundError
from src.core.ee.iam.linked_account.repo import LinkedAccountRepository
from src.core.ee.iam.linked_account.schema import CreateLinkedAccount


class LinkedAccountService:
    def __init__(self, linked_account_repo: LinkedAccountRepository):
        self.linked_account_repo = linked_account_repo

    async def create_linked_account(self, linked_account: CreateLinkedAccount) -> str:
        return await self.linked_account_repo.create_linked_account(linked_account)

    async def get_linked_account_by_sub_and_provider(self, provider: str, sub: str):
        try:
            return await self.linked_account_repo.find_linked_account(
                filter={"provider": provider, "sub": sub}
            )
        except NotFoundError:
            raise NotFoundError(f"Linked account not found with provider:{provider} and sub:{sub}")


def get_linked_account_service(request: Request) -> LinkedAccountService:
    return request.app.state.linked_account_service
