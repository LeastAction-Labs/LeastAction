# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any, Optional
from urllib.parse import urlencode, urlsplit, urlunsplit

from bson import ObjectId
from fastapi import Request
from pydantic import BaseModel, ConfigDict

from src.common.secrets import get_secret
from src.core.iam.auth.api_request import LoginSource
from src.core.iam.auth.credentials.credentials import Provider


class ClientRedirectParams(BaseModel):
    redirect_uri: str
    code: Optional[str] = None
    state: str
    login_source: LoginSource = LoginSource.NATIVE


class ClientRedirectQueryParams(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    code: Optional[str] = None
    state: str
    provider: Provider = Provider.LEASTACTION


class RedirectHandler:
    def __init__(self):
        self.app_public_url = get_secret("APP_PUBLIC_URL") or "http://localhost:8080"
        self.api_base_url = self.app_public_url + "/api/v1"
        self.backend_urls = {
            "login": self.api_base_url + "/login",
            "redirect_with_code": self.api_base_url + "/redirect-with-code",
        }
        self.frontend_urls = {
            "login": self.app_public_url + "/public/login",
        }
        self.sso_redirect_url = get_secret("KEYCLOAK_REDIRECT_URL")

    def get_backend_redirect_with_code_url(self, user_laui: str) -> str:
        return f"{self.backend_urls['redirect_with_code']}?{urlencode({'user_laui': user_laui})}"

    def get_sso_login_url(self, state: str) -> str:
        query_params = {
            "client_id": "leastaction",
            "redirect_uri": self.backend_urls["redirect_with_code"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return f"{self.sso_redirect_url}?{urlencode(query_params)}"

    def get_frontend_login_url(self) -> str:
        return f"{self.frontend_urls['login']}"

    def get_client_redirect_url(self, params: ClientRedirectParams) -> str:
        client_redirect_uri = urlsplit(params.redirect_uri)
        query_params = ClientRedirectQueryParams(
            **params.model_dump(exclude_unset=True),
            provider=(
                Provider.KEYCLOAK
                if params.login_source == LoginSource.SSO
                else Provider.LEASTACTION
            ),
        )
        query_string = urlencode(query_params.model_dump(exclude_none=True))
        url_parts = (
            client_redirect_uri.scheme,
            client_redirect_uri.netloc,
            client_redirect_uri.path,
            query_string,
            "",
        )
        return urlunsplit(url_parts)


def get_redirect_handler(request: Request) -> RedirectHandler:
    return request.app.state.redirect_handler


def convert_objectid_to_str(data: Any) -> Any:
    """Recursively convert ObjectId fields to strings in nested structures"""
    # ObjectId check - bson.ObjectId is the base type for all ObjectId variants
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    return data
