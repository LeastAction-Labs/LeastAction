# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import uuid
from contextvars import ContextVar

# Single context variable for session ID - used by both FastAPI and Celery
session_id_context: ContextVar[str] = ContextVar("session_id")
logger_context: ContextVar[str] = ContextVar("logger_context")
action_context: ContextVar[dict] = ContextVar("action_context")


def get_session_id() -> str:
    try:
        return session_id_context.get()
    except LookupError:
        return "unknown-session"


def set_session_id(session_id: str) -> str:
    """
    Returns:
        str: The token for resetting the context
    """
    return session_id_context.set(session_id)


def clear_session_id() -> None:
    try:
        session_id_context.set("")
    except LookupError:
        pass


def generate_session_id() -> str:
    return str(uuid.uuid4())


def get_logger_context() -> dict:
    return logger_context.get({})


def set_logger_context(logger_data: dict) -> str:
    """
    Returns:
        str: The token for resetting the context
    """
    return logger_context.set(logger_data)


def clear_logger_context() -> None:
    try:
        logger_context.set({})
    except LookupError:
        pass


def get_action_context() -> dict:
    """Get the current action context."""
    try:
        return action_context.get()
    except LookupError:
        return {}


def set_action_context(action_item) -> None:
    """
    Set action context from action_item.

    Args:
        action_item: Action item object or dict with action properties
    """
    # Convert action_item to dict if it has attributes
    if hasattr(action_item, "__dict__"):
        action_dict = action_item.__dict__
    elif isinstance(action_item, dict):
        action_dict = action_item
    else:
        # If it's neither, try to convert to dict
        try:
            action_dict = dict(action_item)
        except (TypeError, ValueError):
            action_dict = {}

    action_context.set(action_dict)


def clear_action_context() -> None:
    """Clear the action context."""
    try:
        action_context.set({})
    except LookupError:
        pass
