# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import secrets
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Cookie, Depends, Form, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.logger.logger import log_info
from src.common.utils import (
    create_url,
    decode_data,
    delete_cookie,
    encode_data,
    load_system_config,
    set_cookie,
)
from src.core.ee.iam.auth.api_request import (
    AuthRequest,
    LoginRequest,
    RedirectWithCodeRequest,
    TokenRequest,
)
from src.core.ee.iam.auth.auth_code_dict import AuthCodeDict, get_auth_code_dict
from src.core.ee.iam.auth.service import AuthService, get_auth_service
from src.core.ee.iam.session.service import SessionService, get_session_service
from src.core.ee.iam.user.schema import User
from src.core.ee.iam.user.service import UserService, get_user_service
from src.core.email.schema import Email
from src.core.email.service import EmailService, get_email_service

auth_router = APIRouter()


# @auth_router.post("/signup")
# async def signup_user(
#         user: CreateUser,
#         user_service: UserService = Depends(get_user_service)
# ):
#     user_laui = await user_service.create_user(user)
#     return user_laui


@auth_router.post("/login")
async def login_user(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    log_info(
        "api",
        "auth_router",
        "login",
        f"user={get_user_laui()} payload={{username={username}, password=***}}",
    )
    request = LoginRequest(username=username, password=unquote(password))
    user = await auth_service.login_user(request=request)
    redirect_url = create_url(
        path="/api/v1/redirect-with-code",
        query_params={"user_laui": user.laui},
        redirect_to="backend",
    )
    response = RedirectResponse(url=redirect_url, status_code=303)
    set_cookie(
        response=response,
        key="session",
        value=encode_data(data=user.model_dump(by_alias=True, exclude=["license_laui"])),
    )
    return response


@auth_router.get("/auth")
async def auth(request: Request, auth_request: Annotated[AuthRequest, Query()]):
    log_info(
        "api", "auth_router", "auth", f"user={get_user_laui()} payload={auth_request.model_dump()}"
    )
    session_cookie = request.cookies.get("session")
    if session_cookie:
        session_data = decode_data(session_cookie)
        user = User(**session_data)
        redirect_url = create_url(
            path="/api/v1/redirect-with-code",
            query_params={"user_laui": user.laui},
            redirect_to="backend",
        )
    else:
        redirect_url = create_url(path="/public/login", redirect_to="frontend")

    response = RedirectResponse(url=redirect_url, status_code=303)

    set_cookie(
        response=response, key="oauth_flow", value=encode_data(data=auth_request.model_dump())
    )

    return response


@auth_router.get("/redirect-with-code")
async def redirect_with_code(
    request: Request,
    query: Annotated[RedirectWithCodeRequest, Query()],
    response: Response,
    auth_code_dict: AuthCodeDict = Depends(get_auth_code_dict),
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
):

    log_info(
        "api",
        "auth_router",
        "redirect_with_code",
        f"user={get_user_laui()} payload={query.model_dump()}",
    )
    config = load_system_config()
    print(config.get("email_totp"))
    email_totp_enabled = config.get("email_totp", False)

    oauth_flow_cookie = request.cookies.get("oauth_flow")
    if not oauth_flow_cookie:
        response.status_code = 403
        return response

    user_laui = query.user_laui
    random_code = secrets.token_hex(6)
    await auth_code_dict.insert(key=random_code, value={"user_laui": user_laui})

    if email_totp_enabled:
        user_email = (await user_service.find_user(laui=PydanticObjectId(user_laui))).email

        email_service.send_email(
            email=Email(
                to=user_email,
                subject="Verfication code from LeastActionLabs",
                message=f"The verfication code is {random_code}",
            )
        )

    oauth_flow_cookie_data = decode_data(oauth_flow_cookie)
    auth_request_instance = AuthRequest(**oauth_flow_cookie_data)

    query_params = {"state": auth_request_instance.state}

    if not email_totp_enabled:
        query_params["code"] = random_code

    redirect_url = create_url(
        path=auth_request_instance.redirect_uri, query_params=query_params, redirect_to="client"
    )
    return RedirectResponse(url=redirect_url, status_code=303)


@auth_router.get("/get-mcp-token")
async def get_mcp_token(
    request: Request, session_service: SessionService = Depends(get_session_service)
):
    log_info("api", "auth_router", "get_mcp_token", f"user={get_user_laui()} payload={{}}")
    token = request.cookies.get("frontend_token")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    try:
        session_service.verify_jwt_token(token)
        return {"access_token": token}
    except ValueError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})


@auth_router.post("/token")
async def get_token(
    request: TokenRequest, response: Response, auth_service: AuthService = Depends(get_auth_service)
):
    log_info(
        "api", "auth_router", "token", f"user={get_user_laui()} payload={request.model_dump()}"
    )
    try:
        session = await auth_service.create_session(token_request=request)
        set_cookie(response=response, key="frontend_token", value=session.access_token)
        return {"must_change_password": session.user.must_change_password}
    except Exception:
        delete_cookie(response=response, key="oauth_flow")
        delete_cookie(response=response, key="session")


@auth_router.post("/logout")
async def logout(response: Response):
    log_info("api", "auth_router", "logout", f"user={get_user_laui()} payload={{}}")
    delete_cookie(response=response, key="frontend_token")
    delete_cookie(response=response, key="oauth_flow")
    delete_cookie(response=response, key="session")
    return "logged out"
