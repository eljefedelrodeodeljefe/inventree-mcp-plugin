"""Category tools: list, get, tree."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import _project, django_orm


@mcp.tool()
@django_orm
def list_categories(
    parent_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List part categories with optional parent filtering.

    Args:
        parent_id: Filter by parent category ID. Use None for root categories.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, name, description, parent, pathstring.
                Defaults to all. ``id`` is always included.
    """
    from part.models import PartCategory

    # PartCategory is a TreeBeard model — skip .only() to avoid internal field conflicts.
    queryset = PartCategory.objects.all()
    if parent_id is not None:
        queryset = queryset.filter(parent_id=parent_id)

    categories = queryset.order_by("name")[offset : offset + limit]
    return [
        _project(
            {
                "id": cat.pk,
                "name": cat.name,
                "description": cat.description,
                "parent": cat.parent_id,
                "pathstring": cat.pathstring,
            },
            fields,
        )
        for cat in categories
    ]


@mcp.tool()
@django_orm
def get_category(
    category_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a part category.

    Args:
        category_id: The ID of the part category.
        fields: Fields to include. Available: id, name, description, parent, pathstring,
                parts_count, children_count. Defaults to all. ``id`` is always included.
    """
    from part.models import PartCategory

    want = set(fields) if fields is not None else None

    cat = PartCategory.objects.get(pk=category_id)
    row: dict[str, Any] = {"id": cat.pk}
    if want is None or "name" in want:
        row["name"] = cat.name
    if want is None or "description" in want:
        row["description"] = cat.description
    if want is None or "parent" in want:
        row["parent"] = cat.parent_id
    if want is None or "pathstring" in want:
        row["pathstring"] = cat.pathstring
    if want is None or "parts_count" in want:
        row["parts_count"] = cat.parts.count()
    if want is None or "children_count" in want:
        row["children_count"] = cat.children.count()
    return row


@mcp.tool()
@django_orm
def get_category_tree(root_id: int | None = None) -> list[dict[str, Any]]:
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

    def _build(parent: int | None) -> list[dict[str, Any]]:
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
