"""MCP tool definitions for InvenTree resources."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from collections.abc import Callable


def django_orm(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a sync tool function to run in a thread pool for Django ORM compatibility."""
    async_fn = sync_to_async(fn, thread_sensitive=False)

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await async_fn(*args, **kwargs)

    return wrapper


def _project(row: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """Return only the requested keys from *row*; unknown keys are silently ignored.

    The ``id`` key is always retained regardless of *fields*.
    If *fields* is ``None`` the original dict is returned unchanged.
    """
    if fields is None:
        return row
    keep = set(fields) | {"id"}
    return {k: v for k, v in row.items() if k in keep}
