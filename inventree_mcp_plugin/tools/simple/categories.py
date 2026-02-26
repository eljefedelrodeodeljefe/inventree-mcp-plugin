"""Category tools: list, get, tree."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from typing_extensions import TypedDict

from ...mcp_server import mcp
from ...tools import django_orm


class CategorySummary(TypedDict):
    id: int
    name: str
    description: str
    parent: int | None
    pathstring: str


class CategoryDetail(TypedDict):
    id: int
    name: str
    description: str
    parent: int | None
    pathstring: str
    parts_count: int
    children_count: int


class CategoryNode(TypedDict):
    id: int
    name: str
    description: str
    children: list[Any]  # recursive: list[CategoryNode]


@mcp.tool()
@django_orm
def list_categories(
    parent_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CategorySummary]:
    """List part categories with optional parent filtering.

    Args:
        parent_id: Filter by parent category ID. Use None for root categories.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from part.models import PartCategory

    queryset = PartCategory.objects.all()
    if parent_id is not None:
        queryset = queryset.filter(parent_id=parent_id)

    categories = queryset.order_by("name")[offset : offset + limit]
    return [
        {
            "id": cat.pk,
            "name": cat.name,
            "description": cat.description,
            "parent": cat.parent_id,
            "pathstring": cat.pathstring,
        }
        for cat in categories
    ]


@mcp.tool()
@django_orm
def get_category(category_id: int) -> CategoryDetail:
    """Get detailed information about a part category.

    Args:
        category_id: The ID of the part category.
    """
    from part.models import PartCategory

    cat = PartCategory.objects.get(pk=category_id)
    return {
        "id": cat.pk,
        "name": cat.name,
        "description": cat.description,
        "parent": cat.parent_id,
        "pathstring": cat.pathstring,
        "parts_count": cat.parts.count(),
        "children_count": cat.children.count(),
    }


@mcp.tool()
@django_orm
def get_category_tree(root_id: int | None = None) -> list[CategoryNode]:
    """Get a fully recursive tree of part categories using a single database query.

    Fetches all categories at once and assembles the hierarchy in memory,
    so the result is complete regardless of tree depth.

    Args:
        root_id: Category ID whose children form the tree root.
                 Use None to return the complete tree starting from all top-level categories.
    """
    from collections import defaultdict

    from part.models import PartCategory

    all_cats = list(PartCategory.objects.all().order_by("name"))

    children_map: dict[int | None, list[Any]] = defaultdict(list)
    for cat in all_cats:
        children_map[cat.parent_id].append(cat)

    def _build(parent: int | None) -> list[CategoryNode]:
        return [
            {
                "id": cat.pk,
                "name": cat.name,
                "description": cat.description,
                "children": _build(cat.pk),
            }
            for cat in children_map[parent]
        ]

    return _build(root_id)
