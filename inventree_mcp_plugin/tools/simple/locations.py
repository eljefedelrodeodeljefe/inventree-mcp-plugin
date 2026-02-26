"""Location tools: list, get, tree."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from typing_extensions import TypedDict

from ...mcp_server import mcp
from ...tools import django_orm


class LocationSummary(TypedDict):
    id: int
    name: str
    description: str
    parent: int | None
    pathstring: str


class LocationDetail(TypedDict):
    id: int
    name: str
    description: str
    parent: int | None
    pathstring: str
    items_count: int
    children_count: int


class LocationNode(TypedDict):
    id: int
    name: str
    description: str
    children: list[Any]  # recursive: list[LocationNode]


@mcp.tool()
@django_orm
def list_locations(
    parent_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LocationSummary]:
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
@django_orm
def get_location(location_id: int) -> LocationDetail:
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
@django_orm
def get_location_tree(root_id: int | None = None) -> list[LocationNode]:
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

    def _build(parent: int | None) -> list[LocationNode]:
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
