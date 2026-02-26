"""Combinatory stock tools: aggregation across stock, categories, and locations."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing_extensions import TypedDict

from ...mcp_server import mcp
from ...tools import django_orm


class StockByCategoryLocationRow(TypedDict):
    category_id: int
    category_name: str
    location_id: int | None
    location_name: str
    total_quantity: float


@mcp.tool()
@django_orm
def stock_by_category_and_location(
    category_id: int | None = None,
) -> list[StockByCategoryLocationRow]:
    """Pivot-table view of stock quantity aggregated by part category and stock location.

    Returns a flat list of rows, each with a category/location pair and the total
    stock quantity for that combination. Useful for warehouse-level overviews
    without needing multiple round-trips.

    Args:
        category_id: Optional category ID to scope results to a single category.
    """
    from django.db.models import Sum
    from part.models import PartCategory
    from stock.models import StockItem, StockLocation

    queryset = StockItem.objects.all()
    if category_id is not None:
        queryset = queryset.filter(part__category=category_id)

    rows = list(
        queryset
        .values("part__category", "location")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("part__category", "location")
    )

    cat_ids = {r["part__category"] for r in rows if r["part__category"] is not None}
    loc_ids = {r["location"] for r in rows if r["location"] is not None}

    cat_names: dict[int, str] = dict(PartCategory.objects.filter(pk__in=cat_ids).values_list("pk", "name"))
    loc_names: dict[int, str] = dict(StockLocation.objects.filter(pk__in=loc_ids).values_list("pk", "name"))

    return [
        {
            "category_id": r["part__category"],
            "category_name": cat_names.get(r["part__category"], "Unknown"),
            "location_id": r["location"],
            "location_name": loc_names.get(r["location"], "Unassigned") if r["location"] is not None else "Unassigned",
            "total_quantity": float(r["total_quantity"]),
        }
        for r in rows
    ]
