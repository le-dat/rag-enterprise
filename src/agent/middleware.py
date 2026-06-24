"""
Agent middleware — centralized guards for tool execution.

Usage:
    @rbac_guard(allowed_departments=["HR"])
    def my_tool(..., config: RunnableConfig) -> str:     # sync tool
        ...

    @rbac_guard(allowed_departments=["*"])
    async def my_tool(..., config: RunnableConfig) -> str:  # async tool
        ...
"""
import inspect
import logging
from functools import wraps
from typing import Callable

from langchain_core.runnables import RunnableConfig

from src.agent.schemas import tool_denied, tool_fail

logger = logging.getLogger(__name__)


def _extract_user(args, kwargs):
    """Pull RunnableConfig from args/kwargs and return the user context."""
    config: RunnableConfig = kwargs.get("config") or (
        args[-1] if args and isinstance(args[-1], dict) else {}
    )
    return config, config.get("configurable", {}).get("user")


def rbac_guard(allowed_departments: list[str]) -> Callable:
    """
    Decorator that enforces department-based access control for agent tools.

    Supports both sync and async tool functions. Reads user context from
    LangGraph's RunnableConfig and rejects calls from unauthorized departments
    before the tool body executes.

    Args:
        allowed_departments: List of department strings (case-insensitive).
                             Pass ["*"] to allow any authenticated user.
    """
    normalized = [d.upper() for d in allowed_departments]
    allow_all = "*" in normalized

    def _check(user) -> str | None:
        """Return a denial/error string if access should be blocked, else None."""
        if not user:
            logger.warning("rbac_guard: missing user context in tool call")
            return tool_fail(
                code="UNAUTHENTICATED",
                detail="User context is missing or unauthenticated.",
            )
        if not allow_all and user.department.upper() not in normalized:
            logger.warning(
                "rbac_guard: access denied for user=%s dept=%s, required=%s",
                user.user_id, user.department, allowed_departments,
            )
            return tool_denied(
                user_id=user.user_id,
                department=user.department,
                required=allowed_departments,
            )
        return None

    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs) -> str:
                _, user = _extract_user(args, kwargs)
                denial = _check(user)
                if denial:
                    return denial
                return await fn(*args, **kwargs)
            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args, **kwargs) -> str:
            _, user = _extract_user(args, kwargs)
            denial = _check(user)
            if denial:
                return denial
            return fn(*args, **kwargs)
        return sync_wrapper

    return decorator
