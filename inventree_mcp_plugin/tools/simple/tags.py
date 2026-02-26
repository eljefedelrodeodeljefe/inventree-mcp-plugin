"""Tag tools: list and search django-taggit tags."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import _project, django_orm


@mcp.tool()
@django_orm
def list_tags(
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List all tags defined in the system.

    Args:
        limit: Maximum number of results to return.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, name, slug. Defaults to all.
                ``id`` is always included.
    """
    from taggit.models import Tag

    tags = Tag.objects.order_by("name")[offset : offset + limit]
    return [_project({"id": t.pk, "name": t.name, "slug": t.slug}, fields) for t in tags]


@mcp.tool()
@django_orm
def search_tags(
    query: str,
    limit: int = 50,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search tags by name (case-insensitive substring match).

    Args:
        query: Search string to match against tag names.
        limit: Maximum number of results to return.
        fields: Fields to include. Available: id, name, slug. Defaults to all.
                ``id`` is always included.
    """
    from taggit.models import Tag

    tags = Tag.objects.filter(name__icontains=query).order_by("name")[:limit]
    return [_project({"id": t.pk, "name": t.name, "slug": t.slug}, fields) for t in tags]
