"""Tag tools: list and search django-taggit tags."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing_extensions import TypedDict

from ...mcp_server import mcp
from ...tools import django_orm


class TagResult(TypedDict):
    id: int
    name: str
    slug: str


@mcp.tool()
@django_orm
def list_tags(
    limit: int = 100,
    offset: int = 0,
) -> list[TagResult]:
    """List all tags defined in the system.

    Args:
        limit: Maximum number of results to return.
        offset: Number of results to skip.
    """
    from taggit.models import Tag

    tags = Tag.objects.order_by("name")[offset : offset + limit]
    return [{"id": t.pk, "name": t.name, "slug": t.slug} for t in tags]


@mcp.tool()
@django_orm
def search_tags(query: str, limit: int = 50) -> list[TagResult]:
    """Search tags by name (case-insensitive substring match).

    Args:
        query: Search string to match against tag names.
        limit: Maximum number of results to return.
    """
    from taggit.models import Tag

    tags = Tag.objects.filter(name__icontains=query).order_by("name")[:limit]
    return [{"id": t.pk, "name": t.name, "slug": t.slug} for t in tags]
