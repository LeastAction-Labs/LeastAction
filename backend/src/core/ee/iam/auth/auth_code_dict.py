# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import os

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import Request

from src.common.exceptions import NotFoundError

load_dotenv()


class AuthCodeDict:
    def __init__(self):
        # 1. Pull the URL from the environment inside the class
        self.redis_url = os.getenv("REDIS_URL")
        if not self.redis_url:
            raise ValueError("REDIS_URL is not set in environment variables")

        # 2. Initialize the client
        self.client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def insert(self, key: str, value: dict[str, any], expire_seconds: int = 300):
        """Store dict as JSON with an expiration (TTL)."""
        # Convert dict to JSON string for storage
        await self.client.setex(name=key, time=expire_seconds, value=json.dumps(value))

    async def lookup(self, key: str) -> dict[str, any]:
        """Fetch and parse the JSON back to a dict."""
        data = await self.client.get(key)

        if data is None:
            raise NotFoundError(message="Authorization code not found or expired")

        return json.loads(data)

    async def delete(self, key: str):
        """Explicitly remove the key (for one-time use)."""
        await self.client.delete(key)


def get_auth_code_dict(request: Request) -> AuthCodeDict:
    return request.app.state.auth_code_dict
