# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import functools
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from fastapi import Depends, Request
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from src.core.db.service import MongoDBClient

session_context: ContextVar[AsyncClientSession | None] = ContextVar("session_context", default=None)


class TransactionManager:
    def __init__(self, client: MongoDBClient):
        self.client = client

    @asynccontextmanager
    async def session(self):
        if session_context.get() is not None:
            # To bypass nested transactions
            yield
        else:
            async with self.client.client.start_session() as session:
                async with await session.start_transaction(
                    read_concern=ReadConcern("majority"), write_concern=WriteConcern("majority")
                ):
                    token = session_context.set(session)
                    try:
                        yield
                    finally:
                        session_context.reset(token)


transaction_manager_context: ContextVar[TransactionManager | None] = ContextVar(
    "transaction_manager_context", default=None
)


def get_transaction_manager(request: Request) -> TransactionManager:
    return request.app.state.transaction_manager


def set_transaction_manager_context(
    transaction_manager: TransactionManager = Depends(get_transaction_manager),
):
    token = transaction_manager_context.set(transaction_manager)
    return token


def get_transaction_manager_from_context() -> TransactionManager:
    transaction_manager = transaction_manager_context.get()
    if transaction_manager is None:
        raise ValueError("Transaction manager not found in context")
    return transaction_manager


def transactional(func: Callable[..., Any]):
    @functools.wraps(func)
    async def wrapper(
        *args: Any,
        **kwargs: Any,
    ):
        transaction_manager = get_transaction_manager_from_context()
        async with transaction_manager.session():
            return await func(*args, **kwargs)

    return wrapper
