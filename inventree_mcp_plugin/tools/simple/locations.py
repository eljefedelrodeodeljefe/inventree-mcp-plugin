"""Location tools: list, get, tree."""

from __future__ import annotations

from typing import Any

from ...mcp_server import mcp


@mcp.tool()
def list_locations(
    parent_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List stock locations with optional parent filtering.

    Args:
        parent_id: Filter by parent location ID. Use None for root locations.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from stock.models import StockLocation

    queryset = StockLocation.objects.all()
    if parent_id is not None:
        queryset = queryset.filter(parent_id=parent_id)

    locations = queryset.order_by("name")[offset : offset + limit]
    return [
        {
            "id": loc.pk,
            "name": loc.name,
            "description": loc.description,
            "parent": loc.parent_id,
            "pathstring": loc.pathstring,
        }
        for loc in locations
    ]


@mcp.tool()
def get_location(location_id: int) -> dict[str, Any]:
    """Get detailed information about a stock location.

    Args:
        location_id: The ID of the stock location.
    """
    from stock.models import StockLocation

    loc = StockLocation.objects.get(pk=location_id)
    return {
        "id": loc.pk,
        "name": loc.name,
        "description": loc.description,
        "parent": loc.parent_id,
        "pathstring": loc.pathstring,
        "items_count": loc.stock_items.count(),
        "children_count": loc.children.count(),
    }


@mcp.tool()
def get_location_tree(parent_id: int | None = None, max_depth: int = 3) -> list[dict[str, Any]]:
    """Get a hierarchical tree of stock locations.

    Args:
        parent_id: Root location ID. Use None for the full tree from root.
        max_depth: Maximum depth to traverse.
    """
    from stock.models import StockLocation

    def _build_tree(parent: int | None, depth: int) -> list[dict[str, Any]]:
        if depth <= 0:
            return []
        locations = StockLocation.objects.filter(parent_id=parent).order_by("name")
        return [
            {
                "id": loc.pk,
                "name": loc.name,
                "description": loc.description,
                "children": _build_tree(loc.pk, depth - 1),
            }
            for loc in locations
        ]

    return _build_tree(parent_id, max_depth)
