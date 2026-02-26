"""Category tools: list, get, tree."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from ...mcp_server import mcp


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
def get_category_tree(parent_id: int | None = None, max_depth: int = 3) -> list[CategoryNode]:
    """Get a hierarchical tree of part categories.

    Args:
        parent_id: Root category ID. Use None for the full tree from root.
        max_depth: Maximum depth to traverse.
    """
    from part.models import PartCategory

    def _build_tree(parent: int | None, depth: int) -> list[CategoryNode]:
        if depth <= 0:
            return []
        categories = PartCategory.objects.filter(parent_id=parent).order_by("name")
        return [
            {
                "id": cat.pk,
                "name": cat.name,
                "description": cat.description,
                "children": _build_tree(cat.pk, depth - 1),
            }
            for cat in categories
        ]

    return _build_tree(parent_id, max_depth)
