# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.


import os

_cache: dict | None = None


def get_secret(key: str, default: str | None = None) -> str | None:
    """Return the value for *key*, checking env first, then AWS Secrets Manager."""
    val = os.getenv(key)
    if val:
        return val

    if os.getenv("USE_AWS_SECRETS", "").lower() == "true":
        secrets = _load_aws_secrets()
        val = secrets.get(key)
        if val:
            return val

    return default


def _load_aws_secrets() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    import json

    import boto3

    secret_name = os.getenv("AWS_SECRETS_NAME", "leastaction/dev")
    region = os.getenv("AWS_REGION", "us-east-1")

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    _cache = json.loads(response["SecretString"])
    return _cache
