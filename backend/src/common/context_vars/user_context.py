# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from contextlib import contextmanager
from contextvars import ContextVar

from src.core.iam.user.schema import User

user_laui_context_var: ContextVar[str] = ContextVar("user_laui", default=None)


def get_user_laui() -> str | None:
    return user_laui_context_var.get()


def set_user_laui(user_laui: str) -> str:
    return user_laui_context_var.set(user_laui)


user_context_var: ContextVar[User] = ContextVar("user", default=None)


def get_user() -> User | None:
    return user_context_var.get()


def set_user_laui(user: User) -> User:
    return user_context_var.set(user)


allowed_mcp_tools_context_var: ContextVar[list | None] = ContextVar(
    "allowed_mcp_tools", default=None
)


def get_allowed_mcp_tools() -> list | None:
    return allowed_mcp_tools_context_var.get()


def set_allowed_mcp_tools(tools: list | None) -> None:
    allowed_mcp_tools_context_var.set(tools)


root_user_laui_context_var: ContextVar[str] = ContextVar("root_user_laui", default=None)


def get_root_user_laui() -> str | None:
    return root_user_laui_context_var.get()


def set_root_user_laui(user_laui: str) -> str:
    return root_user_laui_context_var.set(user_laui)


system_user_laui_context_var: ContextVar[str] = ContextVar("system_user_laui", default=None)


def get_system_user_laui() -> str | None:
    return system_user_laui_context_var.get()


def set_system_user_laui(user_laui: str) -> str:
    return system_user_laui_context_var.set(user_laui)


current_token_context_var: ContextVar[str] = ContextVar("current_context_var_token", default="")


def get_current_token() -> str:
    return current_token_context_var.get()


def set_current_token(token: str) -> None:
    current_token_context_var.set(token)


def is_root_user() -> bool:
    current = get_user_laui()
    root = get_root_user_laui()
    return bool(current and root and current == root)


def is_system_user() -> bool:
    current = get_user_laui()
    system = get_system_user_laui()
    return bool(current and system and current == system)


@contextmanager
def user_context(user: User, root_user_laui: str | None, system_user_laui: str, token: str):
    user_laui_context_var_token = user_laui_context_var.set(user.laui)
    system_user_laui_context_var_token = system_user_laui_context_var.set(system_user_laui)
    root_user_laui_context_var_token = root_user_laui_context_var.set(root_user_laui)
    user_context_var_token = user_context_var.set(user)
    allowed_mcp_tools_context_var_token = allowed_mcp_tools_context_var.set(user.allowed_mcp_tools)
    current_token_context_var_token = current_token_context_var.set(token)
    try:
        yield
    finally:
        user_laui_context_var.set(user_laui_context_var_token)
        system_user_laui_context_var.set(system_user_laui_context_var_token)
        root_user_laui_context_var.set(root_user_laui_context_var_token)
        user_context_var.set(user_context_var_token)
        allowed_mcp_tools_context_var.set(allowed_mcp_tools_context_var_token)
        current_token_context_var.set(current_token_context_var_token)
