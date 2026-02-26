"""Location tools: list, get, tree."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import _project, django_orm


@mcp.tool()
@django_orm
def list_locations(
    parent_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List stock locations with optional parent filtering.

    Args:
        parent_id: Filter by parent location ID. Use None for root locations.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, name, description, parent, pathstring.
                Defaults to all. ``id`` is always included.
    """
    from stock.models import StockLocation

    # StockLocation is a TreeBeard model — skip .only() to avoid internal field conflicts.
    queryset = StockLocation.objects.all()
    if parent_id is not None:
        queryset = queryset.filter(parent_id=parent_id)

    locations = queryset.order_by("name")[offset : offset + limit]
    return [
        _project(
            {
                "id": loc.pk,
                "name": loc.name,
                "description": loc.description,
                "parent": loc.parent_id,
                "pathstring": loc.pathstring,
            },
            fields,
        )
        for loc in locations
    ]


@mcp.tool()
@django_orm
def get_location(
    location_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a stock location.

    Args:
        location_id: The ID of the stock location.
        fields: Fields to include. Available: id, name, description, parent, pathstring,
                items_count, children_count. Defaults to all. ``id`` is always included.
    """
    from stock.models import StockLocation

    want = set(fields) if fields is not None else None

    loc = StockLocation.objects.get(pk=location_id)
    row: dict[str, Any] = {"id": loc.pk}
    if want is None or "name" in want:
        row["name"] = loc.name
    if want is None or "description" in want:
        row["description"] = loc.description
    if want is None or "parent" in want:
        row["parent"] = loc.parent_id
    if want is None or "pathstring" in want:
        row["pathstring"] = loc.pathstring
    if want is None or "items_count" in want:
        row["items_count"] = loc.stock_items.count()
    if want is None or "children_count" in want:
        row["children_count"] = loc.children.count()
    return row


@mcp.tool()
@django_orm
def get_location_tree(root_id: int | None = None) -> list[dict[str, Any]]:
    """Get a fully recursive tree of stock locations using a single database query.

    Fetches all locations at once and assembles the hierarchy in memory,
    so the result is complete regardless of tree depth.

    Args:
        root_id: Location ID whose children form the tree root.
                 Use None to return the complete tree starting from all top-level locations.
    """
    from collections import defaultdict

    from stock.models import StockLocation

    all_locs = list(StockLocation.objects.all().order_by("name"))

    children_map: dict[int | None, list[Any]] = defaultdict(list)
    for loc in all_locs:
        children_map[loc.parent_id].append(loc)

    def _build(parent: int | None) -> list[dict[str, Any]]:
        return [
            {
                "id": loc.pk,
                "name": loc.name,
                "description": loc.description,
                "children": _build(loc.pk),
            }
            for loc in children_map[parent]
        ]

    return _build(root_id)
